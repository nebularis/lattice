import pytest

from lattice_workers.mork_governance import CalibrationGate, CalibrationRequiredError, QueueEntry, open_retrospective_challenge, order_queue, reopen_approvals, require_bulk_gate


def test_queue_ordering_is_replayable_with_stable_tie_breakers():
    entries = [QueueEntry("b", "s2", "pack", "profile", "model", 0.8), QueueEntry("a", "s1", "pack", "profile", "model", 0.8)]
    assert [entry.entry_id for entry in order_queue(entries)] == ["a", "b"]


def test_bulk_confirmation_requires_matching_calibration_dimension():
    gates = [CalibrationGate("pack", "profile", "model-a", 30, 0.9, 0.8)]
    with pytest.raises(CalibrationRequiredError):
        require_bulk_gate(gates, "pack", "profile", "model-b")


def test_named_axiom_reopens_each_affected_approval():
    reopened = reopen_approvals("https://example.test/axioms/new-class", ["approval-1", "approval-2"])
    assert all(item["state"] == "reopened" for item in reopened)


def test_retrospective_challenge_preserves_decision_identity():
    challenge = open_retrospective_challenge("challenge-1", "decision-1", "sha256:" + "a" * 64, "New evidence")
    assert challenge["state"] == "open"
    assert challenge["decisionId"] == "decision-1"