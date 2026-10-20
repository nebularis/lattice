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


def _snapshot_updates() -> bool:
    """Whether the installed pyoxigraph applies every deletion before any insertion (0.5.12 on, TSD-01). Imported here, since the rdflib
    runs need no Oxigraph."""
    from lattice_testing_oxigraph import SNAPSHOT_UPDATES

    return SNAPSHOT_UPDATES


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
    elif _snapshot_updates():
        # From pyoxigraph 0.5.12, every deletion and then every insertion, as the specification says, in either row order (TSD-01).
        assert _p1(_ROWS[order]) is True
    else:
        # Up to 0.5.11, one solution at a time, in the order the VALUES block gives (the mutations are collected, then applied in order).
        assert _p1(_ROWS[order]) == {"insert row first": False, "delete row first": True}[order]


def test_h2_4b_t2_p1_snapshot_update_semantics_holds_on_oxigraph_from_0_5_12_and_not_on_rdflib():
    """Corrected on 2026-10-13. The first version asserted that rdflib keeps the triple in both orders, which held only
    for some hash seeds and made the test fail at random. Changed on 2026-10-20: pyoxigraph 0.5.12 applies the specification's order,
    and 0.5.11 does not, so the expectation follows the installed version (TSD-01). rdflib 7.6.0 does not."""
    if _current() == "rdflib":
        snapshot = all(all(_p1_rdflib_by_seed(rows)) for rows in _ROWS.values())
        assert snapshot is False
    else:
        snapshot = all(_p1(rows) for rows in _ROWS.values())
        assert snapshot is _snapshot_updates()


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


def _datatype_forms(literal: str) -> dict[str, str]:
    """The datatype each engine reports for one literal in five forms: a constant, a parameter substituted by the caller
    (an initial binding on rdflib, text on Oxigraph, as `engines.OxDataset` does), a `VALUES` row, a stored value read back,
    and a stored value compared with the constant in the same query."""
    from rdflib.plugins.sparql.parser import parseQuery  # noqa: F401 (the literal below must be well formed)

    term = literal
    ds = engines.dataset()
    ds.update(f"INSERT DATA {{ GRAPH <urn:g> {{ <urn:s> <urn:p> {term} }} }}")
    param = ds.query(f"SELECT (DATATYPE($p) AS ?d) WHERE {{}}", initBindings={"p": _term(term)})
    forms = {
        "constant": list(ds.query(f"SELECT (DATATYPE({term}) AS ?d) WHERE {{}}"))[0][0],
        "parameter": list(param)[0][0],
        "values": list(ds.query(f"SELECT (DATATYPE(?v) AS ?d) WHERE {{ VALUES ?v {{ {term} }} }}"))[0][0],
        "stored": list(ds.query("SELECT (DATATYPE(?o) AS ?d) WHERE { GRAPH <urn:g> { <urn:s> <urn:p> ?o } }"))[0][0],
    }
    same = list(ds.query(f"SELECT (DATATYPE(?o) = DATATYPE({term}) AS ?same) WHERE {{ GRAPH <urn:g> {{ <urn:s> <urn:p> ?o }} }}"))[0][0]
    return {**{k: str(v) for k, v in forms.items()}, "stored equals constant": str(same)}


def _term(text: str):
    value, _, datatype = text.partition("^^")
    return Literal(value.strip('"'), datatype=URIRef(datatype.strip("<>"))) if datatype else Literal(value.strip('"'))


def test_h2_5_t1_p5_a_long_has_one_datatype_in_every_form_on_each_engine_so_guard_d_can_pass():
    """Guard D compares a parameter's datatype with a constant's (ADR-A123, addendum of 2026-10-13). That rests on a store
    treating the two alike. If an engine ever reports different datatypes for them, guard D refuses every write there, and the
    slice stops for the maintainer (plan 4.3, gate 1)."""
    forms = _datatype_forms(f'"1"^^<{LONG}>')
    expected = _pick(rdflib=LONG, oxigraph="http://www.w3.org/2001/XMLSchema#integer")
    assert set(forms) == {"constant", "parameter", "values", "stored", "stored equals constant"}
    assert {k: v for k, v in forms.items() if k != "stored equals constant"} == dict.fromkeys(("constant", "parameter", "values", "stored"), expected)
    assert forms["stored equals constant"] == "true"


def test_h2_5_t2_p5_a_simple_literal_stays_xsd_string_in_every_form_on_each_engine():
    """Why `Digest` and `String` keep the fixed `xsd:string` test (ADR-A123, addendum of 2026-10-13, point 4)."""
    forms = _datatype_forms('"abc"')
    assert {k: v for k, v in forms.items() if k != "stored equals constant"} == dict.fromkeys(
        ("constant", "parameter", "values", "stored"), "http://www.w3.org/2001/XMLSchema#string")


def _bootstrap_written(bindings: dict, *, guards: bool) -> bool:
    from persistence.builders import build
    from persistence.ir_render import render
    from test_builders import CONTEXT

    ds = engines.dataset()
    ds.update(render(build("bootstrap-version-row", CONTEXT, guards=guards)), initBindings=bindings)
    return bool(len(ds.graph(U("urn:g:meta"))))


@pytest.mark.parametrize("guards", [True, False])
def test_h2_5_t3_a_guarded_write_applies_on_each_engine_where_before_guard_d_every_one_was_refused_on_oxigraph(guards):
    """TD-45. With the guards on, a bootstrap with a well typed epoch writes its row on rdflib and on Oxigraph."""
    from test_builders import LONG as LONG_TERM

    assert _bootstrap_written({"target": U("urn:stream:new"), "epoch": LONG_TERM(3)}, guards=guards)


def test_h2_5_t4_guard_d_refuses_a_missing_or_non_numeric_epoch_on_each_engine_and_an_integer_one_only_where_datatypes_are_kept():
    from rdflib import XSD
    from test_builders import LONG as LONG_TERM

    target = U("urn:stream:new")
    assert not _bootstrap_written({"target": target}, guards=True)
    assert not _bootstrap_written({"target": target, "epoch": Literal("three")}, guards=True)
    assert not _bootstrap_written({"target": target, "epoch": U("urn:epoch")}, guards=True)
    # The addendum's second point: on a store that keeps datatypes only an xsd:long passes, on one that turns every integer
    # into xsd:integer any integer passes and the mismatch cannot arise.
    assert _bootstrap_written({"target": target, "epoch": Literal(3, datatype=XSD.integer)}, guards=True) == _pick(rdflib=False, oxigraph=True)
    assert _bootstrap_written({"target": target, "epoch": LONG_TERM(3)}, guards=True)


# ---- TSD-34 a GRAPH block, a sub-select, a UNION and a FILTER NOT EXISTS ----------------------------------------------------

_TSD34_TRIPLES = [("v1", "cp", "T"), ("v1", "has", "a"), ("v1", "has", "b"), ("v2", "drops", "a"), ("v2", "prev", "v1"), ("v3", "prev", "v2"), ("v2", "adds", "c")]
_TSD34_BODY = {
    "with a sub-select": "{ SELECT ?cp WHERE { ?cp <urn:cp> ?t } }",
    "without a sub-select": "?cp <urn:cp> ?t .",
}


def _tsd34_query(variant: str, version: str) -> str:
    """The members of version 3 (`a` is dropped by version 2, `b` is kept, `c` is added), with the drop test as a `FILTER NOT EXISTS` that has no
    `GRAPH` of its own. The correct answer is `b` and `c`. `version` is `<urn:v3>`, or `$v` when the caller passes it in."""
    return (
        f"SELECT ?m WHERE {{ GRAPH <urn:g> {{ {_TSD34_BODY[variant]} {version} <urn:prev>* ?w . ?w <urn:prev>* ?cp . "
        "{ ?w <urn:has> ?m } UNION { ?w <urn:adds> ?m } "
        f"FILTER NOT EXISTS {{ ?x <urn:drops> ?m ; <urn:prev> ?z . ?z <urn:prev>* ?w . {version} <urn:prev>* ?x }} }} }}"
    )


_TSD34_CHILD = """
import sys
from rdflib import Dataset, URIRef
d = Dataset(); g = d.graph(URIRef("urn:g"))
for s, p, o in %r: g.add((URIRef("urn:" + s), URIRef("urn:" + p), URIRef("urn:" + o)))
rows = d.query(sys.argv[1], initBindings={"v": URIRef("urn:v3")} if "$v" in sys.argv[1] else None)
print("".join(sorted(str(r[0])[-1] for r in rows)))
""" % (_TSD34_TRIPLES,)


def _tsd34_rdflib_by_seed(query: str, seeds=range(16)) -> set[str]:
    """The answers over a sweep of hash seeds, each in a child process (TSD-01, TSD-34)."""
    import os
    import subprocess
    import sys

    return {
        subprocess.run([sys.executable, "-c", _TSD34_CHILD, query], env={**os.environ, "PYTHONHASHSEED": str(seed)}, capture_output=True, text=True, check=True).stdout.strip()
        for seed in seeds
    }


def _tsd34_here(query: str) -> str:
    ds = engines.dataset()
    for s, p, o in _TSD34_TRIPLES:
        ds.graph(U("urn:g")).add((U("urn:" + s), U("urn:" + p), U("urn:" + o)))
    rows = ds.query(query, initBindings={"v": U("urn:v3")} if "$v" in query else None)
    return "".join(sorted(str(r[0])[-1] for r in rows))


@engines.each_engine
@pytest.mark.parametrize("version", ["<urn:v3>", "$v"], ids=["constant", "parameter"])
def test_tsd_34_a_filter_not_exists_in_a_graph_block_with_a_sub_select_and_a_union_sees_the_graph_on_oxigraph_and_only_for_some_hash_seeds_on_rdflib(version):
    """rdflib's `evalGraph` sets `x.ctx.graph` back to the enclosing graph after it yields each solution. Solutions that share one
    context then evaluate a later `FILTER NOT EXISTS` against the dataset's default graph, which holds nothing, and the dropped member `a` stays.
    Which solution comes first follows the hash seed. The same form without the sub-select is right on every seed. The behaviour is the same
    with a constant as with a parameter, so it is not about initial bindings."""
    with_sub = _tsd34_query("with a sub-select", version)
    without = _tsd34_query("without a sub-select", version)
    if _current() == "rdflib":
        assert _tsd34_rdflib_by_seed(with_sub) == {"bc", "abc"}
        assert _tsd34_rdflib_by_seed(without) == {"bc"}
    else:
        assert _tsd34_here(with_sub) == "bc"
        assert _tsd34_here(without) == "bc"


@engines.each_engine
def test_tsd_34_a_variable_used_inside_a_sub_select_takes_the_caller_value_on_each_engine():
    """What TD-68 first assumed was the fault. A parameter inside a sub-select is applied, on rdflib as an initial binding and on Oxigraph as text."""
    ds = engines.dataset()
    for s in ("a", "b"):
        for m in (1, 2, 3):
            ds.graph(U("urn:g")).add((U(f"urn:{s}"), U("urn:p"), U(f"urn:m{m}")))
    rows = ds.query("SELECT ?m WHERE { GRAPH <urn:g> { { SELECT ?m WHERE { $v <urn:p> ?m } } } }", initBindings={"v": U("urn:a")})
    assert len(rows if isinstance(rows, list) else list(rows)) == 3
