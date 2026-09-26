# SPDX-License-Identifier: MPL-2.0

"""
Design-time OWL classes for bound conditions and profiles (ADR-A90).

One module per compilation, an ``exe:OwlArtefact``, holding a class per
condition and profile. A condition's class is its subject class intersected
with its evidence path, each step restricted to at most one value (the
binding's ``elg:singleValued`` claim, ADR-A90 addendum option B), ending in
the candidate's filler:

- a concept condition: the union of the required concepts' fillers minus the
  union of the excluded ones. Hierarchical match uses ``Within(c)``, a class
  of concepts with ``{c} ⊑ Within(c)`` and ``Within(d) ⊑ Within(c)`` for d
  narrower than c. ``∃R.Within(c)`` at the path's last step R is ADR-A90's
  ``Within_R(c)``. Flat strategies use nominals. A condition with
  exclusions only requires the scheme's top concepts, or all its members.
- an interval condition: a datatype restriction on ``owl:real`` per required
  interval, on a ``qnt:Quantity``'s numeric value, in the interval's unit, or
  on the literal itself where the binding reads a literal on the condition's
  space. Units are never converted.

``AllRequired`` profiles intersect their conditions' classes and
``AnySufficient`` ones unite them. Concepts named in a module are declared
distinct, as the SPARQL reference compares them by IRI. Sibling concepts'
``Within`` classes are declared disjoint only on request, and only for a
scheme with one broader concept per member. Each claimed binding also gets a
SHACL shape checking the claim on data, so classes and data agree.

The checks ask the test-only reasoning harness (ADR-A83) and return an
``exe:DesignTimeCheck`` record with the answer.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Dict, Iterable, List, Optional, Sequence, Tuple, Union

from rdflib import BNode, Graph, Literal, URIRef
from rdflib.collection import Collection
from rdflib.namespace import OWL, RDF, RDFS, SH, XSD

from . import reasoning
from .common import local_name, mint
from .eligibility_ir import ConceptPlan, IntervalPlan, IRCompileError, ProfilePlan, RequiredInterval
from .namespaces import ELG, EXE, QNT
from .sparql_backend import literal_readable

OWL_DL = URIRef("http://www.w3.org/ns/owl-profile/DL")
Plan = Union[IntervalPlan, ConceptPlan, ProfilePlan]
CHECKS = {"subsumption": EXE.SubsumptionCheck, "satisfiability": EXE.SatisfiabilityCheck, "overlap": EXE.OverlapCheck}


def owl_class(iri: URIRef) -> URIRef:
    """The generated class of a condition or profile."""
    return mint(iri, "class")


def within(concept: URIRef) -> URIRef:
    return mint(concept, "within")


def _list(graph: Graph, items: Iterable) -> BNode:
    head = BNode()
    Collection(graph, head, list(items))
    return head


def _combine(graph: Graph, kind: URIRef, items: Sequence, datatype: bool = False):
    if len(items) == 1:
        return items[0]
    node = BNode()
    graph.add((node, RDF.type, RDFS.Datatype if datatype else OWL.Class))
    graph.add((node, kind, _list(graph, items)))
    return node


def _complement(graph: Graph, cls) -> BNode:
    node = BNode()
    graph.add((node, RDF.type, OWL.Class))
    graph.add((node, OWL.complementOf, cls))
    return node


def _one_of(graph: Graph, individuals: Sequence[URIRef]) -> BNode:
    node = BNode()
    graph.add((node, RDF.type, OWL.Class))
    graph.add((node, OWL.oneOf, _list(graph, individuals)))
    return node


def _restriction(graph: Graph, prop, predicate: URIRef, value) -> BNode:
    node = BNode()
    graph.add((node, RDF.type, OWL.Restriction))
    graph.add((node, OWL.onProperty, prop))
    graph.add((node, predicate, value))
    return node


def _step(graph: Graph, prop: URIRef, inverse: bool):
    if not inverse:
        return prop
    node = BNode()
    graph.add((node, OWL.inverseOf, prop))
    return node


def _along(graph: Graph, steps: Sequence[Tuple[URIRef, bool]], filler):
    """``≤1 p₁ ⊓ ∃p₁.(≤1 p₂ ⊓ ∃p₂.(… filler))``."""
    for prop, inverse in reversed(steps):
        filler = _combine(graph, OWL.intersectionOf, [
            _restriction(graph, _step(graph, prop, inverse), OWL.maxCardinality, Literal(1, datatype=XSD.nonNegativeInteger)),
            _restriction(graph, _step(graph, prop, inverse), OWL.someValuesFrom, filler),
        ])
    return filler


def _concept_filler(graph: Graph, plan: ConceptPlan):
    if plan.hierarchical:
        tops = [member for member, broader in plan.hierarchy if not broader]
        required = [within(concept) for concept in plan.required or tops]
        excluded = [within(concept) for concept in plan.excluded]
    else:
        required = [_one_of(graph, plan.required or [member for member, _ in plan.hierarchy])]
        excluded = [_one_of(graph, plan.excluded)] if plan.excluded else []
    parts = [_combine(graph, OWL.unionOf, required)]
    if excluded:
        parts.append(_complement(graph, _combine(graph, OWL.unionOf, excluded)))
    return _combine(graph, OWL.intersectionOf, parts)


def _data_range(graph: Graph, interval: RequiredInterval):
    facets = []
    if interval.lower is not None:
        facets.append((XSD.minInclusive if interval.lower_closed else XSD.minExclusive, interval.lower))
    if interval.upper is not None:
        facets.append((XSD.maxInclusive if interval.upper_closed else XSD.maxExclusive, interval.upper))
    if not facets:
        return OWL.real
    restrictions = []
    for facet, value in facets:
        restriction = BNode()
        graph.add((restriction, facet, Literal(Decimal(repr(value)))))
        restrictions.append(restriction)
    node = BNode()
    graph.add((node, RDF.type, RDFS.Datatype))
    graph.add((node, OWL.onDatatype, OWL.real))
    graph.add((node, OWL.withRestrictions, _list(graph, restrictions)))
    return node


def _interval_filler(graph: Graph, plan: IntervalPlan):
    if literal_readable(plan):
        ranges = [_data_range(graph, interval) for interval in plan.required if interval.unit is None]
        if not ranges:
            raise IRCompileError(f"{plan.condition} states every interval in a unit, so none applies to a literal")
        return _combine(graph, OWL.unionOf, ranges, datatype=True)
    if plan.evidence.space is not None:
        raise IRCompileError(f"{plan.evidence.binding} reads literals on another space than {plan.condition}'s")
    quantities = []
    for interval in plan.required:
        parts = [
            _restriction(graph, QNT.onSpace, OWL.hasValue, plan.value_space),
            _restriction(graph, QNT.numericValue, OWL.someValuesFrom, _data_range(graph, interval)),
        ]
        if interval.unit is not None:
            parts.append(_restriction(graph, QNT.inUnit, OWL.hasValue, interval.unit))
        quantities.append(_combine(graph, OWL.intersectionOf, parts))
    return _combine(graph, OWL.unionOf, quantities)


def _sh_path(graph: Graph, steps: Sequence[Tuple[URIRef, bool]]):
    parts = []
    for prop, inverse in steps:
        if inverse:
            node = BNode()
            graph.add((node, SH.inversePath, prop))
            parts.append(node)
        else:
            parts.append(prop)
    return parts[0] if len(parts) == 1 else _list(graph, parts)


def _single_valued_shape(graph: Graph, plan: Union[IntervalPlan, ConceptPlan]) -> URIRef:
    """At most one value at each depth of the path, from each subject."""
    evidence = plan.evidence
    shape = mint(evidence.binding, "single-valued")
    graph.add((shape, RDF.type, SH.NodeShape))
    graph.add((shape, RDF.type, EXE.ShaclArtefact))
    graph.add((shape, SH.targetClass, evidence.subject_class))
    for depth in range(1, len(evidence.steps) + 1):
        prop = BNode()
        graph.add((shape, SH.property, prop))
        graph.add((prop, SH.path, _sh_path(graph, evidence.steps[:depth])))
        graph.add((prop, SH.maxCount, Literal(1)))
        graph.add((prop, SH.message, Literal(f"{evidence.binding} claims a single value at step {depth - 1}")))
    return shape


def _condition(graph: Graph, plan: Union[IntervalPlan, ConceptPlan], artefact: URIRef) -> URIRef:
    evidence = plan.evidence
    if evidence is None:
        raise IRCompileError(f"{plan.condition} has no elg:EvidenceBinding, and the OWL backend compiles bound conditions only")
    if not evidence.single_valued:
        raise IRCompileError(f"{evidence.binding} does not claim elg:singleValued, so its path has no OWL reading (ADR-A90)")
    if isinstance(plan, ConceptPlan) and plan.no_hierarchy:
        raise IRCompileError(
            f"{plan.condition} matches hierarchically over a scheme with no hierarchy, so members it does not "
            f"name are Undetermined (elg:L14), which a design-time class cannot express (ADR-A100)"
        )
    filler = _concept_filler(graph, plan) if isinstance(plan, ConceptPlan) else _interval_filler(graph, plan)
    cls = owl_class(plan.condition)
    graph.add((cls, RDF.type, OWL.Class))
    graph.add((cls, OWL.equivalentClass,
               _combine(graph, OWL.intersectionOf, [evidence.subject_class, _along(graph, evidence.steps, filler)])))

    node = mint(plan.condition, "execplan")
    concept = isinstance(plan, ConceptPlan)
    graph.add((node, RDF.type, EXE.ConceptMatchPlan if concept else EXE.IntervalContainmentPlan))
    graph.add((node, EXE.implementsCondition, plan.condition))
    graph.add((node, EXE.derivedFromEligibilityNode, plan.condition))
    graph.add((node, EXE.derivedFromEligibilityNode, evidence.binding))
    for source in plan.source_nodes[1:]:
        graph.add((node, EXE.derivedFromVocabularyNode if concept else EXE.derivedFromQuantificationNode, source))
    graph.add((node, EXE.producesArtefact, artefact))
    graph.add((node, EXE.producesArtefact, _single_valued_shape(graph, plan)))
    return cls


def _profile(graph: Graph, plan: ProfilePlan, artefact: URIRef) -> None:
    kind = OWL.intersectionOf if plan.aggregation == ELG.AllRequired else OWL.unionOf
    classes = [_condition(graph, condition, artefact) for condition in plan.conditions]
    cls = owl_class(plan.profile)
    graph.add((cls, RDF.type, OWL.Class))
    graph.add((cls, OWL.equivalentClass, _combine(graph, kind, classes)))
    node = mint(plan.profile, "execplan")
    graph.add((node, RDF.type, EXE.ProfilePlan))
    graph.add((node, EXE.implementsProfile, plan.profile))
    graph.add((node, EXE.usesCompatibilityOperation, plan.aggregation))
    graph.add((node, EXE.derivedFromEligibilityNode, plan.profile))
    graph.add((node, EXE.producesArtefact, artefact))
    for condition in plan.conditions:
        graph.add((node, EXE.hasConditionPlan, mint(condition.condition, "execplan")))


def _concept_plans(plans: Sequence[Plan]) -> List[ConceptPlan]:
    found = []
    for plan in plans:
        for part in plan.conditions if isinstance(plan, ProfilePlan) else [plan]:
            if isinstance(part, ConceptPlan):
                found.append(part)
    return found


def _hierarchy(graph: Graph, concepts: Sequence[ConceptPlan], disjoint_siblings: bool) -> None:
    broader: Dict[URIRef, Tuple[URIRef, ...]] = {}
    for plan in concepts:
        if not plan.hierarchical:
            continue
        for member, above in plan.hierarchy:
            if broader.setdefault(member, above) != above:
                raise IRCompileError(f"{member} has different broader concepts in the schemes of one module")
    for member, above in sorted(broader.items()):
        graph.add((within(member), RDF.type, OWL.Class))
        graph.add((_one_of(graph, [member]), RDFS.subClassOf, within(member)))
        for concept in above:
            graph.add((within(member), RDFS.subClassOf, within(concept)))
    if not disjoint_siblings:
        return
    if any(len(above) > 1 for above in broader.values()):
        raise IRCompileError("sibling disjointness needs one broader concept per member")
    children: Dict[Optional[URIRef], List[URIRef]] = {}
    for member, above in sorted(broader.items()):
        children.setdefault(above[0] if above else None, []).append(member)
    for siblings in children.values():
        if len(siblings) > 1:
            node = BNode()
            graph.add((node, RDF.type, OWL.AllDisjointClasses))
            graph.add((node, OWL.members, _list(graph, [within(s) for s in siblings])))


def compile_classes(*plans: Plan, disjoint_siblings: bool = False) -> Graph:
    """One OWL module holding every plan's classes, for plans bound to
    subjects through claimed single-valued paths."""
    graph = Graph()
    first = plans[0]
    artefact = mint(first.profile if isinstance(first, ProfilePlan) else first.condition, "owl")
    graph.add((artefact, RDF.type, EXE.OwlArtefact))
    graph.add((artefact, EXE.owlProfile, OWL_DL))
    graph.add((artefact, EXE.siblingsDisjoint, Literal(disjoint_siblings)))
    for plan in plans:
        if isinstance(plan, ProfilePlan):
            _profile(graph, plan, artefact)
        else:
            _condition(graph, plan, artefact)
    concepts = _concept_plans(plans)
    _hierarchy(graph, concepts, disjoint_siblings)
    named = sorted({c for plan in concepts for c in plan.required + plan.excluded} | {m for plan in concepts for m, _ in plan.hierarchy})
    if len(named) > 1:
        node = BNode()
        graph.add((node, RDF.type, OWL.AllDifferent))
        graph.add((node, OWL.distinctMembers, _list(graph, named)))
    return graph


def check(module: Graph, kind: str, checked: URIRef, against: Optional[URIRef] = None,
          context: Sequence[Graph] = ()) -> Tuple[bool, Graph]:
    """Answer one ADR-A90 item 6 question through the reasoning harness.
    ``checked`` and ``against`` are generated classes (``owl_class``).
    ``context`` holds the declarations of the applied ontology's classes and
    properties, and Quantification's for interval conditions."""
    graph = Graph()
    graph += module
    if kind == "subsumption":
        holds = reasoning.run("subsumes", str(checked), str(against), graphs=[graph, *context])
    elif kind == "satisfiability":
        holds = reasoning.run("satisfiable", str(checked), graphs=[graph, *context])
    elif kind == "overlap":
        both = mint(checked, f"overlap-{local_name(against)}")
        graph.add((both, OWL.equivalentClass, _combine(graph, OWL.intersectionOf, [checked, against])))
        holds = reasoning.run("satisfiable", str(both), graphs=[graph, *context])
    else:
        raise ValueError(f"unknown check {kind}; expected one of {sorted(CHECKS)}")
    record = Graph()
    node = BNode()
    record.add((node, RDF.type, CHECKS[kind]))
    record.add((node, EXE.checkedModule, next(module.subjects(RDF.type, EXE.OwlArtefact))))
    record.add((node, EXE.checkedClass, checked))
    if against is not None:
        record.add((node, EXE.againstClass, against))
    record.add((node, EXE.checkHolds, Literal(bool(holds))))
    return bool(holds), record
