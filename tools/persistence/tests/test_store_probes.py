# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""H2.4b: what each engine does, as tests (formal-methods track H, plan 4.2, probes P1 to P5). Validation Pack:
docs/developer/validation/FMH-H2-4b.md. Test IDs are H2.4b-Tn.

Each probe asserts what rdflib 7.6.0 and Oxigraph 0.5.11 do today. It decides nothing about which form to generate. If an
engine changes, the test fails and the table in the Validation Pack is updated, which is the point: H5's capability record
carries these answers with a probe each, and these are the probes. The engines differ on four of the five."""

from __future__ import annotations

import time

import pytest
from rdflib import Literal, URIRef

import engines

U = URIRef
TRIPLE = (U("urn:s"), U("urn:p"), U("urn:o"))
LONG = "http://www.w3.org/2001/XMLSchema#long"

pytestmark = pytest.mark.usefixtures("engine")


def _current() -> str:
    return engines.CURRENT


def _pick(**by_engine):
    return by_engine[_current()]


# ---- P1 snapshotUpdateSemantics --------------------------------------------------------------------------------------

_ROWS = {"insert row first": "(<urn:s> UNDEF) (UNDEF <urn:s>)", "delete row first": "(UNDEF <urn:s>) (<urn:s> UNDEF)"}


def _p1(rows: str) -> bool:
    """Does the triple the DELETE removes and the INSERT writes survive? The specification removes every deletion and then
    adds every insertion, so it does in either order. An engine that applies each solution in turn loses it when the
    solution that deletes comes after the one that inserts."""
    ds = engines.dataset()
    ds.graph(U("urn:g")).add(TRIPLE)
    ds.update(
        "DELETE { GRAPH <urn:g> { ?d <urn:p> <urn:o> } } INSERT { GRAPH <urn:g> { ?i <urn:p> <urn:o> } } "
        f"WHERE {{ VALUES (?i ?d) {{ {rows} }} }}"
    )
    return TRIPLE in ds.graph(U("urn:g"))


_P1_CHILD = """
import sys
from rdflib import Dataset, URIRef
t = (URIRef("urn:s"), URIRef("urn:p"), URIRef("urn:o"))
d = Dataset(); d.graph(URIRef("urn:g")).add(t)
d.update("DELETE { GRAPH <urn:g> { ?d <urn:p> <urn:o> } } INSERT { GRAPH <urn:g> { ?i <urn:p> <urn:o> } } WHERE { VALUES (?i ?d) { " + sys.argv[1] + " } }")
print(t in d.graph(URIRef("urn:g")))
"""


def _p1_rdflib_by_seed(rows: str, seeds=range(12)) -> list[bool]:
    """rdflib evaluates this WHERE as a non-lazy join, whose right side it puts in a Python set
    (`evaluate.evalJoin`), so the order of the solutions follows the process's hash seed. `update.evalModify` then
    deletes and inserts one solution at a time. Run in child processes with fixed seeds, so the answer is the same on
    every run (docs/architecture/triple-store-discovery.md, TSD-01)."""
    import os
    import subprocess
    import sys

    out = []
    for seed in seeds:
        env = {**os.environ, "PYTHONHASHSEED": str(seed)}
        result = subprocess.run([sys.executable, "-c", _P1_CHILD, rows], env=env, capture_output=True, text=True, check=True)
        out.append(result.stdout.strip() == "True")
    return out


@pytest.mark.parametrize("order", sorted(_ROWS))
def test_h2_4b_t1_p1_how_an_engine_applies_the_result_of_a_delete_insert_where(order):
    if _current() == "rdflib":
        # One solution at a time, in hash order: some seeds keep the triple and some lose it, in either written order.
        by_seed = _p1_rdflib_by_seed(_ROWS[order])
        assert True in by_seed and False in by_seed
    else:
        # One solution at a time, in the order the VALUES block gives (the mutations are collected, then applied in order).
        assert _p1(_ROWS[order]) == {"insert row first": False, "delete row first": True}[order]


def test_h2_4b_t2_p1_snapshot_update_semantics_holds_for_neither_engine():
    """Corrected on 2026-10-13. The first version asserted that rdflib keeps the triple in both orders, which held only
    for some hash seeds and made the test fail at random. Neither engine applies the specification's order."""
    if _current() == "rdflib":
        snapshot = all(all(_p1_rdflib_by_seed(rows)) for rows in _ROWS.values())
    else:
        snapshot = all(_p1(rows) for rows in _ROWS.values())
    assert snapshot is False


# ---- P2 a request whose second operation fails -----------------------------------------------------------------------


def _p2(failing: str) -> tuple[bool, bool]:
    """(the request failed, the first operation's insert is still there)."""
    ds = engines.dataset()
    failed = False
    try:
        ds.update("INSERT DATA { GRAPH <urn:g> { <urn:s> <urn:p> <urn:o> } } ; " + failing)
    except Exception:
        failed = True
    return failed, TRIPLE in ds.graph(U("urn:g"))


def test_h2_4b_t3_p2_a_request_that_fails_at_its_second_operation_keeps_or_loses_its_first():
    """The failure half of `atomicUpdateRequest`. Its isolation half needs concurrent writers, which is H5's."""
    if _current() == "rdflib":
        # CREATE GRAPH is not implemented, and DROP GRAPH of an absent graph does not fail. LOAD of an absent source does.
        assert _p2("LOAD <urn:no-such>") == (True, True)
        assert _p2("DROP GRAPH <urn:absent>") == (False, True)
    else:
        assert _p2("DROP GRAPH <urn:absent>") == (True, False)  # an error at run time, and the first insert is rolled back


# ---- P3 a correlated GRAPH ?g in an inner group -------------------------------------------------------------------------


def _p3_ratio(triples: int = 3000, graphs: int = 100) -> float:
    def timed(count: int) -> float:
        ds = engines.dataset()
        for i in range(count):
            g = ds.graph(U(f"urn:g:{i}"))
            for j in range(triples):
                g.add((U(f"urn:s{j}"), U("urn:p"), Literal(j)))
        best = float("inf")
        for _ in range(3):
            start = time.perf_counter()
            rows = ds.query("SELECT (COUNT(*) AS ?n) WHERE { BIND(<urn:g:0> AS ?g) OPTIONAL { GRAPH ?g { ?s ?p ?o } } }")
            best = min(best, time.perf_counter() - start)
            assert int(list(rows)[0][0]) == triples
        return best

    return timed(graphs) / timed(1)


def test_h2_4b_t4_p3_a_graph_variable_bound_outside_does_not_make_the_query_scan_every_graph():
    """100 graphs of equal size, against 1. A store that evaluated the inner group before the join would take about 100
    times as long. Both engines pass the binding in (the cost note of H2.3-Q2), so `compile` has no reason yet to choose
    the caller-named graph for a store. The bound is wide, since the measure is a ratio of two timings of one machine."""
    assert _p3_ratio() < 8


# ---- P4 an unbound graph variable in a template ------------------------------------------------------------------------


def test_h2_4b_t5_p4_a_template_quad_whose_graph_variable_is_unbound_is_skipped_or_written_to_a_blank_node_graph():
    """TD-44. The specification skips it."""
    ds = engines.dataset()
    ds.update("INSERT { GRAPH ?g { <urn:s> <urn:p> <urn:o> } } WHERE {}")
    names = [str(g.identifier) for g in ds.graphs() if len(g)]
    if _current() == "rdflib":
        assert len(names) == 1 and not names[0].startswith("urn:")  # a fresh blank-node graph holds the triple
    else:
        assert names == []


# ---- P5 numeric datatypes ---------------------------------------------------------------------------------------------


def test_h2_4b_t6_p5_an_integer_derived_literal_keeps_its_datatype_on_rdflib_and_becomes_xsd_integer_on_oxigraph():
    """The persistence profile pins `seq`, `epoch` and every position to `xsd:long` (guide Chapter 13). That holds only on an
    engine that keeps the datatype."""
    ds = engines.dataset()
    ds.update(f'INSERT DATA {{ GRAPH <urn:g> {{ <urn:s> <urn:p> "1"^^<{LONG}> }} }}')
    (stored,) = [o.datatype for _, _, o in ds.graph(U("urn:g"))]
    reported = list(ds.query(f'SELECT (DATATYPE("1"^^<{LONG}>) AS ?d) WHERE {{}}'))[0][0]
    expected = _pick(rdflib=LONG, oxigraph="http://www.w3.org/2001/XMLSchema#integer")
    assert (str(stored), str(reported)) == (expected, expected)


def test_h2_4b_t7_p5_the_parameter_guards_datatype_test_cannot_pass_a_long_on_oxigraph():
    """So an operation with the guard on writes nothing there, and an operation without it writes. A guard whose test an
    engine can never pass is unusable on that engine (FMH-H2-4b, decision 1)."""
    from persistence.builders import build
    from persistence.ir_render import render
    from test_builders import CONTEXT, LONG as LONG_TERM

    def row_written(guards: bool) -> bool:
        ds = engines.dataset()
        ds.update(render(build("bootstrap-version-row", CONTEXT, guards=guards)), initBindings={"target": U("urn:stream:new"), "epoch": LONG_TERM(3)})
        return bool(len(ds.graph(U("urn:g:meta"))))

    assert row_written(False)
    assert row_written(True) == _pick(rdflib=True, oxigraph=False)
