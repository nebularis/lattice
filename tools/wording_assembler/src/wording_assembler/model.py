# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""Namespaces and the reads of a form's tree that every stage shares."""

from __future__ import annotations

import hashlib
from typing import Iterable, List

from rdflib import Graph, Namespace, URIRef
from rdflib.compare import to_isomorphic
from rdflib.namespace import RDF, RDFS

LATTICE = "https://www.nebularis.org/neuro-semantic/lattice/"
WRD = Namespace(LATTICE + "wording#")
WRD_VOC = Namespace(LATTICE + "wording/vocab#")
FND = Namespace(LATTICE + "foundation#")
ELG = Namespace(LATTICE + "eligibility#")
QNT = Namespace(LATTICE + "quantification#")

BASELINE_MODEL = WRD_VOC.BaselineAssemblyModel


def instances(graph: Graph, cls: URIRef) -> List[URIRef]:
    """Nodes of `cls` or a subclass, as the layer's shapes read it. `graph` holds the layer's spec."""
    found = set(graph.subjects(RDF.type, cls))
    for sub in graph.transitive_subjects(RDFS.subClassOf, cls):
        found.update(graph.subjects(RDF.type, sub))
    return sorted((n for n in found if isinstance(n, URIRef)), key=str)


def is_a(graph: Graph, node, cls: URIRef) -> bool:
    return any(c == cls or cls in set(graph.transitive_objects(c, RDFS.subClassOf)) for c in graph.objects(node, RDF.type))


def mode_of(graph: Graph, element) -> URIRef:
    return graph.value(element, WRD.inclusionMode) or WRD_VOC.Mandatory


def variants_of(graph: Graph, slot) -> List[URIRef]:
    return sorted(set(graph.objects(slot, WRD.hasVariant)), key=str)


def is_variant(graph: Graph, node) -> bool:
    return (None, WRD.hasVariant, node) in graph


def children(graph: Graph, node) -> List[URIRef]:
    """The ranked children of a node, in rank order, a slot's variants left out (they are alternatives)."""
    kids = {c for c in graph.objects(node, WRD.directlyComprises) if isinstance(c, URIRef) and not is_variant(graph, c)}
    return sorted(kids, key=lambda c: (str(graph.value(c, WRD.rankKey) or ""), str(c)))


def digest_of(graph: Graph) -> str:
    """A digest of a graph's canonical form, equal for isomorphic graphs."""
    return "sha256:" + hashlib.sha256(str(to_isomorphic(graph).internal_hash()).encode()).hexdigest()


def digest_text(lines: Iterable[str]) -> str:
    return "sha256:" + hashlib.sha256("\n".join(sorted(lines)).encode()).hexdigest()


def local(term) -> str:
    return str(term).rsplit("#", 1)[-1].rsplit("/", 1)[-1]
