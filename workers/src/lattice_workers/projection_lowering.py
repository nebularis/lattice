"""Staged Projection lowering boundary for existing Surface lowering semantics."""

from __future__ import annotations

from typing import Any, Callable, Mapping

from .graph_validation import GraphReference, InvalidJob


def process_projection_lower(
    message: Mapping[str, Any],
    lower: Callable[[GraphReference, GraphReference, str], tuple[GraphReference, list[str]]],
) -> dict[str, Any]:
    forbidden = {"rdf", "turtle", "nquads", "activeMappingGraph", "credentials", "accessToken", "browserToken", "command"}
    if forbidden.intersection(message):
        raise InvalidJob("Projection lowering accepts immutable graph references and staging namespace only")
    required = {"jobId", "correlationId", "contractGraph", "profileGraph", "stagingNamespace"}
    if set(message) != required or any(not isinstance(message[field], str) or not message[field] for field in ("jobId", "correlationId", "stagingNamespace")):
        raise InvalidJob("message fields do not match projection-lower-request 1.0.0")
    contract = GraphReference.from_payload(message["contractGraph"])
    profile = GraphReference.from_payload(message["profileGraph"])
    if contract.tenant_id != profile.tenant_id or contract.project_id != profile.project_id:
        raise InvalidJob("Projection lowering graph references must share a tenant and project scope")
    staging, diagnostics = lower(contract, profile, message["stagingNamespace"])
    if staging.tenant_id != contract.tenant_id or staging.project_id != contract.project_id or not staging.graph_iri.startswith(message["stagingNamespace"]):
        raise InvalidJob("lowering adapter returned a graph outside the requested immutable staging namespace")
    return {"jobId": message["jobId"], "correlationId": message["correlationId"], "outcome": "succeeded" if not diagnostics else "failed", "stagingGraph": {"tenantId": staging.tenant_id, "projectId": staging.project_id, "graphIri": staging.graph_iri, "revisionHash": staging.revision_hash}, "backendCapabilities": ["sparql", "shacl", "swrl", "rml", "native_ir"], "diagnostics": diagnostics}