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
from rdflib import Graph, Namespace, URIRef
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
            elg:compatibilityOperation elg:AllRequired ;
            elg:wildcardSemantics elg:NoWildcard ;
            elg:requiredConcept ex:a .
        ex:profile a elg:AdmissionProfile ;
            elg:hasCondition ex:member ;
            elg:matchStrategy elg:SetMembership ;
            elg:compatibilityOperation elg:AllRequired ;
            elg:wildcardSemantics elg:NoWildcard .
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
            elg:compatibilityOperation elg:AllRequired ;
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
            elg:compatibilityOperation elg:AllRequired ;
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
        str(LAYER / "README.md"), "--layer", "eligibility", "--root", str(root), "--shapes", *SHAPE_FILES,
        "--proofs-root", str(ROOT / "tools" / "proofs"), "--reference-root", str(ROOT / "tools" / "reference"),
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
    "bare-condition": (ELG.ConditionShape, "ex:probe a elg:Condition .", 3),
    "wildcard": (ELG.WildcardPolicyConsistency, """
        ex:probe a elg:WildcardCondition ;
            elg:matchStrategy elg:Wildcard ;
            elg:compatibilityOperation elg:AllRequired ;
            elg:wildcardSemantics elg:NoWildcard .
        """, 1),
    "empty-profile": (ELG.AdmissionProfileShape, """
        ex:probe a elg:AdmissionProfile ;
            elg:matchStrategy elg:SetMembership ;
            elg:compatibilityOperation elg:AllRequired ;
            elg:wildcardSemantics elg:NoWildcard .
        """, 1),
    "empty-decision": (ELG.EligibilityDecisionShape, "ex:probe a elg:EligibilityDecision .", 4),
    "cyclic-scheme": (ELG.HierarchyWellFoundednessShape, """
        ex:contract voc:boundScheme ex:scheme .
        ex:a skos:inScheme ex:scheme ; skos:broader ex:b .
        ex:b skos:inScheme ex:scheme ; skos:broader ex:a .
        ex:probe a elg:Condition ;
            elg:matchStrategy elg:HierarchicalMatch ;
            elg:compatibilityOperation elg:AllRequired ;
            elg:wildcardSemantics elg:NoWildcard ;
            elg:constrainedByContract ex:contract ;
            elg:requiredConcept ex:a .
        """, 1),
    "interval-without-range-set": (ELG.IntervalContainmentRequiresRangeSet, """
        ex:probe a elg:IntervalCondition ;
            elg:matchStrategy elg:IntervalContainment ;
            elg:compatibilityOperation elg:AllRequired ;
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
            elg:compatibilityOperation elg:AllRequired ;
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
