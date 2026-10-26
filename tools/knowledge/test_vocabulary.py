# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""Tests that the knowledge index's T-Box honours the decisions of ADR-A134.

The vocabulary is outside the substrate release and only this repository consumes it, so nothing
else will catch a mistake in it. These tests stand in for that, and each one names the decision it
keeps rather than merely asserting a shape.
"""

from __future__ import annotations

from pathlib import Path

import pyoxigraph as ox
import pytest
import rdflib

TBOX = Path(__file__).resolve().parent / "knowledge.ttl"
KI = "https://www.nebularis.org/neuro-semantic/lattice/dev/knowledge#"
SKOS = "http://www.w3.org/2004/02/skos/core#"


@pytest.fixture(scope="module")
def graph() -> rdflib.Graph:
    g = rdflib.Graph()
    g.parse(TBOX, format="turtle")
    return g


def _local(term) -> str:
    return str(term).rsplit("#", 1)[-1]


def test_the_tbox_parses_in_the_strict_store_not_only_in_rdflib():
    """TSD-37: rdflib accepts IRIs that Oxigraph refuses, so a document validated only on rdflib
    can carry text no strict parser takes. This vocabulary is read by Oxigraph, so it is parsed
    there in the test rather than discovered at the first strict consumer."""
    store = ox.Store()
    store.load(path=str(TBOX), format=ox.RdfFormat.TURTLE)
    assert len(list(store.quads_for_pattern(None, None, None, None))) > 100


def test_every_property_states_a_domain_and_a_range(graph: rdflib.Graph):
    """ADR-A134 decision 5. SHACL cannot check what has no domain and range, and that is the whole
    reason for a T-Box rather than SKOS alone."""
    missing = graph.query(
        """
        PREFIX owl: <http://www.w3.org/2002/07/owl#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        SELECT ?p WHERE {
          { ?p a owl:ObjectProperty } UNION { ?p a owl:DatatypeProperty }
          FILTER (NOT EXISTS { ?p rdfs:domain ?d } || NOT EXISTS { ?p rdfs:range ?r })
        }"""
    )
    assert not [_local(r[0]) for r in missing]


def test_every_class_and_property_says_what_earns_it(graph: rdflib.Graph):
    """ADR-A134 decision 6. A class or property enters the T-Box only when a query or a check needs
    it, and the comment is where that justification is recorded. Without this test the decision is
    an intention rather than a rule, and the vocabulary grows by habit."""
    undocumented = graph.query(
        """
        PREFIX owl: <http://www.w3.org/2002/07/owl#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        SELECT ?t WHERE {
          { ?t a owl:Class } UNION { ?t a owl:ObjectProperty } UNION { ?t a owl:DatatypeProperty }
          FILTER NOT EXISTS { ?t rdfs:comment ?c }
        }"""
    )
    assert not sorted(_local(r[0]) for r in undocumented)


def test_the_derived_edge_is_the_only_one_and_is_marked_as_such(graph: rdflib.Graph):
    """ADR-A134 decision 7. A declared edge and a derived edge are different properties, and a SHACL
    constraint may read only declared ones. If a second derived property appears without its warning
    the distinction has quietly collapsed, and every check becomes as reliable as a co-mention."""
    derived = [
        _local(s)
        for s, _, o in graph.triples((None, rdflib.RDFS.comment, None))
        if "never evidence" in str(o)
    ]
    assert derived == ["citedWith"]


def test_the_facets_meet_the_skos_scheme(graph: rdflib.Graph):
    """The facet properties are where the T-Box meets the concept schemes of facets.ttl, so their
    range is a SKOS concept and not a class of this vocabulary."""
    for name in ("activity", "quality", "technology"):
        ranges = set(graph.objects(rdflib.URIRef(KI + name), rdflib.RDFS.range))
        assert ranges == {rdflib.URIRef(SKOS + "Concept")}, name


def test_every_node_kind_is_a_subclass_of_node(graph: rdflib.Graph):
    """A query selects by kind, and the claim, pointer and identifier properties have ki:Node as
    their domain, so a kind outside that hierarchy would carry none of them."""
    node = rdflib.URIRef(KI + "Node")
    kinds = {
        "Decision", "PendingDecision", "Debt", "Discovery", "Standard",
        "Pattern", "Mechanism", "Principle", "Epic", "Slice", "Question",
    }
    for kind in kinds:
        assert (rdflib.URIRef(KI + kind), rdflib.RDFS.subClassOf, node) in graph, kind


def test_status_is_a_closed_set_of_typed_individuals(graph: rdflib.Graph):
    """ADR-A134 decisions 5 and 6. The fifteen literal Status strings across the 120 decisions
    normalise to these five, and no decision's line opens with Rejected, Withdrawn, Deferred or
    Complete, all four of which an earlier draft declared. A status declared in anticipation makes
    the vocabulary wider than the corpus, so one is added when a document first uses it."""
    statuses = {_local(s) for s in graph.subjects(rdflib.RDF.type, rdflib.URIRef(KI + "Status"))}
    assert statuses == {"Proposed", "Accepted", "Superseded", "Open"}


def test_the_vocabulary_sits_outside_the_substrate_release(graph: rdflib.Graph):
    """ADR-A134 decision 4. It describes this repository rather than the domain, and a published
    document may not cite a working one (ADR-A127), so it is outside ontology/ and outside the
    release of ADR-A129. The dev path segment is what marks that, and the file's location is what
    keeps it true."""
    ontologies = list(graph.subjects(rdflib.RDF.type, rdflib.OWL.Ontology))
    assert len(ontologies) == 1
    assert "/dev/knowledge" in str(ontologies[0])
    assert TBOX.parent.name == "knowledge" and TBOX.parent.parent.name == "tools"
