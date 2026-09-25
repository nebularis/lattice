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

Concept plans (ADR-A89 item 4) are compiled to membership facts plus two fixed
rules. The plan's admitted concepts are asserted ``exe:admittedBy`` the
condition and its denied concepts ``exe:deniedBy`` it, both enumerated at
compile time. One rule derives ``elg:Permitted`` from an admitted candidate,
another ``elg:Denied`` from a denied one, so each derivation rests on a
positive fact. A candidate in neither set derives nothing. The rules assume
one candidate concept per question, since SWRL cannot tell one from several.

Profile plans (ADR-A89 item 5) are compiled to rules over the questions'
``exe:impliesDecision`` facts, deriving ``exe:impliesProfileDecision`` on the
decision record. Each outcome that strong Kleene logic fixes from positive
facts gets rules: under ``elg:AllRequired``, Permitted needs every condition
Permitted and Denied needs any one Denied. Under ``elg:AnySufficient`` the two
swap. Undetermined is never derived.
"""

from __future__ import annotations

from typing import List, Optional, Union

from rdflib import BNode, Graph, Literal, URIRef
from rdflib.collection import Collection
from rdflib.namespace import RDF, XSD


from .common import mint
from .eligibility_ir import (
    DENIED,
    PERMITTED,
    ConceptPlan,
    EvidencePath,
    IntervalPlan,
    IRCompileError,
    ProfilePlan,
    RequiredInterval,
)
from .sparql_backend import literal_readable
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


def _imp(graph: Graph, imp: URIRef, body: List[BNode], head: List[BNode]) -> URIRef:
    graph.add((imp, RDF.type, SWRL.Imp))
    body_list = BNode()
    Collection(graph, body_list, body)
    graph.add((imp, SWRL.body, body_list))
    head_list = BNode()
    Collection(graph, head_list, head)
    graph.add((imp, SWRL.head, head_list))
    return imp


def _path_atoms(
    graph: Graph, owner: URIRef, name: str, evidence: EvidencePath, subject: URIRef, end: URIRef,
    datavalued_end: bool = False,
) -> List[BNode]:
    """Atoms walking ``evidence``'s steps from ``subject`` to ``end``. An inverse
    step swaps its arguments. ``datavalued_end`` makes the last step a
    DatavaluedPropertyAtom, for a literal at the end of the path."""
    atoms: List[BNode] = []
    current = subject
    for index, (prop, inverse) in enumerate(evidence.steps):
        last = index == len(evidence.steps) - 1
        following = end if last else mint(owner, f"var-{name}-step-{index}")
        _declare_variable(graph, following)
        if last and datavalued_end:
            if inverse:
                raise IRCompileError(f"{evidence.binding} ends in an inverse step at a literal")
            atoms.append(_datavalued_property_atom(graph, prop, current, following))
        else:
            args = (following, current) if inverse else (current, following)
            atoms.append(_individual_property_atom(graph, prop, *args))
        current = following
    return atoms


def _comparisons(graph: Graph, number: URIRef, interval: RequiredInterval) -> List[BNode]:
    atoms = []
    if interval.lower is not None:
        op = SWRLB.greaterThanOrEqual if interval.lower_closed else SWRLB.greaterThan
        atoms.append(_builtin_atom(graph, op, [number, Literal(interval.lower, datatype=XSD.decimal)]))
    if interval.upper is not None:
        op = SWRLB.lessThanOrEqual if interval.upper_closed else SWRLB.lessThan
        atoms.append(_builtin_atom(graph, op, [number, Literal(interval.upper, datatype=XSD.decimal)]))
    return atoms


def _bound_interval_rule(graph: Graph, plan: IntervalPlan, interval: RequiredInterval, index: int) -> Optional[URIRef]:
    """A bound subject whose one value lies in ``interval`` is permitted: a
    literal where the binding reads on the condition's space, else a
    qnt:Quantity on that space."""
    condition, evidence = plan.condition, plan.evidence
    if literal_readable(plan) and interval.unit is not None:
        return None  # a literal carries no unit, so a unit-specific interval never applies (ADR-A95)
    subject = _variable(condition, index, "subject")
    number = _variable(condition, index, "number")
    for var in (subject, number):
        _declare_variable(graph, var)
    body = [_class_atom(graph, evidence.subject_class, subject)]
    if literal_readable(plan):
        body += _path_atoms(graph, condition, f"{index}", evidence, subject, number, datavalued_end=True)
    else:
        reading = _variable(condition, index, "reading")
        _declare_variable(graph, reading)
        body += _path_atoms(graph, condition, f"{index}", evidence, subject, reading)
        body.append(_individual_property_atom(graph, QNT.onSpace, reading, plan.value_space))
        body.append(_datavalued_property_atom(graph, QNT.numericValue, reading, number))
        if interval.unit is not None:
            body.append(_individual_property_atom(graph, QNT.inUnit, reading, interval.unit))
    body += _comparisons(graph, number, interval)
    head = [_individual_property_atom(graph, EXE.permittedUnder, subject, condition)]
    return _imp(graph, mint(condition, f"swrl-rule-{index}"), body, head)


def _rule_for_interval(graph: Graph, plan: IntervalPlan, interval: RequiredInterval, index: int) -> Optional[URIRef]:
    if plan.evidence is not None:
        return _bound_interval_rule(graph, plan, interval, index)
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

    if interval.unit is not None:
        value = lower_value if interval.lower is not None else upper_value
        body.append(_individual_property_atom(graph, QNT.inUnit, value, interval.unit))
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


def concept_facts(plan: ConceptPlan) -> tuple:
    """(admitted, denied) concepts to assert as facts. Without a resolved scheme
    only the plan's own concepts are known: required less excluded, and excluded."""
    if plan.scheme is None:
        return tuple(c for c in plan.required if c not in plan.excluded), tuple(plan.excluded)
    return (
        tuple(concept for concept, decision in plan.expansion if decision == PERMITTED),
        tuple(concept for concept, decision in plan.expansion if decision == DENIED),
    )


def _concept_rule(graph: Graph, plan: ConceptPlan, membership: URIRef, decision: URIRef, name: str) -> URIRef:
    candidate = mint(plan.condition, f"var-{name}-candidate")
    _declare_variable(graph, candidate)
    if plan.evidence is None:
        question = mint(plan.condition, f"var-{name}-question")
        _declare_variable(graph, question)
        body = [
            _class_atom(graph, ELG.Question, question),
            _individual_property_atom(graph, ELG.forCondition, question, plan.condition),
            _individual_property_atom(graph, ELG.candidateConcept, question, candidate),
        ]
        head = [_individual_property_atom(graph, EXE.impliesDecision, question, decision)]
    else:
        subject = mint(plan.condition, f"var-{name}-subject")
        _declare_variable(graph, subject)
        body = [_class_atom(graph, plan.evidence.subject_class, subject)]
        body += _path_atoms(graph, plan.condition, name, plan.evidence, subject, candidate)
        qualified = EXE.permittedUnder if decision == ELG.Permitted else EXE.deniedUnder
        head = [_individual_property_atom(graph, qualified, subject, plan.condition)]
    body.append(_individual_property_atom(graph, membership, candidate, plan.condition))
    return _imp(graph, mint(plan.condition, f"swrl-rule-{name}"), body, head)


def _compile_concept_rules(plan: ConceptPlan) -> Graph:
    graph = Graph()
    for prefix, namespace in (("mork", MORK), ("exe", EXE), ("elg", ELG), ("swrl", SWRL)):
        graph.bind(prefix, namespace)

    plan_node = mint(plan.condition, "execplan")
    mapping = mint(plan.condition, "rule-mapping")
    graph.add((plan_node, RDF.type, EXE.ConceptMatchPlan))
    graph.add((plan_node, EXE.implementsCondition, plan.condition))
    graph.add((plan_node, EXE.compiledFromMapping, mapping))
    graph.add((plan_node, EXE.derivedFromEligibilityNode, plan.condition))
    for node in plan.source_nodes:
        if node != plan.condition:
            graph.add((plan_node, EXE.derivedFromVocabularyNode, node))
    graph.add((mapping, RDF.type, MORK.DataMapping))
    graph.add((mapping, MORK.mappingFor, plan.condition))
    graph.add(
        (
            mapping,
            MORK.mappingNote,
            Literal(
                "Positive-only SWRL classification over membership facts enumerated at compile "
                "time: derives elg:Permitted or elg:Denied, never elg:Undetermined (ADR-A24, ADR-A89)."
            ),
        )
    )

    admitted, denied = concept_facts(plan)
    for concepts, membership, decision, name in (
        (admitted, EXE.admittedBy, ELG.Permitted, "admitted"),
        (denied, EXE.deniedBy, ELG.Denied, "denied"),
    ):
        if not concepts:
            continue
        for concept in concepts:
            graph.add((concept, membership, plan.condition))
        imp = _concept_rule(graph, plan, membership, decision, name)
        graph.add((mapping, MORK.generatesRuleDefinition, imp))
        graph.add((plan_node, EXE.producesArtefact, imp))
        graph.add((imp, RDF.type, EXE.SwrlArtefact))
    return graph


def _profile_rule(graph: Graph, plan: ProfilePlan, conditions, decision: URIRef, name: str) -> URIRef:
    """``record`` is an EligibilityDecision of the profile and, for each of
    ``conditions``, asks a question the condition decided ``decision``. For a
    bound profile the record is the subject, qualified per condition."""
    record = mint(plan.profile, f"var-{name}-record")
    _declare_variable(graph, record)
    if plan.subject_class is not None:
        qualified = EXE.permittedUnder if decision == ELG.Permitted else EXE.deniedUnder
        body = [_class_atom(graph, plan.subject_class, record)]
        body += [_individual_property_atom(graph, qualified, record, c.condition) for c in conditions]
        head = [_individual_property_atom(graph, EXE.impliesProfileDecision, record, decision)]
        return _imp(graph, mint(plan.profile, f"swrl-rule-{name}"), body, head)
    body = [
        _class_atom(graph, ELG.EligibilityDecision, record),
        _individual_property_atom(graph, ELG.forProfile, record, plan.profile),
    ]
    for index, condition in enumerate(conditions):
        question = mint(plan.profile, f"var-{name}-question-{index}")
        _declare_variable(graph, question)
        body += [
            _individual_property_atom(graph, ELG.hasQuestion, record, question),
            _individual_property_atom(graph, ELG.forCondition, question, condition.condition),
            _individual_property_atom(graph, EXE.impliesDecision, question, decision),
        ]
    head = [_individual_property_atom(graph, EXE.impliesProfileDecision, record, decision)]
    imp = mint(plan.profile, f"swrl-rule-{name}")
    graph.add((imp, RDF.type, SWRL.Imp))
    body_list = BNode()
    Collection(graph, body_list, body)
    graph.add((imp, SWRL.body, body_list))
    head_list = BNode()
    Collection(graph, head_list, head)
    graph.add((imp, SWRL.head, head_list))
    return imp


def _compile_profile_rules(plan: ProfilePlan) -> Graph:
    graph = Graph()
    for prefix, namespace in (("mork", MORK), ("exe", EXE), ("elg", ELG), ("swrl", SWRL)):
        graph.bind(prefix, namespace)
    plan_node = mint(plan.profile, "execplan")
    mapping = mint(plan.profile, "rule-mapping")
    graph.add((plan_node, RDF.type, EXE.ProfilePlan))
    graph.add((plan_node, EXE.implementsProfile, plan.profile))
    graph.add((plan_node, EXE.usesCompatibilityOperation, plan.aggregation))
    graph.add((plan_node, EXE.compiledFromMapping, mapping))
    graph.add((plan_node, EXE.derivedFromEligibilityNode, plan.profile))
    for condition in plan.conditions:
        graph.add((plan_node, EXE.hasConditionPlan, mint(condition.condition, "execplan")))
    graph.add((mapping, RDF.type, MORK.DataMapping))
    graph.add((mapping, MORK.mappingFor, plan.profile))

    # (conditions that must all hold, decision, name): one rule per entry
    every, anyone = (ELG.Permitted, ELG.Denied) if plan.aggregation == ELG.AllRequired else (ELG.Denied, ELG.Permitted)
    rules = [(plan.conditions, every, "all")]
    rules += [((condition,), anyone, f"any-{index}") for index, condition in enumerate(plan.conditions)]
    for conditions, decision, name in rules:
        imp = _profile_rule(graph, plan, conditions, decision, name)
        graph.add((mapping, MORK.generatesRuleDefinition, imp))
        graph.add((plan_node, EXE.producesArtefact, imp))
        graph.add((imp, RDF.type, EXE.SwrlArtefact))
    return graph


def compile_rules(plan: Union[IntervalPlan, ConceptPlan, ProfilePlan]) -> Graph:
    """Emit the plan's ``swrl:Imp`` rules, and the mapping that generates them."""
    if isinstance(plan, ProfilePlan):
        return _compile_profile_rules(plan)
    if isinstance(plan, ConceptPlan):
        return _compile_concept_rules(plan)
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
        if imp is None:
            continue
        graph.add((mapping, MORK.generatesRuleDefinition, imp))
        graph.add((plan_node, EXE.producesArtefact, imp))
        graph.add((imp, RDF.type, EXE.SwrlArtefact))

    return graph
