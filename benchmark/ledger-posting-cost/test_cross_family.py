# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""The cross-family benchmark's own tests (ADR-A124): it passes on a right history at small sizes, fails on a wrong one, does not fail on time, and leaves no store behind."""

from __future__ import annotations

import itertools
import json
import os

import pytest

import check
import cross_family as cf

SMALL = 2_000
SCHEDULE = ((0, 500), (2_750, 100))


def test_cf1_position_and_close_arithmetic_follow_the_schedule():
    assert cf.position_to_period(SCHEDULE, 1) == (0, 0)
    assert cf.position_to_period(SCHEDULE, 500) == (0, 0)
    assert cf.position_to_period(SCHEDULE, 501) == (0, 1)
    assert cf.position_to_period(SCHEDULE, 2_750) == (0, 5)  # the cut period of the old family
    assert cf.position_to_period(SCHEDULE, 2_751) == (1, 0)
    assert cf.position_to_period(SCHEDULE, 2_851) == (1, 1)
    assert [cf.latest_close(SCHEDULE, p) for p in (0, 499, 500, 2_749, 2_750, 2_800, 2_850, 2_999)] == [-1, -1, 500, 2_500, 2_500, 2_500, 2_850, 2_950]
    assert cf.closes(SCHEDULE, 3_000) == [500, 1_000, 1_500, 2_000, 2_500, 2_850, 2_950]


def test_cf2_a_single_family_schedule_closes_where_check_closes():
    one = ((0, 20),)
    assert [cf.latest_close(one, p) for p in range(0, 90, 7)] == [(p // 20) * 20 if p >= 20 else -1 for p in range(0, 90, 7)]
    assert cf.closes(one, 100) == [20, 40, 60, 80, 100]


def test_cf3_the_graph_name_carries_the_family():
    layer = check.build_tree()[2].iri
    assert cf.graph_name(SCHEDULE, layer, 2_750).value == f"urn:graph:f0:{layer.value.rsplit(':', 1)[1]}:5"
    assert cf.graph_name(SCHEDULE, layer, 2_751).value == f"urn:graph:f1:{layer.value.rsplit(':', 1)[1]}:0"


@pytest.mark.parametrize("scenario,old,new", cf.SCENARIOS)
def test_cf4_every_account_reads_the_models_balance_and_the_cross_read_names_two_families(scenario, old, new):
    rows = cf.measure(scenario, old, new, SMALL)
    by_case = {r.case: r for r in rows}
    assert by_case["cross"].families == 2
    assert by_case["control, coarse family, same width"].families == 1 and by_case["control, fine family"].families == 1
    whole = by_case["unpartitioned fold of the whole history"]
    assert all(r.folded <= whole.folded for r in rows)


def test_cf5_the_stored_count_follows_the_arithmetic():
    structure = check.structure_triples(check.build_tree())
    assert cf.expected_stored(3_000, SCHEDULE) == structure + 8 * 3_000 + 112 * 7 * 4


def test_cf6_a_balance_that_is_off_by_one_fails_the_run(monkeypatch):
    real = cf.read
    monkeypatch.setattr(cf, "read", lambda *a: (lambda b, f, g: (b + 1, f, g))(*real(*a)))
    with pytest.raises(check.WrongResult, match="the model gives"):
        cf.measure("refining", 500, 100, SMALL)


def test_cf7_a_wrong_stored_count_fails_the_run(monkeypatch):
    monkeypatch.setattr(cf, "expected_stored", lambda count, schedule: 0)
    with pytest.raises(check.WrongResult, match="stored"):
        cf.measure("refining", 500, 100, SMALL)


def test_cf8_a_read_that_folds_the_wrong_number_of_postings_fails_the_run(monkeypatch):
    real = cf.read
    monkeypatch.setattr(cf, "read", lambda *a: (lambda b, f, g: (b, f + 1, g))(*real(*a)))
    with pytest.raises(check.WrongResult, match="the range holds"):
        cf.measure("refining", 500, 100, SMALL)


def test_cf9_the_run_does_not_fail_on_time(monkeypatch):
    ticks = itertools.count(0, 10**6)
    monkeypatch.setattr(cf.time, "perf_counter", lambda: next(ticks))
    rows = cf.run((SMALL,))
    assert rows and all(r.read_ms >= 0 for r in rows)


def test_cf10_the_store_is_removed_when_the_run_ends_and_when_it_fails(tmp_path, monkeypatch):
    cf.measure("refining", 500, 100, SMALL, directory=str(tmp_path))
    assert not os.listdir(tmp_path)
    monkeypatch.setattr(cf, "expected_stored", lambda count, schedule: 0)
    with pytest.raises(check.WrongResult):
        cf.measure("refining", 500, 100, SMALL, directory=str(tmp_path))
    assert not os.listdir(tmp_path)


def test_cf11_the_report_is_written_where_asked(tmp_path):
    cf.write_report(cf.run((SMALL,)), tmp_path)
    data = json.loads((tmp_path / "cross_family.json").read_text(encoding="utf-8"))
    assert {r["scenario"] for r in data["rows"]} == {name for name, _, _ in cf.SCENARIOS}
    assert (tmp_path / "cross_family.md").read_text(encoding="utf-8").startswith("# Ledger cross-family read")
