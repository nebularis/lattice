# SPDX-License-Identifier: MPL-2.0
"""Instrument: amendments, assents and taking effect (computable-contract-substrate C9a,
ADR-A104 and its 2026-10-08 addendum). Rows C9a-01 to C9a-14 of the Validation Pack."""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

import pytest
from pyshacl import validate
from rdflib import BNode, Graph, Literal, Namespace, URIRef
from rdflib.namespace import OWL, RDF, SH, XSD

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_parameter_bindings import ALL_SHAPES, LATTICE, LOWER, ONTOLOGY, READ_WITH, SPEC, VOCAB, _graph  # noqa: E402

INS = Namespace(LATTICE + "instrument#")
INS_VOC = Namespace(LATTICE + "instrument/vocab#")
FND = Namespace(LATTICE + "foundation#")
WRD = Namespace(LATTICE + "wording#")
ELG = Namespace(LATTICE + "eligibility#")
BHV = Namespace(LATTICE + "behaviour#")
EXAMPLES = ONTOLOGY / "instrument" / "examples"
FAC = Namespace("https://example.org/lattice/instrument/facility-amendment/")
LIC = Namespace("https://example.org/lattice/instrument/licence-amendments/")
LIC_FORM = Namespace("https://example.org/lattice/instrument/licence-amendments/form/")
END = Namespace("https://example.org/lattice/instrument/property-endorsement/")
FILES = {
    "facility-amendment": [*READ_WITH["facility-amendment"], EXAMPLES / "facility-amendment.ttl"],
    "licence-amendments": [EXAMPLES / "licence-amendments.ttl"],
    "property-endorsement": [EXAMPLES / "property-endorsement.ttl"],
}
MODEL = _graph(SPEC, VOCAB, *[ONTOLOGY / p for p in LOWER])
SHAPES = _graph(*ALL_SHAPES)


def _example(name: str) -> Graph:
    return _graph(*FILES[name])


def _results(data: Graph, severity=SH.Violation) -> list[tuple[str, str]]:
    _, report, _ = validate(data + MODEL, shacl_graph=SHAPES, inference="none", advanced=True)
    return [(str(report.value(r, SH.focusNode)), str(report.value(r, SH.resultMessage)))
            for r in report.subjects(SH.resultSeverity, severity)]


def _time(g: Graph, node, path) -> datetime:
    return g.value(g.value(node, path[0]), path[1]).toPython()


def _valid(g: Graph, node) -> datetime:
    return _time(g, node, (FND.hasTemporalScope, FND.validFrom))


def _recorded(g: Graph, node) -> datetime:
    return min(g.value(e, FND.recordedAt).toPython() for e in g.objects(node, FND.hasEvidence))


def agreed(g: Graph, amendment) -> tuple[datetime, datetime] | None:
    """An amendment by agreement: when every party to the version it amends has assented to the
    version it produces, the (valid, recorded) times of the last assent. None if not agreed."""
    old, new = g.value(amendment, INS.amends), g.value(amendment, INS.resultsIn)
    times = []
    for party in g.objects(old, INS.party):
        assents = [a for a in g.subjects(INS.assentBy, party) if (a, INS.assentTo, new) in g]
        if not assents:
            return None
        times.append(min((_valid(g, a), _recorded(g, a)) for a in assents))
    return max(times)


def version_at(g: Graph, identity, t: datetime, k: datetime):
    """The version of an instrument in force at valid time t, as known at time k."""
    versions = set(g.subjects(FND.hasIdentity, identity)) & set(g.subjects(RDF.type, INS.Instrument))
    current = next(v for v in versions if not set(g.subjects(INS.resultsIn, v)))
    while True:
        step = None
        for a in g.subjects(INS.amends, current):
            done = agreed(g, a)
            if done and done[1] <= k and _valid(g, a) <= t:
                step = g.value(a, INS.resultsIn)
        if step is None:
            return current
        current = step


def _when(text: str) -> datetime:
    return Literal(text, datatype=XSD.dateTime).toPython()


# ---- C9a-01 and C9a-02 -----------------------------------------------------------

def test_c9a_01_spec_terms() -> None:
    spec = _graph(SPEC)
    ontology = next(spec.subjects(RDF.type, OWL.Ontology))
    assert spec.value(ontology, OWL.versionIRI) == URIRef(LATTICE + "instrument/0.15.1")
    terms = spec + _graph(SPEC.parent / "instrument-acts.ttl")                     # C9b1: assents are legal acts
    for term in ("Amendment", "amends", "resultsIn", "affectsExisting", "statedIn", "Assent",
                 "assentBy", "assentTo", "begins", "OnAcceptance"):
        assert terms.value(INS[term], FND.utility) is not None, term
    assert (INS.Amendment, OWL.disjointWith, FND.Version) in spec
    assert (INS_VOC.Conditional, None, None) in _graph(VOCAB)


@pytest.mark.parametrize("name", sorted(FILES))
def test_c9a_02_examples_conform(name: str) -> None:
    assert _results(_example(name)) == []


# ---- C9a-03 to C9a-06: amendments and agreement ---------------------------------

def test_c9a_03_text_changes_are_read_through_stated_in() -> None:
    g = _example("facility-amendment")
    changes = {row.change for row in g.query("""
        SELECT ?change WHERE { ?a ins:statedIn ?doc . ?doc wrd:directlyComprises* ?part .
                               ?change wrd:expressedIn ?part }""",
        initNs={"ins": INS, "wrd": WRD}, initBindings={"a": FAC["amendment-1"]})}
    names = {str(c).rsplit("/", 1)[-1] for c in changes}
    assert names == {"replace-5-2", "strike-5-1", "append-12-2", "strike-5-1-again"}


def test_c9a_04_agreed_when_every_party_has_assented() -> None:
    g = _example("facility-amendment")
    assert agreed(g, FAC["amendment-1"]) == (_when("2028-02-20T16:00:00Z"), _when("2028-02-21T08:30:00Z"))
    for triple in list(g.triples((FAC["assent-larchmont"], None, None))):
        g.remove(triple)
    assert agreed(g, FAC["amendment-1"]) is None


def test_c9a_05_the_facts_in_any_order() -> None:
    g = _example("facility-amendment")
    a = FAC["amendment-1"]
    valid, known = agreed(g, a)
    assert _valid(g, a) < _recorded(g, a) < valid < known
    shuffled = Graph()
    for triple in sorted(g, key=lambda t: str(t), reverse=True):
        shuffled.add(triple)
    assert agreed(shuffled, a) == (valid, known)


def _second_amendment(g: Graph, ns: Namespace, amended, parties, name: str) -> None:
    v = ns[name + "-version"]
    g.add((v, RDF.type, INS.Instrument))
    g.add((v, FND.hasIdentity, g.value(amended, FND.hasIdentity)))
    g.add((v, INS.expressedIn, g.value(amended, INS.expressedIn)))
    a = ns[name]
    for p, o in ((RDF.type, INS.Amendment), (INS.amends, amended), (INS.resultsIn, v),
                 (INS.statedIn, next(g.subjects(RDF.type, WRD.Wording)))):
        g.add((a, p, o))
    for subject in (a,):
        scope, evidence = BNode(), BNode()
        g.add((subject, FND.hasTemporalScope, scope)); g.add((scope, FND.validFrom, Literal("2028-06-01T00:00:00Z", datatype=XSD.dateTime)))
        g.add((subject, FND.hasEvidence, evidence)); g.add((evidence, FND.recordedAt, Literal("2028-05-01T00:00:00Z", datatype=XSD.dateTime)))
    for party in parties:
        g.add((v, INS.party, party))
        s = ns[name + "-assent-" + str(party).rsplit("/", 1)[-1]]
        g.add((s, RDF.type, INS.Assent)); g.add((s, INS.assentBy, party)); g.add((s, INS.assentTo, v))
        scope, evidence = BNode(), BNode()
        g.add((s, FND.hasTemporalScope, scope)); g.add((scope, FND.validFrom, Literal("2028-05-02T00:00:00Z", datatype=XSD.dateTime)))
        g.add((s, FND.hasEvidence, evidence)); g.add((evidence, FND.recordedAt, Literal("2028-05-02T00:00:00Z", datatype=XSD.dateTime)))


def test_c9a_06_one_agreed_amendment_per_version() -> None:
    parties = [END["insurer-occ"], END["insured-occ"]]
    g = _example("property-endorsement")
    assert not [m for _, m in _results(g) if "two agreed amendments" in m]           # one, and at zero for v2
    _second_amendment(g, END, END["policy-v1"], parties[:1], "rival")                 # pending: the insured has not assented
    assert not [m for _, m in _results(g) if "two agreed amendments" in m]
    _second_amendment(g, END, END["policy-v1"], parties, "rival")                     # now agreed too
    assert [f for f, m in _results(g) if "two agreed amendments" in m] == [str(END["policy-v1"])]


# ---- C9a-07 and C9a-08: overtaking and continuity -------------------------------

def test_c9a_07_an_overtaking_amendment_is_reported() -> None:
    g = _example("licence-amendments")
    assert not _results(g, SH.Warning)
    scope = g.value(LIC["amendment-2"], FND.hasTemporalScope)
    g.set((scope, FND.validFrom, Literal("2028-03-01T00:00:00Z", datatype=XSD.dateTime)))
    found = [(f, m) for f, m in _results(g, SH.Warning) if "No authored version holds the window" in m]
    assert [f for f, _ in found] == [str(LIC["amendment-2"])]


def test_c9a_08_affecting_existing_occasions_needs_continuity() -> None:
    g = _example("licence-amendments")
    g.set((LIC["amendment-1"], INS.affectsExisting, Literal(True)))
    found = [m for f, m in _results(g, SH.Warning) if f == str(LIC["amendment-1"])]
    assert any("guarantee" in m and "law I14" in m for m in found)


# ---- C9a-09: taking effect -------------------------------------------------------

def test_c9a_09_formation_regime() -> None:
    g = _example("licence-amendments")
    assert (LIC_FORM["in-force"], INS.begins, INS_VOC.TheInstrument) in g
    assert g.value(LIC_FORM["on-signed"], INS.by) is None                              # every ins:party
    g.add((LIC_FORM["conditional"], INS.begins, INS_VOC.TheInstrument))
    assert any("at most one may" in m for _, m in _results(g))
    g = _example("licence-amendments")
    g.add((LIC["licence-v1"], INS.begins, INS_VOC.TheInstrument))
    assert any("Only a state begins" in m for _, m in _results(g))


def test_c9a_09_formation_completes_on_the_last_signature() -> None:
    g = _example("licence-amendments")
    v1 = LIC["licence-v1"]
    last = max(_valid(g, a) for a in g.subjects(INS.assentTo, v1))
    assert last == _when("2027-09-08T16:00:00Z")
    assert {g.value(a, INS.assentBy) for a in g.subjects(INS.assentTo, v1)} == set(g.objects(v1, INS.party))


# ---- C9a-10: the endorsement and the losses -------------------------------------

@pytest.mark.parametrize("loss,when_notified,later", [
    ("loss-a", "policy-v1", "policy-v1"),
    ("loss-b", "policy-v1", "policy-v2"),
    ("loss-c", "policy-v2", "policy-v2"),
])
def test_c9a_10_which_version_decides_each_loss(loss: str, when_notified: str, later: str) -> None:
    g = _example("property-endorsement")
    t, notified = _valid(g, END[loss]), _recorded(g, END[loss])
    identity = END["policy-identity"]
    assert version_at(g, identity, t, notified) == END[when_notified]
    assert version_at(g, identity, t, _when("2028-12-31T00:00:00Z")) == END[later]


def test_c9a_10_only_version_two_covers_unit_9() -> None:
    g = _example("property-endorsement")
    scopes = {v: {s for r in g.subjects(INS.obligor, END["insurer-occ"])
                  if (g.value(g.value(r, INS.arisesUnder), INS.boundIn)) == v
                  for c in g.objects(r, INS.scope) for s in g.objects(c, ELG.requiredConcept)}
              for v in (END["policy-v1"], END["policy-v2"])}
    assert END["unit-9"] not in scopes[END["policy-v1"]] and END["unit-9"] in scopes[END["policy-v2"]]


# ---- C9a-11 and C9a-12: a party leaving, ending by agreement --------------------

def test_c9a_11_a_released_guarantor_keeps_what_arose_before() -> None:
    g = _example("licence-amendments")
    bound_in = lambda r: g.value(g.value(r, INS.arisesUnder), INS.boundIn)
    guarantor = LIC["guarantor-occ"]
    assert {bound_in(r) for r in g.subjects(INS.obligor, guarantor)} == {LIC["licence-v1"]}
    assert guarantor not in set(g.objects(LIC["licence-v2"], INS.party))
    assert (LIC["release-guarantor"], INS.assentBy, guarantor) in g                    # it agreed its release


def test_c9a_12_ending_by_agreement_is_an_added_ending() -> None:
    g = _example("licence-amendments")
    assert (LIC["ended"], INS.ends, INS_VOC.TheInstrument) in g
    clause = g.value(LIC["term-1-2"], INS.expressedIn)
    assert (LIC["wording-v3"], WRD.includes, clause) in g
    assert (LIC["wording-v2"], WRD.includes, clause) not in g
    assert agreed(g, LIC["amendment-2"])[0] == _when("2028-10-25T10:00:00Z")


# ---- C9a-13: law I4 ---------------------------------------------------------------

def test_c9a_13_one_case_per_relation() -> None:
    g = _example("property-endorsement")
    for i, cls in enumerate(("Loss", "Premises")):
        b = END[f"binding-{i}"]
        g.add((b, RDF.type, ELG.EvidenceBinding)); g.add((b, ELG.subjectClass, END[cls]))
        g.add((b, ELG.bindsCondition, END["at-unit-7-or-9" if i == 0 else "at-unit-7"]))
    g.add((END["v2-indemnify"], INS.scope, END["at-unit-7"]))
    assert any(f == str(END["v2-indemnify"]) and m.startswith("I4") for f, m in _results(g))
    assert not any(f == str(END["v1-indemnify"]) and m.startswith("I4") for f, m in _results(g))


# ---- C9a-14: release -------------------------------------------------------------

def test_c9a_14_release_notes_and_versions() -> None:
    readme = (ONTOLOGY / "instrument" / "README.md").read_text()
    assert "- 0.15.0 (CCS C9a" in readme
    assert (ONTOLOGY / "instrument" / "shapes" / ".version").read_text().strip() == "0.7.0"
    register = (ONTOLOGY.parent / "docs" / "architecture" / "ontology-releases.md").read_text()
    for tag in ("instrument-v0.15.0", "instrument-vocab-v0.15.0", "instrument-shapes-v0.7.0"):
        assert f"| {tag} |" in register, tag
