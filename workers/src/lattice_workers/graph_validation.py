"""Worker boundary for graph-reference validation jobs."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping


class InvalidJob(ValueError):
    """Raised when an untrusted job violates the graph-reference contract."""


@dataclass(frozen=True)
class GraphReference:
    tenant_id: str
    project_id: str
    graph_iri: str
    revision_hash: str

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> "GraphReference":
        required = ("tenantId", "projectId", "graphIri", "revisionHash")
        if set(payload) != set(required) or any(not isinstance(payload[name], str) or not payload[name] for name in required):
            raise InvalidJob("graph must contain only non-empty graph-reference fields")
        if not payload["graphIri"].startswith(("http://", "https://")):
            raise InvalidJob("graphIri must be an absolute HTTP(S) IRI")
        return cls(payload["tenantId"], payload["projectId"], payload["graphIri"], payload["revisionHash"])


def process_graph_validation(message: Mapping[str, Any], validate: Callable[[GraphReference, str], list[str]]) -> dict[str, Any]:
    forbidden = {"rdf", "turtle", "nquads", "credentials", "accessToken", "browserToken"}
    if forbidden.intersection(message):
        raise InvalidJob("jobs must contain graph references, not RDF or credentials")
    required = {"jobId", "correlationId", "graph", "profileId"}
    if set(message) != required or any(not isinstance(message[field], str) or not message[field] for field in ("jobId", "correlationId", "profileId")):
        raise InvalidJob("message fields do not match graph-validation-request 1.0.0")
    graph = GraphReference.from_payload(message["graph"])
    diagnostics = validate(graph, message["profileId"])
    return {
        "jobId": message["jobId"],
        "correlationId": message["correlationId"],
        "outcome": "valid" if not diagnostics else "invalid",
        "graph": {"tenantId": graph.tenant_id, "projectId": graph.project_id, "graphIri": graph.graph_iri, "revisionHash": graph.revision_hash},
        "diagnostics": diagnostics,
    }
