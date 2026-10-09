# SPDX-License-Identifier: MPL-2.0

"""Instrument: terms in time (computable-contract-substrate C7b, ADR-A104 and
its 2026-10-05 addendum, ADR-A115). Row IDs are the C7b Validation Pack's.
Reasoner rows skip when the ADR-A83 harness jar is not built. Row C7b-20
(every diagram renders) is run in a browser, and recorded in the Validation
Pack."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import owlrl
import pytest
from pyshacl import validate
from rdflib import BNode, Graph, Namespace, URIRef
from rdflib.namespace import OWL, RDF, RDFS, SH

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "tools" / "mork_compilers" / "src"))

import literate_extract  # noqa: E402
from mork_compilers import reasoning  # noqa: E402

LATTICE = "https://www.nebularis.org/neuro-semantic/lattice/"
INS = Namespace(LATTICE + "instrument#")
INSV = Namespace(LATTICE + "instrument/vocab#")
BHV = Namespace(LATTICE + "behaviour#")
QNT = Namespace(LATTICE + "quantification#")
VOC = Namespace(LATTICE + "vocabulary#")
FND = Namespace(LATTICE + "foundation#")
SKOS = Namespace("http://www.w3.org/2004/02/skos/core#")
ONTOLOGY = ROOT / "ontology"
LAYER = ONTOLOGY / "instrument"
QLAYER = ONTOLOGY / "quantification"
SPEC, VOCAB = LAYER / "spec" / "instrument.ttl", LAYER / "vocab" / "instrument-vocab.ttl"
NEW = ["trial-reporting", "lease-expiry", "licence-survival", "service-renewal"]
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
QSHAPES = _graph(QLAYER / "shapes" / "constraints.ttl")
EVERY_SHAPE = _graph(*ALL_SHAPES)


def _ns(name: str) -> tuple[Namespace, Namespace]:
    base = f"https://example.org/lattice/instrument/{name}/"
    return Namespace(base), Namespace(base + "form/")


def _example(name: str) -> Graph:
    return _graph(LAYER / "examples" / f"{name}.ttl")


def _changed(name: str, add: str = "", remove: tuple = ()) -> Graph:
    g = _example(name)
    for s, p, o in remove:
        assert (s, p, o) in g or o is None, (s, p, o)
        g.remove((s, p, o))
    if add:
        ex, tmpl = _ns(name)
        g.parse(data=f"@prefix ins: <{INS}> .\n@prefix ins-voc: <{INSV}> .\n@prefix bhv: <{BHV}> .\n@prefix qnt: <{QNT}> .\n"
                     f"@prefix fnd: <{FND}> .\n@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .\n"
                     f"@prefix ex: <{ex}> .\n@prefix tmpl: <{tmpl}> .\n" + add, format="turtle")
    return g


def _messages(data: Graph, shapes: Graph = SHAPES) -> list[tuple[str, str]]:
    _, report, _ = validate(MODEL + data, shacl_graph=shapes, inference="none", advanced=True)
    return [(str(report.value(r, SH.focusNode)), str(report.value(r, SH.resultMessage)))
            for r in report.subjects(SH.resultSeverity, SH.Violation)]


def _reported(data: Graph, focus: str, fragment: str, shapes: Graph = SHAPES) -> bool:
    return any(f.endswith(focus) and fragment in m for f, m in _messages(data, shapes))


needs_reasoner = pytest.mark.skipif(not reasoning.available(), reason="reasoning-testkit jar not built")
TR_EX, TR = _ns("trial-reporting")
LE_EX, LE = _ns("lease-expiry")
LS_EX, LS = _ns("licence-survival")


# ---- C7b-01: the spec -------------------------------------------------------

def test_c7b_01_version_imports_and_new_terms() -> None:
    spec = _graph(SPEC)
    ontology = URIRef("https://www.nebularis.org/neuro-semantic/instrument")
    assert spec.value(ontology, OWL.versionIRI) == URIRef(LATTICE + "instrument/0.16.0")
    assert URIRef(LATTICE + "quantification/0.7.0") in set(spec.objects(ontology, OWL.imports))
    for name in ("due", "recurrence", "window", "dueTolledIn", "at", "ofState", "ends", "survives", "survivalPeriod",
                 "survivesUntil"):
        utility = str(spec.value(INS[name], FND.utility))
        assert "Subject:" in utility and "Value:" in utility, name
    restriction = [r for r in spec.objects(INS.OnEntry, RDFS.subClassOf) if isinstance(r, BNode)]
    assert [spec.value(r, OWL.hasValue) for r in restriction] == [BHV.DerivedTrigger]
    assert spec.value(INS.ofState, RDFS.domain) == INS.OnEntry
    for name in ("due", "recurrence", "window", "at", "ends", "survives"):
        assert spec.value(INS[name], RDFS.domain) is None, name


# ---- C7b-02, C7b-03: the examples -------------------------------------------

@pytest.mark.parametrize("name", NEW)
def test_c7b_02_examples_conform_to_every_layer(name: str) -> None:
    assert _messages(_example(name), EVERY_SHAPE) == []


def test_c7b_02_quantification_example_conforms() -> None:
    # Quantification's own model: with Instrument's vocab beside it, its role binding and Instrument's
    # would conflict on one contract (held design question HQ-4).
    data = _graph(QLAYER / "examples" / "context-anchor.ttl")
    model = _graph(*[ONTOLOGY / p for p in LOWER[:4]])
    _, report, _ = validate(model + data, shacl_graph=EVERY_SHAPE, inference="none", advanced=True)
    assert not list(report.subjects(SH.resultSeverity, SH.Violation))


@needs_reasoner
@pytest.mark.parametrize("name", NEW)
def test_c7b_03_examples_are_consistent(name: str) -> None:
    assert reasoning.run("consistent", graphs=[MODEL, _example(name)]) is True


# ---- C7b-04 to C7b-07: due ranges, windows, recurrences ---------------------

@pytest.mark.parametrize("add, remove, focus, message", [
    ("tmpl:enrolment ins:due ex:within-24-hours .", (), "/enrolment", "law I5"),
    ("tmpl:pay-fees ins:due ex:within-24-hours , ex:within-10-business-days .", (), "/pay-fees", "at most one due range"),
    ("ex:fixed a qnt:Range ; qnt:onSpace ex:time . tmpl:pay-fees ins:due ex:fixed .", (), "/pay-fees", "law I9"),
    ("ex:literal a qnt:Range ; qnt:onSpace ex:time ; qnt:relativeToAnchor [ a qnt:AnchorBinding ; qnt:offsetKind qnt:Absolute ; "
     "qnt:anchorValue [ a qnt:Quantity ; qnt:onSpace ex:time ; qnt:numericValue \"2027-01-01T00:00:00Z\"^^xsd:dateTime ] ] . "
     "tmpl:pay-fees ins:due ex:literal .", (), "/pay-fees", "law I9"),
    ("ex:bare a qnt:Recurrence ; qnt:anchor [ a qnt:Quantity ; qnt:onSpace ex:time ; qnt:numericValue \"2027-01-01T00:00:00Z\"^^xsd:dateTime ] . "
     "tmpl:pay-fees ins:recurrence ex:bare .", (), "/pay-fees", "law I9"),
    ("tmpl:report-sae ins:window ex:within-24-hours .", (), "/report-sae", "Only a power or a permission has a window"),
    ("tmpl:pay-fees ins:dueTolledIn tmpl:pay-fees .", (), "/pay-fees", "Only an obligation with a due range"),
])
def test_c7b_04_to_07_time_shapes_report(add: str, remove: tuple, focus: str, message: str) -> None:
    assert _reported(_changed("trial-reporting", add, remove), focus, message)


# ---- C7b-08, C7b-09: ending and survival ------------------------------------

def test_c7b_08_ends_on_a_plain_state_or_a_bound_term() -> None:
    plain = _changed("licence-survival", "tmpl:plain a bhv:StateSpace ; fnd:hasIdentity tmpl:plain-identity . "
                     "tmpl:plain-end a bhv:State ; bhv:inStateSpace tmpl:plain ; ins:ends ins-voc:TheInstrument .")
    assert _reported(plain, "/plain-end", "is not a state of an ins:Regime")
    bound = _changed("licence-survival", "tmpl:terminated ins:ends ex:term-13-1 .")
    assert _reported(bound, "/terminated", "the instrument (ins-voc:TheInstrument) or stated terms")


def test_c7b_09_survival_shapes() -> None:
    not_quantity = _changed("licence-survival", "ex:s a ins:Survival ; ins:survivalPeriod ex:ending . tmpl:term-11-1 ins:survives ex:s .")
    assert _reported(not_quantity, "/s", "one quantity of time")
    on_bound = _changed("licence-survival", "ex:term-11-4 ins:survives [ a ins:Survival ] .")
    assert _reported(on_bound, "/term-11-4", "Only a stated term survives")


# ---- C7b-10: stated and bound name the same anchored time -------------------

def test_c7b_10_bound_relations_restate_their_time() -> None:
    data = _example("trial-reporting")
    for stated, bound in ((TR["report-sae"], TR_EX["report-sae"]), (TR["safety-report"], TR_EX["safety-report"])):
        assert data.value(stated, INS.due) == data.value(bound, INS.due) is not None
        assert data.value(stated, INS.recurrence) == data.value(bound, INS.recurrence)
    assert data.value(TR["pay-fees"], INS.due) is None


# ---- C7b-11: the new trigger with a reasoner (C7a-R1) -----------------------

def test_c7b_11_on_entry_from_its_property_alone() -> None:
    data = _example("licence-survival")
    trigger = LS["on-termination"]
    for cls in (INS.OnEntry, BHV.TriggerDefinition):
        data.remove((trigger, RDF.type, cls))
    data.remove((trigger, BHV.triggerKind, None))
    closed = Graph()
    closed += _graph(SPEC, ONTOLOGY / "behaviour" / "spec" / "behaviour.ttl")
    closed += data
    owlrl.DeductiveClosure(owlrl.OWLRL_Semantics).expand(closed)
    assert {INS.OnEntry, BHV.TriggerDefinition} <= set(closed.objects(trigger, RDF.type))
    assert set(closed.objects(trigger, BHV.triggerKind)) == {BHV.DerivedTrigger}


# ---- C7b-12: the vocab ------------------------------------------------------

def test_c7b_12_context_roles_and_ending() -> None:
    vocab = _graph(VOCAB)
    binding = vocab.value(None, VOC.bindsScheme, INSV.ContextRoles)
    assert vocab.value(binding, VOC.forContract) == QNT.ContextRoleContract
    roles = set(vocab.subjects(SKOS.inScheme, INSV.ContextRoles))
    assert roles == {INSV[r] for r in ("Arising", "Inception", "Ending", "PeriodStart", "PeriodEnd")}
    used = set()
    for name in NEW:
        used |= {r for r in _example(name).objects(None, QNT.contextRole) if str(r).startswith(str(INSV))}
    assert used and used <= roles
    assert (INSV.Expired, SKOS.inScheme, INSV.StateKinds) in vocab
    assert (INSV.TheInstrument, RDF.type, SKOS.Concept) in vocab


# ---- C7b-13, C7b-15: literate sources and release notes ---------------------

def test_c7b_13_instrument_readme_and_releases() -> None:
    assert literate_extract.main([str(LAYER / "README.md"), "--layer", "instrument", "--root", str(ROOT), "--shapes",
                                  "shapes/structural.ttl", "shapes/constraints.ttl", "shapes/single-expression.ttl",
                                  "--check"]) == 0
    readme = (LAYER / "README.md").read_text()
    assert "0.11.0 (CCS C7b" in readme and "Shapes 0.4.0 (additive" in readme and "0.12.0 (breaking, CCS C7c" in readme
    assert (LAYER / "shapes" / ".version").read_text().strip() == "0.8.0"


def test_c7b_15_quantification_readme_is_the_source() -> None:
    assert literate_extract.main([str(QLAYER / "README.md"), "--layer", "quantification", "--root", str(ROOT),
                                  "--shapes", "shapes/constraints.ttl", "--check"]) == 0
    spec = _graph(QLAYER / "spec" / "quantification.ttl")
    assert spec.value(URIRef("https://www.nebularis.org/neuro-semantic/quantification"), OWL.versionIRI) == \
        URIRef(LATTICE + "quantification/0.7.0")
    assert "**0.7.0** (additive, CCS C7b" in (QLAYER / "README.md").read_text()
    assert (QLAYER / "shapes" / ".version").read_text().strip() == "0.2.0"


# ---- C7b-16: Quantification's shapes ----------------------------------------

def test_c7b_16_context_value_and_offset_shapes() -> None:
    source = (QLAYER / "examples" / "context-anchor.ttl").read_text()
    both = source.replace("qnt:offsetKind qnt:Absolute ;", 'qnt:offsetKind qnt:Absolute ; qnt:lowerOffset "1"^^xsd:decimal ;')
    assert any("never both" in m for _, m in _messages(_graph(both), QSHAPES))
    no_role = source.replace("    qnt:contextRole ex:renewal .", "    .")
    assert any("exactly one role" in m for _, m in _messages(_graph(no_role), QSHAPES))


# ---- C7b-17: the cascade ----------------------------------------------------

def test_c7b_17_nothing_still_imports_quantification_0_6_0() -> None:
    found = subprocess.run(["git", "grep", "-l", "-F", LATTICE + "quantification/0.6.0", "--", "ontology", "tools"],
                           cwd=ROOT, capture_output=True, text=True).stdout.split()
    assert [f for f in found if not f.endswith("catalog-v001.xml") and "fixtures/import_guard" not in f] == []


# ---- C7b-18, C7b-19: expiry, entry and implicit survival --------------------

@pytest.mark.parametrize("add, remove, focus, message", [
    ("tmpl:on-expiry-date ins:after [ a qnt:Quantity ; qnt:onSpace ex:durations ; qnt:numericValue \"1\"^^xsd:decimal ; qnt:inUnit ex:day ] .",
     (), "/on-expiry-date", "exactly one of a length"),
    ("", ((LE["on-expiry-date"], INS.at, LE_EX["expiry-date"]),), "/on-expiry-date", "exactly one of a length"),
    ("", ((LE["on-expired"], INS.ofState, LE["expired"]),), "/on-expired", "exactly one state"),
])
def test_c7b_18_expiry_and_entry_shapes(add: str, remove: tuple, focus: str, message: str) -> None:
    assert _reported(_changed("lease-expiry", add, remove), focus, message)


def test_c7b_19_termination_consequence_needs_no_survival() -> None:
    data = _example("lease-expiry")
    assert data.value(LE["term-12-1"], INS.survives) is None
    assert not [m for f, m in _messages(data) if f.endswith("repay-deposit") or f.endswith("term-12-1")]
