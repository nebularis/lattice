# SPDX-License-Identifier: MPL-2.0
"""Cards: an ontology or vocabulary in one line per term, generated from its RDF, so a proposing model reads a layer in a
few thousand tokens and never the layer's whole specification. A card is deterministic, built in milliseconds, and never
stored, so it cannot drift from the graph it is read from."""

from __future__ import annotations

import functools
from dataclasses import dataclass
from typing import Iterable, Optional

from rdflib import Graph, URIRef
from rdflib.namespace import OWL, RDF, RDFS, SKOS

_KINDS = ((OWL.Class, "class"), (RDFS.Class, "class"), (OWL.ObjectProperty, "object property"),
          (OWL.DatatypeProperty, "datatype property"), (RDF.Property, "property"), (OWL.AnnotationProperty, None),
          (SKOS.Concept, "concept"), (OWL.NamedIndividual, "individual"))
_DEFINITIONS = (RDFS.comment, SKOS.definition)
_LABELS = (RDFS.label, SKOS.prefLabel)


@dataclass(frozen=True)
class Card:
    """One term: its CURIE, its kind, its label and the first sentence of its definition, and what places it."""

    iri: URIRef
    curie: str
    kind: str
    label: str
    definition: str
    places: tuple[str, ...]  # "sub X", "domain X", "range X", "broader X", "type X"

    def line(self) -> str:
        return " | ".join([self.curie, self.kind, self.label, self.definition, ", ".join(self.places)])


def _first_sentence(text: str, limit: int = 160) -> str:
    text = " ".join(text.split())
    end = text.find(". ")
    text = text if end < 0 else text[: end + 1]
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def _one(g: Graph, s, predicates) -> Optional[str]:
    for p in predicates:
        values = sorted((str(o) for o in g.objects(s, p)), key=lambda v: (len(v) == 0, v))
        english = [str(o) for o in g.objects(s, p) if getattr(o, "language", None) in (None, "en")]
        if english:
            return sorted(english)[0]
        if values:
            return values[0]
    return None


def cards(g: Graph, within: Optional[Iterable[str]] = None) -> list[Card]:
    """The cards of every named class, property, concept and individual of `g`, those under the namespaces `within`
    when it is given, sorted by CURIE."""
    nm = g.namespace_manager
    spaces = tuple(within) if within else None
    curie = lambda t: t.n3(nm) if isinstance(t, URIRef) else str(t)
    out = {}
    for rdf_type, kind in _KINDS:
        for s in g.subjects(RDF.type, rdf_type):
            if not isinstance(s, URIRef) or s in out or (spaces and not str(s).startswith(spaces)):
                continue
            if kind is None:
                out[s] = None
                continue
            places = [f"sub {curie(o)}" for o in sorted(g.objects(s, RDFS.subClassOf), key=str) if isinstance(o, URIRef)]
            places += [f"sub {curie(o)}" for o in sorted(g.objects(s, RDFS.subPropertyOf), key=str) if isinstance(o, URIRef)]
            places += [f"domain {curie(o)}" for o in sorted(g.objects(s, RDFS.domain), key=str) if isinstance(o, URIRef)]
            places += [f"range {curie(o)}" for o in sorted(g.objects(s, RDFS.range), key=str) if isinstance(o, URIRef)]
            places += [f"broader {curie(o)}" for o in sorted(g.objects(s, SKOS.broader), key=str)]
            if kind in ("individual", "concept"):
                places += [f"type {curie(o)}" for o in sorted(g.objects(s, RDF.type), key=str)
                           if isinstance(o, URIRef) and o not in (OWL.NamedIndividual, SKOS.Concept)]
            label = _one(g, s, _LABELS) or str(s).rsplit("#", 1)[-1].rsplit("/", 1)[-1]
            out[s] = Card(s, curie(s), kind, label, _first_sentence(_one(g, s, _DEFINITIONS) or ""), tuple(places))
    return sorted((c for c in out.values() if c is not None), key=lambda c: c.curie)


def render(title: str, entries: list[Card]) -> str:
    return "\n".join([f"# {title}", "# curie | kind | label | definition | placement", *(c.line() for c in entries)]) + "\n"


@functools.lru_cache(maxsize=None)
def _layer_graph(module: str) -> Graph:
    import lattice_repo_catalogue as reader

    catalogue = reader.load()
    g = Graph()
    for path in sorted((catalogue.root / catalogue.module(module).directory("spec")).glob("*.ttl")):
        g.parse(path, format="turtle")
    return g


def layer_card(module: str) -> list[Card]:
    """The cards of one LATTICE module's specification, its own terms only."""
    g = _layer_graph(module)
    own = {str(o) for o in g.subjects(RDF.type, OWL.Ontology)}
    namespaces = {ns for _, ns in g.namespace_manager.namespaces() if any(str(ns).startswith(o.rstrip("#/")) for o in own)}
    return cards(g, namespaces or None)


def source_card(g: Graph, within: Optional[Iterable[str]] = None) -> list[Card]:
    """The cards of a source vocabulary, such as ODRL's, read from its RDF."""
    return cards(g, within)


def codebook_card() -> str:
    """MCN's codebook in one line per code, the codes a proposal is written in."""
    import mcn_codebook as cb

    lines = ["# MCN codebook", "# code | term | family or group"]
    lines += [f"{code} | {spec.curie} | type, {spec.family}" for code, spec in sorted(cb.TYPES.items())]
    lines += [f"{code} | {spec.curie} | {spec.group or 'property'}" for code, spec in sorted(cb.PROPERTIES.items())]
    return "\n".join(lines) + "\n"
