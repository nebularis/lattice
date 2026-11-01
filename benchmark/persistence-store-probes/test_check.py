# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""The check's own tests (ADR-A124): it passes when every form counts the graph, fails on a wrong count, and never fails on time."""

from __future__ import annotations

import json

import pytest

import check


@pytest.mark.parametrize("engine_class", check.available_engines(), ids=lambda c: c.name)
def test_bs1_every_form_counts_the_graph_at_the_smallest_size(engine_class):
    report = check.run(quick=True, engine_classes=[engine_class])
    assert {m.form for m in report.measurements} == set(check.FORMS) and all(m.ratio > 0 for m in report.measurements)


def test_bs2_a_form_that_counts_another_graph_fails_the_check():
    wrong = {"wrong": check.COUNT + "GRAPH <urn:g:1> { ?s ?p ?o } FILTER(?o > 10) }"}
    with pytest.raises(check.WrongResult, match="returned"):
        check.run(quick=True, engine_classes=[check.RdflibEngine], forms=wrong)


def test_bs3_an_engine_that_counts_one_too_many_fails_the_check():
    class OffByOne(check.RdflibEngine):
        def count(self, query):
            return super().count(query) + 1

    with pytest.raises(check.WrongResult):
        check.run(quick=True, engine_classes=[OffByOne])


def test_bs4_the_check_does_not_fail_on_time(monkeypatch):
    ticks = iter(range(0, 10**9, 10**6))

    class SlowClock:
        @staticmethod
        def perf_counter():
            return next(ticks)

    monkeypatch.setattr(check, "time", SlowClock)
    report = check.run(quick=True, engine_classes=[check.RdflibEngine])
    assert report.measurements and all(m.many_seconds >= 10**6 for m in report.measurements)


def test_bs5_the_report_names_its_run_and_is_written_where_asked(tmp_path):
    report = check.run(quick=True, engine_classes=[check.RdflibEngine])
    check.write(report, tmp_path)
    text = (tmp_path / "report.md").read_text()
    assert text.startswith("Run: ") and "rdflib" in text.splitlines()[0] and "bind-optional" in text
    assert json.loads((tmp_path / "report.json").read_text())["run"] == report.run_record


def test_bs6_an_absent_jena_is_a_noted_skip_and_not_a_failure():
    notes: list[str] = []
    engines = check.available_engines(notes)
    assert check.RdflibEngine in engines and (check.JenaEngine in engines or any("jena skipped" in n for n in notes))
