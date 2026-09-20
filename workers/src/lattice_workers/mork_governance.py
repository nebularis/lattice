"""Replayable MORK queue, calibration, and named-axiom governance rules."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


class CalibrationRequiredError(PermissionError):
    """Raised when a bulk action lacks a passing matching calibration gate."""


@dataclass(frozen=True)
class QueueEntry:
    entry_id: str
    snapshot_id: str
    pack_id: str
    profile_id: str
    model_id: str
    yield_score: float

    @property
    def ordering_key(self) -> str:
        return f"{1 - self.yield_score:0.12f}|{self.pack_id}|{self.profile_id}|{self.model_id}|{self.entry_id}"


@dataclass(frozen=True)
class CalibrationGate:
    pack_id: str
    profile_id: str
    model_id: str
    sample_size: int
    precision: float
    minimum_precision: float

    @property
    def passed(self) -> bool:
        return self.sample_size > 0 and self.precision >= self.minimum_precision


def order_queue(entries: Iterable[QueueEntry]) -> list[QueueEntry]:
    return sorted(entries, key=lambda entry: entry.ordering_key)


def require_bulk_gate(gates: Iterable[CalibrationGate], pack_id: str, profile_id: str, model_id: str) -> CalibrationGate:
    for gate in gates:
        if (gate.pack_id, gate.profile_id, gate.model_id) == (pack_id, profile_id, model_id) and gate.passed:
            return gate
    raise CalibrationRequiredError("bulk confirmation requires a passing calibration gate for pack, profile, and model")


def reopen_approvals(named_axiom: str, approval_ids: Iterable[str]) -> list[dict[str, str]]:
    if not named_axiom or not list(approval_ids):
        raise ValueError("ontology minting requires a named axiom and affected approvals")
    return [{"approvalId": approval_id, "state": "reopened", "reason": named_axiom} for approval_id in approval_ids]


def open_retrospective_challenge(challenge_id: str, decision_id: str, snapshot_hash: str, reason: str) -> dict[str, str]:
    if not challenge_id or not decision_id or not snapshot_hash.startswith("sha256:") or not reason.strip():
        raise ValueError("retrospective challenge requires immutable decision and snapshot identity")
    return {"challengeId": challenge_id, "decisionId": decision_id, "snapshotHash": snapshot_hash, "state": "open", "reason": reason}