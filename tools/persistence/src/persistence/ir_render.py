# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""The renderer of the typed operation IR (formal-methods track H, slice H2.1, ADR-A123).

:func:`render` turns an :class:`~persistence.ir.Operation` into SPARQL text. It first runs
:func:`check`, which refuses every operation the types in :mod:`persistence.ir` call invalid, each with
a named rule (:data:`RULES`). The same walk derives the graphs and subjects the operation reads and
writes (:func:`access_sets`), so a read or write set is never declared by hand and cannot drift from
the query.

The text carries the request-time variables as ``$name`` and the payload and registry slots as the
Mustache tags ``{{{name}}}``, as the templates do. Predicates in the vocabulary namespaces are written
with prefixes, so the output reads like the templates it replaces.
"""

from __future__ import annotations

import dataclasses
import re
from dataclasses import dataclass, field
from typing import Iterable, Optional

from rdflib.namespace import XSD

from .ir import (
    AccessMode, Binding, Bind, Compare, Const, Expr, Filter, Func, Graph, GraphBlock, GraphRole, Group, IrError, Kind,
    Not, NotExists, Op, Operation, Optional_, Param, ParameterGuard, ParamRef, Path, PayloadSlot, Projected, RdfType,
    RegistrySlot, RowValues,
    SLOT_KINDS, Select, SubSelect, TermGuard, Triple, Union_, ValueGuard, Values, Var,
)
from .namespaces import PAT
from .terms import Iri, Literal

RULES: tuple[str, ...] = (
    "InvalidName",
    "InvalidParameterKind",
    "InvalidEquals",
    "UnencodedConstant",
    "InvalidForm",
    "DuplicateParameter",
    "UndeclaredParameter",
    "UnusedParameter",
    "NameCollision",
    "MissingGraphRole",
    "DefaultGraphPattern",
    "NestedGraph",
    "NotExistsWithoutGraph",
    "PathOutsideWhere",
    "UnsupportedInTemplate",
    "UntaggedTemplateVariable",
    "InconsistentVariableTag",
    "UnboundTemplateVariable",
    "OptionalTagOnBoundVariable",
    "UnboundGraphVariable",
    "BindTargetInScope",
    "WrongGuard",
    "ClockInGuard",
    "ParameterGuardNotDerived",
    "SlotMisuse",
    "UnknownFunction",
    "UnknownOperator",
    "AggregateOutsideSelect",
    "UngroupedProjection",
    "HavingNotGrouped",
    "SubSelectLeak",
    "FragmentLimit",
)
"""Every refusal, in the order a reader meets it. A test names each one."""

# name -> (fewest arguments, most arguments)
FUNCTIONS: dict[str, tuple[int, int]] = {
    "IRI": (1, 1), "CONCAT": (1, 99), "STR": (1, 1), "ENCODE_FOR_URI": (1, 1), "SUBSTR": (2, 3),
    "STRLEN": (1, 1), "STRDT": (2, 2), "COALESCE": (1, 99), "BOUND": (1, 1), "DATATYPE": (1, 1),
    "NOW": (0, 0), "ISIRI": (1, 1), "ISLITERAL": (1, 1), "LANG": (1, 1),
}
AGGREGATES: dict[str, tuple[int, int]] = {
    "COUNT": (1, 1), "MIN": (1, 1), "MAX": (1, 1), "SAMPLE": (1, 1), "GROUP_CONCAT": (1, 1),
}
_ARITHMETIC = {"+", "-", "*", "/"}
_BOOLEAN = {"&&", "||"}
_COMPARISONS = {"=", "!=", "<", "<=", ">", ">="}
_TERM_PINNED = frozenset({Kind.LONG, Kind.POSITION, Kind.DIGEST, Kind.STRING, Kind.LANG_STRING})
_GUARD_DATATYPE = {Kind.DIGEST: XSD.string, Kind.STRING: XSD.string}


def _has_aggregate(expr) -> bool:
    if isinstance(expr, Func):
        return expr.name in AGGREGATES or any(_has_aggregate(a) for a in expr.args)
    if isinstance(expr, (Op, ValueGuard, TermGuard)):
        return _has_aggregate(expr.left) or _has_aggregate(expr.right)
    if isinstance(expr, Not):
        return _has_aggregate(expr.arg)
    return False


def _free_vars(expr) -> set:
    """The variables of ``expr`` outside any aggregate, which a grouped query allows only if they are group keys."""
    if isinstance(expr, Var):
        return {expr.name}
    if isinstance(expr, Func):
        return set() if expr.name in AGGREGATES else set().union(*(_free_vars(a) for a in expr.args))
    if isinstance(expr, (Op, ValueGuard, TermGuard)):
        return _free_vars(expr.left) | _free_vars(expr.right)
    if isinstance(expr, Not):
        return _free_vars(expr.arg)
    return set()


def _projected_names(select: Select) -> set:
    return {i.name if isinstance(i, Var) else i.var.name for i in select.projection}


def _var_names(node, expand: Optional[SubSelect] = None) -> set:
    """Every variable name in an IR value. A sub-select other than ``expand`` contributes its projections only, since
    nothing else of it is visible outside."""
    if isinstance(node, Var):
        return {node.name}
    if isinstance(node, SubSelect) and node is not expand:
        return _projected_names(node.select)
    if dataclasses.is_dataclass(node) and not isinstance(node, type):
        return set().union(*(_var_names(getattr(node, f.name), expand) for f in dataclasses.fields(node)))
    if isinstance(node, (tuple, list)):
        return set().union(*(_var_names(i, expand) for i in node))
    return set()


# ---------------------------------------------------------------------------
# the check


@dataclass(frozen=True, order=True)
class Access:
    """One graph, subject and predicate an operation reads or writes. ``closure`` marks a pattern that
    reaches a set of nodes through a property path, so its subjects are known only at execution. ``mode`` is an
    :class:`~persistence.ir.AccessMode` value (formal-methods H2.6)."""

    role: str
    graph: str
    subject: str
    predicate: str
    closure: bool = False
    mode: str = ""


@dataclass(frozen=True)
class AccessSets:
    reads: frozenset
    writes: frozenset


@dataclass
class _Scope:
    definite: set
    possible: set
    # Variables the enclosing groups bind. A BIND inside an inner group does not see them (the group is evaluated on
    # its own), but a pattern's solutions are joined with the enclosing group's afterwards, so a GRAPH ?g whose ?g an
    # enclosing group binds yields only that graph's triples (ADR-A123, second addendum of 2026-10-12).
    joined: set = field(default_factory=set)

    def inner(self, *, copy: bool = False) -> "_Scope":
        """The scope of a group nested in this one. ``copy`` is for NOT EXISTS, which is evaluated per outer solution."""
        enclosing = self.joined | self.definite
        if copy:
            return _Scope(set(self.definite), set(self.possible), enclosing)
        return _Scope(set(), set(), enclosing)


class _Checker:
    def __init__(self, op: Operation) -> None:
        self.op = op
        self.params: dict[str, Param] = {}
        self.used_params: set[str] = set()
        self.template_tags: dict[str, set] = {}
        self.untagged: set[str] = set()
        self.clock_vars: set[str] = set()
        self.slot_uses: list[str] = []
        self.reads: set[Access] = set()
        self.writes: set[Access] = set()
        self.subselects: list[SubSelect] = []
        self.depth = 0
        self.absence = 0

    # ---- entry

    def run(self) -> AccessSets:
        op = self.op
        if not isinstance(op.id, str) or not op.id:
            raise IrError("InvalidForm", "an operation needs an id")
        self._params()
        self._equals()
        is_select = op.select is not None
        is_update = bool(op.insert or op.delete)
        if is_select == is_update:
            raise IrError("InvalidForm", f"{op.id}: an operation is a SELECT or an update with an INSERT or DELETE template, not both and not neither")
        self._guard()
        self._find_clock_vars(op.where)
        for block in op.delete:
            self._template(block, deleting=True)
        for block in op.insert:
            self._template(block, deleting=False)
        scope = _Scope(set(), set())
        self._group(op.where.elements, scope, graph=None)
        if is_select:
            self._check_select(op.select, sub=False)
            self._projection_bound(op.select, self._mentioned(op.where.elements))
        else:
            self._template_variables(scope)
        self._sub_select_leaks()
        self._params_used()
        return AccessSets(frozenset(self.reads), frozenset(self.writes))

    # ---- parameters

    def _params(self) -> None:
        for param in self.op.params:
            if not isinstance(param, Param):
                raise IrError("UndeclaredParameter", f"{param!r} is not a Param")
            if param.name in self.params:
                raise IrError("DuplicateParameter", f"parameter {param.name!r} is declared twice")
            self.params[param.name] = param

    def _equals(self) -> None:
        """Check every ``equals`` expression as a guard expression. It is checked whether or not guards are on."""
        for param in self.params.values():
            if param.equals is None:
                continue
            if not param.required or param.kind in SLOT_KINDS:
                raise IrError("InvalidEquals", f"{self.op.id}: ${param.name} has an equals check, which needs a required parameter that is not a slot")
            if self._variables(param.equals):
                raise IrError("InvalidEquals", f"{self.op.id}: the equals check of ${param.name} names a variable, and the guard group binds none")
            self._expr(param.equals, guard=True)
            self._clock_check(param.equals, True)

    def _variables(self, expr) -> bool:
        if isinstance(expr, Var):
            return True
        if isinstance(expr, Func):
            return any(self._variables(a) for a in expr.args)
        if isinstance(expr, (Op, ValueGuard, TermGuard)):
            return self._variables(expr.left) or self._variables(expr.right)
        if isinstance(expr, Not):
            return self._variables(expr.arg)
        return False

    def _guard(self) -> None:
        guard = self.op.guard
        if guard is None:
            raise IrError(
                "ParameterGuardNotDerived",
                f"{self.op.id}: no parameter guard. Build with Operation.build, which derives it, or pass guards=False "
                "to leave the checks to the caller",
            )
        if guard.off:
            if guard.params:
                raise IrError("ParameterGuardNotDerived", f"{self.op.id}: a guard that is off names no parameters")
            return
        if guard != ParameterGuard.derive(self.op.params):
            raise IrError(
                "ParameterGuardNotDerived",
                f"{self.op.id}: the guard must be derived from the parameter list with ParameterGuard.derive",
            )

    def _param_ref(self, ref: ParamRef) -> Param:
        param = self.params.get(ref.name)
        if param is None:
            raise IrError("UndeclaredParameter", f"{self.op.id}: ${ref.name} is not a declared parameter")
        if param.kind in SLOT_KINDS:
            raise IrError("SlotMisuse", f"{self.op.id}: ${ref.name} is a {param.kind.value} slot and cannot be bound as a term")
        self.used_params.add(ref.name)
        return param

    def _params_used(self) -> None:
        for name, param in self.params.items():
            if name not in self.used_params:
                raise IrError("UnusedParameter", f"{self.op.id}: parameter {name!r} is declared and never used")
        # No limit on payload slots (H2.6d). A patch-log create writes its payload slot into the data graph and into its add graph, and a
        # patch-log replace has a slot for each of its payload, add and del content.

    # ---- terms

    def _node(self, node, scope: Optional[_Scope], *, allow_path: bool = False, predicate: bool = False) -> None:
        if isinstance(node, Var):
            self._var(node)
        elif isinstance(node, ParamRef):
            self._param_ref(node)
        elif isinstance(node, Const):
            pass
        elif isinstance(node, RdfType):
            if not predicate:
                raise IrError("UnencodedConstant", "the predicate a is only a predicate")
        elif isinstance(node, Path):
            if not predicate:
                raise IrError("PathOutsideWhere", "a property path is only a predicate")
            if not allow_path:
                raise IrError("PathOutsideWhere", f"{self.op.id}: a property path is allowed only in a WHERE pattern, not in a template")
        elif isinstance(node, str):
            raise IrError("UnencodedConstant", f"{self.op.id}: a bare str {node!r} reached the IR, wrap it in a Const made by persistence.terms")
        else:
            raise IrError("UnencodedConstant", f"{self.op.id}: {node!r} is not a term")

    def _var(self, var: Var) -> None:
        if var.name in self.params:
            raise IrError("NameCollision", f"{self.op.id}: variable ?{var.name} has the name of a parameter")

    # ---- graph blocks and groups

    def _graph(self, graph: Graph, scope: Optional[_Scope], where: bool) -> None:
        if not isinstance(graph, Graph):
            raise IrError("MissingGraphRole", f"{self.op.id}: a graph block needs a Graph with a role")
        term = graph.term
        if isinstance(term, Var):
            self._var(term)
            if where and scope is not None and term.name not in scope.definite and term.name not in scope.joined:
                raise IrError(
                    "UnboundGraphVariable",
                    f"{self.op.id}: GRAPH ?{term.name} is matched before a BIND or VALUES binds it in this group or an enclosing one, "
                    "so it ranges over every graph",
                )
        elif isinstance(term, ParamRef):
            self._param_ref(term)

    def _group(self, elements, scope: _Scope, graph: Optional[GraphBlock]) -> None:
        seen: set[str] = set()
        for el in elements:
            names = self._element(el, scope, graph, seen)
            seen |= names

    def _element(self, el, scope: _Scope, graph: Optional[GraphBlock], seen: set) -> set:
        """Check one element of a pattern group. Returns the variable names it mentions."""
        if isinstance(el, Triple):
            if graph is None:
                raise IrError("DefaultGraphPattern", f"{self.op.id}: a triple outside a GRAPH block would match the default graph")
            names = self._triple(el, scope, graph)
            return names
        if isinstance(el, PayloadSlot):
            raise IrError("SlotMisuse", f"{self.op.id}: a payload slot belongs in an INSERT template, not a WHERE pattern")
        if isinstance(el, GraphBlock):
            if graph is not None:
                raise IrError("NestedGraph", f"{self.op.id}: a GRAPH block inside a GRAPH block")
            self._graph(el.graph, scope, where=True)
            names = set()
            if isinstance(el.graph.term, Var):
                names.add(el.graph.term.name)
                scope.definite.add(el.graph.term.name)
            inner = scope.inner()
            self._group(el.elements, inner, el)
            scope.definite |= inner.definite
            scope.possible |= inner.possible
            return names | inner.definite | inner.possible | self._mentioned(el.elements)
        if isinstance(el, Optional_):
            # SPARQL evaluates an inner group on its own and joins it afterwards, so a BIND or a GRAPH ?g inside
            # it does not see what the enclosing group bound (SPARQL 1.1 section 18.2). Only NOT EXISTS, which is
            # evaluated once per outer solution with its values substituted, does.
            inner = scope.inner()
            self._group(el.group.elements, inner, graph)
            scope.possible |= inner.definite - scope.definite | inner.possible
            return self._mentioned(el.group.elements)
        if isinstance(el, NotExists):
            if graph is not None and not any(isinstance(e, GraphBlock) for e in el.group.elements):
                # rdflib 7.6.0 can evaluate a body with no GRAPH of its own against the default graph, once the enclosing GRAPH block has
                # yielded a solution (TSD-34). A body that names its graph does not depend on the enclosing context, on any store.
                raise IrError("NotExistsWithoutGraph", f"{self.op.id}: a NOT EXISTS inside a GRAPH block must name its graph in its body (TSD-34)")
            inner = scope.inner(copy=True)
            self.absence += 1
            # the body names its graph, so it is checked outside the enclosing block (a GRAPH inside a GRAPH is not a nested block here)
            self._group(el.group.elements, inner, None)
            self.absence -= 1
            return self._mentioned(el.group.elements)
        if isinstance(el, Filter):
            names = self._expr(el.expr, guard=True)
            self._clock_check(el.expr, True)
            return names
        if isinstance(el, Bind):
            names = self._expr(el.expr, guard=False)
            if not isinstance(el.var, Var):
                raise IrError("InvalidName", f"{self.op.id}: BIND needs a Var to bind")
            self._var(el.var)
            if el.var.name in seen or el.var.name in scope.definite or el.var.name in scope.possible:
                raise IrError("BindTargetInScope", f"{self.op.id}: BIND(... AS ?{el.var.name}) names a variable already in scope")
            if self._definitely_bound(el.expr, scope):
                scope.definite.add(el.var.name)
            else:
                scope.possible.add(el.var.name)
            return names | {el.var.name}
        if isinstance(el, RowValues):
            if not el.vars or not all(isinstance(v, Var) for v in el.vars):
                raise IrError("InvalidName", f"{self.op.id}: VALUES rows need one or more Vars")
            for v in el.vars:
                self._var(v)
            if len({v.name for v in el.vars}) != len(el.vars):
                raise IrError("InvalidName", f"{self.op.id}: VALUES rows name a variable twice")
            self._slot(el.slot.param, Kind.ROWS)
            scope.definite |= {v.name for v in el.vars}
            return {v.name for v in el.vars}
        if isinstance(el, Values):
            if not isinstance(el.var, Var):
                raise IrError("InvalidName", f"{self.op.id}: VALUES needs a Var")
            self._var(el.var)
            for item in el.items:
                if isinstance(item, RegistrySlot):
                    self._slot(item.param, Kind.REGISTRY_LIST)
                elif isinstance(item, Const):
                    pass
                else:
                    raise IrError("UnencodedConstant", f"{self.op.id}: a VALUES item is a Const or a RegistrySlot, got {item!r}")
            scope.definite.add(el.var.name)
            return {el.var.name}
        if isinstance(el, Union_):
            branches = []
            names: set = set()
            for g in el.groups:
                inner = scope.inner()
                self._group(g.elements, inner, graph)
                branches.append(inner)
                names |= self._mentioned(g.elements)
            if branches:
                common = set.intersection(*(b.definite for b in branches))
                every = set.union(*(b.definite | b.possible for b in branches))
                scope.definite |= common
                scope.possible |= every - common
            return names
        if isinstance(el, SubSelect):
            if self.depth:
                raise IrError("FragmentLimit", f"{self.op.id}: a sub-select inside a sub-select is outside the fragment (ADR-A123, addendum of 2026-10-13)")
            self._check_select(el.select, sub=True)
            # A sub-select is evaluated on its own, so it starts with nothing in scope, and only its projections leave it.
            inner = _Scope(set(), set(), set())
            self.depth += 1
            self._group(el.where.elements, inner, graph)
            self.depth -= 1
            self._projection_bound(el.select, self._mentioned(el.where.elements))
            definite, possible = self._select_names(el.select, inner)
            scope.definite |= definite
            scope.possible |= possible - definite
            self.subselects.append(el)
            return _projected_names(el.select)
        if isinstance(el, Group):
            inner = scope.inner()
            self._group(el.elements, inner, graph)
            scope.definite |= inner.definite
            scope.possible |= inner.possible
            return self._mentioned(el.elements)
        raise IrError("UnsupportedInTemplate", f"{self.op.id}: {el!r} is not a pattern element")

    def _triple(self, t: Triple, scope: _Scope, graph: GraphBlock) -> set:
        self._node(t.subject, scope)
        self._node(t.predicate, scope, allow_path=True, predicate=True)
        self._node(t.object, scope)
        names = set()
        for part in (t.subject, t.predicate, t.object):
            if isinstance(part, Var):
                names.add(part.name)
                scope.definite.add(part.name)
        self.reads.add(self._access(graph.graph, t, self._read_mode(graph.graph, t)))
        return names

    def _read_mode(self, graph: Graph, t: Triple) -> str:
        """An absence read inside ``NOT EXISTS``. A read through a path, or of every triple of a root's data graph, reads the
        whole aggregate. A read with a variable subject elsewhere is a scan, and one with a given subject is a point read."""
        if self.absence:
            return AccessMode.ABSENCE_READ.value
        if isinstance(t.predicate, Path):
            return AccessMode.WHOLE_AGGREGATE_READ.value
        if isinstance(t.subject, Var):
            if graph.role is GraphRole.DATA and isinstance(t.predicate, Var):
                return AccessMode.WHOLE_AGGREGATE_READ.value
            return AccessMode.SCAN_READ.value
        return AccessMode.POINT_READ.value

    def _mentioned(self, elements) -> set:
        names: set = set()
        for el in elements:
            if isinstance(el, Triple):
                names |= {p.name for p in (el.subject, el.predicate, el.object) if isinstance(p, Var)}
            elif isinstance(el, GraphBlock):
                if isinstance(el.graph.term, Var):
                    names.add(el.graph.term.name)
                names |= self._mentioned(el.elements)
            elif isinstance(el, (Optional_, NotExists)):
                names |= self._mentioned(el.group.elements)
            elif isinstance(el, Group):
                names |= self._mentioned(el.elements)
            elif isinstance(el, Union_):
                for g in el.groups:
                    names |= self._mentioned(g.elements)
            elif isinstance(el, SubSelect):
                names |= _projected_names(el.select)
            elif isinstance(el, Bind):
                names.add(el.var.name)
            elif isinstance(el, Values):
                names.add(el.var.name)
            elif isinstance(el, RowValues):
                names |= {v.name for v in el.vars}
        return names

    def _slot(self, name: str, kind: Kind) -> None:
        param = self.params.get(name)
        if param is None:
            raise IrError("UndeclaredParameter", f"{self.op.id}: slot {{{{{{{name}}}}}}} is not a declared parameter")
        if param.kind is not kind:
            raise IrError("SlotMisuse", f"{self.op.id}: slot {name!r} must be a {kind.value} parameter, it is {param.kind.value}")
        self.used_params.add(name)
        self.slot_uses.append(name)

    # ---- binding analysis

    def _definitely_bound(self, expr, scope: _Scope) -> bool:
        if isinstance(expr, Var):
            return expr.name in scope.definite
        if isinstance(expr, ParamRef):
            param = self.params.get(expr.name)
            return param is not None and param.required
        if isinstance(expr, Const):
            return True
        if isinstance(expr, Func):
            if expr.name == "COALESCE":
                return any(self._definitely_bound(a, scope) for a in expr.args)
            return all(self._definitely_bound(a, scope) for a in expr.args)
        if isinstance(expr, (Op, ValueGuard, TermGuard)):
            return self._definitely_bound(expr.left, scope) and self._definitely_bound(expr.right, scope)
        if isinstance(expr, Not):
            return self._definitely_bound(expr.arg, scope)
        return False

    # ---- templates

    def _template(self, block, *, deleting: bool) -> None:
        if not isinstance(block, GraphBlock):
            raise IrError("DefaultGraphPattern", f"{self.op.id}: a template element must be a GraphBlock, got {block!r}")
        self._graph(block.graph, None, where=False)
        if isinstance(block.graph.term, Var):
            self._tag(block.graph.term)
        target = self.writes
        for el in block.elements:
            if isinstance(el, Triple):
                self._node(el.subject, None)
                self._node(el.predicate, None, predicate=True)
                self._node(el.object, None)
                for part in (el.subject, el.predicate, el.object):
                    if isinstance(part, Var):
                        self._tag(part)
                target.add(self._access(block.graph, el, AccessMode.DELETE.value if deleting else AccessMode.INSERT.value))
            elif isinstance(el, PayloadSlot):
                if deleting:
                    raise IrError("SlotMisuse", f"{self.op.id}: a payload slot is for an INSERT template, not a DELETE template")
                self._slot(el.param, Kind.PAYLOAD)
                target.add(Access(block.graph.role.value, _term_text(block.graph.term), "{payload}", "*", False, AccessMode.INSERT.value))
            else:
                raise IrError("UnsupportedInTemplate", f"{self.op.id}: a template holds triples and a payload slot only, got {el!r}")

    def _tag(self, var: Var) -> None:
        self._var(var)
        if var.binding is None:
            self.untagged.add(var.name)
        else:
            self.template_tags.setdefault(var.name, set()).add(var.binding)

    def _template_variables(self, scope: _Scope) -> None:
        for name in sorted(self.untagged):
            raise IrError(
                "UntaggedTemplateVariable",
                f"{self.op.id}: ?{name} is used in a template without a Binding of Bound or OptionalAllowed",
            )
        for name, tags in sorted(self.template_tags.items()):
            if len(tags) > 1:
                raise IrError("InconsistentVariableTag", f"{self.op.id}: ?{name} is tagged both Bound and OptionalAllowed")
            (tag,) = tags
            if tag is Binding.BOUND and name not in scope.definite:
                raise IrError("UnboundTemplateVariable", f"{self.op.id}: ?{name} is tagged Bound and is not bound in every solution of WHERE")
            if tag is Binding.OPTIONAL_ALLOWED:
                if name in scope.definite:
                    raise IrError("OptionalTagOnBoundVariable", f"{self.op.id}: ?{name} is tagged OptionalAllowed and WHERE always binds it")
                if name not in scope.possible:
                    raise IrError("UnboundTemplateVariable", f"{self.op.id}: ?{name} is tagged OptionalAllowed and WHERE never binds it")

    # ---- expressions

    def _find_clock_vars(self, group: Group) -> None:
        binds: list[Bind] = []

        def walk(elements) -> None:
            for el in elements:
                if isinstance(el, Bind):
                    binds.append(el)
                elif isinstance(el, GraphBlock):
                    walk(el.elements)
                elif isinstance(el, (Optional_, NotExists)):
                    walk(el.group.elements)
                elif isinstance(el, Group):
                    walk(el.elements)
                elif isinstance(el, SubSelect):
                    walk(el.where.elements)
                elif isinstance(el, Union_):
                    for g in el.groups:
                        walk(g.elements)

        walk(group.elements)
        changed = True
        while changed:
            changed = False
            for bind in binds:
                if bind.var.name not in self.clock_vars and self._clocked(bind.expr):
                    self.clock_vars.add(bind.var.name)
                    changed = True

    def _clocked(self, expr) -> bool:
        if isinstance(expr, Func):
            return expr.name == "NOW" or any(self._clocked(a) for a in expr.args)
        if isinstance(expr, Var):
            return expr.name in self.clock_vars
        if isinstance(expr, (Op, ValueGuard, TermGuard)):
            return self._clocked(expr.left) or self._clocked(expr.right)
        if isinstance(expr, Not):
            return self._clocked(expr.arg)
        return False

    def _operand_policy(self, operand) -> tuple[Optional[Kind], Compare]:
        if isinstance(operand, ParamRef):
            param = self._param_ref(operand)
            return param.kind, param.compare
        if isinstance(operand, Var):
            return operand.kind, operand.compare
        return None, Compare.VALUE  # a computed value, a constant or a function result has no pinned term

    def _expr(self, expr, *, guard: bool, aggregate_ok: bool = False) -> set:
        """Check an expression. ``guard`` is true in a FILTER, a HAVING and the required-parameter guard."""
        if isinstance(expr, Var):
            self._var(expr)
            return {expr.name}
        if isinstance(expr, ParamRef):
            self._param_ref(expr)
            return set()
        if isinstance(expr, Const):
            return set()
        if isinstance(expr, str) or isinstance(expr, (int, float, bool)):
            raise IrError("UnencodedConstant", f"{self.op.id}: {expr!r} reached an expression unwrapped, use a Const")
        if isinstance(expr, Func):
            return self._func(expr, guard=guard, aggregate_ok=aggregate_ok)
        if isinstance(expr, Op):
            if expr.op in _COMPARISONS:
                raise IrError("UnknownOperator", f"{self.op.id}: a comparison {expr.op!r} is a ValueGuard or a TermGuard, not an Op")
            if expr.op not in _ARITHMETIC | _BOOLEAN:
                raise IrError("UnknownOperator", f"{self.op.id}: operator {expr.op!r} is not one of {sorted(_ARITHMETIC | _BOOLEAN)}")
            return self._expr(expr.left, guard=guard, aggregate_ok=aggregate_ok) | self._expr(expr.right, guard=guard, aggregate_ok=aggregate_ok)
        if isinstance(expr, Not):
            return self._expr(expr.arg, guard=guard, aggregate_ok=aggregate_ok)
        if isinstance(expr, TermGuard):
            for operand in (expr.left, expr.right):
                _, compare = self._operand_policy(operand)
                if isinstance(operand, (Var, ParamRef)) and compare is Compare.VALUE:
                    raise IrError("WrongGuard", f"{self.op.id}: sameTerm on a position declared value-compared ({_term_text(operand)})")
            names = self._expr(expr.left, guard=guard, aggregate_ok=aggregate_ok) | self._expr(expr.right, guard=guard, aggregate_ok=aggregate_ok)
            self._clock_check(expr, guard)
            return names
        if isinstance(expr, ValueGuard):
            if expr.op not in _COMPARISONS:
                raise IrError("UnknownOperator", f"{self.op.id}: comparison {expr.op!r} is not one of {sorted(_COMPARISONS)}")
            for operand in (expr.left, expr.right):
                if isinstance(operand, (Var, ParamRef)):
                    kind, compare = self._operand_policy(operand)
                    if compare is Compare.TERM and kind is not Kind.IRI:
                        raise IrError(
                            "WrongGuard",
                            f"{self.op.id}: a value comparison on a term-matched position ({_term_text(operand)}). "
                            "Declare it Compare.VALUE, or compare with a TermGuard",
                        )
            names = self._expr(expr.left, guard=guard, aggregate_ok=aggregate_ok) | self._expr(expr.right, guard=guard, aggregate_ok=aggregate_ok)
            self._clock_check(expr, guard)
            return names
        raise IrError("UnknownOperator", f"{self.op.id}: {expr!r} is not an expression")

    def _clock_check(self, expr, guard: bool) -> None:
        if guard and self._clocked(expr):
            raise IrError("ClockInGuard", f"{self.op.id}: NOW() reaches a guard, directly or through a BIND")

    def _func(self, f: Func, *, guard: bool, aggregate_ok: bool) -> set:
        name = f.name
        if name in AGGREGATES:
            if not aggregate_ok:
                raise IrError("AggregateOutsideSelect", f"{self.op.id}: {name} is allowed only in a SELECT list or HAVING")
            low, high = AGGREGATES[name]
        elif name in FUNCTIONS:
            low, high = FUNCTIONS[name]
        else:
            raise IrError("UnknownFunction", f"{self.op.id}: {name!r} is not a function the renderer supports")
        if not low <= len(f.args) <= high:
            raise IrError("UnknownFunction", f"{self.op.id}: {name} takes {low} to {high} arguments, got {len(f.args)}")
        if f.distinct and name not in AGGREGATES:
            raise IrError("UnknownFunction", f"{self.op.id}: DISTINCT applies to an aggregate, not {name}")
        if f.separator is not None and name != "GROUP_CONCAT":
            raise IrError("UnknownFunction", f"{self.op.id}: a separator applies to GROUP_CONCAT only")
        names: set = set()
        for arg in f.args:
            # An aggregate may sit inside a scalar function of a projection, such as IRI(MIN(STR(?x))), and never inside another aggregate.
            names |= self._expr(arg, guard=guard, aggregate_ok=aggregate_ok and name not in AGGREGATES)
        if name == "NOW" and guard:
            raise IrError("ClockInGuard", f"{self.op.id}: NOW() in a guard")
        return names

    # ---- select

    def _check_select(self, select: Select, *, sub: bool) -> None:
        """The rules of a ``SELECT`` that hold whether it is a query or a sub-select (ADR-A123, addendum of 2026-10-13)."""
        op = self.op.id
        if select.order_by or select.limit is not None or select.offset is not None:
            raise IrError("FragmentLimit", f"{op}: ORDER BY, LIMIT and OFFSET are outside the fragment, since an order differs by store and a limit makes a result depend on it")
        if select.distinct and sub:
            raise IrError("FragmentLimit", f"{op}: DISTINCT inside a sub-select is outside the fragment, since it changes the counts above it")
        for item in select.projection:
            if isinstance(item, Var):
                self._var(item)
            elif isinstance(item, Projected):
                if not isinstance(item.var, Var):
                    raise IrError("InvalidForm", f"{op}: a projected expression needs a Var to bind")
                self._var(item.var)
                self._expr(item.expr, guard=False, aggregate_ok=True)
            else:
                raise IrError("InvalidForm", f"{op}: a SELECT list holds Vars and Projected expressions, got {item!r}")
        for var in select.group_by:
            if not isinstance(var, Var):
                raise IrError("InvalidForm", f"{op}: GROUP BY holds Vars")
            self._var(var)
        grouped = {v.name for v in select.group_by}
        aggregating = bool(grouped) or any(isinstance(i, Projected) and _has_aggregate(i.expr) for i in select.projection) or bool(select.having)
        if aggregating:
            for item in select.projection:
                free = {item.name} if isinstance(item, Var) else _free_vars(item.expr)
                loose = free - grouped
                if loose:
                    raise IrError(
                        "UngroupedProjection",
                        f"{op}: ?{sorted(loose)[0]} is projected and is neither a GROUP BY key nor inside an aggregate. SPARQL refuses the query, "
                        "or a store may pick any value",
                    )
        for expr in select.having:
            self._expr(expr, guard=True, aggregate_ok=True)
            self._clock_check(expr, True)
            loose = _free_vars(expr) - grouped
            if loose:
                raise IrError(
                    "HavingNotGrouped",
                    f"{op}: ?{sorted(loose)[0]} in HAVING is neither a GROUP BY key nor inside an aggregate, so the test is an error "
                    "and the group is dropped with no message",
                )

    def _projection_bound(self, select: Select, mentioned: set) -> None:
        for name in [*(_projected_names(select) & {i.name for i in select.projection if isinstance(i, Var)}), *(v.name for v in select.group_by)]:
            if name not in mentioned:
                raise IrError("InvalidForm", f"{self.op.id}: ?{name} is projected or grouped and the WHERE never binds it")

    def _select_names(self, select: Select, inner: _Scope) -> tuple[set, set]:
        """The projected names of a sub-select that are bound in every solution, and those that may not be (the boundness
        table of the plan, 4.3). Only ``COUNT`` is bound over an empty group, and any other aggregate needs a ``GROUP BY``
        and an argument that is bound in every inner solution. A scalar function of an aggregate is bound when its arguments are."""
        definite: set = set()
        possible: set = set()
        for item in select.projection:
            if isinstance(item, Var):
                ok, name = item.name in inner.definite, item.name
            else:
                ok, name = self._projected_bound(item.expr, select, inner), item.var.name
            (definite if ok else possible).add(name)
        return definite, possible

    def _projected_bound(self, expr, select: Select, inner: _Scope) -> bool:
        if isinstance(expr, Func):
            if expr.name in AGGREGATES:
                return expr.name == "COUNT" or (bool(select.group_by) and self._definitely_bound(expr.args[0], inner))
            if expr.name == "COALESCE":
                return any(self._projected_bound(a, select, inner) for a in expr.args)
            return all(self._projected_bound(a, select, inner) for a in expr.args)
        if isinstance(expr, (Op, ValueGuard, TermGuard)):
            return self._projected_bound(expr.left, select, inner) and self._projected_bound(expr.right, select, inner)
        if isinstance(expr, Not):
            return self._projected_bound(expr.arg, select, inner)
        return self._definitely_bound(expr, inner)

    def _sub_select_leaks(self) -> None:
        if not self.subselects:
            return
        outside = _var_names(self.op)
        for sub in self.subselects:
            hidden = _var_names(sub, expand=sub) - _projected_names(sub.select)
            leaked = hidden & outside
            if leaked:
                raise IrError(
                    "SubSelectLeak",
                    f"{self.op.id}: ?{sorted(leaked)[0]} is used inside a sub-select and outside it without being projected. "
                    "The two are different variables, so the outer use is joined to nothing",
                )

    # ---- access

    def _access(self, graph: Graph, t: Triple, mode: str) -> Access:
        closure = isinstance(t.predicate, Path)
        return Access(graph.role.value, _term_text(graph.term), _term_text(t.subject), _term_text(t.predicate), closure, mode)


def _term_text(term) -> str:
    if isinstance(term, Var):
        return f"?{term.name}"
    if isinstance(term, ParamRef):
        return f"${term.name}"
    if isinstance(term, Const):
        return str(term.term)
    if isinstance(term, RdfType):
        return "a"
    if isinstance(term, Path):
        return str(term.path)
    raise IrError("UnencodedConstant", f"{term!r} is not a term")


def check(op: Operation) -> AccessSets:
    """Refuse an invalid operation, with the name of the rule. Returns what it reads and writes."""
    return _Checker(op).run()


def access_sets(op: Operation) -> AccessSets:
    """The graphs and subjects the operation reads (its ``WHERE``) and writes (its ``DELETE`` and ``INSERT``)."""
    return check(op)


# ---------------------------------------------------------------------------
# rendering

_PREFIXES = {"pat": str(PAT), "xsd": str(XSD)}
_IRI = re.compile(r"<([^<>\s]*)>")
_TYPED_LITERAL = re.compile(r'^(".*")\^\^(<[^<>\s]*>)$', re.S)
_LOCAL = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")


class _Out:
    """Collects the prefixes a rendering used, so only those are declared."""

    def __init__(self) -> None:
        self.used: set[str] = set()

    def compact(self, text: str) -> str:
        def repl(match: re.Match) -> str:
            iri = match.group(1)
            for prefix, ns in _PREFIXES.items():
                if iri.startswith(ns) and _LOCAL.match(iri[len(ns):]):
                    self.used.add(prefix)
                    return f"{prefix}:{iri[len(ns):]}"
            return match.group(0)

        return _IRI.sub(repl, text)

    def term(self, term) -> str:
        if isinstance(term, Var):
            return f"?{term.name}"
        if isinstance(term, ParamRef):
            return f"${term.name}"
        if isinstance(term, Const):
            return self._const(term.term)
        if isinstance(term, RdfType):
            return "a"
        if isinstance(term, Path):
            return self.compact(str(term.path))
        raise IrError("UnencodedConstant", f"{term!r} is not a term")

    def _const(self, term) -> str:
        """An IRI is compacted, and so is a literal's datatype. The value of a literal is never touched, since
        it may hold text that looks like an IRI."""
        text = str(term)
        if isinstance(term, Iri):
            return self.compact(text)
        typed = _TYPED_LITERAL.match(text)
        if typed:
            return f"{typed.group(1)}^^{self.compact(typed.group(2))}"
        return text

    # ---- expressions

    def expr(self, e, *, parent: Optional[str] = None) -> str:
        if isinstance(e, (Var, ParamRef, Const)):
            return self.term(e)
        if isinstance(e, Func):
            if e.name == "GROUP_CONCAT":
                sep = Literal.encode(e.separator if e.separator is not None else " ")
                inner = self.expr(e.args[0])
                return f"GROUP_CONCAT({'DISTINCT ' if e.distinct else ''}{inner}; separator={sep})"
            inner = ", ".join(self.expr(a) for a in e.args)
            return f"{e.name}({'DISTINCT ' if e.distinct else ''}{inner})"
        if isinstance(e, Not):
            return "!" + self._wrap(e.arg)
        if isinstance(e, TermGuard):
            text = f"sameTerm({self.expr(e.left)}, {self.expr(e.right)})"
            return ("!" + text) if e.negated else text
        if isinstance(e, ValueGuard):
            return f"{self._wrap(e.left)} {e.op} {self._wrap(e.right)}"
        if isinstance(e, Op):
            if e.op in _BOOLEAN:
                left = self.expr(e.left) if _same_op(e.left, e.op) or _comparison(e.left) else self._wrap(e.left)
                right = self.expr(e.right) if _same_op(e.right, e.op) or _comparison(e.right) else self._wrap(e.right)
            else:
                # Always parenthesise a nested operand, even a left one of the same precedence. SPARQL 1.1 reads `a - b + c`
                # as `(a - b) + c`, and Oxigraph 0.5.11 evaluates it as `a - (b + c)` (TSD-17).
                left, right = self._wrap(e.left), self._wrap(e.right)
            return f"{left} {e.op} {right}"
        raise IrError("UnknownOperator", f"{e!r} is not an expression")

    def _wrap(self, e) -> str:
        text = self.expr(e)
        if isinstance(e, (Op, ValueGuard, Not)) or (isinstance(e, TermGuard) and e.negated):
            return f"({text})"
        return text

    # ---- patterns

    def statements(self, elements) -> list[str]:
        """The lines of a group's elements. Consecutive triples of one subject share a statement."""
        lines: list[str] = []
        run: list[Triple] = []

        def flush(last: bool) -> None:
            if not run:
                return
            lines.append(self._triples(run) + ("" if last else " ."))
            run.clear()

        n = len(elements)
        for i, el in enumerate(elements):
            last = i == n - 1
            if isinstance(el, Triple):
                if run and run[-1].subject != el.subject:
                    flush(False)
                run.append(el)
                if last:
                    flush(True)
                continue
            flush(False)
            lines.extend(self.element(el))
        return lines

    def _triples(self, run: list[Triple]) -> str:
        parts = [f"{self.term(run[0].subject)} {self.term(run[0].predicate)} {self.term(run[0].object)}"]
        for t in run[1:]:
            parts.append(f"{self.term(t.predicate)} {self.term(t.object)}")
        return " ; ".join(parts)

    def braced(self, head: str, inner: list[str]) -> list[str]:
        if len(inner) == 1 and len(head) + len(inner[0]) < 88:
            return [f"{head} {{ {inner[0]} }}"]
        return [f"{head} {{", *("  " + line for line in inner), "}"]

    def element(self, el) -> list[str]:
        if isinstance(el, GraphBlock):
            return self.graph_block(el)
        if isinstance(el, PayloadSlot):
            return ["{{{" + el.param + "}}}"]
        if isinstance(el, Optional_):
            return self.braced("OPTIONAL", self.statements(el.group.elements))
        if isinstance(el, NotExists):
            return self.braced("FILTER NOT EXISTS", self.statements(el.group.elements))
        if isinstance(el, Filter):
            return [f"FILTER({self.expr(el.expr)})"]
        if isinstance(el, Bind):
            return [f"BIND({self.expr(el.expr)} AS ?{el.var.name})"]
        if isinstance(el, Values):
            items = " ".join(
                ("{{{" + i.param + "}}}") if isinstance(i, RegistrySlot) else self.term(i) for i in el.items
            )
            return [f"VALUES ?{el.var.name} {{ {items} }}"]
        if isinstance(el, SubSelect):
            block = self.braced("", self.select_lines(el.select, self.statements(el.where.elements)))
            block[0] = block[0].lstrip()
            return block
        if isinstance(el, RowValues):
            names = " ".join(f"?{v.name}" for v in el.vars)
            return ["VALUES (" + names + ") { {{{" + el.slot.param + "}}} }"]
        if isinstance(el, Union_):
            out: list[str] = []
            for i, g in enumerate(el.groups):
                block = self.braced("", self.statements(g.elements))
                block[0] = block[0].lstrip()
                if i:
                    out[-1] += " UNION " + block[0]
                    out.extend(block[1:])
                else:
                    out.extend(block)
            return out
        if isinstance(el, Group):
            block = self.braced("", self.statements(el.elements))
            block[0] = block[0].lstrip()
            return block
        raise IrError("UnsupportedInTemplate", f"{el!r} is not a pattern element")

    def select_lines(self, select: Select, where_lines: list[str]) -> list[str]:
        """``SELECT``, ``WHERE``, ``GROUP BY`` and ``HAVING`` of a query or a sub-select."""
        head = "SELECT " + ("DISTINCT " if select.distinct else "") + " ".join(self.projection(i) for i in select.projection)
        lines = [head, "WHERE {", *("  " + ln for ln in where_lines), "}"]
        if select.group_by:
            lines.append("GROUP BY " + " ".join(f"?{v.name}" for v in select.group_by))
        for h in select.having:
            lines.append(f"HAVING ({self.expr(h)})")
        return lines

    def projection(self, item) -> str:
        if isinstance(item, Var):
            return f"?{item.name}"
        return f"({self.expr(item.expr)} AS ?{item.var.name})"

    def graph_block(self, block: GraphBlock) -> list[str]:
        head = f"GRAPH {self.term(block.graph.term)}"
        return self.braced(head, self.statements(block.elements))


def _comparison(e) -> bool:
    return isinstance(e, (ValueGuard, TermGuard))


def _same_op(e, op: str) -> bool:
    return isinstance(e, Op) and e.op == op


def _guard_expr(op: Operation) -> Optional[Expr]:
    """The conjunction the required-parameter guard renders, or ``None`` when there is nothing to require. Each
    parameter gets one type test. An unbound parameter makes its test an error, which fails the filter."""
    conjuncts: list[Expr] = []
    for param in op.guard.params if op.guard else ():
        ref = ParamRef(param.name)
        if param.kind is Kind.IRI:
            conjuncts.append(Func("ISIRI", (ref,)))
        elif param.kind is Kind.IRI_OR_LITERAL:
            # any bound IRI or literal: a value the adopter owns, such as the valid time of an event
            conjuncts.append(Op("||", Func("ISIRI", (ref,)), Func("ISLITERAL", (ref,))))
        elif param.kind is Kind.LITERAL:
            # any literal without a language tag, so a timestamp of any datatype passes and an IRI or a missing value does not
            conjuncts.append(Op("&&", Func("ISLITERAL", (ref,)), ValueGuard("=", Func("LANG", (ref,)), Const(Literal.encode("")))))
        elif param.kind is Kind.LANG_STRING:
            conjuncts.append(ValueGuard("!=", Func("LANG", (ref,)), Const(Literal.encode(""))))
        elif param.kind in (Kind.LONG, Kind.POSITION):
            # Guard D (ADR-A123, addendum of 2026-10-13): the datatype is compared with what the store makes of an xsd:long
            # constant, so the test adapts to a store that does not keep numeric datatypes (TSD-07).
            conjuncts.append(ValueGuard("=", Func("DATATYPE", (ref,)), Func("DATATYPE", (Const(Literal.encode("0", datatype=str(XSD.long))),))))
        else:
            conjuncts.append(ValueGuard("=", Func("DATATYPE", (ref,)), Const(Iri.encode(str(_GUARD_DATATYPE[param.kind])))))
        if param.equals is not None:
            conjuncts.append(TermGuard(ref, param.equals))
    if not conjuncts:
        return None
    expr = conjuncts[0]
    for c in conjuncts[1:]:
        expr = Op("&&", expr, c)
    return expr


def render(op: Operation) -> str:
    """The SPARQL text of ``op``, after :func:`check` has accepted it."""
    check(op)
    out = _Out()
    where_elements = list(op.where.elements)
    guard = _guard_expr(op)
    if guard is not None:
        # A FILTER applies to the solutions of its whole group, after the group's patterns have matched. At the
        # top level a pattern such as `$root pat:seq $expectedSeq` would bind a missing $root from the data and
        # the guard would pass. In its own group the guard is tested before anything can bind the parameter.
        where_elements.insert(0, Group((Filter(guard),)))
    body: list[str] = []
    where_lines = out.statements(tuple(where_elements))
    if op.select is not None:
        body.extend(out.select_lines(op.select, where_lines))
    else:
        if op.delete:
            body.extend(_template_lines(out, "DELETE", op.delete))
        if op.insert:
            body.extend(_template_lines(out, "INSERT", op.insert))
        body.extend(["WHERE {", *("  " + ln for ln in where_lines), "}"])
    prefixes = [f"PREFIX {p}: <{_PREFIXES[p]}>" for p in sorted(out.used)]
    return "\n".join([*prefixes, *([""] if prefixes else []), *body]) + "\n"


def _template_lines(out: _Out, keyword: str, blocks: Iterable[GraphBlock]) -> list[str]:
    lines = [ln for b in blocks for ln in out.graph_block(b)]
    return [f"{keyword} {{", *("  " + ln for ln in lines), "}"]


__all__ = ["RULES", "FUNCTIONS", "AGGREGATES", "Access", "AccessSets", "check", "access_sets", "render"]
