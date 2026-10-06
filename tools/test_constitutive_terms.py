# SPDX-License-Identifier: MPL-2.0

"""Instrument: what terms are, and whom they bind (computable-contract-substrate
C7c, ADR-A104 and its 2026-10-06 addendum). Row IDs are the C7c Validation
Pack's. Reasoner rows skip when the ADR-A83 harness jar is not built. Row C7c-16
(every diagram renders) is run in a browser, and C7c-17 and C7c-18 by the
existing tests and checks; both are recorded in the Validation Pack."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
from pyshacl import validate
from rdflib import Graph, Namespace, URIRef
from rdflib.namespace import OWL, RDF, RDFS, SH

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "tools" / "mork_compilers" / "src"))

import literate_extract  # noqa: E402
from mork_compilers import reasoning  # noqa: E402

LATTICE = "https://www.nebularis.org/neuro-semantic/lattice/"
INS = Namespace(LATTICE + "instrument#")
INSV = Namespace(LATTICE + "instrument/vocab#")
PTY = Namespace(LATTICE + "party#")
FND = Namespace(LATTICE + "foundation#")
WRD = Namespace(LATTICE + "wording#")
ONTOLOGY = ROOT / "ontology"
LAYER = ONTOLOGY / "instrument"
SPEC, VOCAB = LAYER / "spec" / "instrument.ttl", LAYER / "vocab" / "instrument-vocab.ttl"
NEW = ["framework-lots", "service-towers", "facility-definitions", "trial-definitions", "supply-classification"]
LOWER = ["foundation/spec/foundation.ttl", "vocabulary/spec/vocabulary.ttl", "quantification/spec/quantification.ttl",
         "quantification/vocab/quantification-vocab.ttl", "party/spec/party.ttl", "party/vocab/party-vocab.ttl",
         "eligibility/spec/eligibility.ttl", "eligibility/vocab/eligibility-vocab.ttl", "wording/spec/wording.ttl",
         "wording/vocab/wording-vocab.ttl", "behaviour/spec/behaviour.ttl", "behaviour/vocab/behaviour-vocab.ttl",
         "foundation/examples/keys.ttl"]
ALL_SHAPES = [ONTOLOGY / layer / "shapes" / f"{kind}.ttl"
              for layer in ("foundation", "vocabulary", "quantification", "party", "eligibility", "wording", "behaviour",
                            "instrument")
              for kind in ("structural", "constraints")]


def _graph(*sources) -> Graph:
    g = Graph()
    for source in sources:
        g.parse(source) if isinstance(source, Path) else g.parse(data=source, format="turtle")
    return g


MODEL = _graph(*[ONTOLOGY / p for p in LOWER], SPEC, VOCAB)
SHAPES = _graph(LAYER / "shapes" / "structural.ttl", LAYER / "shapes" / "constraints.ttl")
EVERY_SHAPE = _graph(*ALL_SHAPES)
NS = {"framework-lots": "framework", "service-towers": "service-towers", "facility-definitions": "facility-definitions",
      "trial-definitions": "trial-definitions", "supply-classification": "supply-classification"}


def _ns(name: str) -> tuple[Namespace, Namespace]:
    base = f"https://example.org/lattice/instrument/{NS[name]}/"
    return Namespace(base), Namespace(base + "form/")


def _example(name: str) -> Graph:
    return _graph(LAYER / "examples" / f"{name}.ttl")


def _changed(name: str, add: str = "", remove: tuple = ()) -> Graph:
    g = _example(name)
    for s, p, o in remove:
        assert (s, p, o) in g, (s, p, o)
        g.remove((s, p, o))
    if add:
        ex, tmpl = _ns(name)
        g.parse(data=f"@prefix ins: <{INS}> .\n@prefix ins-voc: <{INSV}> .\n@prefix pty: <{PTY}> .\n"
                     f"@prefix elg: <{LATTICE}eligibility#> .\n@prefix owl: <http://www.w3.org/2002/07/owl#> .\n"
                     f"@prefix ex: <{ex}> .\n@prefix tmpl: <{tmpl}> .\n" + add, format="turtle")
    return g


def _results(data: Graph, shapes: Graph = SHAPES, severity=SH.Violation) -> list[tuple[str, str]]:
    _, report, _ = validate(MODEL + data, shacl_graph=shapes, inference="none", advanced=True)
    return [(str(report.value(r, SH.focusNode)), str(report.value(r, SH.resultMessage)))
            for r in report.subjects(SH.resultSeverity, severity)]


def _reported(data: Graph, focus: str, fragment: str, severity=SH.Violation) -> bool:
    return any(f.endswith(focus) and fragment in m for f, m in _results(data, SHAPES, severity))


needs_reasoner = pytest.mark.skipif(not reasoning.available(), reason="reasoning-testkit jar not built")
FW_EX, FW = _ns("framework-lots")
ST_EX, ST = _ns("service-towers")
FD_EX, FD = _ns("facility-definitions")
TD_EX, TD = _ns("trial-definitions")
SC_EX, SC = _ns("supply-classification")


# ---- C7c-01: the spec, and Party made domain-neutral ------------------------

def test_c7c_01_version_imports_and_new_terms() -> None:
    spec = _graph(SPEC)
    ontology = URIRef("https://www.nebularis.org/neuro-semantic/instrument")
    assert spec.value(ontology, OWL.versionIRI) == URIRef(LATTICE + "instrument/0.14.0")
    assert {str(i) for i in spec.objects(ontology, OWL.imports)} == {LATTICE + v for v in (
        "foundation/0.4.0", "vocabulary/0.4.0", "quantification/0.7.0", "party/0.8.0", "eligibility/0.10.0",
        "wording/0.7.0", "behaviour/0.13.0")}
    for name in ("defines", "means", "actingRule", "prevailsOver", "deems", "when", "conclusive", "forPurposeOf",
                 "classification", "section", "appliesWithin", "notWithin", "boundWithin", "boundUnder", "resolvedBy",
                 "resolvesFrom", "resolutionStep", "resolutionFilter"):
        utility = str(spec.value(INS[name], URIRef(LATTICE + "foundation#utility")))
        assert "Subject:" in utility and "Value:" in utility, name
    for name in ("scope", "maintains", "condition"):          # a word may stand there on stated meaning (D12)
        assert spec.value(INS[name], RDFS.range) is None, name
    assert (INS.qualifies, RDF.type, OWL.FunctionalProperty) not in spec  # a bound qualifier spans sections (D10)


def test_c7c_01_party_is_domain_neutral() -> None:
    party = _graph(ONTOLOGY / "party" / "spec" / "party.ttl", ONTOLOGY / "party" / "vocab" / "party-vocab.ttl")
    assert (PTY.outwardShare, RDF.type, OWL.DatatypeProperty) in party
    assert (PTY.inwardShare, RDF.type, OWL.DatatypeProperty) in party
    assert (PTY.EachForOwnShare, RDF.type, PTY.CompositionRule) in party
    assert (PTY.EachForWhole, RDF.type, PTY.CompositionRule) in party
    assert not any(PTY.share in t or PTY.SeveralOnly in t or PTY.JointAndSeveral in t for t in party)
    found = subprocess.run(["git", "grep", "-l", "-E", r"pty:(share\b|SeveralOnly|JointAndSeveral)", "--", "ontology",
                            "tools"], cwd=ROOT, capture_output=True, text=True).stdout.split()
    assert found == []


# ---- C7c-02, C7c-03: the examples -------------------------------------------

@pytest.mark.parametrize("name", NEW)
def test_c7c_02_examples_conform_to_every_layer(name: str) -> None:
    assert _results(_example(name), EVERY_SHAPE) == []


def test_c7c_02_the_only_warning_is_the_lot_2_overlap() -> None:
    warnings = [w for name in NEW for w in _results(_example(name), EVERY_SHAPE, SH.Warning)
                if "law I16" in w[1] and not w[1].startswith("On the form")]   # C8 adds the form's and coverage
    assert len(warnings) == 1
    focus, message = warnings[0]
    assert focus == str(FW_EX["def-s1-1"]) and "def-s1-2" in message and "lot-2-identity" in message


@needs_reasoner
@pytest.mark.parametrize("name", NEW)
def test_c7c_03_examples_are_consistent(name: str) -> None:
    assert reasoning.run("consistent", graphs=[MODEL, _example(name)]) is True


# ---- C7c-04: definitions and deemings ---------------------------------------

@pytest.mark.parametrize("add, remove, focus, message", [
    ("", ((FD["def-obligors"], INS.defines, FD_EX.Obligor),), "/def-obligors", "exactly one word"),
    ("", ((FD["def-mae"], INS.means, FD_EX.mae),), "/def-mae", "at least one thing"),
    ("tmpl:deemed-receipt ins:deems ex:delivered-by-hand .", (), "/deemed-receipt", "exactly one condition"),
    ("tmpl:def-mae ins:defines ex:Borrower .", (), "/def-mae", "exactly one word"),
])
def test_c7c_04_definition_and_deeming_shapes(add: str, remove: tuple, focus: str, message: str) -> None:
    assert _reported(_changed("facility-definitions", add, remove), focus, message)


def test_c7c_04_a_bound_definition_names_no_role_and_a_bound_trigger_no_word() -> None:
    assert _reported(_changed("facility-definitions", "ex:def-obligors ins:means ex:Borrower ."), "/def-obligors",
                     "never roles or words")
    assert _reported(_changed("service-towers", "ex:service-credit-in-tower-a ins:scope ex:ServiceFailure ."),
                     "/service-credit-in-tower-a", "never roles or words")


def test_c7c_04_an_undefined_word_is_reported() -> None:
    data = _changed("facility-definitions", "ex:Undefined a <http://www.w3.org/2004/02/skos/core#Concept> . "
                                            "tmpl:on-mae ins:condition ex:Undefined .",
                    ((FD["on-mae"], INS.condition, FD_EX.MaterialAdverseEffect),))
    assert _reported(data, "/on-mae", "defined word")


# ---- C7c-05: scopes and declared sections -----------------------------------

@pytest.mark.parametrize("add, remove, focus, message", [
    ("tmpl:term-s1-2 ins:appliesWithin ex:lot-2 .", ((FW["term-s1-2"], INS.appliesWithin, FW_EX["lot-2-identity"]),),
     "/term-s1-2", "never an element version"),
    ("tmpl:lots ins:section ex:lot-1 .", (), "/lots", "never an element version"),
    ("tmpl:term-3-1 ins:notWithin ex:sch-1-identity .", (), "/term-3-1", "lies below none"),
    ("ex:term-3-1-in-lot-3 ins:appliesWithin ex:lot-3-identity .", (), "/term-3-1-in-lot-3", "Only a stated term"),
])
def test_c7c_05_scope_shapes(add: str, remove: tuple, focus: str, message: str) -> None:
    assert _reported(_changed("framework-lots", add, remove), focus, message)


def test_c7c_05_a_declared_section_must_be_included() -> None:
    data = _changed("framework-lots", "", ((FW_EX["framework-wording-v1"], WRD.includes, FW_EX["lot-4"]),))
    assert _reported(data, "/framework-v1", "lot-4-identity")


def test_c7c_05_a_scope_cutting_through_a_section_is_a_warning() -> None:
    data = _changed("service-towers", "tmpl:term-6-1 ins:appliesWithin ex:cl-b-1-identity .")
    assert _reported(data, "/term-6-1", "inside the declared section", SH.Warning)


# ---- C7c-06, C7c-07: a case's section (I15) ---------------------------------

def test_c7c_06_a_call_off_falls_in_its_award_power_s_lot() -> None:
    g = _example("framework-lots")
    for calloff, lot in (("calloff-0042-v1", "lot-2-identity"), ("calloff-0057-v1", "lot-3-identity")):
        rows = g.query(f"SELECT ?s WHERE {{ <{FW_EX[calloff]}> <{INS.boundUnder}>/<{INS.arisesUnder}>/<{INS.boundWithin}> ?s }}")
        assert [str(r.s) for r in rows] == [str(FW_EX[lot])]


def test_c7c_07_a_power_bound_within_two_sections_is_reported() -> None:
    data = _changed("framework-lots", "ex:term-l2-1 ins:boundWithin ex:lot-1-identity .")
    assert _reported(data, "/calloff-0042-v1", "law I15")


# ---- C7c-08, C7c-09: overlapping definitions (I16) --------------------------

def test_c7c_08_an_overlap_meaning_different_parties_is_one_warning() -> None:
    data = _changed("framework-lots", "ex:def-s1-2 ins:means ex:birch-occ .",
                    ((FW_EX["def-s1-2"], INS.means, FW_EX["ash-occ"]),))
    warnings = [w for w in _results(data, SHAPES, SH.Warning) if "law I16" in w[1] and not w[1].startswith("On the form")]
    assert len(warnings) == 1 and "lot-2-identity" in warnings[0][1]


def test_c7c_09_a_prevailing_definition_removes_the_warning() -> None:
    data = _changed("framework-lots", "ex:def-s1-2 ins:prevailsOver ex:def-s1-1 .")
    assert [w for w in _results(data, SHAPES, SH.Warning) if "law I16" in w[1] and not w[1].startswith("On the form")] == []


def test_c7c_09_conflicting_acting_rules_are_a_violation() -> None:
    data = _changed("framework-lots", "ex:def-s1-1 ins:actingRule pty:EachForWhole . "
                                      "ex:def-s1-2 ins:actingRule pty:EachForOwnShare .")
    assert any("conflicting acting rules" in m for _, m in _results(data))


def test_c7c_09_an_acting_rule_disagreeing_with_its_group_is_reported() -> None:
    data = _changed("framework-lots", "", ((FW_EX["lot-3-suppliers"], PTY.hasCompositionRule, PTY.EachForWhole),))
    assert _reported(data, "/def-s1-3", "does not")


# ---- C7c-10, C7c-11: party resolution and silent groups ---------------------

@pytest.mark.parametrize("add, remove, focus, message", [
    ("ex:age a owl:DatatypeProperty . ex:participant-resolution ins:resolutionStep "
     "[ a elg:EvidenceStep ; elg:stepIndex 1 ; elg:stepProperty ex:age ; elg:stepDirection elg:Forward ] .",
     (), "/participant-resolution", "never literals"),
    ("ex:participant-resolution ins:resolutionFilter ex:site-inactive .", (), "/participant-resolution",
     "at most one condition"),
    ("ex:participant-occ pty:occupiedBy ex:halcyon .", (), "/participant-occ", "contingent"),
])
def test_c7c_10_party_resolution_shapes(add: str, remove: tuple, focus: str, message: str) -> None:
    assert _reported(_changed("trial-definitions", add, remove), focus, message)


def test_c7c_10_a_resolution_with_no_step_is_reported() -> None:
    g = _example("trial-definitions")
    step = g.value(TD_EX["participant-resolution"], INS.resolutionStep)
    g.remove((TD_EX["participant-resolution"], INS.resolutionStep, step))
    assert _reported(g, "/participant-resolution", "at least one Eligibility step")


def test_c7c_11_a_silent_group_conforms_and_the_readme_says_undetermined() -> None:
    data = _changed("framework-lots", "", ((FW["def-s1-3"], INS.actingRule, PTY.EachForWhole),
                                          (FW_EX["def-s1-3"], INS.actingRule, PTY.EachForWhole),
                                          (FW_EX["lot-3-suppliers"], PTY.hasCompositionRule, PTY.EachForWhole)))
    assert _results(data) == []
    assert "with no acting rule is silent, and the relations it reaches are Undetermined (CC-D10)" in \
        (LAYER / "README.md").read_text()


# ---- C7c-12 to C7c-14: classification, ending a section, precedence ---------

def test_c7c_12_a_classification_outside_the_bound_scheme_is_reported() -> None:
    data = _changed("supply-classification", "tmpl:term-6-1 ins:classification ex:conforming .")
    assert _reported(data, "/term-6-1", "TermClassificationContract")
    assert _reported(_changed("supply-classification", "ex:term-6-1 ins:classification ex:condition ."),
                     "/term-6-1", "Only a stated term is classified")


def test_c7c_13_ending_a_section() -> None:
    assert _results(_example("framework-lots")) == []
    data = _changed("framework-lots", "tmpl:lot-4-withdrawn ins:ends ex:cl-3-1-identity .")
    assert _reported(data, "/lot-4-withdrawn", "only a section ends this way")
    data = _changed("framework-lots", "tmpl:lot-4-withdrawn ins:ends ex:lot-4 .")
    assert _reported(data, "/lot-4-withdrawn", "or a section by its persistent identity")


def test_c7c_14_prevails_over_between_relations_is_reported() -> None:
    data = _changed("framework-lots", "tmpl:provide-services ins:prevailsOver tmpl:deliver-goods .")
    assert _reported(data, "/provide-services", "Only a definition prevails")


# ---- C7c-15: literate source and release notes ------------------------------

def test_c7c_15_readme_is_the_source_and_releases_are_recorded() -> None:
    assert literate_extract.main([str(LAYER / "README.md"), "--layer", "instrument", "--root", str(ROOT), "--shapes",
                                  "shapes/structural.ttl", "shapes/constraints.ttl", "shapes/single-expression.ttl",
                                  "--check"]) == 0
    readme = (LAYER / "README.md").read_text()
    assert "0.12.0 (breaking, CCS C7c" in readme and "Shapes 0.5.0" in readme
    assert (LAYER / "shapes" / ".version").read_text().strip() == "0.6.0"
    register = (ROOT / "docs" / "architecture" / "ontology-releases.md").read_text()
    for tag in ("instrument-v0.12.0", "instrument-shapes-v0.5.0", "instrument-vocab-v0.12.0", "party-v0.8.0",
                "party-vocab-v0.8.0", "eligibility-v0.10.0", "behaviour-v0.13.0", "wording-v0.6.0"):
        assert tag in register, tag
    vocab = _graph(VOCAB)
    assert (INSV.TermClassificationContract, URIRef(LATTICE + "vocabulary#constrainsProperty"), INS.classification) in vocab
    assert (INSV.Award, URIRef("http://www.w3.org/2004/02/skos/core#inScheme"), INSV.Activities) in vocab


# ---- C7c-19 to C7c-22: binding per section, and what is shared --------------

def _supplier_in(g: Graph, section: URIRef) -> frozenset:
    """What "the Supplier" resolves to within a section: the union of the bound definitions applying there."""
    return frozenset(m for d in g.subjects(INS.defines, FW_EX.Supplier) if (d, RDF.type, INS.Template) not in g
                     for m in g.objects(d, INS.means)
                     if (g.value(d, INS.arisesUnder), INS.boundWithin, section) in g)


def test_c7c_19_sections_resolving_alike_share_one_bound_term() -> None:
    g = _example("framework-lots")
    bound = [t for t in g.subjects(INS.boundFrom, FW["term-3-1"])]
    assert len(bound) == 2
    groups = [frozenset(g.objects(t, INS.boundWithin)) for t in bound]
    assert set().union(*groups) == {FW_EX["lot-1-identity"], FW_EX["lot-2-identity"], FW_EX["lot-3-identity"]}
    assert not groups[0] & groups[1]
    for sections in groups:                       # within a bound term, every section resolves the word alike
        assert len({_supplier_in(g, s) for s in sections}) == 1
    assert _supplier_in(g, next(iter(groups[0]))) != _supplier_in(g, next(iter(groups[1])))


def test_c7c_19_one_stated_term_never_binds_a_section_twice() -> None:
    data = _changed("framework-lots", "ex:extra a ins:Term ; ins:boundIn ex:framework-v1 ; ins:boundFrom tmpl:term-3-1 ; "
                                      "ins:boundWithin ex:lot-2-identity .")
    assert _reported(data, "/extra", "never binds one section twice")


def test_c7c_20_a_cross_section_cap_is_bound_once() -> None:
    g = _example("service-towers")
    caps = list(g.subjects(INS.boundFrom, ST["credit-cap"]))
    credits = set(g.subjects(INS.boundFrom, ST["service-credit"]))
    assert len(caps) == 1 and len(credits) == 3
    assert set(g.objects(caps[0], INS.qualifies)) == credits
    data = _changed("service-towers", "tmpl:credit-cap ins:qualifies tmpl:pay-charges .")
    assert _reported(data, "/credit-cap", "A stated qualifier qualifies exactly one")


def test_c7c_21_an_incident_in_two_towers_is_placed_in_neither() -> None:
    g = _example("service-towers")
    conditions = {str(g.value(t, INS.condition)).rsplit("/", 1)[-1]: t
                  for r in g.subjects(INS.boundFrom, ST["service-credit"]) for t in g.objects(r, INS.arisesOn)}
    assert set(conditions) == {"p1-unresolved", "dc-unavailable", "latency-breach"}
    assert not list(g.predicate_objects(ST_EX["incident-0311"])) or \
        all(p in (RDF.type, RDFS.label) for p, _ in g.predicate_objects(ST_EX["incident-0311"]))


@pytest.mark.parametrize("name", NEW)
def test_c7c_22_stated_meaning_is_context_free(name: str) -> None:
    # Stated meaning names no element version except through ins:expressedIn, and no instrument, so a
    # wording matched on its hash brings its stated meaning with it (D2, D3).
    g = MODEL + _example(name)
    rows = g.query(f"""
        SELECT ?s ?p ?o WHERE {{
            ?s a <{INS.Template}> ; ?p ?o .
            FILTER (?p != <{INS.expressedIn}>)
            {{ ?o a/<{RDFS.subClassOf}>* <{WRD.Element}> }} UNION {{ ?o a <{INS.Instrument}> }}
        }}""")
    assert list(rows) == []
