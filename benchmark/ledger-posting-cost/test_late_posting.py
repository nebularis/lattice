# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""The late-posting benchmark's own tests (ADR-A124): it passes on a right history at small sizes, fails on a wrong one, does not fail on time, never emits a forward-dated posting, and leaves no store behind."""

from __future__ import annotations

import itertools
import json
import os

import pytest

import check
import late_posting as lp

SMALL = 2_000
RATE, REACH = 0.05, 2


def test_lp1_a_rate_of_zero_takes_effect_where_it_is_recorded():
    assert lp.effective_positions(SMALL, 0.0, 0) == list(range(1, SMALL + 1))
    assert lp.effective_positions(SMALL, 0.2, 0) == list(range(1, SMALL + 1))  # no reach, no late posting


def test_lp2_the_generator_never_emits_a_forward_dated_posting():
    for rate, reach in itertools.product((0.0, 0.01, 0.05, 0.2, 1.0), (0, 1, 10, 40, 10_000)):
        effective = lp.effective_positions(SMALL, rate, reach)
        assert all(1 <= x <= e for e, x in enumerate(effective, start=1))


def test_lp3_a_forward_dated_posting_fails_the_bound():
    lp.assert_never_forward([1, 2, 3])
    with pytest.raises(check.WrongResult, match="takes effect at 4"):
        lp.assert_never_forward([1, 4, 3])
    with pytest.raises(check.WrongResult, match="takes effect at 0"):
        lp.assert_never_forward([1, 2, 0])


def test_lp4_the_effective_position_arithmetic_follows_rate_and_reach():
    reach = REACH * lp.EVERY
    effective = lp.effective_positions(SMALL, RATE, reach)
    late = [(e, x) for e, x in enumerate(effective, start=1) if x != e]
    assert 0.5 * RATE * SMALL < len(late) < 1.5 * RATE * SMALL
    assert all(1 <= e - x <= reach for e, x in late)
    assert effective[0] == 1
    low = {e for e, x in enumerate(lp.effective_positions(SMALL, 0.01, reach), start=1) if x != e}
    high = {e for e, x in enumerate(lp.effective_positions(SMALL, 0.20, reach), start=1) if x != e}
    assert low < high  # the late events at a lower rate are among those at a higher one


def test_lp5_the_stored_count_follows_the_arithmetic():
    structure = check.structure_triples(check.build_tree())
    assert lp.expected_stored(3_000) == structure + 9 * 3_000 + 112 * 6 * 4


def test_lp6_a_late_posting_moves_the_effective_balance_and_not_the_recorded_one():
    accounts = check.build_tree()
    stream = check.events(SMALL, accounts)
    effective = lp.effective_positions(SMALL, 0.2, 3 * lp.EVERY)
    recorded = list(range(1, SMALL + 1))
    point = 900
    assert lp.balances_as_of(accounts, stream, effective, point) != lp.balances_as_of(accounts, stream, recorded, point)
    assert lp.balances_as_of(accounts, stream, recorded, point) == lp.balances_as_of(accounts, stream, recorded, point)
    assert lp.balances_as_of(accounts, stream, list(range(1, SMALL + 1)), SMALL) == lp.balances_as_of(accounts, stream, effective, SMALL)  # every posting is effective by the end


def test_lp7_every_account_reads_the_models_balance_and_the_folds_follow_the_reach():
    rows = lp.measure(SMALL, RATE, REACH)
    assert {r.read for r in rows} == set(lp.READS)
    for age in ("recent", "mid", "old"):
        by = {r.read: r for r in rows if r.age == age}
        uncapped, capped = by["as-of-effective, no reach cap"], by["as-of-effective, declared reach cap"]
        assert capped.periods <= uncapped.periods and capped.folded <= uncapped.folded
        assert uncapped.folded <= by["unpartitioned fold on effective"].folded
        assert by["as-of-recorded"].stragglers == 0 and uncapped.stragglers >= capped.stragglers
    assert all(r.late > 0 for r in rows)


def test_lp8_the_periods_folded_run_from_the_checkpoint_to_the_end_without_a_cap():
    rows = lp.measure(SMALL, RATE, REACH)
    old = {r.read: r for r in rows if r.age == "old"}["as-of-effective, no reach cap"]
    assert old.after == -1 and old.periods == (SMALL - 1) // lp.EVERY + 1  # no close before the point, so every period
    recent = {r.read: r for r in rows if r.age == "recent"}["as-of-effective, no reach cap"]
    assert recent.after == 1_500 and recent.periods == 1


def test_lp9_a_reach_cap_shorter_than_the_reach_misses_postings_and_fails(monkeypatch):
    real = lp.read_effective
    monkeypatch.setattr(lp, "read_effective", lambda store, account, point, events, cap: real(store, account, point, events, None if cap is None else 0))
    with pytest.raises(check.WrongResult, match="the model gives"):
        lp.measure(SMALL, 0.2, 3)


def test_lp10_a_balance_that_is_off_by_one_fails_the_run(monkeypatch):
    real = lp.read_effective
    monkeypatch.setattr(lp, "read_effective", lambda *a: (lambda b, f, g, p: (b + 1, f, g, p))(*real(*a)))
    with pytest.raises(check.WrongResult, match="the model gives"):
        lp.measure(SMALL, RATE, REACH)


def test_lp11_a_read_that_folds_the_wrong_number_of_postings_fails_the_run(monkeypatch):
    real = lp.read_effective
    monkeypatch.setattr(lp, "read_effective", lambda *a: (lambda b, f, g, p: (b, f + 1, g, p))(*real(*a)))
    with pytest.raises(check.WrongResult, match="the range holds"):
        lp.measure(SMALL, RATE, REACH)


def test_lp12_a_wrong_stored_count_fails_the_run(monkeypatch):
    monkeypatch.setattr(lp, "expected_stored", lambda count: 0)
    with pytest.raises(check.WrongResult, match="stored"):
        lp.measure(SMALL, RATE, REACH)


def test_lp13_the_run_does_not_fail_on_time(monkeypatch):
    ticks = itertools.count(0, 10**6)
    monkeypatch.setattr(lp.time, "perf_counter", lambda: next(ticks))
    monkeypatch.setattr(lp, "RATES", (0.0, 0.05))
    monkeypatch.setattr(lp, "REACHES", (1,))
    rows = lp.run((SMALL,))
    assert rows and all(r.read_ms >= 0 for r in rows)


def test_lp14_the_store_is_removed_when_the_run_ends_and_when_it_fails(tmp_path, monkeypatch):
    lp.measure(SMALL, RATE, REACH, directory=str(tmp_path))
    assert not os.listdir(tmp_path)
    monkeypatch.setattr(lp, "expected_stored", lambda count: 0)
    with pytest.raises(check.WrongResult):
        lp.measure(SMALL, RATE, REACH, directory=str(tmp_path))
    assert not os.listdir(tmp_path)


def test_lp15_the_report_is_written_where_asked(tmp_path, monkeypatch):
    monkeypatch.setattr(lp, "RATES", (0.0, 0.05))
    monkeypatch.setattr(lp, "REACHES", (1,))
    lp.write_report(lp.run((SMALL,)), tmp_path)
    data = json.loads((tmp_path / "late_posting.json").read_text(encoding="utf-8"))
    assert {r["rate"] for r in data["rows"]} == {0.0, 0.05}
    assert (tmp_path / "late_posting.md").read_text(encoding="utf-8").startswith("# Ledger as-of-effective read")
