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


def test_an_uncertain_mapping_in_a_proposal_waits_for_review_and_is_no_error():
    mcn = (ROOT / "ontology" / "mork" / "mtp" / "data" / "cassettes" / "C-UNCERTAIN.yaml")
    text = yaml.safe_load(mcn.read_text())["mcn"]
    checked = json.loads(check_mapping(text))
    reviews = [f for f in checked["findings"] if f["code"] == "Uncertain"]
    assert reviews and all(f["severity"] == "review" for f in reviews)


def test_a_target_term_the_target_vocabulary_does_not_declare_in_its_own_namespace_is_an_error():
    from mork_propose.check import unknown_targets

    vocabulary = Graph().parse(data="""@prefix ins: <https://example.org/ins#> . @prefix owl: <http://www.w3.org/2002/07/owl#> .
        ins:Obligation a owl:Class . ins:activity a owl:ObjectProperty .""", format="turtle")
    g = Graph().parse(data="""@prefix mork: <http://www.nebularis.org/ontologies/Mork#> . @prefix ins: <https://example.org/ins#> .
        @prefix ex: <https://example.org/m#> . @prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
        ex:a mork:exactTBoxMatch ins:Obligatio . ex:b mork:exactRBoxMatch ins:activity . ex:c mork:exactRBoxMatch rdf:type .
        ex:d mork:exactABoxMatch ex:Own .""", format="turtle")
    assert [(str(m), code) for _, _, code, m, _ in unknown_targets(g, vocabulary)] == [("https://example.org/m#a", "UnknownTarget")]


def test_a_card_gives_the_comment_or_the_utility_whichever_says_more_in_full():
    from mork_propose.cards import cards

    g = Graph().parse(data="""@prefix owl: <http://www.w3.org/2002/07/owl#> . @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
        @prefix fnd: <https://www.nebularis.org/neuro-semantic/lattice/foundation#> . @prefix ex: <https://example.org/x#> .
        ex:A a owl:Class ; rdfs:comment "Short." ; fnd:utility "Subject: a permission. Excepts exactly one prohibition | whose obligor is its holder (law I8)." .
        ex:B a owl:Class ; rdfs:comment "What B is, said at length. And a second sentence the old cards cut." ; fnd:utility "Use B." .""", format="turtle")
    by = {c.curie.rsplit(":", 1)[-1]: c.definition for c in cards(g, ["https://example.org/x#"])}
    assert by == {"A": "Subject: a permission. Excepts exactly one prohibition / whose obligor is its holder (law I8).",
                  "B": "What B is, said at length. And a second sentence the old cards cut."}


def test_describe_term_gives_a_term_s_utility_and_the_laws_its_shapes_state():
    from mork_propose.server import describe_term

    permission = describe_term("ins:Permission")
    assert "utility: Subject: a permission. Excepts exactly one prohibition" in permission
    assert any("(law I8)" in line for line in permission.splitlines() if line.startswith("- "))
    role = describe_term("pty:Role")
    assert "individuals: pty:Accountable, pty:Guarantor, pty:Obligee, pty:Obligor, pty:Performing" in role
    assert "laws and shapes" not in role  # a shape about pty:RoleOccupancy is not about pty:Role
    with pytest.raises(ValueError):
        describe_term("ins:NoSuchTerm")


def test_the_check_holds_what_a_proposal_writes_on_a_sample_to_the_target_layers_laws():
    from mork_propose.server import check_mapping

    odrl = Path(__file__).resolve().parents[3] / "contracts" / "config-studio" / "odrl"
    sample = str(odrl / "trial" / "software-licence.ttl")
    run_1 = json.loads(check_mapping((odrl / "trial" / "run-1" / "proposal.mcn").read_text(encoding="utf-8"), sample))
    broken = {f["message"].split(" (on ")[0] for f in run_1["findings"] if f["code"] == "TargetShape" and f["severity"] == "error"}
    assert "A permission excepts exactly one prohibition." in broken  # law I8, which the trial's reviews corrected
    assert all(f["about"] for f in run_1["findings"] if f["stage"] == "meaning")  # each on the mapping that wrote it

    from mork_propose.check import check_graph
    from mork_propose.server import _target

    vocabulary, shapes = _target()
    pack = check_graph(Graph().parse(odrl / "odrl-instrument.mork.ttl"), sample=Graph().parse(sample), target_vocabulary=vocabulary, target_shapes=shapes)
    assert {f[2] for f in pack.findings if f[1] == "error"} == set()
    assert {f[2] for f in pack.findings if f[0] == "meaning"} == {"ContextShape"}


def test_a_run_records_what_it_cost(tmp_path):
    from datetime import datetime, timezone
    from rdflib import Literal, URIRef
    from rdflib.namespace import PROV, XSD

    from mork_propose.history import MORK, History

    history = History(tmp_path / "history.ttl")
    run = URIRef("urn:mork-propose:run:cost")
    at, started = datetime(2026, 10, 30, 12, tzinfo=timezone.utc), datetime(2026, 10, 30, 11, 55, tzinfo=timezone.utc)
    history.record_run(run, Graph(), URIRef("urn:x:s"), model="m", pack="p", source=None, at=at, started=started, total_tokens=150000)
    g = history.graph
    assert (run, PROV.startedAtTime, Literal(started.isoformat(), datatype=XSD.dateTime)) in g
    assert (run, MORK.totalTokens, Literal(150000, datatype=XSD.nonNegativeInteger)) in g
    assert g.value(run, MORK.inputTokens) is None


def test_every_term_of_the_translation_table_is_declared_by_a_layer():
    from mork_propose.server import LAYERS, describe_term
    from mork_propose.translations import table

    for entry in table():
        for reading in entry["means"]:
            assert describe_term(reading["term"]).startswith("# "), reading["term"]


def test_a_source_s_right_finds_each_relation_it_may_mean_through_the_translation_table():
    from mork_propose.server import candidate_terms, teaching_pack

    lrml = Path(__file__).resolve().parents[3] / "contracts" / "config-studio" / "legalruleml" / "trial" / "legalruleml-metamodel.ttl"
    found = {line.split(" | ")[1] for line in candidate_terms(str(lrml), "lrmlmm:Right", ["instrument", "eligibility", "party", "behaviour"], 6).splitlines()}
    assert {"ins:Permission", "ins:Power", "ins:Exclusion", "ins:Obligation"} <= found
    assert "right, entitlement | ins:Power | a right to terminate" in teaching_pack()


@pytest.mark.parametrize("cassette", ["C-STATED-OBLIGATION", "C-PERMISSION", "C-CONCEPT-CONDITION", "C-INTERVAL-CONDITION", "C-REMEDY-ON-BREACH"])
def test_a_target_side_cassette_runs_over_its_sample_and_keeps_the_target_layers_laws(cassette):
    import mcn_decoder
    from mork_propose.check import check_graph
    from mork_propose.server import _mtp, _target

    root = Path(__file__).resolve().parents[3]
    data = yaml.safe_load((_mtp() / "data" / "cassettes" / f"{cassette}.yaml").read_text(encoding="utf-8"))
    vocabulary, shapes = _target()
    checked = check_graph(mcn_decoder.decode(data["mcn"]), sample=Graph().parse(root / data["sample"]), target_vocabulary=vocabulary, target_shapes=shapes)
    assert checked.output is not None and len(checked.output) > 0
    assert [f for f in checked.findings if f[1] in ("error", "warning")] == []


def test_a_history_teaches_rules_grouped_by_what_was_corrected_the_most_frequent_first():
    from mork_propose.history import History
    from mork_propose.server import _target

    trial = Path(__file__).resolve().parents[3] / "contracts" / "config-studio"
    vocabulary = _target()[0]
    lrml = History(trial / "legalruleml" / "trial" / "history.ttl").rules(None, vocabulary)
    assert lrml[0].startswith("stated meaning names roles, never occupancies") and "6x" in lrml[0] and "[recurring" in lrml[0]
    odrl = History(trial / "odrl" / "trial" / "history.ttl").rules(Graph().parse(trial / "odrl" / "odrl-instrument.mork.ttl"), vocabulary)
    assert any(r.startswith("Instead of elg:ExactCondition, write elg:Condition. The proposal wrote a subclass") for r in odrl)


def test_the_communities_baseline_is_the_same_for_the_same_reviews_and_groups_a_source_s_parties_with_its_relations(tmp_path):
    from rdflib.compare import isomorphic
    from rdflib.namespace import RDF

    from mork_propose import baseline
    from mork_propose.history import MORK

    first, second = tmp_path / "a.ttl", tmp_path / "b.ttl"
    assert baseline.main(["--out", str(first)]) == 0 and baseline.main(["--out", str(second)]) == 0
    a, b = Graph().parse(first), Graph().parse(second)
    assert isomorphic(a, b)
    members = [{str(a.value(ms, MORK.memberConcept)) for ms in a.objects(c, MORK.hasCommunityMembership)}
               for c in a.subjects(RDF.type, MORK.SemanticCommunity)]
    lrml = "http://docs.oasis-open.org/legalruleml/ns/v1.0/metamodel#"
    assert any({lrml + "Bearer", lrml + "AuxiliaryParty", lrml + "Obligation"} <= m for m in members)
