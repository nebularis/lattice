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
