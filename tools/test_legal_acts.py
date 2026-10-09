# SPDX-License-Identifier: MPL-2.0
"""Instrument: the legal acts tier (computable-contract-substrate C9b1, ADR-A104, ADR-A120).
Rows C9b1-01 to C9b1-11 of the Validation Pack."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from pyshacl import validate
from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import OWL, RDF, RDFS, SH, XSD

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent / "mork_compilers" / "src"))
from test_parameter_bindings import ALL_SHAPES, LATTICE, LOWER, ONTOLOGY, READ_WITH, SPEC, VOCAB, _graph  # noqa: E402

from mork_compilers.eligibility_ir import compile_any_condition  # noqa: E402
from mork_compilers.namespaces import MORK  # noqa: E402
from mork_compilers.sparql_backend import compile_query_template  # noqa: E402

INS = Namespace(LATTICE + "instrument#")
INS_VOC = Namespace(LATTICE + "instrument/vocab#")
FND = Namespace(LATTICE + "foundation#")
BHV = Namespace(LATTICE + "behaviour#")
LAYER = ONTOLOGY / "instrument"
ACTS = LAYER / "spec" / "instrument-acts.ttl"
EXAMPLES = LAYER / "examples"
RE = Namespace("https://example.org/lattice/instrument/reinsurance-claims-cooperation/")
FR = Namespace("https://example.org/lattice/instrument/facility-requests/")
FAM = Namespace("https://example.org/lattice/instrument/facility-amendment/")
FILES = {
    "reinsurance-claims-cooperation": [EXAMPLES / "reinsurance-claims-cooperation.ttl"],
    "facility-requests": [*READ_WITH["facility-requests"], EXAMPLES / "facility-requests.ttl"],
}
MODEL = _graph(SPEC, ACTS, VOCAB, *[ONTOLOGY / p for p in LOWER])
SHAPES = _graph(*ALL_SHAPES)
CLASSES = ("LegalAct", "Declaration", "Assent", "Consent", "Objection", "Withdrawal", "Exercise", "Proposal")
PROPERTIES = ("actBy", "assentBy", "assentTo", "proposedBy", "proposes", "directedAt", "withdraws", "exercises",
              "pursuantTo", "forCase")
PREFIXES = (f"@prefix ins: <{INS}> .\n@prefix fnd: <{FND}> .\n@prefix xsd: <{XSD}> .\n"
            f"@prefix ex: <{RE}> .\n@prefix fr: <{FR}> .\n@prefix fam: <{FAM}> .\n")


def _example(name: str, add: str = "", remove: tuple = ()) -> Graph:
    g = _graph(*FILES[name])
    for s, p, o in remove:
        assert (s, p, o) in g or o is None, (s, p, o)
        g.remove((s, p, o))
    if add:
        g.parse(data=PREFIXES + add, format="turtle")
    return g


def _results(data: Graph, severity=SH.Violation) -> list[tuple[str, str]]:
    _, report, _ = validate(data + MODEL, shacl_graph=SHAPES, inference="none", advanced=True)
    return [(str(report.value(r, SH.focusNode)), str(report.value(r, SH.resultMessage)))
            for r in report.subjects(SH.resultSeverity, severity)]


def _reported(data: Graph, focus: str, fragment: str) -> bool:
    return any(f.endswith(focus) and fragment in m for f, m in _results(data))


# ---- C9b1-01 and C9b1-02: the acts document and its imports ------------------------

def test_c9b1_01_the_acts_document() -> None:
    acts, main = _graph(ACTS), _graph(SPEC)
    ontology = URIRef("https://www.nebularis.org/neuro-semantic/instrument-acts")
    version = str(main.value(URIRef("https://www.nebularis.org/neuro-semantic/instrument"), OWL.versionIRI))
    assert str(acts.value(ontology, OWL.versionIRI)) == version.replace("/instrument/", "/instrument-acts/")
    for term in (*CLASSES, *PROPERTIES):
        assert acts.value(INS[term], FND.utility) is not None, term
        assert main.value(INS[term], FND.utility) is None, term                 # moved, or new here
    for term in PROPERTIES:
        assert "Subject:" in str(acts.value(INS[term], FND.utility)), term
        assert "Value:" in str(acts.value(INS[term], FND.utility)), term
    assert set(acts.objects(INS.LegalAct, RDFS.subClassOf)) == {URIRef("http://www.w3.org/ns/prov#Activity"),
                                                                 FND.TemporallyScoped, FND.Evidenced}
    assert (INS.assentBy, RDFS.subPropertyOf, INS.actBy) in acts and (INS.proposedBy, RDFS.subPropertyOf, INS.actBy) in acts
    assert "consent to a power" not in str(acts.value(INS.Assent, FND.utility))


def test_c9b1_02_the_acts_document_imports_no_behaviour_runtime() -> None:
    """The import guard reads behaviour-runtime as Behaviour (TD-28), so this document is checked alone."""
    acts, main = _graph(ACTS), _graph(SPEC)
    version = main.value(URIRef("https://www.nebularis.org/neuro-semantic/instrument"), OWL.versionIRI)
    assert set(acts.objects(None, OWL.imports)) == {version}
    for path in (ACTS, SPEC):
        assert "behaviour-runtime" not in path.read_text() and "/applied/" not in path.read_text(), path.name
    assert "instrument-acts" not in SPEC.read_text()
    runtime = _graph(ONTOLOGY / "behaviour" / "spec" / "behaviour-runtime.ttl")
    declared = {s for s in runtime.subjects(RDF.type, None) if str(s).startswith(str(BHV))}
    assert not declared & set(acts.all_nodes()), declared & set(acts.all_nodes())


# ---- C9b1-03: the examples ---------------------------------------------------------

@pytest.mark.parametrize("name", sorted(FILES))
def test_c9b1_03_examples_conform(name: str) -> None:
    assert _results(_example(name)) == []


@pytest.mark.parametrize("name", ["facility-amendment", "licence-amendments", "property-endorsement"])
def test_c9b1_03_c9a_examples_conform_with_the_acts_document(name: str) -> None:
    assert _results(_graph(*READ_WITH.get(name, []), EXAMPLES / f"{name}.ttl")) == []


# ---- C9b1-04: each act's shapes, at zero and too many -------------------------------

TIME = 'fnd:hasTemporalScope [ fnd:validFrom "2028-03-02T00:00:00Z"^^xsd:dateTime ]'


@pytest.mark.parametrize("name, add, remove, focus, message", [
    ("facility-requests", "", ((FR["request-2"], INS.proposes, FR.waiver),), "/request-2", "exactly one matter"),
    ("facility-requests", "fr:request-2 ins:proposes fam:amendment-1 .", (), "/request-2", "exactly one matter"),
    ("facility-requests", "", ((FR["request-2"], INS.proposedBy, FAM["borrower-occ"]),), "/request-2", "ins:proposedBy"),
    ("facility-requests", "", ((FR["consent-northgate"], INS.directedAt, FR["request-2"]),), "/consent-northgate",
     "exactly one proposal"),
    ("facility-requests", "fr:objection-tidewater ins:directedAt fr:request-1 .", (), "/objection-tidewater",
     "exactly one proposal"),
    ("facility-requests", "fr:consent-northgate ins:directedAt fam:amendment-1 .",
     ((FR["consent-northgate"], INS.directedAt, FR["request-2"]),), "/consent-northgate", "exactly one proposal"),
    ("facility-requests", "", ((FR["withdrawal-larchmont"], INS.withdraws, FR["consent-larchmont"]),),
     "/withdrawal-larchmont", "exactly one assent, consent or objection"),
    ("facility-requests", "fr:withdrawal-larchmont ins:withdraws fr:consent-northgate .", (), "/withdrawal-larchmont",
     "exactly one assent, consent or objection"),
    ("facility-requests", "", ((FR["consent-larchmont"], INS.actBy, FAM["larchmont-occ"]),), "/consent-larchmont",
     "ins:actBy"),
    ("facility-requests", "fr:objection-tidewater ins:actBy fr:request-2 .", (), "/objection-tidewater", "ins:actBy"),
    ("reinsurance-claims-cooperation", "", ((RE["settlement-2"], INS.exercises, RE.settle),), "/settlement-2",
     "exactly one bound power"),
    ("reinsurance-claims-cooperation", "ex:settlement-2 ins:exercises ex:approve .", (), "/settlement-2",
     "exactly one bound power"),
    ("reinsurance-claims-cooperation", "ex:settlement-2 ins:exercises ex:settle-stated .",
     ((RE["settlement-2"], INS.exercises, RE.settle),), "/settlement-2", "exactly one bound power"),
    ("reinsurance-claims-cooperation", "ex:settlement-2 ins:forCase ex:claim-1 .", (), "/settlement-2",
     "at most one case"),
    ("reinsurance-claims-cooperation", "ex:approval-1 " + TIME + " .", (), "/approval-1", "exactly one time"),
    ("reinsurance-claims-cooperation", "", ((RE["approval-1"], FND.hasTemporalScope, None),), "/approval-1",
     "exactly one time"),
    ("reinsurance-claims-cooperation", "", ((RE["request-1"], FND.hasEvidence, None),), "/request-1",
     "recording time"),
])
def test_c9b1_04_act_shapes_report(name: str, add: str, remove: tuple, focus: str, message: str) -> None:
    assert _reported(_example(name, add, remove), focus, message)


# ---- C9b1-05: only acts carry the acts' properties -----------------------------------

@pytest.mark.parametrize("add, focus, message", [
    ("ex:policy ins:proposes ex:settlement-terms-1 .", "/policy", "Only a proposal"),
    ("ex:policy ins:directedAt ex:request-1 .", "/policy", "Only a consent or an objection"),
    ("ex:policy ins:withdraws ex:approval-1 .", "/policy", "Only a withdrawal"),
    ("ex:indemnify ins:exercises ex:settle .", "/indemnify", "Only an exercise"),
    ("ex:indemnify ins:forCase ex:claim-1 .", "/indemnify", "Only a legal act"),
    ("ex:indemnify ins:pursuantTo ex:approval-1 .", "/indemnify", "Only a legal act"),
])
def test_c9b1_05_subject_shapes_report(add: str, focus: str, message: str) -> None:
    assert _reported(_example("reinsurance-claims-cooperation", add), focus, message)


# ---- C9b1-06: a proposal and what it proposes ----------------------------------------

def test_c9b1_06_a_proposal_is_made_when_its_amendment_is_not() -> None:
    g = _example("facility-requests")
    amendment = g.value(FR["request-1"], INS.proposes)
    assert amendment == FAM["amendment-1"] and (amendment, RDF.type, INS.Amendment) in g
    made = g.value(g.value(FR["request-1"], FND.hasTemporalScope), FND.validFrom).toPython()
    effective = g.value(g.value(amendment, FND.hasTemporalScope), FND.validFrom).toPython()
    assert effective < made                                                     # proposed in February, effective 1 January
    assert not (INS.Amendment, RDFS.subClassOf, INS.Proposal) in MODEL          # C9b1-Q1 (a): the amendment is unchanged
    assert {g.value(c, INS.actBy) for c in g.subjects(INS.directedAt, FR["request-2"])} == \
        {FAM["northgate-occ"], FAM["tidewater-occ"], FAM["larchmont-occ"]}
    assert {g.value(w, INS.withdraws) for w in g.subjects(RDF.type, INS.Withdrawal)} == \
        {FR["consent-larchmont"], FR["objection-tidewater"]}


# ---- C9b1-07 and C9b1-08: pursuant to, before, by the holder -------------------------

def test_c9b1_07_pursuant_to_across_instruments() -> None:
    g = _example("reinsurance-claims-cooperation")
    instrument = lambda act: g.value(g.value(g.value(act, INS.exercises), INS.arisesUnder), INS.boundIn)
    assert (RE["settlement-1"], INS.pursuantTo, RE["approval-1"]) in g
    assert instrument(RE["settlement-1"]) == RE.policy and instrument(RE["approval-1"]) == RE.reinsurance
    assert not [m for _, m in _results(g) if "pursuant to" in m]


def _move(g: Graph, act, when: str) -> Graph:
    g.set((g.value(act, FND.hasTemporalScope), FND.validFrom, Literal(when, datatype=XSD.dateTime)))
    return g


def test_c9b1_07_an_approval_after_the_settlement_is_reported() -> None:
    g = _move(_example("reinsurance-claims-cooperation"), RE["approval-1"], "2028-04-20T00:00:00Z")
    found = [(f, m) for f, m in _results(g) if "is made pursuant to" in m]
    assert [f for f, _ in found] == [str(RE["settlement-1"])]
    g = _move(_example("reinsurance-claims-cooperation"), RE["approval-1"], "2028-04-15T12:00:00Z")   # the same moment
    assert not [m for _, m in _results(g) if "is made pursuant to" in m]


def test_c9b1_08_an_approval_by_another_party_is_reported() -> None:
    g = _example("reinsurance-claims-cooperation", "ex:approval-1 ins:actBy ex:reinsured-occ .",
                 ((RE["approval-1"], INS.actBy, RE["reinsurer-occ"]),))
    found = [(f, m) for f, m in _results(g) if "does not hold the power" in m]
    assert [f for f, _ in found] == [str(RE["approval-1"])]
    later = ("ex:reinsurer-occ-2 a <https://www.nebularis.org/neuro-semantic/lattice/party#RoleOccupancy> ; "
             "fnd:hasIdentity ex:reinsurer-occ-identity . ex:approval-1 ins:actBy ex:reinsurer-occ-2 .")
    g = _example("reinsurance-claims-cooperation", later, ((RE["approval-1"], INS.actBy, RE["reinsurer-occ"]),))
    assert not [m for _, m in _results(g) if "does not hold the power" in m]    # a later version of the holder


# ---- C9b1-09: the indemnity's scope, read along the acts -----------------------------

def _decisions(g: Graph) -> dict[str, str]:
    g = g + _graph(VOCAB)
    template = compile_query_template(compile_any_condition(g, RE["settled-with-approval"]))
    query = str(template.value(next(template.subjects(RDF.type, MORK.QueryTemplate)), MORK.queryText))
    return {str(r["question"]).rsplit("/", 1)[-1]: str(r["decision"]).rsplit("#", 1)[-1] for r in g.query(query)}


def test_c9b1_09_settled_with_approval_is_permitted() -> None:
    g = _example("reinsurance-claims-cooperation")
    assert g.value(RE.indemnify, INS.scope) == RE["settled-with-approval"]
    assert g.value(RE.indemnify, INS.arisesOnExerciseOf) == RE.settle
    assert _decisions(g) == {"claim-1": "Permitted", "claim-2": "Undetermined"}   # no approval: HQ-6


def test_c9b1_09_without_the_settlements_reliance_the_claim_is_undetermined() -> None:
    g = _example("reinsurance-claims-cooperation", remove=((RE["settlement-1"], INS.pursuantTo, RE["approval-1"]),))
    assert _decisions(g)["claim-1"] == "Undetermined"


# ---- C9b1-10: an exercise trigger is derived -----------------------------------------

def test_c9b1_10_on_exercise_is_a_derived_trigger() -> None:
    spec = _graph(SPEC)
    kinds = {spec.value(r, OWL.hasValue) for r in spec.objects(INS.OnExercise, RDFS.subClassOf)
             if spec.value(r, OWL.onProperty) == BHV.triggerKind}
    assert kinds == {BHV.DerivedTrigger}
    for path in sorted(EXAMPLES.glob("*.ttl")):
        g = _graph(path)
        for trigger in g.subjects(RDF.type, INS.OnExercise):
            assert set(g.objects(trigger, BHV.triggerKind)) == {BHV.DerivedTrigger}, (path.name, trigger)
    g = _graph(EXAMPLES / "licence-notice.ttl")
    trigger = URIRef("https://example.org/lattice/instrument/licence-notice/form/on-notice-given")
    g.set((trigger, BHV.triggerKind, BHV.ExternalStimulus))
    assert any(f == str(trigger) and "bhv:DerivedTrigger, fixed" in m for f, m in _results(g))


# ---- C9b1-11: a term implied by a judgment -------------------------------------------

def test_c9b1_11_a_term_implied_by_a_judgment() -> None:
    assert "judgment" in str(_graph(SPEC).value(INS.impliedBy, FND.utility))
    g = _example("reinsurance-claims-cooperation")
    source = g.value(RE["re-implied-term"], INS.impliedBy)
    assert "EWCA Civ 1047" in str(g.value(source, RDFS.label))
    assert g.value(RE["not-withhold-arbitrarily"], INS.impliedBy) == source
    assert g.value(RE["not-withhold-arbitrarily"], INS.obligor) == g.value(RE.approve, INS.holder)
    readme = (LAYER / "README.md").read_text()
    assert "Instrument's runtime document is upstream" not in readme
