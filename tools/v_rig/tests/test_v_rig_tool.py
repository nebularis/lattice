# SPDX-License-Identifier: MPL-2.0
"""The lifter on the synthetic mini-rig. Every expected value here is the mini-rig's own, written from generic premises,
and no other rig is named anywhere in the repository."""

from __future__ import annotations

import logging
import shutil
import sys
from pathlib import Path

import pytest
from pyshacl import validate
from rdflib import RDF, Graph, Literal, URIRef

from v_rig import OutError, RigError, lift, read_rig, resolve_out, write_outputs
from v_rig import canon
from v_rig.lift import VRIG, RunInfo, blind
from v_rig.out import deny_terms

HERE = Path(__file__).resolve().parent
MINI_RIG = HERE / "mini-rig"
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "tools"))

import lattice_repo_catalogue as reader  # noqa: E402

RUN = RunInfo("0000000000000000000000000000000000000000", "0.0.0", "0.1.0", None)


@pytest.fixture(scope="module")
def rig():
    return read_rig(MINI_RIG)


@pytest.fixture(scope="module")
def graph(rig):
    return lift(rig, RUN)


def _facts(graph: Graph, carrier_id: str | None = None, key: str | None = None) -> list[URIRef]:
    found = []
    for fact in graph.subjects(RDF.type, VRIG.Fact):
        if key is not None and str(graph.value(fact, VRIG.key)) != key:
            continue
        if carrier_id is not None and str(graph.value(graph.value(fact, VRIG.of), VRIG.rigId)) != carrier_id:
            continue
        found.append(fact)
    return found


def _module_graphs() -> tuple[Graph, Graph]:
    module = reader.load(ROOT).module("v-rig")
    spec, shapes = Graph(), Graph()
    for path in module.files("spec") + module.files("vocab"):
        spec.parse(path, format="turtle")
    for path in module.files("shapes"):
        shapes.parse(path, format="turtle")
    return spec, shapes


# ---- the three fact states --------------------------------------------------------

def test_fact_stated_with_a_value(graph):
    (fact,) = _facts(graph, "ev-001", "loss_amount")
    assert graph.value(fact, VRIG.value).toPython() == 2500000
    assert graph.value(fact, VRIG.unknown) is None and graph.value(fact, VRIG.empty) is None


def test_fact_stated_as_not_known(graph):
    (fact,) = _facts(graph, "ev-001", "prior_knowledge")
    assert graph.value(fact, VRIG.unknown).toPython() is True
    assert graph.value(fact, VRIG.value) is None


def test_fact_not_stated_is_absent(graph):
    assert _facts(graph, "ev-001", "exhaustion_of_underlying") == []
    # The same key on the other event is stated and negative, a third thing again.
    (fact,) = _facts(graph, "ev-002", "prior_knowledge")
    assert graph.value(fact, VRIG.value).toPython() is False


def test_null_value_is_the_empty_marker(graph):
    records = [f for f in _facts(graph, "prog-001", "related_documents")]
    assert len(records) == 1
    (item,) = graph.objects(records[0], VRIG.item)
    target = [f for f in graph.subjects(VRIG.of, item) if str(graph.value(f, VRIG.key)) == "target"]
    assert len(target) == 1 and graph.value(target[0], VRIG.empty).toPython() is True


# ---- the two views ----------------------------------------------------------------

def test_front_matter_facts_are_declared_and_body_nodes_blind(graph):
    for fact in _facts(graph, "prim-001"):
        assert graph.value(graph.value(fact, VRIG.locator), VRIG.view) == VRIG.Declared
    views = {graph.value(graph.value(n, VRIG.locator), VRIG.view) for n in graph.subjects(RDF.type, VRIG.BodyNode)}
    assert VRIG.Blind in views and VRIG.Declared not in views


def test_rendering_is_its_own_view(graph):
    rendering = [v for v in graph.subjects(RDF.type, VRIG.RenderingView)]
    assert len(rendering) == 1 and str(graph.value(rendering[0], VRIG.renderingName)) == "prim-001-ocr"
    nodes = [n for n in graph.subjects(RDF.type, VRIG.BodyNode)
             if graph.value(graph.value(n, VRIG.locator), VRIG.view) == rendering[0]]
    assert nodes, "the rendering lifted to no body node"
    clause = [n for n in nodes if str(graph.value(n, VRIG.kind)) == "clause" and str(graph.value(n, VRIG.number)) == "1.1"]
    assert len(clause) == 1


def test_blind_view_has_no_facts_and_documents_reduced_to_id(graph):
    view = blind(graph)
    assert list(view.subjects(RDF.type, VRIG.Fact)) == []
    assert list(view.subjects(RDF.type, VRIG.Programme)) == []
    for document in view.subjects(RDF.type, VRIG.Document):
        assert view.value(document, VRIG.rigId) is not None
        assert view.value(document, VRIG.formatVersion) is None
    assert len(list(view.subjects(RDF.type, VRIG.BodyNode))) == len(list(graph.subjects(RDF.type, VRIG.BodyNode)))


# ---- what the lifter carries ------------------------------------------------------

def test_every_key_is_a_fact_including_unknown_ones(graph):
    keys = {str(graph.value(f, VRIG.key)) for f in _facts(graph, "prim-001")}
    assert {"limit", "lines", "exhaustion", "custom_note_key", "retroactive_date"} <= keys
    assert "id" not in keys


def test_provenance_is_dropped_at_the_gate(graph):
    assert _facts(graph, key="provenance") == []
    assert "provenance" not in graph.serialize(format="turtle")
    assert "test author" not in graph.serialize(format="turtle")


def test_list_key_is_one_fact_with_one_ordered_list(graph):
    (fact,) = _facts(graph, "prim-001", "lines")
    (head,) = graph.objects(fact, VRIG.value)
    assert [str(item) for item in graph.items(head)] == ["general-liability", "products"]
    assert isinstance(head, URIRef), "list cells are IRIs, so the output has no blank node"


def test_structured_values_are_records_with_facts(graph):
    layers = sorted(graph.subjects(RDF.type, VRIG.Layer), key=lambda l: int(graph.value(l, VRIG.layerNumber)))
    assert [int(graph.value(l, VRIG.layerNumber)) for l in layers] == [1, 2, 3]
    placements = [p for p in graph.subjects(RDF.type, VRIG.Placement) if graph.value(p, VRIG.onLayer) == layers[2]]
    assert len(placements) == 2
    shares = sorted(graph.value(f, VRIG.value).toPython() for p in placements for f in graph.subjects(VRIG.of, p)
                    if str(graph.value(f, VRIG.key)) == "share")
    assert [str(s) for s in shares] == ["0.4", "0.6"]


def test_formula_kept_as_written_with_its_inputs(graph):
    (fact,) = _facts(graph, "xs2-001", "limit")
    assert (fact, RDF.type, VRIG.Formula) in graph
    assert str(graph.value(fact, VRIG.expression)) == "0.6 x layer_limit"
    assert {str(i) for i in graph.objects(fact, VRIG.input)} == {"layer_limit"}
    (plain,) = _facts(graph, "prim-001", "limit")
    assert (plain, RDF.type, VRIG.Formula) not in graph


def test_id_valued_facts_resolve(graph):
    (fact,) = _facts(graph, "xs1-001", "follows_form_of")
    (target,) = graph.objects(fact, VRIG.resolvesTo)
    assert str(graph.value(target, VRIG.rigId)) == "prim-001"
    (programme_fact,) = _facts(graph, "ev-001", "programme")
    assert (programme_fact, RDF.type, VRIG.Fact) in graph
    assert any(str(graph.value(t, VRIG.rigId)) == "prog-001" for t in graph.objects(programme_fact, VRIG.resolvesTo))


def test_references_resolved_and_unresolved(graph):
    refs = {str(graph.value(r, VRIG.referenceText)): r for r in graph.subjects(RDF.type, VRIG.Reference)
            if graph.value(graph.value(r, VRIG.locator), VRIG.view) == VRIG.Blind}
    internal = refs["Section 3"]
    assert graph.value(internal, VRIG.external).toPython() is False
    assert str(graph.value(graph.value(internal, VRIG.resolvesTo), VRIG.kind)) == "section"
    external = refs["Section 4 of the Primary Policy"]
    assert graph.value(external, VRIG.external).toPython() is True
    assert graph.value(external, VRIG.resolvesTo) is not None
    unresolved = refs["Condition 5.3 of the Underlying Policy"]
    assert graph.value(unresolved, VRIG.resolvesTo) is None
    findings = [f for f in graph.subjects(RDF.type, VRIG.Finding) if (f, VRIG.about, unresolved) in graph]
    assert len(findings) == 1 and graph.value(findings[0], VRIG.findingKind) == VRIG.UnresolvedReference


def test_definitions_and_prose_only(graph):
    terms = {str(graph.value(d, VRIG["term"])) for d in graph.subjects(RDF.type, VRIG.DefinedTerm)}
    assert {"Insured", "Occurrence", "Policy Period"} <= terms
    prose = list(graph.subjects(RDF.type, VRIG.ProseOnly))
    assert prose
    for node in prose:
        assert str(graph.value(node, VRIG.kind)) == "paragraph"
    assert any(graph.value(f, VRIG.findingKind) == VRIG.ProseOnlyMeaning for f in graph.subjects(RDF.type, VRIG.Finding))


def test_every_node_located_and_digested(graph):
    for node in graph.subjects(RDF.type, VRIG.BodyNode):
        assert graph.value(node, VRIG.locator) is not None
        assert len(str(graph.value(node, VRIG.digest))) == 64
    for document in graph.subjects(RDF.type, VRIG.Document):
        assert str(graph.value(document, VRIG.digest)) == canon.sha256_hex(
            canon.normalise_file((MINI_RIG / "documents" / f"{graph.value(document, VRIG.rigId)}.md").read_text()))


# ---- conformance, stability and hygiene -------------------------------------------

def test_representation_conforms_to_the_module_shapes(graph):
    spec, shapes = _module_graphs()
    conforms, report, text = validate(graph + spec, shacl_graph=shapes, inference="rdfs", advanced=True)
    assert conforms, text


def test_outputs_are_byte_stable(rig, graph, tmp_path):
    again = lift(read_rig(MINI_RIG), RUN)
    from v_rig.lift import canonical_turtle
    assert canonical_turtle(graph) == canonical_turtle(again)
    ids = sorted(str(f) for f in graph.subjects(RDF.type, VRIG.Finding))
    assert ids == sorted(str(f) for f in again.subjects(RDF.type, VRIG.Finding))


def test_rig_files_unchanged_after_a_run(rig, tmp_path):
    before = {p: p.read_bytes() for p in MINI_RIG.rglob("*") if p.is_file()}
    out = ROOT / ".local" / "v-rig" / "test-run"
    write_outputs(rig, lift(rig, RUN), resolve_out(rig, out, ROOT), {"test": True})
    shutil.rmtree(out)
    assert {p: p.read_bytes() for p in MINI_RIG.rglob("*") if p.is_file()} == before


def test_no_rig_text_in_any_log_line(caplog):
    with caplog.at_level(logging.INFO, logger="v_rig"):
        lift(read_rig(MINI_RIG), RUN)
    body_lines = [l.strip() for d in (MINI_RIG / "documents").glob("*.md") for l in d.read_text().splitlines()
                  if len(l.strip()) > 30 and not l.startswith(("#", "|", "---"))]
    assert body_lines
    for record in caplog.records:
        for line in body_lines:
            assert line not in record.getMessage()
        assert "Invented" not in record.getMessage()


def test_deny_list_covers_ids_titles_and_body_text(graph):
    terms = deny_terms(graph)
    import re
    assert any(re.fullmatch(t, "prim-001") for t in terms)
    assert any(re.fullmatch(t, "Primary Liability Policy") for t in terms)
    assert any(re.fullmatch(t, "The Insurer will pay on behalf of the Insured those sums the Insured becomes legally obligated to pay as damages because of bodily injury or property damage to which this policy applies, subject to Section 3 and to the Limit of Liability in Item 3.") for t in terms)


# ---- refusals -------------------------------------------------------------------

def test_unsupported_format_version_refused(tmp_path):
    copy = tmp_path / "rig"
    shutil.copytree(MINI_RIG, copy)
    manifest = copy / "manifest.yaml"
    manifest.write_text(manifest.read_text().replace("format_version: 1", "format_version: 2"))
    with pytest.raises(RigError, match="format_version is 2"):
        read_rig(copy)
    manifest.write_text("\n".join(l for l in manifest.read_text().splitlines() if "format_version" not in l))
    with pytest.raises(RigError, match="no format_version key"):
        read_rig(copy)


def test_output_under_the_rig_refused(rig):
    with pytest.raises(OutError, match="inside the rig"):
        resolve_out(rig, MINI_RIG / "out", ROOT)


def test_output_not_ignored_refused(rig, tmp_path):
    with pytest.raises(OutError, match="not a path git ignores"):
        resolve_out(rig, tmp_path / "out", ROOT)
    with pytest.raises(OutError, match="not a path git ignores"):
        resolve_out(rig, ROOT / "tools" / "v_rig" / "out", ROOT)


def test_default_output_is_under_local(rig):
    out = resolve_out(rig, None, ROOT)
    assert out == (ROOT / ".local" / "v-rig" / rig.digest).resolve()


# ---- canonicalisation rules ---------------------------------------------------------

def test_tuple_encoding_matches_the_minting_specification():
    assert canon.tuple_encode(["v1", "person-email-unique", "acme", "ada@example.org"]) == \
        b"2:v119:person-email-unique4:acme15:ada@example.org"


def test_locator_string_and_identifiers():
    s = canon.locator_string("doc a", "blind", section="1", clause="1.1", row="0.ref1")
    assert s == "doc%20a@blind/section=1/clause=1.1/row=0.ref1"
    assert canon.node_iri(s).startswith("urn:lattice-v-rig:v1:node:doc%20a@blind/")
    assert canon.finding_iri("UnresolvedReference", "doc a", s, None) == \
        canon.finding_iri("UnresolvedReference", "doc a", s, "")
    assert canon.finding_iri("UnresolvedReference", "doc a", s, None) != canon.finding_iri("ProseOnlyMeaning", "doc a", s, None)
