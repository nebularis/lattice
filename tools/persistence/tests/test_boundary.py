# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""Reading a dal:boundaryShape as a classified tree (ADR-A122, sketch §4). The tree's own tests,
and the project fixture's, are in test_ownership_tree.py."""

from __future__ import annotations

from rdflib import Graph, URIRef

from persistence.boundary import walk_ownership

LENDING = "https://example.org/lending#"


def test_walks_a_nested_shape_into_owned_edges_and_value_properties(example):
    g = example("composite-property-boundary-shacl.ttl")
    tree = walk_ownership(g, URIRef(LENDING + "OrderAggregateShape"))
    assert {str(e.step.predicate).rsplit("#", 1)[-1] for e in tree.owned_edges()} == {"lineItem"}
    assert {str(p).rsplit("#", 1)[-1] for p in tree.predicates()} == {"lineItem", "sku"}
    assert URIRef(LENDING + "customer") not in tree.predicates()


def test_a_shape_that_leads_back_to_itself_is_walked_once_and_is_not_refused():
    """Recursion is allowed (ADR-A122 decision 2). It replaces the cycle check of the old walk."""
    g = Graph()
    g.parse(
        data="""
        @prefix sh: <http://www.w3.org/ns/shacl#> .
        @prefix dal: <https://www.nebularis.org/neuro-semantic/lattice/persistence#> .
        @prefix ex: <https://example.org/lending#> .
        ex:A sh:property [ sh:path ex:toB ; sh:node ex:B ; dal:ownership dal:Owned ] .
        ex:B sh:property [ sh:path ex:toA ; sh:node ex:A ; dal:ownership dal:Owned ] .
        """,
        format="turtle",
    )
    tree = walk_ownership(g, URIRef(LENDING + "A"))
    assert tree.shapes == [URIRef(LENDING + "A"), URIRef(LENDING + "B")]
    assert tree.owned_path() is not None


def test_an_empty_shape_has_no_edges_and_no_path():
    tree = walk_ownership(Graph(), URIRef(LENDING + "EmptyShape"))
    assert tree.edges == [] and tree.owned_path() is None
