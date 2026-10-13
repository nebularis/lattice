# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""H2.1: the typed operation IR refuses what its types forbid (formal-methods track H, ADR-A123).
Validation Pack: docs/developer/validation/FMH-H2-1.md. Test IDs are H2.1-Tn."""

from __future__ import annotations

import re
from dataclasses import replace
import pathlib

import pytest

from persistence import ir, ir_render
from persistence.ir import (
    GUARDS_OFF, A, Bind, Binding, Compare, Const, Filter, Func, Graph, GraphBlock, GraphRole, Group, IrError, Kind, Not,
    NotExists, Op, Operation, Optional_, Param, ParameterGuard, ParamRef, PayloadSlot, Path, Projected,
    RegistrySlot, Select, SubSelect, TermGuard, Triple, Union_, ValueGuard, Values, Var,
)
from persistence.ir_render import RULES, check, render
from persistence.paths import Step
from persistence.terms import Iri, Literal, PropertyPath, SparqlTerm

from ir_fixtures import (
    DATA, EPOCH, EXPECTED, META, NEXT, PARAMS, REV, ROOT, TXN, TXN_ID, delete, insert, integer, iri, pat, string, true,
    valid, where,
)

SRC = pathlib.Path(ir.__file__).parent


def refused(rule: str, operation: Operation) -> None:
    with pytest.raises(IrError) as caught:
        check(operation)
    assert caught.value.rule == rule, caught.value


def _long_filter(guard) -> Operation:
    return valid(where_=(*where(), Filter(guard)))


def _with_param(*extra: Param) -> tuple:
    return (*PARAMS, *extra)


def _bad_construction(make) -> None:
    with pytest.raises(IrError):
        make()


# ---- the SELECT rules (H2.5, ADR-A123 addendum of 2026-10-13) ----------------------------------------------------

_KEYS = Graph(GraphRole.KEYS, iri("urn:g:keys"))
_CLAIMS = GraphBlock(_KEYS, (Triple(Var("claim"), pat("claimedBy"), Var("owner")),))
_COUNT = Projected(Func("COUNT", (Var("owner"),)), Var("n"))
_MANY = ValueGuard(">", Func("COUNT", (Var("owner"),)), integer(1))


def _query(select: Select, where_=(_CLAIMS,)) -> Operation:
    return Operation.build("audit", (), Group(where_), select=select)


def _sub(select: Select) -> SubSelect:
    return SubSelect(select, Group((_CLAIMS,)))


def _outer_with(sub: SubSelect, *more) -> Operation:
    return valid(where_=(*where(), sub, *more))


# ---- the positive case the refusals vary ----------------------------------------------------------


def test_h2_1_t1_the_base_operation_is_accepted_and_renders():
    sets = check(valid())
    assert sets.reads and sets.writes
    assert render(valid()).startswith("PREFIX pat:")


# ---- one refusal per rule -------------------------------------------------------------------------

_PATH = Path(PropertyPath.encode(Step(__import__("rdflib").URIRef("urn:p:owns"))))


_USE_GX = GraphBlock(Graph(GraphRole.LOG, Var("gx")), (Triple(Var("a"), pat("p"), Var("b")),))


def _refusals() -> list[tuple[str, str, object]]:
    """(rule, label, a function returning an operation, or raising IrError for a construction-time rule)."""
    bound = lambda n: Var(n, binding=Binding.BOUND)
    optional = lambda n: Var(n, binding=Binding.OPTIONAL_ALLOWED)
    return [
        ("InvalidName", "parameter", lambda: Param("1bad", Kind.IRI)),
        ("InvalidName", "variable", lambda: Var("a b")),
        ("InvalidName", "reference", lambda: ParamRef("x y")),
        ("InvalidParameterKind", "kind as a string", lambda: Param("x", "Iri")),
        ("UnencodedConstant", "bare str", lambda: Const("urn:x")),
        ("UnencodedConstant", "blank node as a SparqlTerm", lambda: Const(SparqlTerm("_:b0"))),
        ("UnencodedConstant", "blank node as an Iri", lambda: Const(Iri("_:b0"))),
        ("UnencodedConstant", "an unescaped literal", lambda: Const(Literal('"} DROP ALL {"x'))),
        ("UnencodedConstant", "bare str in a triple", lambda: valid(where_=(*where(), GraphBlock(META, (Triple(ROOT, pat("p"), "urn:x"),))))),
        ("UnencodedConstant", "bare number in an expression", lambda: valid(where_=(*where(), Bind(Func("STR", (1,)), Var("n"))))),
        ("UnencodedConstant", "a path that is not encoded", lambda: Path("<urn:p>/<urn:q>")),
        ("UnencodedConstant", "a PropertyPath built without its encoder", lambda: Path(PropertyPath("<urn:p> } DROP ALL"))),
        ("UnencodedConstant", "an Iri built without its encoder, holding a \\u escape", lambda: Const(Iri("<urn:x\\u003E>"))),
        ("InvalidForm", "neither update nor select", lambda: valid(insert_=(), delete_=())),
        ("InvalidForm", "both", lambda: valid(select=Select((Var("x"),)))),
        ("DuplicateParameter", "twice", lambda: valid(params=_with_param(Param("root", Kind.IRI)))),
        ("UndeclaredParameter", "a reference", lambda: valid(where_=(*where(), GraphBlock(META, (Triple(ROOT, pat("p"), ParamRef("nope")),))))),
        ("UndeclaredParameter", "a slot", lambda: valid(insert_=(*insert(), GraphBlock(DATA, (PayloadSlot("missing"),))))),
        ("UnusedParameter", "declared and never used", lambda: valid(params=_with_param(Param("spare", Kind.IRI)))),
        ("NameCollision", "variable named as a parameter", lambda: valid(where_=(*where(), GraphBlock(META, (Triple(Var("root"), pat("p"), Var("x")),))))),
        ("MissingGraphRole", "no role", lambda: Graph(None, iri("urn:g:x"))),
        ("MissingGraphRole", "role as a string", lambda: Graph("meta", iri("urn:g:x"))),
        ("DefaultGraphPattern", "bare triple in WHERE", lambda: valid(where_=(*where(), Triple(ROOT, pat("p"), Var("x"))))),
        ("DefaultGraphPattern", "template element outside a graph", lambda: valid(insert_=(*insert(), Triple(ROOT, pat("p"), Var("x", binding=Binding.BOUND))))),
        ("NestedGraph", "graph in graph", lambda: valid(where_=(*where(), GraphBlock(META, (GraphBlock(TXN, ()),))))),
        ("PathOutsideWhere", "path in INSERT", lambda: valid(insert_=(*insert(), GraphBlock(DATA, (Triple(ROOT, _PATH, ROOT),))))),
        ("PathOutsideWhere", "path in DELETE", lambda: valid(delete_=(GraphBlock(DATA, (Triple(ROOT, _PATH, ROOT),)),))),
        ("UnsupportedInTemplate", "filter in INSERT", lambda: valid(insert_=(GraphBlock(META, (Filter(Func("BOUND", (ROOT,))),)),))),
        ("UntaggedTemplateVariable", "no tag", lambda: valid(insert_=(*insert(), GraphBlock(META, (Triple(ROOT, pat("p"), Var("now")),))))),
        ("InconsistentVariableTag", "both tags", lambda: valid(insert_=(*insert(), GraphBlock(META, (Triple(ROOT, pat("p"), bound("now")), Triple(ROOT, pat("q"), optional("now"))))))),
        ("UnboundTemplateVariable", "Bound but only optional", lambda: valid(insert_=insert(prev=Binding.BOUND))),
        ("UnboundTemplateVariable", "Bound and never bound", lambda: valid(insert_=(*insert(), GraphBlock(META, (Triple(ROOT, pat("p"), bound("ghost")),))))),
        ("UnboundTemplateVariable", "Bound from an optional parameter", lambda: valid(
            params=_with_param(Param("hint", Kind.IRI, required=False)),
            where_=(*where(), Bind(ParamRef("hint"), Var("h"))),
            insert_=(*insert(), GraphBlock(META, (Triple(ROOT, pat("hint"), bound("h")),))))),
        ("UnboundTemplateVariable", "Bound from a BIND in a nested group over an outer variable", lambda: valid(
            where_=(*where(), Group((Bind(Func("STR", (Var("now"),)), Var("stamp")),))),
            insert_=(*insert(), GraphBlock(META, (Triple(ROOT, pat("stamp"), bound("stamp")),))))),
        ("UnboundTemplateVariable", "Bound from a BIND in a UNION branch over an outer variable", lambda: valid(
            where_=(*where(), Union_((Group((Bind(Func("STR", (Var("now"),)), Var("stamp")),)), Group((Bind(string("x"), Var("stamp")),))))),
            insert_=(*insert(), GraphBlock(META, (Triple(ROOT, pat("stamp"), bound("stamp")),))))),
        ("UnboundGraphVariable", "GRAPH ?g in an OPTIONAL that nothing binds", lambda: valid(where_=(*where(), Optional_(Group((_USE_GX,)))))),
        ("UnboundGraphVariable", "GRAPH ?g in a UNION branch that nothing binds", lambda: valid(where_=(*where(), Union_((Group((_USE_GX,)), Group(())))))),
        ("UnboundGraphVariable", "GRAPH ?g bound only after the group that uses it", lambda: valid(where_=(*where(), Optional_(Group((_USE_GX,))), Bind(iri("urn:g:x"), Var("gx"))))),
        ("InvalidEquals", "on an optional parameter", lambda: valid(params=_with_param(Param("extra", Kind.IRI, required=False, equals=iri("urn:x"))), where_=(*where(), GraphBlock(META, (Triple(ROOT, pat("p"), ParamRef("extra")),))))),
        ("InvalidEquals", "on a slot", lambda: valid(params=(*PARAMS[:6], Param("payloadTriples", Kind.PAYLOAD, equals=iri("urn:x"))))),
        ("InvalidEquals", "naming a variable", lambda: valid(params=_with_param(Param("g", Kind.IRI, equals=Func("IRI", (Func("STR", (Var("now"),)),)))), where_=(*where(), GraphBlock(Graph(GraphRole.DATA, ParamRef("g")), (Triple(ROOT, pat("p"), Var("x")),))))),
        ("ClockInGuard", "NOW in an equals check", lambda: valid(params=_with_param(Param("g", Kind.IRI, equals=Func("IRI", (Func("STR", (Func("NOW"),)),)))), where_=(*where(), GraphBlock(Graph(GraphRole.DATA, ParamRef("g")), (Triple(ROOT, pat("p"), Var("x")),))))),
        ("UndeclaredParameter", "an equals check naming an undeclared parameter", lambda: valid(params=_with_param(Param("g", Kind.IRI, equals=Func("IRI", (Func("STR", (ParamRef("nope"),)),)))), where_=(*where(), GraphBlock(Graph(GraphRole.DATA, ParamRef("g")), (Triple(ROOT, pat("p"), Var("x")),))))),
        ("UnboundTemplateVariable", "OptionalAllowed and never bound", lambda: valid(insert_=(*insert(), GraphBlock(META, (Triple(ROOT, pat("p"), optional("ghost")),))))),
        ("OptionalTagOnBoundVariable", "always bound", lambda: valid(insert_=insert(now=Binding.OPTIONAL_ALLOWED))),
        ("UnboundGraphVariable", "free GRAPH ?g", lambda: valid(where_=(*where(), GraphBlock(Graph(GraphRole.LOG, Var("free")), (Triple(Var("a"), pat("p"), Var("b")),))))),
        ("BindTargetInScope", "already in scope", lambda: valid(where_=(*where(), Bind(string("x"), Var("now"))))),
        ("WrongGuard", "value comparison on a term-matched position", lambda: _long_filter(ValueGuard("<=", EXPECTED, ParamRef("nextSeq")))),
        ("WrongGuard", "value comparison on an untyped variable", lambda: _long_filter(ValueGuard(">", Var("now"), string("x")))),
        ("WrongGuard", "sameTerm on a value-compared position", lambda: valid(params=(*PARAMS[:2], Param("expectedSeq", Kind.POSITION, compare=Compare.VALUE), *PARAMS[3:]), where_=(*where(), Filter(TermGuard(EXPECTED, ParamRef("nextSeq")))))),
        ("ClockInGuard", "NOW in a filter", lambda: _long_filter(ValueGuard("<", Func("NOW"), Func("NOW")))),
        ("ClockInGuard", "NOW through a BIND", lambda: valid(where_=(*where(), Filter(Not(Func("BOUND", (Var("now"),))))))),
        ("ClockInGuard", "NOW through two BINDs", lambda: valid(where_=(*where(), Bind(Func("STR", (Var("now"),)), Var("stamp")), Filter(Func("BOUND", (Var("stamp"),)))))),
        ("ParameterGuardNotDerived", "missing a parameter", lambda: replace(valid(), guard=ParameterGuard(PARAMS[:1]))),
        ("ParameterGuardNotDerived", "no guard at all", lambda: replace(valid(), guard=None)),
        ("ParameterGuardNotDerived", "a guard that is off and names parameters", lambda: replace(valid(), guard=replace(GUARDS_OFF, params=PARAMS[:1]))),
        ("ParameterGuardNotDerived", "a stray parameter", lambda: replace(valid(), guard=ParameterGuard(PARAMS[:6] + (Param("extra", Kind.IRI),)))),
        ("SlotMisuse", "payload in WHERE", lambda: valid(where_=(*where(), GraphBlock(META, (PayloadSlot("payloadTriples"),))))),
        ("SlotMisuse", "payload in DELETE", lambda: valid(delete_=(*delete(), GraphBlock(DATA, (PayloadSlot("payloadTriples"),))))),
        ("SlotMisuse", "two payload slots", lambda: valid(insert_=(*insert(), GraphBlock(META, (PayloadSlot("payloadTriples"),))))),
        ("SlotMisuse", "slot naming a non-payload parameter", lambda: valid(insert_=(*insert(), GraphBlock(META, (PayloadSlot("root"),))))),
        ("SlotMisuse", "slot bound as a term", lambda: valid(where_=(*where(), GraphBlock(META, (Triple(ROOT, pat("p"), ParamRef("payloadTriples")),))))),
        ("SlotMisuse", "registry slot naming a payload", lambda: valid(where_=(*where(), Values(Var("log"), (RegistrySlot("payloadTriples"),))))),
        ("UnknownFunction", "unsupported", lambda: valid(where_=(*where(), Bind(Func("RAND"), Var("r"))))),
        ("UnknownFunction", "wrong arity", lambda: valid(where_=(*where(), Bind(Func("STR", ()), Var("r"))))),
        ("UnknownFunction", "DISTINCT on a scalar", lambda: valid(where_=(*where(), Bind(Func("STR", (ROOT,), distinct=True), Var("r"))))),
        ("UnknownOperator", "comparison as an Op", lambda: valid(where_=(*where(), Filter(Op("=", ROOT, ROOT))))),
        ("UnknownOperator", "unknown Op", lambda: valid(where_=(*where(), Bind(Op("%", string("a"), string("b")), Var("r"))))),
        ("UnknownOperator", "unknown comparison", lambda: valid(where_=(*where(), Filter(ValueGuard("~", ROOT, ROOT))))),
        ("AggregateOutsideSelect", "COUNT in BIND", lambda: valid(where_=(*where(), Bind(Func("COUNT", (Var("now"),)), Var("r"))))),
        ("UngroupedProjection", "a variable that is not grouped", lambda: _query(Select((Var("claim"), Var("owner")), group_by=(Var("claim"),)))),
        ("UngroupedProjection", "a variable beside an aggregate with no GROUP BY", lambda: _query(Select((Var("claim"), _COUNT)))),
        ("UngroupedProjection", "an expression over an ungrouped variable", lambda: _query(Select((Projected(Func("STR", (Var("owner"),)), Var("s")), _COUNT)))),
        ("HavingNotGrouped", "a HAVING term over an ungrouped variable", lambda: _query(Select((Var("claim"),), group_by=(Var("claim"),), having=(ValueGuard(">", Var("owner", compare=Compare.VALUE), integer(1)),)))),
        ("SubSelectLeak", "an inner variable used outside the sub-select", lambda: _outer_with(_sub(Select((Var("claim"), _COUNT), group_by=(Var("claim"),))), GraphBlock(META, (Triple(Var("owner"), pat("p"), Var("claim")),)))),
        ("SubSelectLeak", "an inner variable that another sub-select projects", lambda: _outer_with(_sub(Select((Var("claim"),), group_by=(Var("claim"),))), SubSelect(Select((Var("owner"),), group_by=(Var("owner"),)), Group((_CLAIMS,))))),
        ("FragmentLimit", "ORDER BY", lambda: _query(Select((Var("claim"),), order_by=(Var("claim"),)))),
        ("FragmentLimit", "LIMIT", lambda: _query(Select((Var("claim"),), limit=1))),
        ("FragmentLimit", "OFFSET", lambda: _query(Select((Var("claim"),), offset=1))),
        ("FragmentLimit", "DISTINCT inside a sub-select", lambda: _outer_with(_sub(Select((Var("claim"),), distinct=True)))),
        ("FragmentLimit", "a sub-select inside a sub-select", lambda: _outer_with(SubSelect(Select((Var("claim"),)), Group((_sub(Select((Var("claim"),))),))))),
    ]


_REFUSALS = _refusals()


def test_h2_1_t2_every_rule_has_a_refusal_test():
    assert {rule for rule, _, _ in _REFUSALS} == set(RULES)


def test_h2_1_t3_every_rule_the_code_raises_is_named_in_rules():
    raised = set()
    for module in ("ir.py", "ir_render.py"):
        raised |= set(re.findall(r'IrError\(\s*"(\w+)"', (SRC / module).read_text(encoding="utf-8")))
    assert raised <= set(RULES), raised - set(RULES)


@pytest.mark.parametrize("rule, label, make", _REFUSALS, ids=[f"{r}-{l}" for r, l, _ in _REFUSALS])
def test_h2_1_t4_an_invalid_value_is_refused_with_its_rule(rule, label, make):
    with pytest.raises(IrError) as caught:
        result = make()
        if isinstance(result, Operation):
            check(result)
    assert caught.value.rule == rule, caught.value


_OPERATION_REFUSALS = [r for r in _REFUSALS if r[0] not in {"InvalidName", "InvalidParameterKind", "UnencodedConstant", "MissingGraphRole"} or r[1] in {"bare str in a triple", "bare number in an expression"}]


@pytest.mark.parametrize("rule, label, make", _OPERATION_REFUSALS, ids=[f"{r}-{l}" for r, l, _ in _OPERATION_REFUSALS])
def test_h2_1_t4b_render_refuses_what_check_refuses(rule, label, make):
    try:
        operation = make()
    except IrError:
        return  # refused when built, so there is nothing to render
    with pytest.raises(IrError) as caught:
        render(operation)
    assert caught.value.rule == rule


# ---- what is accepted ------------------------------------------------------------------------------


def test_h2_1_t5_a_property_path_is_accepted_in_where():
    where_ = (*where(), GraphBlock(DATA, (Triple(ROOT, _PATH, Var("s")), Triple(Var("s"), Var("p"), Var("o")))))
    sets = check(valid(where_=where_))
    assert any(a.closure for a in sets.reads)
    assert not any(a.closure for a in sets.writes)


def test_h2_1_t6_a_guard_matches_the_position_it_compares():
    value = Param("fence", Kind.LONG, compare=Compare.VALUE)
    ok = valid(params=_with_param(value), where_=(*where(), GraphBlock(META, (Triple(ROOT, pat("fence"), Var("f", Kind.LONG, Compare.VALUE)),)), Filter(ValueGuard("<=", Var("f", Kind.LONG, Compare.VALUE), ParamRef("fence")))))
    check(ok)
    check(_long_filter(TermGuard(EXPECTED, ParamRef("nextSeq"))))
    check(_long_filter(ValueGuard("!=", ROOT, REV)))  # IRIs: value and term equality agree


def test_h2_1_t7_graph_variables_are_accepted_when_a_bind_or_values_binds_them():
    values = (Values(Var("log"), (iri("urn:g:pinned"), RegistrySlot("logGraphs"))), GraphBlock(Graph(GraphRole.LOG, Var("log")), (Triple(Var("r"), A, pat("Revision")),)))
    params = (Param("logGraphs", Kind.REGISTRY_LIST),)
    select = Select((Var("r"),))
    check(Operation.build("audit", params, Group(values), select=select))


def _joined_graph(shape: str) -> Operation:
    use = _USE_GX
    inner = {"OPTIONAL": Optional_(Group((use,))), "nested group": Group((use,)), "UNION branch": Union_((Group((use,)), Group(())))}[shape]
    return valid(where_=(*where(), Bind(iri("urn:g:x"), Var("gx")), inner))


@pytest.mark.parametrize("shape", ["OPTIONAL", "nested group", "UNION branch"])
def test_h2_3_t1_a_graph_variable_bound_in_an_enclosing_group_is_accepted_in_an_inner_one(shape):
    """H2.3-Q2. The refusal case this replaces is listed in the Validation Pack of FMH-H2-3. A pattern's solutions are
    joined with the enclosing group on ?g, so the result holds only that graph's triples (test_h2_3_t2)."""
    check(_joined_graph(shape))


def test_h2_1_t8_the_parameter_guard_is_derived_and_removable():
    op = valid()
    assert op.guard == ParameterGuard.derive(PARAMS)
    assert [p.name for p in op.guard.params] == ["root", "epoch", "expectedSeq", "nextSeq", "newRev", "txnId"]
    bare = replace(op, guard=GUARDS_OFF)
    assert check(bare) == check(op)
    assert "ISIRI" in render(op) and "ISIRI" not in render(bare)


def test_h2_1_t9_an_optional_parameter_is_not_guarded():
    params = (*PARAMS[:6], Param("cause", Kind.IRI, required=False), PARAMS[6])
    op = valid(params=params, where_=(*where(), GraphBlock(META, (Triple(ROOT, pat("cause"), ParamRef("cause")),))))
    assert "cause" not in [p.name for p in op.guard.params]
    assert "BOUND($cause)" not in render(op)
