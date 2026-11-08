# SPDX-License-Identifier: MPL-2.0

"""The verification rig module (ADR-A153). Validates the module's examples against the structural
shapes and the fact-state constraint with the spec loaded beside them, checks the module imports
nothing and names no layer term, and that the README's extraction matches the committed Turtle."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
from rdflib import Graph, URIRef
from rdflib.namespace import OWL, SH

ROOT = Path(__file__).resolve().parents[1]
V_RIG = ROOT / "ontology" / "v-rig"
SPEC_IRI = URIRef("https://www.nebularis.org/neuro-semantic/lattice/v-rig")

sys.path.insert(0, str(ROOT / "tools"))
from conftest import repo_files  # noqa: E402


@pytest.fixture(scope="module", autouse=True)
def _cached_graphs(request: pytest.FixtureRequest, graph_cache, validated) -> None:
    module = request.module
    module.MODEL = graph_cache(V_RIG / "spec" / "v-rig.ttl", V_RIG / "vocab" / "v-rig-vocab.ttl")
    module.SHAPES = graph_cache(V_RIG / "shapes" / "structural.ttl", V_RIG / "shapes" / "constraints.ttl")
    module.validate = validated


ACCEPTED = ["declared-facts", "body-nodes", "programme-and-findings"]
REFUSALS = {
    "refusal-fact-without-state": "exactly one of these holds",
    "refusal-node-without-locator": "exactly one locator",
    "refusal-finding-without-kind": "exactly one kind",
}


def _example(name: str) -> Graph:
    return Graph().parse(V_RIG / "examples" / f"{name}.ttl")


def _messages(report: Graph) -> set[str]:
    return {str(report.value(r, SH.resultMessage)) for r in report.subjects(SH.resultSeverity, SH.Violation)}


@pytest.mark.parametrize("name", ACCEPTED)
def test_accepted_examples_conform(name: str) -> None:
    conforms, report, _ = validate(MODEL + _example(name), shacl_graph=SHAPES, inference="rdfs", advanced=True)
    assert conforms, _messages(report)


@pytest.mark.parametrize("name,message", REFUSALS.items())
def test_refusals_fail_the_named_shape(name: str, message: str) -> None:
    conforms, report, _ = validate(MODEL + _example(name), shacl_graph=SHAPES, inference="rdfs", advanced=True)
    assert not conforms
    assert any(message in m for m in _messages(report)), (name, _messages(report))


def test_fact_state_refuses_both_states_together() -> None:
    """The second fact of the refusal carries a value and the unknown marker, so the xone refuses it too."""
    conforms, report, _ = validate(MODEL + _example("refusal-fact-without-state"), shacl_graph=SHAPES,
                                   inference="rdfs", advanced=True)
    focus = {str(report.value(r, SH.focusNode)).rsplit(":", 1)[-1] for r in report.subjects(SH.resultSeverity, SH.Violation)}
    assert {"fact-limit", "fact-attachment"} <= focus, focus


def test_spec_imports_nothing() -> None:
    assert list(MODEL.objects(SPEC_IRI, OWL.imports)) == []


def test_spec_names_no_layer_term() -> None:
    hits = repo_files(["ontology/v-rig/spec", "ontology/v-rig/vocab", "ontology/v-rig/shapes"],
                      r"\b(voc|qnt|ldg|pty|elg|wrd|bhv|ins):[A-Za-z]|\bfnd:(?!utility\b)[A-Za-z]")
    assert hits == []


def test_literate_extraction_matches_committed_turtle() -> None:
    result = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "literate_extract.py"),
         str(V_RIG / "README.md"), "--layer", "v-rig", "--root", str(ROOT), "--check"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
