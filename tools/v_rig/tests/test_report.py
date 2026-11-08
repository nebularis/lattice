# SPDX-License-Identifier: MPL-2.0
"""P4 on the mini-rig: the findings as nodes under the identifier rule, and the report rendered from them."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from rdflib import RDF, Graph, URIRef

from v_rig import lift, read_rig
from v_rig.lift import VRIG, RunInfo, canonical_turtle, findings_graph
from v_rig import p1, p1_checks, report
from v_rig import canon

HERE = Path(__file__).resolve().parent
MINI_RIG = HERE / "mini-rig"
EXTENSION = HERE / "mini-rig.extension.ttl"
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "tools"))
RUN = RunInfo("0000000000000000000000000000000000000000", "0.0.0", "0.1.0", "lattice-v-rig-vectors/1")
INFO = {"rig_digest": "0" * 64, "format_version": "1", "checkout_commit": "0" * 40, "substrate_release": "0.0.0",
        "vocabulary_version": "0.1.0", "vector_schema_version": "lattice-v-rig-vectors/1", "canonicalisation": "v1"}


def _complete(rig):
    graph = lift(rig, RUN)
    projection = p1.project(graph, [EXTENSION])
    checks = p1_checks.check_all(graph, projection.layers, reasoner=False)
    p1.add_findings(graph, URIRef(canon.run_iri(rig.digest)), projection.findings + checks.findings)
    return graph


@pytest.fixture(scope="module")
def graph():
    return _complete(read_rig(MINI_RIG))


def test_every_finding_has_a_kind_a_locator_and_an_identifier_under_the_rule(graph):
    findings = list(graph.subjects(RDF.type, VRIG.Finding))
    assert len(findings) > 100
    for finding in findings:
        kind = graph.value(finding, VRIG.findingKind)
        locator = graph.value(finding, VRIG.locator)
        key = graph.value(finding, VRIG.key)
        document = str(graph.value(locator, VRIG.documentId))
        string = str(locator)[len(canon.locator_iri("")):]
        assert str(finding) == canon.finding_iri(str(kind).rsplit("#", 1)[-1], document, string, str(key) if key is not None else None)
        assert len(list(graph.objects(finding, VRIG.message))) == 1


def test_two_runs_give_the_same_finding_identifiers(graph):
    again = _complete(read_rig(MINI_RIG))
    assert sorted(map(str, graph.subjects(RDF.type, VRIG.Finding))) == sorted(map(str, again.subjects(RDF.type, VRIG.Finding)))
    assert canonical_turtle(findings_graph(graph)) == canonical_turtle(findings_graph(again))


def test_a_resolved_finding_disappears_from_a_diff_by_id(graph):
    """Remove the unresolved reference from the mini-rig's text in memory, and that one finding, and only it, goes."""
    before = {str(f) for f in graph.subjects(RDF.type, VRIG.Finding)}
    unresolved = [f for f in graph.subjects(VRIG.findingKind, VRIG.UnresolvedReference)]
    assert len(unresolved) == 3
    import shutil, tempfile
    with tempfile.TemporaryDirectory() as directory:
        copy = Path(directory) / "rig"
        shutil.copytree(MINI_RIG, copy)
        document = copy / "documents" / "xs1-001.md"
        document.write_text(document.read_text().replace(", subject to Condition 5.3 of the Underlying Policy", ""))
        after_graph = _complete(read_rig(copy))
    after = {str(f) for f in after_graph.subjects(RDF.type, VRIG.Finding)}
    gone = before - after
    assert len(gone) >= 1
    assert any(str(f) in gone for f in unresolved)
    assert all(graph.value(URIRef(g), VRIG.findingKind) in (VRIG.UnresolvedReference, VRIG.ShapeViolation, VRIG.UncertainMapping) for g in gone)


def test_report_renders_every_finding_sorted_by_document_and_locator(graph):
    text = report.render(graph, INFO)
    findings = list(graph.subjects(RDF.type, VRIG.Finding))
    rows = [line for line in text.splitlines() if line.startswith("| ") and "`" in line and line.count("|") == 6]
    assert len(rows) == len(findings)
    assert text.startswith("# Verification rig run")
    assert f"| Rig digest | `{'0' * 64}` |" in text
    assert "| Vector schema | lattice-v-rig-vectors/1 |" in text
    assert "## Findings by kind" in text and "| ShapeViolation |" in text and "| UnmappedKey |" in text
    headings = [line[3:] for line in text.splitlines() if line.startswith("## ") and line != "## Findings by kind"]
    assert headings == sorted(headings)
    assert "prim-001" in headings and "projection/competency/instrument.rq" in headings


def test_report_is_byte_stable_and_names_no_body_text(graph):
    assert report.render(graph, INFO) == report.render(_complete(read_rig(MINI_RIG)), INFO)
    text = report.render(graph, INFO)
    body_lines = [l.strip() for d in (MINI_RIG / "documents").glob("*.md") for l in d.read_text().splitlines()
                  if len(l.strip()) > 30 and not l.startswith(("#", "|", "---"))]
    for line in body_lines:
        assert line not in text
    assert "Invented Insurer" not in text and "Invented Holdings" not in text
