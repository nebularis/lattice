# SPDX-License-Identifier: MPL-2.0
"""The checks over P1 on the mini-rig: the layers' shapes, the consistency check and the competency queries, each
answer that is not clean a located finding."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from rdflib import RDF, Graph, Literal, URIRef

from v_rig import lift, read_rig
from v_rig.lift import VRIG, RunInfo
from v_rig import p1, p1_checks

HERE = Path(__file__).resolve().parent
MINI_RIG = HERE / "mini-rig"
EXTENSION = HERE / "mini-rig.extension.ttl"
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "tools"))
RUN = RunInfo("0000000000000000000000000000000000000000", "0.0.0", "0.1.0", None)


@pytest.fixture(scope="module")
def graph():
    return lift(read_rig(MINI_RIG), RUN)


@pytest.fixture(scope="module")
def layers(graph):
    return p1.project(graph, [EXTENSION]).layers


@pytest.fixture(scope="module")
def modules():
    return p1_checks.layer_graphs()


@pytest.fixture(scope="module")
def shapes(graph, layers, modules):
    result = p1_checks.ChecksResult()
    p1_checks.validate_layers(graph, layers, result, modules)
    return result


@pytest.fixture(scope="module")
def competency(graph, layers):
    result = p1_checks.ChecksResult()
    p1_checks.ask_competency(graph, layers, result)
    return result


def test_every_target_layer_with_shapes_is_validated(shapes):
    assert {"foundation", "ledger", "wording", "instrument", "quantification"} <= set(shapes.shape_reports)


def test_each_shape_violation_is_a_located_finding(graph, shapes):
    violations = [f for f in shapes.findings if f[0] == VRIG.ShapeViolation]
    assert violations
    for _, locator, _, message, _ in violations:
        assert (locator, RDF.type, VRIG.Locator) in graph
        assert graph.value(locator, VRIG.documentId) is not None
        assert ": " in message


def test_a_violation_on_a_projected_node_lands_on_the_node_it_came_from(graph, shapes):
    """An element Foundation refuses, for want of an identity, is located at the body node it was projected from."""
    located = [(locator, key) for _, locator, key, message, _ in shapes.findings if message.startswith("foundation:") and "VersionedShape" in key]
    assert located
    ids = {str(graph.value(locator, VRIG.documentId)) for locator, _ in located}
    assert {"prim-001", "xs1-001"} <= ids <= {"prim-001", "xs1-001", "xs2-001", "xs2-002", "prog-001", "events"}, ids
    assert len({(str(l), k) for l, k in located}) == len(located), "one finding per node and constraint"


def test_findings_written_into_the_representation_conform_to_the_module_shapes(graph, shapes, competency):
    from pyshacl import validate
    import lattice_repo_catalogue as reader
    copy = Graph()
    copy += graph
    run = URIRef("urn:lattice-v-rig:v1:run:test")
    copy.add((run, RDF.type, VRIG.Run))
    for predicate in ("rigDigest", "formatVersion", "checkoutCommit", "substrateRelease", "vocabularyVersion"):
        copy.add((run, VRIG[predicate], Literal("x")))
    written = p1.add_findings(copy, run, shapes.findings + competency.findings)
    assert written == len(shapes.findings) + len(competency.findings)
    module = reader.load(ROOT).module("v-rig")
    spec, module_shapes = Graph(), Graph()
    for path in module.files("spec") + module.files("vocab"):
        spec.parse(path, format="turtle")
    for path in module.files("shapes"):
        module_shapes.parse(path, format="turtle")
    conforms, _, text = validate(copy + spec, shacl_graph=module_shapes, inference="rdfs", advanced=True)
    assert conforms, text[:2000]


def test_back_locator_reads_the_identifier(graph):
    document = next(d for d in graph.subjects(RDF.type, VRIG.Document) if str(graph.value(d, VRIG.rigId)) == "prim-001")
    assert p1_checks.back_locator(graph, "urn:lattice-v-rig:v1:p1/instrument/prim-001") == graph.value(document, VRIG.locator)
    node = next(graph.subjects(RDF.type, VRIG.BodyNode))
    from urllib.parse import quote
    assert p1_checks.back_locator(graph, "urn:lattice-v-rig:v1:p1/element/" + quote(str(graph.value(node, VRIG.locator)), safe="")) == graph.value(node, VRIG.locator)
    assert p1_checks.back_locator(graph, "urn:lattice-v-rig:v1:p1/actor/Nobody") is None


def test_competency_files_parse_into_questions():
    files = p1_checks.competency_files()
    assert {p.stem for p in files} == {"foundation", "instrument", "party", "quantification", "ledger", "wording", "insurance-common"}
    for path in files:
        prologue, asked = p1_checks.questions(path)
        assert "PREFIX" in prologue and asked
        for name, question, query in asked:
            assert question.endswith("?") and query.startswith("SELECT"), (path.name, name)


def test_questions_with_no_answer_are_findings_and_answered_ones_are_not(graph, competency):
    assert competency.competency["instrument/parties"] == 4
    assert competency.competency["instrument/wording"] == 4
    assert competency.competency["party/shares"] == 4
    assert competency.competency["wording/typed"] > 0
    assert competency.competency["insurance-common/events"] == 2
    empty = {m.split(": ", 1)[0] + "/" for _, _, _, m, _ in competency.findings if False} or None
    names = {str(graph.value(locator, VRIG.keyPath)) for kind, locator, _, _, _ in competency.findings if kind == VRIG.EmptyQuery}
    assert {"limit", "attachment", "follows-form", "spaces", "units", "parts", "references", "perils", "instrument-period"} <= names
    assert not {"parties", "wording", "shares", "typed", "events", "amounts", "values"} & names


def test_an_empty_query_finding_is_located_at_the_file_that_asked(graph, competency):
    kinds = {kind for kind, *_ in competency.findings}
    assert kinds == {VRIG.EmptyQuery}
    for _, locator, _, message, _ in competency.findings:
        assert str(graph.value(locator, VRIG.documentId)).startswith("projection/competency/")
        assert str(graph.value(locator, VRIG.view)) == str(VRIG.Declared)


def test_consistency_is_checked_or_reported_unavailable(graph, layers, modules):
    result = p1_checks.ChecksResult()
    p1_checks.check_consistency(graph, layers, result, modules)
    kinds = {kind for kind, *_ in result.findings}
    try:
        from mork_compilers import reasoning
        available = reasoning.available()
    except ImportError:
        available = False
    if available:
        assert result.consistent is not None
        assert kinds <= {VRIG.Inconsistent}
        assert (result.consistent is False) == (VRIG.Inconsistent in kinds)
    else:
        assert kinds == {VRIG.ReasonerUnavailable}


def test_without_a_reasoner_the_check_is_a_finding(graph, layers, modules, monkeypatch):
    reasoning = pytest.importorskip("mork_compilers.reasoning")
    monkeypatch.setattr(reasoning, "available", lambda: False)
    result = p1_checks.ChecksResult()
    p1_checks.check_consistency(graph, layers, result, modules)
    assert [kind for kind, *_ in result.findings] == [VRIG.ReasonerUnavailable]
    assert result.consistent is None


def test_checks_are_byte_stable(graph, layers, modules):
    first, second = p1_checks.ChecksResult(), p1_checks.ChecksResult()
    for result in (first, second):
        p1_checks.validate_layers(graph, layers, result, modules)
        p1_checks.ask_competency(graph, layers, result)
    assert [tuple(map(str, f)) for f in first.findings] == [tuple(map(str, f)) for f in second.findings]
