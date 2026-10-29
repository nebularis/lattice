# SPDX-License-Identifier: MPL-2.0
"""The mapping proposal tools: cards are deterministic and read only a layer's own terms, ranking puts the matching
relation first for ODRL's rule kinds, and the check turns every failure into a finding."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml
from rdflib import Graph

from mork_propose.cards import codebook_card, layer_card, render, source_card
from mork_propose.rank import candidates, words
from mork_propose.server import check_mapping, target_cards, teaching_pack

ROOT = Path(__file__).resolve().parents[3]
ODRL = ROOT / "contracts" / "config-studio" / "odrl" / "odrl22.ttl"
DEONTIC = ("instrument", "eligibility", "party", "behaviour")


@pytest.fixture(scope="module")
def odrl():
    return source_card(Graph().parse(ODRL), ["http://www.w3.org/ns/odrl/2/"])


@pytest.fixture(scope="module")
def target():
    return [c for m in DEONTIC for c in layer_card(m)]


def test_a_card_is_the_same_each_time_and_holds_only_the_layers_own_terms():
    first = render("instrument", layer_card("instrument"))
    assert first == render("instrument", layer_card("instrument"))
    assert all(line.startswith(("#", "ins:")) for line in first.splitlines())


@pytest.mark.parametrize("source, expected", [("odrl:Permission", "ins:Permission"), ("odrl:Prohibition", "ins:Prohibition"), ("odrl:Duty", "ins:Obligation")])
def test_an_odrl_rule_kind_ranks_its_instrument_relation_first(odrl, target, source, expected):
    card = next(c for c in odrl if c.curie == source)
    assert candidates(card, target, 4)[0][0].curie == expected


def test_words_split_names_and_drop_plurals():
    assert words("hasCompositionRules of_the Parties") == ["has", "composition", "rule", "partie"]
    assert words("assigneeParty") == ["assignee", "party"]


def test_the_pack_holds_mtp_and_the_codebook():
    pack = teaching_pack()
    assert "MORK Teaching Pack L0" in pack and "# MCN codebook" in pack and "cassette C-LOAN" in pack
    assert "xt | mork:exactTBoxMatch" in codebook_card()


def test_the_check_reports_a_proposal_that_does_not_decode_or_names_no_scheme():
    bad = json.loads(check_mapping("this is not mcn"))
    assert not bad["decoded"] and bad["findings"][0]["stage"] == "decode"
    cassette = yaml.safe_load((ROOT / "ontology" / "mork" / "mtp" / "data" / "cassettes" / "C-LOAN.yaml").read_text())["mcn"]
    loan = json.loads(check_mapping(cassette))
    assert loan["decoded"] and loan["errors"] == 0, "a JSON source is left to its backend, not refused"


def test_an_unknown_layer_is_refused():
    with pytest.raises(ValueError):
        target_cards(["instrument", "nowhere"])


# ---- the history of proposals and reviews ----------------------------------------------------------------------------

from datetime import datetime, timezone

from rdflib import URIRef

from mork_propose.history import History, agreement, patterns, review_against, scores

AT = datetime(2026, 10, 29, tzinfo=timezone.utc)
PACK = ROOT / "contracts" / "config-studio" / "odrl" / "odrl-instrument.mork.ttl"
SCHEME = URIRef("https://www.nebularis.org/neuro-semantic/lattice/config-studio/odrl-mapping#Scheme")


def test_the_pack_reviewed_against_itself_is_accepted_whole():
    g = Graph().parse(PACK)
    assert scores(review_against(g, SCHEME, g, SCHEME, AT))["accepted_share"] == 1.0


def test_a_review_recorded_is_the_mapping_s_latest_decision_and_a_lesson(tmp_path):
    history = History(tmp_path / "history.ttl")
    g = Graph().parse(PACK)
    run = URIRef("urn:x:run/1")
    mappings = history.record_run(run, g, SCHEME, model="a model", pack="MTP 0", source=None, at=AT)
    history.record_review(URIRef("urn:x:review/1"), mappings[0], "rejected", reviewer=URIRef("urn:x:me"), at=AT, note="wrong")
    history.record_review(URIRef("urn:x:review/2"), mappings[0], "accepted", reviewer=URIRef("urn:x:me"), at=AT.replace(hour=1))
    history.save()
    again = History(tmp_path / "history.ttl")
    assert again.decisions()[mappings[0]][0] == URIRef("http://www.nebularis.org/ontologies/Mork#Accepted")
    assert len(again.lessons()) == 1


def test_a_run_s_patterns_do_not_depend_on_minted_names():
    from rdflib import Literal
    from rdflib.namespace import RDF
    a, b = Graph(), Graph()
    for g, base in ((a, "urn:one/"), (b, "urn:two/")):
        g.add((URIRef(base + "x"), RDF.type, URIRef("urn:t#Permission")))
        g.add((URIRef(base + "x"), URIRef("urn:t#activity"), URIRef("urn:o#use")))
    assert agreement(patterns(a, "urn:one/"), patterns(b, "urn:two/"))["recall"] == 1.0


# ---- the LangGraph pipeline meets the same check ----------------------------------------------------------------------

def test_the_pipeline_compiles_an_rdf_scheme_with_mork_rdf_and_refuses_what_the_check_refuses():
    import asyncio
    from mork_communities.pipeline import PipelineNodes

    nodes = PipelineNodes(None, None, None)
    state = {"mapping_turtle": PACK.read_text(), "iteration_count": 0, "session_id": "s", "provenance": []}
    compiled = asyncio.run(nodes.compile(state))
    assert [a["artefact_type"] for a in compiled["compiled_artefacts"]] == ["sparql"]
    cycle = """@prefix mork: <http://www.nebularis.org/ontologies/Mork#> . @prefix mm: <http://example.org/m#> .
        mm:S a mork:MappingScheme . mm:A mork:mappingScheme mm:S ; mork:precedes mm:B . mm:B mork:mappingScheme mm:S ; mork:precedes mm:A ."""
    validated = asyncio.run(nodes.validate({"mapping_turtle": cycle, "iteration_count": 0}))
    assert not validated["validation_passed"]
