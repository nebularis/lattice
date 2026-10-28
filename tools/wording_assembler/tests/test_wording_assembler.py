# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""The baseline assembly model (ADR-A139) as run by the reference assembler (ADR-A140). Row names are the
laws', WA1 to WA6."""

from __future__ import annotations

import random
import re
import shutil
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
from rdflib import Graph, URIRef
from rdflib.compare import isomorphic
from rdflib.namespace import RDF, SH

from helpers import AT, FACILITY as F, LICENCE as L, WRD, counting_mint, settings
from wording_assembler import assemble, check, findings, plan, reassemble, render
from wording_assembler.layer import catalogue

FACILITY_SETTINGS = "f:s-lenders a wrd:VariableValue ; wrd:forVariable f:gv-lender-count ; wrd:literalValue \"{}\"^^xsd:decimal ."
JURISDICTIONS = "f:s-jur a wrd:VariableValue ; wrd:forVariable f:var-jurisdictions ; wrd:value f:uk , f:ie ."
DEPLOYMENT = "l:s-dep a wrd:VariableValue ; wrd:forVariable l:gv-deployment ; wrd:value l:{} ."
FEE = "l:s-fee a wrd:VariableValue ; wrd:forVariable l:var-fee ; wrd:literalValue \"GBP 5,000\" ."


def facility(plan_, count=None, choices=(F["cl-5-2b"],), jurisdictions=True, mint=None):
    lines = ([FACILITY_SETTINGS.format(count)] if count is not None else []) + ([JURISDICTIONS] if jurisdictions else [])
    return assemble(plan_, settings("\n".join(lines)), set(choices), at=AT, mint=mint or counting_mint())


def licence(plan_, deployment=None, choices=(), mint=None):
    lines = [FEE] + ([DEPLOYMENT.format(deployment)] if deployment else [])
    return assemble(plan_, settings("\n".join(lines)), set(choices), at=AT, mint=mint or counting_mint())


def included(result):
    return {str(o).rsplit("/", 1)[1] for o in result.record.objects(result.record_iri, WRD.includes)}


def stages(result):
    return [(f.stage, f.severity) for f in findings(result.findings)]


@pytest.fixture(scope="module")
def facility_plan(facility_form, layer):
    return plan(facility_form, F.form, layer=layer)


@pytest.fixture(scope="module")
def licence_plan(licence_form, layer):
    return plan(licence_form, L.form, layer=layer)


# ---- check and plan --------------------------------------------------------------------------

def test_a_sound_form_has_no_findings(facility_form, licence_form, layer):
    for form, iri in ((facility_form, F.form), (licence_form, L.form)):
        assert [f for f in findings(check(form, iri, layer=layer)) if f.severity == SH.Violation] == []


def test_a_broken_form_is_reported_under_validate(facility_form, layer):
    broken = Graph() + facility_form
    broken.add((F["cl-5-2a"], WRD.inclusionMode, URIRef("https://www.nebularis.org/neuro-semantic/lattice/wording/vocab#Optional")))
    broken.remove((F["cl-5-2a"], WRD.inclusionMode, URIRef("https://www.nebularis.org/neuro-semantic/lattice/wording/vocab#Variation")))
    report = check(broken, F.form, layer=layer)
    assert any(f.stage == "validate" and "W3" in f.message for f in findings(report))
    refused = plan(broken, F.form, layer=layer)
    assert not refused.ok and not refused.inclusions
    result = assemble(refused, settings(""), set(), at=AT, mint=counting_mint())
    assert not result.ok and result.record is None


def test_the_plan_lists_the_questions_its_conditions_pose(facility_plan, licence_plan):
    assert facility_plan.questions == ((F["cl-9-1"], F["gv-lender-count"]),)
    assert licence_plan.questions == tuple(sorted(
        [(L["cl-hosted"], L["gv-deployment"]), (L["cl-hosted-local"], L["gv-deployment"]), (L["cl-hosted-local"], L["gv-deployment"])], key=str))
    assert "SELECT" in facility_plan.inclusions[F["cl-9-1"]].query and facility_plan.digest.startswith("sha256:")


# ---- decisions: admit, deny, undetermined -----------------------------------------------------

def test_an_admitted_condition_includes_the_element(facility_plan):
    result = facility(facility_plan, count=3)
    assert result.ok, findings(result.findings)
    assert included(result) == {"sec-5", "cl-5-1", "slot-5-2", "cl-5-2b", "sec-9", "cl-9-1", "sec-12", "cl-12-1"}


def test_a_denied_condition_leaves_the_element_out(facility_plan):
    result = facility(facility_plan, count=1)
    assert result.ok and "cl-9-1" not in included(result) and "sec-9" in included(result)


def test_an_undetermined_condition_refuses_naming_the_governing_variable(facility_plan):
    result = facility(facility_plan)
    assert not result.ok and result.record is None
    (finding,) = [f for f in findings(result.findings) if f.severity == SH.Violation]
    assert finding.stage == "decide" and finding.focus == F["cl-9-1"] and finding.value == F["gv-lender-count"]
    assert str(F["gv-lender-count"]) in finding.message


def test_the_concept_conditions_decide_a_slot(licence_plan):
    result = licence(licence_plan, "hybrid", choices=())
    assert result.ok, findings(result.findings)
    assert "cl-hosted-local" in included(result) and "cl-hosted" not in included(result) and "slot-hosting" in included(result)


# ---- slots -------------------------------------------------------------------------------------

def test_a_slot_with_no_admitted_variant_refuses(licence_plan):
    result = licence(licence_plan, "on-premises")
    assert not result.ok and result.record is None
    assert any(f.stage == "decide" and "admits none" in f.message for f in findings(result.findings))


def test_a_slot_with_two_admitted_variants_refuses(licence_plan):
    result = licence(licence_plan, "hosted")
    assert not result.ok and result.record is None
    assert any(f.stage == "decide" and "several" in f.message and str(L["cl-hosted-local"]) in f.message for f in findings(result.findings))


def test_a_slot_whose_conditions_are_undetermined_names_the_variable(licence_plan):
    result = licence(licence_plan)
    assert not result.ok
    assert {f.value for f in findings(result.findings) if f.stage == "decide"} == {L["gv-deployment"]}


def test_a_variant_with_no_condition_is_included_when_chosen(facility_plan):
    assert "cl-5-2a" in included(facility(facility_plan, count=3, choices=(F["cl-5-2a"],)))
    refused = facility(facility_plan, count=3, choices=())
    assert not refused.ok and any("admits none" in f.message for f in findings(refused.findings))
    both = facility(facility_plan, count=3, choices=(F["cl-5-2a"], F["cl-5-2b"]))
    assert not both.ok and any("several" in f.message for f in findings(both.findings))


# ---- optional elements -------------------------------------------------------------------------

def test_an_optional_element_is_included_only_when_chosen(licence_plan):
    assert "cl-audit" in included(licence(licence_plan, "hybrid", choices=(L["cl-audit"],)))
    assert "cl-audit" not in included(licence(licence_plan, "hybrid"))


def test_a_choice_that_is_not_a_choice_is_a_load_finding(facility_plan):
    result = facility(facility_plan, count=3, choices=(F["cl-5-2b"], F["cl-5-1"]))
    assert not result.ok and [f.stage for f in findings(result.findings)] == ["load"]


# ---- the record: WA1, WA2, PROV ----------------------------------------------------------------

def test_wa1_the_record_names_one_model_and_its_assembly(facility_plan, layer):
    result = facility(facility_plan, count=3)
    model = list(result.record.objects(result.record_iri, WRD.assembledUnder))
    assert len(model) == 1
    activity = result.record.value(result.record_iri, URIRef("http://www.w3.org/ns/prov#wasGeneratedBy"))
    used = set(result.record.objects(activity, URIRef("http://www.w3.org/ns/prov#used")))
    assert {F.form, model[0]} <= used and len(used) == 3
    assert set(result.digests) == {"plan", "settings", "choices", "model"}
    twice = Graph() + result.record
    twice.add((result.record_iri, WRD.assembledUnder, URIRef("urn:test:other-model")))
    from wording_assembler.check import run_shapes
    out = Graph()
    run_shapes(twice + facility_plan.graph, layer, "record", out, {result.record_iri})
    assert any("WA1" in f.message for f in findings(out))


def test_wa2_the_record_satisfies_the_assembled_laws(facility_plan, layer):
    """A wrong value breaks W6 and the assembly is refused at stage assemble."""
    bad = settings(FACILITY_SETTINGS.format(3) + "\nf:s-bad a wrd:VariableValue ; wrd:forVariable f:var-jurisdictions ; wrd:value f:atlantis .")
    result = assemble(facility_plan, bad, {F["cl-5-2b"]}, at=AT, mint=counting_mint())
    assert not result.ok and result.record is None
    assert any(f.stage == "assemble" and "W6" in f.message for f in findings(result.findings))


# ---- WA5 and WA6 -------------------------------------------------------------------------------

def _shuffled(graph: Graph, seed: int) -> Graph:
    triples = sorted(graph, key=str)
    random.Random(seed).shuffle(triples)
    out = Graph()
    for t in triples:
        out.add(t)
    return out


def test_wa5_the_same_inputs_give_the_same_record(facility_form, layer):
    values = settings(FACILITY_SETTINGS.format(3) + "\n" + JURISDICTIONS)
    records = []
    for seed in (1, 2, 3, 3):
        p = plan(_shuffled(facility_form, seed), F.form, layer=layer)
        records.append(assemble(p, _shuffled(values, seed), {F["cl-5-2b"]}, at=AT, mint=counting_mint(), layer=layer).record)
    assert all(r is not None and isomorphic(records[0], r) for r in records)
    assert set(records[0]) == set(records[1])


def test_wa6_a_failed_assembly_gives_findings_and_no_record(facility_plan):
    result = facility(facility_plan)
    assert (result.ok, result.record, result.record_iri) == (False, None, None)
    assert next(result.findings.subjects(RDF.type, SH.ValidationReport)) is not None
    assert next(result.findings.objects(None, SH.conforms)).toPython() is False


# ---- re-assembly -------------------------------------------------------------------------------

def test_reassembly_shares_unchanged_values_and_keeps_the_identity(facility_plan):
    first = facility(facility_plan, count=3)
    new = settings(FACILITY_SETTINGS.format(1) + "\n" + JURISDICTIONS)
    mint = counting_mint()
    again = reassemble(first.record, first.record_iri, facility_plan, new, {F["cl-5-2b"]}, at=AT, mint=mint)
    assert again.ok, findings(again.findings)
    identity = lambda g, r: g.value(r, URIRef("https://www.nebularis.org/neuro-semantic/lattice/foundation#hasIdentity"))
    assert identity(again.record, again.record_iri) == identity(first.record, first.record_iri)
    old, fresh = set(first.record.objects(first.record_iri, WRD.hasValue)), set(again.record.objects(again.record_iri, WRD.hasValue))
    assert old & fresh == {F["s-jur"]} and len(fresh - old) == 1 and len(old - fresh) == 1
    assert (F["s-jur"], None, None) not in again.record, "a shared record is not written again"
    assert "cl-9-1" not in included(again)
    assert (first.record_iri, URIRef("https://www.nebularis.org/neuro-semantic/lattice/foundation#supersededBy"), again.record_iri) in again.record


# ---- render ------------------------------------------------------------------------------------

NS = {"d": "https://www.nebularis.org/neuro-semantic/lattice/document/1"}


def _numbers(xml: str):
    root = ET.fromstring(xml)
    return [("".join(c.itertext())).split(" ", 1)[0] for c in root.iter("{%s}clause" % NS["d"])]


def _validate(xml: str, tmp_path: Path) -> None:
    root = ET.fromstring(xml)                                    # well formed
    ids = [e.get("id") for e in root.iter() if e.get("id")]
    assert len(ids) == len(set(ids))
    assert all(re.fullmatch(r"[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}", i) for i in ids)
    cat = catalogue()
    schema = cat.root / cat.area("contracts") / "document" / "document.xsd"
    if shutil.which("xmllint"):                                  # the schema check runs where xmllint is installed
        path = tmp_path / "out.xml"
        path.write_text(xml, encoding="utf-8", newline="\n")
        done = subprocess.run(["xmllint", "--noout", "--schema", str(schema), str(path)], capture_output=True, text=True)
        assert done.returncode == 0, done.stderr


def test_render_numbers_by_rank_among_the_included_siblings(licence_plan, licence_form, tmp_path):
    with_audit = licence(licence_plan, "hybrid", choices=(L["cl-audit"],))
    without = licence(licence_plan, "hybrid")
    xml_with, xml_without = (render(r.record, r.record_iri, licence_form) for r in (with_audit, without))
    assert _numbers(xml_with) == ["1.1", "1.2", "1.3", "2.1", "2.2"]
    assert _numbers(xml_without) == ["1.1", "1.2", "2.1", "2.2"], "a clause left out moves those after it up"
    assert "The licence is not transferable." in xml_without and "1.2 The licence is not transferable." in xml_without
    assert "2.2 The vendor hosts the software, and the licensee runs a local component." in xml_without
    assert '<var key="annual-fee">GBP 5,000</var>' in xml_without
    for xml in (xml_with, xml_without):
        _validate(xml, tmp_path)


def test_a_chosen_variant_takes_its_slots_number(facility_plan, facility_form, tmp_path):
    result = facility(facility_plan, count=3)
    xml = render(result.record, result.record_iri, facility_form)
    assert _numbers(xml) == ["1.1", "1.2", "2.1", "3.1"]
    assert "1.2 Each interest period is three months." in xml and "2.1 The agent acts" in xml
    assert "Ireland, United Kingdom" in xml
    _validate(xml, tmp_path)
    assert render(result.record, result.record_iri, facility_form) == xml
