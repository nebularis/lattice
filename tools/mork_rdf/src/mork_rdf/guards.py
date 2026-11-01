# SPDX-License-Identifier: MPL-2.0
"""A mapping's guard, a SHACL node shape (`mork:appliesWhen`), compiled to a SPARQL expression that holds of a focus node
exactly when the node conforms to the shape (README §7.7). Only the constraint components listed in `_PROPERTY` and
`_NODE` are compiled, and any other is refused by name, since a guard compiled in part would admit nodes the shape
does not."""

from __future__ import annotations

from typing import Callable

from rdflib import BNode, Graph, Literal, URIRef
from rdflib.collection import Collection
from rdflib.namespace import RDF, RDFS, SH

# What a guard may say without changing what it admits.
_IGNORED = {RDF.type, SH.name, SH.description, SH.message, SH.severity, SH.order, SH.group, RDFS.label, RDFS.comment}
_EACH = {SH["in"], SH["class"], SH.datatype, SH.nodeKind}  # met by each value
_PROPERTY = _EACH | {SH.path, SH.minCount, SH.maxCount, SH.hasValue}
_NODE = _EACH | {SH.hasValue, SH.property, SH["not"], SH["and"], SH["or"]}
_KINDS = {SH.IRI: "isIRI({v})", SH.Literal: "isLiteral({v})", SH.BlankNode: "isBlank({v})",
          SH.BlankNodeOrIRI: "(isBlank({v}) || isIRI({v}))", SH.BlankNodeOrLiteral: "(isBlank({v}) || isLiteral({v}))",
          SH.IRIOrLiteral: "(isIRI({v}) || isLiteral({v}))"}


class GuardError(ValueError):
    pass


def compile_guard(g: Graph, shape, focus: str, term: Callable, var: Callable) -> str:
    """The expression that holds of `focus` exactly when it conforms to `shape`. `term` writes an RDF term as SPARQL,
    checked, and `var` mints a fresh variable."""
    return _node(g, shape, focus, term, var, ())


def _list(g: Graph, node) -> list:
    if node == RDF.nil:
        return []
    return list(Collection(g, node))


def _check(g: Graph, node, allowed: set, what: str) -> None:
    for p in set(g.predicates(node, None)):
        if p in _IGNORED or p in allowed:
            continue
        raise GuardError(f"{what} uses {p.n3()}, which a guard cannot yet compile")


def _node(g: Graph, shape, focus: str, term, var, seen: tuple) -> str:
    if shape in seen:
        raise GuardError("the guard's shapes refer to themselves")
    seen = seen + (shape,)
    if not isinstance(shape, (URIRef, BNode)):
        raise GuardError(f"{shape!r} is not a shape")
    _check(g, shape, _NODE, "a node shape")
    parts = [_values(g, shape, focus, term)] if any((shape, p, None) in g for p in _EACH) else []
    parts += [_same(focus, value, term) for value in g.objects(shape, SH.hasValue)]
    for prop in sorted(g.objects(shape, SH.property), key=str):
        parts.append(_property(g, prop, focus, term, var))
    for inner in g.objects(shape, SH["not"]):
        parts.append(f"!({_node(g, inner, focus, term, var, seen)})")
    for members in g.objects(shape, SH["and"]):
        parts.append("(" + " && ".join(_node(g, m, focus, term, var, seen) for m in _list(g, members)) + ")" if _list(g, members) else "true")
    for members in g.objects(shape, SH["or"]):
        parts.append("(" + " || ".join(_node(g, m, focus, term, var, seen) for m in _list(g, members)) + ")" if _list(g, members) else "false")
    return " && ".join(f"({p})" for p in parts) if parts else "true"


def _path(g: Graph, prop, term) -> str:
    path = g.value(prop, SH.path)
    if isinstance(path, URIRef):
        return term(path)
    if isinstance(path, BNode) and isinstance(g.value(path, SH.inversePath), URIRef) and len(set(g.predicates(path, None))) == 1:
        return "^" + term(g.value(path, SH.inversePath))
    raise GuardError("a guard's property shape names its sh:path as one property or the sh:inversePath of one")


def _property(g: Graph, prop, focus: str, term, var) -> str:
    _check(g, prop, _PROPERTY, "a property shape")
    path = _path(g, prop, term)
    parts = []
    lo, hi = g.value(prop, SH.minCount), g.value(prop, SH.maxCount)
    for bound, name in ((lo, "sh:minCount"), (hi, "sh:maxCount")):
        if bound is not None and int(bound) not in (0, 1):
            raise GuardError(f"a guard's {name} is 0 or 1, since a count beyond one cannot be tested inside a filter on every engine alike")
    if lo is not None and int(lo) == 1:
        parts.append(f"EXISTS {{ {focus} {path} {var('any')} . }}")
    if hi is not None:
        a, b = var("a"), var("b")
        parts.append(f"NOT EXISTS {{ {focus} {path} {a} . }}" if int(hi) == 0
                     else f"NOT EXISTS {{ {focus} {path} {a} , {b} . FILTER ({a} != {b}) }}")
    for value in g.objects(prop, SH.hasValue):
        parts.append(f"EXISTS {{ {focus} {path} {term(value)} . }}")
    if any((prop, p, None) in g for p in _EACH):
        value = var("value")
        # Every value conforms: no value fails the value constraints, so a node with no value conforms, as in SHACL.
        parts.append(f"NOT EXISTS {{ {focus} {path} {value} . FILTER (!({_values(g, prop, value, term)})) }}")
    return " && ".join(f"({p})" for p in parts) if parts else "true"


def _same(v: str, value, term) -> str:
    return f"sameTerm({v}, {term(value)})"


def _values(g: Graph, shape, v: str, term) -> str:
    """The constraints each value meets, the value being the focus itself for a node shape or one value of a path.
    Membership is by RDF term, as SHACL's sh:in is, never by value."""
    parts = []
    for members in g.objects(shape, SH["in"]):
        listed = _list(g, members)
        parts.append("(" + " || ".join(_same(v, m, term) for m in listed) + ")" if listed else "false")
    for cls in g.objects(shape, SH["class"]):
        parts.append(f"EXISTS {{ {v} {term(RDF.type)}/{term(RDFS.subClassOf)}* {term(cls)} . }}")
    for dt in g.objects(shape, SH.datatype):
        parts.append(f"(isLiteral({v}) && DATATYPE({v}) = {term(dt)})")
    for kind in g.objects(shape, SH.nodeKind):
        if kind not in _KINDS:
            raise GuardError(f"{kind.n3()} is not a node kind")
        parts.append(_KINDS[kind].format(v=v))
    return " && ".join(parts) if parts else "true"
