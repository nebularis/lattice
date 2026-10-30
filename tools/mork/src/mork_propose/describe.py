# SPDX-License-Identifier: MPL-2.0
"""One LATTICE term read deeply, where a card reads it in one line: its comment and its utility in full, where it sits,
the properties whose domain or range it is, its individuals, and the message of every shape that names it, which is
where a layer states the laws a mapping must keep. A proposing agent reads twenty terms this way rather than every
layer at length, so what it reads grows with the source and not with LATTICE."""

from __future__ import annotations

import functools
import re
from typing import Iterable, Optional

from rdflib import Graph, URIRef
from rdflib.namespace import OWL, RDF, RDFS, SH, SKOS

from .cards import _layer_graph, _one

FND_UTILITY = URIRef("https://www.nebularis.org/neuro-semantic/lattice/foundation#utility")


@functools.lru_cache(maxsize=None)
def _shapes(module: str) -> Graph:
    import lattice_repo_catalogue as reader

    catalogue = reader.load()
    g = Graph()
    try:
        folder = catalogue.root / catalogue.module(module).directory("shapes")
    except (KeyError, ValueError):
        return g  # a module with no shapes
    for path in sorted(folder.glob("*.ttl")):
        g.parse(path, format="turtle")
    return g


def _members(g: Graph, node) -> list:
    """A class, or the members of an owl:unionOf."""
    if isinstance(node, URIRef):
        return [node]
    union = g.value(node, OWL.unionOf)
    return [m for m in g.items(union)] if union is not None else []


def _resolve(term: str, graphs: Iterable[Graph]) -> Optional[URIRef]:
    if "://" in term or term.startswith("urn:"):
        return URIRef(term)
    prefix, _, local = term.partition(":")
    for g in graphs:
        for p, ns in g.namespaces():
            if p == prefix:
                return URIRef(str(ns) + local)
    return None


def _messages(shapes: Graph, term: URIRef, curie: str) -> list[str]:
    """The message of each shape that targets the term, constrains it as a path or a class, lists it, or names it in its
    SPARQL, the nearest node's message first and never a message twice."""
    found: list[str] = []

    def add(node) -> None:
        for m in sorted(str(x) for x in shapes.objects(node, SH.message)):
            if m not in found:
                found.append(m)

    for shape in sorted(shapes.subjects(SH.targetClass, term), key=str):
        add(shape)
        for p in shapes.objects(shape, SH.property):
            add(p)
        for c in shapes.objects(shape, SH.sparql):
            add(c)
    for pred in (SH.path, SH["class"], SH.hasValue):
        for node in sorted(shapes.subjects(pred, term), key=str):
            add(node)
    # A name ends where a name character does not follow, so pty:Role never matches pty:RoleOccupancy.
    named = re.compile("(?:" + "|".join(re.escape(n) for n in (f"<{term}>", curie) if n) + r")(?![A-Za-z0-9_-])")
    for node, text in shapes.subject_objects(SH.select):
        if named.search(str(text)):
            add(node)
    return found


def describe_term(term: str, layers: Iterable[str]) -> str:
    """The term, a CURIE such as ins:Permission or a full IRI, as it is declared in one of `layers`."""
    layers = list(layers)
    graphs = {m: _layer_graph(m) for m in layers}
    iri = _resolve(term, graphs.values())
    owner = next((m for m, g in graphs.items() if iri is not None and (iri, RDF.type, None) in g), None)
    if owner is None:
        raise ValueError(f"no layer of {', '.join(layers)} declares {term}")
    g = graphs[owner]
    world = Graph()
    for other in graphs.values():
        world += other
    nm = g.namespace_manager
    curie = lambda t: t.n3(nm) if isinstance(t, URIRef) else "a combination"
    kinds = sorted(curie(t) for t in g.objects(iri, RDF.type))
    lines = [f"# {curie(iri)} ({', '.join(kinds)}), in {owner}", f"label: {_one(g, iri, (RDFS.label, SKOS.prefLabel)) or '-'}"]
    for name, predicates in (("comment", (RDFS.comment, SKOS.definition)), ("utility", (FND_UTILITY,))):
        text = _one(g, iri, predicates)
        if text:
            lines.append(f"{name}: {' '.join(text.split())}")
    for name, pred in (("sub", RDFS.subClassOf), ("sub", RDFS.subPropertyOf), ("domain", RDFS.domain), ("range", RDFS.range),
                       ("inverse of", OWL.inverseOf), ("broader", SKOS.broader)):
        values = [curie(o) for o in sorted(g.objects(iri, pred), key=str) if isinstance(o, URIRef)]
        if values:
            lines.append(f"{name}: {', '.join(values)}")
    narrower = sorted(curie(s) for s in world.subjects(RDFS.subClassOf, iri) if isinstance(s, URIRef))
    if narrower:
        lines.append(f"narrower: {', '.join(narrower)}")
    as_domain = sorted({curie(p) + (f" -> {curie(world.value(p, RDFS.range))}" if world.value(p, RDFS.range) is not None else "")
                        for p, d in world.subject_objects(RDFS.domain) if iri in _members(world, d)})
    as_range = sorted({curie(p) + (f" from {curie(world.value(p, RDFS.domain))}" if world.value(p, RDFS.domain) is not None else "")
                       for p, r in world.subject_objects(RDFS.range) if iri in _members(world, r)})
    if as_domain:
        lines.append("properties of it: " + "; ".join(as_domain))
    if as_range:
        lines.append("properties to it: " + "; ".join(as_range))
    individuals = sorted(curie(s) for s in world.subjects(RDF.type, iri) if isinstance(s, URIRef))
    if individuals:
        lines.append(f"individuals: {', '.join(individuals)}")
    shapes = Graph()
    for m in layers:
        shapes += _shapes(m)
    messages = _messages(shapes, iri, curie(iri))
    if messages:
        lines.append("laws and shapes:")
        lines += [f"- {' '.join(m.split())}" for m in messages]
    return "\n".join(lines) + "\n"
