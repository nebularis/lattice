# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""H2.12: the rows replace (formal-methods track H, plan 4.20). The compare-and-set of a named-graph or composite family carries its payload,
and under a patch log its delta, as rows of the `WHERE` instead of in the template, so the write is linear in the aggregate's size on a store
that applies every deletion before any insertion (TSD-65, TSD-01). `compile` selects it where the capability spec declares
`dal:providesSnapshotUpdateSemantics` or the profile opts in with `dal:replaceForm`. These tests cover the builders and their contract, the
behaviour against the template form on each engine where the form is safe, the four empty cases, the selection and the diagnostics.
Validation Pack: docs/developer/validation/FMH-H2-12.md. Test IDs are H2.12-Tn."""

from __future__ import annotations

import pytest
from rdflib import Graph, Literal as RdfLiteral, URIRef

import engines
from builder_goldens import CANONICAL_CONTEXT
from persistence import witness
from persistence.builders import BUILDERS, ROWS, build
from persistence.compiler import CompileError, compile_targets, compile_to_graph
from persistence.contract import contract_of
from persistence.ir import Binding, Const, Graph as IrGraph, GraphBlock, GraphRole, Group, IrError, Kind, Operation, Param, PayloadRows, Triple, Var
from persistence.ir_render import check, render
from persistence.templatecheck import operations as checked_operations
from persistence.terms import Iri
from test_patch_log import (
    ADDED, DATA, FAMILIES, META, OUTSIDER, P, PAT, PAYLOAD, REMOVED, ROOT, TXN, aggregate, args, data_graph, everything, nt, run, stem, store, triples,
)

U = URIRef
ROWS_BUILDERS = sorted(k for k in BUILDERS if "-rows" in k)
RECEIPTS = {"named-graph": ("", "-patch-log", "-no-receipt"), "composite": ("-patch-log", "-no-receipt")}
EXAMPLE = witness.EXAMPLES_DIR / "replace-form-rows.ttl"
BYSTANDER = {(OUTSIDER, P, RdfLiteral("outside"))}
"""The neighbour a composite store holds in the same data graph, which no replace of the root may touch."""


def rows_stem(family: str, tag: str = "-patch-log", dg: bool = False) -> str:
    base = "cas-replace-named-graph-rows" if family == "named-graph" else "cas-replace-composite-property-rows"
    return base + tag + ("-dataset-guard" if dg else "")


def rows(triples_) -> str:
    return " ".join(f"({s.n3()} {p.n3()} {o.n3()})" for s, p, o in triples_)


def _safe_engine() -> None:
    """The rows form needs every deletion applied before any insertion. rdflib applies each solution in turn (TSD-01), and Oxigraph does
    so from 0.5.12 (TSD-01, P1)."""
    if engines.CURRENT == "rdflib":
        pytest.skip("the rows replace is not selected for rdflib, which applies each solution in turn (TSD-01)")
    if engines.CURRENT == "oxigraph":
        from lattice_testing_oxigraph import SNAPSHOT_UPDATES

        if not SNAPSHOT_UPDATES:
            pytest.skip("this pyoxigraph applies each solution in turn (TSD-01), so the rows replace is not selected for it")


# ---- the builders and their contract ------------------------------------------------------------------------------------------------


def test_h2_12_t1_ten_rows_builders_exist_one_per_receipt_model_and_guard_of_each_family():
    assert ROWS_BUILDERS == sorted(
        rows_stem(family, tag, dg) for family in FAMILIES for tag in RECEIPTS[family] for dg in (False, True)
    )


@pytest.mark.parametrize("key", ROWS_BUILDERS)
def test_h2_12_t2_a_rows_builder_carries_its_payload_as_rows_and_keeps_the_template_forms_contract(key):
    op = build(key, dict(CANONICAL_CONTEXT))
    sets = check(op)
    text = render(op)
    where = text[text.index("WHERE"):]
    assert "VALUES (?newS ?newP ?newO) { {{{payloadTriples}}} }" in where
    assert ("VALUES (?addS ?addP ?addO) { {{{assertTriples}}} }" in where) is ("-patch-log" in key)
    assert where.rstrip().endswith("UNION {\n  }\n}"), "the last branch is empty, so a replace of nothing by nothing still moves the row"
    assert "{{{" not in text[:text.index("WHERE")], "no slot is left in a template"
    contract = contract_of(op)
    template = contract_of(build(key.replace("-rows", ""), dict(CANONICAL_CONTEXT)))
    assert contract.payload.encoding == "TripleRows" and template.payload.encoding == "GroundNTriples"
    assert contract.version == 1
    assert (contract.parameters, contract.digest, contract.kind) == (template.parameters, template.digest, template.kind)
    assert set(contract.accesses) == set(template.accesses), "the rows triple is recorded as the payload's access, as the slot is"
    assert any(a.subject == "{payload}" and a.mode == "Insert" for a in sets.writes)


def _op(where, params=(Param("root", Kind.IRI), Param("payloadTriples", Kind.PAYLOAD))):
    data = IrGraph(GraphRole.DATA, Const(Iri.encode("urn:g:x")))
    insert = (GraphBlock(data, (Triple(*(Var(n, binding=Binding.OPTIONAL_ALLOWED) for n in ("newS", "newP", "newO"))),)),)
    return Operation.build("x", params, Group(where), insert=insert)


@pytest.mark.parametrize("bad, rule", [
    (PayloadRows((Var("newS"), Var("newP")), "payloadTriples"), "InvalidName"),
    (PayloadRows((Var("newS"), Var("newS"), Var("newO")), "payloadTriples"), "InvalidName"),
    (PayloadRows((Var("newS"), Var("newP"), Var("newO")), "eventRows"), "UndeclaredParameter"),
    (PayloadRows((Var("newS"), Var("newP"), Var("newO")), "root"), "SlotMisuse"),
], ids=["two variables", "a variable twice", "an undeclared parameter", "a parameter that is not a payload"])
def test_h2_12_t3_the_checker_refuses_malformed_payload_rows(bad, rule):
    with pytest.raises(IrError) as e:
        check(_op((bad,)))
    assert str(e.value).startswith(rule)


# ---- behaviour, against the template form ---------------------------------------------------------------------------------------------


def _slots(payload, added=(), removed=()) -> tuple[dict, dict]:
    """The slot texts of a request, for the template form and for the rows form."""
    return (
        {"payloadTriples": nt(payload), "assertTriples": nt(added), "retractTriples": nt(removed)},
        {"payloadTriples": rows(payload), "assertTriples": rows(added), "retractTriples": rows(removed)},
    )


def _both(family, tag, dg, payload, added=(), removed=(), *, before=store, bindings=None):
    """Run the template replace and the rows replace from the same state, returning the two stores."""
    template_slots, rows_slots = _slots(payload, added, removed)
    one, two = before(family, dataset_epoch=1 if dg else None), before(family, dataset_epoch=1 if dg else None)
    run(one, stem("replace", family, tag, dg), bindings or args(), **template_slots)
    run(two, rows_stem(family, tag, dg), bindings or args(), **rows_slots)
    return one, two


@pytest.mark.parametrize("family", FAMILIES)
@pytest.mark.parametrize("dg", [False, True], ids=["row-guard", "dataset-guard"])
@engines.each_engine_and_guards
def test_h2_12_t4_the_rows_replace_leaves_what_the_template_replace_leaves_under_each_receipt_model(family, dg):
    _safe_engine()
    for tag in RECEIPTS[family]:
        template, rows_ = _both(family, tag, dg, PAYLOAD, [ADDED], [REMOVED])
        assert everything(template) == everything(rows_), (family, tag, dg)
        assert triples(rows_, data_graph(family)) == PAYLOAD | (BYSTANDER if family == "composite" else set())


@pytest.mark.parametrize("family", FAMILIES)
@engines.each_engine_and_guards
def test_h2_12_t5_a_lost_race_and_a_retry_write_nothing(family):
    _safe_engine()
    _, rows_slots = _slots(PAYLOAD, [ADDED], [REMOVED])
    ds = store(family)
    before = everything(ds)
    run(ds, rows_stem(family), args(seq=5), **rows_slots)
    assert everything(ds) == before
    ds.graph(TXN).add((U("urn:txn:2"), U(PAT + "rev"), U("urn:rev:elsewhere")))
    before = everything(ds)
    run(ds, rows_stem(family), args(), **rows_slots)
    assert everything(ds) == before


def _empty_aggregate(family, **kw):
    return store(family, data=False, **kw)


@pytest.mark.parametrize("family", FAMILIES)
@engines.each_engine_and_guards
def test_h2_12_t6_the_four_empty_cases_leave_what_the_template_form_leaves(family):
    """E1 from an empty aggregate to a payload, E2 to an empty payload, E3 from empty to empty, E4 an identical re-save (the sketch's §5.3)."""
    _safe_engine()
    old = aggregate(family)
    cases = {
        "E1": (_empty_aggregate, PAYLOAD, PAYLOAD, ()),
        "E2": (store, set(), (), old),
        "E3": (_empty_aggregate, set(), (), ()),
        "E4": (store, old, (), ()),
    }
    for case, (before, payload, added, removed) in cases.items():
        template, rows_ = _both(family, "-patch-log", False, payload, added, removed, before=before)
        assert everything(template) == everything(rows_), case
        assert (ROOT, U(PAT + "seq"), engines.canon(RdfLiteral(2, datatype=URIRef("http://www.w3.org/2001/XMLSchema#long")))) in triples(rows_, META), case
        # a store built with data holds the composite's bystander, and one built without holds nothing beside the row
        bystander = BYSTANDER if family == "composite" and before is store else set()
        assert triples(rows_, data_graph(family)) == set(payload) | bystander, case


# ---- the selection and the diagnostics ---------------------------------------------------------------------------------------------------


def _replaces(graph) -> dict:
    out = {}
    for ct in compile_targets(graph):
        name = str(ct.target.cls).rsplit("#", 1)[-1]
        out[name] = next(op.template_id for op in ct.operations if op.operation == "cas-replace")
    return out


def test_h2_12_t7_compile_selects_the_rows_form_by_the_spec_or_by_the_opt_in_and_the_template_form_otherwise():
    assert _replaces(witness._load_fixture(EXAMPLE)) == {
        "Invoice": "cas-replace-named-graph-rows-patch-log", "Note": "cas-replace-named-graph-rows", "Memo": "cas-replace-named-graph-patch-log",
    }


DAL, EX = "https://www.nebularis.org/neuro-semantic/lattice/persistence#", "https://example.org/lending#"


def _with(extra: str, *remove: tuple) -> Graph:
    """The example with the triples of ``extra`` added, after each ``(subject, predicate)`` of ``remove`` is cleared, since the properties
    are single-valued."""
    g = witness._load_fixture(EXAMPLE)
    for subject, predicate in remove:
        g.remove((U(EX + subject), U(DAL + predicate), None))
    g.parse(data=f"@prefix dal: <{DAL}> . @prefix ex: <{EX}> . " + extra, format="turtle")
    return g


def test_h2_12_t8_a_spec_that_declares_the_semantics_false_and_an_opt_out_keep_the_template_form():
    assert _replaces(_with("ex:FusekiOverTdb2 dal:providesSnapshotUpdateSemantics false .", ("FusekiOverTdb2", "providesSnapshotUpdateSemantics")))["Invoice"] == "cas-replace-named-graph-patch-log"
    assert _replaces(_with("ex:InvoiceProfile dal:replaceForm dal:TemplateReplace ."))["Invoice"] == "cas-replace-named-graph-patch-log"


def test_h2_12_t9_the_opt_in_against_a_declared_false_is_refused():
    g = _with("ex:FusekiOverTdb2 dal:providesSnapshotUpdateSemantics false . ex:InvoiceProfile dal:replaceForm dal:RowsReplace .", ("FusekiOverTdb2", "providesSnapshotUpdateSemantics"))
    with pytest.raises(CompileError, match="ReplaceFormContradictsCapability"):
        compile_targets(g)


def test_h2_12_t10_a_form_on_a_family_with_no_sweeping_replace_is_recorded_and_warned():
    g = _with(
        "ex:MemoProfile dal:concurrencyProfile dal:ProvidedConcurrency ; dal:replaceForm dal:RowsReplace . ",
        ("MemoProfile", "concurrencyProfile"), ("MemoProfile", "minConcurrencyLevel"),
    )
    (memo,) = [ct for ct in compile_targets(g) if str(ct.target.cls).endswith("#Memo")]
    assert "ReplaceFormNotApplicable" in {d.kind for d in memo.diagnostics}
    assert not any(op.operation == "cas-replace" for op in memo.operations)


def test_h2_12_t11_a_composite_family_takes_the_rows_form_under_a_deployment_wide_spec():
    g = witness._load_fixture(witness.EXAMPLES_DIR / "composite-project-ownership.ttl")
    g.parse(data="@prefix dal: <https://www.nebularis.org/neuro-semantic/lattice/persistence#> . <urn:env> a dal:CapabilitySpec ; dal:providesCas dal:Linearizable ; dal:providesSnapshotUpdateSemantics true .", format="turtle")
    assert any(t.startswith("cas-replace-composite-property-rows") for t in _replaces(g).values())


def test_h2_12_t12_the_template_check_parses_every_operation_of_the_example_with_rows_stand_ins():
    compiled, _ = compile_to_graph(witness._load_fixture(EXAMPLE))
    ops = checked_operations(compiled)
    rows_ops = [o for o in ops if "-rows" in o.template]
    assert len(rows_ops) == 2 and all("(<urn:x-check:s> <urn:x-check:p> <urn:x-check:o>)" in o.text for o in rows_ops)
