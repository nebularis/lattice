import pytest

from lattice_workers.graph_validation import InvalidJob, process_graph_validation


def message():
    return {"jobId": "job-1", "correlationId": "correlation-1", "profileId": "https://example.test/profiles/default", "graph": {"tenantId": "tenant", "projectId": "project", "graphIri": "https://example.test/graphs/contract", "revisionHash": "sha256:abc"}}


def test_worker_returns_a_graph_reference_result():
    result = process_graph_validation(message(), lambda graph, profile: [])
    assert result["outcome"] == "valid"
    assert result["graph"]["revisionHash"] == "sha256:abc"


def test_worker_rejects_inline_rdf():
    invalid = message() | {"turtle": "@prefix ex: <https://example.test/> ."}
    with pytest.raises(InvalidJob, match="graph references"):
        process_graph_validation(invalid, lambda graph, profile: [])
