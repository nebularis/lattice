# SPDX-License-Identifier: MPL-2.0

"""Behaviour below Instrument, split into configuration and runtime
(computable-contract-substrate C10, ADR-A106). Row IDs are the C10 Validation
Pack's."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from owlrl import DeductiveClosure, RDFS_Semantics
from pyshacl import validate
from rdflib import Graph, Namespace, URIRef
from rdflib.namespace import OWL, RDF, RDFS

sys.path.insert(0, str(Path(__file__).resolve().parent))

from ontology_catalog import Catalog, closure  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
LAYER = ROOT / "ontology" / "behaviour"
LATTICE = "https://www.nebularis.org/neuro-semantic/lattice/"
BHV = Namespace(LATTICE + "behaviour#")
CONFIG = LAYER / "spec" / "behaviour.ttl"
RUNTIME = LAYER / "spec" / "behaviour-runtime.ttl"
VOCAB = LAYER / "vocab" / "behaviour-vocab.ttl"
CAPACITY_IRI = "https://www.nebularis.org/neuro-semantic/lattice/applied/capacity/execution"

DECLARATION = {"StateSpace", "State", "TransitionDefinition", "TriggerDefinition", "GuardDefinition",
               "EffectDefinition", "AllowanceDefinition", "SelectionPolicy", "ActivationPolicy",
               "TriggerKind", "TargetKind", "AbsorptionPolicy", "OperationalProfile",
               "EntryMode", "TransitionType"}  # C11a
RUNTIME_TIERS = {"Stimulus", "TransitionExecution", "EffectApplication", "StateOccupancy", "AllowanceAccount"}

# Every fixture conformed before C10 (recorded on a122915, before any change).
FIXTURES = {
    LAYER / "examples" / "state-transition.ttl": True,
    LAYER / "examples" / "sequential-allowance.ttl": True,
    LAYER / "test" / "B-P1-basic-transition.ttl": True,
    LAYER / "test" / "B-P2-sequential-allowance.ttl": True,
    ROOT / "test" / "conformance" / "cases" / "behaviour-bp1-transition.ttl": True,
}


def _graph(*paths: Path) -> Graph:
    g = Graph()
    for path in paths:
        g.parse(path)
    return g


SHAPES = _graph(LAYER / "shapes" / "structural.ttl", LAYER / "shapes" / "constraints.ttl")


def _conforms(data: Graph) -> bool:
    return validate(_graph(CONFIG, RUNTIME, VOCAB) + data, shacl_graph=SHAPES, inference="none", advanced=True)[0]


PREFIXES = f"@prefix bhv: <{BHV}> .\n@prefix ex: <https://example.org/b/> .\n"
TRANSITION = ("ex:from a bhv:State ; bhv:inStateSpace ex:space . ex:to a bhv:State ; bhv:inStateSpace ex:space . "
              "ex:trigger a bhv:TriggerDefinition . ")


def _data(text: str) -> Graph:
    return Graph().parse(data=PREFIXES + text, format="turtle")


def _declared_classes(path: Path) -> set:
    return {str(c).rsplit("#", 1)[-1] for c in _graph(path).subjects(RDF.type, OWL.Class) if str(c).startswith(str(BHV))}


# ---- C10-01 to C10-04: imports, no higher layer, no ranges, tiers ----------------

def test_c10_01_imports() -> None:
    config, runtime = _graph(CONFIG), _graph(RUNTIME)
    assert set(config.objects(None, OWL.imports)) == {URIRef(LATTICE + f"{layer}") for layer in (
        "foundation/0.4.0", "vocabulary/0.4.0", "quantification/0.8.0", "party/0.9.0", "eligibility/0.11.0")}
    assert {str(i).rsplit("/", 1)[0] for i in runtime.objects(None, OWL.imports)} == {LATTICE + "behaviour"}


def test_c10_02_names_no_instrument_term() -> None:
    """Every Behaviour file, fixtures included (B7), and the shared conformance case."""
    files = [p for p in LAYER.rglob("*") if p.suffix in {".ttl", ".md"}]
    files.append(ROOT / "test" / "conformance" / "cases" / "behaviour-bp1-transition.ttl")
    for path in files:
        text = path.read_text()
        assert "lattice/instrument" not in text and "ins:" not in text, path.relative_to(ROOT)
        if path.parent.name in {"examples", "test", "cases"}:
            assert "bhv:InstrumentTarget" not in text, path.relative_to(ROOT)


@pytest.mark.parametrize("prop", ["targets", "forSubject"])
def test_c10_03_no_range(prop: str) -> None:
    assert _graph(CONFIG, RUNTIME).value(BHV[prop], RDFS.range) is None


def test_c10_04_each_tier_in_one_document() -> None:
    assert _declared_classes(CONFIG) == DECLARATION
    runtime = _declared_classes(RUNTIME)
    assert RUNTIME_TIERS <= runtime and not runtime & DECLARATION  # C11 adds occasions and records


# ---- C10-05 to C10-08: shapes -------------------------------------------------

def test_c10_05_a_transition_needs_no_effect() -> None:
    assert _conforms(_data(TRANSITION + "ex:t a bhv:TransitionDefinition ; bhv:fromState ex:from ; bhv:toState ex:to ; "
                           "bhv:hasTrigger ex:trigger ; bhv:selectionPolicy bhv:SingleMatch ; "
                           "bhv:activationPolicy bhv:ImmediateActivation ."))


@pytest.mark.parametrize("policies", [
    "bhv:activationPolicy bhv:ImmediateActivation .",                                             # no selection policy
    "bhv:selectionPolicy bhv:PriorityOrdered ; bhv:activationPolicy bhv:ImmediateActivation .",  # no priority
], ids=["no-selection-policy", "priority-ordered-without-priority"])
def test_c10_06_policies_stay_required(policies: str) -> None:
    assert not _conforms(_data(TRANSITION + "ex:t a bhv:TransitionDefinition ; bhv:fromState ex:from ; "
                               "bhv:toState ex:to ; bhv:hasTrigger ex:trigger ; " + policies))


@pytest.mark.parametrize("effect", [
    "ex:e a bhv:EffectDefinition ; bhv:targetKind bhv:PartyTarget ; bhv:targets ex:anything .",
    "ex:a a bhv:AllowanceDefinition ; bhv:allowanceSpace ex:s ; bhv:absorptionPolicy bhv:Sequential . "
    "ex:e a bhv:EffectDefinition ; bhv:targetKind bhv:AllowanceTarget ; bhv:targetsAllowance ex:a .",
], ids=["targets-anything", "targets-allowance"])
def test_c10_07_effects_target_any_resource(effect: str) -> None:
    assert _conforms(_data(effect))


@pytest.mark.parametrize("effect", [
    "ex:e a bhv:EffectDefinition ; bhv:targetKind bhv:PartyTarget .",
    "ex:e a bhv:EffectDefinition ; bhv:targets ex:anything .",
], ids=["no-target", "no-target-kind"])
def test_c10_08_an_effect_needs_a_kind_and_a_target(effect: str) -> None:
    assert not _conforms(_data(effect))


# ---- C10-09: no type inferred from the removed ranges -------------------------

def test_c10_09_no_type_is_inferred_for_a_subject_or_target() -> None:
    data = _graph(CONFIG, RUNTIME) + _data(
        "ex:o a bhv:StateOccupancy ; bhv:forSubject ex:agreement . ex:e a bhv:EffectDefinition ; bhv:targets ex:relation .")
    DeductiveClosure(RDFS_Semantics).expand(data)
    for node in ("agreement", "relation"):
        types = set(data.objects(URIRef("https://example.org/b/" + node), RDF.type)) - {RDFS.Resource}
        assert types == set(), (node, types)


# ---- C10-10 to C10-13: fixtures, cascade, deprecation, releases ---------------------

@pytest.mark.parametrize("fixture, before", FIXTURES.items(), ids=lambda v: getattr(v, "name", str(v)))
def test_c10_10_fixtures_keep_their_outcome(fixture: Path, before: bool) -> None:
    assert _conforms(_graph(fixture)) is before


def test_c10_11_capacity_resolves_through_runtime_to_configuration() -> None:
    graph = closure(Catalog(ROOT / "ontology" / "catalog-v001.xml"), CAPACITY_IRI)
    ontologies = set(graph.subjects(RDF.type, OWL.Ontology))
    assert URIRef("https://www.nebularis.org/neuro-semantic/behaviour-runtime") in ontologies
    assert URIRef("https://www.nebularis.org/neuro-semantic/behaviour") in ontologies
    assert not any("instrument" in str(o) for o in ontologies)


def test_c10_12_instrument_target_is_deprecated() -> None:
    vocab = _graph(VOCAB)
    assert (BHV.InstrumentTarget, RDF.type, BHV.TargetKind) in vocab
    assert vocab.value(BHV.InstrumentTarget, OWL.deprecated).toPython() is True


def test_c10_13_every_changed_version_has_a_release_row() -> None:
    register = (ROOT / "docs" / "architecture" / "ontology-releases.md").read_text()
    for tag in ("behaviour-v0.8.0", "behaviour-runtime-v0.8.0", "behaviour-vocab-v0.8.0", "behaviour-shapes-v0.2.0",
                "behaviour-projection-v0.2.0", "applied-capacity-execution-v0.8.0"):
        assert f"| {tag} |" in register, tag
