# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""The check's own tests (ADR-A124): it passes on a right result at small sizes, and fails on a wrong one, never on time."""

from __future__ import annotations

import pytest

import check


@pytest.fixture(scope="module")
def operation():
    return check.replace_operation()


@pytest.mark.parametrize("engine_class", check.available_engines(), ids=lambda c: c.name)
@pytest.mark.parametrize("size", [10, 100])
def test_bench_t1_a_replace_leaves_exactly_the_payload_at_small_sizes(engine_class, size, operation):
    check.run_once(engine_class, size, *operation)


def test_bench_t2_a_wrong_result_fails_the_check(operation):
    text, graphs = operation

    class DoesNothing(check.RdflibEngine):
        name = "does-nothing"

        def update(self, text, parameters):
            pass

    with pytest.raises(check.WrongResult):
        check.run_once(DoesNothing, 10, text, graphs)


def test_bench_t3_an_update_that_keeps_an_old_triple_fails_the_check(operation):
    text, graphs = operation

    class KeepsOne(check.RdflibEngine):
        name = "keeps-one"

        def update(self, text, parameters):
            super().update(text, parameters)
            self.add(graphs["data"], [(check.ROOT, check.EX + "name", "str", "Apollo")])

    with pytest.raises(check.WrongResult, match="data graph"):
        check.run_once(KeepsOne, 10, text, graphs)


def test_bench_t4_the_check_does_not_fail_on_time(operation, monkeypatch):
    ticks = iter(range(0, 10_000_000, 1_000_000))
    monkeypatch.setattr(check.time, "perf_counter", lambda: next(ticks))  # every update appears to take a million seconds
    report = check.run(max_size=10, engine_classes=[check.RdflibEngine])
    assert report.measurements and report.measurements[0].seconds >= 1_000_000


def test_bench_t5_the_growth_exponent_of_a_quadratic_series_is_two():
    report = check.Report([check.Measurement("e", n, 3 * n, n, 1e-6 * n * n, 1) for n in (100, 1000, 10000)])
    assert report.growth("e") == pytest.approx(2.0, abs=1e-6)
    assert check.Report([check.Measurement("e", 10, 30, 10, 1.0, 1)]).growth("e") is None


@pytest.mark.parametrize("engine_class", check.available_engines(), ids=lambda c: c.name)
def test_bench_t6_an_isolated_run_returns_its_timing_and_the_stored_count(engine_class, operation):
    kind, seconds, stored = check.run_isolated(engine_class, 10, *operation, memory_gb=8)
    assert (kind, stored) == ("ok", 8) and seconds > 0


def test_bench_t7_a_run_that_cannot_stay_under_its_memory_cap_is_recorded_and_is_not_a_wrong_result(operation):
    kind, reason, _ = check.run_isolated(check.RdflibEngine, 10, *operation, memory_gb=0.01)
    assert kind == "dnf" and ("out of memory" in reason or "0.01 GB" in reason)


def test_bench_t8_a_wrong_result_in_a_child_process_still_fails_the_check(operation, monkeypatch):
    monkeypatch.setattr(check, "run_isolated", lambda *a, **k: ("wrong", "the data graph holds 3 triples", None))
    with pytest.raises(check.WrongResult):
        check.run(max_size=10, engine_classes=[check.RdflibEngine], isolated=True)


def test_bench_t9_a_run_that_did_not_finish_is_in_the_report_and_not_in_the_fit(operation, monkeypatch, tmp_path):
    monkeypatch.setattr(check, "run_isolated", lambda *a, **k: ("dnf", "out of memory", None))
    report = check.run(max_size=100, engine_classes=[check.RdflibEngine], isolated=True)
    assert all(m.seconds is None and m.outcome.startswith("did not finish") for m in report.measurements)
    assert report.growth("rdflib") is None
    check.write_report(report, tmp_path)
    assert "did not finish: out of memory" in (tmp_path / "report.md").read_text(encoding="utf-8")
