# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""H2.4a: the composite family's builders (formal-methods track H, slice H2.4a, plan 4.2). The ports were held to their
templates by a harness that H2.9 removed with the templates (FMH-H2-9), and the lifecycle of an aggregate is tested in test_composite_lifecycle.py and
test_composite_boundary.py, which now run on the builders. These tests add what the ports bring: the read and write sets,
the guard's case for this family, the engine rules the sweep relies on, and the stored-IR rules SI-1 and SI-2
(typed IR sketch 9.4). Validation Pack: docs/developer/validation/FMH-H2-4a.md. Test IDs are H2.4a-Tn."""

from __future__ import annotations

import dataclasses
import enum
import warnings

import pytest

import engines
from rdflib import Dataset, Literal, URIRef, Variable
from rdflib.namespace import XSD

from persistence import ir as ir_module
from persistence import witness
from persistence.builders import BUILDERS, build
from persistence.compiler import compile_to_graph
from persistence.instantiate import instantiate_by_target
from persistence.ir import GUARDS_OFF
from persistence import templatecheck
from persistence.ir_render import access_sets, fill_slots
from persistence.terms import Integer, Iri, Literal as EncodedLiteral, PropertyPath, SparqlTerm

from test_builders import _ported, ported_operations
from test_composite_lifecycle import (
    CREATE, DATA_GRAPH, PAT, PROJECT_EXAMPLE, REPLACE, ROOT, TOMBSTONE, _data, _data_graph, _dataset, _delete_set, _meta,
    _nt, _px, _quads, _run, _text,
)


def _compiled():
    return compile_to_graph(witness._load_fixture(PROJECT_EXAMPLE))[0]


def _context(stem: str) -> dict:
    ops = ported_operations([("project", _compiled())])
    return next(c for _, _, s, c in ops if s == stem)


# ---- the read and write sets (plan 4.2 step 2) --------------------------------------------------------------------


def test_h2_4a_t1_a_replace_reads_the_closure_and_writes_the_delete_set_the_payload_and_the_row():
    context = _context(REPLACE)
    sets = access_sets(build(REPLACE, context))
    data = str(context["dataGraph"])
    path = str(context["ownedPath"])
    reads = {(a.role, a.graph, a.subject, a.predicate, a.closure) for a in sets.reads}
    writes = {(a.role, a.graph, a.subject, a.predicate) for a in sets.writes}
    assert ("data", data, "$root", path, True) in reads  # the sweep, reached at execution
    assert ("data", data, "?s", "?p") in writes and ("data", data, "{payload}", "*") in writes
    assert ("meta", str(context["metaGraphPrefix"]), "$root", "<https://example.org/lattice/patterns#seq>") in writes
    assert not any(a.closure for a in sets.writes)


def test_h2_4a_t2_a_tombstone_has_no_payload_and_a_create_reads_the_roots_triples_to_refuse_a_second():
    tomb = access_sets(build(TOMBSTONE, _context(TOMBSTONE)))
    assert not any(a.subject == "{payload}" for a in tomb.writes)
    create = access_sets(build(CREATE, _context(CREATE)))
    data = str(_context(CREATE)["dataGraph"])
    assert ("data", data, "$root", "?anyP") in {(a.role, a.graph, a.subject, a.predicate) for a in create.reads}
    assert not any(a.closure for a in create.reads)


# ---- the guard's case for this family (step 4) ---------------------------------------------------------------------


def _text_without_guard(operation: str) -> str:
    (by_target,) = instantiate_by_target(compile_to_graph(witness._load_fixture(PROJECT_EXAMPLE), guards=False)[0]).values()
    return fill_slots(by_target[operation], templatecheck._SLOT_STAND_INS)


def _second_aggregate(ds: Dataset) -> None:
    ds.graph(_meta(REPLACE)).add((_px("p2"), URIRef(PAT + "epoch"), Literal(1, datatype=XSD.long)))
    ds.graph(_meta(REPLACE)).add((_px("p2"), URIRef(PAT + "seq"), Literal(1, datatype=XSD.long)))


def _values_without_root() -> dict:
    return {
        "epoch": Literal(1, datatype=XSD.long), "expectedSeq": Literal(1, datatype=XSD.long), "nextSeq": Literal(2, datatype=XSD.long),
        "newRev": URIRef("urn:rev:x"), "txnId": URIRef("urn:txn:x"), "requestDigest": Literal("d"),
    }


def _update(ds: Dataset, text: str, values: dict) -> None:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        ds.update(text, initBindings={Variable(k): v for k, v in values.items()})


@engines.rdflib_only
def test_h2_4a_t3_a_replace_with_no_root_over_two_aggregates_writes_nothing_and_unguarded_it_sweeps_the_data_graph():
    payload = _nt({(ROOT, _px("name"), Literal("Back"))})
    guarded = _dataset(REPLACE, data=_data())
    _second_aggregate(guarded)
    before = _quads(guarded)
    _update(guarded, _text(REPLACE).replace(_text_stand_in(), payload), _values_without_root())
    assert _quads(guarded) == before
    unguarded = _dataset(REPLACE, data=_data())
    _second_aggregate(unguarded)
    _update(unguarded, _text_without_guard("cas-replace").replace(_text_stand_in(), payload), _values_without_root())
    # what rdflib does, recorded: with no root the sweep reaches the nodes of every stored aggregate, so both are swept, the
    # payload is written once, and both stored version rows move. Only nodes no aggregate reaches (the references) stay.
    left = _data_graph(unguarded)
    assert (ROOT, _px("name"), Literal("Back")) in left
    assert not {s for s, _, _ in left} & {_px("p2"), _px("m9"), _px("m1"), _px("t1")}
    assert {_px("acme"), _px("alice")} <= {s for s, _, _ in left}
    meta = {(s, o) for s, p, o, g in _quads(unguarded) if p == URIRef(PAT + "seq")}
    assert (_px("p2"), Literal(2, datatype=XSD.long)) in meta and (ROOT, Literal(2, datatype=XSD.long)) in meta


def _text_stand_in() -> str:
    from persistence import templatecheck

    return templatecheck._SLOT_STAND_INS["payloadTriples"]


# ---- the variants and replays (step 3, what the lifecycle tests do not) ---------------------------------------------


@engines.each_engine_and_guards
def test_h2_4a_t4_a_replay_of_a_replace_and_of_a_tombstone_changes_nothing():
    for template, kwargs in ((REPLACE, {"payload": {(ROOT, _px("name"), Literal("Back"))}}), (TOMBSTONE, {})):
        ds = _dataset(template, data=_data())
        _run(ds, template, **kwargs)
        after = _quads(ds)
        _run(ds, template, **kwargs)
        assert _quads(ds) == after, template


@engines.each_engine_and_guards
def test_h2_4a_t5_a_replace_of_a_row_whose_aggregate_is_empty_still_moves_the_row():
    """The sweep is optional. An aggregate with a row and no triples is replaced, and the payload is written."""
    ds = _dataset(REPLACE, data=None)
    _run(ds, REPLACE, payload={(ROOT, _px("name"), Literal("First"))})
    assert _data_graph(ds) == {(ROOT, _px("name"), Literal("First"))}
    assert (ROOT, URIRef(PAT + "seq"), engines.canon(Literal(2, datatype=XSD.long)), str(_meta(REPLACE))) in _quads(ds)


# ---- engine rules the sweep relies on, run on rdflib (plan 5.1, step 6) ---------------------------------------------


def _select(ds: Dataset, query: str) -> set:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        return {tuple(str(v) for v in row) for row in ds.query(query)}


@pytest.mark.conformance
@engines.each_engine_and_guards
def test_h2_4a_t6_a_path_that_may_match_no_steps_reaches_the_root_itself_and_an_inverse_step_walks_against_the_edge():
    ds = engines.dataset()
    g = ds.graph(URIRef("urn:g"))
    g.add((URIRef("urn:r"), URIRef("urn:owns"), URIRef("urn:a")))
    g.add((URIRef("urn:c"), URIRef("urn:on"), URIRef("urn:a")))
    reached = _select(ds, "SELECT ?s WHERE { GRAPH <urn:g> { <urn:r> (<urn:owns>|^<urn:on>)* ?s } }")
    assert reached == {("urn:r",), ("urn:a",), ("urn:c",)}  # the root, a forward step, and an inverse step from a
    # a term that is in no triple of the graph. rdflib and Jena match it with itself and Oxigraph does not (FMH-H2-4b, TSD-08, TSD-51)
    absent = _select(ds, "SELECT ?s WHERE { GRAPH <urn:g> { <urn:lonely> (<urn:owns>)* ?s } }")
    assert absent == ({("urn:lonely",)} if engines.CURRENT in ("rdflib", "jena") else set())


@engines.each_engine_and_guards
def test_h2_4a_t7_a_payload_that_keeps_a_triple_the_aggregate_already_has_keeps_it_on_an_engine_that_applies_each_solution_in_turn():
    """R0 inserts the whole payload in every solution, so the result does not depend on the order an engine applies
    removals and additions in (typed IR sketch 4.3). rdflib applies one solution at a time."""
    data = _data()
    ds = _dataset(REPLACE, data=data)
    kept = {t for t in data if t[0] == ROOT and t[1] == _px("name")}
    assert kept
    _run(ds, REPLACE, payload=kept | {(ROOT, _px("note"), Literal("new"))})
    assert kept <= _data_graph(ds) and (ROOT, _px("note"), Literal("new")) in _data_graph(ds)
    assert {t for t in _data_graph(ds) if t[0] == ROOT} == kept | {(ROOT, _px("note"), Literal("new"))}


# ---- the stored-IR rules SI-1 and SI-2 (typed IR sketch 9.4, step 5) ------------------------------------------------


_TERMS = (Iri, EncodedLiteral, Integer, PropertyPath)


def encode(value):
    """A generic structural encoding. It accepts only what SI-1 allows and raises TypeError for anything else."""
    if value is None or type(value) in (bool, int, str):
        return ("atom", value)
    if isinstance(value, SparqlTerm):
        if type(value) not in _TERMS:
            raise TypeError(f"{type(value).__name__} is not an encoded term")
        return ("term", type(value).__name__, str(value))
    if isinstance(value, enum.Enum):
        return ("enum", type(value).__name__, value.name)
    if isinstance(value, tuple):
        return ("tuple", tuple(encode(v) for v in value))
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        if not type(value).__dataclass_params__.frozen:
            raise TypeError(f"{type(value).__name__} is not frozen")
        return ("value", type(value).__name__, tuple((f.name, encode(getattr(value, f.name))) for f in dataclasses.fields(value)))
    raise TypeError(f"{type(value).__name__} is not an IR value, an enum, an atom, a tuple or an encoded term")


def decode(encoded):
    kind = encoded[0]
    if kind == "atom":
        return encoded[1]
    if kind == "term":
        cls = {c.__name__: c for c in _TERMS}[encoded[1]]
        return cls(encoded[2])
    if kind == "enum":
        return getattr(ir_module, encoded[1])[encoded[2]]
    if kind == "tuple":
        return tuple(decode(v) for v in encoded[1])
    return getattr(ir_module, encoded[1])(**{name: decode(v) for name, v in encoded[2]})


def test_h2_4a_t8_every_ported_operation_goes_through_a_structural_encoding_and_back_and_is_equal_to_itself():
    checked = 0
    for _, _, stem, context in _ported():
        for guards in (True, False):
            for names in ("query", "caller"):
                operation = build(stem, context, guards=guards, graph_names=names)
                assert decode(encode(operation)) == operation, (stem, guards, names)
                checked += 1
    assert checked >= 4 * len(BUILDERS)


def test_h2_4a_t9_building_an_operation_twice_gives_equal_values():
    for _, _, stem, context in _ported():
        assert build(stem, context) == build(stem, context)


def test_h2_4a_t10_a_builder_reads_no_file_clock_or_environment(monkeypatch):
    import builtins
    import os
    import time

    def refuse(*_a, **_k):
        raise AssertionError("a builder touched the outside world")

    operations = [(stem, context) for _, _, stem, context in _ported()]
    expected = [build(stem, context) for stem, context in operations]
    monkeypatch.setattr(builtins, "open", refuse)
    monkeypatch.setattr(time, "time", refuse)
    monkeypatch.setattr(os, "getenv", refuse)
    monkeypatch.setattr(os, "environ", type("Env", (dict,), {"__getitem__": refuse, "get": refuse})())
    assert [build(stem, context) for stem, context in operations] == expected


@pytest.mark.parametrize("make", [
    lambda: dataclasses.replace(build(TOMBSTONE, _context(TOMBSTONE)), id=lambda: 1),
    lambda: dataclasses.replace(build(TOMBSTONE, _context(TOMBSTONE)), insert=[]),
    lambda: dataclasses.replace(build(TOMBSTONE, _context(TOMBSTONE)), id=URIRef("urn:x")),
    lambda: dataclasses.replace(build(TOMBSTONE, _context(TOMBSTONE)), params=({"a": 1},)),
], ids=["a callable", "a mutable list", "an rdflib node", "a dict"])
def test_h2_4a_t11_a_value_that_holds_anything_si1_forbids_fails_the_encoding(make):
    with pytest.raises(TypeError):
        encode(make())
