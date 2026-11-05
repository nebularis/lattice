# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""The check's own tests (ADR-A124): it passes when the forms agree, fails on a wrong result, and never fails on time."""

from __future__ import annotations

import json
from dataclasses import replace

import pytest

import check


@pytest.mark.parametrize("engine_class", check.available_engines(), ids=lambda c: c.name)
@pytest.mark.parametrize("experiment", check.EXPERIMENTS, ids=lambda e: e.key)
def test_bq1_the_two_forms_return_the_same_solutions_at_the_smallest_size(engine_class, experiment):
    measurement, counts = check.run_experiment(experiment, experiment.sizes[0], engine_class)
    assert len(counts) == measurement.focus_nodes and measurement.naive_seconds > 0 and measurement.improved_seconds > 0


def test_bq2_an_improved_form_that_returns_other_solutions_fails_the_check():
    wrong = replace(check.EXPERIMENTS[0], improved=check.COUNT + "{ $this ex:inScheme ?s . $this ex:nothing ?z }")
    with pytest.raises(check.WrongResult, match="E1"):
        check.run_experiment(wrong, 16, check.RdflibEngine)


def test_bq3_an_engine_that_disagrees_with_the_others_fails_the_check():
    class OffByOne(check.RdflibEngine):
        name = "off-by-one"

        def run(self, prepared, focus):
            return super().run(prepared, focus) + 1

    with pytest.raises(check.WrongResult, match="engines disagree"):
        check.run(quick=True, engine_classes=[check.RdflibEngine, OffByOne])


def test_bq4_the_check_does_not_fail_on_time(monkeypatch):
    ticks = iter(range(0, 10**9, 10**6))

    class SlowClock:
        @staticmethod
        def perf_counter():
            return next(ticks)  # every reading is a million seconds after the last

    monkeypatch.setattr(check, "time", SlowClock)
    report = check.run(quick=True, engine_classes=[check.RdflibEngine])
    assert report.measurements and all(m.naive_seconds >= 10**6 for m in report.measurements)


def test_bq5_the_growth_exponent_of_a_quadratic_series_is_two():
    series = [check.Measurement("E", "e", n, 10, 1e-6 * n * n * 10, 1e-6 * n * 10) for n in (100, 200, 400)]
    report = check.Report(measurements=series)
    # the time per focus node is 1e-6 * size^2 for the naive form and 1e-6 * size for the improved one
    assert report.growth("E", "e", "naive") == pytest.approx(2.0, abs=1e-6)
    assert report.growth("E", "e", "improved") == pytest.approx(1.0, abs=1e-6)
    assert check.Report(measurements=series[:1]).growth("E", "e", "naive") is None


def test_bq6_the_report_names_its_run_and_is_written_where_asked(tmp_path):
    report = check.run(quick=True, engine_classes=[check.RdflibEngine])
    check.write(report, tmp_path)
    text = (tmp_path / "report.md").read_text()
    assert text.startswith("Run: ") and "rdflib" in text.splitlines()[0] and "E5" in text
    assert json.loads((tmp_path / "report.json").read_text())["run"] == report.run_record


def test_bq7_the_ways_of_running_one_query_agree():
    seconds = check.run_parse_cost([check.RdflibEngine])
    assert set(seconds) == {"rdflib from text", "rdflib prepared"} and all(v > 0 for v in seconds.values())
