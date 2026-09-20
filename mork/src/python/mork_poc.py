"""
mork_poc.py

Proof-of-concept entry point for the MORK agent pipeline.

Demonstrates the full end-to-end flow:
  1. Accept natural language input
  2. Run the pipeline to the review interrupt
  3. Display the review package
  4. Accept a review decision
  5. Finalise or abort

Prerequisites:
  - A running SPARQL endpoint (Jena Fuseki or Stardog)
    with the target ontology loaded, OR
  - Set MORK_OFFLINE=1 to run without a triple store
    (retrieval tools return empty results)

  - A LiteLLM-compatible model configured via environment:
    LITELLM_MODEL=anthropic/claude-sonnet-4-20250514
    ANTHROPIC_API_KEY=sk-...

Usage:
  python mork_poc.py "Revenue between 10M and 100M excluding nation-state attacks"
  python mork_poc.py --offline "cyber cover up to 25M in US states"
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("mork_poc")


# ─── Offline stub for GraphRAGClient ───

class OfflineGraphRAGClient:
    """
    Stub client for running the PoC without a triple store.

    Returns empty but structurally valid results for all queries.
    Useful for testing the pipeline orchestration, schema
    validation, and Turtle generation without infrastructure.
    """

    class _Result:
        def __init__(self):
            self.serialised_context = "(No triple store configured — offline mode)"
            self.token_estimate = 20
            self.latency_ms = 0.0
            self.result_count = 0
            self.template_name = "offline"
            self.parameters_used = {}
            self.raw_results = {}

    def execute(self, template, parameters, session=None):
        logger.debug(
            "Offline retrieval: %s with %s",
            getattr(template, "name", template.get("name", "?")),
            parameters,
        )
        return self._Result()


def _get_template_library():
    """
    Load the standard SPARQL template library.

    In offline mode, templates are still needed (for their names
    and structure) even though execution returns empty results.
    """
    try:
        from graph_rag_client import TEMPLATE_LIBRARY
        return TEMPLATE_LIBRARY
    except ImportError:
        # Minimal stub templates for offline mode
        class _Stub:
            def __init__(self, name):
                self.name = name

        return {
            "I1_ConceptLookup": _Stub("I1_ConceptLookup"),
            "M1_ClassContext": _Stub("M1_ClassContext"),
            "M2_PathFinding": _Stub("M2_PathFinding"),
            "M3_TemplateMatch": _Stub("M3_TemplateMatch"),
            "M4_ExistingMappings": _Stub("M4_ExistingMappings"),
            "R1_ConflictDetection": _Stub("R1_ConflictDetection"),
        }


async def run_pipeline(
    natural_language_input: str,
    offline: bool = False,
    model: str = "anthropic/claude-sonnet-4-20250514",
):
    """Run the MORK pipeline end-to-end on the given input."""

    # ─── Dependency setup ───

    if offline:
        graph_rag_client = OfflineGraphRAGClient()
        sparql_endpoint = None
        ontology_graph_uri = None
    else:
        from graph_rag_client import GraphRAGClient
        sparql_endpoint = os.environ.get(
            "MORK_SPARQL_ENDPOINT", "http://localhost:3030/mork/sparql"
        )
        ontology_graph_uri = os.environ.get(
            "MORK_ONTOLOGY_GRAPH", "urn:mork:ontology:target"
        )
        graph_rag_client = GraphRAGClient(
            endpoint_url=sparql_endpoint,
        )

    template_library = _get_template_library()

    from mork_agents import (
        create_intent_agent,
        create_mapping_agent,
        create_review_agent,
    )
    from mork_communities.pipeline import (
        PipelineNodes,
        build_pipeline,
        create_initial_state,
    )

    intent_agent = create_intent_agent(
        graph_rag_client, template_library, model=model
    )
    mapping_agent = create_mapping_agent(
        graph_rag_client,
        template_library,
        sparql_endpoint=sparql_endpoint,
        ontology_graph_uri=ontology_graph_uri,
        model=model,
    )
    review_agent = create_review_agent(
        graph_rag_client,
        template_library,
        sparql_endpoint=sparql_endpoint,
        ontology_graph_uri=ontology_graph_uri,
    )

    nodes = PipelineNodes(
        intent_agent=intent_agent,
        mapping_agent=mapping_agent,
        review_agent=review_agent,
        compiler=None,  # PoC: no compiler; passthrough mode
        sparql_endpoint=sparql_endpoint,
        ontology_graph_uri=ontology_graph_uri,
    )

    pipeline = build_pipeline(nodes, checkpoint_backend="memory")
    config = {"configurable": {"thread_id": "poc-session"}}

    # ─── Run to review interrupt ───

    print("\n" + "=" * 60)
    print("MORK Agent Pipeline — Proof of Concept")
    print("=" * 60)
    print(f"\nInput: {natural_language_input}")
    print(f"Mode:  {'offline' if offline else 'connected'}")
    print(f"Model: {model}")
    print("-" * 60)

    initial_state = create_initial_state(
        natural_language_input=natural_language_input,
        max_iterations=3,
    )

    print("\n▶ Running pipeline (Stages 1–4)...\n")

    result = await pipeline.ainvoke(initial_state, config)

    # ─── Display review package ───

    print("\n" + "=" * 60)
    print("REVIEW PACKAGE")
    print("=" * 60)

    print(f"\nStage: {result.get('current_stage', '?')}")
    print(
        f"Validation passed: {result.get('validation_passed', '?')}"
    )
    print(
        f"Iterations: {result.get('iteration_count', '?')}"
        f"/{result.get('max_iterations', '?')}"
    )

    if result.get("validation_errors"):
        print("\nValidation issues:")
        for err in result["validation_errors"]:
            print(f"  {'✗' if not err.startswith('WARNING') else '⚠'} {err}")

    if result.get("intent_turtle"):
        print("\n--- Layer 1: Intent Turtle ---")
        print(result["intent_turtle"][:2000])

    if result.get("mapping_turtle"):
        print("\n--- Layer 2: Mapping Turtle ---")
        print(result["mapping_turtle"][:2000])

    artefacts = result.get("compiled_artefacts", [])
    if artefacts:
        print(f"\n--- Layer 3: {len(artefacts)} Compiled Artefact(s) ---")
        for a in artefacts:
            print(f"  {a['iri']} ({a['artefact_type']})")

    if result.get("review_explanation"):
        print("\n--- Review Agent Explanation ---")
        print(result["review_explanation"][:2000])

    if result.get("provenance"):
        print(f"\n--- Provenance: {len(result['provenance'])} records ---")
        for p in result["provenance"]:
            print(f"  [{p['stage']}] {p['agent_role']} at {p['timestamp']}")

    # ─── Human review decision ───

    print("\n" + "=" * 60)
    decision = input(
        "Review decision [approve/modify/reject] (default: approve): "
    ).strip().lower()

    if not decision:
        decision = "approve"

    notes = ""
    if decision == "modify":
        notes = input("Modification notes: ").strip()

    # ─── Resume pipeline with decision ───

    print(f"\n▶ Resuming with decision: {decision}")

    final_result = await pipeline.ainvoke(
        {
            "review_decision": decision,
            "review_notes": notes if notes else None,
        },
        config,
    )

    print(f"\nFinal stage: {final_result.get('current_stage', '?')}")
    print("\n✓ Pipeline complete.")

    return final_result


def main():
    parser = argparse.ArgumentParser(
        description="MORK Agent Pipeline — Proof of Concept"
    )
    parser.add_argument(
        "input",
        nargs="?",
        default=(
            "Revenue between $10M and $100M for technology companies, "
            "excluding nation-state attacks"
        ),
        help="Natural language specification to process",
    )
    parser.add_argument(
        "--offline",
        action="store_true",
        default=bool(os.environ.get("MORK_OFFLINE")),
        help="Run without a triple store (offline mode)",
    )
    parser.add_argument(
        "--model",
        default=os.environ.get(
            "LITELLM_MODEL", "anthropic/claude-sonnet-4-20250514"
        ),
        help="LiteLLM model identifier",
    )

    args = parser.parse_args()

    try:
        asyncio.run(
            run_pipeline(
                args.input,
                offline=args.offline,
                model=args.model,
            )
        )
    except KeyboardInterrupt:
        print("\n\nAborted by user.")
        sys.exit(1)


if __name__ == "__main__":
    main()