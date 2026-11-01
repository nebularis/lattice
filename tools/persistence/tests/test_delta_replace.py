"""DR1: the replace under `dal:ChangedTriples` writes what changed (persistence delta replace unit, slice DR1).
Validation Pack: docs/developer/validation/DR1.md. Test IDs are DR1-Tn.

A delta replace deletes the retracted triples and inserts the asserted ones, guarded on the version row as the whole replace is, and
sweeps nothing. These tests hold it to the state the whole replace leaves, to the guard, and to the aggregate it names, on each engine."""

from __future__ import annotations

import warnings
from pathlib import Path
from urllib.parse import quote

import pytest

import engines
from rdflib import RDF, Dataset, Literal, URIRef, Variable
from rdflib.namespace import XSD

from builder_goldens import CANONICAL_CONTEXT
from persistence import witness
from persistence.builders import build
from persistence.compiler import compile_to_graph
from persistence.ir_render import render
from persistence.namespaces import DAL

from conftest import EXAMPLES_DIR

EX = "https://example.org/lending#"
PAT = "https://www.nebularis.org/neuro-semantic/lattice/persistence-store#"
ROOT, OTHER = URIRef("urn:order:1"), URIRef("urn:order:2")
META = URIRef("urn:g:meta/17")
NAMED = URIRef("urn:g:orders/" + quote(str(ROOT), safe="") + "/data")
DATA = URIRef("urn:g:orders")
STATUS, NOTE, LINE = URIRef(EX + "status"), URIRef(EX + "note"), URIRef(EX + "lineItem")

BEFORE = {(ROOT, RDF.type, URIRef(EX + "Order")), (ROOT, STATUS, Literal("open")), (ROOT, NOTE, Literal("keep"))}
ASSERT = {(ROOT, STATUS, Literal("paid"))}
RETRACT = {(ROOT, STATUS, Literal("open"))}
AFTER = (BEFORE - RETRACT) | ASSERT


def _canon(triple) -> tuple:
    return tuple(engines.canon(term) for term in triple)


def _nt(triples) -> str:
    return " ".join(f"{s.n3()} {p.n3()} {o.n3()} ." for s, p, o in sorted(triples))


def _text(template: str, **slots) -> str:
    text = render(build(template, CANONICAL_CONTEXT, guards=engines.guards()))
    for name, triples in slots.items():
        text = text.replace("{{{" + name + "}}}", _nt(triples))
    assert "{{{" not in text
    return text


def _values(expected_seq: int = 1, txn: str = "urn:txn:a") -> dict:
    return {
        Variable("root"): ROOT, Variable("epoch"): Literal(1, datatype=XSD.long),
        Variable("expectedSeq"): Literal(expected_seq, datatype=XSD.long), Variable("nextSeq"): Literal(expected_seq + 1, datatype=XSD.long),
        Variable("newRev"): URIRef(f"urn:rev:{expected_seq + 1}"), Variable("txnId"): URIRef(txn), Variable("requestDigest"): Literal("d"),
    }


def _dataset(aggregate: URIRef, *, others: bool = False, dataset_guard: bool = False) -> Dataset:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        ds = engines.dataset()
        ds.graph(META).add((ROOT, URIRef(PAT + "epoch"), Literal(1, datatype=XSD.long)))
        ds.graph(META).add((ROOT, URIRef(PAT + "seq"), Literal(1, datatype=XSD.long)))
        if dataset_guard:
            ds.graph(URIRef("urn:g:dataset")).add((URIRef("urn:g:dataset"), URIRef(PAT + "epoch"), Literal(1, datatype=XSD.long)))
        for t in BEFORE:
            ds.graph(aggregate).add(t)
        if others:
            ds.graph(aggregate).add((OTHER, STATUS, Literal("open")))
    return ds


def _run(ds: Dataset, text: str, **values) -> None:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        ds.update(text, initBindings=_values(**values))


def _graph(ds: Dataset, name: URIRef) -> set:
    return {(s, p, o) for s, p, o in ds.graph(name)}


def _seq(ds: Dataset):
    return {o for s, p, o in ds.graph(META) if s == ROOT and p == URIRef(PAT + "seq")}


@engines.each_engine_and_guards
@pytest.mark.parametrize("template", ["cas-replace-named-graph-delta", "cas-replace-named-graph-delta-patch-log", "cas-replace-named-graph-delta-no-receipt"])
def test_dr1_t1_a_named_graph_delta_leaves_the_state_the_whole_replace_leaves(template):
    whole = template.replace("-delta", "")
    by_delta, by_whole = _dataset(NAMED), _dataset(NAMED)
    _run(by_delta, _text(template, assertTriples=ASSERT, retractTriples=RETRACT))
    _run(by_whole, _text(whole, payloadTriples=AFTER, assertTriples=ASSERT, retractTriples=RETRACT))
    assert _graph(by_delta, NAMED) == _graph(by_whole, NAMED) == {_canon(t) for t in AFTER}
    assert _seq(by_delta) == _seq(by_whole) == {engines.canon(Literal(2, datatype=XSD.long))}


@engines.each_engine_and_guards
def test_dr1_t2_a_patch_log_delta_records_the_delta_and_names_it_from_the_receipt():
    ds = _dataset(NAMED)
    _run(ds, _text("cas-replace-named-graph-delta-patch-log", assertTriples=ASSERT, retractTriples=RETRACT))
    assert _graph(ds, URIRef("urn:rev:2/add")) == {_canon(t) for t in ASSERT}
    assert _graph(ds, URIRef("urn:rev:2/del")) == {_canon(t) for t in RETRACT}


@engines.each_engine_and_guards
@pytest.mark.parametrize("expected_seq, txn", [(5, "urn:txn:a"), (1, "urn:txn:used")])
def test_dr1_t3_a_stale_or_replayed_delta_changes_nothing(expected_seq, txn):
    ds = _dataset(NAMED)
    if txn == "urn:txn:used":
        ds.graph(URIRef("urn:g:txn")).add((URIRef(txn), URIRef(PAT + "rev"), URIRef("urn:rev:old")))
    before = {(s, p, o, str(getattr(g, "identifier", g))) for s, p, o, g in ds.quads((None, None, None, None))}
    _run(ds, _text("cas-replace-named-graph-delta-patch-log", assertTriples=ASSERT, retractTriples=RETRACT), expected_seq=expected_seq, txn=txn)
    after = {(s, p, o, str(getattr(g, "identifier", g))) for s, p, o, g in ds.quads((None, None, None, None))}
    assert after == before


@engines.each_engine_and_guards
@pytest.mark.parametrize("template", ["cas-replace-composite-property-delta-patch-log", "cas-replace-composite-property-delta-no-receipt"])
def test_dr1_t4_a_composite_delta_changes_its_aggregate_and_leaves_another_in_the_shared_graph(template):
    ds = _dataset(DATA, others=True)
    _run(ds, _text(template, assertTriples=ASSERT, retractTriples=RETRACT))
    assert _graph(ds, DATA) == {_canon(t) for t in AFTER | {(OTHER, STATUS, Literal("open"))}}


@engines.each_engine_and_guards
@pytest.mark.parametrize("template", ["cas-replace-named-graph-delta-dataset-guard", "cas-replace-composite-property-delta-patch-log-dataset-guard"])
def test_dr1_t5_the_dataset_guard_variant_does_the_same(template):
    graph = NAMED if "named" in template else DATA
    ds = _dataset(graph, dataset_guard=True)
    _run(ds, _text(template, assertTriples=ASSERT, retractTriples=RETRACT))
    assert _graph(ds, graph) == {_canon(t) for t in AFTER}


@pytest.mark.parametrize("template", ["cas-replace-named-graph-delta-patch-log", "cas-replace-composite-property-delta-no-receipt"])
def test_dr1_t6_a_delta_replace_sweeps_nothing_and_deletes_only_what_it_retracts(template):
    text = render(build(template, CANONICAL_CONTEXT))
    delete = text.split("INSERT {")[0]
    assert "OPTIONAL { GRAPH" not in text and "?s ?p ?o" not in text
    assert delete.count("{{{retractTriples}}}") == 1 and "{{{assertTriples}}}" not in delete and "payloadTriples" not in text


def _replace_template(source: Path) -> str:
    compiled, _ = compile_to_graph(witness._load_fixture(source))
    nodes = [n for n in compiled.subjects(DAL.forOperation, None) if str(compiled.value(n, DAL.forOperation)).endswith("cas-replace")]
    return str(compiled.value(compiled.value(nodes[0], DAL.usesTemplate), DAL.templateId))


def test_dr1_t7_an_optimistic_in_place_family_that_declares_no_encoding_replaces_by_its_delta():
    assert _replace_template(EXAMPLES_DIR / "baseline-single-class.ttl") == "cas-replace-named-graph-delta-patch-log"
    assert _replace_template(EXAMPLES_DIR / "composite-project-ownership.ttl").startswith("cas-replace-composite-property-delta")


def test_dr1_t8_a_family_that_declares_whole_state_keeps_the_whole_replace(tmp_path):
    fixture = tmp_path / "whole.ttl"
    fixture.write_text(
        "# base: baseline-single-class.ttl\n"
        "@prefix dal: <https://www.nebularis.org/neuro-semantic/lattice/persistence#> .\n"
        "@prefix ex: <https://example.org/lending#> .\n"
        "ex:WholeState a dal:WriteDisciplineProfile ; dal:appliesTo ex:LoanApplicationClass ; dal:replaceEncoding dal:WholeState .\n",
        encoding="utf-8", newline="\n",
    )
    assert _replace_template(fixture) == "cas-replace-named-graph-patch-log"
