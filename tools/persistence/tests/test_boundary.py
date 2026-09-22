# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""Walking a dal:boundaryShape (sketch §4.3): properties reachable within
the closure, and cycle detection."""

from __future__ import annotations

import pytest
from rdflib import RDF, Graph, URIRef

from persistence.boundary import BoundaryCycleError, walk_boundary_shape
from persistence.namespaces import SH

LENDING = "https://example.org/lending#"


def test_walks_nested_shape_into_composite_properties(example):
    g = example("composite-property-boundary-shacl.ttl")
    shape = URIRef(LENDING + "OrderAggregateShape")
    closure = walk_boundary_shape(g, shape)
    local_names = {str(p).rsplit("#", 1)[-1] for p in closure.composite_properties}
    assert local_names == {"lineItem", "sku"}
    assert URIRef(LENDING + "customer") not in closure.composite_properties


def test_detects_cycles():
    g = Graph()
    a, b = URIRef(LENDING + "A"), URIRef(LENDING + "B")
    prop_a, prop_b = URIRef(LENDING + "toB"), URIRef(LENDING + "toA")
    a_prop = URIRef(LENDING + "aProp")
    b_prop = URIRef(LENDING + "bProp")

    g.add((a, SH.property, a_prop))
    g.add((a_prop, SH.path, prop_a))
    g.add((a_prop, SH.node, b))

    g.add((b, SH.property, b_prop))
    g.add((b_prop, SH.path, prop_b))
    g.add((b_prop, SH.node, a))

    with pytest.raises(BoundaryCycleError):
        walk_boundary_shape(g, a)


def test_empty_shape_has_no_composite_properties():
    g = Graph()
    shape = URIRef(LENDING + "EmptyShape")
    closure = walk_boundary_shape(g, shape)
    assert closure.composite_properties == []
