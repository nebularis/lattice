# SPDX-License-Identifier: MPL-2.0

"""Eligibility examples validate cleanly, and the concept-declaration warning
fires exactly where ADR-A87 says it should.

Data graph: an example plus ``spec/eligibility.ttl``, so ``sh:targetClass``
reaches instances of subclasses. Shapes graph: the layer's three shape files.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from pyshacl import validate
from rdflib import Graph, Namespace, URIRef
from rdflib.compare import isomorphic
from rdflib.namespace import RDF

ROOT = Path(__file__).resolve().parents[1]
LAYER = ROOT / "ontology" / "eligibility"
ELG = Namespace("https://www.nebularis.org/neuro-semantic/lattice/eligibility#")
EX = Namespace("https://example.org/lattice/eligibility/")
SH = Namespace("http://www.w3.org/ns/shacl#")

DECLARATION = ELG.ConceptConditionDeclarationShape
REACHABLE = ELG.ReachableExclusionShape
EXAMPLES = ["hierarchical-match", "condition-taxonomy", "interval-containment", "evidence-binding"]

PREFIXES = """
@prefix elg: <https://www.nebularis.org/neuro-semantic/lattice/eligibility#> .
@prefix skos: <http://www.w3.org/2004/02/skos/core#> .
@prefix ex: <https://example.org/lattice/eligibility/> .
"""


def _shapes() -> Graph:
    shapes = Graph()
    for name in ("structural", "constraints", "rules"):
        shapes.parse(LAYER / "shapes" / f"{name}.ttl")
    return shapes


SHAPES = _shapes()
SPEC = Graph().parse(LAYER / "spec" / "eligibility.ttl")


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


def _readme_shapes() -> Graph:
    text = (LAYER / "README.md").read_text()
    blocks = re.findall(r"```turtle-shapes\n(.*?)```", text, re.S)
    graph = Graph()
    for block in blocks:
        graph.parse(data=block, format="turtle")
    return graph


@pytest.mark.parametrize("shape", [DECLARATION, REACHABLE])
def test_readme_mirrors_shape_file(shape: URIRef) -> None:
    # AOR2-10
    constraints = Graph().parse(LAYER / "shapes" / "constraints.ttl")
    assert isomorphic(_readme_shapes().cbd(shape), constraints.cbd(shape))
