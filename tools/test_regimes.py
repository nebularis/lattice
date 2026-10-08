# SPDX-License-Identifier: MPL-2.0

"""Instrument: legal triggers, regimes and gating (computable-contract-substrate
C7a, ADR-A104 and its 2026-10-04 addendum). Row IDs are the C7a Validation
Pack's. Reasoner rows skip when the ADR-A83 harness jar is not built. The OWL 2
RL rows (C7a-15 to C7a-18) use owlrl, which pySHACL already depends on."""

from __future__ import annotations

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
VOC = Namespace(LATTICE + "vocabulary#")
FND = Namespace(LATTICE + "foundation#")
SKOS = Namespace("http://www.w3.org/2004/02/skos/core#")
ONTOLOGY = ROOT / "ontology"
LAYER = ONTOLOGY / "instrument"
SPEC, VOCAB = LAYER / "spec" / "instrument.ttl", LAYER / "vocab" / "instrument-vocab.ttl"
EXAMPLES = sorted((LAYER / "examples").glob("*.ttl"))
REGIME_EXAMPLES = [LAYER / "examples" / f"{name}.ttl"
                   for name in ("licence-notice", "supply-suspension", "facility-cure-period", "service-dispute")]
LOWER = ["foundation/spec/foundation.ttl", "vocabulary/spec/vocabulary.ttl", "quantification/spec/quantification.ttl",
         "quantification/vocab/quantification-vocab.ttl", "party/spec/party.ttl", "party/vocab/party-vocab.ttl",
         "eligibility/spec/eligibility.ttl", "eligibility/vocab/eligibility-vocab.ttl", "wording/spec/wording.ttl",
         "wording/vocab/wording-vocab.ttl", "behaviour/spec/behaviour.ttl", "behaviour/vocab/behaviour-vocab.ttl",
         "foundation/examples/keys.ttl"]
ALL_SHAPES = [ONTOLOGY / layer / "shapes" / f"{kind}.ttl"
              for layer in ("foundation", "vocabulary", "quantification", "party", "eligibility", "wording", "behaviour",
                            "instrument")
              for kind in ("structural", "constraints")]
TRIGGERS = (INS.OnExercise, INS.OnBreach, INS.OnAct, INS.OnCondition, INS.OnExpiry)
FIXED_KIND = {INS.OnExercise: BHV.ExternalStimulus, INS.OnAct: BHV.ExternalStimulus, INS.OnBreach: BHV.DerivedTrigger,
              INS.OnCondition: BHV.DerivedTrigger, INS.OnExpiry: BHV.ScheduledTrigger}


def _graph(*sources) -> Graph:
    g = Graph()
    for source in sources:
        if isinstance(source, Path):
            g.parse(source)
        else:
            g.parse(data=source, format="turtle")
    return g


MODEL = _graph(*[ONTOLOGY / p for p in LOWER], SPEC, VOCAB)
SHAPES = _graph(LAYER / "shapes" / "structural.ttl", LAYER / "shapes" / "constraints.ttl")
EVERY_SHAPE = _graph(*ALL_SHAPES)
# The closure's axioms: Instrument's and Behaviour's specs (§12). The other layers are not closed.
AXIOMS = _graph(SPEC, ONTOLOGY / "behaviour" / "spec" / "behaviour.ttl")


def _example(name: str) -> Graph:
    return _graph(LAYER / "examples" / f"{name}.ttl")


def _ns(name: str) -> tuple[Namespace, Namespace]:
    base = f"https://example.org/lattice/instrument/{name}/"
    return Namespace(base), Namespace(base + "form/")


def _prefixes(name: str) -> str:
    ex, tmpl = _ns(name)
    return (f"@prefix ins: <{INS}> .\n@prefix ins-voc: <{INSV}> .\n@prefix bhv: <{BHV}> .\n@prefix fnd: <{FND}> .\n"
            f"@prefix ex: <{ex}> .\n@prefix tmpl: <{tmpl}> .\n")


def _changed(name: str, add: str = "", remove: tuple = ()) -> Graph:
    g = _example(name)
    for triple in remove:
        assert triple in g, triple
        g.remove(triple)
    if add:
        g.parse(data=_prefixes(name) + add, format="turtle")
    return g


def _messages(data: Graph, shapes: Graph = SHAPES) -> list[tuple[str, str]]:
    _, report, _ = validate(MODEL + data, shacl_graph=shapes, inference="none", advanced=True)
    return [(str(report.value(r, SH.focusNode)), str(report.value(r, SH.resultMessage)))
            for r in report.subjects(SH.resultSeverity, SH.Violation)]


def _reported(data: Graph, focus: str, fragment: str) -> bool:
    return any(f.endswith(focus) and fragment in m for f, m in _messages(data))


def _lean(data: Graph) -> Graph:
    """The example as an author with a reasoner writes it: no Behaviour type,
    policy or kind on any node with an Instrument regime or trigger type (§12.2)."""
    lean = Graph()
    lean += data
    instrument_typed = {s for t in (INS.Regime, INS.RegimeTransition, *TRIGGERS) for s in data.subjects(RDF.type, t)}
    for node in instrument_typed:
        for cls in (BHV.StateSpace, BHV.TransitionDefinition, BHV.TriggerDefinition):
            lean.remove((node, RDF.type, cls))
        for prop in (BHV.selectionPolicy, BHV.activationPolicy, BHV.triggerKind):
            lean.remove((node, prop, None))
    return lean


def _closed(data: Graph) -> Graph:
    closed = Graph()
    closed += AXIOMS
    closed += data
    owlrl.DeductiveClosure(owlrl.OWLRL_Semantics).expand(closed)
    return closed


needs_reasoner = pytest.mark.skipif(not reasoning.available(), reason="reasoning-testkit jar not built")
LN_EX, LN = _ns("licence-notice")
SD_EX, SD = _ns("service-dispute")
FC_EX, FC = _ns("facility-cure-period")


# ---- C7a-01: the spec -------------------------------------------------------

def test_c7a_01_version_imports_and_comments() -> None:
    spec = _graph(SPEC)
    ontology = URIRef("https://www.nebularis.org/neuro-semantic/instrument")
    assert spec.value(ontology, OWL.versionIRI) == URIRef(LATTICE + "instrument/0.14.0")
    assert set(spec.objects(ontology, OWL.imports)) == {URIRef(LATTICE + v) for v in (
        "foundation/0.4.0", "vocabulary/0.4.0", "quantification/0.7.0", "party/0.8.0", "eligibility/0.10.0",
        "wording/0.7.0", "behaviour/0.13.0")}
    new = ("ofPower", "ofObligation", "by", "condition", "after", "tolledIn", "stateKind", "appliesInState",
           "arisesOn", "arisesOnBreachOf", "arisesOnExerciseOf", "endsOn")
    for name in new:
        utility = str(spec.value(INS[name], FND.utility))
        assert "Subject:" in utility and "Value:" in utility, name
    assert "behaviour-runtime" not in SPEC.read_text()


def test_c7a_01_domains_follow_the_rule() -> None:
    spec = _graph(SPEC)
    assert spec.value(INS.activity, RDFS.domain) is None                      # C7a-Q2
    domains = {p: spec.value(INS[p], RDFS.domain) for p in ("ofPower", "ofObligation", "tolledIn")}
    assert domains == {"ofPower": INS.OnExercise, "ofObligation": INS.OnBreach, "tolledIn": INS.OnExpiry}
    for name in ("by", "condition", "after", "stateKind", "appliesInState", "arisesOn", "arisesOnBreachOf",
                 "arisesOnExerciseOf", "endsOn"):
        assert spec.value(INS[name], RDFS.domain) is None, name


def test_c7a_01_fixed_values_are_has_value_restrictions() -> None:
    spec = _graph(SPEC)

    def has_value(cls: URIRef, prop: URIRef) -> set:
        return {spec.value(r, OWL.hasValue) for r in spec.objects(cls, RDFS.subClassOf)
                if isinstance(r, BNode) and spec.value(r, OWL.onProperty) == prop}

    assert has_value(INS.RegimeTransition, BHV.selectionPolicy) == {BHV.SingleMatch}
    assert has_value(INS.RegimeTransition, BHV.activationPolicy) == {BHV.ImmediateActivation}
    for cls, kind in FIXED_KIND.items():
        assert has_value(cls, BHV.triggerKind) == {kind}, cls
        assert (cls, RDFS.subClassOf, BHV.TriggerDefinition) in spec
    assert (INS.Regime, RDFS.subClassOf, BHV.StateSpace) in spec
    assert not list(spec.subjects(OWL.allValuesFrom, None))


# ---- C7a-02, C7a-03: the examples -------------------------------------------

@pytest.mark.parametrize("example", EXAMPLES, ids=lambda p: p.stem)
def test_c7a_02_examples_conform_to_every_layer(example: Path) -> None:
    assert _messages(_graph(example), EVERY_SHAPE) == []


@needs_reasoner
@pytest.mark.parametrize("example", REGIME_EXAMPLES, ids=lambda p: p.stem)
def test_c7a_03_regime_examples_are_consistent(example: Path) -> None:
    assert reasoning.run("consistent", graphs=[MODEL, _graph(example)]) is True


# ---- C7a-04: regimes and their transitions ----------------------------------

@pytest.mark.parametrize("add, remove, focus, message", [
    ("tmpl:notice-regime ins:arisesUnder tmpl:term-11-2 .", (), "/notice-regime", "exactly one term"),
    ("", ((LN["notice-regime"], INS.arisesUnder, LN["term-11-1"]),), "/notice-regime", "exactly one term"),
    ("tmpl:notice-regime ins:arisesUnder ex:term-11-1 .", ((LN["notice-regime"], INS.arisesUnder, LN["term-11-1"]),),
     "/notice-regime", "a stated term"),
    ("", ((LN["notice-regime"], RDF.type, INS.Template),), "/notice-regime", "stated meaning only"),
    ("tmpl:notice-regime ins:boundFrom tmpl:notice-regime .", (), "/notice-regime", "never bound"),
    ("tmpl:plain a bhv:TriggerDefinition ; bhv:triggerKind bhv:ExternalStimulus . tmpl:give-notice bhv:hasTrigger tmpl:plain .",
     ((LN["give-notice"], BHV.hasTrigger, LN["on-notice-given"]),), "/give-notice", "legal triggers"),
    ("tmpl:give-notice bhv:selectionPolicy bhv:AllMatches .", ((LN["give-notice"], BHV.selectionPolicy, BHV.SingleMatch),),
     "/give-notice", "bhv:SingleMatch, fixed"),
    ("tmpl:give-notice bhv:activationPolicy bhv:DeferredActivation .",
     ((LN["give-notice"], BHV.activationPolicy, BHV.ImmediateActivation),), "/give-notice", "bhv:ImmediateActivation, fixed"),
    ("", ((LN["give-notice"], RDF.type, INS.RegimeTransition),), "/notice-regime", "is not an ins:RegimeTransition"),
])
def test_c7a_04_regime_shapes_report(add: str, remove: tuple, focus: str, message: str) -> None:
    assert _reported(_changed("licence-notice", add, remove), focus, message)


# ---- C7a-05: each trigger's required value and kind -------------------------

@pytest.mark.parametrize("name, add, remove, focus, message", [
    ("licence-notice", "", ((LN["on-notice-given"], INS.ofPower, LN["end-on-notice"]),), "/on-notice-given", "exactly one power"),
    ("licence-notice", "tmpl:on-notice-given ins:ofPower tmpl:end-for-breach .", (), "/on-notice-given", "exactly one power"),
    ("licence-notice", "tmpl:bad a ins:OnBreach , bhv:TriggerDefinition ; bhv:triggerKind bhv:DerivedTrigger ; ins:ofPower tmpl:end-on-notice .",
     (), "/bad", "exactly one obligation"),
    ("licence-notice", "tmpl:bad a ins:OnBreach , bhv:TriggerDefinition ; bhv:triggerKind bhv:DerivedTrigger ; ins:ofObligation tmpl:end-on-notice .",
     (), "/bad", "exactly one obligation"),
    ("licence-notice", "", ((LN["on-notice-expiry"], INS.after, None),), "/on-notice-expiry", "exactly one of a length"),
    ("facility-cure-period", "", ((FC["on-leverage-exceeded"], INS.condition, FC_EX["leverage-exceeded"]),),
     "/on-leverage-exceeded", "exactly one Eligibility condition"),
    ("service-dispute", "", ((SD["on-dispute"], INS.activity, INSV.Dispute),), "/on-dispute", "exactly one act"),
    ("service-dispute", "tmpl:on-dispute ins:by ins-voc:Dispute .", (), "/on-dispute", "names parties"),
    ("licence-notice", "", ((LN["on-notice-given"], BHV.triggerKind, BHV.ExternalStimulus),), "/on-notice-given",
     "bhv:ExternalStimulus, fixed"),
    ("licence-notice", "tmpl:on-notice-expiry bhv:triggerKind bhv:ExternalStimulus .",
     ((LN["on-notice-expiry"], BHV.triggerKind, BHV.ScheduledTrigger),), "/on-notice-expiry", "bhv:ScheduledTrigger, fixed"),
    ("facility-cure-period", "tmpl:on-leverage-exceeded bhv:triggerKind bhv:ScheduledTrigger .",
     ((FC["on-leverage-exceeded"], BHV.triggerKind, BHV.DerivedTrigger),), "/on-leverage-exceeded", "bhv:DerivedTrigger, fixed"),
])
def test_c7a_05_trigger_shapes_report(name: str, add: str, remove: tuple, focus: str, message: str) -> None:
    g = _example(name)
    for s, p, o in remove:
        assert (s, p, o) in g or o is None
        g.remove((s, p, o))
    if add:
        g.parse(data=_prefixes(name) + add, format="turtle")
    assert _reported(g, focus, message)


# ---- C7a-06: the explicit Behaviour type (law B4) ---------------------------

@pytest.mark.parametrize("name, remove, focus", [
    ("service-dispute", (SD["on-dispute"], RDF.type, BHV.TriggerDefinition), "/on-dispute"),
    ("licence-notice", (LN["notice-regime"], RDF.type, BHV.StateSpace), "/notice-regime"),
    ("licence-notice", (LN["give-notice"], RDF.type, BHV.TransitionDefinition), "/give-notice"),
])
def test_c7a_06_behaviour_type_is_required(name: str, remove: tuple, focus: str) -> None:
    assert _reported(_changed(name, remove=(remove,)), focus, "law B4")


# ---- C7a-07: a gate names a state of a regime -------------------------------

def test_c7a_07_gate_on_a_plain_state_space() -> None:
    data = _changed("licence-notice", "tmpl:plain a bhv:StateSpace ; fnd:hasIdentity tmpl:plain-identity . "
                    "tmpl:plain-state a bhv:State ; bhv:inStateSpace tmpl:plain . "
                    "ex:sublicensing-excluded ins:appliesInState tmpl:plain-state .")
    assert _reported(data, "/sublicensing-excluded", "not a state of an ins:Regime")


def test_c7a_07_only_relations_are_gated() -> None:
    data = _changed("licence-notice", "tmpl:term-11-3 ins:appliesInState tmpl:notice-period .")
    assert _reported(data, "/term-11-3", "Only a legal relation is gated")


# ---- C7a-08: a per-occasion gate reaches its occasion (C11a-Q4) -------------

def test_c7a_08_per_occasion_gate_without_arising() -> None:
    data = _changed("service-dispute", remove=((SD_EX["termination-excluded"], INS.arisesOnBreachOf, SD_EX["provide-service"]),))
    assert _reported(data, "/termination-excluded", "no occasion is reached")
    assert not _reported(_example("service-dispute"), "/termination-excluded", "no occasion is reached")


def test_c7a_08_arising_through_a_trigger_reaches_the_occasion() -> None:
    data = _changed("service-dispute",
                    "ex:on-breach a ins:OnBreach , bhv:TriggerDefinition ; bhv:triggerKind bhv:DerivedTrigger ; "
                    "ins:ofObligation ex:provide-service . ex:termination-excluded ins:arisesOn ex:on-breach .",
                    ((SD_EX["termination-excluded"], INS.arisesOnBreachOf, SD_EX["provide-service"]),))
    assert not _reported(data, "/termination-excluded", "no occasion is reached")


def test_c7a_08_no_arising_or_ending_on_an_expiry() -> None:
    for prop in ("arisesOn", "endsOn"):
        data = _changed("licence-notice", f"ex:sublicensing-excluded ins:{prop} tmpl:on-notice-expiry .")
        assert _reported(data, "/sublicensing-excluded", "moves only regimes"), prop


def test_c7a_08_arising_tiers() -> None:
    data = _changed("service-dispute", "ex:end-for-failure ins:arisesOnBreachOf tmpl:provide-service .",
                    ((SD_EX["end-for-failure"], INS.arisesOnBreachOf, SD_EX["provide-service"]),))
    assert _reported(data, "/end-for-failure", "decision 3")


# ---- C7a-09: tolling --------------------------------------------------------

def test_c7a_09_tolled_by_its_own_state_space() -> None:
    data = _changed("facility-cure-period", "tmpl:on-cure-expiry ins:tolledIn tmpl:performing .")
    assert _reported(data, "/on-cure-expiry", "the state space it runs in")
    assert not _reported(_example("facility-cure-period"), "/on-cure-expiry", "the state space it runs in")


# ---- C7a-10: an act trigger is no legal relation (C7a-Q2) -------------------

@needs_reasoner
def test_c7a_10_act_trigger_is_not_a_legal_relation() -> None:
    data = _graph(_prefixes("service-dispute") + f"@prefix owl: <{OWL}> .\n"
                  "ex:NotARelation owl:complementOf ins:LegalRelation . "
                  "ex:act a ins:OnAct , ex:NotARelation ; ins:activity ins-voc:Dispute .")
    assert reasoning.run("consistent", graphs=[MODEL, data]) is True


# ---- C7a-11: structure and state stay apart (DP6) ---------------------------

@pytest.mark.parametrize("example", REGIME_EXAMPLES, ids=lambda p: p.stem)
def test_c7a_11_no_state_in_what_a_relation_covers(example: Path) -> None:
    data = MODEL + _graph(example)
    states = set(data.subjects(BHV.inStateSpace, None))
    for relation in {s for c in (INS.Obligation, INS.Permission, INS.Exclusion, INS.Power, INS.ContinuingObligation,
                                 INS.Prohibition) for s in data.subjects(RDF.type, c)}:
        frontier = [o for p in (INS.scope, INS.maintains, INS.activity) for o in data.objects(relation, p)]
        seen = set()
        while frontier:
            node = frontier.pop()
            if node in seen:
                continue
            seen.add(node)
            frontier += [o for o in data.objects(node, None) if not isinstance(o, URIRef) or o not in seen]
        assert not seen & states, relation


def test_c7a_11_the_grant_is_independent_of_the_regime() -> None:
    data = _example("licence-notice")
    for grant in (LN["grant-sublicences"], LN_EX["grant-sublicences"]):
        assert data.value(grant, INS.appliesInState) is None
        assert data.value(grant, INS.scope) is None


# ---- C7a-12: the vocab ------------------------------------------------------

def test_c7a_12_state_kinds_and_activities() -> None:
    vocab = _graph(VOCAB)
    assert (INSV.StateKindContract, VOC.constrainsProperty, INS.stateKind) in vocab
    assert (INSV.StateKindContract, VOC.boundScheme, INSV.StateKinds) in vocab
    kinds = set(vocab.subjects(SKOS.inScheme, INSV.StateKinds))
    activities = set(vocab.subjects(SKOS.inScheme, INSV.Activities))
    used_kinds, used_activities = set(), set()
    for example in EXAMPLES:
        g = _graph(example)
        used_kinds |= set(g.objects(None, INS.stateKind))
        used_activities |= set(g.objects(None, INS.activity))
    assert used_kinds and used_kinds <= kinds, used_kinds - kinds
    assert used_activities <= activities, used_activities - activities


# ---- C7a-13: literate source and release notes ------------------------------

def test_c7a_13_readme_is_the_source_and_releases_are_recorded() -> None:
    assert literate_extract.main([str(LAYER / "README.md"), "--layer", "instrument", "--root", str(ROOT), "--shapes",
                                  "shapes/structural.ttl", "shapes/constraints.ttl", "shapes/single-expression.ttl",
                                  "--check"]) == 0
    readme = (LAYER / "README.md").read_text()
    assert "0.10.0 (CCS C7a" in readme and "Shapes 0.3.0 (additive" in readme
    assert (LAYER / "shapes" / ".version").read_text().strip() == "0.6.0"
    vocab = _graph(VOCAB)
    assert URIRef(LATTICE + "instrument-vocab/0.14.0") in set(vocab.objects(None, OWL.versionIRI))


# ---- C7a-15 to C7a-18: authoring with a reasoner (C7a-R1) -------------------

def test_c7a_15_lean_licence_conforms_once_closed() -> None:
    closed = _closed(_lean(_example("licence-notice")))
    assert _messages(closed, EVERY_SHAPE) == []
    transitions = set(closed.subjects(RDF.type, INS.RegimeTransition))
    assert len(transitions) == 4
    for transition in transitions:
        assert set(closed.objects(transition, BHV.selectionPolicy)) == {BHV.SingleMatch}
        assert set(closed.objects(transition, BHV.activationPolicy)) == {BHV.ImmediateActivation}
        assert (transition, RDF.type, BHV.TransitionDefinition) in closed
    for cls, kind in FIXED_KIND.items():
        for trigger in closed.subjects(RDF.type, cls):
            assert set(closed.objects(trigger, BHV.triggerKind)) == {kind}, trigger


def test_c7a_16_lean_licence_fails_b4_without_a_reasoner() -> None:
    messages = _messages(_lean(_example("licence-notice")))
    b4 = {f for f, m in messages if "law B4" in m}
    assert b4 == {str(LN[n]) for n in ("notice-regime", "give-notice", "notice-runs-out", "terminate-from-in-force",
                                       "terminate-during-notice", "on-notice-given", "on-notice-expiry",
                                       "on-termination-for-breach")}
    assert not [m for _, m in messages if ", fixed" in m and "Assert it" not in m]


def test_c7a_17_wrong_policy_is_reported_where_stated_and_spreads_once_closed() -> None:
    wrong = _lean(_example("licence-notice"))
    wrong.add((LN["give-notice"], BHV.selectionPolicy, BHV.AllMatches))
    asserted = {f for f, m in _messages(wrong) if "bhv:SingleMatch, fixed" in m}
    assert asserted == {str(LN["give-notice"])}
    closed = {f for f, m in _messages(_closed(wrong)) if "bhv:SingleMatch, fixed" in m}
    assert closed == {str(t) for t in _example("licence-notice").subjects(RDF.type, INS.RegimeTransition)}


def test_c7a_18_a_trigger_from_its_property_alone() -> None:
    data = _lean(_example("licence-notice"))
    data.remove((LN["on-notice-given"], RDF.type, INS.OnExercise))
    closed = _closed(data)
    trigger = LN["on-notice-given"]
    assert {INS.OnExercise, BHV.TriggerDefinition} <= set(closed.objects(trigger, RDF.type))
    assert set(closed.objects(trigger, BHV.triggerKind)) == {BHV.ExternalStimulus}
