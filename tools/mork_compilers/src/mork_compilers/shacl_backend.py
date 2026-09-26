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

Concept plans (ADR-A89) get three shapes over the plan's enumerated sets.
Readiness reports a question with no candidate concept or several.
Determinacy reports one whose candidate the plan leaves Undetermined (outside
the resolved scheme, or above an exclusion). Admission reports one whose
candidate is not admitted. Read in that order, the first shape to report a
question gives its outcome (Undetermined, Undetermined, Denied), and a
question no shape reports is Permitted.

Profile plans get two shapes on ``elg:EligibilityDecision`` records of the
profile, each wrapping the profile's SPARQL aggregation: one reports an
Undetermined record, the other a Denied one. A record neither reports is
Permitted.
"""

from __future__ import annotations

from typing import List, Sequence, Tuple, Union

from rdflib import BNode, Graph, Literal, URIRef
from rdflib.namespace import RDF

from .common import mint
from .eligibility_ir import PERMITTED, UNDETERMINED, ConceptPlan, IntervalPlan, ProfilePlan
from .namespaces import ELG, EXE, MORK, SH
from .sparql_backend import PREFIXES as QUERY_PREFIXES
from .sparql_backend import applicable, containment_expression, evidence_path, literal_readable, profile_select

PREFIXES = (
    "PREFIX elg: <https://www.nebularis.org/neuro-semantic/lattice/eligibility#>\n"
    "PREFIX qnt: <https://www.nebularis.org/neuro-semantic/lattice/quantification#>\n"
    "PREFIX skos: <http://www.w3.org/2004/02/skos/core#>\n"
)


def render_containment_select(plan: IntervalPlan) -> str:
    """A SPARQL-based SHACL constraint: reports ``$this`` when its candidate is NOT contained."""
    containment = containment_expression(plan)
    return (
        "PREFIX elg: <https://www.nebularis.org/neuro-semantic/lattice/eligibility#>\n"
        "PREFIX qnt: <https://www.nebularis.org/neuro-semantic/lattice/quantification#>\n"
        "SELECT $this WHERE {\n"
        f"  $this elg:forCondition <{plan.condition}> .\n"
        "  $this elg:candidateRangeSet ?candidateRangeSet .\n"
        "  ?candidateRangeSet qnt:hasRange ?candidateRange .\n"
        "  ?candidateRange qnt:lowerBound/qnt:boundValue/qnt:numericValue ?candLower .\n"
        "  ?candidateRange qnt:upperBound/qnt:boundValue/qnt:numericValue ?candUpper .\n"
        "  OPTIONAL { ?candidateRange qnt:lowerBound/qnt:boundValue/qnt:inUnit ?candUnit }\n"
        f"  FILTER ({applicable(plan)} && !({containment}))\n"
        "}\n"
    )


def render_readiness_select(plan: IntervalPlan) -> str:
    """A SPARQL-based SHACL constraint: reports a Question of this condition with no
    candidate range set at all, or one whose candidate has no bound in its unit —
    scoped to this condition, not every Question, since a Question for a different
    condition may legitimately use elg:candidateValue instead.
    """
    missing = "  { FILTER NOT EXISTS { $this elg:candidateRangeSet ?candidateRangeSet } }\n"
    if applicable(plan) != "true":  # also report a candidate with no bound in its unit (ADR-A95)
        missing += (
            "  UNION { $this elg:candidateRangeSet/qnt:hasRange ?candidateRange .\n"
            "    OPTIONAL { ?candidateRange qnt:lowerBound/qnt:boundValue/qnt:inUnit ?candUnit }\n"
            f"    FILTER (!{applicable(plan)}) }}\n"
        )
    return (
        "PREFIX elg: <https://www.nebularis.org/neuro-semantic/lattice/eligibility#>\n"
        "PREFIX qnt: <https://www.nebularis.org/neuro-semantic/lattice/quantification#>\n"
        "SELECT $this WHERE {\n"
        f"  $this elg:forCondition <{plan.condition}> .\n"
        + missing +
        "}\n"
    )


def concept_sets(plan: ConceptPlan) -> Tuple[List[URIRef], List[URIRef]]:
    """(admitted, undetermined) concepts. Without a resolved scheme the plan
    admits its required concepts less its exclusions and leaves none undetermined."""
    if plan.scheme is None:
        return [c for c in plan.required if c not in plan.excluded], []
    admitted = [concept for concept, decision in plan.expansion if decision == PERMITTED]
    undetermined = [concept for concept, decision in plan.expansion if decision == UNDETERMINED]
    return admitted, undetermined


def _in_list(concepts: Sequence[URIRef]) -> str:
    return ", ".join(f"<{concept}>" for concept in concepts)


def _source(plan: Union[IntervalPlan, ConceptPlan]) -> Tuple[str, str, URIRef]:
    """(anchor pattern, path to the candidate, target class). A question is
    anchored to its condition. A bound subject is selected by the target class
    alone and reached through the binding's path (ADR-A91)."""
    if plan.evidence is None:
        via = "elg:candidateConcept" if isinstance(plan, ConceptPlan) else "elg:candidateRangeSet"
        return f"  $this elg:forCondition <{plan.condition}> .\n", via, ELG.Question
    return "", evidence_path(plan.evidence), plan.evidence.subject_class


def _single_candidate(plan: Union[IntervalPlan, ConceptPlan], name: str = "?candidate") -> str:
    anchor, via, _ = _source(plan)
    return (
        f"{anchor}  $this {via} {name} .\n"
        f"  FILTER NOT EXISTS {{ $this {via} ?other FILTER (?other != {name}) }}\n"
    )


def _readiness(plan: Union[IntervalPlan, ConceptPlan]) -> Tuple[str, str, str]:
    anchor, via, _ = _source(plan)
    return (
        "readiness",
        f"No candidate, or several ({EXE.MissingCandidate}, {EXE.SeveralCandidates}).",
        PREFIXES
        + "SELECT $this WHERE {\n"
        + anchor
        + f"  {{ FILTER NOT EXISTS {{ $this {via} ?any }} }}\n"
        f"  UNION {{ $this {via} ?first , ?second . FILTER (?first != ?second) }}\n"
        "}\n",
    )


def render_concept_selects(plan: ConceptPlan) -> List[Tuple[str, str, str]]:
    """(role, message, select) for each concept shape, in reading order."""
    admitted, undetermined = concept_sets(plan)
    selects = [_readiness(plan)]
    undecided = []
    if plan.scheme is not None:
        undecided.append(f"NOT EXISTS {{ ?candidate skos:inScheme <{plan.scheme.scheme}> }}")
    if undetermined:
        undecided.append(f"?candidate IN ({_in_list(undetermined)})")
    if undecided:
        selects.append(
            (
                "determinacy",
                f"The candidate is outside the resolved scheme or cannot be placed in it ({EXE.OutsideScheme}, "
                f"{EXE.NoHierarchy if plan.no_hierarchy else EXE.AboveExclusion}).",
                PREFIXES + "SELECT $this WHERE {\n" + _single_candidate(plan)
                + f"  FILTER ({' || '.join(undecided)})\n" + "}\n",
            )
        )
    admission = f"  FILTER (?candidate NOT IN ({_in_list(admitted)}))\n" if admitted else ""
    selects.append(
        (
            "admission",
            "The candidate concept is not admitted by this condition.",
            PREFIXES + "SELECT $this WHERE {\n" + _single_candidate(plan) + admission + "}\n",
        )
    )
    return selects


def _compile_concept_shapes(plan: ConceptPlan) -> Graph:
    graph = Graph()
    for prefix, namespace in (("mork", MORK), ("exe", EXE), ("elg", ELG), ("sh", SH)):
        graph.bind(prefix, namespace)

    plan_node = mint(plan.condition, "execplan")
    mapping = mint(plan.condition, "shape-mapping")
    graph.add((plan_node, RDF.type, EXE.ConceptMatchPlan))
    graph.add((plan_node, EXE.implementsCondition, plan.condition))
    graph.add((plan_node, EXE.compiledFromMapping, mapping))
    graph.add((plan_node, EXE.derivedFromEligibilityNode, plan.condition))
    for node in plan.source_nodes:
        if node != plan.condition:
            graph.add((plan_node, EXE.derivedFromVocabularyNode, node))
    graph.add((mapping, RDF.type, MORK.DataMapping))
    graph.add((mapping, MORK.mappingFor, plan.condition))

    _emit(graph, plan_node, mapping, plan.condition, render_concept_selects(plan), _source(plan)[2])
    return graph


def _emit(graph: Graph, plan_node: URIRef, mapping: URIRef, owner: URIRef, selects, target: URIRef) -> None:
    """One sh:NodeShape per (role, message, select), targeting ``target``."""
    for role, message, select in selects:
        shape = mint(owner, f"{role}-shape")
        constraint = BNode()
        graph.add((mapping, MORK.generatesShapeDefinition, shape))
        graph.add((plan_node, EXE.producesArtefact, shape))
        graph.add((shape, RDF.type, SH.NodeShape))
        graph.add((shape, RDF.type, EXE.ShaclArtefact))
        graph.add((shape, SH.targetClass, target))
        graph.add((shape, SH.sparql, constraint))
        graph.add((constraint, SH.message, Literal(message)))
        graph.add((constraint, SH.select, Literal(select)))


def render_bound_interval_selects(plan: IntervalPlan) -> List[Tuple[str, str, str]]:
    """(role, message, select) for a bound interval condition, in reading order:
    readiness and determinacy give Undetermined, containment gives Denied."""
    literal = "isLiteral(?reading)" if literal_readable(plan) else "false"
    reading = (
        _single_candidate(plan, "?reading")
        + f"  OPTIONAL {{ ?reading qnt:numericValue ?quantity ; qnt:onSpace <{plan.value_space}> }}\n"
        + "  OPTIONAL { ?reading qnt:inUnit ?candUnit }\n"
        + f"  BIND(IF({literal}, ?reading, ?quantity) AS ?candLower)\n"
        + "  BIND(?candLower AS ?candUpper)\n"
    )
    return [
        _readiness(plan),
        (
            "determinacy",
            f"The value is not read on the condition's value space, or no bound is stated in its unit ({EXE.ValueSpaceMismatch}, {EXE.NoBoundInUnit}).",
            PREFIXES + "SELECT $this WHERE {\n" + reading + f"  FILTER (!BOUND(?candLower) || !{applicable(plan)})\n}}\n",
        ),
        (
            "containment",
            "The value is not contained by any required interval.",
            PREFIXES + "SELECT $this WHERE {\n" + reading
            + f"  FILTER (BOUND(?candLower) && {applicable(plan)} && !({containment_expression(plan)}))\n}}\n",
        ),
    ]


def _compile_bound_interval_shapes(plan: IntervalPlan) -> Graph:
    graph = Graph()
    for prefix, namespace in (("mork", MORK), ("exe", EXE), ("elg", ELG), ("sh", SH)):
        graph.bind(prefix, namespace)
    plan_node = mint(plan.condition, "execplan")
    mapping = mint(plan.condition, "shape-mapping")
    graph.add((plan_node, RDF.type, EXE.IntervalContainmentPlan))
    graph.add((plan_node, EXE.implementsCondition, plan.condition))
    graph.add((plan_node, EXE.compiledFromMapping, mapping))
    graph.add((plan_node, EXE.derivedFromEligibilityNode, plan.condition))
    graph.add((plan_node, EXE.derivedFromEligibilityNode, plan.evidence.binding))
    for node in plan.source_nodes:
        if node != plan.condition:
            graph.add((plan_node, EXE.derivedFromQuantificationNode, node))
    graph.add((mapping, RDF.type, MORK.DataMapping))
    graph.add((mapping, MORK.mappingFor, plan.condition))
    _emit(graph, plan_node, mapping, plan.condition, render_bound_interval_selects(plan), plan.evidence.subject_class)
    return graph


def render_profile_selects(plan: ProfilePlan) -> List[Tuple[str, str, str]]:
    """(role, message, select) for each profile shape."""
    return [
        (
            f"profile-{outcome.lower()}",
            f"The profile's outcome for this record is {outcome}.",
            QUERY_PREFIXES + "SELECT $this WHERE {\n  {\n" + profile_select(plan, "$this")
            + f'  }}\n  FILTER (?decision = "{outcome}")\n}}\n',
        )
        for outcome in (UNDETERMINED, "Denied")
    ]


def _compile_profile_shapes(plan: ProfilePlan) -> Graph:
    graph = Graph()
    for prefix, namespace in (("mork", MORK), ("exe", EXE), ("elg", ELG), ("sh", SH)):
        graph.bind(prefix, namespace)
    plan_node = mint(plan.profile, "execplan")
    mapping = mint(plan.profile, "shape-mapping")
    graph.add((plan_node, RDF.type, EXE.ProfilePlan))
    graph.add((plan_node, EXE.implementsProfile, plan.profile))
    graph.add((plan_node, EXE.usesCompatibilityOperation, plan.aggregation))
    graph.add((plan_node, EXE.compiledFromMapping, mapping))
    graph.add((plan_node, EXE.derivedFromEligibilityNode, plan.profile))
    for condition in plan.conditions:
        graph.add((plan_node, EXE.hasConditionPlan, mint(condition.condition, "execplan")))
    graph.add((mapping, RDF.type, MORK.DataMapping))
    graph.add((mapping, MORK.mappingFor, plan.profile))
    target = plan.subject_class or ELG.EligibilityDecision
    _emit(graph, plan_node, mapping, plan.profile, render_profile_selects(plan), target)
    return graph


def compile_shapes(plan: Union[IntervalPlan, ConceptPlan, ProfilePlan]) -> Graph:
    """Emit the plan's shapes, and the mapping that generates them."""
    if isinstance(plan, ProfilePlan):
        return _compile_profile_shapes(plan)
    if isinstance(plan, ConceptPlan):
        return _compile_concept_shapes(plan)
    if plan.evidence is not None:
        return _compile_bound_interval_shapes(plan)
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
