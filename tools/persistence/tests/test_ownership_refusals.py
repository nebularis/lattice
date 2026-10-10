# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""HO6: the refusals and the warning of the classified boundary shape (formal-methods track H,
slice HO6, ADR-A122 decision 1, 4 and 5, sketch §5).
Validation Pack: docs/developer/validation/FMH-HO6.md. Test IDs are HO6-Tn."""

from __future__ import annotations

import pytest
from rdflib import Graph, Literal, URIRef

from persistence import witness
from persistence.compiler import CompileError, compile_targets

from conftest import EXAMPLES_DIR

PREFIXES = """
@prefix dal:  <https://www.nebularis.org/neuro-semantic/lattice/persistence#> .
@prefix ex:   <https://example.org/lending#> .
@prefix px:   <https://example.org/projects#> .
@prefix sh:   <http://www.w3.org/ns/shacl#> .
@prefix skos: <http://www.w3.org/2004/02/skos/core#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix xsd:  <http://www.w3.org/2001/XMLSchema#> .
"""
DAL = "https://www.nebularis.org/neuro-semantic/lattice/persistence#"
ORDER = "composite-property-boundary-shacl.ttl"
PROJECT = "composite-project-ownership.ttl"


def _with(example: str, ttl: str) -> Graph:
    graph = witness._load_fixture(EXAMPLES_DIR / example)
    graph.parse(data=PREFIXES + ttl, format="turtle")
    return graph


def _order(property_shape: str) -> Graph:
    return _with(ORDER, f"ex:OrderAggregateShape sh:property [ {property_shape} ] .")


def _kind(graph: Graph) -> str:
    with pytest.raises(CompileError) as error:
        compile_targets(graph)
    cause = error.value.cause
    return getattr(cause, "kind", type(cause).__name__)


def _warnings(graph: Graph) -> list[str]:
    return [d.kind for ct in compile_targets(graph) for d in ct.diagnostics if d.severity == "WARNING"]


def test_ho6_t1_a_sequence_path_is_refused():
    assert _kind(_order("sh:path ( ex:customer ex:address ) ; sh:class ex:Address ; dal:ownership dal:Reference")) == "ComplexBoundaryPath"


def test_ho6_t2_a_node_property_with_no_classification_is_refused_naming_the_shape_and_predicate():
    graph = _order("sh:path ex:customer ; sh:class ex:Customer")
    with pytest.raises(CompileError) as error:
        compile_targets(graph)
    assert error.value.cause.kind == "UnclassifiedBoundaryEdge"
    assert "OrderAggregateShape" in str(error.value.cause) and "customer" in str(error.value.cause)


def test_ho6_t3_a_reference_given_sh_node_and_no_classification_is_refused():
    """Review F1. It is no longer swept silently, and no longer accepted unclassified."""
    assert _kind(_order("sh:path ex:placedBy ; sh:node ex:CustomerShape")) == "UnclassifiedBoundaryEdge"


def test_ho6_t4_ownership_on_a_value_property_is_refused():
    assert _kind(_order("sh:path ex:note ; sh:datatype xsd:string ; dal:ownership dal:Owned")) == "OwnershipOnValueProperty"
    assert _kind(_order("sh:path ex:note ; sh:nodeKind sh:Literal ; dal:ownership dal:Reference")) == "OwnershipOnValueProperty"


def test_ho6_t5_a_composite_shape_with_only_value_and_reference_properties_is_refused():
    graph = witness._load_fixture(witness.WITNESS_DIR / "refusal-CompositeBoundaryWithoutOwnedEdges.ttl")
    assert _kind(graph) == "CompositeBoundaryWithoutOwnedEdges"


def test_ho6_t6_an_owned_edge_to_a_concept_is_refused():
    assert _kind(_order("sh:path ex:status ; sh:class skos:Concept ; dal:ownership dal:Owned")) == "OwnedReferenceData"
    assert _kind(_order("sh:path ex:scheme ; sh:class skos:ConceptScheme ; dal:ownership dal:Owned")) == "OwnedReferenceData"


def test_ho6_t7_the_same_edge_is_accepted_when_the_profile_manages_reference_data():
    graph = _order("sh:path ex:status ; sh:class skos:Concept ; dal:ownership dal:Owned")
    graph.add((URIRef("https://example.org/lending#OrderBoundaryProfile"), URIRef(DAL + "ownsReferenceData"), Literal(True)))
    assert compile_targets(graph)


def test_ho6_t8_a_declared_reference_data_class_and_its_subclass_are_refused_as_owned():
    declare = "ex:Currencies a dal:ReferenceData ; dal:coversClass ex:Currency . ex:ForeignCurrency rdfs:subClassOf ex:Currency ."
    for cls in ("ex:Currency", "ex:ForeignCurrency"):
        graph = _with(ORDER, declare + f" ex:OrderAggregateShape sh:property [ sh:path ex:currency ; sh:class {cls} ; dal:ownership dal:Owned ] .")
        assert _kind(graph) == "OwnedReferenceData", cls


def test_ho6_t9_two_composite_profiles_that_own_one_class_are_refused_naming_both_shapes():
    graph = _with(
        PROJECT,
        """
        px:NoteClass a dal:ClassScope ; dal:targetClass px:Note .
        px:NoteBoundary a dal:AggregateBoundaryProfile ; dal:appliesTo px:NoteClass ; dal:strategy dal:CompositePropertyBoundary ;
            dal:boundaryShape px:NoteShape ; dal:dataGraph <urn:g:notes> .
        px:NoteShape a sh:NodeShape ; sh:targetClass px:Note ;
            sh:property [ sh:path px:attachment ; sh:node px:DocumentShape ; dal:ownership dal:Owned ] .
        """,
    )
    with pytest.raises(CompileError) as error:
        compile_targets(graph)
    assert error.value.cause.kind == "OverlappingOwnership"
    text = str(error.value.cause)
    assert "ProjectShape" in text and "NoteShape" in text and "Document" in text


@pytest.mark.parametrize("run", range(5))
def test_ho6_t10_a_profile_that_owns_another_composites_root_is_refused_as_a_boundary_conflict_every_time(run):
    graph = _with(
        PROJECT,
        """
        px:PortfolioClass a dal:ClassScope ; dal:targetClass px:Portfolio .
        px:PortfolioBoundary a dal:AggregateBoundaryProfile ; dal:appliesTo px:PortfolioClass ; dal:strategy dal:CompositePropertyBoundary ;
            dal:boundaryShape px:PortfolioShape ; dal:dataGraph <urn:g:portfolios> .
        px:PortfolioShape a sh:NodeShape ; sh:targetClass px:Portfolio ;
            sh:property [ sh:path px:holds ; sh:node px:ProjectShape ; dal:ownership dal:Owned ] .
        """,
    )
    with pytest.raises(CompileError) as error:
        compile_targets(graph)
    assert type(error.value.cause).__name__ == "BoundaryConflict"


def test_ho6_t11_a_reference_from_outside_to_a_member_class_warns_and_the_compile_succeeds():
    graph = _with(PROJECT, "px:InvoiceShape a sh:NodeShape ; sh:targetClass px:Invoice ; sh:property [ sh:path px:forMilestone ; sh:class px:Milestone ] .")
    assert "ReferenceToOwnedClass" in _warnings(graph)


def test_ho6_t12_the_reference_fixture_has_neither_a_refusal_nor_the_warning():
    assert "ReferenceToOwnedClass" not in _warnings(witness._load_fixture(EXAMPLES_DIR / PROJECT))


def test_ho6_t13_a_reference_to_the_root_class_does_not_warn():
    graph = _with(PROJECT, "px:InvoiceShape a sh:NodeShape ; sh:targetClass px:Invoice ; sh:property [ sh:path px:forProject ; sh:class px:Project ] .")
    assert "ReferenceToOwnedClass" not in _warnings(graph)


@pytest.mark.parametrize(
    ("family", "kind"),
    [
        ("refusal", "ComplexBoundaryPath"), ("refusal", "UnclassifiedBoundaryEdge"), ("refusal", "OwnershipOnValueProperty"),
        ("refusal", "OwnedReferenceData"), ("refusal", "OverlappingOwnership"), ("warning", "ReferenceToOwnedClass"),
    ],
)
def test_ho6_t14_each_new_witness_triggers_exactly_its_own_rule(family, kind):
    observed = witness.observe_compile([witness.WITNESS_DIR / f"{family}-{kind}.ttl"])
    assert set(observed) == {witness.Rule(family, kind)}


def test_ho6_t15_a_named_graph_profile_that_names_a_shape_is_checked_by_the_same_rules():
    graph = witness._load_fixture(EXAMPLES_DIR / "baseline-single-class.ttl")
    profile = "ex:LoanApplicationStrongProfile"
    graph.parse(
        data=PREFIXES + f"""
        {profile} dal:boundaryShape ex:LoanShape .
        ex:LoanShape a sh:NodeShape ; sh:targetClass ex:LoanApplication ;
            sh:property [ sh:path ex:applicant ; sh:class ex:Person ] .
        """,
        format="turtle",
    )
    assert _kind(graph) == "UnclassifiedBoundaryEdge"
    classified = witness._load_fixture(EXAMPLES_DIR / "baseline-single-class.ttl")
    classified.parse(
        data=PREFIXES + f"""
        {profile} dal:boundaryShape ex:LoanShape .
        ex:LoanShape a sh:NodeShape ; sh:targetClass ex:LoanApplication ;
            sh:property [ sh:path ex:applicant ; sh:class ex:Person ; dal:ownership dal:Reference ] .
        """,
        format="turtle",
    )
    assert compile_targets(classified)


def test_ho6_t16_the_warning_reads_the_same_whatever_the_blank_node_labels():
    text = "px:InvoiceShape a sh:NodeShape ; sh:targetClass px:Invoice ; sh:property [ sh:path px:forMilestone ; sh:class px:Milestone ] ."
    messages = {tuple(d.message for ct in compile_targets(_with(PROJECT, text)) for d in ct.diagnostics) for _ in range(3)}
    assert len(messages) == 1
