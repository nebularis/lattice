"""
mork_pipeline.py

The MORK agent pipeline implemented as a LangGraph StateGraph.

Implements the five-stage pipeline from §5.4 of the foundations:
  Stage 1: Intent Extraction (LLM)
  Stage 2: Mapping Generation (LLM)
  Stage 3: Validation (deterministic)
  Stage 4: Compilation (deterministic)
  Stage 5: Human Review (interrupt)

With feedback loops:
  - Validation failure → retry mapping (bounded by max_iterations)
  - Human review → modify → retry mapping

Preserves:
  - Pipeline determinism (Theorem 5.10) — Stage 4 is a pure function
  - Layer independence (Proposition 5.2a.1) — tool scoping
  - Feedback loop convergence (Proposition C.4) — bounded retries
  - Provenance completeness (Proposition 5.2a.3) — state accumulation
"""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Annotated, List, Optional, TypedDict
from uuid import uuid4

import operator

from langchain_core.messages import BaseMessage, HumanMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver
from rdflib import Graph

from mork_schemas import (
    IntentExtractionOutput,
    MappingGenerationOutput,
    TURTLE_PREFIXES,
    intent_output_to_turtle,
    mapping_output_to_turtle,
)
from mork_validation import validate_fragment

logger = logging.getLogger(__name__)


# ─── State definitions ───

class IntentFragment(TypedDict):
    iri: str
    intent_type: str
    natural_language_source: str
    confidence: float
    turtle: str


class MappingFragment(TypedDict):
    iri: str
    mapping_type: str
    turtle: str
    intent_source: Optional[str]
    validation_status: str
    validation_errors: List[str]


class CompiledArtefact(TypedDict):
    iri: str
    artefact_type: str
    turtle: str
    source_mapping: str
    validation_status: str


class ProvenanceRecord(TypedDict):
    session_id: str
    stage: str
    timestamp: str
    agent_role: str
    model_id: str
    input_hash: str
    output_hash: str


class PipelineState(TypedDict):
    """Full pipeline state, checkpointed at every node transition."""

    # Input
    natural_language_input: str
    session_id: str
    base_namespace: str

    # Layer 1
    intent_output: Optional[IntentExtractionOutput]
    intent_turtle: str

    # Layer 2
    mapping_output: Optional[MappingGenerationOutput]
    mapping_turtle: str

    # Layer 3
    compiled_artefacts: Annotated[List[CompiledArtefact], operator.add]

    # Conversation
    messages: Annotated[List[BaseMessage], add_messages]

    # Control
    current_stage: str
    iteration_count: int
    max_iterations: int
    validation_passed: bool
    validation_errors: List[str]

    # Provenance
    provenance: Annotated[List[ProvenanceRecord], operator.add]

    # Human review
    review_decision: Optional[str]
    review_notes: Optional[str]
    review_explanation: str


# ─── Provenance helper ───

def _make_provenance(
    session_id: str,
    stage: str,
    agent_role: str,
    input_data: str,
    output_data: str,
) -> ProvenanceRecord:
    return ProvenanceRecord(
        session_id=session_id,
        stage=stage,
        timestamp=datetime.now(timezone.utc).isoformat(),
        agent_role=agent_role,
        model_id="",
        input_hash=hashlib.sha256(
            input_data.encode()
        ).hexdigest()[:16],
        output_hash=hashlib.sha256(
            output_data.encode()
        ).hexdigest()[:16],
    )


# ─── Node implementations ───

class PipelineNodes:
    """
    Encapsulates pipeline node functions with their dependencies.

    Dependencies (agents, compiler) are injected at construction
    time so that node functions are pure in their state argument.
    """

    def __init__(
        self,
        intent_agent,
        mapping_agent,
        review_agent,
        compiler=None,
        sparql_endpoint: Optional[str] = None,
        ontology_graph_uri: Optional[str] = None,
    ):
        self.intent_agent = intent_agent
        self.mapping_agent = mapping_agent
        self.review_agent = review_agent
        self.compiler = compiler
        self.sparql_endpoint = sparql_endpoint
        self.ontology_graph_uri = ontology_graph_uri

    async def extract_intents(self, state: PipelineState) -> dict:
        """Stage 1: Intent extraction via the Intent Agent."""
        logger.info("Stage 1: Extracting intents")

        result = await self.intent_agent.ainvoke({
            "messages": [
                HumanMessage(content=(
                    "Extract structured intents from:\n\n"
                    f"{state['natural_language_input']}"
                ))
            ]
        })

        # Extract the structured output from the agent's response
        intent_output = _extract_structured_output(
            result, IntentExtractionOutput
        )

        if intent_output is None:
            logger.warning(
                "Intent agent did not produce structured output; "
                "passing raw messages to next stage"
            )
            return {
                "current_stage": "intent_failed",
                "messages": result.get("messages", []),
                "provenance": [
                    _make_provenance(
                        state["session_id"],
                        "intent_extraction",
                        "IntentAgent",
                        state["natural_language_input"],
                        "FAILED",
                    )
                ],
            }

        turtle = intent_output_to_turtle(
            intent_output, state["base_namespace"]
        )

        return {
            "intent_output": intent_output,
            "intent_turtle": turtle,
            "current_stage": "intent_complete",
            "messages": result.get("messages", []),
            "provenance": [
                _make_provenance(
                    state["session_id"],
                    "intent_extraction",
                    "IntentAgent",
                    state["natural_language_input"],
                    turtle,
                )
            ],
        }

    async def generate_mappings(self, state: PipelineState) -> dict:
        """Stage 2: Mapping generation via the Mapping Agent."""
        logger.info(
            "Stage 2: Generating mappings (iteration %d)",
            state["iteration_count"] + 1,
        )

        # Build the prompt with intent context and any prior errors
        intent_context = state.get("intent_turtle", "")
        prompt_parts = [
            "Generate MORK mappings for these intent nodes:\n\n",
            intent_context,
        ]

        if state.get("validation_errors"):
            prompt_parts.append(
                "\n\nPREVIOUS VALIDATION ERRORS "
                "(you must fix these):\n"
            )
            for err in state["validation_errors"]:
                prompt_parts.append(f"  ✗ {err}\n")

        if state.get("review_notes"):
            prompt_parts.append(
                f"\n\nHUMAN REVIEWER NOTES:\n{state['review_notes']}"
            )

        result = await self.mapping_agent.ainvoke({
            "messages": [HumanMessage(content="".join(prompt_parts))]
        })

        mapping_output = _extract_structured_output(
            result, MappingGenerationOutput
        )

        if mapping_output is None:
            logger.warning(
                "Mapping agent did not produce structured output"
            )
            return {
                "current_stage": "mapping_failed",
                "validation_passed": False,
                "validation_errors": [
                    "Mapping agent failed to produce structured output"
                ],
                "iteration_count": state["iteration_count"] + 1,
                "messages": result.get("messages", []),
            }

        mapping_ns = f"{state['base_namespace']}mappings/"
        turtle = mapping_output_to_turtle(mapping_output, mapping_ns)

        return {
            "mapping_output": mapping_output,
            "mapping_turtle": turtle,
            "current_stage": "mapping_complete",
            "messages": result.get("messages", []),
            "provenance": [
                _make_provenance(
                    state["session_id"],
                    "mapping_generation",
                    "MappingAgent",
                    state.get("intent_turtle", ""),
                    turtle,
                )
            ],
        }

    async def validate(self, state: PipelineState) -> dict:
        """
        Stage 3: Validation (deterministic, no LLM).

        Checks GCI axioms, structural completeness,
        precedence acyclicity, and IRI existence.
        """
        logger.info("Stage 3: Validating mappings")

        turtle = state.get("mapping_turtle", "")
        if not turtle.strip():
            return {
                "validation_passed": False,
                "validation_errors": ["No mapping Turtle to validate"],
                "iteration_count": state["iteration_count"] + 1,
                "current_stage": "validation_complete",
            }

        result = validate_fragment(
            turtle,
            sparql_endpoint=self.sparql_endpoint,
            ontology_graph_uri=self.ontology_graph_uri,
        )

        return {
            "validation_passed": result.valid,
            "validation_errors": result.violations + [
                f"WARNING: {w}" for w in result.warnings
            ],
            "iteration_count": state["iteration_count"] + 1,
            "current_stage": "validation_complete",
        }

    async def compile(self, state: PipelineState) -> dict:
        """
        Stage 4: Compilation (deterministic, no LLM).

        Uses the existing MORK compiler. If no compiler is
        configured, passes through the validated Turtle as-is.
        """
        logger.info("Stage 4: Compiling artefacts")

        turtle = state.get("mapping_turtle", "")

        if self.compiler is not None:
            try:
                g = Graph()
                g.parse(data=turtle, format="turtle")
                compiled = self.compiler.compile_graph(g)
                artefacts = [
                    CompiledArtefact(
                        iri=str(a.iri),
                        artefact_type=a.type,
                        turtle=a.serialise("turtle"),
                        source_mapping=str(a.source_mapping_iri),
                        validation_status="compiled",
                    )
                    for a in compiled.artefacts
                ]
            except Exception as e:
                logger.error("Compilation failed: %s", e)
                artefacts = []
        else:
            # No compiler available — pass through the mapping Turtle
            # as a single artefact for review
            artefacts = [
                CompiledArtefact(
                    iri=f"urn:mork:passthrough:{state['session_id']}",
                    artefact_type="passthrough",
                    turtle=turtle,
                    source_mapping="",
                    validation_status="uncompiled",
                )
            ]

        return {
            "compiled_artefacts": artefacts,
            "current_stage": "compilation_complete",
            "provenance": [
                _make_provenance(
                    state["session_id"],
                    "compilation",
                    "Compiler",
                    turtle,
                    json.dumps([a["iri"] for a in artefacts]),
                )
            ],
        }

    async def review(self, state: PipelineState) -> dict:
        """
        Stage 5: Review preparation via the Review Agent.

        Generates human-readable explanations. The pipeline
        pauses after this node for human input.
        """
        logger.info("Stage 5: Preparing review package")

        artefact_summary = "\n\n".join(
            f"Artefact: {a['iri']}\nType: {a['artefact_type']}\n"
            f"Turtle:\n{a['turtle'][:500]}"
            for a in state.get("compiled_artefacts", [])
        )

        result = await self.review_agent.ainvoke({
            "messages": [
                HumanMessage(content=(
                    "Prepare a review package for these artefacts. "
                    "Explain each in plain English, trace provenance, "
                    "and flag concerns.\n\n"
                    f"{artefact_summary}"
                ))
            ]
        })

        explanation = ""
        for msg in result.get("messages", []):
            if hasattr(msg, "content") and isinstance(msg.content, str):
                explanation = msg.content
                break

        return {
            "current_stage": "review_pending",
            "review_explanation": explanation,
            "messages": result.get("messages", []),
        }

    async def finalise(self, state: PipelineState) -> dict:
        """
        Write approved artefacts to the graph store.

        In the PoC, this logs the output. In production, this
        writes to the staging graph and marks provenance as APPROVED.
        """
        logger.info(
            "Finalising: %d artefacts approved",
            len(state.get("compiled_artefacts", [])),
        )

        # In a full implementation, this would:
        # 1. Write to urn:mork:staging:{session_id}
        # 2. Update provenance reviewStatus to APPROVED
        # 3. Optionally promote to production graphs

        return {
            "current_stage": "finalised",
        }


def _extract_structured_output(result: dict, schema_type):
    """Extract structured output from a ReAct agent result."""
    for msg in reversed(result.get("messages", [])):
        if hasattr(msg, "content"):
            content = msg.content
            if isinstance(content, schema_type):
                return content
            if isinstance(content, dict):
                try:
                    return schema_type(**content)
                except Exception:
                    pass
            if isinstance(content, str):
                try:
                    data = json.loads(content)
                    return schema_type(**data)
                except Exception:
                    pass
    return None


# ─── Routing functions ───

def _should_retry_mapping(state: PipelineState) -> str:
    """Route after validation: compile, retry, or escalate."""
    if state.get("validation_passed", False):
        return "compile"
    if state.get("iteration_count", 0) >= state.get(
        "max_iterations", 5
    ):
        return "escalate"
    return "retry_mapping"


def _after_review(state: PipelineState) -> str:
    """Route after human review decision."""
    decision = state.get("review_decision")
    if decision == "approve":
        return "finalise"
    if decision == "modify":
        return "retry_mapping"
    return "end"


# ─── Pipeline construction ───

def build_pipeline(
    nodes: PipelineNodes,
    checkpoint_backend: str = "memory",
) -> StateGraph:
    """
    Build and compile the MORK agent pipeline.

    Returns a compiled LangGraph application ready to invoke.
    """
    workflow = StateGraph(PipelineState)

    # Register nodes
    workflow.add_node("extract_intents", nodes.extract_intents)
    workflow.add_node("generate_mappings", nodes.generate_mappings)
    workflow.add_node("validate", nodes.validate)
    workflow.add_node("compile", nodes.compile)
    workflow.add_node("review", nodes.review)
    workflow.add_node("finalise", nodes.finalise)

    # Wire edges
    workflow.add_edge(START, "extract_intents")
    workflow.add_edge("extract_intents", "generate_mappings")
    workflow.add_edge("generate_mappings", "validate")

    workflow.add_conditional_edges(
        "validate",
        _should_retry_mapping,
        {
            "compile": "compile",
            "retry_mapping": "generate_mappings",
            "escalate": "review",
        },
    )

    workflow.add_edge("compile", "review")

    workflow.add_conditional_edges(
        "review",
        _after_review,
        {
            "finalise": "finalise",
            "retry_mapping": "generate_mappings",
            "end": END,
        },
    )

    workflow.add_edge("finalise", END)

    # Configure checkpointing
    if checkpoint_backend == "memory":
        checkpointer = MemorySaver()
    else:
        raise ValueError(
            f"Checkpoint backend '{checkpoint_backend}' not "
            f"implemented in PoC. Use 'memory' or extend with "
            f"SqliteSaver/PostgresSaver."
        )

    return workflow.compile(
        checkpointer=checkpointer,
        interrupt_before=["review"],
    )


def create_initial_state(
    natural_language_input: str,
    base_namespace: str = "urn:mork:session:",
    max_iterations: int = 3,
) -> PipelineState:
    """Create the initial pipeline state for a new session."""
    session_id = str(uuid4())[:8]
    return PipelineState(
        natural_language_input=natural_language_input,
        session_id=session_id,
        base_namespace=f"{base_namespace}{session_id}/",
        intent_output=None,
        intent_turtle="",
        mapping_output=None,
        mapping_turtle="",
        compiled_artefacts=[],
        messages=[],
        current_stage="start",
        iteration_count=0,
        max_iterations=max_iterations,
        validation_passed=False,
        validation_errors=[],
        provenance=[],
        review_decision=None,
        review_notes=None,
        review_explanation="",
    )