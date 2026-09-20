# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""
MORK-to-SPARQL compiler for Eligibility interval conditions (ADR-A23, ADR-A24).

Generates one parameterised SPARQL ``SELECT`` per condition plan, answering
the three-valued question ADR-A24 requires — ``Permitted``, ``Denied``, or
``Undetermined`` — never a silent ``Denied`` for missing evidence. The query
is written as a ``mork:QueryTemplate``, which MorkEnhancements.md recommends
as the first target and which ``ontology/mork/spec/Mork.ttl`` already models
(``queryText``, ``queryLanguage``, ``paramBinding``). It is not attached to a
``mork:DataMapping``: ``QueryTemplate`` is ``rdfs:subClassOf skos:Concept``
in the ontology today, with no property linking a mapping to one, so
provenance instead runs ``exe:IntervalContainmentPlan -> exe:producesArtefact
-> mork:QueryTemplate``.

Undetermined handling: a candidate missing either bound is Undetermined, not
Denied, matching ADR-A24's stated requirement that unsupported or absent
evidence must never silently read as a denial.
"""

from __future__ import annotations

from rdflib import Graph, Literal
from rdflib.namespace import RDF

from .common import mint
from .eligibility_ir import IntervalPlan, RequiredInterval
from .namespaces import ELG, EXE, MORK, QNT


def _interval_clause(interval: RequiredInterval) -> str:
    clauses = []
    if interval.lower is not None:
        op = ">=" if interval.lower_closed else ">"
        clauses.append(f"?candLower {op} {interval.lower!r}")
    if interval.upper is not None:
        op = "<=" if interval.upper_closed else "<"
        clauses.append(f"?candUpper {op} {interval.upper!r}")
    return "(" + " && ".join(clauses) + ")" if clauses else "true"


def _containment_expression(plan: IntervalPlan) -> str:
    """A SPARQL boolean expression: the candidate is contained by *some* required interval."""
    return " || ".join(_interval_clause(interval) for interval in plan.required)


def render_query(plan: IntervalPlan) -> str:
    """The SPARQL query text for one condition plan."""
    return (
        "PREFIX elg: <https://www.nebularis.org/neuro-semantic/lattice/eligibility#>\n"
        "PREFIX qnt: <https://www.nebularis.org/neuro-semantic/lattice/quantification#>\n"
        "SELECT ?question ?decision WHERE {\n"
        f"  ?question elg:forCondition <{plan.condition}> .\n"
        "  OPTIONAL {\n"
        "    ?question elg:candidateRangeSet ?candidateRangeSet .\n"
        "    ?candidateRangeSet qnt:hasRange ?candidateRange .\n"
        "    ?candidateRange qnt:lowerBound/qnt:boundValue/qnt:numericValue ?candLower .\n"
        "    ?candidateRange qnt:upperBound/qnt:boundValue/qnt:numericValue ?candUpper .\n"
        "  }\n"
        "  BIND(\n"
        "    IF(!BOUND(?candLower) || !BOUND(?candUpper), \"Undetermined\",\n"
        f"       IF({_containment_expression(plan)}, \"Permitted\", \"Denied\")\n"
        "    ) AS ?decision\n"
        "  )\n"
        "}\n"
    )


def compile_query_template(plan: IntervalPlan) -> Graph:
    """Emit the ``mork:QueryTemplate`` and its ``exe:IntervalContainmentPlan`` provenance."""
    graph = Graph()
    for prefix, namespace in (("mork", MORK), ("exe", EXE), ("elg", ELG), ("qnt", QNT)):
        graph.bind(prefix, namespace)

    plan_node = mint(plan.condition, "execplan")
    template = mint(plan.condition, "sparql")

    graph.add((plan_node, RDF.type, EXE.IntervalContainmentPlan))
    graph.add((plan_node, EXE.implementsCondition, plan.condition))
    graph.add((plan_node, EXE.producesArtefact, template))
    graph.add((plan_node, EXE.derivedFromEligibilityNode, plan.condition))
    for node in plan.source_nodes:
        if node != plan.condition:
            graph.add((plan_node, EXE.derivedFromQuantificationNode, node))

    graph.add((template, RDF.type, MORK.QueryTemplate))
    graph.add((template, RDF.type, EXE.SparqlArtefact))
    graph.add((template, MORK.queryLanguage, Literal("SPARQL")))
    graph.add((template, MORK.queryText, Literal(render_query(plan))))
    return graph
