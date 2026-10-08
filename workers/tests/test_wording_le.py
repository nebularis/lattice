"""Tests the Logical English reading of the Wording layer (ADR-A118, plan WA6).

Covers S6-01 to S6-13 of docs/developer/plans/word-authoring-poc.md section "WA6".
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pytest
import rdflib
from jsonschema import Draft202012Validator
from rdflib.compare import isomorphic
from referencing import Registry, Resource

from lattice_workers.wording_le import analyse, classify, forms, matcher, model, offsets, proposal, tokens
from lattice_workers.wording_le.model import Element

REPO = Path(__file__).resolve().parents[2]
WORDING_FIXTURES = REPO / "contracts" / "authoring" / "fixtures" / "wording"
GOLDENS = Path(__file__).resolve().parent / "fixtures" / "wording_le"
CONTRACTS = REPO / "contracts"
VOCAB = REPO / "platform" / "authoring-service" / "src" / "main" / "resources" / "vocab" / "wording-provisional.ttl"

BASE = "https://example.org/lattice/authoring/"
SAMPLES = {
    "facility-agreement": "00000001-0000-4000-8000-000000000000",
    "software-licence": "00000002-0000-4000-8000-000000000000",
    "property-policy": "00000003-0000-4000-8000-000000000000",
}


def _load_sample(sample_id: str) -> model.Wording:
    graph = rdflib.Graph()
    graph.parse(WORDING_FIXTURES / f"{sample_id}.nt", format="nt")
    wording_iri = f"{BASE}doc/{SAMPLES[sample_id]}/wording"
    return model.load_wording(graph, wording_iri)


def _facility_element(object_id: str) -> model.Element:
    wording = _load_sample("facility-agreement")
    for element in wording.elements:
        if element.object_id == object_id:
            return element
    raise AssertionError(f"no facility element with objectId {object_id}")


def _full_analysis(wording: model.Wording, profile: forms.FormProfile) -> dict[str, Any]:
    result = analyse.analyse_wording(wording, profile)
    proposal_graph_iri = f"{wording.iri[: -len('wording')]}rev/1/proposal-graph"
    graph = proposal.proposal_graph(wording, result["elements"], proposal_graph_iri, profile)
    return {**result, "graphView": proposal.graph_view(wording, graph)}


# S6-01 ------------------------------------------------------------------------------------------


def test_utf16_offsets():
    assert offsets.utf16_len("abc") == 3
    assert offsets.utf16_len("\U0001d465a") == 3  # the astral MATHEMATICAL ITALIC SMALL X counts 2
    assert offsets.utf16_index("\U0001d465a", 1) == 2


# S6-02 --------------------------------------------------------------------------------------------


def test_tokenise_facility_element_06():
    element = _facility_element("2.1")
    found = tokens.tokenise(element)

    kinds = [token.kind for token in found]
    assert "constant" in kinds
    assert "word" in kinds
    assert "variable" in kinds

    for token in found:
        assert element.text[token.start : token.end] == token.text

    # the opening/closing quotes around no term here, and the final full stop, give no token
    assert all(token.text not in ('"', "\u201c", "\u201d", ".") for token in found)


def test_tokenise_gives_a_punct_token_for_a_comma():
    element = Element("e1", "urn:e1", "9.1", "body", "clause", None, (
        model.Part(0, "literal", "first, second and third."),
    ))
    found = tokens.tokenise(element)
    comma = [token for token in found if token.text == ","]
    assert len(comma) == 1
    assert comma[0].kind == "punct"


# S6-03 --------------------------------------------------------------------------------------------

_TERM_KINDS = {"Obligation", "Prohibition", "Permission", "Exclusion", "Power", "Definition", "Deeming"}
_PLACEHOLDER = re.compile(r"\*an?\s+(\w+)\*")


def test_profile_is_internally_consistent():
    profile = forms.load_profile()

    form_ids = [form.form_id for form in profile.forms]
    assert len(form_ids) == len(set(form_ids))
    assert all(form.relation_class in _TERM_KINDS for form in profile.forms)

    for form in profile.forms:
        slot_names = [item.name for item in form.items if isinstance(item, forms.Slot)]
        template_names = _PLACEHOLDER.findall(form.template)
        assert slot_names == template_names, form.form_id


def test_every_form_matches_at_least_one_sample_element():
    profile = forms.load_profile()
    used_form_ids: set[str] = set()
    for sample_id in SAMPLES:
        wording = _load_sample(sample_id)
        analysis = analyse.analyse_wording(wording, profile)
        used_form_ids.update(ea["formId"] for ea in analysis["elements"] if ea.get("formId"))
    assert used_form_ids == {form.form_id for form in profile.forms}


# S6-04 --------------------------------------------------------------------------------------------


def test_best_match_prefers_prohibition_over_obligation():
    element = Element("e1", "urn:e1", "9.1", "body", "clause", None, (
        model.Part(0, "reference", "Borrower", target_element_id="def-1"),
        model.Part(1, "literal", " shall not create any security over its assets."),
    ))
    profile = forms.load_profile()
    found = matcher.best_match(tokens.tokenise(element), profile, element, {})
    assert found is not None
    assert found.form.form_id == "prohibition"


def test_best_match_tiebreak_prefers_most_fixed_words_not_earliest_form():
    # Two synthetic forms sharing a trigger word, ordered so "most fixed words" and "earliest in
    # the profile" disagree: the form with fewer fixed words is listed first. Real profile forms
    # happen to never exercise this (see the Validation Pack's "Self-probe"), so this isolates the
    # tie-break rule itself from the profile's own incidental ordering.
    few_fixed = forms.Form("few", "Permission", "t1", (
        forms.Slot("party", "party", None), forms.Fixed(("may",)), forms.Slot("activity", "text", None),
    ))
    many_fixed = forms.Form("many", "Power", "t2", (
        forms.Slot("party", "party", None), forms.Fixed(("may", "terminate")), forms.Slot("activity", "text", None),
    ))
    tiny_profile = forms.FormProfile("test", "0.0.0", (), (few_fixed, many_fixed))

    element = Element("e1", "urn:e1", "9.1", "body", "clause", None, (
        model.Part(0, "reference", "Borrower", target_element_id="def-1"),
        model.Part(1, "literal", " may terminate this agreement."),
    ))
    found = matcher.best_match(tokens.tokenise(element), tiny_profile, element, {})
    assert found is not None
    assert found.form.form_id == "many"


# S6-05 --------------------------------------------------------------------------------------------


def test_matching_negative_cases():
    profile = forms.load_profile()

    # a party slot over a literal (not a reference) never matches
    literal_party = Element("e1", "urn:e1", "9.1", "body", "clause", None, (
        model.Part(0, "literal", "Someone shall pay."),
    ))
    form = next(f for f in profile.forms if f.form_id == "obligation")
    assert matcher.match(tokens.tokenise(literal_party), form, profile.ignorable, literal_party, {}) is None

    # a text slot left with zero tokens never matches
    no_activity = Element("e2", "urn:e2", "9.2", "body", "clause", None, (
        model.Part(0, "reference", "Borrower", target_element_id="def-1"),
        model.Part(1, "literal", " shall"),
    ))
    assert matcher.match(tokens.tokenise(no_activity), form, profile.ignorable, no_activity, {}) is None

    # a rate slot (percentage) over a duration variable never matches
    wrong_type = Element("e3", "urn:e3", "9.3", "body", "clause", None, (
        model.Part(0, "reference", "Borrower", target_element_id="def-1"),
        model.Part(1, "literal", " shall pay interest on the Loan at "),
        model.Part(2, "variable", "30 days", variable_key="term"),
        model.Part(3, "literal", " per annum."),
    ))
    rate_form = next(f for f in profile.forms if f.form_id == "pay-interest-at-rate")
    variable_types = {"term": "duration"}
    assert matcher.match(tokens.tokenise(wrong_type), rate_form, profile.ignorable, wrong_type, variable_types) is None


# S6-06 --------------------------------------------------------------------------------------------

_KEYWORD_CASES = [
    ("A thing shall be deemed done.", "clause", "Deeming"),
    ("A thing is deemed done.", "clause", "Deeming"),
    ("This policy does not cover fire.", "clause", "Exclusion"),
    ("Insurer is not liable for loss.", "clause", "Exclusion"),
    ("Cover excluded for war.", "clause", "Exclusion"),
    ("Borrower shall not act.", "clause", "Prohibition"),
    ("Lender may terminate this agreement.", "clause", "Power"),
    ("Borrower shall pay.", "clause", "Obligation"),
    ("Borrower may assign.", "clause", "Permission"),
]


@pytest.mark.parametrize("text,element_kind,expected", _KEYWORD_CASES)
def test_keyword_rules(text, element_kind, expected):
    element = Element("e1", "urn:e1", "9.1", "body", element_kind, None, (model.Part(0, "literal", text),))
    assert classify.keyword_class(tokens.tokenise(element), element_kind) == expected


def test_keyword_rules_competing_words_pick_the_earlier_rule():
    # "shall be deemed" (rule 2) must win over "shall" alone (rule 6)
    deemed = Element("e1", "urn:e1", "9.1", "body", "clause", None, (
        model.Part(0, "literal", "A thing shall be deemed done."),
    ))
    assert classify.keyword_class(tokens.tokenise(deemed), "clause") == "Deeming"

    # "shall not" (rule 4) must win over "shall" alone (rule 6)
    prohibition = Element("e2", "urn:e2", "9.2", "body", "clause", None, (
        model.Part(0, "literal", "Borrower shall not act."),
    ))
    assert classify.keyword_class(tokens.tokenise(prohibition), "clause") == "Prohibition"


def test_keyword_rules_give_none_when_no_rule_applies():
    element = Element("e1", "urn:e1", "9.1", "body", "clause", None, (model.Part(0, "literal", "Nothing here."),))
    assert classify.keyword_class(tokens.tokenise(element), "clause") is None


# S6-07 --------------------------------------------------------------------------------------------


@pytest.mark.parametrize("sample_id", list(SAMPLES))
def test_spans_are_sorted_non_overlapping_and_cover_every_word_token(sample_id):
    wording = _load_sample(sample_id)
    profile = forms.load_profile()
    analysis = analyse.analyse_wording(wording, profile)

    for ea in analysis["elements"]:
        spans = ea["spans"]
        assert spans == sorted(spans, key=lambda s: s["start"])
        for a, b in zip(spans, spans[1:]):
            assert a["end"] <= b["start"]

        element = next(e for e in wording.elements if e.element_id == ea["elementId"])
        for token in tokens.tokenise(element):
            if token.kind != "word":
                continue
            covering = [s for s in spans if s["start"] <= token.start and token.end <= s["end"]]
            assert len(covering) == 1, (sample_id, ea["objectId"], token)


# S6-08 --------------------------------------------------------------------------------------------


@pytest.mark.parametrize("sample_id", list(SAMPLES))
def test_analysis_matches_the_committed_golden(sample_id):
    wording = _load_sample(sample_id)
    profile = forms.load_profile()
    analysis = _full_analysis(wording, profile)

    golden = json.loads((GOLDENS / f"{sample_id}.analysis.json").read_text(encoding="utf-8"))
    assert analysis == golden


# S6-09 --------------------------------------------------------------------------------------------


def test_facility_le_program_matches_the_golden():
    wording = _load_sample("facility-agreement")
    profile = forms.load_profile()
    analysis = analyse.analyse_wording(wording, profile)

    golden = (GOLDENS / "facility-agreement.le").read_text(encoding="utf-8")
    assert analysis["leProgram"] == golden


# S6-10 --------------------------------------------------------------------------------------------


def test_facility_proposal_graph_matches_the_golden():
    wording = _load_sample("facility-agreement")
    profile = forms.load_profile()
    analysis = analyse.analyse_wording(wording, profile)
    proposal_graph_iri = f"{wording.iri[: -len('wording')]}rev/1/proposal-graph"
    graph = proposal.proposal_graph(wording, analysis["elements"], proposal_graph_iri, profile)

    golden = rdflib.Graph()
    golden.parse(GOLDENS / "facility-agreement.proposal.ttl", format="turtle")
    assert isomorphic(graph, golden)

    from lattice_workers.wording_le.namespaces import INS

    for relation in graph.subjects(INS.expressedIn, None):
        assert len(list(graph.objects(relation, INS.expressedIn))) == 1

    declared_variables = {str(variable.iri) for variable in wording.variables}
    for variable_ref in graph.objects(None, INS.fromVariable):
        assert str(variable_ref) in declared_variables


# S6-11 --------------------------------------------------------------------------------------------


def _schema_registry() -> Registry:
    resources = []
    for path in sorted((CONTRACTS / "authoring").glob("*.schema.json")):
        schema = json.loads(path.read_text(encoding="utf-8"))
        resources.append((schema["$id"], Resource.from_contents(schema)))
    return Registry().with_resources(resources)


@pytest.mark.parametrize("sample_id", list(SAMPLES))
def test_analysis_validates_against_the_common_schema(sample_id):
    wording = _load_sample(sample_id)
    profile = forms.load_profile()
    analysis = _full_analysis(wording, profile)

    registry = _schema_registry()
    common_id = "https://schemas.nebularis.org/lattice/authoring/common/0.1.0"
    validator = Draft202012Validator({"$ref": f"{common_id}#/$defs/Analysis"}, registry=registry)
    errors = list(validator.iter_errors(analysis))
    assert errors == [], errors


# S6-12 --------------------------------------------------------------------------------------------


def test_every_namespace_is_declared_in_the_java_vocabulary():
    from lattice_workers.wording_le import namespaces

    vocab_text = VOCAB.read_text(encoding="utf-8")
    for name in ("WRD", "INS", "WAP", "PROV", "DCTERMS"):
        namespace = str(getattr(namespaces, name))
        assert namespace in vocab_text, name


# S6-13 --------------------------------------------------------------------------------------------


def test_an_element_with_zero_parts_gets_basis_none_and_the_rest_are_unaffected():
    wording = _load_sample("facility-agreement")
    empty = model.Element("empty-1", "urn:empty-1", "9.9", "definitions", "clause", None, ())
    patched = model.Wording(
        wording.iri, wording.document_id, wording.title, wording.template_id, wording.revision,
        (empty, *wording.elements), wording.variables,
    )
    profile = forms.load_profile()
    analysis = analyse.analyse_wording(patched, profile)

    empty_analysis = next(ea for ea in analysis["elements"] if ea["elementId"] == "empty-1")
    assert empty_analysis["basis"] == "none"
    assert empty_analysis["spans"] == []
    assert empty_analysis["relationClass"] is None

    rest = [ea for ea in analysis["elements"] if ea["elementId"] != "empty-1"]
    original = analyse.analyse_wording(wording, profile)["elements"]
    assert rest == original
