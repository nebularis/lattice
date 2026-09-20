import pytest

from lattice_workers.graph_validation import InvalidJob
from lattice_workers.mork_analysis_worker import process_mork_analysis


def message():
    return {"jobId": "analysis-1", "correlationId": "correlation-1", "mappingGraph": {"tenantId": "tenant", "projectId": "project", "graphIri": "https://example.test/mork/staging/arr", "revisionHash": "sha256:abc"}, "reviewerRole": "domain_steward"}


def test_domain_steward_result_excludes_technical_mork_content():
    result = process_mork_analysis(message(), lambda graph: {"snapshotId": "snapshot-1", "snapshotHash": graph.revision_hash, "sectionId": "section-1", "tenantId": graph.tenant_id, "projectId": graph.project_id, "mcn": "restricted", "technicalDiagnostics": ["restricted"], "evidenceProjection": []})
    assert "mcn" not in result["snapshot"]
    assert "technicalDiagnostics" not in result["snapshot"]


def test_cross_scope_analysis_result_is_rejected():
    with pytest.raises(InvalidJob, match="outside"):
        process_mork_analysis(message(), lambda graph: {"tenantId": "other", "projectId": graph.project_id})