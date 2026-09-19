"""Scope-restricted boundary around existing MORK validation and community analysis."""

from __future__ import annotations

from typing import Any, Callable, Mapping

from .graph_validation import GraphReference, InvalidJob
from .mork_evidence_projection import project_evidence


def process_mork_analysis(
    message: Mapping[str, Any],
    analyse: Callable[[GraphReference], Mapping[str, Any]],
) -> dict[str, Any]:
    required = {"jobId", "correlationId", "mappingGraph", "reviewerRole"}
    forbidden = {"rdf", "turtle", "mcn", "credentials", "accessToken", "browserToken", "command"}
    if forbidden.intersection(message) or set(message) != required:
        raise InvalidJob("MORK analysis accepts only mapping graph references and reviewer role")
    graph = GraphReference.from_payload(message["mappingGraph"])
    snapshot = dict(analyse(graph))
    if snapshot.get("tenantId") != graph.tenant_id or snapshot.get("projectId") != graph.project_id:
        raise InvalidJob("MORK analysis adapter returned evidence outside the requested graph scope")
    return {"jobId": message["jobId"], "correlationId": message["correlationId"], "snapshot": project_evidence(snapshot, message["reviewerRole"])}