"""Append-only governance ledger projection for MORK queue and calibration actions."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class GovernanceLedgerEntry:
    entry_id: str
    kind: str
    subject_id: str
    correlation_id: str
    evidence_reference: str
    occurred_at: datetime


class GovernanceLedger:
    def __init__(self) -> None:
        self._entries: list[GovernanceLedgerEntry] = []

    def append(self, entry: GovernanceLedgerEntry) -> GovernanceLedgerEntry:
        if any(existing.entry_id == entry.entry_id for existing in self._entries):
            raise ValueError("governance ledger entry ID already exists")
        self._entries.append(entry)
        return entry

    def replay(self) -> list[GovernanceLedgerEntry]:
        return sorted(self._entries, key=lambda entry: (entry.occurred_at, entry.entry_id))


def template_exception(exception_id: str, template_id: str, snapshot_id: str, reason: str) -> dict[str, str | bool]:
    if not exception_id or not template_id or not snapshot_id or not reason.strip():
        raise ValueError("template exception requires template, snapshot, and reason")
    return {"exceptionId": exception_id, "templateId": template_id, "snapshotId": snapshot_id, "reason": reason, "engineeringReviewRequired": True}


def utc_now() -> datetime:
    return datetime.now(timezone.utc)