# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""
A SHACL property path, as an expansion projection states its members (``srf:membersPath``, law ``srf:P20``).

The forms are SHACL's own, the ones ``sh:path`` takes: a property, a sequence, an alternative, an inverse, zero or more and one
or more. ``sh:zeroOrOnePath`` is not one an expansion states, since a statement that is at most one for each instance is no
expansion. A path is read from the contract's graph into a tree, and written as the text a MORK mapping's ``mork:dataRef``
reads, so no path is compiled by this layer.

An expansion's two named sources are paths too. A list's members, ``srf:ListMembers``, is ``<property>/rdf:rest*/rdf:first``
and a property's transitive closure, ``srf:TransitiveClosure``, is ``<property>+``, each over the property the expansion's
evidence binding names.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple, Union

from rdflib import BNode, Graph, URIRef

from .namespaces import RDF, SH


class PathError(ValueError):
    """A node that is no SHACL property path of the forms an expansion states."""


@dataclass(frozen=True)
class Property:
    iri: URIRef


@dataclass(frozen=True)
class Sequence:
    parts: Tuple["PathNode", ...]


@dataclass(frozen=True)
class Alternative:
    parts: Tuple["PathNode", ...]


@dataclass(frozen=True)
class Inverse:
    path: "PathNode"


@dataclass(frozen=True)
class ZeroOrMore:
    path: "PathNode"


@dataclass(frozen=True)
class OneOrMore:
    path: "PathNode"


PathNode = Union[Property, Sequence, Alternative, Inverse, ZeroOrMore, OneOrMore]

_UNARY = ((SH.inversePath, Inverse), (SH.zeroOrMorePath, ZeroOrMore), (SH.oneOrMorePath, OneOrMore))

#: The deepest a path may nest, which no contract needs and which stops a cycle in the graph from running without end.
MAX_DEPTH = 32


def read_path(graph: Graph, node, _depth: int = 0) -> PathNode:
    """The path a node states, as SHACL's ``sh:path`` does, or a ``PathError`` that says what is wrong."""
    if _depth > MAX_DEPTH:
        raise PathError("a path nested deeper than %d, or one that contains itself" % MAX_DEPTH)
    if isinstance(node, URIRef):
        return Property(node)
    if not isinstance(node, BNode):
        raise PathError(f"{node} is neither a property nor a blank node path")
    forms = [(predicate, kind) for predicate, kind in _UNARY if (node, predicate, None) in graph]
    alternative = (node, SH.alternativePath, None) in graph
    sequence = (node, RDF.first, None) in graph
    if len(forms) + int(alternative) + int(sequence) != 1:
        if (node, SH.zeroOrOnePath, None) in graph:
            raise PathError("sh:zeroOrOnePath is not a form an expansion states")
        raise PathError("a blank node that is not exactly one of a sequence, an alternative, an inverse, zero or more or one or more")
    if forms:
        predicate, kind = forms[0]
        values = list(graph.objects(node, predicate))
        if len(values) != 1:
            raise PathError(f"a path states {predicate} more than once")
        return kind(read_path(graph, values[0], _depth + 1))
    if alternative:
        values = list(graph.objects(node, SH.alternativePath))
        if len(values) != 1:
            raise PathError("a path states sh:alternativePath more than once")
        members = _members(graph, values[0], "an alternative")
        return Alternative(tuple(read_path(graph, member, _depth + 1) for member in members))
    members = _members(graph, node, "a sequence")
    return Sequence(tuple(read_path(graph, member, _depth + 1) for member in members))


def _members(graph: Graph, head, what: str) -> list:
    """The members of an RDF list, in order, at least two."""
    members = []
    seen = set()
    cell = head
    while cell != RDF.nil:
        if cell in seen or not isinstance(cell, BNode):
            raise PathError(f"{what} that is not a well-formed RDF list")
        seen.add(cell)
        firsts, rests = list(graph.objects(cell, RDF.first)), list(graph.objects(cell, RDF.rest))
        if len(firsts) != 1 or len(rests) != 1:
            raise PathError(f"{what} that is not a well-formed RDF list")
        members.append(firsts[0])
        cell = rests[0]
    if len(members) < 2:
        raise PathError(f"{what} of fewer than two members")
    return members


def properties(path: PathNode) -> frozenset:
    """Every property the path names."""
    if isinstance(path, Property):
        return frozenset({path.iri})
    if isinstance(path, (Sequence, Alternative)):
        return frozenset().union(*(properties(part) for part in path.parts))
    return properties(path.path)


def list_members(prop: URIRef) -> PathNode:
    """The members of the RDF list that a property holds, ``<property>/rdf:rest*/rdf:first``."""
    return Sequence((Property(prop), ZeroOrMore(Property(RDF.rest)), Property(RDF.first)))


def transitive_closure(prop: URIRef) -> PathNode:
    """What a property reaches by one or more steps, ``<property>+``."""
    return OneOrMore(Property(prop))


def text(path: PathNode) -> str:
    """The path as a MORK mapping writes it in ``mork:dataRef``, every IRI in full and a compound part inside a compound
    parenthesised."""
    if isinstance(path, Property):
        return f"<{path.iri}>"
    if isinstance(path, Sequence):
        return "/".join(_part(p) for p in path.parts)
    if isinstance(path, Alternative):
        return "|".join(_part(p) for p in path.parts)
    if isinstance(path, Inverse):
        return "^" + _atom(path.path)
    if isinstance(path, ZeroOrMore):
        return _atom(path.path) + "*"
    return _atom(path.path) + "+"


def _atom(path: PathNode) -> str:
    return text(path) if isinstance(path, Property) else f"({text(path)})"


def _part(path: PathNode) -> str:
    simple = isinstance(path, (Property, Inverse, ZeroOrMore, OneOrMore))
    return text(path) if simple else f"({text(path)})"
