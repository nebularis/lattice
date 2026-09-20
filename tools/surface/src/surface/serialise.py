# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""
Deterministic Turtle output.

Parsing is rdflib's; writing is not. rdflib's Turtle serialiser makes no
ordering or blank-node-labelling guarantee across runs, and a generated estate
whose diffs move for no semantic reason cannot support law ``srf:R3`` — a
scoped change must leave every other surface byte-identical, and that has to be
observable by comparing files rather than by rehashing everything.

So this writer sorts subjects, predicates and objects, and renders the blank
nodes the compiler minted under the labels it minted them with. The compiler
derives those labels from the term they belong to, so they are stable across
runs without being meaningful. Hashing does not depend on any of this: the
canonical form in ``canonical.py`` relabels blank nodes by graph position.
"""

from __future__ import annotations

from typing import Dict, Iterable, List, Sequence, Tuple

from rdflib import BNode, Graph, Literal, URIRef
from rdflib.namespace import NamespaceManager
from rdflib.term import Node

from .namespaces import RDF


def _sort_key(term: Node) -> Tuple[int, str, str, str]:
    """A total order over terms, so that emission order never varies."""
    if isinstance(term, URIRef):
        return (0, str(term), "", "")
    if isinstance(term, BNode):
        return (1, str(term), "", "")
    if isinstance(term, Literal):
        return (
            2,
            str(term),
            str(term.datatype) if term.datatype else "",
            str(term.language) if term.language else "",
        )
    return (3, str(term), "", "")


def _render(term: Node, manager: NamespaceManager) -> str:
    if isinstance(term, BNode):
        return f"_:{term}"
    return term.n3(manager)


def serialise(
    graph: Graph,
    prefixes: Dict[str, object],
    header: Sequence[str] = (),
) -> str:
    """Render a graph as Turtle, deterministically, grouped by subject."""
    manager = NamespaceManager(Graph())
    for prefix, namespace in prefixes.items():
        manager.bind(prefix, namespace, override=True, replace=True)

    lines: List[str] = list(header)
    for prefix, namespace in sorted(prefixes.items()):
        lines.append(f"@prefix {prefix}: <{namespace}> .")
    lines.append("")

    grouped: Dict[Tuple, List[Tuple[Node, Node, Node]]] = {}
    for triple in graph:
        grouped.setdefault(_sort_key(triple[0]), []).append(triple)

    for _, triples in sorted(grouped.items()):
        subject = triples[0][0]
        by_predicate: Dict[str, List[Node]] = {}
        for _, predicate, obj in triples:
            by_predicate.setdefault(str(predicate), []).append(obj)

        rendered: List[str] = []
        type_iri = str(RDF.type)
        for predicate in sorted(by_predicate, key=lambda p: (p != type_iri, p)):
            objects = sorted(by_predicate[predicate], key=_sort_key)
            written = " , ".join(_render(o, manager) for o in objects)
            name = "a" if predicate == type_iri else _render(URIRef(predicate), manager)
            rendered.append(f"    {name} {written}")

        lines.append(_render(subject, manager))
        lines.append(" ;\n".join(rendered) + " .")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def parse_files(paths: Iterable[str], graph: Graph | None = None) -> Graph:
    """Parse one or more Turtle files into a single graph."""
    graph = graph if graph is not None else Graph()
    for path in paths:
        graph.parse(source=str(path), format="turtle")
    return graph
