# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""The check's own tests (ADR-A124): the workload is what it says, the checks catch a wrong result, a right result passes on every engine, and none of it fails on time."""

from __future__ import annotations

import pytest

import check
from check import build_run


@pytest.fixture(scope="module")
def texts():
    return check.templates()


def test_bench_t1_the_workload_keeps_half_and_changes_half_and_the_payload_is_m_triples():
    m = 20
    assert len(check.state(m, 2)) == m
    kept = check.state(m, 2) & check.state(m, 3)
    assert len(kept) == m // 2
    assert check.changed(m, 3) == check.state(m, 3) - kept
    assert check.changed(m, 2).isdisjoint(check.changed(m, 3))


def test_bench_t2_the_candidates_are_derived_from_the_rendered_replace(texts):
    r0, r1, r2 = texts["R0"], texts["R1-candidate"], texts["R2-candidate"]
    assert r0.count("OPTIONAL { GRAPH $g { ?s ?p ?o } }") == 1
    assert r1.count(" ;\n") == 1 and r1.count("DELETE {") == 2 and r1.count("OPTIONAL { GRAPH $g { ?s ?p ?o } }") == 1
    assert "OPTIONAL { GRAPH $g" not in r2 and "UNION" in r2
    assert "GRAPH ?w {" in r2 and "GRAPH ?metaW {" in r2 and "GRAPH ?txnW {" in r2 and "GRAPH $g { {{{payloadTriples}}} }" not in r2


def test_bench_t3_a_built_run_is_whole(texts):
    run = check.build_run(texts, "R0", 20, repeats=2)
    for text in (run.create, *(s.text for s in run.steps)):
        assert "$" not in text and "{{{" not in text
    assert [s.seq for s in run.steps] == [2, 3]
    assert run.steps[0].expect_add == check.changed(20, 2) and run.steps[0].expect_del == check.changed(20, 1)
    assert check.build_run(texts, "R0-nodelta", 20, repeats=1).steps[0].expect_add == set()


@pytest.mark.parametrize("engine_class", check.available_engines(), ids=lambda c: c.name)
@pytest.mark.parametrize("form", ["R0", "R0-nodelta", "R1-candidate"])
def test_bench_t4_a_replace_leaves_exactly_what_it_should(engine_class, form, texts):
    check.run_form(engine_class, texts, form, 20, repeats=2)


def test_bench_t5_the_one_operation_candidate_passes_on_a_snapshot_engine(texts):
    from lattice_testing_oxigraph import SNAPSHOT_UPDATES

    if not SNAPSHOT_UPDATES:
        pytest.skip("this Oxigraph applies an update one solution at a time (P1)")
    check.run_form(check.OxigraphEngine, texts, "R2-candidate", 20, repeats=2)


def test_bench_t6_a_replace_that_does_nothing_fails_the_check(texts):
    class DoesNothing(check.RdflibEngine):
        name = "does-nothing"

        def update(self, text):
            if "DELETE {" not in text:  # the create runs, the replace does nothing
                super().update(text)

    with pytest.raises(check.WrongResult):
        check.run_form(DoesNothing, texts, "R0", 20, repeats=1)


def test_bench_t7_a_lost_kept_triple_is_named_in_the_reason(texts):
    run = check.build_run(texts, "R0", 20, repeats=1)
    engine = check.RdflibEngine()
    engine.update(run.create)
    step = run.steps[0]
    before = engine.outside(step.graphs, check.LOG)
    engine.update(step.text)
    assert check.verify(engine, step, before) == []
    from rdflib import Literal, URIRef

    engine.ds.graph(URIRef(step.root_graph)).remove((URIRef(f"{check.SUBJECT}0"), URIRef(check.PREDICATE), Literal("k")))
    assert "1 of them kept triples (first lost urn:x:s/0)" in check.verify(engine, step, before)[0]


def test_bench_t8_a_change_outside_the_replace_is_caught(texts):
    run = check.build_run(texts, "R0", 20, repeats=1)
    engine = check.RdflibEngine()
    engine.update(run.create)
    step = run.steps[0]
    before = engine.outside(step.graphs, check.LOG)
    engine.update(step.text)
    engine.update("INSERT DATA { GRAPH <urn:g:other> { <urn:a> <urn:b> <urn:c> } }")
    assert any("outside" in issue for issue in check.verify(engine, step, before))


def test_bench_t9_the_emitted_operations_pass_their_own_checks_on_rdflib():
    doc = check.emit_operations(sizes=(20,), repeats=2)
    run = doc["runs"]["20"]
    engine = check.RdflibEngine()
    engine.update(run["create"])
    for step in run["forms"]["R0"]:
        before = int(list(engine.ds.query(step["outsideQuery"]))[0][0])
        engine.update(step["text"])
        for item in step["counts"]:
            assert int(list(engine.ds.query(item["query"]))[0][0]) == item["expect"], item["query"]
        assert int(list(engine.ds.query(step["outsideQuery"]))[0][0]) == before
        for key, graph in (("root", "rootGraph"), ("add", "addGraph"), ("del", "delGraph")):
            rows = {f'<{s}> <{p}> "{o}" .' for s, p, o in engine.triples(step[graph])}
            assert rows == set(step["expect"][key])


def test_bench_t10_the_values_rows_are_rendered_from_the_triples_the_slot_form_uses(texts):
    import re

    assert "{{{payloadTriples}}}" not in texts["R2-values-candidate"] and "OPTIONAL { GRAPH $g" not in texts["R2-values-candidate"]
    values = build_run(texts, "R2-values-candidate", 20, repeats=1).steps[0]
    slots = build_run(texts, "R0", 20, repeats=1).steps[0]
    for block, expected in (("ps pp po", slots.expect_root), ("as ap ao", slots.expect_add), ("ds dp do", slots.expect_del)):
        names = "".join(f"\\?{v} " for v in block.split()).strip()
        body = re.search(r"VALUES \(" + names + r"\) \{(.*?)\} \}", values.text).group(1)
        assert set(re.findall(r'\(<([^>]+)> <([^>]+)> "([^"]*)"\)', body)) == expected
        assert body.count("(<") == len(expected)
        assert check.rows(expected) in body or not expected
