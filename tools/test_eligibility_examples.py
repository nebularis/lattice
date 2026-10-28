# SPDX-License-Identifier: MPL-2.0

"""Eligibility examples validate cleanly, and the concept-declaration warning
fires exactly where ADR-A87 says it should.

Data graph: an example plus ``spec/eligibility.ttl``, so ``sh:targetClass``
reaches instances of subclasses. Shapes graph: the layer's three shape files.
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

import pytest
from pyshacl import validate
from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import RDF

sys.path.insert(0, str(Path(__file__).resolve().parent))

import literate_extract  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
LAYER = ROOT / "ontology" / "eligibility"
ELG = Namespace("https://www.nebularis.org/neuro-semantic/lattice/eligibility#")
EX = Namespace("https://example.org/lattice/eligibility/")
SH = Namespace("http://www.w3.org/ns/shacl#")

DECLARATION = ELG.ConceptConditionDeclarationShape
REACHABLE = ELG.ReachableExclusionShape
EXAMPLES = [
    "hierarchical-match", "condition-taxonomy", "interval-containment", "evidence-binding",
    "flat-scheme-lending", "flat-scheme-employment",  # AIR31-10
    "set-reading-admissions", "set-reading-trial",  # AIR32-12
    "closure-usage-reports",  # HQ6a1-10
    "hierarchy-relation",  # C9b3c-01
    "set-comparison-licensing", "set-comparison-trial", "set-comparison-bonds",  # C9b3a-01
]

PREFIXES = """
@prefix elg: <https://www.nebularis.org/neuro-semantic/lattice/eligibility#> .
@prefix skos: <http://www.w3.org/2004/02/skos/core#> .
@prefix voc: <https://www.nebularis.org/neuro-semantic/lattice/vocabulary#> .
@prefix ex: <https://example.org/lattice/eligibility/> .
"""


def _shapes() -> Graph:
    shapes = Graph()
    for name in ("structural", "constraints", "rules"):
        shapes.parse(LAYER / "shapes" / f"{name}.ttl")
    return shapes


@pytest.fixture(scope="module", autouse=True)
def _cached_graphs(request: pytest.FixtureRequest, graph_cache, validated) -> None:
    """TM1/TM2: shared, session-scoped graphs and validation cache
    (python-test-melting)."""
    module = request.module
    module.SHAPES = graph_cache(LAYER / "shapes" / "structural.ttl", LAYER / "shapes" / "constraints.ttl",
                                 LAYER / "shapes" / "rules.ttl")
    module.SPEC = graph_cache(LAYER / "spec" / "eligibility.ttl")
    module.validate = validated


def results(data: Graph) -> list[tuple[URIRef, URIRef, URIRef]]:
    """(severity, source shape, focus node) for every validation result."""
    _, report, _ = validate(
        data,
        shacl_graph=SHAPES,
        ont_graph=SPEC,
        advanced=True,
        inference="none",
        allow_warnings=True,
    )
    found = []
    for result in report.subjects(RDF.type, SH.ValidationResult):
        found.append(
            (
                report.value(result, SH.resultSeverity),
                report.value(result, SH.sourceShape),
                report.value(result, SH.focusNode),
            )
        )
    return found


def example(name: str) -> Graph:
    return Graph().parse(LAYER / "examples" / f"{name}.ttl")


def declaration_warnings(data: Graph) -> list[URIRef]:
    return [focus for severity, shape, focus in results(data) if shape == DECLARATION and severity == SH.Warning]


@pytest.mark.parametrize("name", EXAMPLES)
def test_example_validates_with_no_results(name: str) -> None:
    # AOR2-01, AOR2-02, AOR2-03
    assert results(example(name)) == []


@pytest.mark.parametrize(
    "name, condition",
    [
        ("hierarchical-match", EX["hierarchical-condition"]),  # AOR2-04
        ("condition-taxonomy", EX["exact-condition"]),  # AOR2-05
        ("condition-taxonomy", EX["set-condition"]),  # AOR2-06
    ],
)
def test_removing_required_concept_raises_declaration_warning(name: str, condition: URIRef) -> None:
    data = example(name)
    data.remove((condition, ELG.requiredConcept, None))
    assert declaration_warnings(data) == [condition]


def test_profile_is_exempt_from_declaration_warning() -> None:
    # AOR2-07
    data = Graph().parse(
        data=PREFIXES
        + """
        ex:member a elg:Condition ;
            elg:matchStrategy elg:SetMembership ;
            elg:wildcardSemantics elg:NoWildcard ;
            elg:requiredConcept ex:a .
        ex:profile a elg:AdmissionProfile ;
            elg:hasCondition ex:member ;
            elg:compositionOperation elg:AllRequired .
        """,
        format="turtle",
    )
    assert declaration_warnings(data) == []


def test_condition_without_concepts_still_warns() -> None:
    # AOR2-08
    data = Graph().parse(
        data=PREFIXES
        + """
        ex:bare a elg:Condition ;
            elg:matchStrategy elg:SetMembership ;
            elg:wildcardSemantics elg:NoWildcard .
        """,
        format="turtle",
    )
    assert declaration_warnings(data) == [EX.bare]


def test_unreachable_exclusion_warns() -> None:
    # AOR2-09
    data = Graph().parse(
        data=PREFIXES
        + """
        ex:root a skos:Concept .
        ex:inside a skos:Concept ; skos:broader ex:root .
        ex:elsewhere a skos:Concept .
        ex:condition a elg:Condition ;
            elg:matchStrategy elg:HierarchicalMatch ;
            elg:wildcardSemantics elg:NoWildcard ;
            elg:requiredConcept ex:root ;
            elg:excludedConcept ex:inside , ex:elsewhere .
        """,
        format="turtle",
    )
    focus = [focus for severity, shape, focus in results(data) if shape == REACHABLE]
    assert focus == [EX.condition]


SHAPE_FILES = ["shapes/structural.ttl", "shapes/constraints.ttl", "shapes/rules.ttl"]


def _literate_check(root: Path) -> int:
    return literate_extract.main([
        str(LAYER / "README.md"), "--layer", "eligibility", "--root", str(root), "--proofs-root", str(ROOT / "tools" / "proofs"), "--reference-root", str(ROOT / "tools" / "reference"),
        "--check",
    ])


def test_readme_generates_every_file() -> None:
    # AOR2-10, C9b0-01: the README is Eligibility's whole source
    assert _literate_check(ROOT) == 0


def test_a_generated_file_edited_by_hand_fails_the_check(tmp_path: Path) -> None:
    # C9b0-02
    copy = tmp_path / "ontology" / "eligibility"
    shutil.copytree(LAYER, copy)
    edited = copy / "shapes" / "constraints.ttl"
    edited.write_text(edited.read_text().replace("sh:minCount 1", "sh:minCount 2", 1))
    assert _literate_check(tmp_path) == 1


def test_no_shape_is_declared_in_two_files() -> None:
    # C9b0-03
    seen: dict[URIRef, str] = {}
    for name in SHAPE_FILES:
        for shape in Graph().parse(LAYER / name).subjects(RDF.type, SH.NodeShape):
            assert shape not in seen, f"{shape} in {seen.get(shape)} and {name}"
            seen[shape] = name


def violations(data: Graph) -> list[tuple[URIRef, URIRef, object, URIRef]]:
    """(owning node shape, focus node, path, constraint component) per violation."""
    _, report, _ = validate(data, shacl_graph=SHAPES, ont_graph=SPEC, advanced=True, inference="none")
    found = []
    for result in report.subjects(RDF.type, SH.ValidationResult):
        if report.value(result, SH.resultSeverity) != SH.Violation:
            continue
        shape = report.value(result, SH.sourceShape)
        owner = SHAPES.value(predicate=SH.property, object=shape) or shape
        found.append((owner, report.value(result, SH.focusNode), report.value(result, SH.resultPath),
                      report.value(result, SH.sourceConstraintComponent)))
    return found


PROBES = {  # C9b0-04 to C9b0-09: each moved, renamed or once-duplicated shape fires on its probe
    "bare-condition": (ELG.SingleConditionMechanismShape, "ex:probe a elg:Condition .", 1),
    # ELC, OD-D46: a composition operation only on a profile, and a match strategy or wildcard policy never on one
    "composition-on-a-condition": (ELG.CompositionOnProfileShape, """
        ex:probe a elg:Condition ;
            elg:matchStrategy elg:ExactMatch ;
            elg:wildcardSemantics elg:NoWildcard ;
            elg:requiredConcept ex:a ;
            elg:compositionOperation elg:AllRequired .
        """, 1),
    "mechanism-on-a-profile": (ELG.AdmissionProfileShape, """
        ex:probe a elg:AdmissionProfile ;
            elg:hasCondition ex:c ;
            elg:compositionOperation elg:AllRequired ;
            elg:matchStrategy elg:ExactMatch ;
            elg:wildcardSemantics elg:NoWildcard .
        ex:c a elg:Condition ; elg:matchStrategy elg:ExactMatch ; elg:wildcardSemantics elg:NoWildcard ;
            elg:requiredConcept ex:a .
        """, 2),
    "wildcard": (ELG.WildcardPolicyConsistency, """
        ex:probe a elg:WildcardCondition ;
            elg:matchStrategy elg:Wildcard ;
            elg:wildcardSemantics elg:NoWildcard .
        """, 1),
    "empty-profile": (ELG.AdmissionProfileShape, """
        ex:probe a elg:AdmissionProfile ;
            elg:compositionOperation elg:AllRequired .
        """, 1),
    "empty-decision": (ELG.EligibilityDecisionShape, "ex:probe a elg:EligibilityDecision .", 4),
    "cyclic-scheme": (ELG.HierarchyWellFoundednessShape, """
        ex:contract voc:boundScheme ex:scheme .
        ex:a skos:inScheme ex:scheme ; skos:broader ex:b .
        ex:b skos:inScheme ex:scheme ; skos:broader ex:a .
        ex:probe a elg:Condition ;
            elg:matchStrategy elg:HierarchicalMatch ;
            elg:wildcardSemantics elg:NoWildcard ;
            elg:constrainedByContract ex:contract ;
            elg:requiredConcept ex:a .
        """, 1),
    "interval-without-range-set": (ELG.IntervalContainmentRequiresRangeSet, """
        ex:probe a elg:IntervalCondition ;
            elg:matchStrategy elg:IntervalContainment ;
            elg:wildcardSemantics elg:NoWildcard .
        """, 1),
}


@pytest.mark.parametrize("probe", PROBES)
def test_moved_shape_fires_once_on_its_probe(probe: str) -> None:
    shape, body, count = PROBES[probe]
    found = violations(Graph().parse(data=PREFIXES + body, format="turtle"))
    assert [focus for owner, focus, _, _ in found if owner == shape] == [EX.probe] * count, found
    assert len(found) == len(set(found)), f"a violation is reported twice: {found}"  # C9b0-10


def test_two_readings_and_a_double_negation_are_rejected() -> None:
    # AIR32-13
    data = Graph().parse(
        data=PREFIXES
        + """
        ex:c a elg:Condition ;
            elg:matchStrategy elg:SetMembership ;
            elg:wildcardSemantics elg:NoWildcard ;
            elg:requiredConcept ex:a ;
            elg:negated true , false .
        ex:b a elg:EvidenceBinding ;
            elg:bindsCondition ex:c ;
            elg:subjectClass ex:Thing ;
            elg:valueReading elg:SomeValue , elg:EveryValue ;
            elg:evidenceStep [ a elg:EvidenceStep ; elg:stepIndex 0 ; elg:stepProperty ex:p ; elg:stepDirection elg:Forward ] .
        """,
        format="turtle",
    )
    def violated(graph: Graph) -> set:
        return {focus for severity, _, focus in results(graph) if severity == SH.Violation}

    assert {EX.c, EX.b} <= violated(data)
    data.remove((EX.c, ELG.negated, None))
    data.remove((EX.b, ELG.valueReading, ELG.EveryValue))
    assert not {EX.c, EX.b} & violated(data)  # one reading and no negation conform


HIERARCHY_SHAPE = ELG.HierarchyRelationShape
HIERARCHY_WARNING = ELG.HierarchyRelationNeedsHierarchicalMatchShape


def _hierarchy_violations(data: Graph) -> list:
    return [(owner, focus) for owner, focus, _, _ in violations(data) if owner == HIERARCHY_SHAPE]


def test_the_hierarchy_relation_example_names_two_relations_over_one_scheme() -> None:
    # C9b3c-02
    data = example("hierarchy-relation")
    relations = {data.value(c, ELG.hierarchyRelation) for c in (EX["kind-of-tumour"], EX["part-of-tumour"])}
    assert relations == {EX["kind-of"], EX["part-of"]}
    assert data.value(EX["any-link-to-tumour"], ELG.hierarchyRelation) is None


def test_a_relation_with_no_route_to_broader_is_refused() -> None:
    # C9b3c-03: removing the sub-property declaration is the adversarial probe
    data = example("hierarchy-relation")
    data.remove((EX["kind-of"], URIRef("http://www.w3.org/2000/01/rdf-schema#subPropertyOf"), None))
    assert _hierarchy_violations(data) == [(HIERARCHY_SHAPE, EX["kind-of-tumour"])]


def test_broader_itself_and_a_two_step_sub_property_are_accepted() -> None:
    # C9b3c-04
    data = Graph().parse(
        data=PREFIXES
        + """
        @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
        ex:near rdfs:subPropertyOf ex:linked . ex:linked rdfs:subPropertyOf skos:broader .
        ex:a a elg:Condition ; elg:matchStrategy elg:HierarchicalMatch ; elg:wildcardSemantics elg:NoWildcard ;
            elg:requiredConcept ex:x ; elg:hierarchyRelation skos:broader .
        ex:b a elg:Condition ; elg:matchStrategy elg:HierarchicalMatch ; elg:wildcardSemantics elg:NoWildcard ;
            elg:requiredConcept ex:x ; elg:hierarchyRelation ex:near .
        """,
        format="turtle",
    )
    assert _hierarchy_violations(data) == []


def test_a_condition_names_at_most_one_relation() -> None:
    # C9b3c-05, cardinality above one
    data = example("hierarchy-relation")
    data.add((EX["kind-of-tumour"], ELG.hierarchyRelation, EX["part-of"]))
    assert _hierarchy_violations(data) == [(HIERARCHY_SHAPE, EX["kind-of-tumour"])]


def test_a_relation_on_a_condition_that_does_not_match_hierarchically_warns() -> None:
    # C9b3c-06
    data = example("hierarchy-relation")
    data.set((EX["kind-of-tumour"], ELG.matchStrategy, ELG.SetMembership))
    warned = [focus for severity, shape, focus in results(data) if shape == HIERARCHY_WARNING and severity == SH.Warning]
    assert warned == [EX["kind-of-tumour"]]
    assert _hierarchy_violations(data) == []


SET_COMPARISON = ELG.SetComparisonShape
SET_BINDINGS = ELG.SetComparisonBindingsShape
SET_BINDING = ELG.SetComparisonBindingShape
LICENSING = Namespace("https://example.org/lattice/eligibility/licensing/")
MEDICATIONS = Namespace("https://example.org/lattice/eligibility/medications/")
RESOLUTION = Namespace("https://example.org/lattice/eligibility/resolution/")
RDFS_NS = Namespace("http://www.w3.org/2000/01/rdf-schema#")


def _owners(data: Graph) -> list:
    """(owning node shape, focus node) for every violation, sorted."""
    return sorted((owner, focus) for owner, focus, _, _ in violations(data))


def test_the_set_comparison_examples_name_two_distinct_bindings_over_one_subject_class() -> None:
    # C9b3a-02
    for name, namespace, comparisons in (
        ("set-comparison-licensing", LICENSING, ["distribution-within-grant"]),
        ("set-comparison-trial", MEDICATIONS, ["no-prohibited-medication"]),
        ("set-comparison-bonds", RESOLUTION, ["all-consented", "some-consented"]),
    ):
        data = example(name)
        for local in comparisons:
            comparison = namespace[local]
            tested, reference = data.value(comparison, ELG.testedBinding), data.value(comparison, ELG.referenceBinding)
            assert tested != reference and None not in (tested, reference)
            assert data.value(tested, ELG.bindsCondition) == data.value(reference, ELG.bindsCondition) == comparison
            assert data.value(tested, ELG.subjectClass) == data.value(reference, ELG.subjectClass)


def test_a_set_comparison_states_nothing_to_match_without_warning() -> None:
    # C9b3a-03: the declaration warning exempts a comparison, and still warns of a bare concept condition
    assert declaration_warnings(example("set-comparison-trial")) == []
    bare = Graph().parse(
        data=PREFIXES + "ex:bare a elg:Condition ; elg:matchStrategy elg:ExactMatch ; elg:wildcardSemantics elg:NoWildcard .",
        format="turtle",
    )
    assert declaration_warnings(bare) == [EX.bare]


def test_a_comparison_declares_exactly_one_comparison() -> None:
    # C9b3a-04: zero, then two
    zero = example("set-comparison-trial")
    zero.remove((MEDICATIONS["no-prohibited-medication"], ELG.comparison, None))
    assert (SET_COMPARISON, MEDICATIONS["no-prohibited-medication"]) in _owners(zero)
    two = example("set-comparison-trial")
    two.add((MEDICATIONS["no-prohibited-medication"], ELG.comparison, ELG.Subset))
    assert (SET_COMPARISON, MEDICATIONS["no-prohibited-medication"]) in _owners(two)


def test_a_comparison_names_exactly_one_tested_and_one_reference_binding() -> None:
    # C9b3a-05: each at zero and above one
    focus = MEDICATIONS["no-prohibited-medication"]
    for link in (ELG.testedBinding, ELG.referenceBinding):
        zero = example("set-comparison-trial")
        zero.remove((focus, link, None))
        assert (SET_COMPARISON, focus) in _owners(zero)
        many = example("set-comparison-trial")
        many.add((focus, link, MEDICATIONS["extra-binding"]))
        assert (SET_COMPARISON, focus) in _owners(many)


def test_a_comparison_whose_two_bindings_are_one_is_refused() -> None:
    # C9b3a-06
    data = example("set-comparison-trial")
    focus = MEDICATIONS["no-prohibited-medication"]
    data.set((focus, ELG.referenceBinding, MEDICATIONS["medication-binding"]))
    assert (SET_BINDINGS, focus) in _owners(data)


def test_a_binding_that_does_not_name_its_comparison_is_refused() -> None:
    # C9b3a-07
    data = example("set-comparison-trial")
    data.remove((MEDICATIONS["prohibited-binding"], ELG.bindsCondition, None))
    owners = _owners(data)
    assert (SET_BINDINGS, MEDICATIONS["no-prohibited-medication"]) in owners


def test_two_bindings_over_different_subject_classes_are_refused() -> None:
    # C9b3a-08
    data = example("set-comparison-trial")
    data.set((MEDICATIONS["prohibited-binding"], ELG.subjectClass, MEDICATIONS.Protocol))
    assert (SET_BINDINGS, MEDICATIONS["no-prohibited-medication"]) in _owners(data)


def test_a_binding_of_a_comparison_declares_no_reading_and_no_space() -> None:
    # C9b3a-09: either binding, and each property
    for binding in ("medication-binding", "prohibited-binding"):
        for prop, value in ((ELG.valueReading, ELG.SomeValue), (ELG.readOnSpace, MEDICATIONS.space)):
            data = example("set-comparison-trial")
            data.add((MEDICATIONS[binding], prop, value))
            assert (SET_BINDINGS, MEDICATIONS["no-prohibited-medication"]) in _owners(data), (binding, prop)


def test_a_binding_of_a_comparison_that_the_comparison_does_not_name_is_refused() -> None:
    # C9b3a-10
    data = example("set-comparison-trial")
    stray = MEDICATIONS["stray-binding"]
    for triple in (
        (stray, RDF.type, ELG.EvidenceBinding),
        (stray, ELG.bindsCondition, MEDICATIONS["no-prohibited-medication"]),
        (stray, ELG.subjectClass, MEDICATIONS.Participant),
    ):
        data.add(triple)
    data.add((stray, ELG.evidenceStep, MEDICATIONS["stray-step"]))
    for triple in (
        (MEDICATIONS["stray-step"], RDF.type, ELG.EvidenceStep),
        (MEDICATIONS["stray-step"], ELG.stepIndex, Literal(0)),
        (MEDICATIONS["stray-step"], ELG.stepProperty, MEDICATIONS.takes),
        (MEDICATIONS["stray-step"], ELG.stepDirection, ELG.Forward),
    ):
        data.add(triple)
    assert _owners(data) == [(SET_BINDING, stray)]


def test_a_comparison_matches_exactly_or_hierarchically_and_names_no_concept() -> None:
    # C9b3a-11
    wrong = example("set-comparison-trial")
    wrong.set((MEDICATIONS["no-prohibited-medication"], ELG.matchStrategy, ELG.SetMembership))
    assert (SET_COMPARISON, MEDICATIONS["no-prohibited-medication"]) in _owners(wrong)
    for prop in (ELG.requiredConcept, ELG.excludedConcept):
        named = example("set-comparison-trial")
        named.add((MEDICATIONS["no-prohibited-medication"], prop, MEDICATIONS.aspirin))
        assert (SET_COMPARISON, MEDICATIONS["no-prohibited-medication"]) in _owners(named), prop


def test_a_closure_without_a_reading_is_still_refused_on_an_ordinary_binding() -> None:
    # C9b3a-12: the exemption is for a comparison's bindings only
    data = Graph().parse(
        data=PREFIXES
        + """
        ex:c a elg:Condition ; elg:matchStrategy elg:SetMembership ; elg:wildcardSemantics elg:NoWildcard ;
            elg:requiredConcept ex:a .
        ex:b a elg:EvidenceBinding ; elg:bindsCondition ex:c ; elg:subjectClass ex:Thing ; elg:closedUnder ex:cl ;
            elg:evidenceStep [ a elg:EvidenceStep ; elg:stepIndex 0 ; elg:stepProperty ex:p ; elg:stepDirection elg:Forward ] .
        ex:cl a elg:Closure ; elg:licensedBy ex:source .
        """,
        format="turtle",
    )
    assert _owners(data) == [(ELG.ClosureNeedsSetReadingShape, EX.b)]
