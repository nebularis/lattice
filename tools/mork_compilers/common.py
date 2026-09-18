# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""
Shared MORK backend-compiler core (ADR-A19, ADR-A23).

Every backend compiler in this package reads the same two things out of a
MORK mapping graph: a mapping's resolved parameter bindings, and the order
in which a batch of mappings must compile relative to one another
(``mork:dependsOnMapping`` — "Compositional dependency ensuring that target
concepts exist before the GenerativeMapping is compiled", per
``mork/spec/Mork.ttl``). Reading either one is duplicated once per backend
without a shared module.

Kept independent of ``tools/surface``: that package's equivalent helpers
(``tools/surface/mork.py``'s ``_parameters``, ``tools/surface/lowering.py``'s
``contract_parameter_bindings``) read a Surface contract's shape, not a
generic MORK mapping's, and this package has no dependency on Surface.
"""

from __future__ import annotations

from typing import Dict, List, Set, Tuple

from rdflib import Graph, URIRef

from .namespaces import MORK


class DependencyCycleError(ValueError):
    """``mork:dependsOnMapping`` is cyclic within the given batch; no order exists."""


def local_name(iri: str) -> str:
    """The fragment after '#', or the segment after the final '/'."""
    text = str(iri)
    if "#" in text:
        return text.rsplit("#", 1)[1]
    return text.rstrip("/").rsplit("/", 1)[-1]


def mint(iri, suffix: str) -> URIRef:
    """Mint a sibling identifier next to ``iri``, e.g. ``.../x`` + ``execplan`` -> ``.../x-execplan``.

    Shared by every backend in this package so a condition's plan, mapping,
    and artefact identifiers are minted the same way regardless of which
    backend produced them.
    """
    text = str(iri)
    if "#" in text:
        base, key = text.rsplit("#", 1)
        return URIRef(f"{base}#{key}-{suffix}")
    base, key = text.rstrip("/").rsplit("/", 1)
    return URIRef(f"{base}/{key}-{suffix}")


def resolve_parameters(graph: Graph, mapping: URIRef) -> Dict[str, object]:
    """Every ``mork:hasParameterBinding`` on a mapping, by ``paramName``."""
    resolved: Dict[str, object] = {}
    for node in graph.objects(mapping, MORK.hasParameterBinding):
        name = graph.value(node, MORK.paramName)
        value = graph.value(node, MORK.paramValue)
        if name is not None:
            resolved[str(name)] = value
    return resolved


def dependency_order(graph: Graph, mappings: List[URIRef]) -> List[URIRef]:
    """A topological order over ``mork:dependsOnMapping`` within ``mappings``.

    A dependency outside ``mappings`` is not this function's concern — the
    caller is compiling a batch, not necessarily the whole mapping graph, and
    a dependency belonging to an already-compiled or separate batch is
    resolved (or not) by the caller, not by this ordering.

    Deterministic: mappings are visited in IRI order, and each mapping's own
    dependency edges are visited in IRI order, so the same batch always
    orders the same way.
    """
    remaining: Set[str] = {str(m) for m in mappings}
    by_str = {str(m): m for m in mappings}
    edges: Dict[str, List[str]] = {s: [] for s in remaining}
    for mapping in mappings:
        for dep in graph.objects(mapping, MORK.dependsOnMapping):
            if str(dep) in remaining:
                edges[str(mapping)].append(str(dep))

    ordered: List[URIRef] = []
    visited: Set[str] = set()

    def visit(node: str, trail: Tuple[str, ...]) -> None:
        if node in visited:
            return
        if node in trail:
            raise DependencyCycleError(
                "mork:dependsOnMapping is cyclic: " + " -> ".join(trail + (node,))
            )
        for dep in sorted(edges.get(node, [])):
            visit(dep, trail + (node,))
        visited.add(node)
        ordered.append(by_str[node])

    for node in sorted(remaining):
        visit(node, ())

    return ordered
