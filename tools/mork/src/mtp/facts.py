"""Extract stable teaching-pack facts from the normative MORK ontology."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

from rdflib import Graph, URIRef
from rdflib.compare import to_isomorphic
from rdflib.namespace import OWL, RDF, RDFS


@dataclass(frozen=True)
class Term:
    iri: str
    kinds: tuple[str, ...]
    logical_hash: str


@dataclass(frozen=True)
class Axiom:
    subject: str
    predicate: str
    object: str
    fingerprint: str


@dataclass(frozen=True)
class Facts:
    graph_hash: str
    terms: tuple[Term, ...]
    axioms: tuple[Axiom, ...]


LOGICAL_PREDICATES = {RDFS.subClassOf, RDFS.subPropertyOf, RDFS.domain, RDFS.range, OWL.equivalentClass, OWL.equivalentProperty, OWL.disjointWith, RDF.type}


def graph_hash(graph: Graph) -> str:
    return _hash(str(to_isomorphic(graph).graph_digest()))


def term_hash(graph: Graph, iri: URIRef) -> str:
    logical_graph = Graph()
    for _, predicate, object in graph.triples((iri, None, None)):
        if predicate in LOGICAL_PREDICATES:
            logical_graph.add((iri, predicate, object))
    for subject, predicate, _ in graph.triples((None, OWL.inverseOf, iri)):
        logical_graph.add((subject, predicate, iri))
    return _hash(str(to_isomorphic(logical_graph).graph_digest()))


def extract(path: Path) -> Facts:
    graph = Graph().parse(path, format="turtle")
    namespace = "http://www.nebularis.org/ontologies/Mork#"
    iris = sorted({term for triple in graph for term in triple if isinstance(term, URIRef) and str(term).startswith(namespace)}, key=str)
    terms = tuple(Term(str(iri), tuple(sorted(str(kind) for kind in graph.objects(iri, RDF.type))), term_hash(graph, iri)) for iri in iris)
    axioms = []
    for subject, predicate, object in graph:
        if predicate in LOGICAL_PREDICATES or predicate in {OWL.inverseOf, OWL.members}:
            text = f"{subject.n3()} {predicate.n3()} {object.n3()}"
            axioms.append(Axiom(str(subject), str(predicate), str(object), _hash(text)))
    return Facts(graph_hash(graph), terms, tuple(sorted(axioms, key=lambda axiom: axiom.fingerprint)))


def _hash(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()