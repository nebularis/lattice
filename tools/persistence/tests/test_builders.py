# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""H2.2: the first builders, held to their Mustache templates by the equivalence harness of the typed IR sketch
§7.1, and the required-parameter guard run on rdflib (TD-34). Validation Pack: docs/developer/validation/FMH-H2-2.md.
Test IDs are H2.2-Tn."""

from __future__ import annotations

import dataclasses
import functools
import re

import pytest

import engines
from rdflib import RDF, XSD, Dataset, Literal as RdfLiteral, URIRef

from persistence import witness
from persistence.builders import BUILDERS, GRAPH_ROLES, Bindings, build, build_recording
from persistence.compiler import CompileError, compile_to_graph
from persistence.ir import GUARDS_OFF, SLOT_KINDS, Const, Graph, GraphBlock, GraphRole, Kind, ParamRef, Path, TermGuard, Var
from persistence.ir_render import _Out, render
from persistence.terms import Iri, Literal, PropertyPath

import equivalence as eq
from request_slots import fill_request_slots

PORTED = sorted(BUILDERS)


@functools.lru_cache(maxsize=1)
def _corpus() -> tuple:
    out = []
    for path in witness.compile_fixtures():
        try:
            compiled, _ = compile_to_graph(witness._load_fixture(path))
        except CompileError:
            continue
        out.append((path.name, compiled))
    return tuple(out)


@functools.lru_cache(maxsize=1)
def _ported() -> tuple:
    return tuple(eq.ported_operations(_corpus()))


def _first(stem: str):
    return next(op for op in _ported() if op[2] == stem)


# ---- the harness ----------------------------------------------------------------------------------------


def test_h2_2_t1_the_ported_operations_are_the_templates_listed_and_every_one_is_generated_by_a_fixture():
    assert PORTED == sorted([
        "append-event", "append-event-dataset-guard", "append-version", "append-version-dataset-guard", "bootstrap-version-row", "bootstrap-version-row-dataset-guard",
        "cas-replace-composite-property", "cas-replace-composite-property-dataset-guard",
        "cas-replace-named-graph", "cas-replace-named-graph-dataset-guard",
        "create-if-absent-composite", "create-if-absent-composite-dataset-guard",
        "create-if-absent-named-graph", "create-if-absent-named-graph-dataset-guard",
        "tombstone-delete-composite", "tombstone-delete-composite-dataset-guard",
        "tombstone-delete-named-graph", "tombstone-delete-named-graph-dataset-guard", "unconditional-write",
        # H2.5: the key claims and the audits. H2.7 ported the last template, cas-replace-value-guard (TD-43).
        "cas-replace-value-guard",
        "key-claim-write", "key-claim-write-dual", "key-claim-retire", "key-claim-quarantine", "key-claim-merge-rewrite",
        "key-claim-duplicate-audit", "fork-detection-audit", "gap-scan-audit", "revision-multi-txn-audit", "txn-multi-revision-audit",
        # H2.6f: the append of versions that states its members as changes, and the query that reads them.
        "append-version-delta", "append-version-delta-dataset-guard", "members",
        # H2.6d: the patch-log and no-receipt variants of the six in-place writes, each with its dataset-guard variant.
        *[
            f"{base}{tag}{guard}"
            for base in (
                "create-if-absent-named-graph", "create-if-absent-composite", "cas-replace-named-graph", "cas-replace-composite-property",
                "tombstone-delete-named-graph", "tombstone-delete-composite",
            )
            for tag in ("-patch-log", "-no-receipt")
            for guard in ("", "-dataset-guard")
        ],
    ])
    assert {stem for _, _, stem, _ in _ported()} == set(PORTED)


def test_h2_2_t2_every_builder_equals_its_template_on_every_fixture_binding_apart_from_the_guard():
    operations = _ported()
    assert eq.compare_all(operations) == len(operations) >= len(PORTED)


@pytest.mark.parametrize("stem", PORTED)
def test_h2_2_t3_a_builder_reads_exactly_the_bindings_its_template_uses(stem):
    _, _, _, context = _first(stem)
    _, read = build_recording(stem, context, guards=False)
    assert read == eq.template_tags(eq.load_template(stem + ".mustache"))


def test_h2_2_t4_the_harness_fails_when_it_compares_fewer_operations_than_were_ported():
    operations = _ported()
    with pytest.raises(eq.Mismatch, match="compared"):
        eq.require_compared(eq.compare_all(operations[:-1]), len(operations))
    with pytest.raises(eq.Mismatch, match="compared"):
        eq.require_compared(eq.compare_all([]), len(operations))
    eq.require_compared(eq.compare_all(operations), len(operations))


def _mutated_text(stem: str, mutate) -> tuple[str, str]:
    _, _, _, context = _first(stem)
    template = eq.load_template(stem + ".mustache")
    mustache = fill_request_slots(eq.mustache_render(template, context))
    operation, _ = build_recording(stem, context, guards=False)
    return mustache, fill_request_slots(render(mutate(operation)))


def _drop_a_triple(op):
    block = op.insert[0]
    return dataclasses.replace(op, insert=(dataclasses.replace(block, elements=block.elements[1:]), *op.insert[1:]))


def _move_to_another_graph(op):
    block = op.insert[0]
    other = dataclasses.replace(block.graph, term=Const(Iri.encode("urn:g:elsewhere")))
    return dataclasses.replace(op, insert=(dataclasses.replace(block, graph=other), *op.insert[1:]))


def _rename(node, old: str, new: str):
    if isinstance(node, Var):
        return dataclasses.replace(node, name=new) if node.name == old else node
    if dataclasses.is_dataclass(node) and not isinstance(node, type):
        return dataclasses.replace(node, **{f.name: _rename(getattr(node, f.name), old, new) for f in dataclasses.fields(node)})
    if isinstance(node, tuple):
        return tuple(_rename(i, old, new) for i in node)
    return node


MUTATIONS = {
    "a dropped triple": _drop_a_triple,
    "a pattern in another graph": _move_to_another_graph,
    "a renamed variable": lambda op: _rename(op, "any", "other"),
}


@pytest.mark.parametrize("stem", ["bootstrap-version-row", "append-event"])
@pytest.mark.parametrize("name", sorted(MUTATIONS))
def test_h2_2_t5_a_mutated_builder_is_caught(stem, name):
    mustache, built = _mutated_text(stem, MUTATIONS[name])
    with pytest.raises(eq.Mismatch):
        eq.compare(mustache, built, name)


def _expected_guard_line(params) -> str:
    tests = []
    for p in params:
        if p.kind is Kind.IRI:
            tests.append(f"ISIRI(${p.name})")
        elif p.kind in (Kind.LONG, Kind.POSITION):
            tests.append(f"DATATYPE(${p.name}) = DATATYPE(\"0\"^^xsd:long)")
        elif p.kind in (Kind.DIGEST, Kind.STRING):
            tests.append(f"DATATYPE(${p.name}) = xsd:string")
        elif p.kind is Kind.IRI_OR_LITERAL:
            tests.append(f"(ISIRI(${p.name}) || ISLITERAL(${p.name}))")
        elif p.kind is Kind.LITERAL:
            tests.append(f'ISLITERAL(${p.name}) && LANG(${p.name}) = ""')
        if p.equals is not None:  # computed from the parameter list, as the type tests are
            tests.append(_Out().expr(TermGuard(ParamRef(p.name), p.equals)))
    return "FILTER(" + " && ".join(tests) + ")"


@pytest.mark.parametrize("names", ["query", "caller"])
@pytest.mark.parametrize("stem", PORTED)
def test_h2_2_t6_the_guard_is_exactly_one_group_with_one_filter_of_type_tests_first_in_where(stem, names):
    _, _, _, context = _first(stem)
    guarded, _ = build_recording(stem, context, graph_names=names)
    bare, _ = build_recording(stem, context, guards=False, graph_names=names)
    assert bare.guard == GUARDS_OFF and guarded.guard != GUARDS_OFF
    assert dataclasses.replace(guarded, guard=GUARDS_OFF) == bare
    on, off = render(guarded).splitlines(), render(bare).splitlines()
    required = [p for p in guarded.params if p.required and p.kind not in SLOT_KINDS]
    if not required:
        assert on == off  # nothing to require, so no guard group at all (plan 4.3, gate 1)
        return
    start = on.index("WHERE {")
    line = _expected_guard_line(required)
    # one group, one FILTER, first in WHERE, on one line when short and on three otherwise
    candidates = [["  { " + line + " }"], ["  {", "    " + line, "  }"]]
    assert any(on == off[: start + 1] + group + off[start + 1:] for group in candidates)


# ---- TD-34 and the guard's position, on rdflib -------------------------------------------------------------

LOG = "urn:g:txlog/"
CONTEXT = {
    "metaGraphPrefix": Iri.encode("urn:g:meta"), "txnGraph": Iri.encode("urn:g:txn"),
    "logGraphPrefix": Iri.encode(LOG), "eventGraphPrefix": Iri.encode("urn:g:events/order/"),
    "datasetGraph": Iri.encode("urn:g:dataset"), "datasetNode": Iri.encode("urn:g:dataset-node"),
}
PAT = "https://example.org/lattice/patterns#"
LONG = lambda n: RdfLiteral(n, datatype=XSD.long)
STREAM = URIRef("urn:stream:orders/1")
APPEND = {
    "stream": STREAM, "epoch": LONG(3), "revBase": RdfLiteral("urn:rev:orders/1/e3/"), "txnId": URIRef("urn:txn:1"),
    "requestDigest": RdfLiteral("ab" * 32),
}


def event_row(event: str = "urn:event:1", event_type: str = "urn:type:Placed", op_seq: int = 1, at: str = "2026-10-12T10:00:00Z") -> str:
    """One row of an append's `{{{eventRows}}}` slot, as a caller renders it (formal-methods H2.6b)."""
    return f'(<{event}> <{event_type}> "{op_seq}"^^<{XSD.long}> "{at}"^^<{XSD.dateTime}>)'


EVENT_SLOTS = ("{{{eventRows}}}", "{{{eventTriples}}}")


def fill_events(text: str, rows: str | None = None, triples: str = "") -> str:
    """The text of an append with its two request-time slots filled. Other operations have neither slot."""
    return text.replace(EVENT_SLOTS[0], event_row() if rows is None else rows).replace(EVENT_SLOTS[1], triples)


def _store(*, rows: int = 1, dataset_epoch: int | None = None) -> Dataset:
    ds = engines.dataset()
    meta = ds.graph(URIRef("urn:g:meta"))
    for i in range(rows):
        row = URIRef(f"urn:stream:orders/{i + 1}")
        meta.add((row, URIRef(PAT + "epoch"), LONG(3)))
        meta.add((row, URIRef(PAT + "seq"), LONG(0)))
    if dataset_epoch is not None:
        ds.graph(URIRef("urn:g:dataset")).add((URIRef("urn:g:dataset-node"), URIRef(PAT + "epoch"), LONG(dataset_epoch)))
    return ds


def _run(stem: str, ds: Dataset, bindings: dict, *, guards: bool | None = None, rows: str | None = None, triples: str = "") -> Dataset:
    text = fill_events(render(build(stem, CONTEXT, guards=engines.guards(guards))), rows, triples)
    ds.update(text, initBindings=bindings)
    return ds


def _meta(ds: Dataset) -> set:
    return {(str(s), str(p).removeprefix(PAT), str(o)) for s, p, o in ds.graph(URIRef("urn:g:meta"))}


@engines.each_engine_and_guards
def test_h2_2_t7_append_writes_the_event_the_receipt_the_log_and_moves_the_head():
    ds = _run("append-event", _store(), APPEND)
    rev = "urn:rev:orders/1/e3/0000000000000000001"
    assert (str(STREAM), "seq", "1") in _meta(ds) and (str(STREAM), "head", rev) in _meta(ds)
    assert (str(STREAM), "seq", "0") not in _meta(ds)
    assert (URIRef("urn:txn:1"), URIRef(PAT + "rev"), URIRef(rev)) in ds.graph(URIRef("urn:g:txn"))
    event_graphs = {str(g.identifier) for g in ds.graphs() if (URIRef("urn:event:1"), None, None) in g}
    log_graphs = {str(g.identifier) for g in ds.graphs() if (URIRef(rev), None, None) in g and str(g.identifier).startswith(LOG)}
    assert len(event_graphs) == 1 and next(iter(event_graphs)).startswith("urn:g:events/order/")
    assert len(log_graphs) == 1


@engines.each_engine_and_guards
def test_h2_2_t8_the_first_revision_has_no_previous_revision_and_is_still_written():
    ds = _run("append-event", _store(), APPEND)
    log = next(g for g in ds.graphs() if str(g.identifier).startswith(LOG))
    assert len(list(log.objects(None, URIRef(PAT + "prevRev")))) == 0
    assert len(list(log.objects(None, URIRef(PAT + "recordedAt")))) == 1


@engines.each_engine_and_guards
def test_h2_2_t9_a_retry_with_the_same_transaction_changes_nothing():
    ds = _run("append-event", _store(), APPEND)
    before = {(str(g.identifier), s, p, o) for g in ds.graphs() for s, p, o in g}
    _run("append-event", ds, APPEND)
    assert {(str(g.identifier), s, p, o) for g in ds.graphs() for s, p, o in g} == before


@engines.each_engine_and_guards
def test_h2_2_t10_a_second_event_chains_to_the_first():
    ds = _run("append-event", _store(), APPEND)
    second = {**APPEND, "txnId": URIRef("urn:txn:2")}
    _run("append-event", ds, second, rows=event_row("urn:event:2", op_seq=2))
    assert (str(STREAM), "seq", "2") in _meta(ds)
    log = next(g for g in ds.graphs() if str(g.identifier).startswith(LOG))
    assert (URIRef("urn:rev:orders/1/e3/0000000000000000002"), URIRef(PAT + "prevRev"), URIRef("urn:rev:orders/1/e3/0000000000000000001")) in log


@engines.each_engine_and_guards
def test_h2_2_t11_the_dataset_guard_variant_writes_only_while_the_dataset_epoch_matches():
    wrote = _run("append-event-dataset-guard", _store(dataset_epoch=3), APPEND)
    assert (str(STREAM), "seq", "1") in _meta(wrote)
    refused = _run("append-event-dataset-guard", _store(dataset_epoch=4), APPEND)
    assert (str(STREAM), "seq", "0") in _meta(refused) and not any(s == str(STREAM) and p == "head" for s, p, _ in _meta(refused))


@engines.each_engine_and_guards
def test_h2_2_t12_bootstrap_creates_the_row_once():
    target = URIRef("urn:stream:new")
    ds = _run("bootstrap-version-row", engines.dataset(), {"target": target, "epoch": LONG(3)})
    rows = _meta(ds)
    assert rows == {(str(target), "epoch", "3"), (str(target), "seq", "0"), (str(target), str(RDF.type), PAT + "VersionRow")}
    _run("bootstrap-version-row", ds, {"target": target, "epoch": LONG(9)})
    assert _meta(ds) == rows


@engines.each_engine_and_guards
def test_h2_2_t13_the_bootstrap_dataset_guard_variant_needs_a_matching_dataset_epoch():
    target = URIRef("urn:stream:new")
    assert _meta(_run("bootstrap-version-row-dataset-guard", _store(rows=0, dataset_epoch=4), {"target": target, "epoch": LONG(3)})) == set()
    assert len(_meta(_run("bootstrap-version-row-dataset-guard", _store(rows=0, dataset_epoch=3), {"target": target, "epoch": LONG(3)}))) == 3


_TARGET = URIRef("urn:stream:new")
_TYPE = (str(_TARGET), str(RDF.type), PAT + "VersionRow")


@pytest.mark.parametrize("name, bindings, unguarded", [
    ("no epoch", {"target": _TARGET}, {_TYPE, (str(_TARGET), "seq", "0")}),
    ("no target", {"epoch": LONG(3)}, set()),
    ("epoch as xsd:integer", {"target": _TARGET, "epoch": RdfLiteral(3)}, {_TYPE, (str(_TARGET), "seq", "0"), (str(_TARGET), "epoch", "3")}),
    ("target as a literal", {"target": RdfLiteral("urn:stream:new"), "epoch": LONG(3)}, {_TYPE, (str(_TARGET), "seq", "0"), (str(_TARGET), "epoch", "3")}),
])
def test_h2_2_t14_a_missing_or_mistyped_parameter_writes_nothing_where_without_the_guard_it_writes_a_bad_row(name, bindings, unguarded):
    assert _meta(_run("bootstrap-version-row", engines.dataset(), bindings)) == set()
    assert _meta(_run("bootstrap-version-row", engines.dataset(), bindings, guards=False)) == unguarded  # TD-34


@pytest.mark.parametrize("missing", sorted(set(APPEND) - {"stream"}))
def test_h2_2_t15_append_with_any_one_parameter_missing_writes_nothing(missing):
    bindings = {k: v for k, v in APPEND.items() if k != missing}
    ds = _run("append-event", _store(), bindings)
    assert _meta(ds) == _meta(_store())
    assert not list(ds.graph(URIRef("urn:g:txn")))


def test_h2_2_t16_a_missing_stream_is_not_bound_from_the_data():
    """The pattern `$stream pat:epoch $epoch` would bind a missing `$stream` to every stored row. The guard is
    tested first, in its own group (ADR-A123 decision 5), so nothing is written."""
    bindings = {k: v for k, v in APPEND.items() if k != "stream"}
    guarded = _run("append-event", _store(rows=2), bindings)
    assert _meta(guarded) == _meta(_store(rows=2))
    unguarded = _run("append-event", _store(rows=2), bindings, guards=False)
    assert _meta(unguarded) != _meta(_store(rows=2))  # what the guard prevents


# ---- instantiate renders the ported operations from their builders --------------------------------------------


def _instantiate(*, guards: bool = True, graph_names: str = "query", **kwargs) -> dict:
    """The operations of the append-event fixture as `instantiate` renders them from a profile compiled with the run's choices (H2.7-Q2)."""
    from persistence.instantiate import instantiate_by_target

    compiled, _ = compile_to_graph(witness._load_fixture(witness.WITNESS_DIR / "template-append-event.ttl"), guards=guards, graph_names=graph_names)
    return instantiate_by_target(compiled, **kwargs)


def test_h2_2_t17_instantiate_renders_a_ported_operation_with_its_guard_and_without_it_on_request():
    guarded = next(iter(_instantiate().values()))["append"]
    bare = next(iter(_instantiate(guards=False).values()))["append"]
    assert "ISIRI($stream)" in guarded and "ISIRI($stream)" not in bare
    assert "FILTER(ISIRI($stream)" in guarded


def test_h2_2_t18_an_overriding_template_library_is_still_rendered_by_mustache(tmp_path):
    from persistence.render import _template_dir_default

    for template in _template_dir_default().glob("*.mustache"):
        (tmp_path / template.name).write_text(template.read_text(encoding="utf-8"), encoding="utf-8")
    text = next(iter(_instantiate(template_dir=tmp_path).values()))["append"]
    assert "ISIRI" not in text and "{{" not in text.replace("{{{payloadTriples}}}", "").replace("{{{eventRows}}}", "").replace("{{{eventTriples}}}", "")


def test_h2_2_t19_the_command_line_flag_of_compile_leaves_the_guards_out_and_instantiate_follows_the_profile(tmp_path):
    from persistence.cli import main

    config = [str(witness.SPEC_TTL), str(witness.EXAMPLES_DIR / "append-stream-dataset-guard.ttl")]
    on_profile, off_profile = tmp_path / "on.ttl", tmp_path / "off.ttl"
    assert main(["compile", *config, "--out", str(on_profile)]) == 0
    assert main(["compile", *config, "--out", str(off_profile), "--no-parameter-guards"]) == 0
    assert main(["instantiate", str(on_profile), "--out", str(tmp_path / "on")]) == 0
    assert main(["instantiate", str(off_profile), "--out", str(tmp_path / "off")]) == 0
    on = next((tmp_path / "on").rglob("append.rq")).read_text(encoding="utf-8")
    off = next((tmp_path / "off").rglob("append.rq")).read_text(encoding="utf-8")
    assert "ISIRI($stream)" in on and "ISIRI($stream)" not in off


# ---- graph roles and binding types (review of H2.2, 2026-10-12) ---------------------------------------------


def _graphs(node):
    """Every Graph inside an IR value."""
    if isinstance(node, Graph):
        yield node
    elif dataclasses.is_dataclass(node) and not isinstance(node, type):
        for f in dataclasses.fields(node):
            yield from _graphs(getattr(node, f.name))
    elif isinstance(node, tuple):
        for item in node:
            yield from _graphs(item)


def test_h2_2_t20_every_graph_of_every_ported_operation_has_the_role_its_name_gives_it():
    checked = 0
    for fixture, name, stem, context in _ported():
        by_value = {str(context[n]): n for n in GRAPH_ROLES if n in context}
        for graph in _graphs(build(stem, context)):
            if isinstance(graph.term, Var):
                key = graph.term.name
            else:
                key = by_value[str(graph.term.term)]
            assert graph.role is GRAPH_ROLES[key], f"{fixture} {name}: {key} has role {graph.role}"
            checked += 1
    assert checked > 0


_GRAPH_SLOT = re.compile(r"GRAPH (?:\{\{\{([A-Za-z]+)\}\}\}|\?([A-Za-z0-9]+))")


def test_h2_2_t21_the_role_table_names_every_graph_slot_and_graph_variable_of_every_template():
    names = set()
    from persistence.render import _template_dir_default

    for template in sorted(_template_dir_default().glob("*.mustache")):
        text = eq._COMMENT.sub("", template.read_text(encoding="utf-8"))
        names |= {a or b for a, b in _GRAPH_SLOT.findall(text)}
    assert names and names <= set(GRAPH_ROLES), sorted(names - set(GRAPH_ROLES))


def test_h2_2_t22_a_binding_is_wrapped_as_its_declared_type():
    seen = set()
    for _, compiled in _corpus():
        from persistence.instantiate import operation_context
        from persistence.namespaces import DAL

        for node in compiled.subjects(RDF.type, DAL.GeneratedOperation):
            context = operation_context(compiled, node)
            for binding in compiled.objects(node, DAL.hasParameterBinding):
                declared = str(compiled.value(binding, DAL.paramType))
                value = context[str(compiled.value(binding, DAL.paramName))]
                expected = {"Integer": int, "Iri": Iri, "String": Literal, "Literal": Literal, "PropertyPath": PropertyPath}[declared]
                assert type(value) is expected, (declared, value)
                seen.add(declared)
    assert {"Iri", "Integer", "PropertyPath"} <= seen


def test_h2_2_t23_an_unknown_parameter_type_is_refused():
    from rdflib import BNode, Graph as RdfGraph
    from persistence.instantiate import operation_context
    from persistence.namespaces import DAL

    g, op, binding = RdfGraph(), BNode(), BNode()
    g.add((op, DAL.hasParameterBinding, binding))
    g.add((binding, DAL.paramName, RdfLiteral("x")))
    g.add((binding, DAL.paramValue, RdfLiteral("<urn:x>")))
    g.add((binding, DAL.paramType, RdfLiteral("Var")))
    with pytest.raises(ValueError, match="unknown dal:paramType"):
        operation_context(g, op)


def test_h2_2_t24_a_property_path_binding_is_read_as_a_path_and_never_as_a_constant():
    from persistence.paths import Alt, Star, Step

    path = PropertyPath.encode(Star(Alt((Step(URIRef("urn:p:a")), Step(URIRef("urn:p:b"), inverse=True)))))
    bindings = Bindings({"ownedPath": path})
    assert bindings.path("ownedPath") == Path(path)
    with pytest.raises(TypeError, match="path"):
        bindings.const("ownedPath")

