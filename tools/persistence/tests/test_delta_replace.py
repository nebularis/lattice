# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""DR1: the delta replace (persistence-delta-replace, plan section 3). The compare-and-set of an optimistic named-graph or composite family
takes the triples the caller retracted and asserted against the state it read, deletes the first and inserts the second, and sweeps nothing,
so it is linear in the size of the change on every engine, rdflib included, and none of these tests skips by engine. `dal:replaceEncoding`
chooses between it (`dal:ChangedTriples`, the default under `dal:Optimistic`) and the whole-state replace (`dal:WholeState`). These tests cover
the builders and their contract, the selection, the diagnostics and the behaviour against the whole-state replace.
Validation Pack: docs/developer/validation/persistence-delta-replace.md. Test IDs are DR1-Tn."""

from __future__ import annotations

import re

import pytest
from rdflib import Literal as RdfLiteral, URIRef

import engines
from builder_goldens import CANONICAL_CONTEXT
from persistence import witness
from persistence.builders import BUILDERS, build
from persistence.compiler import compile_targets
from persistence.contract import OperationKind, contract_of
from persistence.ir_render import check, render
from persistence.operations import replace_encoding
from test_patch_log import (
    ADDED, DATA, FAMILIES, META, OUTSIDER, OWNS, MEMBER, P, Q, PAT, REMOVED, ROOT, TXN, LONG, _kinds, _refusal, _templates, aggregate, args, data_graph,
    delta, everything, nt, run, stem, store, triples,
)

U = URIRef
DELTA_BUILDERS = sorted(k for k in BUILDERS if "-delta" in k and k.startswith("cas-replace"))
RECEIPTS = {"named-graph": ("", "-patch-log", "-no-receipt"), "composite": ("-patch-log", "-no-receipt")}
CASES = [
    pytest.param(family, tag, dg, id=f"{family}{tag}{'-dataset-guard' if dg else ''}")
    for family in FAMILIES for tag in RECEIPTS[family] for dg in (False, True)
]
EXAMPLE = witness.EXAMPLES_DIR / "replace-encoding.ttl"
BYSTANDER = {(OUTSIDER, P, RdfLiteral("outside"))}
"""The neighbour a composite store holds in the same data graph, which no replace of the root may touch."""
DAL, EX = "https://www.nebularis.org/neuro-semantic/lattice/persistence#", "https://example.org/lending#"


def delta_stem(family: str, tag: str = "-patch-log", dg: bool = False) -> str:
    base = "cas-replace-named-graph-delta" if family == "named-graph" else "cas-replace-composite-property-delta"
    return base + tag + ("-dataset-guard" if dg else "")


def _bystander(family: str) -> set:
    return BYSTANDER if family == "composite" else set()


def _row(ds) -> dict:
    return {str(p).removeprefix(PAT): o for s, p, o in ds.graph(META) if s == ROOT}


# ---- the builders and their contract ------------------------------------------------------------------------------------------------


def test_dr1_t1_ten_delta_builders_exist_one_per_receipt_model_and_guard_of_each_family():
    assert DELTA_BUILDERS == sorted(delta_stem(family, tag, dg) for family in FAMILIES for tag in RECEIPTS[family] for dg in (False, True))
    assert len(DELTA_BUILDERS) == 10


@pytest.mark.parametrize("key", DELTA_BUILDERS)
def test_dr1_t2_a_delta_builder_deletes_and_inserts_the_callers_two_slots_and_sweeps_nothing(key):
    op = build(key, dict(CANONICAL_CONTEXT))
    sets = check(op)
    assert any(a.subject == "{payload}" and a.mode == "Delete" for a in sets.writes) and any(a.subject == "{payload}" and a.mode == "Insert" for a in sets.writes)
    text = render(op)
    deleted, inserted = text[text.index("DELETE"):text.index("INSERT")], text[text.index("INSERT"):text.index("WHERE")]
    graph = "?g" if "named-graph" in key else "<urn:g:orders>"
    assert "UNION" not in text and "?s ?p ?o" not in text
    assert set(re.findall(r"OPTIONAL \{[^}]*\}", text)) <= {"OPTIONAL { $root pat:head ?prevRev }"}, "the head is the only optional, never a sweep"
    assert "GRAPH " + graph + " { {{{retractTriples}}} }" in deleted and "pat:seq $expectedSeq" in deleted
    assert "GRAPH " + graph + " { {{{assertTriples}}} }" in inserted
    patch_log = "-patch-log" in key
    assert ("GRAPH ?addGraph { {{{assertTriples}}} }" in inserted) is patch_log
    assert ("GRAPH ?delGraph { {{{retractTriples}}} }" in inserted) is patch_log
    assert "payloadTriples" not in text
    contract = contract_of(op)
    assert contract.kind is OperationKind.DELTA_REPLACE
    assert "payloadTriples" not in {p.name for p in contract.parameters}
    assert (contract.payload.parameter, contract.payload.encoding) == ("assertTriples", "GroundNTriples")
    assert contract.version == 1
    assert contract.digest.parts() == (
        ("OperationKindPart", ()), ("TargetPart", ("root",)), ("ExpectedSeqPart", ("expectedSeq",)), ("AddPart", ("assertTriples",)),
        ("DelPart", ("retractTriples",)),
    )


# ---- the selection and the diagnostics ---------------------------------------------------------------------------------------------------


def _replaces(graph) -> dict:
    out = {}
    for ct in compile_targets(graph):
        name = str(ct.target.cls).rsplit("#", 1)[-1]
        out[name] = next(op.template_id for op in ct.operations if op.operation == "cas-replace")
    return out


def test_dr1_t3_compile_selects_the_delta_by_default_under_optimistic_and_the_whole_state_replace_where_declared():
    assert _replaces(witness._load_fixture(EXAMPLE)) == {
        "Ticket": "cas-replace-named-graph-delta-patch-log", "Draft": "cas-replace-named-graph-delta", "Snapshot": "cas-replace-named-graph-rows",
    }
    assert _templates(witness.EXAMPLES_DIR / "baseline-single-class.ttl")["cas-replace"] == "cas-replace-named-graph-delta-patch-log"
    assert _templates(witness.EXAMPLES_DIR / "composite-project-ownership.ttl")["cas-replace"] == "cas-replace-composite-property-delta-patch-log"
    # the effective encoding: the declared one, else the delta under dal:Optimistic and the whole state under any other concurrency
    g = witness._load_fixture(EXAMPLE)
    g.remove((U(EX + "DraftProfile"), U(DAL + "replaceEncoding"), None))
    g.remove((U(EX + "DraftProfile"), U(DAL + "concurrencyProfile"), None))
    g.remove((U(EX + "DraftProfile"), U(DAL + "minConcurrencyLevel"), None))
    g.add((U(EX + "DraftProfile"), U(DAL + "concurrencyProfile"), U(DAL + "ProvidedConcurrency")))
    encodings = {str(ct.target.cls).rsplit("#", 1)[-1]: replace_encoding(ct.dimensions) for ct in compile_targets(g)}
    assert encodings == {"Ticket": "ChangedTriples", "Draft": "WholeState", "Snapshot": "WholeState"}


def test_dr1_t4_an_encoding_that_is_neither_of_the_two_is_refused():
    assert _refusal(witness._load_fixture(witness.WITNESS_DIR / "refusal-ReplaceEncodingUnknown.ttl")) == "ReplaceEncodingUnknown"


def test_dr1_t5_changed_triples_on_a_family_with_no_version_row_guard_is_refused():
    assert _refusal(witness._load_fixture(witness.WITNESS_DIR / "refusal-ChangedTriplesNeedsOptimistic.ttl")) == "ChangedTriplesNeedsOptimistic"


def test_dr1_t6_an_encoding_on_a_family_with_no_replace_to_encode_is_warned_and_one_on_a_replacing_family_is_not():
    assert "ReplaceEncodingNotApplicable" in _kinds(witness._load_fixture(witness.WITNESS_DIR / "warning-ReplaceEncodingNotApplicable.ttl"))
    assert "ReplaceEncodingNotApplicable" not in _kinds(witness._load_fixture(EXAMPLE))


def test_dr1_t7_a_replace_form_on_a_delta_family_is_warned_and_on_a_whole_state_family_is_not():
    g = witness._load_fixture(EXAMPLE)
    for name in ("Ticket", "Snapshot"):
        g.add((U(EX + name + "Profile"), U(DAL + "replaceForm"), U(DAL + "RowsReplace")))
    warned = {str(ct.target.cls).rsplit("#", 1)[-1] for ct in compile_targets(g) if "ReplaceFormNotApplicable" in {d.kind for d in ct.diagnostics}}
    assert warned == {"Ticket"}


# ---- behaviour, against the whole-state replace -----------------------------------------------------------------------------------------


@pytest.mark.parametrize("family,tag,dg", CASES)
@engines.each_engine_and_guards
def test_dr1_t8_the_delta_replace_leaves_what_the_whole_state_replace_leaves_under_each_receipt_model_and_guard(family, tag, dg):
    old = aggregate(family)
    new = (old - {REMOVED}) | {ADDED}
    ds = store(family, dataset_epoch=1 if dg else None, head=tag != "-no-receipt")
    run(ds, delta_stem(family, tag, dg), args(), assertTriples=nt([ADDED]), retractTriples=nt([REMOVED]))
    assert triples(ds, data_graph(family)) == new | _bystander(family)
    row = _row(ds)
    assert row["seq"].toPython() == 2
    assert ("head" in row and row["head"] == U("urn:rev:order/1/2")) is (tag != "-no-receipt")
    assert (U("urn:txn:2"), U(PAT + "rev"), U("urn:rev:order/1/2")) in triples(ds, TXN)
    if tag == "-patch-log":
        assert triples(ds, delta(2, "add")) == {ADDED} and triples(ds, delta(2, "del")) == {REMOVED}
    whole = store(family, dataset_epoch=1 if dg else None, head=tag != "-no-receipt")
    run(whole, stem("replace", family, tag, dg), args(), payloadTriples=nt(new), assertTriples=nt([ADDED]), retractTriples=nt([REMOVED]))
    assert triples(whole, data_graph(family)) == triples(ds, data_graph(family))


@pytest.mark.parametrize("family", FAMILIES)
@engines.each_engine_and_guards
def test_dr1_t9_a_lost_race_writes_nothing_in_any_graph(family):
    ds = store(family, seq=2)
    before = everything(ds)
    run(ds, delta_stem(family), args(seq=1), assertTriples=nt([ADDED]), retractTriples=nt([REMOVED]))
    assert everything(ds) == before


@pytest.mark.parametrize("tag", ["-patch-log", "-no-receipt"])
@pytest.mark.parametrize("family", FAMILIES)
@engines.each_engine_and_guards
def test_dr1_t10_a_retry_under_the_same_transaction_id_changes_nothing_the_second_time(family, tag):
    ds = store(family)
    slots = {"assertTriples": nt([ADDED]), "retractTriples": nt([REMOVED])}
    run(ds, delta_stem(family, tag), args(), **slots)
    # put the row back at the seq the request expects, so that the claim alone refuses the second run
    ds.graph(META).remove((ROOT, U(PAT + "seq"), None))
    ds.graph(META).add((ROOT, U(PAT + "seq"), LONG(1)))
    before = everything(ds)
    run(ds, delta_stem(family, tag), args(), **slots)
    assert everything(ds) == before


@pytest.mark.parametrize("tag", RECEIPTS["composite"])
@engines.each_engine_and_guards
def test_dr1_t11_a_composite_delta_that_retracts_a_member_removes_it_and_leaves_the_root_and_the_neighbour(tag):
    ds = store("composite", head=tag != "-no-receipt")
    run(ds, delta_stem("composite", tag), args(), assertTriples="", retractTriples=nt([(ROOT, OWNS, MEMBER), (MEMBER, P, RdfLiteral("line"))]))
    root = {(ROOT, P, RdfLiteral("old")), (ROOT, Q, RdfLiteral("keep"))}
    assert triples(ds, DATA) == root | BYSTANDER
    assert _row(ds)["seq"].toPython() == 2


@pytest.mark.parametrize("tag", ["-patch-log", "-no-receipt"])
@pytest.mark.parametrize("family", FAMILIES)
@engines.each_engine_and_guards
def test_dr1_t12_an_empty_delta_still_moves_the_row_and_writes_the_receipt_which_is_why_the_caller_withholds_it(family, tag):
    ds = store(family, head=tag != "-no-receipt")
    before = triples(ds, data_graph(family))
    run(ds, delta_stem(family, tag), args(), assertTriples="", retractTriples="")
    assert triples(ds, data_graph(family)) == before
    assert _row(ds)["seq"].toPython() == 2
    assert (U("urn:txn:2"), U(PAT + "rev"), U("urn:rev:order/1/2")) in triples(ds, TXN)
    if tag == "-patch-log":
        assert not triples(ds, delta(2, "add")) and not triples(ds, delta(2, "del"))
        assert (U("urn:rev:order/1/2"), U(PAT + "asserts"), delta(2, "add")) in {t for g in ds.graphs() for t in g}


def test_dr1_t13_a_composite_family_with_a_boundary_shape_keeps_its_payload_check_under_the_delta():
    (ct,) = compile_targets(witness._load_fixture(witness.EXAMPLES_DIR / "composite-project-ownership.ttl"))
    ids = {o.operation: o.template_id for o in ct.operations}
    assert ids["cas-replace"] == "cas-replace-composite-property-delta-patch-log" and ids["payload-check"] == "payload-check"
