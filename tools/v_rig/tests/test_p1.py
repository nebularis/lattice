# SPDX-License-Identifier: MPL-2.0
"""P1 on the mini-rig: the tracked scheme and the mini-rig's extension compiled and run by mork_rdf over the derived
mapping source, the layer graph they make, and the findings the run leaves. Every expected value is the mini-rig's own."""

from __future__ import annotations

import sys
from decimal import Decimal
from pathlib import Path

import pytest
from rdflib import RDF, Graph, Literal, Namespace, URIRef

from v_rig import lift, read_rig
from v_rig.lift import VRIG, RunInfo, canonical_turtle, key_iri, mapping_source
from v_rig import p1

HERE = Path(__file__).resolve().parent
MINI_RIG = HERE / "mini-rig"
EXTENSION = HERE / "mini-rig.extension.ttl"
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "tools"))

LATTICE = "https://www.nebularis.org/neuro-semantic/lattice/"
INS, WRD, PTY = Namespace(LATTICE + "instrument#"), Namespace(LATTICE + "wording#"), Namespace(LATTICE + "party#")
QNT, LDG, FND = Namespace(LATTICE + "quantification#"), Namespace(LATTICE + "ledger#"), Namespace(LATTICE + "foundation#")
ICM = Namespace(LATTICE + "insurance/common#")
EXT = Namespace("urn:example:v-rig:mini-rig-extension#")
RUN = RunInfo("0000000000000000000000000000000000000000", "0.0.0", "0.1.0", None)


@pytest.fixture(scope="module")
def graph():
    return lift(read_rig(MINI_RIG), RUN)


@pytest.fixture(scope="module")
def target():
    return p1.target_vocabulary()


@pytest.fixture(scope="module")
def projection(graph, target):
    return p1.project(graph, [EXTENSION], target=target)


def _of_type(g: Graph, cls) -> list[URIRef]:
    return list(g.subjects(RDF.type, cls))


# ---- the scheme compiles and declares --------------------------------------------------

def test_the_tracked_scheme_compiles_with_no_error(projection):
    errors = [f for f in projection.compile_findings if f.startswith("error")]
    assert errors == [], errors


def test_reading_keys_are_declared_by_the_scheme_and_typed_in_the_representation(graph, projection):
    assert projection.reading_keys == ("drop_down", "exhaustion")
    from v_rig.lift import mark_readings
    assert mark_readings(graph, projection.reading_keys) == 5
    readings = _of_type(graph, VRIG.Reading)
    assert {str(graph.value(r, VRIG.key)) for r in readings} == {"exhaustion", "drop_down"}
    for r in readings:
        assert isinstance(graph.value(r, VRIG.value), Literal)


# ---- the derived mapping source --------------------------------------------------------

def test_mapping_source_adds_one_edge_per_fact_and_keeps_the_representation(graph):
    source = mapping_source(graph)
    assert len(source) > len(graph)
    for triple in graph:
        assert triple in source
    doc = next(d for d in _of_type(graph, VRIG.Document) if str(graph.value(d, VRIG.rigId)) == "prim-001")
    assert source.value(doc, key_iri("limit")).toPython() == 1000000
    lines = source.value(doc, key_iri("lines"))
    assert [str(x) for x in source.items(lines)] == ["general-liability", "products"]
    event = next(e for e in _of_type(graph, VRIG.Event) if str(graph.value(e, VRIG.rigId)) == "ev-001")
    unknown = source.value(event, key_iri("prior_knowledge"))
    assert (unknown, VRIG.unknown, Literal(True)) in source, "an unknown fact's edge points at the fact itself"


# ---- what the layer graph holds ---------------------------------------------------------

def test_each_document_is_an_instrument_expressed_in_a_wording(projection):
    g = projection.layers
    instruments = _of_type(g, INS.Instrument)
    assert len(instruments) == 4
    for instrument in instruments:
        wording = g.value(instrument, INS.expressedIn)
        assert (wording, RDF.type, WRD.Wording) in g
        assert g.value(instrument, RDFS_LABEL) is not None


RDFS_LABEL = URIRef("http://www.w3.org/2000/01/rdf-schema#label")


def test_body_nodes_are_elements_in_a_tree_with_text_parts(graph, projection):
    g = projection.layers
    elements = _of_type(g, WRD.Element)
    assert len(elements) == len(_of_type(graph, VRIG.BodyNode))
    assert all(any(True for _ in g.subjects(WRD.directlyComprises, e)) for e in elements), "every element has a parent"
    texts = _of_type(g, WRD.Text)
    assert texts and all(g.value(t, WRD.hasTextPart) is not None for t in texts)
    types = {str(o).rsplit("#", 1)[-1] for o in g.objects(None, WRD.elementType)}
    assert {"Section", "Clause", "Definition", "Endorsement"} <= types


def test_layers_are_groups_each_for_its_own_share_party_to_their_instruments(projection):
    g = projection.layers
    groups = _of_type(g, PTY.ParticipationGroup)
    assert len(groups) == 3
    assert all(g.value(group, PTY.hasCompositionRule) == PTY.EachForOwnShare for group in groups)
    parties = list(g.subject_objects(INS.party))
    assert len(parties) == 4
    assert all((s, RDF.type, INS.Instrument) in g and (o, RDF.type, PTY.ParticipationGroup) in g for s, o in parties)
    assert {str(s).rsplit("/", 1)[-1] for s, _ in parties} == {"prim-001", "xs1-001", "xs2-001", "xs2-002"}
    memberships = _of_type(g, PTY.GroupMembership)
    assert sorted(Decimal(str(g.value(m, PTY.outwardShare))) for m in memberships) == [Decimal("0.4"), Decimal("0.6"), Decimal(1), Decimal(1)]
    roles = sorted(str(g.value(g.value(m, PTY.memberOccupancy), PTY.inRole)) for m in memberships)
    assert roles == [str(EXT.Follow), str(EXT.Lead), str(EXT.Sole), str(EXT.Sole)]
    actors = {str(g.value(a, RDFS_LABEL)) for a in _of_type(g, PTY.Actor)}
    assert actors == {"Invented Insurer One", "Invented Insurer Two", "Invented Insurer Three", "Invented Insurer Four"}


def test_tokens_reach_concepts_through_the_extension(projection):
    g = projection.layers
    assert set(g.objects(None, ICM.classOfBusiness)) == {EXT.GeneralLiability, EXT.Products}


def test_limits_are_account_definitions_and_attachments_quantities(projection):
    g = projection.layers
    accounts = _of_type(g, LDG.AccountDefinition)
    assert len(accounts) == 6, "four documents and three layers state a limit, one of them as a formula no account takes"
    amounts = sorted(g.value(g.value(a, LDG.statedAmount), QNT.numericValue).toPython() for a in accounts if isinstance(g.value(g.value(a, LDG.statedAmount), QNT.numericValue).toPython(), int))
    assert 1000000 in amounts and 3000000 in amounts


def test_a_fact_stated_as_not_known_is_an_unresolved_value(target):
    source = Graph().parse(data=f"""
        @prefix vrig: <{VRIG}> . @prefix ex: <urn:x:> .
        ex:d a vrig:Document ; vrig:rigId "d" .
        ex:f a vrig:Fact ; vrig:of ex:d ; vrig:key "attachment" ; vrig:unknown true ; vrig:locator ex:l .
        ex:l a vrig:Locator ; vrig:documentId "d" ; vrig:view vrig:Declared .
    """, format="turtle")
    out = p1.project(source, [], target=target)
    assert len(_of_type(out.layers, QNT.UnresolvedValue)) == 1
    assert _of_type(out.layers, QNT.Quantity) == []


def test_the_programme_period_is_a_temporal_scope_in_order(projection):
    g = projection.layers
    scopes = [s for s in _of_type(g, FND.TemporalScope) if g.value(s, FND.validTo) is not None]
    assert len(scopes) == 1
    assert str(g.value(scopes[0], FND.validFrom)) == "2027-01-01" and str(g.value(scopes[0], FND.validTo)) == "2027-12-31"


def test_the_extension_scheme_runs_after_the_tracked_one(projection):
    g = projection.layers
    events = _of_type(g, ICM.LossEvent)
    assert len(events) == 2
    dates = sorted(str(g.value(g.value(e, FND.hasTemporalScope), FND.validFrom)) for e in events)
    assert dates == ["2027-03-04", "2027-07-19"]


# ---- the findings ---------------------------------------------------------------------

def test_every_key_no_scheme_reads_is_a_finding_and_readings_are_not(projection):
    unmapped = {key for kind, _, key, _, _ in projection.findings if kind == VRIG.UnmappedKey}
    assert {"custom_note_key", "trigger", "governing_law", "loss_amount"} <= unmapped
    assert not {"limit", "lines", "share", "exhaustion", "drop_down"} & unmapped


def test_a_lookup_nothing_answers_is_an_uncertain_mapping_at_its_node(projection):
    uncertain = [(locator, message) for kind, locator, _, message, _ in projection.findings if kind == VRIG.UncertainMapping]
    assert uncertain and all(locator is not None for locator, _ in uncertain)
    assert all(message.startswith("LookupUnresolved") for _, message in uncertain), {m for _, m in uncertain}


def test_p1_is_byte_stable(graph, projection, target):
    again = p1.project(lift(read_rig(MINI_RIG), RUN), [EXTENSION], target=target)
    assert canonical_turtle(again.layers) == canonical_turtle(projection.layers)
    assert sorted(map(str, again.findings)) == sorted(map(str, projection.findings))
