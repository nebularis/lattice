from datetime import datetime, timezone

import pytest

from lattice_workers.mork_governance_ledger import GovernanceLedger, GovernanceLedgerEntry, template_exception


def test_governance_ledger_replays_stably_by_time_and_entry_id():
    ledger = GovernanceLedger()
    at = datetime(2026, 9, 20, tzinfo=timezone.utc)
    ledger.append(GovernanceLedgerEntry("b", "bulk_blocked", "entry-1", "correlation", "gate:failed", at))
    ledger.append(GovernanceLedgerEntry("a", "calibration_failed", "entry-1", "correlation", "gate:failed", at))
    assert [entry.entry_id for entry in ledger.replay()] == ["a", "b"]


def test_template_exception_always_requires_engineering_review():
    assert template_exception("exception-1", "template-1", "snapshot-1", "unusual fiscal calendar")["engineeringReviewRequired"] is True


def test_ledger_rejects_duplicate_entry_identity():
    ledger = GovernanceLedger()
    entry = GovernanceLedgerEntry("entry-1", "challenge_opened", "challenge-1", "correlation", "challenge:1", datetime.now(timezone.utc))
    ledger.append(entry)
    with pytest.raises(ValueError, match="already exists"):
        ledger.append(entry)