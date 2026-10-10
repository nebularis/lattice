# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""Static checks over the SPARQL the compiler generates (formal-methods
track H, slice H1.3, review §12 and priority items S-3 and S-4).

Both read the text of each generated update after ``instantiate`` has filled
in the compile-time bindings, with no backend and no data.

S-3, unbound INSERT variables
    A variable in an INSERT template that is not bound in a solution makes
    the engine skip that triple silently, so a confirmation-outcome record can
    lose a field with no error. Every variable in an INSERT template must be a
    request-time parameter (written ``$name``, bound by the caller), bound in
    every solution of the WHERE clause, or listed with a reason in
    :data:`OPTIONAL_INSERT_VARIABLES`.

S-4, blank nodes in templates
    A blank node in an INSERT template is a fresh node on every solution and
    every execution, so a retry is not a no-op. In a DELETE template it is not
    legal at all. Neither may appear. Generated operations take skolemized
    payloads, so the payload slot is the caller's obligation and is not checked.

A construct this module cannot analyse is reported, never passed over.

Two assumptions, both decided 2026-10-09 (H-D11, H-D12, explained in plan
section 13 of docs/developer/plans/formal-methods-track-h.md) and both to be removed by the typed
IR of slice H2:

* A name written ``$name`` is taken to be supplied by the caller. The compiled profile does not list
  request-time parameters, so the convention is read from the text. A template author who writes
  ``$x`` where the WHERE clause should bind ``?x`` would escape the check.
* A BIND whose inputs are all bound is taken to give its variable a value. An expression can fail,
  for example when the caller omits a parameter, and the INSERT then skips its triples silently.
  Nothing here detects that. See TD-34 in docs/developer/plans/technical-debt.md.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Mapping

from rdflib import RDF, BNode, Graph, Variable
from rdflib.plugins.sparql.algebra import translateUpdate
from rdflib.plugins.sparql.parser import parseQuery, parseUpdate
from rdflib.plugins.sparql.parserutils import CompValue
from rdflib.term import Node

from .hygiene import VIOLATION, Finding
from .instantiate import _render_operation
from .namespaces import DAL
from .render import REQUEST_TIME_SLOTS

# Variables a template may leave unbound in an INSERT, by template file stem,
# each with the reason. An entry is a deliberate, reviewed exception and is
# checked for staleness, so it cannot outlive the variable it excuses.
_FIRST_CAS = (
    "a pre-created row has no pat:head before its first write, so its first revision has no previous "
    "revision and the pat:prevRev triple is correctly absent (guide §14.2)"
)
_FIRST_APPEND = (
    "a new stream has no pat:head before its first append, so its first revision has no previous "
    "revision and the pat:prevRev triple is correctly absent (guide §14.2)"
)
OPTIONAL_INSERT_VARIABLES: dict[str, dict[str, str]] = {
    "cas-replace-named-graph": {"prevRev": _FIRST_CAS},
    "cas-replace-named-graph-dataset-guard": {"prevRev": _FIRST_CAS},
    "cas-replace-composite-property": {"prevRev": _FIRST_CAS},
    "cas-replace-composite-property-dataset-guard": {"prevRev": _FIRST_CAS},
    "tombstone-delete-composite": {"prevRev": _FIRST_CAS},
    "tombstone-delete-composite-dataset-guard": {"prevRev": _FIRST_CAS},
    "tombstone-delete-named-graph": {"prevRev": _FIRST_CAS},
    "tombstone-delete-named-graph-dataset-guard": {"prevRev": _FIRST_CAS},
    "append-event": {"prev": _FIRST_APPEND},
    "append-event-dataset-guard": {"prev": _FIRST_APPEND},
}

# Stand-ins for the request-time slots, so the text parses as SPARQL. The
# payload is a ground triple. A real payload is skolemized by the caller.
_SLOT_STAND_INS = {
    "payloadTriples": "<urn:x-check:s> <urn:x-check:p> <urn:x-check:o> .",
    "logGraphs": "<urn:x-check:log>",
}

_COMMENT = re.compile(r"\{\{!.*?\}\}", re.S)
_PARAMETER = re.compile(r"\$(\w+)")
_STRING_OR_IRI = re.compile(r'"(?:[^"\\\n]|\\.)*"|\'(?:[^\'\\\n]|\\.)*\'|<[^<>\s]*>|#[^\n]*')


@dataclass(frozen=True)
class Operation:
    """One generated operation, ready to analyse."""

    target: str
    name: str
    template: str  # the template file stem
    text: str  # rendered, request-time slots filled with stand-ins


def operations(compiled: Graph) -> list[Operation]:
    """Every generated operation of every target in a compiled profile,
    rendered as ``instantiate`` renders it."""
    out: list[Operation] = []
    for profile in sorted(compiled.subjects(RDF.type, DAL.CompiledProfile), key=str):
        target = str(compiled.value(profile, DAL.forTarget)).rsplit("#", 1)[-1]
        deployment = compiled.value(profile, DAL.forDeployment)
        if deployment is not None:
            target += "@" + str(deployment).rsplit("#", 1)[-1]
        for node in sorted(compiled.objects(profile, DAL.generatedOperation), key=str):
            name, text = _render_operation(compiled, node, None)
            path = str(compiled.value(compiled.value(node, DAL.usesTemplate), DAL.templatePath))
            for slot in REQUEST_TIME_SLOTS:
                text = text.replace("{{{" + slot + "}}}", _SLOT_STAND_INS[slot])
            out.append(Operation(target, name, path.removesuffix(".mustache"), text))
    return out


# --------------------------------------------------------------------------
# which variables are bound in every solution


class _Unsupported(Exception):
    pass


def _variables(node) -> set[Variable]:
    """Every variable mentioned anywhere inside an expression or pattern."""
    if isinstance(node, Variable):
        return {node}
    found: set[Variable] = set()
    if isinstance(node, CompValue):
        for value in node.values():
            found |= _variables(value)
    elif isinstance(node, dict):
        for value in node.values():
            found |= _variables(value)
    elif isinstance(node, (list, tuple, set)):
        for value in node:
            found |= _variables(value)
    return found


def definitely_bound(node, parameters: frozenset[Variable]) -> set[Variable]:
    """Variables bound in every solution of a pattern, as rdflib's algebra
    describes it. Conservative: a variable that may be unbound is left out.

    A BIND counts as binding its variable when every variable in its
    expression is itself bound (a request parameter counts), on the
    assumption that an expression over bound inputs yields a value."""
    name = getattr(node, "name", None)
    if name == "BGP":
        return {t for triple in node.triples for t in triple if isinstance(t, Variable)}
    if name == "Join":
        return definitely_bound(node.p1, parameters) | definitely_bound(node.p2, parameters)
    if name in ("LeftJoin", "Minus"):
        return definitely_bound(node.p1, parameters)
    if name in ("Filter", "Distinct", "Reduced", "OrderBy", "Slice"):
        return definitely_bound(node.p, parameters)
    if name == "Extend":
        inner = definitely_bound(node.p, parameters)
        if _variables(node.expr) <= inner | parameters:
            inner = inner | {node.var}
        return inner
    if name == "Graph":
        inner = definitely_bound(node.p, parameters)
        return inner | ({node.term} if isinstance(node.term, Variable) else set())
    if name == "Union":
        return definitely_bound(node.p1, parameters) & definitely_bound(node.p2, parameters)
    if name == "ToMultiSet":
        return definitely_bound(node.p, parameters)
    if name == "values":
        rows = node.res
        if not rows:
            return set()
        # rdflib stores UNDEF as the plain string "UNDEF" (a Literal is a str subclass, so test the type)
        return set.intersection(*({k for k, v in row.items() if type(v) is not str} for row in rows))
    if name == "Project":
        return definitely_bound(node.p, parameters) & set(node.PV)
    if name == "Group":
        return set()  # a group key is bound by the Extend rdflib places above the aggregate
    if name == "AggregateJoin":
        # rdflib rewrites each aggregate to a hidden variable bound once per group
        return {aggregate.res for aggregate in node.A}
    raise _Unsupported(f"the algebra node {name!r}")


# --------------------------------------------------------------------------
# the two checks


def _clause(update: CompValue, name: str):
    """The INSERT or DELETE clause of a Modify, or ``None``. ``CompValue.get``
    returns the key itself for a missing one, so test for membership."""
    return update[name] if name in update else None


def _template_terms(clause) -> list[tuple[Node, tuple]]:
    """(graph name or None, triple) for every triple in an INSERT or DELETE clause."""
    if clause is None:
        return []
    out: list[tuple[Node, tuple]] = []
    for triple in clause.get("triples", []) or []:
        out.append((None, triple))
    for graph_name, triples in (clause.get("quads", {}) or {}).items():
        for triple in triples:
            out.append((graph_name, triple))
    return out


@dataclass(frozen=True)
class Issue:
    """A raw result of analysing one update, before an allowance is applied."""

    check: str
    message: str
    variable: str = ""


def analyse(text: str) -> list[Issue]:
    """S-3 and S-4 (and a parse check) over one generated update, with no allowances."""
    issues: list[Issue] = []
    try:
        updates = translateUpdate(parseUpdate(text)).algebra
    except Exception as error:  # not an update, or a syntax error
        try:
            parseQuery(text)
            return []  # a read-only query (an audit) has no INSERT or DELETE template
        except Exception:
            return [Issue("S-0", f"does not parse as SPARQL ({type(error).__name__}: {str(error)[:120]})")]

    cleaned = _STRING_OR_IRI.sub(" ", _COMMENT.sub("", text))
    parameters = frozenset(Variable(n) for n in _PARAMETER.findall(cleaned))

    for update in updates:
        kind = getattr(update, "name", "")
        if kind not in ("Modify", "InsertData", "DeleteData", "DeleteWhere"):
            continue  # LOAD, CLEAR, DROP and the like have no templates
        if kind == "Modify":
            insert, delete = _template_terms(_clause(update, "insert")), _template_terms(_clause(update, "delete"))
        elif kind == "InsertData":
            insert, delete = _template_terms(update), []
        else:
            insert, delete = [], _template_terms(update)

        for clause, terms in (("INSERT", insert), ("DELETE", delete)):
            for graph_name, triple in terms:
                for term in (*triple, graph_name):
                    if isinstance(term, BNode):
                        why = (
                            "a blank node is fresh on every solution, so a retry is not a no-op"
                            if clause == "INSERT"
                            else "a blank node is not legal in a DELETE template"
                        )
                        issues.append(Issue("S-4", f"{clause} template has a blank node ({why})", str(term)))

        if kind != "Modify":
            continue
        try:
            bound = definitely_bound(update.where, parameters)
        except _Unsupported as error:
            issues.append(Issue("S-3", f"cannot analyse the WHERE clause ({error}), so its INSERT variables are unchecked"))
            continue
        used: set[Variable] = set()
        for graph_name, triple in insert:
            used |= {t for t in (*triple, graph_name) if isinstance(t, Variable)}
        for variable in sorted(used - bound - parameters, key=str):
            issues.append(
                Issue(
                    "S-3",
                    f"INSERT uses ?{variable}, which is not bound in every solution and is not a $parameter, "
                    "so the triples that use it can be skipped silently",
                    str(variable),
                )
            )
    return issues


def check_text(text: str, template: str, label: str, allow: Mapping[str, Mapping[str, str]] | None = None) -> list[Finding]:
    """S-3 and S-4 over one generated update, with the template's allowances applied."""
    allowed = (OPTIONAL_INSERT_VARIABLES if allow is None else allow).get(template, {})
    return [
        Finding(issue.check, VIOLATION, (label,), f"{label}: {issue.message}")
        for issue in analyse(text)
        if not (issue.check == "S-3" and issue.variable in allowed)
    ]


def unbound_by_template(compiled: Graph) -> dict[str, set[str]]:
    """For each template used in a compiled profile, the INSERT variables it
    leaves unbound. This is what an allowance excuses."""
    seen: dict[str, set[str]] = {}
    for op in operations(compiled):
        variables = {i.variable for i in analyse(op.text) if i.check == "S-3" and i.variable}
        seen.setdefault(op.template, set()).update(variables)
    return seen


def stale_allowances(unbound: Mapping[str, set[str]], allow: Mapping[str, Mapping[str, str]] | None = None) -> list[Finding]:
    """An allowance for a variable that no template leaves unbound any more is
    stale. ``unbound`` is the union of :func:`unbound_by_template` over the
    whole corpus, since one compile uses only some of the templates."""
    allow = OPTIONAL_INSERT_VARIABLES if allow is None else allow
    return [
        Finding("S-3", VIOLATION, (template,), f"{template}: the allowance for ?{variable} is stale, it is no longer left unbound")
        for template, variables in sorted(allow.items())
        for variable in sorted(variables)
        if variable not in unbound.get(template, set())
    ]


def check_compiled(compiled: Graph, allow: Mapping[str, Mapping[str, str]] | None = None) -> list[Finding]:
    """S-3 and S-4 over every generated operation of a compiled profile."""
    findings: list[Finding] = []
    for op in operations(compiled):
        findings += check_text(op.text, op.template, f"{op.target}/{op.name}", allow)
    return sorted(set(findings))


__all__ = [
    "Issue",
    "OPTIONAL_INSERT_VARIABLES",
    "Operation",
    "analyse",
    "unbound_by_template",
    "check_compiled",
    "check_text",
    "definitely_bound",
    "operations",
    "stale_allowances",
]
