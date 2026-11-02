# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""The check's own tests (ADR-A124): the workload is what it says, the checks catch a wrong result, a right result passes on every engine, the composite family and the edge cases are built as stated, and none of it fails on time."""

from __future__ import annotations

import re

import pytest

import check
from check import build_run, sized_states


@pytest.fixture(scope="module")
def named():
    return check.named_family()


@pytest.fixture(scope="module")
def composite():
    return check.composite_family()


@pytest.fixture(scope="module", params=check.FAMILIES)
def family(request, named, composite):
    return {"named-graph": named, "composite": composite}[request.param]


def test_bench_t1_the_workload_keeps_half_and_changes_half_and_the_payload_is_m_triples():
    m = 20
    assert len(check.state(m, 2)) == m
    kept = check.state(m, 2) & check.state(m, 3)
    assert len(kept) == m // 2
    assert check.changed(m, 3) == check.state(m, 3) - kept
    assert check.changed(m, 2).isdisjoint(check.changed(m, 3))


def test_bench_t2_the_candidates_are_derived_from_the_rendered_replace(named):
    texts = named.texts
    r0, r1, r2 = texts["R0"], texts["R1-candidate"], texts["R2-candidate"]
    assert r0.count("OPTIONAL { GRAPH $g { ?s ?p ?o } }") == 1
    assert r1.count(" ;\n") == 1 and r1.count("DELETE {") == 2 and r1.count("OPTIONAL { GRAPH $g { ?s ?p ?o } }") == 1
    assert "OPTIONAL { GRAPH $g" not in r2 and "UNION" in r2
    assert "GRAPH ?w {" in r2 and "GRAPH ?metaW {" in r2 and "GRAPH ?txnW {" in r2 and "GRAPH $g { {{{payloadTriples}}} }" not in r2


def test_bench_t3_a_built_run_is_whole(family):
    run = build_run(family, "R0", sized_states(family, 20, 2))
    for text in (run.create, *(s.text for s in run.steps)):
        assert "$" not in text and "{{{" not in text
    assert [s.seq for s in run.steps] == [2, 3]
    states = sized_states(family, 20, 2)
    assert run.steps[0].expect_add == states[1] - states[0] and run.steps[0].expect_del == states[0] - states[1]
    assert build_run(family, "R0-nodelta", sized_states(family, 20, 1)).steps[0].expect_add == set()


@pytest.mark.parametrize("engine_class", check.available_engines(), ids=lambda c: c.name)
@pytest.mark.parametrize("form", ["R0", "R0-nodelta", "R1-candidate", "R3-delta"])
def test_bench_t4_a_replace_leaves_exactly_what_it_should(engine_class, form, family):
    check.run_form(engine_class, family, form, 20, repeats=2)


def test_bench_t5_the_one_operation_candidates_pass_on_a_snapshot_engine(family):
    from lattice_testing_oxigraph import SNAPSHOT_UPDATES

    if not SNAPSHOT_UPDATES:
        pytest.skip("this Oxigraph applies an update one solution at a time (P1)")
    for form in ("R2-candidate", "R2-values-candidate"):
        if form in family.forms:
            check.run_form(check.OxigraphEngine, family, form, 20, repeats=2)


@pytest.mark.parametrize("form", ["R0", "R3-delta"])
def test_bench_t6_a_replace_that_does_nothing_fails_the_check(family, form):
    class DoesNothing(check.RdflibEngine):
        name = "does-nothing"

        def update(self, text):
            if "DELETE {" not in text:  # the create runs, the replace does nothing
                super().update(text)

    with pytest.raises(check.WrongResult):
        check.run_form(DoesNothing, family, form, 20, repeats=1)


def test_bench_t7_a_lost_kept_triple_is_named_in_the_reason(named):
    run = build_run(named, "R0", sized_states(named, 20, 1))
    engine = check.start(check.RdflibEngine, run)
    step = run.steps[0]
    before = engine.outside(step.graphs, step.log)
    engine.update(step.text)
    assert check.verify(engine, step, before) == []
    from rdflib import Literal, URIRef

    engine.ds.graph(URIRef(step.root_graph)).remove((URIRef(f"{check.SUBJECT}0"), URIRef(check.PREDICATE), Literal("k")))
    assert "1 of them kept triples (first lost urn:x:s/0)" in check.verify(engine, step, before)[0]


def test_bench_t8_a_change_outside_the_replace_is_caught(named):
    run = build_run(named, "R0", sized_states(named, 20, 1))
    engine = check.start(check.RdflibEngine, run)
    step = run.steps[0]
    before = engine.outside(step.graphs, step.log)
    engine.update(step.text)
    engine.update("INSERT DATA { GRAPH <urn:g:other> { <urn:a> <urn:b> <urn:c> } }")
    assert any("outside" in issue for issue in check.verify(engine, step, before))


def test_bench_t9_the_emitted_operations_pass_their_own_checks_on_rdflib(family):
    doc = check.emit_family(family, sizes=(20,), repeats=2)
    run = doc["runs"]["20"]
    engine = check.RdflibEngine()
    if doc["preload"]:
        engine.update(doc["preload"])
    engine.update(run["create"])
    for step in run["forms"]["R0"]:
        before = int(list(engine.ds.query(step["outsideQuery"]))[0][0])
        engine.update(step["text"])
        for item in step["counts"]:
            assert int(list(engine.ds.query(item["query"]))[0][0]) == item["expect"], item["query"]
        assert int(list(engine.ds.query(step["outsideQuery"]))[0][0]) == before
        for key, graph in (("root", "rootGraph"), ("add", "addGraph"), ("del", "delGraph")):
            rows = {f'<{s}> <{p}> {check.term(o)} .' for s, p, o in engine.triples(step[graph])}
            assert rows == set(step["expect"][key])


def test_bench_t10_the_rows_slots_are_filled_with_the_triples_the_slot_form_uses(family):
    rows_text = family.texts["R2-values-candidate"]
    assert all(f"{{{{{{{slot}}}}}}}" in rows_text for slot in ("payloadTriples", "assertTriples", "retractTriples"))
    assert "OPTIONAL {" not in rows_text.split("WHERE {")[1].split("BIND(NOW()")[1]
    states = sized_states(family, 20, 1)
    values = build_run(family, "R2-values-candidate", states).steps[0]
    slots = build_run(family, "R0", states).steps[0]
    assert "{{{" not in values.text
    for block, expected in (("newS newP newO", set(states[1])), ("addS addP addO", slots.expect_add), ("delS delP delO", slots.expect_del)):
        names = " ".join(f"\\?{v}" for v in block.split())
        body = re.search(r"VALUES \(" + names + r"\) \{(.*?)\} \}", values.text).group(1)
        found = set(re.findall(r'\(<([^>]+)> <([^>]+)> (?:<([^>]+)>|"([^"]*)")\)', body))
        assert {(s, p, i or lit) for s, p, i, lit in found} == expected
        assert body.count("(<") == len(expected)
    assert check.rows(states[1]) in values.text


def test_bench_t11_the_composite_sweep_is_grabbed_from_the_rendered_text(composite):
    r0 = composite.texts["R0"]
    assert composite.graph == "urn:g:projects" and composite.sweep in re.sub(r"\s+", " ", r0).replace("{ $root", "{ $root")
    assert composite.sweep in re.sub(r"\s+", " ", composite.texts["R2-values-candidate"])
    assert "OPTIONAL" not in composite.texts["R2-values-candidate"].split("BIND(NOW() AS ?now)")[1]
    assert composite.texts["R1-candidate"].count(" ;\n") == 1 and "?logGraph2" in composite.texts["R2-values-candidate"]
    assert "R2-candidate" not in composite.texts and "R2-candidate" not in composite.forms


def test_bench_t12_the_bystander_is_outside_the_aggregate_and_untouched(composite):
    state = composite.state(50, 2)
    assert len(state) == 50
    assert not composite.bystander & state
    subjects = {s for s, _, _ in state}
    assert not {s for s, _, _ in composite.bystander} & subjects
    run = build_run(composite, "R0", sized_states(composite, 20, 1))
    assert composite.bystander <= run.steps[0].expect_root
    engine = check.start(check.RdflibEngine, run)
    assert composite.bystander <= engine.triples(composite.graph)
    engine.update(run.steps[0].text)
    assert composite.bystander <= engine.triples(composite.graph)
    engine.ds.graph(__import__("rdflib").URIRef(composite.graph)).remove((__import__("rdflib").URIRef(next(iter(composite.bystander))[0]), None, None))
    assert any("bystander" in issue for issue in check.verify(engine, run.steps[0], 0))


def test_bench_t13_the_five_edge_cases_have_the_stated_deltas(family):
    expected = {"E1": (50, 0), "E2": (0, 50), "E3": (0, 0), "E4": (0, 0), "E5": (50, 0)}
    for case, _ in family.edge_cases:
        step = build_run(family, "R0", check.edge_states(family, case)).steps[0]
        assert (len(step.expect_add), len(step.expect_del)) == expected[case], case
        assert step.seq == 2
    assert ("E5" in dict(family.edge_cases)) == (family.name == "composite")
    assert "VALUES (?newS ?newP ?newO) {  }" in build_run(family, "R2-values-candidate", check.edge_states(family, "E2")).steps[0].text


@pytest.mark.parametrize("engine_class", check.available_engines(), ids=lambda c: c.name)
def test_bench_t14_a_generated_replace_passes_the_edge_cases_it_can_or_reports_why_not(engine_class, family):
    for case, _ in family.edge_cases:
        cell = check.edge_cell(engine_class, family, case, "R0", True)
        assert cell.startswith(("pass", "wrong:", "error:")), (case, cell)


def test_bench_t15_the_bare_sweep_counts_the_aggregate(composite):
    engine = check.start(check.OxigraphEngine if check.available_engines()[0].name == "oxigraph" else check.RdflibEngine, build_run(composite, "R0", sized_states(composite, 50, 1)))
    assert engine.count(composite.sweep_query(True)) == 50


def test_bench_t16_the_delta_form_changes_one_triple_per_revision_sweeps_nothing_and_needs_no_snapshot(family):
    assert "R3-delta" in family.forms and "R3-delta" in check.GENERATED and "R3-delta" not in check.CANDIDATES + check.NEEDS_SNAPSHOT
    states = sized_states(family, 20, 2, "R3-delta")
    assert states[0] == family.state(20, 1) and all(len(s) == 20 for s in states)
    assert all(len(a - b) == 1 == len(b - a) for a, b in zip(states[1:], states))
    run = build_run(family, "R3-delta", states)
    assert [(len(s.expect_add), len(s.expect_del)) for s in run.steps] == [(1, 1), (1, 1)]
    text = family.texts["R3-delta"]
    assert "payloadTriples" not in text and "UNION" not in text and "?s ?p ?o" not in text
    assert all("{{{" not in s.text and "$" not in s.text for s in run.steps)

