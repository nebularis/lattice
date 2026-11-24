# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI
"""The typed value expressions and the source node identity: the shapes of ontology/mork accept a scheme that uses them
and refuse each kind of defect. Nothing here compiles a scheme. A scheme is checked as written, with no ontology beside
it, so every shape names the concrete classes it targets."""

from __future__ import annotations

from pathlib import Path

import pytest
from pyshacl import validate
from rdflib import Graph
from rdflib.namespace import SH

ROOT = Path(__file__).resolve().parents[3]
SHAPES = ROOT / "ontology" / "mork" / "shapes" / "constraints.ttl"

PREFIXES = """
@prefix mork: <http://www.nebularis.org/ontologies/Mork#> .
@prefix xsd:  <http://www.w3.org/2001/XMLSchema#> .
@prefix src:  <http://example.org/src#> .
@prefix tgt:  <http://example.org/tgt#> .
@prefix mm:   <http://example.org/mapping#> .
"""

# The scheme of the annual figure in README section 5.4, with a choice and a rounding added so every class is used.
SCHEME = PREFIXES + """
mm:Arr a mork:MappingScheme .

mm:Concept_Subscription a mork:DataConcept ; mork:representedAs src:Subscription .

mm:Map_Subscription a mork:DataMapping , mork:Datum ;
    mork:mappingScheme mm:Arr ;
    mork:mappingFor mm:Concept_Subscription ;
    mork:identityRule mork:SourceNodeIdentity ;
    mork:compositeNarrowerMapping mm:Map_Arr .

mm:Map_Arr a mork:DataMapping ;
    mork:mappingScheme mm:Arr ;
    mork:exactRBoxMatch tgt:annualRecurringRevenue ;
    mork:valueExpression mm:Root .

mm:Root a mork:RoundingExpression ;
    mork:resultDatatype xsd:decimal ; mork:roundedOperand mm:Share ; mork:roundingScale 2 .
mm:Share a mork:QuotientExpression ;
    mork:resultDatatype xsd:decimal ; mork:leftOperand mm:Capped ; mork:rightOperand mm:Twelve .
mm:Twelve a mork:TypedLiteralExpression ;
    mork:resultDatatype xsd:integer ; mork:typedValue 12 .
mm:Capped a mork:ChoiceExpression ;
    mork:resultDatatype xsd:decimal ; mork:comparisonOperator mork:GreaterThan ;
    mork:comparedLeft mm:Gross ; mork:comparedRight mm:Cap ; mork:whenTrue mm:Cap ; mork:whenFalse mm:Gross .
mm:Gross a mork:ProductExpression ;
    mork:resultDatatype xsd:decimal ; mork:leftOperand mm:Price ; mork:rightOperand mm:Periods .
mm:Price a mork:TypedRefExpression ; mork:resultDatatype xsd:decimal ; mork:dataRef "src:monthlyPrice" .
mm:Periods a mork:TypedRefExpression ; mork:resultDatatype xsd:integer ; mork:dataRef "src:periodsPerYear" .
mm:Cap a mork:TypedRefExpression ; mork:resultDatatype xsd:decimal ; mork:dataRef "src:cap" .
mm:Label a mork:TypedRefExpression ; mork:resultDatatype xsd:string ; mork:dataRef "src:label" .
"""


def violations(turtle: str) -> set[str]:
    """The names of the shapes that report a violation, a property shape named by the node shape that holds it."""
    shapes = Graph().parse(SHAPES, format="turtle")
    data = Graph().parse(data=turtle, format="turtle")
    _, report, _ = validate(data, shacl_graph=shapes, advanced=True, inference="none")
    names = set()
    for shape in report.objects(None, SH.sourceShape):
        parent = next(iter(shapes.subjects(SH.property, shape)), shape)
        names.add(str(parent).rsplit("#", 1)[-1])
    return names


def changed(old: str, new: str, turtle: str = SCHEME) -> str:
    assert turtle.count(old) == 1, old
    return turtle.replace(old, new)


def test_a_scheme_of_value_expressions_and_a_source_node_root_conforms():
    assert violations(SCHEME) == set()


def test_an_untyped_operand_is_refused():
    untyped = changed("mm:Price a mork:TypedRefExpression ; mork:resultDatatype xsd:decimal ;", "mm:Price mork:resultDatatype xsd:decimal ;")
    assert "ValueOperandShape" in violations(untyped)


def test_an_operand_that_states_no_datatype_is_refused():
    untyped = changed('mm:Price a mork:TypedRefExpression ; mork:resultDatatype xsd:decimal ;', "mm:Price a mork:TypedRefExpression ;")
    assert "ValueExpressionShape" in violations(untyped)


def test_a_choice_missing_a_branch_is_refused():
    assert "ChoiceExpressionShape" in violations(changed("mork:whenTrue mm:Cap ; mork:whenFalse mm:Gross .", "mork:whenTrue mm:Cap ."))
    assert "ChoiceExpressionShape" in violations(changed("mork:whenTrue mm:Cap ; ", ""))


def test_a_choice_without_an_operator_of_the_vocabulary_is_refused():
    assert "ChoiceExpressionShape" in violations(changed("mork:comparisonOperator mork:GreaterThan", "mork:comparisonOperator mork:Bigger"))


def test_an_arithmetic_expression_missing_an_operand_is_refused():
    assert "ArithmeticExpressionShape" in violations(changed("mork:leftOperand mm:Price ; ", ""))


def test_a_non_numeric_operand_of_arithmetic_is_refused():
    assert "ValueOperandNumericShape" in violations(changed("mork:rightOperand mm:Periods .", "mork:rightOperand mm:Label ."))


def test_an_ordering_comparison_needs_numeric_operands():
    assert "ChoiceOrderingOperandsShape" in violations(changed("mork:comparedRight mm:Cap", "mork:comparedRight mm:Label"))


def test_compared_operands_of_other_datatypes_are_refused_unless_both_numeric():
    equal = changed("mork:comparisonOperator mork:GreaterThan", "mork:comparisonOperator mork:EqualTo")
    assert violations(equal) == set()
    assert "ChoiceComparedOperandsShape" in violations(changed("mork:comparedRight mm:Cap", "mork:comparedRight mm:Label", equal))


def test_branches_of_another_datatype_are_refused():
    assert "ChoiceBranchDatatypeShape" in violations(changed("mork:whenTrue mm:Cap", "mork:whenTrue mm:Periods"))


def test_a_result_datatype_the_operands_do_not_give_is_refused():
    wrong = changed("mm:Gross a mork:ProductExpression ;\n    mork:resultDatatype xsd:decimal", "mm:Gross a mork:ProductExpression ;\n    mork:resultDatatype xsd:integer")
    assert "ArithmeticDatatypeShape" in violations(wrong)


def test_a_quotient_is_at_least_decimal():
    wrong = changed("mm:Share a mork:QuotientExpression ;\n    mork:resultDatatype xsd:decimal", "mm:Share a mork:QuotientExpression ;\n    mork:resultDatatype xsd:integer")
    assert "QuotientDatatypeShape" in violations(wrong)


def test_a_rounding_expression_keeps_its_operands_datatype():
    wrong = changed("mm:Root a mork:RoundingExpression ;\n    mork:resultDatatype xsd:decimal", "mm:Root a mork:RoundingExpression ;\n    mork:resultDatatype xsd:double")
    assert "RoundingDatatypeShape" in violations(wrong)


def test_a_rounding_expression_needs_an_integer_scale():
    assert "RoundingExpressionShape" in violations(changed("mork:roundingScale 2", 'mork:roundingScale "2"'))
    assert "RoundingExpressionShape" in violations(changed(" mork:roundingScale 2", ""))


def test_a_literal_of_another_datatype_is_refused():
    assert "TypedLiteralDatatypeShape" in violations(changed("mork:typedValue 12", 'mork:typedValue "12"'))


def test_an_expression_that_is_an_operand_of_itself_is_refused():
    assert "ValueExpressionAcyclicityShape" in violations(changed("mork:leftOperand mm:Price ;", "mork:leftOperand mm:Gross ;"))


def test_a_mapping_with_two_values_is_refused():
    assert "ValueExpressionAssertionShape" in violations(changed("mork:valueExpression mm:Root .", 'mork:valueExpression mm:Root ; mork:dataRef "src:x" .'))
    assert "ValueExpressionAssertionShape" in violations(changed("mork:valueExpression mm:Root .", 'mork:valueExpression mm:Root ; mork:dataInline "x" .'))


def test_a_value_expression_that_is_not_typed_is_refused():
    assert "ValueExpressionAssertionShape" in violations(changed("mork:valueExpression mm:Root .", "mork:valueExpression mm:Elsewhere ."))


@pytest.mark.parametrize(
    "other",
    [
        "mork:identityTemplateMapping mm:Template",
        'mork:conceptName "subscription"',
        "mork:individualIRI src:one",
        "mork:exactABoxMatch tgt:one",
    ],
)
def test_a_source_node_root_states_no_other_identity(other):
    assert "SourceNodeIdentityShape" in violations(changed("mork:identityRule mork:SourceNodeIdentity ;", f"mork:identityRule mork:SourceNodeIdentity ; {other} ;"))


@pytest.mark.parametrize("typing", ["mork:deferredMapping mm:Class", "mork:exactTBoxMatch tgt:Subscription"])
def test_a_source_node_root_types_nothing(typing):
    assert "SourceNodeIdentityShape" in violations(changed("mork:identityRule mork:SourceNodeIdentity ;", f"mork:identityRule mork:SourceNodeIdentity ; {typing} ;"))


def test_a_source_node_root_iterates_a_source_concept():
    assert "SourceNodeIdentityShape" in violations(changed("    mork:mappingFor mm:Concept_Subscription ;\n", ""))
    assert "SourceNodeIdentityShape" in violations(changed("a mork:DataMapping , mork:Datum ;", "a mork:DataMapping ;"))


def test_an_identity_rule_outside_the_vocabulary_is_refused():
    assert "SourceNodeIdentityShape" in violations(changed("mork:identityRule mork:SourceNodeIdentity", "mork:identityRule mm:Elsewhere"))
