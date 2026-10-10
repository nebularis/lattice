# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""HO3: the ownership vocabulary and its shapes (formal-methods track H, slice HO3, ADR-A122).
Validation Pack: docs/developer/validation/FMH-HO3.md. Test IDs are HO3-Tn.

The compiler does not read ``dal:ownership`` yet (HO4 and HO5). These tests check the vocabulary and
the shapes that govern it."""

from __future__ import annotations

import pyshacl
import pytest
from rdflib import Graph, URIRef

from persistence import witness

from conftest import EXAMPLES_DIR

PREAMBLE = """
@prefix dal:  <https://www.nebularis.org/neuro-semantic/lattice/persistence#> .
@prefix ex:   <https://example.org/projects#> .
@prefix sh:   <http://www.w3.org/ns/shacl#> .
@prefix skos: <http://www.w3.org/2004/02/skos/core#> .
@prefix xsd:  <http://www.w3.org/2001/XMLSchema#> .
"""

# The reference configuration of the design sketch, section 10.1.
PROJECT = PREAMBLE + """
ex:ProjectClass a dal:ClassScope ; dal:targetClass ex:Project ; dal:priority "20"^^xsd:integer .
ex:ProjectBoundaryProfile a dal:AggregateBoundaryProfile ;
    dal:appliesTo ex:ProjectClass ; dal:strategy dal:CompositePropertyBoundary ;
    dal:boundaryShape ex:ProjectShape ; dal:dataGraph <urn:g:projects> .
ex:ProjectShape a sh:NodeShape ; sh:targetClass ex:Project ;
    sh:property [ sh:path ex:name ; sh:datatype xsd:string ] ,
                [ sh:path ex:forClient ; sh:class ex:Organisation ; dal:ownership dal:Reference ] ,
                [ sh:path ex:hasMilestone ; sh:node ex:MilestoneShape ; dal:ownership dal:Owned ] .
ex:MilestoneShape a sh:NodeShape ; sh:targetClass ex:Milestone ;
    sh:property [ sh:path ex:status ; sh:class skos:Concept ; dal:ownership dal:Vocabulary ] ,
                [ sh:path [ sh:inversePath ex:onMilestone ] ; sh:node ex:CommentShape ; dal:ownership dal:Owned ] .
ex:CommentShape a sh:NodeShape ; sh:targetClass ex:Comment .
"""


def _reporting(data_ttl: str) -> set[str]:
    """The local names of the node shapes of ``constraints.ttl`` that report on ``data_ttl``."""
    shapes = Graph().parse(witness.SHAPES_TTL, format="turtle")
    data = Graph().parse(witness.SPEC_TTL, format="turtle")
    data.parse(data=data_ttl, format="turtle")
    _, results, _ = pyshacl.validate(data, shacl_graph=shapes, inference="none", advanced=True, allow_warnings=True)
    sources = results.objects(None, URIRef("http://www.w3.org/ns/shacl#sourceShape"))
    owners = {witness._owning_shape(shapes, s) for s in sources}
    return {witness._local(o) for o in owners if o is not None}


def _profile(extra: str) -> str:
    return PREAMBLE + f"""
ex:C a dal:ClassScope ; dal:targetClass ex:Widget .
ex:P a dal:AggregateBoundaryProfile ; dal:appliesTo ex:C ; {extra} .
"""


def test_ho3_t1_an_ownership_that_is_not_one_of_the_three_kinds_is_reported():
    data = PREAMBLE + "ex:S a sh:NodeShape ; sh:property [ sh:path ex:a ; sh:node ex:T ; dal:ownership ex:Other ] ."
    assert "BoundaryOwnershipShape" in _reporting(data)


def test_ho3_t2_two_ownership_values_on_one_property_shape_are_reported():
    data = PREAMBLE + "ex:S a sh:NodeShape ; sh:property [ sh:path ex:a ; sh:node ex:T ; dal:ownership dal:Owned , dal:Reference ] ."
    assert "BoundaryOwnershipShape" in _reporting(data)


def test_ho3_t3_the_sketch_reference_configuration_is_reported_by_no_dal_shape():
    assert _reporting(PROJECT) == set()


def test_ho3_t4_a_reference_data_declaration_without_a_class_is_reported():
    assert "ReferenceDataShape" in _reporting(PREAMBLE + "ex:Currencies a dal:ReferenceData .")


def test_ho3_t5_a_reference_data_declaration_that_names_a_class_is_accepted():
    assert "ReferenceDataShape" not in _reporting(PREAMBLE + "ex:Currencies a dal:ReferenceData ; dal:coversClass ex:Currency .")


def test_ho3_t6_a_non_boolean_owns_reference_data_is_reported():
    data = _profile('dal:strategy dal:NamedGraphBoundary ; dal:ownsReferenceData "yes"')
    assert "AggregateBoundaryProfileShape" in _reporting(data)
    assert "AggregateBoundaryProfileShape" not in _reporting(_profile("dal:strategy dal:NamedGraphBoundary ; dal:ownsReferenceData true"))


def test_ho3_t8_a_composite_profile_needs_a_data_graph():
    composite = 'dal:strategy dal:CompositePropertyBoundary ; dal:boundaryShape ex:WShape'
    assert "CompositePropertyBoundaryRequiresDataGraphShape" in _reporting(_profile(composite))
    assert "CompositePropertyBoundaryRequiresDataGraphShape" not in _reporting(_profile(composite + " ; dal:dataGraph <urn:g:widgets>"))
    # a named-graph profile needs none
    assert "CompositePropertyBoundaryRequiresDataGraphShape" not in _reporting(_profile("dal:strategy dal:NamedGraphBoundary"))


def test_ho3_t9_dal_ownership_is_declared_without_a_domain_and_cover_class_without_one_either():
    spec = Graph().parse(witness.SPEC_TTL, format="turtle")
    rdfs = "http://www.w3.org/2000/01/rdf-schema#"
    dal = "https://www.nebularis.org/neuro-semantic/lattice/persistence#"
    assert list(spec.objects(URIRef(dal + "ownership"), URIRef(rdfs + "domain"))) == []
    assert list(spec.objects(URIRef(dal + "coversClass"), URIRef(rdfs + "domain"))) == []


def test_ho3_t10_max_traversal_depth_is_gone_from_the_spec_the_shapes_and_the_examples():
    for path in (witness.SPEC_TTL, witness.SHAPES_TTL, *EXAMPLES_DIR.glob("*.ttl")):
        assert "maxTraversalDepth" not in path.read_text(encoding="utf-8"), path.name
