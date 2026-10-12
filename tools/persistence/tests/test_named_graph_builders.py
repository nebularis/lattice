# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""H2.3: the named-graph row writers, run on rdflib, and the caller-named graph (ADR-A123, second addendum of
2026-10-12). The ports themselves are held to their templates by the harness of test_builders.py. Validation
Pack: docs/developer/validation/FMH-H2-3.md. Test IDs are H2.3-Tn."""

from __future__ import annotations

import re
import urllib.parse

import pytest

import engines
from rdflib import RDF, XSD, Dataset, Literal as RdfLiteral, URIRef

from persistence.builders import build
from persistence.ir import Kind, ParamRef, TermGuard
from persistence.ir_render import _Out, render
from persistence.terms import Iri, Literal

from test_builders import CONTEXT as BASE, LONG, PAT, _first, _meta

CONTEXT = {
    **BASE,
    "graphPrefix": Literal.encode("urn:g:orders/"),
    "graphSuffix": Literal.encode(""),
}
LOG = "urn:g:txlog/"
ROOT = URIRef("urn:root:1")
OTHER = URIRef("urn:root:2")
PAYLOAD = '<urn:root:1> <urn:p> "v1" .'
PAYLOAD2 = '<urn:root:1> <urn:p> "v2" .'
SLOT = "{{{payloadTriples}}}"


def graph_of(root: URIRef) -> URIRef:
    return URIRef("urn:g:orders/" + urllib.parse.quote(str(root), safe="-_.~"))


def create_args(root=ROOT, n=1) -> dict:
    return {"root": root, "epoch": LONG(3), "newRev": URIRef(f"urn:rev:{root}/1"), "txnId": URIRef(f"urn:txn:create{n}"),
            "requestDigest": RdfLiteral("cd" * 32)}


def replace_args(root=ROOT, expected=1, n=1) -> dict:
    return {"root": root, "epoch": LONG(3), "expectedSeq": LONG(expected), "nextSeq": LONG(expected + 1),
            "newRev": URIRef(f"urn:rev:{root}/{expected + 1}"), "txnId": URIRef(f"urn:txn:replace{n}"),
            "requestDigest": RdfLiteral("ef" * 32)}


def tombstone_args(root=ROOT, expected=1, n=1) -> dict:
    return {**replace_args(root, expected, n), "cause": URIRef("urn:cause:gdpr"), "actor": URIRef("urn:actor:admin")}


def run(stem: str, ds: Dataset, args: dict, *, payload: str = PAYLOAD, guards: bool | None = None, names: str = "query") -> Dataset:
    text = render(build(stem, CONTEXT, guards=engines.guards(guards), graph_names=names)).replace(SLOT, payload)
    ds.update(text, initBindings=args)
    return ds


def quads(ds: Dataset, graph: URIRef) -> set:
    return {(str(s), str(p), str(o)) for s, p, o in ds.graph(graph)}


def everything(ds: Dataset) -> set:
    return {(str(g.identifier), str(s), str(p), str(o)) for g in ds.graphs() for s, p, o in g}


def created(root=ROOT, *, dataset_epoch: int | None = None) -> Dataset:
    ds = engines.dataset()
    if dataset_epoch is not None:
        ds.graph(URIRef("urn:g:dataset")).add((URIRef("urn:g:dataset-node"), URIRef(PAT + "epoch"), LONG(dataset_epoch)))
    stem = "create-if-absent-named-graph" + ("-dataset-guard" if dataset_epoch is not None else "")
    return run(stem, ds, create_args(root), payload=PAYLOAD.replace("urn:root:1", str(root)))


# ---- create-if-absent ------------------------------------------------------------------------------------------


@engines.each_engine
def test_h2_3_t3_a_create_writes_the_payload_into_the_roots_own_graph_and_a_version_row_at_seq_1():
    ds = created()
    assert quads(ds, graph_of(ROOT)) == {("urn:root:1", "urn:p", "v1")}
    meta = _meta(ds)
    assert (str(ROOT), "seq", "1") in meta and (str(ROOT), "head", f"urn:rev:{ROOT}/1") in meta and (str(ROOT), "epoch", "3") in meta
    assert (URIRef("urn:txn:create1"), URIRef(PAT + "rev"), URIRef(f"urn:rev:{ROOT}/1")) in ds.graph(URIRef("urn:g:txn"))
    receipts = [g for g in ds.graphs() if str(g.identifier).startswith(LOG)]
    assert len(receipts) == 1 and (URIRef(f"urn:rev:{ROOT}/1"), URIRef(PAT + "target"), ROOT) in receipts[0]


@engines.each_engine
def test_h2_3_t4_a_second_create_of_the_same_root_writes_nothing():
    ds = created()
    before = everything(ds)
    run("create-if-absent-named-graph", ds, create_args(n=2), payload=PAYLOAD2)
    assert everything(ds) == before


def test_h2_3_t5_without_a_root_nothing_is_written_and_without_the_guard_a_claim_and_receipt_are():
    args = {k: v for k, v in create_args().items() if k != "root"}
    assert everything(run("create-if-absent-named-graph", engines.dataset(), args)) == set()
    unguarded = run("create-if-absent-named-graph", engines.dataset(), args, guards=False)
    written = everything(unguarded)
    # what rdflib does, recorded: a claim and the part of a receipt that needs no root, no row and no payload
    assert any(g == "urn:g:txn" for g, *_ in written)
    assert not any(g == "urn:g:meta" for g, *_ in written) and not any(g.startswith("urn:g:orders/") for g, *_ in written)


@engines.each_engine
def test_h2_3_t6_a_create_under_the_dataset_guard_needs_the_matching_dataset_epoch():
    assert quads(created(dataset_epoch=3), graph_of(ROOT)) == {("urn:root:1", "urn:p", "v1")}
    ds = engines.dataset()
    ds.graph(URIRef("urn:g:dataset")).add((URIRef("urn:g:dataset-node"), URIRef(PAT + "epoch"), LONG(4)))
    run("create-if-absent-named-graph-dataset-guard", ds, create_args())
    assert quads(ds, graph_of(ROOT)) == set() and _meta(ds) == set()


# ---- unconditional-write -----------------------------------------------------------------------------------------


@engines.each_engine
def test_h2_3_t7_an_unconditional_write_writes_into_the_roots_graph_and_nowhere_else():
    ds = run("unconditional-write", engines.dataset(), {"root": ROOT})
    assert everything(ds) == {(str(graph_of(ROOT)), "urn:root:1", "urn:p", "v1")}


def test_h2_3_t8_a_literal_root_builds_a_graph_name_only_without_the_guard_and_a_missing_root_never_names_a_graph():
    assert everything(run("unconditional-write", engines.dataset(), {"root": RdfLiteral("urn:root:1")})) == set()
    unguarded = run("unconditional-write", engines.dataset(), {"root": RdfLiteral("urn:root:1")}, guards=False)
    assert quads(unguarded, graph_of(ROOT)) == {("urn:root:1", "urn:p", "v1")}  # a name built from a literal's text
    # rdflib, recorded: with no root and no guard it writes the payload into a fresh blank-node graph, where the
    # specification skips a quad whose graph is unbound. No graph with an IRI is touched.
    unnamed = everything(run("unconditional-write", engines.dataset(), {}, guards=False))
    assert not any(graph.startswith("urn:") for graph, *_ in unnamed)


# ---- cas-replace ---------------------------------------------------------------------------------------------------


@engines.each_engine
def test_h2_3_t9_a_replace_leaves_exactly_the_payload_and_moves_the_row():
    ds = created()
    run("cas-replace-named-graph", ds, replace_args(), payload=PAYLOAD2)
    assert quads(ds, graph_of(ROOT)) == {("urn:root:1", "urn:p", "v2")}
    meta = _meta(ds)
    assert (str(ROOT), "seq", "2") in meta and (str(ROOT), "seq", "1") not in meta
    assert (str(ROOT), "head", f"urn:rev:{ROOT}/2") in meta and (str(ROOT), "head", f"urn:rev:{ROOT}/1") not in meta


@engines.each_engine
def test_h2_3_t10_a_replace_at_the_wrong_seq_writes_nothing():
    ds = created()
    before = everything(ds)
    run("cas-replace-named-graph", ds, replace_args(expected=7), payload=PAYLOAD2)
    assert everything(ds) == before


@engines.each_engine
def test_h2_3_t11_the_first_replace_after_a_create_chains_its_receipt_to_the_create():
    ds = created()
    run("cas-replace-named-graph", ds, replace_args(), payload=PAYLOAD2)
    receipts = next(g for g in ds.graphs() if str(g.identifier).startswith(LOG))
    assert (URIRef(f"urn:rev:{ROOT}/2"), URIRef(PAT + "prevRev"), URIRef(f"urn:rev:{ROOT}/1")) in receipts


@engines.each_engine
def test_h2_3_t12_a_replace_without_asserted_and_retracted_graphs_writes_the_receipt_without_those_two_triples():
    ds = created()
    run("cas-replace-named-graph", ds, replace_args(), payload=PAYLOAD2)
    receipts = next(g for g in ds.graphs() if str(g.identifier).startswith(LOG))
    assert not list(receipts.objects(URIRef(f"urn:rev:{ROOT}/2"), URIRef(PAT + "asserts")))
    given = {**replace_args(n=2), "expectedSeq": LONG(2), "nextSeq": LONG(3), "newRev": URIRef(f"urn:rev:{ROOT}/3"),
             "assertGraph": URIRef("urn:g:added"), "retractGraph": URIRef("urn:g:removed")}
    run("cas-replace-named-graph", ds, given, payload=PAYLOAD)
    receipts = next(g for g in ds.graphs() if str(g.identifier).startswith(LOG))
    assert (URIRef(f"urn:rev:{ROOT}/3"), URIRef(PAT + "asserts"), URIRef("urn:g:added")) in receipts


@engines.each_engine
def test_h2_3_t13_a_replace_of_one_root_leaves_another_roots_graph_alone():
    ds = created()
    run("create-if-absent-named-graph", ds, create_args(OTHER, n=3), payload='<urn:root:2> <urn:p> "other" .')
    other = quads(ds, graph_of(OTHER))
    run("cas-replace-named-graph", ds, replace_args(), payload=PAYLOAD2)
    assert quads(ds, graph_of(OTHER)) == other == {("urn:root:2", "urn:p", "other")}


@engines.each_engine
def test_h2_3_t14_a_replay_of_a_replace_changes_nothing():
    ds = created()
    run("cas-replace-named-graph", ds, replace_args(), payload=PAYLOAD2)
    before = everything(ds)
    run("cas-replace-named-graph", ds, replace_args(), payload=PAYLOAD2)
    assert everything(ds) == before


@engines.each_engine
def test_h2_3_t15_a_replace_under_the_dataset_guard_rebases_the_rows_epoch():
    ds = created(dataset_epoch=3)
    ds.graph(URIRef("urn:g:dataset")).remove((None, None, None))
    ds.graph(URIRef("urn:g:dataset")).add((URIRef("urn:g:dataset-node"), URIRef(PAT + "epoch"), LONG(5)))
    args = {**replace_args(), "epoch": LONG(5)}
    run("cas-replace-named-graph-dataset-guard", ds, args, payload=PAYLOAD2)
    meta = _meta(ds)
    assert (str(ROOT), "epoch", "5") in meta and (str(ROOT), "epoch", "3") not in meta and (str(ROOT), "seq", "2") in meta


def test_h2_3_t16_a_replace_with_no_root_writes_nothing_where_without_the_guard_it_writes_every_aggregate_at_that_seq():
    def two() -> Dataset:
        ds = created()
        run("create-if-absent-named-graph", ds, create_args(OTHER, n=3), payload='<urn:root:2> <urn:p> "other" .')
        return ds

    args = {k: v for k, v in replace_args().items() if k != "root"}
    guarded = two()
    before = everything(guarded)
    run("cas-replace-named-graph", guarded, args, payload=PAYLOAD2)
    assert everything(guarded) == before
    unguarded = two()
    run("cas-replace-named-graph", unguarded, args, payload=PAYLOAD2, guards=False)
    assert everything(unguarded) != before
    assert (str(ROOT), "seq", "2") in _meta(unguarded) and (str(OTHER), "seq", "2") in _meta(unguarded)


# ---- tombstone-delete --------------------------------------------------------------------------------------------


@engines.each_engine
def test_h2_3_t17_a_tombstone_empties_the_graph_marks_the_row_and_writes_a_deletion_receipt_with_cause_and_actor():
    ds = created()
    run("tombstone-delete-named-graph", ds, tombstone_args())
    assert quads(ds, graph_of(ROOT)) == set()
    assert (str(ROOT), "deleted", "true") in _meta(ds) and (str(ROOT), "seq", "2") in _meta(ds)
    receipts = next(g for g in ds.graphs() if str(g.identifier).startswith(LOG))
    rev = URIRef(f"urn:rev:{ROOT}/2")
    assert (rev, RDF.type, URIRef(PAT + "Deletion")) in receipts
    assert (rev, URIRef(PAT + "cause"), URIRef("urn:cause:gdpr")) in receipts and (rev, URIRef(PAT + "actor"), URIRef("urn:actor:admin")) in receipts


@engines.each_engine
def test_h2_3_t18_after_a_tombstone_a_replace_writes_nothing_and_a_replay_of_the_tombstone_changes_nothing():
    ds = created()
    run("tombstone-delete-named-graph", ds, tombstone_args())
    before = everything(ds)
    run("cas-replace-named-graph", ds, replace_args(expected=2, n=2), payload=PAYLOAD2)
    run("tombstone-delete-named-graph", ds, tombstone_args())
    assert everything(ds) == before


@engines.each_engine
def test_h2_3_t19_a_tombstone_under_the_dataset_guard_needs_the_matching_dataset_epoch():
    ds = created(dataset_epoch=3)
    ds.graph(URIRef("urn:g:dataset")).remove((None, None, None))
    ds.graph(URIRef("urn:g:dataset")).add((URIRef("urn:g:dataset-node"), URIRef(PAT + "epoch"), LONG(4)))
    before = everything(ds)
    run("tombstone-delete-named-graph-dataset-guard", ds, tombstone_args())
    assert everything(ds) == before
    ds2 = created(dataset_epoch=3)
    run("tombstone-delete-named-graph-dataset-guard", ds2, tombstone_args())
    assert quads(ds2, graph_of(ROOT)) == set() and (str(ROOT), "deleted", "true") in _meta(ds2)


@pytest.mark.parametrize("missing", ["cause", "actor", "root", "expectedSeq", "requestDigest"])
def test_h2_3_t20_a_tombstone_with_a_required_parameter_missing_writes_nothing(missing):
    ds = created()
    before = everything(ds)
    run("tombstone-delete-named-graph", ds, {k: v for k, v in tombstone_args().items() if k != missing})
    assert everything(ds) == before


# ---- the caller-named graph --------------------------------------------------------------------------------------

NAMING = ["create-if-absent-named-graph", "cas-replace-named-graph", "tombstone-delete-named-graph", "unconditional-write"]


def _normalised(ds: Dataset) -> set:
    return {(g, s, p, "<time>" if p.endswith("recordedAt") else o) for g, s, p, o in everything(ds)}


@engines.each_engine
def test_h2_3_t21_with_the_right_g_a_replace_gives_the_same_result_as_the_query_naming_the_graph():
    by_query = created()
    run("cas-replace-named-graph", by_query, replace_args(), payload=PAYLOAD2)
    by_caller = created()
    run("cas-replace-named-graph", by_caller, {**replace_args(), "g": graph_of(ROOT)}, payload=PAYLOAD2, names="caller")
    assert _normalised(by_caller) == _normalised(by_query)


@pytest.mark.parametrize("stem, args", [
    ("create-if-absent-named-graph", create_args()),
    ("tombstone-delete-named-graph", tombstone_args()),
    ("unconditional-write", {"root": ROOT}),
])
def test_h2_3_t22_with_the_right_g_each_naming_operation_equals_its_default_form(stem, args):
    def prepared() -> Dataset:
        return engines.dataset() if stem != "tombstone-delete-named-graph" else created()

    default = run(stem, prepared(), args)
    caller = run(stem, prepared(), {**args, "g": graph_of(ROOT)}, names="caller")
    assert _normalised(caller) == _normalised(default)


@pytest.mark.parametrize("wrong", [URIRef("urn:g:orders/other"), URIRef("urn:g:orders/urn:root:1"), RdfLiteral("urn:g:orders/urn%3Aroot%3A1")])
def test_h2_3_t23_a_wrong_g_writes_nothing_under_the_guard_and_into_that_graph_without_it(wrong):
    ds = engines.dataset()
    run("unconditional-write", ds, {"root": ROOT, "g": wrong}, names="caller")
    assert everything(ds) == set()
    if isinstance(wrong, URIRef):
        unguarded = run("unconditional-write", engines.dataset(), {"root": ROOT, "g": wrong}, guards=False, names="caller")
        assert quads(unguarded, wrong) == {("urn:root:1", "urn:p", "v1")}


def test_h2_3_t24_a_replace_with_a_wrong_g_leaves_the_stored_aggregate_alone():
    ds = created()
    before = everything(ds)
    run("cas-replace-named-graph", ds, {**replace_args(), "g": graph_of(OTHER)}, payload=PAYLOAD2, names="caller")
    assert everything(ds) == before


def _substitute(text: str, args: dict) -> str:
    """What a caller with no initial-binding API does: put each parameter's term in the text."""
    for name, value in sorted(args.items(), key=lambda kv: -len(kv[0])):
        term = value.n3()
        text = re.sub(r"\$" + name + r"\b", lambda _: term, text)
    return text


@engines.each_engine
def test_h2_3_t25_a_caller_that_substitutes_text_gets_a_constant_graph_and_the_same_result():
    args = {**replace_args(), "g": graph_of(ROOT)}
    text = render(build("cas-replace-named-graph", CONTEXT, guards=engines.guards(), graph_names="caller")).replace(SLOT, PAYLOAD2)
    substituted = _substitute(text, args)
    assert f"GRAPH <{graph_of(ROOT)}>" in substituted and "GRAPH ?g" not in substituted and "GRAPH $g" not in substituted
    assert set(re.findall(r"\$\w+", substituted)) == {"$assertGraph", "$retractGraph"}  # the optional parameters nobody gave
    ds = created()
    ds.update(substituted)
    reference = created()
    run("cas-replace-named-graph", reference, replace_args(), payload=PAYLOAD2)
    assert _normalised(ds) == _normalised(reference)


def test_h2_3_t26_the_caller_named_form_declares_g_and_the_guard_checks_it_after_its_type_test():
    caller = build("cas-replace-named-graph", CONTEXT, graph_names="caller")
    default = build("cas-replace-named-graph", CONTEXT)
    g = next(p for p in caller.params if p.name == "g")
    assert g.kind is Kind.IRI and g.equals is not None and not any(p.name == "g" for p in default.params)
    conjunct = _Out().expr(TermGuard(ParamRef("g"), g.equals))
    assert "ISIRI($g) && " + conjunct in render(caller)
    off = render(build("cas-replace-named-graph", CONTEXT, guards=False, graph_names="caller"))
    assert "sameTerm" not in off and "ISIRI" not in off  # guards off drops the equals check with the type tests
    assert "GRAPH ?g" not in render(caller) and "GRAPH $g" in render(caller)


def test_h2_3_t27_the_guard_names_the_graph_by_the_rule_of_decision_8():
    text = render(build("unconditional-write", CONTEXT, graph_names="caller"))
    assert "sameTerm($g, IRI(CONCAT(\"urn:g:orders/\", ENCODE_FOR_URI(STR($root)), \"\")))" in text


def test_h2_3_t28_graph_names_changes_only_the_operations_that_name_a_graph():
    for stem in ("bootstrap-version-row", "append-event"):
        _, _, _, context = _first(stem)
        assert render(build(stem, context)) == render(build(stem, context, graph_names="caller"))
    with pytest.raises(ValueError):
        build("unconditional-write", CONTEXT, graph_names="neither")
    _, _, _, append_context = _first("append-event")
    with pytest.raises(ValueError):
        build("append-event", append_context, graph_names="neither")


# ---- the shipped form and the golden text -------------------------------------------------------------------------

GOLDEN = __import__("pathlib").Path(__file__).parent / "fixtures" / "ir"


def test_h2_3_t29_the_default_and_caller_named_forms_of_a_replace_are_pinned_and_differ_in_listed_lines_only():
    default = render(build("cas-replace-named-graph", CONTEXT))
    caller = render(build("cas-replace-named-graph", CONTEXT, graph_names="caller"))
    assert default == (GOLDEN / "replace-named-graph.rq").read_text(encoding="utf-8")
    assert caller == (GOLDEN / "replace-named-graph-caller.rq").read_text(encoding="utf-8")
    changed = [line.strip() for line in set(caller.splitlines()) ^ set(default.splitlines())]
    assert sorted(changed) == sorted([
        "GRAPH $g { ?s ?p ?o }", "GRAPH $g { {{{payloadTriples}}} }", "OPTIONAL { GRAPH $g { ?s ?p ?o } }",
        "GRAPH ?g { ?s ?p ?o }", "GRAPH ?g { {{{payloadTriples}}} }", "OPTIONAL { GRAPH ?g { ?s ?p ?o } }",
        'BIND(IRI(CONCAT("urn:g:orders/", ENCODE_FOR_URI(STR($root)), "")) AS ?g)',
        next(line.strip() for line in caller.splitlines() if line.strip().startswith("FILTER(")),
        next(line.strip() for line in default.splitlines() if line.strip().startswith("FILTER(")),
    ])


def _compiled_with(stem: str):
    from test_builders import _corpus

    name = _first(stem)[0]
    return next(c for n, c in _corpus() if n == name)


def test_h2_3_t30_instantiate_renders_the_caller_named_form_on_request():
    from persistence.instantiate import instantiate_by_target

    stem = "unconditional-write"
    default = next(iter(instantiate_by_target(_compiled_with(stem)).values()))
    caller = next(iter(instantiate_by_target(_compiled_with(stem), graph_names="caller").values()))
    assert default != caller
    text = next(t for t in caller.values() if "GRAPH $g" in t)
    assert "sameTerm($g" in text


def test_h2_3_t31_the_command_line_flag_gives_the_caller_named_form(tmp_path):
    from persistence.cli import main

    compiled = tmp_path / "compiled.ttl"
    _compiled_with("unconditional-write").serialize(compiled, format="turtle")
    assert main(["instantiate", str(compiled), "--out", str(tmp_path / "default")]) == 0
    assert main(["instantiate", str(compiled), "--out", str(tmp_path / "caller"), "--caller-graph-names"]) == 0
    default = "".join(p.read_text(encoding="utf-8") for p in (tmp_path / "default").rglob("*.rq"))
    caller = "".join(p.read_text(encoding="utf-8") for p in (tmp_path / "caller").rglob("*.rq"))
    assert "GRAPH $g" not in default and "GRAPH $g" in caller


# ---- the roles, written down apart from the table that assigns them -------------------------------------------------
# GRAPH_ROLES decides a role, and a test that asks the table for the answer cannot find a wrong entry (found by a
# probe that swapped the roles of the metadata and transaction graphs). This one says what each graph is.

_BINDING_ROLES = {"metaGraphPrefix": "meta", "txnGraph": "txn", "datasetGraph": "dataset", "dataGraph": "data",
                  "keysGraph": "keys", "keyQuarantineGraph": "quarantine", "retentionGraph": "retention", "pinnedGraph": "pinned"}
_VARIABLE_ROLES = {"?g": "data", "$g": "data", "?logGraph": "log", "?logGraph2": "log", "?log": "log", "?eventGraph": "event"}


def test_h2_3_t32_every_graph_of_every_ported_operation_has_the_role_its_name_says():
    from persistence.ir_render import access_sets
    from test_builders import _ported

    seen = set()
    for _, _, stem, context in _ported():
        operation = build(stem, context)
        by_text = {str(context[name]): role for name, role in _BINDING_ROLES.items() if name in context}
        for access in access_sets(operation).reads | access_sets(operation).writes:
            expected = by_text.get(access.graph) or _VARIABLE_ROLES.get(access.graph)
            assert expected == access.role, (stem, access)
            seen.add(access.role)
    assert {"meta", "txn", "log", "data", "event", "dataset"} <= seen
