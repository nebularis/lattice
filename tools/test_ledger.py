# SPDX-License-Identifier: MPL-2.0

"""Ledger LG-1: the configuration document (ADR-A131). Row IDs are the plan's LG-1 "in detail"
table. Validates LG-0's examples (configuration part only: the runtime document is LG-2) against
the structural shapes and the six SHACL-SPARQL constraints, checks the import guard holds, the
spec names no term of Party, Eligibility, Wording, Instrument or Behaviour, and the generated
cycle shape finishes on a larger generated tree."""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

import pytest
from pyshacl import validate
from rdflib import Graph, Namespace, URIRef
from rdflib.namespace import SH

ROOT = Path(__file__).resolve().parents[1]
ONTOLOGY = ROOT / "ontology"
LEDGER = ONTOLOGY / "ledger"
LATTICE = "https://www.nebularis.org/neuro-semantic/lattice/"
LDG = Namespace(LATTICE + "ledger#")
QNT = Namespace(LATTICE + "quantification#")

sys.path.insert(0, str(ROOT / "tools"))
import literate_extract  # noqa: E402
from conftest import repo_files  # noqa: E402


def _graph(*sources) -> Graph:
    g = Graph()
    for source in sources:
        g.parse(source) if isinstance(source, Path) else g.parse(data=source, format="turtle")
    return g


@pytest.fixture(scope="module", autouse=True)
def _cached_graphs(request: pytest.FixtureRequest, graph_cache, validated) -> None:
    module = request.module
    module.MODEL = graph_cache(
        ONTOLOGY / "foundation" / "spec" / "foundation.ttl",
        ONTOLOGY / "vocabulary" / "spec" / "vocabulary.ttl",
        ONTOLOGY / "quantification" / "spec" / "quantification.ttl",
        LEDGER / "spec" / "ledger.ttl",
        LEDGER / "vocab" / "ledger-vocab.ttl",
    )
    module.SHAPES = graph_cache(LEDGER / "shapes" / "structural.ttl", LEDGER / "shapes" / "constraints.ttl")
    module.validate = validated


ACCEPTED = ["licence-seats", "revolving-facility", "research-grant", "authority-aggregate", "insurance-aggregate"]
REFUSALS = {
    "refusal-cycle": "NoCycleThroughPartOfShape",
    "refusal-unit": "ChildUnitMatchesParentShape",
    "refusal-proportional-unrounded": "ProportionalNeedsRoundingShape",
    "refusal-intensive-unit": "ExtensiveUnitOfAccountShape",
}


def _example(name: str) -> Graph:
    return _graph(LEDGER / "examples" / f"{name}.ttl")


def _violating_shapes(report: Graph) -> set[str]:
    return {str(report.value(r, SH.sourceShape)) for r in report.subjects(SH.resultSeverity, SH.Violation)}


# ---- LG1-02: LG-0's accepted examples, configuration part, conform -----------

@pytest.mark.parametrize("name", ACCEPTED)
def test_accepted_examples_conform(name: str) -> None:
    conforms, report, _ = validate(MODEL + _example(name), shacl_graph=SHAPES, inference="none", advanced=True)
    assert conforms, _violating_shapes(report)


# ---- LG1-03, LG1-04, LG1-05, LG1-05b: each refusal fails its named shape -----

@pytest.mark.parametrize("name,shape", REFUSALS.items())
def test_refusals_fail_the_named_shape(name: str, shape: str) -> None:
    conforms, report, _ = validate(MODEL + _example(name), shacl_graph=SHAPES, inference="none", advanced=True)
    assert not conforms
    hit = {s for s in _violating_shapes(report) if s.endswith(f"#{shape}")}
    assert hit, (name, shape, _violating_shapes(report))


# ---- LG1-06: the import guard -------------------------------------------------

def test_imports_only_foundation_vocabulary_quantification() -> None:
    imports = {str(o) for o in MODEL.objects(URIRef("https://www.nebularis.org/neuro-semantic/ledger"),
                                              URIRef("http://www.w3.org/2002/07/owl#imports"))}
    assert all("/foundation/" in i or "/vocabulary/" in i or "/quantification/" in i for i in imports)


# ---- LG1-07: no term of Party, Eligibility, Wording, Instrument or Behaviour --

def test_spec_names_no_higher_layer() -> None:
    hits = repo_files(["ontology/ledger/spec", "ontology/ledger/vocab"], r"\b(ins|bhv|elg|pty|wrd):")
    assert hits == []


# ---- LG1-01: the README's extraction is consistent with the committed Turtle -

def test_literate_extraction_matches_committed_turtle() -> None:
    result = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "literate_extract.py"),
         str(LEDGER / "README.md"), "--layer", "ledger", "--root", str(ROOT), "--check"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr


# ---- LG1-09: the cycle shape finishes on a larger generated tree, time recorded

def test_cycle_shape_scales(record_property) -> None:
    """10,000 account definitions in a shallow, wide tree (a root, 99 sections each part of
    it, the rest sublimits spread across the sections), the shape real account trees actually
    have (an aggregate, its sections, their sublimits), never a single 10,000-deep chain, which
    is both unrealistic and recurses past rdflib's property-path evaluator's Python call depth."""
    g = Graph()
    g += MODEL
    prefixes = f"@prefix ldg: <{LDG}> .\n@prefix qnt: <{QNT}> .\n@prefix ex: <https://example.org/lattice/ledger/scale/> .\n"
    lines = ["ex:space a qnt:ValueSpace ; qnt:spaceKey \"scale\" ; qnt:orderKind qnt:TotalOrder ; "
             "qnt:densityKind qnt:Discrete ; qnt:spaceHash \"scale-v1\" ; qnt:additivity qnt:Extensive ; "
             "qnt:hasOperationCapability ex:sum , ex:diff .",
             "ex:sum a qnt:OperationCapability ; qnt:operationKind qnt:Sum ; qnt:resultSpace ex:space .",
             "ex:diff a qnt:OperationCapability ; qnt:operationKind qnt:Difference ; qnt:resultSpace ex:space .",
             "ex:amount a qnt:Quantity ; qnt:onSpace ex:space ; qnt:numericValue \"100\"^^<http://www.w3.org/2001/XMLSchema#decimal> .",
             "ex:root a ldg:AccountDefinition ; ldg:statedAmount ex:amount ; ldg:unitOfAccount ex:space ; "
             "ldg:admitsOwnerKind qnt:ValueSpace ; ldg:mergeRule ldg:Refuse ."]
    sections = 99
    for s in range(sections):
        lines.append(f"ex:section{s} a ldg:AccountDefinition ; ldg:statedAmount ex:amount ; "
                      f"ldg:unitOfAccount ex:space ; ldg:admitsOwnerKind qnt:ValueSpace ; "
                      f"ldg:mergeRule ldg:Refuse ; ldg:partOf ex:root .")
    for i in range(10_000 - 1 - sections):
        section = i % sections
        lines.append(f"ex:sublimit{i} a ldg:AccountDefinition ; ldg:statedAmount ex:amount ; "
                      f"ldg:unitOfAccount ex:space ; ldg:admitsOwnerKind qnt:ValueSpace ; "
                      f"ldg:mergeRule ldg:Refuse ; ldg:partOf ex:section{section} .")
    g += _graph(prefixes + "\n".join(lines))
    started = time.monotonic()
    conforms, report, _ = validate(g, shacl_graph=SHAPES, inference="none", advanced=True)
    elapsed = time.monotonic() - started
    record_property("cycle_shape_10000_seconds", elapsed)
    assert conforms
