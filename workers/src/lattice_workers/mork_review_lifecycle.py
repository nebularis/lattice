"""Stale-safe in-memory lifecycle for immutable MORK review snapshots."""

from __future__ import annotations

from dataclasses import dataclass

from .mork_review import Decision, ReviewEffect, decision_effect


class StaleReviewSnapshotError(ValueError):
    """Raised when a decision is made against a superseded snapshot hash."""


@dataclass(frozen=True)
class ReviewSnapshot:
    snapshot_id: str
    snapshot_hash: str
    tenant_id: str
    project_id: str
    section_id: str
    version: int


@dataclass(frozen=True)
class RecordedDecision:
    snapshot_id: str
    snapshot_hash: str
    decision: Decision
    effect: ReviewEffect
    rationale: str


class ReviewLifecycle:
    def __init__(self) -> None:
        self._snapshots: dict[str, ReviewSnapshot] = {}
        self._decisions: list[RecordedDecision] = []

    def register(self, snapshot: ReviewSnapshot) -> ReviewSnapshot:
        current = self._snapshots.get(snapshot.snapshot_id)
        if current and snapshot.version <= current.version:
            raise StaleReviewSnapshotError("review snapshot version is not newer")
        self._snapshots[snapshot.snapshot_id] = snapshot
        return snapshot

    def decide(self, snapshot_id: str, snapshot_hash: str, decision: Decision, rationale: str) -> RecordedDecision:
        current = self._snapshots.get(snapshot_id)
        if current is None or current.snapshot_hash != snapshot_hash:
            raise StaleReviewSnapshotError("review snapshot is stale or unavailable")
        if not rationale.strip():
            raise ValueError("review decision requires rationale")
        recorded = RecordedDecision(snapshot_id, snapshot_hash, decision, decision_effect(decision), rationale)
        self._decisions.append(recorded)
        return recorded