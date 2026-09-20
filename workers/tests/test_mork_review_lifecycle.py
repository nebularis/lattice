import pytest

from lattice_workers.mork_evidence_projection import project_evidence
from lattice_workers.mork_review_lifecycle import ReviewLifecycle, ReviewSnapshot, StaleReviewSnapshotError


def snapshot(version=1, digest="sha256:" + "a" * 64):
    return ReviewSnapshot("snapshot-1", digest, "tenant", "project", "section-1", version)


def test_stale_snapshot_decision_conflicts_safely():
    lifecycle = ReviewLifecycle()
    lifecycle.register(snapshot())
    lifecycle.register(snapshot(2, "sha256:" + "b" * 64))
    with pytest.raises(StaleReviewSnapshotError, match="stale"):
        lifecycle.decide("snapshot-1", "sha256:" + "a" * 64, "confirm", "Evidence holds")


def test_domain_steward_cannot_retrieve_mcn_or_diagnostics():
    projected = project_evidence({"snapshotId": "snapshot-1", "snapshotHash": "sha256:" + "a" * 64, "sectionId": "section-1", "mcn": "secret", "technicalDiagnostics": ["lint"], "evidenceProjection": [{"witness": "text"}]}, "domain_steward")
    assert "mcn" not in projected
    assert "technicalDiagnostics" not in projected