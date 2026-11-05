# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""The check's own tests (ADR-A124): it passes on a right history at small sizes, fails on a wrong one, and does not fail on time."""

from __future__ import annotations

import pytest

import check


@pytest.mark.parametrize("engine", check.available_engines())
@pytest.mark.parametrize("strategy", check.STRATEGIES)
def test_bench_t1_each_strategy_reads_the_models_members_and_stores_the_expected_count(engine, strategy):
    check.engines.CURRENT = engine
    try:
        for n in (1, 3):
            check.run_strategy(strategy, n)
    finally:
        check.engines.CURRENT = "rdflib"


def test_bench_t2_a_wrong_count_fails_the_check(monkeypatch):
    monkeypatch.setattr(check, "expected_stored", lambda strategy, n: (0, 0))
    with pytest.raises(check.WrongResult, match="stored"):
        check.run_strategy("delta", 3)


def test_bench_t3_a_members_query_that_ignores_drops_fails_the_check(monkeypatch):
    real = check._members_text
    monkeypatch.setattr(check, "_members_text", lambda: real().replace("pat:dropsMember ?member", "pat:dropsMember <urn:never>"))
    with pytest.raises(check.WrongResult, match="differ"):
        check.run_strategy("delta", 3)


def test_bench_t4_the_check_does_not_fail_on_time(monkeypatch):
    ticks = iter(range(0, 10_000_000, 1_000_000))
    monkeypatch.setattr(check.time, "perf_counter", lambda: next(ticks))
    report = check.run(max_versions=1, engine_names=["rdflib"])
    assert report.measurements and all(m.read_seconds >= 1_000_000 for m in report.measurements)


def test_bench_t5_the_arithmetic_of_the_stored_counts():
    assert check.expected_stored("full", 10) == (5030, 0)
    assert check.expected_stored("delta", 1) == (503, 0)
    assert check.expected_stored("delta", 17) == (503 + 14 * 5 + 504 + 5, 0)
    assert check.expected_stored("in-place", 100) == (500, 198)
