"""Graph-reference job boundary for existing Surface compiler operations."""

from __future__ import annotations

from typing import Any, Callable, Mapping

from .graph_validation import GraphReference, InvalidJob

SURFACE_JOB_TYPES = frozenset({"generation", "parity", "invalidation"})


def process_surface_job(
    message: Mapping[str, Any],
    execute: Callable[[str, GraphReference, GraphReference, list[GraphReference], GraphReference | None], tuple[list[dict[str, str]], list[str]]],
) -> dict[str, Any]:
    """Validate a Surface job envelope and delegate to a graph-resolving adapter."""
    forbidden = {"rdf", "turtle", "nquads", "credentials", "accessToken", "browserToken", "command"}
    if forbidden.intersection(message):
        raise InvalidJob("Surface jobs must contain graph references, not RDF, credentials, or commands")
    required = {"jobId", "correlationId", "jobType", "contractGraph", "profileGraph", "sourceGraphs"}
    allowed = required | {"manifestGraph"}
    if not required.issubset(message) or not set(message).issubset(allowed) or any(not isinstance(message[field], str) or not message[field] for field in ("jobId", "correlationId", "jobType")):
        raise InvalidJob("message fields do not match surface-job-request 1.0.0")
    if message["jobType"] not in SURFACE_JOB_TYPES or not isinstance(message["sourceGraphs"], list):
        raise InvalidJob("Surface job type or source graph list is invalid")

    contract_graph = GraphReference.from_payload(message["contractGraph"])
    profile_graph = GraphReference.from_payload(message["profileGraph"])
    source_graphs = [GraphReference.from_payload(graph) for graph in message["sourceGraphs"]]
    manifest_graph = GraphReference.from_payload(message["manifestGraph"]) if "manifestGraph" in message else None
    if message["jobType"] == "invalidation" and manifest_graph is None:
        raise InvalidJob("invalidation jobs require a generated manifest graph reference")
    if message["jobType"] != "invalidation" and manifest_graph is not None:
        raise InvalidJob("manifestGraph is only valid for invalidation jobs")
    all_graphs = [profile_graph, *source_graphs, *([manifest_graph] if manifest_graph else [])]
    if any(graph.tenant_id != contract_graph.tenant_id or graph.project_id != contract_graph.project_id for graph in all_graphs):
        raise InvalidJob("Surface job graph references must share a tenant and project scope")

    outputs, diagnostics = execute(message["jobType"], contract_graph, profile_graph, source_graphs, manifest_graph)
    return {
        "jobId": message["jobId"],
        "correlationId": message["correlationId"],
        "jobType": message["jobType"],
        "outcome": "succeeded" if not diagnostics else "failed",
        "contractGraph": message["contractGraph"],
        "profileGraph": message["profileGraph"],
        "outputs": outputs,
        "diagnostics": diagnostics,
    }
