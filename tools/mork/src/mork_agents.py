"""
mork_agents.py

Agent constructors for the MORK pipeline.

Each agent is a LangGraph ReAct agent with:
  - A role-specific system prompt
  - A scoped tool set (enforcing R1: layer independence)
  - Structured output configuration

Implements:
  - Agent roles from §D.5.2 and §5 of the reference architecture
  - Tool scoping from §D.4.2
"""

from __future__ import annotations

from typing import List, Optional

from langchain_litellm import ChatLiteLLM
from langgraph.prebuilt import create_react_agent

from mork_schemas import IntentExtractionOutput, MappingGenerationOutput
from mork_tools import create_tools


# ─── System prompts ───

INTENT_AGENT_PROMPT = """You are the MORK Intent-Agent. You extract structured semantic intents from natural language specifications.

You produce a JSON object matching the IntentExtractionOutput schema. Each IntentNode has:
- local_name: a short, descriptive identifier (e.g., "intent_cyber_cover")
- intent_types: one or more from CoverageIntent, QuantitativeConstraint, SpatialScope, TemporalScope, ExclusionIntent, InclusionIntent
- natural_language_source: the exact text fragment this intent was extracted from
- confidence: your extraction confidence (0.0–1.0)
- refines_intents: local names of component intents (for compound intents)

For QuantitativeConstraint, also set: constraint_operator, constraint_value, constraint_upper_value (if Between), constraint_unit_iri.
For SpatialScope, also set: scope_type, scope_inclusion, scope_value_iri.

RULES:
1. Use the lookup_skos_concepts tool to ground entity references against controlled vocabularies.
2. Do NOT reference target ontology classes or properties. Intents are ontology-independent.
3. Compound intents refine their components. E.g., "cyber cover up to $25M in US states" refines "cyber cover", "up to $25M", and "in US states".
4. Set confidence below 0.6 for genuinely ambiguous phrases."""


MAPPING_AGENT_PROMPT = """You are the MORK Mapping-Agent. You produce DataMapping, ShapeMapping, and RuleMapping individuals as a JSON object matching the MappingGenerationOutput schema.

MANDATORY WORKFLOW (follow this order):
1. Call retrieve_class_context for each target class mentioned in the intents.
2. Call find_property_paths to identify valid property chains for sh:path expressions.
3. Call find_existing_mappings to check for reusable mappings (prefer weighting >= 70).
4. Call find_templates to check for applicable ShapeTemplates or RuleTemplates.
5. Generate mappings as MappingSpec instances.
6. Call validate_mork_fragment on the generated Turtle to confirm GCI compliance.

SCHEMA RULES:
- Every ShapeMapping and RuleMapping MUST have targeting_spec and at least one parameter_binding.
- If using broader_applicative, you MUST include an exactRBoxMatch or inverseRBoxMatch in box_matches (GCI 2.14a).
- A Datum MUST have deferred_mapping (GCI 2.7a).
- Every IRI you reference in box_matches.target_iri MUST come from the retrieved context. Do NOT invent IRIs.

PARAMETER BINDINGS:
- param_type "Path": param_value is a space-separated list of property IRIs forming the sh:path.
- param_type "Numeric": param_value is a decimal number.
- param_type "Concept": param_value is a SKOS concept IRI.
- param_type "String": param_value is a literal string.

Set weighting between 60-95 based on your confidence. Set mapping_note to explain your reasoning."""


REVIEW_AGENT_PROMPT = """You are the MORK Review-Agent. You validate and explain generated artefacts for human reviewers.

For each artefact, provide:
1. A plain-English explanation of what it does.
2. Which IntentNode it traces back to.
3. Any concerns or potential conflicts with existing constraints.
4. A confidence assessment.

Use detect_conflicts to check for contradictions with existing constraints.
Use validate_mork_fragment to verify structural correctness.
Be precise. Cite specific IRIs. Explain the provenance chain."""


# ─── Agent constructors ───

def create_intent_agent(
    graph_rag_client,
    template_library: dict,
    model: str = "anthropic/claude-sonnet-4-20250514",
):
    """
    Create the Intent Agent (Layer 1).

    Access restricted to SKOS vocabularies and existing intents.
    Produces IntentExtractionOutput via structured output.
    """
    llm = ChatLiteLLM(model=model, temperature=0.1)
    structured_llm = llm.with_structured_output(
        IntentExtractionOutput
    )

    tools = create_tools(
        graph_rag_client=graph_rag_client,
        template_library=template_library,
        allowed_graphs=[
            "urn:mork:skos:vocabularies",
            "urn:mork:intents:active",
        ],
    )

    return create_react_agent(
        structured_llm,
        tools,
        state_modifier=INTENT_AGENT_PROMPT,
    )


def create_mapping_agent(
    graph_rag_client,
    template_library: dict,
    sparql_endpoint: Optional[str] = None,
    ontology_graph_uri: Optional[str] = None,
    model: str = "anthropic/claude-sonnet-4-20250514",
):
    """
    Create the Mapping Agent (Layer 2).

    Full access to target ontology, existing mappings, and templates.
    Produces MappingGenerationOutput via structured output.
    """
    llm = ChatLiteLLM(model=model, temperature=0.0)
    structured_llm = llm.with_structured_output(
        MappingGenerationOutput
    )

    tools = create_tools(
        graph_rag_client=graph_rag_client,
        template_library=template_library,
        allowed_graphs=[
            "urn:mork:ontology:target",
            "urn:mork:mappings:active",
            "urn:mork:mappings:templates",
            "urn:mork:skos:vocabularies",
        ],
        sparql_endpoint=sparql_endpoint,
        ontology_graph_uri=ontology_graph_uri,
    )

    return create_react_agent(
        structured_llm,
        tools,
        state_modifier=MAPPING_AGENT_PROMPT,
    )


def create_review_agent(
    graph_rag_client,
    template_library: dict,
    sparql_endpoint: Optional[str] = None,
    ontology_graph_uri: Optional[str] = None,
    model: str = "anthropic/claude-haiku-3",
):
    """
    Create the Review Agent (cross-layer validation and explanation).

    Uses a smaller model — explanation does not require frontier reasoning.
    """
    llm = ChatLiteLLM(model=model, temperature=0.2)

    tools = create_tools(
        graph_rag_client=graph_rag_client,
        template_library=template_library,
        allowed_graphs=[
            "urn:mork:constraints:active",
            "urn:mork:mappings:active",
        ],
        sparql_endpoint=sparql_endpoint,
        ontology_graph_uri=ontology_graph_uri,
    )

    return create_react_agent(
        llm,
        tools,
        state_modifier=REVIEW_AGENT_PROMPT,
    )