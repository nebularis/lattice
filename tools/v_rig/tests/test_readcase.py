# SPDX-License-Identifier: MPL-2.0
"""The read-case seam on the mini-rig: a Turtle graph in the vocabulary from outside, validated, compared with the
declared view, its disagreements findings."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from rdflib import RDF, Graph, Literal, URIRef

from v_rig import lift, read_rig
from v_rig.lift import VRIG, RunInfo
from v_rig import p1, readcase, canon

HERE = Path(__file__).resolve().parent
MINI_RIG = HERE / "mini-rig"
READ_CASE = HERE / "read-case.ttl"
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "tools"))
RUN = RunInfo("0000000000000000000000000000000000000000", "0.0.0", "0.1.0", None)


@pytest.fixture(scope="module")
def graph():
    return lift(read_rig(MINI_RIG), RUN)


@pytest.fixture(scope="module")
def module_graphs():
    return readcase.module_graphs()


def test_a_conforming_read_case_loads(module_graphs):
    case = readcase.load(READ_CASE, module_graphs)
    assert len(list(case.subjects(RDF.type, VRIG.Fact))) == 5


def test_a_read_case_the_shapes_refuse_is_refused(module_graphs, tmp_path):
    bad = tmp_path / "bad.ttl"
    bad.write_text(READ_CASE.read_text().replace('vrig:key "trigger" ; vrig:value "occurrence" ;', 'vrig:key "trigger" ;'))
    with pytest.raises(readcase.ReadCaseError, match="does not conform"):
        readcase.load(bad, module_graphs)


def test_disagreements_on_a_value_and_on_a_state_and_nothing_else(graph, module_graphs):
    case = readcase.load(READ_CASE, module_graphs)
    found = readcase.compare(graph, case)
    assert sorted((str(graph.value(locator, VRIG.documentId)), key) for _, locator, key, _, _ in found) == [("prim-001", "attachment"), ("xs1-001", "exhaustion")]
    for kind, locator, key, message, about in found:
        assert kind == VRIG.Disagreement
        assert graph.value(locator, VRIG.view) == VRIG.Declared, "located at the declared fact"
        assert "differ" in message and "25000" not in message
        assert (about, RDF.type, VRIG.Fact) in case


def test_disagreements_become_findings_about_both_facts(graph, module_graphs):
    copy = Graph()
    copy += graph
    case = readcase.load(READ_CASE, module_graphs)
    found = readcase.compare(copy, case)
    readcase.add_read_case(copy, case)
    run = URIRef(canon.run_iri("x"))
    written = p1.add_findings(copy, run, found)
    assert written == 2
    for finding in copy.subjects(VRIG.findingKind, VRIG.Disagreement):
        assert len(list(copy.objects(finding, VRIG.about))) == 1
        about = copy.value(finding, VRIG.about)
        assert (about, RDF.type, VRIG.Fact) in copy
        assert str(finding).startswith("urn:lattice-v-rig:v1:finding:")


def test_the_comparison_is_the_same_whatever_wrote_the_case(graph, module_graphs):
    """The same facts under other identifiers give the same disagreements, since the comparison reads documents and keys."""
    text = READ_CASE.read_text().replace("urn:example:v-rig:read-case:", "urn:example:v-rig:another-reader:")
    other = Graph().parse(data=text, format="turtle")
    first = readcase.compare(graph, readcase.load(READ_CASE, module_graphs))
    second = readcase.compare(graph, other)
    assert [(str(l), k) for _, l, k, _, _ in first] == [(str(l), k) for _, l, k, _, _ in second]
