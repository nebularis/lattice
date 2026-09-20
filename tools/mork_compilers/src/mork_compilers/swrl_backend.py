# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""
MORK-to-SWRL compiler for Eligibility interval conditions (ADR-A23, ADR-A24).

SWRL is restricted to positive, monotonic inference in this package,
matching both ADR-A24's decision and MorkEnhancements.md's own warning: a
SWRL rule must not derive ``elg:Denied`` merely from failing to infer
``elg:Permitted`` — open-world reasoning makes that inference invalid.
``elg:Undetermined`` is not expressible in SWRL at all for the same reason.

So this backend emits rules for the *positive* case only: one ``swrl:Imp``
per required interval in the condition plan (a candidate satisfying any one
of them is sufficient — a legitimate Horn-clause disjunction expressed as
several independent rules sharing one consequent), each a conjunction of
``swrlb`` numeric comparisons against that interval's bounds. There is no
rule, and no attempt, to derive ``elg:Denied`` or ``elg:Undetermined``.

The consequent asserts ``exe:impliesDecision(?question, elg:Permitted)``, a
property this package's ``ontology/mork/spec/Executable.ttl`` addition declares
specifically because ``elg:decisionValue``'s domain is ``elg:EligibilityDecision``,
not ``elg:Question`` — SWRL derives a fact about the individual already in
scope (the Question), not a newly minted EligibilityDecision individual.

Rules are structured RDF (``swrl:Imp`` with ``swrl:body``/``swrl:head`` atom
lists), per ``ontology/mork/spec/Mork.ttl``'s own description of ``RuleMapping`` — not
a serialised SWRL string. ``mork:swrlCompactSyntax`` is added purely as a
human-readable annotation alongside the structured form, exactly as MORK's
own documentation describes it.
"""

from __future__ import annotations

from typing import List

from rdflib import BNode, Graph, Literal, URIRef
from rdflib.collection import Collection
from rdflib.namespace import RDF, XSD

from .common import mint
from .eligibility_ir import IntervalPlan, RequiredInterval
from .namespaces import ELG, EXE, MORK, QNT, SWRL, SWRLB


def _variable(condition: URIRef, index: int, name: str) -> URIRef:
    return mint(condition, f"var-{index}-{name}")


def _class_atom(graph: Graph, cls: URIRef, var: URIRef) -> BNode:
    atom = BNode()
    graph.add((atom, RDF.type, SWRL.ClassAtom))
    graph.add((atom, SWRL.classPredicate, cls))
    graph.add((atom, SWRL.argument1, var))
    return atom


def _individual_property_atom(graph: Graph, prop: URIRef, var1: URIRef, var2: URIRef) -> BNode:
    atom = BNode()
    graph.add((atom, RDF.type, SWRL.IndividualPropertyAtom))
    graph.add((atom, SWRL.propertyPredicate, prop))
    graph.add((atom, SWRL.argument1, var1))
    graph.add((atom, SWRL.argument2, var2))
    return atom


def _datavalued_property_atom(graph: Graph, prop: URIRef, var1: URIRef, var2: URIRef) -> BNode:
    atom = BNode()
    graph.add((atom, RDF.type, SWRL.DatavaluedPropertyAtom))
    graph.add((atom, SWRL.propertyPredicate, prop))
    graph.add((atom, SWRL.argument1, var1))
    graph.add((atom, SWRL.argument2, var2))
    return atom


def _builtin_atom(graph: Graph, builtin: URIRef, args: List) -> BNode:
    atom = BNode()
    graph.add((atom, RDF.type, SWRL.BuiltinAtom))
    graph.add((atom, SWRL.builtin, builtin))
    args_list = BNode()
    Collection(graph, args_list, list(args))
    graph.add((atom, SWRL.arguments, args_list))
    return atom


def _declare_variable(graph: Graph, var: URIRef) -> None:
    graph.add((var, RDF.type, SWRL.Variable))


def _rule_for_interval(graph: Graph, plan: IntervalPlan, interval: RequiredInterval, index: int) -> URIRef:
    condition = plan.condition
    question = _variable(condition, index, "question")
    rangeset = _variable(condition, index, "rangeset")
    candidate_range = _variable(condition, index, "range")
    for var in (question, rangeset, candidate_range):
        _declare_variable(graph, var)

    body: List[BNode] = [
        _class_atom(graph, ELG.Question, question),
        _individual_property_atom(graph, ELG.forCondition, question, condition),
        _individual_property_atom(graph, ELG.candidateRangeSet, question, rangeset),
        _individual_property_atom(graph, QNT.hasRange, rangeset, candidate_range),
    ]

    if interval.lower is not None:
        lower_bound = _variable(condition, index, "lowerbound")
        lower_value = _variable(condition, index, "lowervalue")
        lower_num = _variable(condition, index, "lowernum")
        for var in (lower_bound, lower_value, lower_num):
            _declare_variable(graph, var)
        body.append(_individual_property_atom(graph, QNT.lowerBound, candidate_range, lower_bound))
        body.append(_individual_property_atom(graph, QNT.boundValue, lower_bound, lower_value))
        body.append(_datavalued_property_atom(graph, QNT.numericValue, lower_value, lower_num))
        op = SWRLB.greaterThanOrEqual if interval.lower_closed else SWRLB.greaterThan
        body.append(
            _builtin_atom(
                graph, op, [lower_num, Literal(interval.lower, datatype=XSD.decimal)]
            )
        )

    if interval.upper is not None:
        upper_bound = _variable(condition, index, "upperbound")
        upper_value = _variable(condition, index, "uppervalue")
        upper_num = _variable(condition, index, "uppernum")
        for var in (upper_bound, upper_value, upper_num):
            _declare_variable(graph, var)
        body.append(_individual_property_atom(graph, QNT.upperBound, candidate_range, upper_bound))
        body.append(_individual_property_atom(graph, QNT.boundValue, upper_bound, upper_value))
        body.append(_datavalued_property_atom(graph, QNT.numericValue, upper_value, upper_num))
        op = SWRLB.lessThanOrEqual if interval.upper_closed else SWRLB.lessThan
        body.append(
            _builtin_atom(
                graph, op, [upper_num, Literal(interval.upper, datatype=XSD.decimal)]
            )
        )

    head = [_individual_property_atom(graph, EXE.impliesDecision, question, ELG.Permitted)]

    imp = mint(condition, f"swrl-rule-{index}")
    graph.add((imp, RDF.type, SWRL.Imp))
    body_list = BNode()
    Collection(graph, body_list, body)
    graph.add((imp, SWRL.body, body_list))
    head_list = BNode()
    Collection(graph, head_list, head)
    graph.add((imp, SWRL.head, head_list))
    return imp


def compile_rules(plan: IntervalPlan) -> Graph:
    """Emit one ``swrl:Imp`` per required interval, and the mapping that generates them."""
    graph = Graph()
    for prefix, namespace in (
        ("mork", MORK), ("exe", EXE), ("elg", ELG), ("qnt", QNT),
        ("swrl", SWRL), ("swrlb", SWRLB),
    ):
        graph.bind(prefix, namespace)

    plan_node = mint(plan.condition, "execplan")
    mapping = mint(plan.condition, "rule-mapping")

    graph.add((plan_node, RDF.type, EXE.IntervalContainmentPlan))
    graph.add((plan_node, EXE.implementsCondition, plan.condition))
    graph.add((plan_node, EXE.compiledFromMapping, mapping))
    graph.add((plan_node, EXE.derivedFromEligibilityNode, plan.condition))
    for node in plan.source_nodes:
        if node != plan.condition:
            graph.add((plan_node, EXE.derivedFromQuantificationNode, node))

    graph.add((mapping, RDF.type, MORK.DataMapping))
    graph.add((mapping, MORK.mappingFor, plan.condition))
    graph.add(
        (
            mapping,
            MORK.mappingNote,
            Literal(
                "Positive-only SWRL classification: derives exe:impliesDecision "
                "elg:Permitted, never elg:Denied or elg:Undetermined (ADR-A24)."
            ),
        )
    )

    for index, interval in enumerate(plan.required):
        imp = _rule_for_interval(graph, plan, interval, index)
        graph.add((mapping, MORK.generatesRuleDefinition, imp))
        graph.add((plan_node, EXE.producesArtefact, imp))
        graph.add((imp, RDF.type, EXE.SwrlArtefact))

    return graph
