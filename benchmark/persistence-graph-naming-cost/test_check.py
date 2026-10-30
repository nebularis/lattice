# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""The check's own tests (ADR-A124): it passes on a right result at small sizes, and fails on a wrong one, never on time."""

from __future__ import annotations

import pytest

import check


@pytest.fixture(scope="module")
def ops():
    return check.operations()


@pytest.mark.parametrize("engine_class", check.available_engines(), ids=lambda c: c.name)
@pytest.mark.parametrize("names", ["query", "caller"])
def test_bench_t1_a_replace_leaves_exactly_the_payload_among_ballast(engine_class, names, ops):
    check.run_replace(engine_class, names, 1_000, ops, repeats=2)


@pytest.mark.parametrize("engine_class", check.available_engines(), ids=lambda c: c.name)
def test_bench_t2_every_form_counts_what_it_should_over_a_few_graphs(engine_class):
    for where in check.FORMS.values():
        check.form_ratio(engine_class, where, graphs=5, triples=20)


def test_bench_t3_a_replace_that_does_nothing_fails_the_check(ops):
    class DoesNothing(check.RdflibEngine):
        name = "does-nothing"

        def update(self, text, parameters):
            pass

    with pytest.raises(check.WrongResult):
        check.run_replace(DoesNothing, "query", 100, ops, repeats=1)


def test_bench_t4_a_form_that_counts_wrongly_fails_the_check():
    class CountsOne(check.RdflibEngine):
        name = "counts-one"

        def select_count(self, where):
            return 1

    with pytest.raises(check.WrongResult):
        check.form_ratio(CountsOne, check.FORMS["constant BIND, one group"], graphs=3, triples=10)


def test_bench_t5_the_slope_is_read_from_the_smallest_and_largest_ballast():
    report = check.Report(replaces=[("e", "query", 0, 0.001), ("e", "query", 1_000_000, 0.701), ("e", "caller", 0, 0.001)])
    assert report.slope_ms_per_1000_quads("e", "query") == pytest.approx(0.7)
    assert report.slope_ms_per_1000_quads("e", "caller") is None


def test_bench_t6_the_emitted_operations_are_whole_and_pass_their_own_checks_on_rdflib():
    doc = check.emit_operations(repeats=2)
    assert "$" not in doc["steps"]["query"]["replaces"][0]["text"]
    assert "{{{" not in doc["steps"]["caller"]["create"]
    for names in ("query", "caller"):
        engine = check.RdflibEngine()
        step = doc["steps"][names]
        engine.ds.update(step["create"])
        for replace in step["replaces"]:
            engine.ds.update(replace["text"])
            for item in replace["checks"]:
                assert int(list(engine.ds.query(item["query"]))[0][0]) == item["expect"], (names, item["query"])
