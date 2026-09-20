# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""
MORK-to-SHACL compiler for Eligibility interval conditions (ADR-A23, ADR-A24).

Generates two shapes per condition plan: a readiness shape (a Question has
the candidate evidence this condition needs at all) and a containment shape
(the candidate is contained by some required interval). Both are generated
from ``mork:generatesShapeDefinition`` on one ``mork:DataMapping``, which is
what classifies that mapping as a ``mork:ShapeMapping`` by MORK's own
inference rule.

SHACL conformance is not itself an eligibility decision — MorkEnhancements.md
makes this point explicitly. A conforming Question has passed both checks;
a non-conforming one failed readiness, containment, or both, and a decision
adapter (not built here) would still be needed to turn a validation report
into ``elg:Permitted``/``elg:Denied``/``elg:Undetermined``. This backend
produces the validating shapes only, per delivery-plan Phase 5's own scope.
"""

from __future__ import annotations

from rdflib import BNode, Graph, Literal
from rdflib.namespace import RDF

from .common import mint
from .eligibility_ir import IntervalPlan, RequiredInterval
from .namespaces import ELG, EXE, MORK, SH


def _containment_filter(plan: IntervalPlan) -> str:
    clauses = []
    for interval in plan.required:
        clauses.append(_interval_clause(interval))
    return " || ".join(clauses)


def _interval_clause(interval: RequiredInterval) -> str:
    parts = []
    if interval.lower is not None:
        op = ">=" if interval.lower_closed else ">"
        parts.append(f"?candLower {op} {interval.lower!r}")
    if interval.upper is not None:
        op = "<=" if interval.upper_closed else "<"
        parts.append(f"?candUpper {op} {interval.upper!r}")
    return "(" + " && ".join(parts) + ")" if parts else "true"


def render_containment_select(plan: IntervalPlan) -> str:
    """A SPARQL-based SHACL constraint: reports ``$this`` when its candidate is NOT contained."""
    containment = _containment_filter(plan)
    return (
        "PREFIX elg: <https://www.nebularis.org/neuro-semantic/lattice/eligibility#>\n"
        "PREFIX qnt: <https://www.nebularis.org/neuro-semantic/lattice/quantification#>\n"
        "SELECT $this WHERE {\n"
        f"  $this elg:forCondition <{plan.condition}> .\n"
        "  $this elg:candidateRangeSet ?candidateRangeSet .\n"
        "  ?candidateRangeSet qnt:hasRange ?candidateRange .\n"
        "  ?candidateRange qnt:lowerBound/qnt:boundValue/qnt:numericValue ?candLower .\n"
        "  ?candidateRange qnt:upperBound/qnt:boundValue/qnt:numericValue ?candUpper .\n"
        f"  FILTER (!({containment}))\n"
        "}\n"
    )


def render_readiness_select(plan: IntervalPlan) -> str:
    """A SPARQL-based SHACL constraint: reports a Question of this condition with no
    candidate range set at all — scoped to this condition, not every Question, since
    a Question for a different condition may legitimately use elg:candidateValue instead.
    """
    return (
        "PREFIX elg: <https://www.nebularis.org/neuro-semantic/lattice/eligibility#>\n"
        "SELECT $this WHERE {\n"
        f"  $this elg:forCondition <{plan.condition}> .\n"
        "  FILTER NOT EXISTS { $this elg:candidateRangeSet ?candidateRangeSet }\n"
        "}\n"
    )


def compile_shapes(plan: IntervalPlan) -> Graph:
    """Emit the readiness and containment shapes, and the mapping that generates them."""
    graph = Graph()
    for prefix, namespace in (("mork", MORK), ("exe", EXE), ("elg", ELG), ("sh", SH)):
        graph.bind(prefix, namespace)

    plan_node = mint(plan.condition, "execplan")
    mapping = mint(plan.condition, "shape-mapping")
    readiness_shape = mint(plan.condition, "readiness-shape")
    containment_shape = mint(plan.condition, "containment-shape")

    graph.add((plan_node, RDF.type, EXE.IntervalContainmentPlan))
    graph.add((plan_node, EXE.implementsCondition, plan.condition))
    graph.add((plan_node, EXE.compiledFromMapping, mapping))
    graph.add((plan_node, EXE.producesArtefact, readiness_shape))
    graph.add((plan_node, EXE.producesArtefact, containment_shape))
    graph.add((plan_node, EXE.derivedFromEligibilityNode, plan.condition))
    for node in plan.source_nodes:
        if node != plan.condition:
            graph.add((plan_node, EXE.derivedFromQuantificationNode, node))

    graph.add((mapping, RDF.type, MORK.DataMapping))
    graph.add((mapping, MORK.mappingFor, plan.condition))
    graph.add((mapping, MORK.generatesShapeDefinition, readiness_shape))
    graph.add((mapping, MORK.generatesShapeDefinition, containment_shape))

    graph.add((readiness_shape, RDF.type, SH.NodeShape))
    graph.add((readiness_shape, RDF.type, EXE.ShaclArtefact))
    graph.add((readiness_shape, SH.targetClass, ELG.Question))
    readiness_sparql = BNode()
    graph.add((readiness_shape, SH.sparql, readiness_sparql))
    graph.add(
        (
            readiness_sparql,
            SH.message,
            Literal(
                "A Question for this condition has no candidate range set; the "
                "condition is Undetermined, not Denied, until evidence arrives."
            ),
        )
    )
    graph.add((readiness_sparql, SH.select, Literal(render_readiness_select(plan))))

    graph.add((containment_shape, RDF.type, SH.NodeShape))
    graph.add((containment_shape, RDF.type, EXE.ShaclArtefact))
    graph.add((containment_shape, SH.targetClass, ELG.Question))
    sparql_node = BNode()
    graph.add((containment_shape, SH.sparql, sparql_node))
    graph.add(
        (
            sparql_node,
            SH.message,
            Literal("A Question's candidate range is not contained by any required interval."),
        )
    )
    graph.add((sparql_node, SH.select, Literal(render_containment_select(plan))))

    return graph
