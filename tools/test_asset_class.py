# SPDX-License-Identifier: MPL-2.0

"""The reference asset class edition, its mobility characteristic and its constraints
(unit `asset-class`, slice ASC-2, ontology/applied/asset-class/README.md).

Data graph: the spec and vocab documents, the classification module's vocab document
(for the contract the edition binds) and an example. Shapes graph: the module's
constraints and Vocabulary's shapes. Refusals other than the shipped example mutate a
fresh copy of the edition, each breaking one rule.
"""

from __future__ import annotations

import subprocess
import sys
from collections import Counter
from pathlib import Path

import pytest
from pyshacl import validate
from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import RDF

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "ontology" / "applied" / "asset-class"
CLASSIFICATION = ROOT / "ontology" / "applied" / "classification"
VOCABULARY_SHAPES = ROOT / "ontology" / "vocabulary" / "shapes"

ASC = Namespace("https://www.nebularis.org/neuro-semantic/lattice/applied/asset-class#")
ASCV = Namespace("https://www.nebularis.org/neuro-semantic/lattice/applied/asset-class/vocab#")
CLSV = Namespace("https://www.nebularis.org/neuro-semantic/lattice/applied/classification/vocab#")
SKOS = Namespace("http://www.w3.org/2004/02/skos/core#")
VOC = Namespace("https://www.nebularis.org/neuro-semantic/lattice/vocabulary#")
SH = Namespace("http://www.w3.org/ns/shacl#")
EX = Namespace("https://example.org/asset-class#")


def _graph(*paths: Path) -> Graph:
    g = Graph()
    for path in paths:
        g.parse(path)
    return g


def _edition() -> Graph:
    return _graph(MODULE / "spec" / "asset-class.ttl", MODULE / "vocab" / "asset-class-vocab.ttl",
                  CLASSIFICATION / "vocab" / "classification-vocab.ttl")


SHAPES = _graph(MODULE / "shapes" / "constraints.ttl", VOCABULARY_SHAPES / "structural.ttl",
                VOCABULARY_SHAPES / "constraints.ttl")
EDITION = _edition()


def _violations(data: Graph) -> set[tuple[URIRef, URIRef, object]]:
    """(source shape, focus node, value) of every result."""
    _, report, _ = validate(data, shacl_graph=SHAPES, advanced=True, allow_warnings=True)
    out = set()
    for result in report.subjects(RDF.type, SH.ValidationResult):
        out.add((report.value(result, SH.sourceShape), report.value(result, SH.focusNode),
                 report.value(result, SH.value)))
    return out


def _copy() -> Graph:
    g = Graph()
    for triple in EDITION:
        g.add(triple)
    return g


def _concepts(scheme: URIRef = ASCV.AssetClassScheme) -> set[URIRef]:
    return set(EDITION.subjects(SKOS.inScheme, scheme))


def test_asc2_01_the_readme_is_the_source_of_the_documents() -> None:
    result = subprocess.run(
        [sys.executable, "tools/literate_extract.py", "ontology/applied/asset-class/README.md",
         "--layer", "applied/asset-class", "--root", ".", "--check"],
        cwd=ROOT, capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_asc2_02_the_edition_and_the_well_formed_example_conform() -> None:
    data = _copy()
    data.parse(MODULE / "examples" / "well-formed.ttl")
    assert _violations(data) == set()


def test_asc2_03_the_edition_is_one_tree_under_its_top_concepts() -> None:
    concepts = _concepts()
    tops = set(EDITION.objects(ASCV.AssetClassScheme, SKOS.hasTopConcept))
    assert tops == {ASCV.NonFinancialAsset, ASCV.FinancialAsset}
    narrower: dict[URIRef, list[URIRef]] = {}
    for concept in concepts - tops:
        parents = list(EDITION.objects(concept, SKOS.broader))
        assert len(parents) == 1 and parents[0] in concepts, concept
        narrower.setdefault(parents[0], []).append(concept)
    reached, todo = Counter(), list(tops)
    while todo:
        concept = todo.pop()
        reached[concept] += 1
        todo.extend(narrower.get(concept, []))
    assert set(reached) == concepts and set(reached.values()) == {1}
    assert len(concepts) > 90


def test_asc2_04_a_concept_with_two_broader_concepts_is_refused() -> None:
    data = _copy()
    data.add((ASCV.Vessel, SKOS.broader, ASCV.MobilePlant))
    found = _violations(data)
    assert (ASC.ReferenceTreeShape, ASCV.AssetClassScheme, ASCV.Vessel) in found


@pytest.mark.parametrize("change", ["missing", "different"])
def test_asc2_05_a_narrower_concept_without_its_broader_concepts_mobility_is_refused(change: str) -> None:
    data = _copy()
    data.remove((ASCV.Vessel, ASC.mobility, ASCV.Mobile))
    if change == "different":
        data.add((ASCV.Vessel, ASC.mobility, ASCV.Stationary))
    found = _violations(data)
    assert (ASC.MobilityInheritedShape, ASCV.TransportEquipment, ASCV.Vessel) in found


def test_asc2_05_the_shipped_refusal_is_refused_by_the_inherited_mobility_shape() -> None:
    data = _copy()
    data.parse(MODULE / "examples" / "refusal-mobility.ttl")
    assert _violations(data) == {(ASC.MobilityInheritedShape, EX.Vehicle, EX.ParkedTrailer)}


@pytest.mark.parametrize("value", [ASCV.Vessel, EX.Wandering])
def test_asc2_06_a_mobility_outside_the_mobility_scheme_is_refused(value: URIRef) -> None:
    data = _copy()
    data.add((ASCV.ComputerSoftware, ASC.mobility, value))
    found = _violations(data)
    assert (ASC.MobilityValueShape, ASCV.ComputerSoftware, value) in found


def test_asc2_06_two_mobilities_are_refused() -> None:
    data = _copy()
    data.add((ASCV.Land, ASC.mobility, ASCV.Mobile))
    assert any(shape == ASC.MobilityValueShape and focus == ASCV.Land for shape, focus, _ in _violations(data))


@pytest.mark.parametrize("remove", [
    (ASCV.AssetClassScheme, SKOS.hasTopConcept, ASCV.FinancialAsset),
    (ASCV.FinancialAsset, SKOS.topConceptOf, ASCV.AssetClassScheme),
])
def test_asc2_07_a_top_concept_listed_one_way_only_is_refused(remove: tuple) -> None:
    data = _copy()
    data.remove(remove)
    found = _violations(data)
    assert any(shape == ASC.ReferenceTreeShape and focus == ASCV.AssetClassScheme and value == ASCV.FinancialAsset
               for shape, focus, value in found)


def test_asc2_07_a_cycle_that_reaches_no_top_concept_is_refused() -> None:
    data = _copy()
    data.remove((ASCV.Valuable, SKOS.broader, ASCV.ProducedAsset))
    data.add((ASCV.Valuable, SKOS.broader, ASCV.OtherValuable))
    found = _violations(data)
    assert (ASC.ReferenceTreeShape, ASCV.AssetClassScheme, ASCV.Valuable) in found


def test_asc2_08_the_asset_class_contract_is_bound_to_the_edition_once() -> None:
    assert list(EDITION.objects(CLSV.AssetClassContract, VOC.boundScheme)) == [ASCV.AssetClassScheme]
    data = _copy()
    data.add((CLSV.AssetClassContract, VOC.boundScheme, EX.OtherScheme))
    assert any(focus == CLSV.AssetClassContract for _, focus, _ in _violations(data))


def test_asc2_09_every_concept_is_documented_and_cites_its_source() -> None:
    for scheme in (ASCV.AssetClassScheme, ASCV.MobilityScheme):
        for concept in _concepts(scheme):
            for prop in (SKOS.prefLabel, SKOS.definition, SKOS.note):
                values = [v for v in EDITION.objects(concept, prop) if isinstance(v, Literal) and v.language == "en"]
                assert values, (concept, prop)
    for concept in _concepts():
        note = str(EDITION.value(concept, SKOS.note))
        assert note.startswith(("Follows SNA 2008 ", "Groups SNA 2008 ")), concept
    data = _copy()
    data.remove((ASCV.Loan, SKOS.note, None))
    assert (ASC.ReferenceDocumentationShape, ASCV.AssetClassScheme, ASCV.Loan) in _violations(data)
