import pytest

from lattice_workers.graph_validation import GraphReference, InvalidJob
from lattice_workers.projection_lowering import process_projection_lower


def graph(name):
    return {"tenantId": "tenant", "projectId": "project", "graphIri": f"https://example.test/graphs/{name}", "revisionHash": "sha256:abc"}


def message():
    return {"jobId": "lower-1", "correlationId": "correlation-1", "contractGraph": graph("projection-contract"), "profileGraph": graph("profile"), "stagingNamespace": "https://example.test/mork/staging/"}


def test_lowering_returns_only_a_staging_graph():
    result = process_projection_lower(message(), lambda contract, profile, namespace: (GraphReference("tenant", "project", namespace + "arr", "sha256:abc"), []))
    assert result["outcome"] == "succeeded"
    assert result["stagingGraph"]["graphIri"].startswith("https://example.test/mork/staging/")


def test_lowering_rejects_active_mapping_target_in_request():
    with pytest.raises(InvalidJob, match="staging namespace only"):
        process_projection_lower(message() | {"activeMappingGraph": graph("active")}, lambda *arguments: (GraphReference("tenant", "project", "https://example.test/mork/staging/arr", "sha256:abc"), []))


def test_lowering_rejects_adapter_result_outside_staging_namespace():
    with pytest.raises(InvalidJob, match="outside the requested immutable staging namespace"):
        process_projection_lower(message(), lambda contract, profile, namespace: (GraphReference("tenant", "project", "https://example.test/mork/active/arr", "sha256:abc"), []))