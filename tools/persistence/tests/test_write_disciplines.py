# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""H2.6c: the write disciplines (formal-methods track H, plan 4.9). `dal:writeDiscipline` picks how a family writes. These tests cover
the resolution and selection in `compile`, the refusal and the warning it adds, the relaxed refusal, the contract of the new
operation, and what `append-version` writes, on each engine. The builder is held to its template by the harness of `test_builders.py`.
Validation Pack: docs/developer/validation/FMH-H2-6c.md. Test IDs are H2.6c-Tn."""

from __future__ import annotations

import copy

import pytest
from rdflib import RDF, RDFS, Literal as RdfLiteral, URIRef
from rdflib.namespace import XSD

import engines
from persistence import witness
from persistence.builders import build
from persistence.compiler import CompileError, compile_targets
from persistence.contract import OperationKind, ResourceKind, contract_of
from persistence.ir_render import access_sets, render
from persistence.namespaces import DAL, FND, PAT as PAT_NS
from persistence.terms import Iri

U = URIRef
PAT = str(PAT_NS)
PREVIOUS = U(PAT + "previousVersion")
SUPERSEDED_BY = U(str(FND.supersededBy))
EXAMPLES = witness.EXAMPLES_DIR
COMPOSITE = EXAMPLES / "write-discipline-composite-append-versions.ttl"
NO_BOUNDARY = EXAMPLES / "write-discipline-noboundary-append-versions.ttl"
WITNESSES = witness.WITNESS_DIR

DATA, META, TXN = U("urn:g:quotes"), U("urn:g:meta"), U("urn:g:txn")
CONTEXT = {
    "metaGraphPrefix": Iri.encode(str(META)), "txnGraph": Iri.encode(str(TXN)), "logGraphPrefix": Iri.encode("urn:g:txlog/"),
    "dataGraph": Iri.encode(str(DATA)), "datasetGraph": Iri.encode("urn:g:dataset"), "datasetNode": Iri.encode("urn:g:dataset-node"),
}
IDENTITY = U("urn:quote:1")
LONG = lambda n: RdfLiteral(n, datatype=XSD.long)
EX = "https://example.org/quoting#"


def _p(name: str) -> URIRef:
    return U(EX + name)


V1, V2, V3, TERMS = U("urn:quote:1/v1"), U("urn:quote:1/v2"), U("urn:quote:1/v3"), U("urn:quote:1/terms")


def _nt(triples) -> str:
    return " ".join(f"<{s}> <{p}> {o.n3() if not isinstance(o, URIRef) else '<' + str(o) + '>'} ." for s, p, o in triples)


def bindings(seq: int, n: int, version: URIRef, *, txn: str | None = None, epoch: int = 1) -> dict:
    return {
        "root": IDENTITY, "epoch": LONG(epoch), "expectedSeq": LONG(seq), "nextSeq": LONG(seq + 1), "newRev": U(f"urn:rev:quote/1/{n}"),
        "txnId": U(txn or f"urn:txn:{n}"), "requestDigest": RdfLiteral("ab" * 32), "newVersion": version,
    }


def store(*, dataset_epoch: int | None = None):
    """A dataset with the identity's version row at seq 0, as bootstrap-version-row leaves it."""
    ds = engines.dataset()
    meta = ds.graph(META)
    meta.add((IDENTITY, RDF.type, U(PAT + "VersionRow")))
    meta.add((IDENTITY, U(PAT + "epoch"), LONG(1)))
    meta.add((IDENTITY, U(PAT + "seq"), LONG(0)))
    if dataset_epoch is not None:
        ds.graph(U("urn:g:dataset")).add((U("urn:g:dataset-node"), U(PAT + "epoch"), LONG(dataset_epoch)))
    return ds


def append(ds, seq: int, n: int, version: URIRef, payload, *, stem: str = "append-version", guards: bool | None = None, **kw):
    text = render(build(stem, CONTEXT, guards=engines.guards(guards))).replace("{{{payloadTriples}}}", _nt(payload))
    ds.update(text, initBindings=bindings(seq, n, version, **kw))
    return ds


def first(ds, **kw):
    return append(ds, 0, 1, V1, [(V1, RDF.type, _p("Quote")), (V1, _p("hasTerms"), TERMS), (TERMS, _p("premium"), RdfLiteral("100"))], **kw)


def second(ds, **kw):
    """A revision that restates the quote node only. The terms node is shared by reference."""
    return append(ds, 1, 2, V2, [(V2, RDF.type, _p("Quote")), (V2, _p("hasTerms"), TERMS), (V2, _p("note"), RdfLiteral("revised"))], **kw)


def triples(ds, graph: URIRef) -> set:
    return {(s, p, o) for s, p, o in ds.graph(graph)}


def everything(ds) -> list:
    return sorted(f"{g.identifier} {s} {p} {o}" for g in ds.graphs() for s, p, o in g if not str(p).endswith("recordedAt"))


def row(ds) -> dict:
    return {str(p).removeprefix(PAT): o for s, p, o in ds.graph(META) if s == IDENTITY}


# ---- what append-version writes ----------------------------------------------------------------------------------------


@engines.each_engine_and_guards
def test_h2_6c_t1_a_second_version_leaves_the_first_in_place_and_the_second_links_to_it_by_previous_version():
    ds = second(first(store()))
    data = triples(ds, DATA)
    assert (V1, RDF.type, _p("Quote")) in data and (V1, _p("hasTerms"), TERMS) in data  # the first version is whole
    assert (V2, RDF.type, _p("Quote")) in data and (V2, _p("note"), RdfLiteral("revised")) in data
    assert (V2, PREVIOUS, V1) in data
    assert not any(p == PREVIOUS and s == V1 for s, p, o in data)  # the first version follows nothing
    assert not any(p == SUPERSEDED_BY for s, p, o in data)  # persistence never writes fnd:supersededBy, the domain does (R2)


@engines.each_engine_and_guards
def test_h2_6c_t2_the_first_version_follows_nothing_and_the_row_names_the_latest_version_written():
    ds = first(store())
    assert not any(p in (PREVIOUS, SUPERSEDED_BY) for s, p, o in triples(ds, DATA))
    assert row(ds)["currentVersion"] == V1 and row(ds)["head"] == U("urn:rev:quote/1/1") and row(ds)["seq"].toPython() == 1
    ds = second(ds)
    assert row(ds)["currentVersion"] == V2 and row(ds)["head"] == U("urn:rev:quote/1/2") and row(ds)["seq"].toPython() == 2
    ds = append(ds, 2, 3, V3, [(V3, RDF.type, _p("Quote"))])
    data = triples(ds, DATA)
    assert (V2, PREVIOUS, V1) in data and (V3, PREVIOUS, V2) in data and (V3, PREVIOUS, V1) not in data  # a chain


@engines.each_engine_and_guards
def test_h2_6c_t3_each_version_names_its_receipt_and_the_receipts_chain():
    ds = second(first(store()))
    data = triples(ds, DATA)
    assert (V1, U(PAT + "revision"), U("urn:rev:quote/1/1")) in data and (V2, U(PAT + "revision"), U("urn:rev:quote/1/2")) in data
    log = [g for g in ds.graphs() if str(g.identifier).startswith("urn:g:txlog/")]
    receipts = {(s, p, o) for g in log for s, p, o in g}
    r2 = U("urn:rev:quote/1/2")
    assert (r2, U(PAT + "prevRev"), U("urn:rev:quote/1/1")) in receipts and (r2, U(PAT + "target"), IDENTITY) in receipts
    assert not any(p == U(PAT + "prevRev") for s, p, o in receipts if s == U("urn:rev:quote/1/1"))


@engines.each_engine_and_guards
def test_h2_6c_t4_a_member_the_caller_does_not_restate_is_still_reachable_from_the_new_version():
    ds = second(first(store()))
    data = triples(ds, DATA)
    assert (TERMS, _p("premium"), RdfLiteral("100")) in data  # written once, by the first version
    assert (V2, _p("hasTerms"), TERMS) in data
    reachable = {o for s, p, o in data if s == V2 and p == _p("hasTerms")}
    assert {o for s, p, o in data if s in reachable and p == _p("premium")} == {RdfLiteral("100")}
    assert sum(1 for s, p, o in data if s == TERMS) == 1  # nothing copied


@engines.each_engine_and_guards
def test_h2_6c_t5_a_retry_with_the_same_transaction_id_writes_nothing():
    ds = second(first(store()))
    before = everything(ds)
    # the same request again, and the same transaction id under a seq that would otherwise match
    second(ds)
    append(ds, 2, 3, V3, [(V3, RDF.type, _p("Quote"))], txn="urn:txn:2")
    assert everything(ds) == before


@engines.each_engine_and_guards
def test_h2_6c_t6_a_stale_seq_writes_nothing():
    ds = first(store())
    before = everything(ds)
    append(ds, 0, 9, V2, [(V2, RDF.type, _p("Quote"))])  # the row is at 1
    append(ds, 5, 10, V2, [(V2, RDF.type, _p("Quote"))])  # ahead of the row
    assert everything(ds) == before


@engines.each_engine_and_guards
def test_h2_6c_t7_a_row_that_does_not_exist_or_is_marked_deleted_writes_nothing():
    ds = engines.dataset()
    first(ds)
    assert everything(ds) == []
    ds = store()
    ds.graph(META).add((IDENTITY, U(PAT + "deleted"), RdfLiteral(True)))
    first(ds)
    assert not triples(ds, DATA)


@engines.each_engine_and_guards
def test_h2_6c_t8_the_dataset_guard_variant_writes_only_while_the_dataset_epoch_matches():
    stem = "append-version-dataset-guard"
    ds = store(dataset_epoch=2)
    first(ds, stem=stem)  # the dataset is at epoch 2 and the request says 1
    assert not triples(ds, DATA)
    ds = store(dataset_epoch=1)
    second(first(ds, stem=stem), stem=stem)
    assert (V2, PREVIOUS, V1) in triples(ds, DATA) and row(ds)["currentVersion"] == V2
    ds = store(dataset_epoch=1)
    ds.graph(META).remove((IDENTITY, U(PAT + "epoch"), LONG(1)))
    ds.graph(META).add((IDENTITY, U(PAT + "epoch"), LONG(0)))  # a row behind the dataset is rebased by the write
    first(ds, stem=stem)
    assert row(ds)["epoch"].toPython() == 1 and row(ds)["currentVersion"] == V1


@engines.each_engine_and_guards
def test_h2_6c_t9_a_missing_parameter_writes_nothing_where_the_guard_is_on():
    ds = store()
    text = render(build("append-version", CONTEXT, guards=True)).replace("{{{payloadTriples}}}", _nt([(V1, RDF.type, _p("Quote"))]))
    partial = {k: v for k, v in bindings(0, 1, V1).items() if k != "newVersion"}
    before = everything(ds)
    ds.update(text, initBindings=partial)
    assert everything(ds) == before


# ---- the operation as data ---------------------------------------------------------------------------------------------


def test_h2_6c_t10_append_version_never_deletes_from_the_data_graph_and_reads_and_writes_the_four_resources():
    operation = build("append-version", CONTEXT)
    sets = access_sets(operation)
    assert not any(a.mode == "Delete" and a.role == "data" for a in sets.writes), "no sweep and no delete"
    c = contract_of(operation)
    assert c.kind is OperationKind.APPEND_VERSION and c.version == 4  # 2 since R2 (pat:previousVersion, H2.6d), 3 since its NOT EXISTS names its graph (H2.6g), 4 since the store vocabulary moved to its published namespace (OR-6)
    by_resource = {(a.resource, a.mode) for a in c.accesses}
    assert (ResourceKind.AGGREGATE.value, "Insert") in by_resource  # the version
    assert (ResourceKind.AGGREGATE.value, "Delete") not in by_resource
    assert {(ResourceKind.VERSION_ROW.value, m) for m in ("Insert", "Delete", "PointRead")} <= by_resource
    assert (ResourceKind.RECEIPT.value, "Insert") in by_resource and (ResourceKind.TRANSACTION_CLAIM.value, "Insert") in by_resource
    assert c.payload is not None and c.payload.parameter == "payloadTriples"
    assert c.digest is not None and (c.digest.target, c.digest.expected, c.digest.payload) == ("root", "expectedSeq", "payloadTriples")
    assert {p.name for p in c.parameters} == {
        "root", "epoch", "expectedSeq", "nextSeq", "newRev", "txnId", "requestDigest", "newVersion", "payloadTriples",
    }


# ---- resolution and selection ------------------------------------------------------------------------------------------


def _operations(path, *, remove=(), add=""):
    graph = witness._load_fixture(path)
    for triple in remove:
        graph.remove(triple)
    if add:
        graph.parse(data=add, format="turtle")
    return graph


def _names(graph) -> list:
    (ct,) = compile_targets(graph)
    return [o.operation for o in ct.operations]


WRITES = ("create-if-absent", "cas-replace", "tombstone-delete", "append", "append-version", "bootstrap-version-row")


def test_h2_6c_t11_the_discipline_resolves_in_place_when_absent_and_every_example_that_declares_none_compiles_as_before():
    count = 0
    for path in sorted(EXAMPLES.glob("*.ttl")):
        try:
            targets = compile_targets(witness._load_fixture(path))
        except CompileError:
            continue
        for ct in targets:
            declared = ct.dimensions["writeDiscipline"]
            if path.name.startswith("write-discipline-"):
                assert declared.value == "AppendVersions" or str(declared.value).endswith("AppendVersions")
            else:
                assert declared.value == "InPlace" and declared.won_by is None
                assert "append-version" not in {o.operation for o in ct.operations}
                count += 1
    assert count >= 20


def test_h2_6c_t12_append_versions_selects_a_bootstrap_and_an_append_version_and_no_create_replace_or_tombstone():
    names = _names(witness._load_fixture(COMPOSITE))
    writes = [n for n in names if n in WRITES]
    assert writes == ["bootstrap-version-row", "append-version"]
    assert [n for n in _names(witness._load_fixture(NO_BOUNDARY)) if n in WRITES] == ["bootstrap-version-row", "append-version"]


def test_h2_6c_t13_the_guard_scope_picks_the_variant_of_the_write():
    def templates(path):
        (ct,) = compile_targets(witness._load_fixture(path))
        return {o.operation: o.template_id for o in ct.operations}

    assert templates(COMPOSITE)["append-version"] == "append-version-dataset-guard"
    assert templates(NO_BOUNDARY)["append-version"] == "append-version-dataset-guard"
    (ct,) = compile_targets(witness._load_fixture(WITNESSES / "write-discipline-append-versions-row-guard.ttl"))
    assert {o.operation: o.template_id for o in ct.operations}["append-version"] == "append-version"


def test_h2_6c_t14_append_records_selects_the_append_form_and_in_place_selects_the_replace_family():
    names = _names(witness._load_fixture(WITNESSES / "write-discipline-append-records-composite.ttl"))
    assert [n for n in names if n in WRITES] == ["bootstrap-version-row", "append"]
    graph = witness._load_fixture(WITNESSES / "warning-VersionedClassWrittenInPlace.ttl")
    assert [n for n in _names(graph) if n in WRITES] == ["create-if-absent", "cas-replace", "tombstone-delete"]


def test_h2_6c_t15_the_append_versions_binding_names_the_data_graph_and_no_owned_path():
    (ct,) = compile_targets(witness._load_fixture(COMPOSITE))
    (op,) = [o for o in ct.operations if o.operation == "append-version"]
    names = {b.name for b in op.bindings}
    assert "dataGraph" in names and "ownedPath" not in names


# ---- the refusal -------------------------------------------------------------------------------------------------------


def _refusal(graph) -> str | None:
    try:
        compile_targets(graph)
    except CompileError as error:
        return getattr(error.cause, "kind", type(error.cause).__name__)
    return None


def test_h2_6c_t16_append_versions_is_refused_for_a_named_graph_family_for_a_concurrency_that_is_not_optimistic_and_for_no_boundary_without_a_data_graph():
    assert _refusal(witness._load_fixture(WITNESSES / "refusal-AppendVersionsUnsupported.ttl")) == "AppendVersionsUnsupported"
    not_optimistic = _operations(
        COMPOSITE, remove=[(_p("QuoteConcurrencyProfile"), DAL.concurrencyProfile, DAL.Optimistic)],
        add="@prefix dal: <https://www.nebularis.org/neuro-semantic/lattice/persistence#> . "
            "@prefix ex: <https://example.org/quoting#> . ex:QuoteConcurrencyProfile dal:concurrencyProfile dal:ProvidedConcurrency .",
    )
    assert _refusal(not_optimistic) == "AppendVersionsUnsupported"
    no_graph = _operations(NO_BOUNDARY, remove=[(_ox("OfferBoundaryProfile"), DAL.dataGraph, None)])
    assert _refusal(no_graph) == "AppendVersionsUnsupported"
    assert _refusal(witness._load_fixture(NO_BOUNDARY)) is None


def _ox(name: str) -> URIRef:
    return U("https://example.org/offers#" + name)


def test_h2_6c_t17_a_no_boundary_family_without_a_value_guard_is_refused_in_place_and_allowed_when_it_appends_versions():
    in_place = _operations(NO_BOUNDARY, remove=[(_ox("OfferWriteProfile"), None, None)])
    assert _refusal(in_place) == "NoBoundaryConcurrencyConflict"
    assert _refusal(witness._load_fixture(NO_BOUNDARY)) is None


# ---- the relaxed refusal ------------------------------------------------------------------------------------------------


def test_h2_6c_t18_a_composite_family_with_receipt_only_is_refused_in_place_and_allowed_when_it_appends_versions_or_records():
    base = witness._load_fixture(COMPOSITE)
    assert _refusal(base) is None  # AppendVersions, ReceiptOnly
    assert _refusal(witness._load_fixture(WITNESSES / "write-discipline-append-records-composite.ttl")) is None
    in_place = _operations(COMPOSITE, remove=[(_p("QuoteWriteProfile"), None, None)])
    assert _refusal(in_place) == "CompositeBoundaryReceiptConflict"
    assert _refusal(witness._load_fixture(EXAMPLES / "invalid-compositeboundary-receiptonly.ttl")) == "CompositeBoundaryReceiptConflict"


# ---- the warning --------------------------------------------------------------------------------------------------------

FND_VERSION = U(str(FND.Versioned))


def _warnings(graph) -> set:
    return {d.kind for ct in compile_targets(graph) for d in ct.diagnostics}


def test_h2_6c_t19_a_versioned_class_written_in_place_is_warned_and_a_class_that_appends_or_is_not_versioned_is_not():
    in_place = witness._load_fixture(WITNESSES / "warning-VersionedClassWrittenInPlace.ttl")
    assert "VersionedClassWrittenInPlace" in _warnings(in_place)
    assert "VersionedClassWrittenInPlace" not in _warnings(witness._load_fixture(COMPOSITE))  # AppendVersions
    assert "VersionedClassWrittenInPlace" not in _warnings(witness._load_fixture(WITNESSES / "write-discipline-append-records-composite.ttl"))
    plain = witness._load_fixture(WITNESSES / "_base-thing.ttl")
    assert "VersionedClassWrittenInPlace" not in _warnings(plain)


def test_h2_6c_t20_the_warning_finds_a_version_through_a_chain_of_subclasses_and_names_the_class_and_the_remedy():
    graph = witness._load_fixture(WITNESSES / "_base-thing.ttl")
    thing, middle = U("https://example.org/lending#Thing"), U("https://example.org/lending#Middle")
    graph.add((thing, RDFS.subClassOf, middle))
    graph.add((middle, RDFS.subClassOf, FND_VERSION))
    (ct,) = compile_targets(graph)
    (diagnostic,) = [d for d in ct.diagnostics if d.kind == "VersionedClassWrittenInPlace"]
    assert diagnostic.severity == "WARNING" and "dal:AppendVersions" in diagnostic.message and diagnostic.target == str(ct.target)
