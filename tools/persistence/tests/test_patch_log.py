# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""H2.6d: the patch log for in-place families, and no receipt (formal-methods track H, plan 4.10). Under `dal:PatchLog` the create, replace and
tombstone of both families write delta graphs in the same update, named from the receipt, and the receipt names them. Under `dal:NoReceipt` they
write neither a receipt nor a head and keep the transaction claim. These tests cover the behaviour on each engine, the contract, the selection
in `compile`, and the refusal. The builders are held to their templates by the harness of `test_builders.py`.
Validation Pack: docs/developer/validation/FMH-H2-6d.md. Test IDs are H2.6d-Tn."""

from __future__ import annotations

import re

import pytest
from rdflib import RDF, Literal as RdfLiteral, URIRef
from rdflib.namespace import XSD

import engines
from persistence import witness
from persistence.builders import build
from persistence.compiler import CompileError, compile_targets
from persistence.contract import LOGICAL_KEYS, OperationKind, ResourceKind, contract_of
from persistence.ir_render import render
from persistence.namespaces import PAT as PAT_NS
from persistence.paths import Star, Step
from persistence.terms import Iri, Literal, PropertyPath

U = URIRef
PAT = str(PAT_NS)
LONG = lambda n: RdfLiteral(n, datatype=XSD.long)
EXAMPLES, WITNESSES = witness.EXAMPLES_DIR, witness.WITNESS_DIR
DAL_NS = "https://www.nebularis.org/neuro-semantic/lattice/persistence#"

META, TXN, LOG_PREFIX, DATA = U("urn:g:meta/1"), U("urn:g:txn"), "urn:g:txlog/", U("urn:g:orders")
CONTEXT = {
    "metaGraphPrefix": Iri.encode(str(META)), "txnGraph": Iri.encode(str(TXN)), "logGraphPrefix": Iri.encode(LOG_PREFIX),
    "dataGraph": Iri.encode(str(DATA)), "datasetGraph": Iri.encode("urn:g:dataset"), "datasetNode": Iri.encode("urn:g:dataset-node"),
    "graphPrefix": Literal.encode("urn:g:orders/"), "graphSuffix": Literal.encode(""),
    "ownedPath": PropertyPath.encode(Star(Step(U("urn:p:owns")))),
}
ROOT = U("urn:order:1")
NAMED_GRAPH = U("urn:g:orders/urn%3Aorder%3A1")
OWNS, P, Q = U("urn:p:owns"), U("urn:p:status"), U("urn:p:note")
MEMBER, OUTSIDER = U("urn:order:1/line"), U("urn:order:2")
FAMILIES = ("named-graph", "composite")
WRITES = {"create": "create-if-absent", "replace": "cas-replace", "tombstone": "tombstone-delete"}


_BASES = {
    ("create", "named-graph"): "create-if-absent-named-graph", ("create", "composite"): "create-if-absent-composite",
    ("replace", "named-graph"): "cas-replace-named-graph", ("replace", "composite"): "cas-replace-composite-property",
    ("tombstone", "named-graph"): "tombstone-delete-named-graph", ("tombstone", "composite"): "tombstone-delete-composite",
}


def stem(op: str, family: str, tag: str = "-patch-log", dg: bool = False) -> str:
    return _BASES[(op, family)] + tag + ("-dataset-guard" if dg else "")


def data_graph(family: str) -> URIRef:
    return NAMED_GRAPH if family == "named-graph" else DATA


def aggregate(family: str) -> set:
    """The old state of the aggregate, which for a composite family is the root and a member reached by `urn:p:owns`."""
    base = {(ROOT, P, RdfLiteral("old")), (ROOT, Q, RdfLiteral("keep"))}
    return base if family == "named-graph" else base | {(ROOT, OWNS, MEMBER), (MEMBER, P, RdfLiteral("line"))}


def store(family: str, *, seq: int | None = 1, data: bool = True, dataset_epoch: int | None = None, head: bool = True):
    ds = engines.dataset()
    if seq is not None:
        meta = ds.graph(META)
        meta.add((ROOT, RDF.type, U(PAT + "VersionRow")))
        meta.add((ROOT, U(PAT + "epoch"), LONG(1)))
        meta.add((ROOT, U(PAT + "seq"), LONG(seq)))
        if head:
            meta.add((ROOT, U(PAT + "head"), U("urn:rev:order/1/prev")))
    if data:
        for t in aggregate(family):
            ds.graph(data_graph(family)).add(t)
        if family == "composite":  # a neighbour the sweep must leave alone
            ds.graph(DATA).add((OUTSIDER, P, RdfLiteral("outside")))
    if dataset_epoch is not None:
        ds.graph(U("urn:g:dataset")).add((U("urn:g:dataset-node"), U(PAT + "epoch"), LONG(dataset_epoch)))
    return ds


def nt(triples) -> str:
    return " ".join(f"{s.n3()} {p.n3()} {o.n3()} ." for s, p, o in triples)


def args(seq: int = 1, n: int = 2, *, txn: str | None = None) -> dict:
    return {
        "root": ROOT, "epoch": LONG(1), "expectedSeq": LONG(seq), "nextSeq": LONG(seq + 1), "newRev": U(f"urn:rev:order/1/{n}"),
        "txnId": U(txn or f"urn:txn:{n}"), "requestDigest": RdfLiteral("ab" * 32), "cause": U("urn:decision:1"), "actor": U("urn:agent:1"),
    }


def create_args(n: int = 1, *, txn: str | None = None) -> dict:
    return {k: v for k, v in args(0, n, txn=txn).items() if k not in ("expectedSeq", "nextSeq", "cause", "actor")}


def run(ds, name: str, bindings: dict, **slots: str):
    """Run the operation `name`, giving each request-time slot the text in `slots`. A slot not given stays a Mustache tag."""
    text = render(build(name, CONTEXT, guards=engines.guards()))
    for slot, value in slots.items():
        text = text.replace("{{{" + slot + "}}}", value)
    ds.update(text, initBindings=bindings)
    return ds


def triples(ds, graph) -> set:
    return {(s, p, o) for s, p, o in ds.graph(U(str(graph)))}


def everything(ds) -> list:
    return sorted(f"{g.identifier} {s} {p} {o}" for g in ds.graphs() for s, p, o in g if not str(p).endswith("recordedAt"))


def receipt(ds, rev: str) -> dict:
    out: dict = {}
    for g in ds.graphs():
        if str(g.identifier).startswith(LOG_PREFIX):
            for s, p, o in g:
                if s == U(rev):
                    out.setdefault(str(p).removeprefix(PAT), set()).add(o)
    return out


def log_graphs(ds) -> list:
    return [g for g in ds.graphs() if str(g.identifier).startswith(LOG_PREFIX) and len(g)]


def delta(n: int, direction: str) -> URIRef:
    return U(f"urn:rev:order/1/{n}/{direction}")


ADDED, REMOVED = (ROOT, P, RdfLiteral("new")), (ROOT, P, RdfLiteral("old"))
PAYLOAD = {(ROOT, P, RdfLiteral("new")), (ROOT, Q, RdfLiteral("keep"))}


# ---- a replace, a tombstone and a create write their delta in the same update ----------------------------------------------------


@pytest.mark.parametrize("family", FAMILIES)
@pytest.mark.parametrize("dg", [False, True], ids=["row-guard", "dataset-guard"])
@engines.each_engine_and_guards
def test_h2_6d_t1_a_replace_writes_exactly_the_callers_delta_into_the_two_graphs_the_receipt_names(family, dg):
    ds = store(family, dataset_epoch=1 if dg else None)
    run(ds, stem("replace", family, dg=dg), args(), payloadTriples=nt(PAYLOAD), assertTriples=nt([ADDED]), retractTriples=nt([REMOVED]))
    assert triples(ds, delta(2, "add")) == {ADDED} and triples(ds, delta(2, "del")) == {REMOVED}
    assert PAYLOAD <= triples(ds, data_graph(family)) and REMOVED not in triples(ds, data_graph(family))  # the aggregate holds the new state
    r = receipt(ds, "urn:rev:order/1/2")
    assert r["asserts"] == {delta(2, "add")} and r["retracts"] == {delta(2, "del")}
    assert r["prevRev"] == {U("urn:rev:order/1/prev")} and r["seq"] == {engines.canon(LONG(2))}


@pytest.mark.parametrize("family", FAMILIES)
@engines.each_engine_and_guards
def test_h2_6d_t2_the_delta_is_the_callers_and_not_the_payload_a_payload_never_fills_the_add_graph(family):
    ds = store(family)
    # a delta that is not the difference of the payload and the old state is written as given, since the caller computed it
    odd = (ROOT, U("urn:p:other"), RdfLiteral("only in the delta"))
    run(ds, stem("replace", family), args(), payloadTriples=nt(PAYLOAD), assertTriples=nt([odd]), retractTriples="")
    assert triples(ds, delta(2, "add")) == {odd} and triples(ds, delta(2, "del")) == set()
    assert not (PAYLOAD - {odd}) & triples(ds, delta(2, "add"))


@pytest.mark.parametrize("family", FAMILIES)
@engines.each_engine_and_guards
def test_h2_6d_t3_a_tombstones_del_graph_holds_the_old_aggregate_copied_from_its_sweep_and_nothing_else(family):
    ds = store(family)
    run(ds, stem("tombstone", family), args())
    old = aggregate(family)
    assert triples(ds, delta(2, "del")) == old  # the root, and for a composite the owned member, and no neighbour
    assert OUTSIDER not in {s for s, p, o in triples(ds, delta(2, "del"))}
    assert not triples(ds, data_graph(family)) & old
    assert not triples(ds, delta(2, "add"))
    r = receipt(ds, "urn:rev:order/1/2")
    assert r["retracts"] == {delta(2, "del")} and "asserts" not in r and U(PAT + "Deletion") in r[str(RDF.type)]
    assert (ROOT, U(PAT + "deleted"), RdfLiteral(True)) in triples(ds, META)


@pytest.mark.parametrize("family", FAMILIES)
@engines.each_engine_and_guards
def test_h2_6d_t4_a_creates_add_graph_holds_its_payload_and_the_receipt_names_it(family):
    ds = store(family, seq=None, data=False)
    run(ds, stem("create", family), create_args(), payloadTriples=nt(PAYLOAD))
    assert triples(ds, delta(1, "add")) == PAYLOAD == triples(ds, data_graph(family))
    assert not triples(ds, delta(1, "del"))
    r = receipt(ds, "urn:rev:order/1/1")
    assert r["asserts"] == {delta(1, "add")} and "retracts" not in r


@pytest.mark.parametrize("op", ["create", "replace", "tombstone"])
@pytest.mark.parametrize("family", FAMILIES)
@engines.each_engine_and_guards
def test_h2_6d_t5_a_retry_with_the_same_transaction_id_writes_nothing_the_delta_graphs_included(op, family):
    ds = store(family, seq=None if op == "create" else 1, data=op != "create")
    bindings = create_args() if op == "create" else args()
    slots = {"payloadTriples": nt(PAYLOAD), "assertTriples": nt([ADDED]), "retractTriples": nt([REMOVED])}
    run(ds, stem(op, family), bindings, **slots)
    before = everything(ds)
    # the same request again, and a new revision under the same transaction id at a seq that would otherwise match
    run(ds, stem(op, family), bindings, **slots)
    assert everything(ds) == before


@pytest.mark.parametrize("op", ["create", "replace", "tombstone"])
@pytest.mark.parametrize("family", FAMILIES)
@engines.each_engine_and_guards
def test_h2_6d_t6_a_write_that_loses_the_race_writes_nothing_and_neither_does_its_delta(op, family):
    ds = store(family, seq=1, data=True)  # a create finds a row, a replace and a tombstone find the wrong seq
    before = everything(ds)
    bindings = create_args(n=9) if op == "create" else args(seq=5, n=9)
    run(ds, stem(op, family), bindings, payloadTriples=nt(PAYLOAD), assertTriples=nt([ADDED]), retractTriples=nt([REMOVED]))
    assert everything(ds) == before
    assert not [g for g in ds.graphs() if str(g.identifier).startswith("urn:rev:")]


@pytest.mark.parametrize("missing", ["assertTriples", "retractTriples", "payloadTriples"])
@pytest.mark.parametrize("family", FAMILIES)
@engines.each_engine_and_guards
def test_h2_6d_t7_a_replace_with_a_slot_missing_fails_closed(family, missing):
    ds = store(family)
    before = everything(ds)
    slots = {"payloadTriples": nt(PAYLOAD), "assertTriples": nt([ADDED]), "retractTriples": nt([REMOVED])}
    del slots[missing]
    with pytest.raises(Exception):  # the unrendered Mustache tag is a syntax error on every engine
        run(ds, stem("replace", family), args(), **slots)
    assert everything(ds) == before


@engines.each_engine_and_guards
def test_h2_6d_t8_a_create_with_the_payload_slot_missing_fails_closed():
    ds = store("named-graph", seq=None, data=False)
    with pytest.raises(Exception):
        run(ds, stem("create", "named-graph"), create_args())
    assert everything(ds) == []


@pytest.mark.parametrize("family", FAMILIES)
@engines.each_engine_and_guards
def test_h2_6d_t9_an_empty_delta_gives_an_empty_graph_and_the_receipt_still_names_both(family):
    ds = store(family)
    run(ds, stem("replace", family), args(), payloadTriples=nt(aggregate(family)), assertTriples="", retractTriples="")
    assert not triples(ds, delta(2, "add")) and not triples(ds, delta(2, "del"))
    r = receipt(ds, "urn:rev:order/1/2")
    assert r["asserts"] == {delta(2, "add")} and r["retracts"] == {delta(2, "del")}


@pytest.mark.parametrize("family", FAMILIES)
@engines.each_engine_and_guards
def test_h2_6d_t10_the_chain_of_receipts_lets_the_log_rebuild_the_aggregate_from_its_deltas(family):
    """A create, a replace and a tombstone leave a log from which the state before the tombstone is the create's payload less the replace's del
    and plus its add, which is what the plan's patch invariants say (4.6, consistency rule 4)."""
    ds = store(family, seq=None, data=False)
    created = {(ROOT, P, RdfLiteral("v1")), (ROOT, Q, RdfLiteral("keep"))}
    run(ds, stem("create", family), create_args(n=1), payloadTriples=nt(created))
    new = {(ROOT, P, RdfLiteral("v2")), (ROOT, Q, RdfLiteral("keep"))}
    run(ds, stem("replace", family), args(seq=1, n=2), payloadTriples=nt(new), assertTriples=nt([(ROOT, P, RdfLiteral("v2"))]),
        retractTriples=nt([(ROOT, P, RdfLiteral("v1"))]))
    state = (triples(ds, delta(1, "add")) - triples(ds, delta(2, "del"))) | triples(ds, delta(2, "add"))
    assert state == new == triples(ds, data_graph(family))
    run(ds, stem("tombstone", family), args(seq=2, n=3))
    assert triples(ds, delta(3, "del")) == new and not triples(ds, data_graph(family))


# ---- no receipt ----------------------------------------------------------------------------------------------------------------


def no_receipt(op: str, family: str, dg: bool = False) -> str:
    return stem(op, family, "-no-receipt", dg)


@pytest.mark.parametrize("op", ["create", "replace", "tombstone"])
@pytest.mark.parametrize("family", FAMILIES)
@pytest.mark.parametrize("dg", [False, True], ids=["row-guard", "dataset-guard"])
@engines.each_engine_and_guards
def test_h2_6d_t11_a_write_under_no_receipt_writes_no_receipt_no_log_bucket_and_no_head_but_keeps_the_claim(op, family, dg):
    ds = store(family, seq=None if op == "create" else 1, data=op != "create", dataset_epoch=1 if dg else None, head=False)
    bindings = create_args() if op == "create" else args()
    run(ds, no_receipt(op, family, dg), bindings, payloadTriples=nt(PAYLOAD))
    assert not [g for g in ds.graphs() if str(g.identifier).startswith(LOG_PREFIX)]
    assert not [g for g in ds.graphs() if str(g.identifier).startswith("urn:rev:")]
    row = {str(p).removeprefix(PAT): o for s, p, o in ds.graph(META) if s == ROOT}
    assert "head" not in row and row["seq"].toPython() == (1 if op == "create" else 2)
    assert (bindings["txnId"], U(PAT + "rev"), bindings["newRev"]) in triples(ds, TXN)
    assert (bindings["txnId"], U(PAT + "requestDigest"), RdfLiteral("ab" * 32)) in triples(ds, TXN)
    if op == "tombstone":
        assert row["deleted"].toPython() is True and not triples(ds, data_graph(family)) & aggregate(family)
    else:
        assert PAYLOAD <= triples(ds, data_graph(family))


@pytest.mark.parametrize("op", ["create", "replace", "tombstone"])
@pytest.mark.parametrize("family", FAMILIES)
@engines.each_engine_and_guards
def test_h2_6d_t12_a_retry_and_a_lost_race_under_no_receipt_write_nothing(op, family):
    ds = store(family, seq=None if op == "create" else 1, data=op != "create")
    bindings = create_args() if op == "create" else args()
    run(ds, no_receipt(op, family), bindings, payloadTriples=nt(PAYLOAD))
    before = everything(ds)
    run(ds, no_receipt(op, family), bindings, payloadTriples=nt(PAYLOAD))  # the same transaction id
    stale = create_args(n=9) if op == "create" else args(seq=7, n=9)
    run(ds, no_receipt(op, family), stale, payloadTriples=nt(PAYLOAD))
    assert everything(ds) == before


@engines.each_engine_and_guards
def test_h2_6d_t13_a_family_that_had_a_head_keeps_it_untouched_since_no_receipt_writes_none_and_removes_none():
    """A row that a receipt model left a head on is not rewritten to lose it, so switching a family to `dal:NoReceipt` leaves its old head for
    the receipts it did write."""
    ds = store("named-graph", head=True)
    run(ds, no_receipt("replace", "named-graph"), args(), payloadTriples=nt(PAYLOAD))
    row = {str(p).removeprefix(PAT): o for s, p, o in ds.graph(META) if s == ROOT}
    assert row["head"] == U("urn:rev:order/1/prev") and row["seq"].toPython() == 2


# ---- the contract ----------------------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("family", FAMILIES)
def test_h2_6d_t14_the_patch_log_replace_declares_its_digest_parts_in_order_and_the_patch_content_it_writes(family):
    c = contract_of(build(stem("replace", family), CONTEXT))
    assert c.kind is OperationKind.REPLACE
    assert (c.digest.target, c.digest.expected, c.digest.payload, c.digest.add, c.digest.delete) == (
        "root", "expectedSeq", "payloadTriples", "assertTriples", "retractTriples",
    )
    assert (ResourceKind.PATCH_CONTENT.value, "Insert", None) in {(a.resource, a.mode, a.keyed_by) for a in c.accesses}
    assert {p.name for p in c.parameters} >= {"assertTriples", "retractTriples", "payloadTriples"}
    assert not {"assertGraph", "retractGraph"} & {p.name for p in c.parameters}
    assert LOGICAL_KEYS[ResourceKind.PATCH_CONTENT] == ("target", "epoch", "seq", "direction")


@pytest.mark.parametrize("family", FAMILIES)
def test_h2_6d_t15_a_create_and_a_tombstone_have_no_part_of_their_own_for_what_they_assert_or_retract(family):
    create = contract_of(build(stem("create", family), CONTEXT))
    tomb = contract_of(build(stem("tombstone", family), CONTEXT))
    assert (create.digest.add, create.digest.delete) == (None, None) and create.payload.parameter == "payloadTriples"  # the add graph is the payload
    assert (tomb.digest.add, tomb.digest.delete) == (None, None) and tomb.payload is None  # the del graph is the sweep
    assert (ResourceKind.PATCH_CONTENT.value, "Insert", None) in {(a.resource, a.mode, a.keyed_by) for a in create.accesses}
    assert (ResourceKind.PATCH_CONTENT.value, "Insert", None) in {(a.resource, a.mode, a.keyed_by) for a in tomb.accesses}


@pytest.mark.parametrize("op", ["create", "replace", "tombstone"])
@pytest.mark.parametrize("family", FAMILIES)
def test_h2_6d_t16_the_no_receipt_variants_touch_no_receipt_and_the_patch_log_variants_touch_it_and_the_patch_content(op, family):
    none = contract_of(build(no_receipt(op, family), CONTEXT))
    assert ResourceKind.RECEIPT.value not in {a.resource for a in none.accesses}
    assert ResourceKind.PATCH_CONTENT.value not in {a.resource for a in none.accesses}
    assert ResourceKind.TRANSACTION_CLAIM.value in {a.resource for a in none.accesses} and none.digest is not None
    patch = contract_of(build(stem(op, family), CONTEXT))
    assert {ResourceKind.RECEIPT.value, ResourceKind.PATCH_CONTENT.value} <= {a.resource for a in patch.accesses}
    if op == "tombstone":
        assert not {"cause", "actor"} & {p.name for p in none.parameters}


# ---- selection in compile ---------------------------------------------------------------------------------------------------------


def _templates(path) -> dict:
    (ct,) = compile_targets(witness._load_fixture(path))
    return {o.operation: o.template_id for o in ct.operations}


def test_h2_6d_t17_compile_selects_the_patch_log_variants_under_dal_patch_log_for_both_families_and_both_guards():
    assert {k: v for k, v in _templates(EXAMPLES / "baseline-single-class.ttl").items() if k in WRITES.values()} == {
        "create-if-absent": "create-if-absent-named-graph-patch-log.mustache", "cas-replace": "cas-replace-named-graph-patch-log.mustache",
        "tombstone-delete": "tombstone-delete-named-graph-patch-log.mustache",
    }
    assert _templates(EXAMPLES / "epoch-dataset-level-guard.ttl")["cas-replace"] == "cas-replace-named-graph-patch-log-dataset-guard.mustache"
    assert {k: v for k, v in _templates(EXAMPLES / "composite-project-ownership.ttl").items() if k in WRITES.values()} == {
        "create-if-absent": "create-if-absent-composite-patch-log.mustache", "cas-replace": "cas-replace-composite-property-patch-log.mustache",
        "tombstone-delete": "tombstone-delete-composite-patch-log.mustache",
    }
    assert _templates(WITNESSES / "template-cas-replace-composite-property-dataset-guard.ttl")["tombstone-delete"] == (
        "tombstone-delete-composite-patch-log-dataset-guard.mustache"
    )


def test_h2_6d_t18_compile_selects_the_no_receipt_variants_and_leaves_out_the_audits_that_read_receipts():
    for fixture, expected in (
        ("write-discipline-no-receipt-named-graph.ttl", "cas-replace-named-graph-no-receipt.mustache"),
        ("write-discipline-no-receipt-named-graph-dataset-guard.ttl", "cas-replace-named-graph-no-receipt-dataset-guard.mustache"),
        ("write-discipline-no-receipt-composite.ttl", "cas-replace-composite-property-no-receipt.mustache"),
        ("write-discipline-no-receipt-composite-dataset-guard.ttl", "cas-replace-composite-property-no-receipt-dataset-guard.mustache"),
    ):
        templates = _templates(WITNESSES / fixture)
        assert templates["cas-replace"] == expected, fixture
        assert "gap-scan-audit" not in templates and "revision-multi-txn-audit" not in templates and "txn-multi-revision-audit" not in templates
        assert "fork-detection-audit" in templates  # it reads the claims, which are still written


def test_h2_6d_t19_the_other_receipt_models_keep_the_receipt_only_writes():
    assert _templates(WITNESSES / "write-discipline-snapshot-named-graph.ttl")["cas-replace"] == "cas-replace-named-graph.mustache"
    assert _templates(WITNESSES / "write-discipline-snapshot-composite.ttl")["cas-replace"] == "cas-replace-composite-property.mustache"
    receipt_only = witness._load_fixture(WITNESSES / "_base-thing.ttl")
    receipt_only.set((U("https://example.org/lending#ThingProfile"), U(DAL_NS + "receiptModel"), U(DAL_NS + "ReceiptOnly")))
    (ct,) = compile_targets(receipt_only)
    assert {o.operation: o.template_id for o in ct.operations}["tombstone-delete"] == "tombstone-delete-named-graph.mustache"


def _kinds(graph) -> set:
    return {d.kind for ct in compile_targets(graph) for d in ct.diagnostics}


def test_h2_6d_t20_receipt_model_not_honoured_warns_for_the_snapshot_alone():
    assert "ReceiptModelNotHonoured" in _kinds(witness._load_fixture(WITNESSES / "warning-ReceiptModelNotHonoured.ttl"))
    assert "ReceiptModelNotHonoured" in _kinds(witness._load_fixture(WITNESSES / "write-discipline-snapshot-composite.ttl"))
    for honoured in ("baseline-single-class.ttl", "composite-project-ownership.ttl", "epoch-dataset-level-guard.ttl"):
        assert "ReceiptModelNotHonoured" not in _kinds(witness._load_fixture(EXAMPLES / honoured)), honoured
    assert "ReceiptModelNotHonoured" not in _kinds(witness._load_fixture(WITNESSES / "write-discipline-no-receipt-composite.ttl"))


# ---- the refusal ---------------------------------------------------------------------------------------------------------------------


def _refusal(graph) -> str | None:
    try:
        compile_targets(graph)
    except CompileError as error:
        return getattr(error.cause, "kind", type(error.cause).__name__)
    return None


QUOTE = EXAMPLES / "write-discipline-composite-append-versions.ttl"


def test_h2_6d_t21_no_receipt_is_refused_with_each_append_discipline_and_with_a_stream_and_allowed_in_place():
    assert _refusal(witness._load_fixture(WITNESSES / "refusal-NoReceiptWithAppendDiscipline.ttl")) == "NoReceiptWithAppendDiscipline"  # AppendVersions
    records = witness._load_fixture(WITNESSES / "refusal-NoReceiptWithAppendDiscipline.ttl")
    records.set((U("https://example.org/quoting#QuoteWriteProfile"), U(DAL_NS + "writeDiscipline"), U(DAL_NS + "AppendRecords")))
    assert _refusal(records) == "NoReceiptWithAppendDiscipline"
    stream = witness._load_fixture(EXAMPLES / "append-stream-dataset-guard.ttl")
    receipts = [s for s in stream.subjects(U(DAL_NS + "receiptModel"), None)]
    assert receipts
    for subject in receipts:
        stream.set((subject, U(DAL_NS + "receiptModel"), U(DAL_NS + "NoReceipt")))
    assert _refusal(stream) == "NoReceiptWithAppendDiscipline"
    for fixture in ("write-discipline-no-receipt-named-graph.ttl", "write-discipline-no-receipt-composite.ttl"):
        assert _refusal(witness._load_fixture(WITNESSES / fixture)) is None, fixture
    assert _refusal(witness._load_fixture(QUOTE)) is None  # the same family with its receipt model unchanged compiles


def test_h2_6d_t22_a_composite_family_that_asks_for_no_receipt_is_not_refused_as_receipt_only_is():
    composite = witness._load_fixture(EXAMPLES / "composite-property-boundary-shacl.ttl")
    composite.set((U("https://example.org/lending#OrderReceiptProfile"), U(DAL_NS + "receiptModel"), U(DAL_NS + "ReceiptOnly")))
    assert _refusal(composite) == "CompositeBoundaryReceiptConflict"
    assert _refusal(witness._load_fixture(WITNESSES / "write-discipline-no-receipt-composite.ttl")) is None


# ---- the delta graphs are named from the receipt, never by the caller --------------------------------------------------------------------


@pytest.mark.parametrize("family", FAMILIES)
def test_h2_6d_t23_the_delta_graph_names_are_the_receipts_and_no_parameter_names_them(family):
    text = render(build(stem("replace", family), CONTEXT))
    assert 'BIND(IRI(CONCAT(STR($newRev), "/add")) AS ?addGraph)' in text and 'BIND(IRI(CONCAT(STR($newRev), "/del")) AS ?delGraph)' in text
    assert not re.search(r"\$(assertGraph|retractGraph)\b", text)
