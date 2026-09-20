import pytest

from lattice_workers.graph_validation import InvalidJob
from lattice_workers.surface_jobs import process_surface_job


def message():
    graph = {"tenantId": "tenant", "projectId": "project", "graphIri": "https://example.test/graphs/contract", "revisionHash": "sha256:abc"}
    return {"jobId": "job-1", "correlationId": "correlation-1", "jobType": "generation", "contractGraph": graph, "profileGraph": graph | {"graphIri": "https://example.test/graphs/profile"}, "sourceGraphs": []}


def test_surface_job_dispatches_only_graph_references():
    result = process_surface_job(message(), lambda job_type, contract, profile, sources, manifest: ([{"digest": "sha256:output"}], []))
    assert result["outcome"] == "succeeded"
    assert result["outputs"] == [{"digest": "sha256:output"}]


def test_surface_job_rejects_compiler_commands():
    invalid = message() | {"command": "python -m tools.surface compile"}
    with pytest.raises(InvalidJob, match="credentials, or commands"):
        process_surface_job(invalid, lambda *arguments: ([], []))


def test_surface_job_rejects_cross_project_sources():
    invalid = message() | {"sourceGraphs": [{"tenantId": "tenant", "projectId": "other", "graphIri": "https://example.test/graphs/source", "revisionHash": "sha256:abc"}]}
    with pytest.raises(InvalidJob, match="tenant and project"):
        process_surface_job(invalid, lambda *arguments: ([], []))


def test_invalidation_requires_a_separate_manifest_reference():
    invalid = message() | {"jobType": "invalidation"}
    with pytest.raises(InvalidJob, match="manifest graph reference"):
        process_surface_job(invalid, lambda *arguments: ([], []))
