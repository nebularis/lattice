# SPDX-License-Identifier: MPL-2.0

"""Occasions, records, declared initial states and the evidence rule
(computable-contract-substrate C11, ADR-A106). Row IDs are the C11 Validation
Pack's. Reasoner rows skip when the ADR-A83 harness jar is not built."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from pyshacl import validate
from rdflib import Graph, Namespace, URIRef
from rdflib.namespace import OWL, RDF, RDFS, SH

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent / "mork_compilers" / "src"))

from mork_compilers import reasoning  # noqa: E402
from ontology_catalog import Catalog, closure  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
LAYER = ROOT / "ontology" / "behaviour"
LATTICE = "https://www.nebularis.org/neuro-semantic/lattice/"
BHV = Namespace(LATTICE + "behaviour#")
CONFIG, RUNTIME, VOCAB = LAYER / "spec" / "behaviour.ttl", LAYER / "spec" / "behaviour-runtime.ttl", LAYER / "vocab" / "behaviour-vocab.ttl"
EXAMPLES = [LAYER / "examples" / "adverse-event-occasion.ttl", LAYER / "examples" / "licence-suspension.ttl"]
ALL_EXAMPLES = sorted((LAYER / "examples").glob("*.ttl"))
NEW_PROPERTIES = {"enteredBy", "occasionOf", "forCase", "occasionParty", "fromStimulus", "actor", "activity",
                  "ofOccasion", "closureReliedOn", "exercised", "tookEffect", "reasonNotTaken", "matter",
                  "determiner", "determinedValue", "deeming", "conditionSatisfied", "accepted", "initialState"}


def _graph(*paths: Path) -> Graph:
    g = Graph()
    for path in paths:
        g.parse(path)
    return g


SHAPES = _graph(LAYER / "shapes" / "structural.ttl", LAYER / "shapes" / "constraints.ttl")


@pytest.fixture(scope="module", autouse=True)
def _cached_graphs(request: pytest.FixtureRequest, graph_cache, validated) -> None:
    """TM1/TM2: MODEL used to be rebuilt by every `_violations` call; now
    parsed once, shared across the whole suite (python-test-melting)."""
    module = request.module
    module.MODEL = graph_cache(CONFIG, RUNTIME, VOCAB)
    module.SHAPES = graph_cache(LAYER / "shapes" / "structural.ttl", LAYER / "shapes" / "constraints.ttl")
    module.validate = validated


def _violations(data: Graph) -> set:
    _, report, _ = validate(MODEL + data, shacl_graph=SHAPES, inference="none", advanced=True)
    return {str(n).rsplit("/", 1)[-1] for n in report.objects(None, SH.focusNode)}


PREFIXES = (f"@prefix bhv: <{BHV}> .\n@prefix fnd: <{LATTICE}foundation#> .\n@prefix pty: <{LATTICE}party#> .\n"
            "@prefix prov: <http://www.w3.org/ns/prov#> .\n@prefix ex: <https://example.org/r/> .\n")
OCCASION = "ex:occ a bhv:Occasion ; bhv:occasionOf ex:duty ; bhv:forCase ex:case ; bhv:occasionParty ex:p . ex:p a pty:RoleOccupancy . "


def _data(text: str) -> Graph:
    return Graph().parse(data=PREFIXES + text, format="turtle")


def test_c11_01_runtime_version_imports_and_no_instrument() -> None:
    runtime = _graph(RUNTIME)
    assert runtime.value(URIRef("https://www.nebularis.org/neuro-semantic/behaviour-runtime"), OWL.versionIRI) == URIRef(LATTICE + "behaviour-runtime/0.13.1")  # C11a
    assert set(runtime.objects(None, OWL.imports)) == {URIRef(LATTICE + "behaviour/0.13.1")}
    assert "lattice/instrument" not in RUNTIME.read_text() and "ins:" not in RUNTIME.read_text()


@pytest.mark.parametrize("example", ALL_EXAMPLES, ids=lambda p: p.stem)
def test_c11_02_examples_conform(example: Path) -> None:
    assert _violations(_graph(example)) == set()


def test_c11_03_an_occupancy_with_neither_execution_nor_evidence_fails() -> None:
    assert "o" in _violations(_data("ex:o a bhv:StateOccupancy ; bhv:isHypothetical false ; bhv:occupiesState ex:s ."))


def test_c11_04_an_execution_with_no_stimulus_fails() -> None:
    assert "o" in _violations(_data("ex:x a bhv:TransitionExecution . "
                                    "ex:o a bhv:StateOccupancy ; bhv:isHypothetical false ; bhv:enteredBy ex:x ."))


def test_c11_05_an_occasion_occupancy_not_derived_from_a_record_fails() -> None:
    assert "o" in _violations(_data(OCCASION + "ex:o a bhv:StateOccupancy ; bhv:isHypothetical false ; bhv:forSubject ex:occ ; "
                                    "bhv:occupiesState bhv:Arisen ; fnd:hasEvidence [ a fnd:Evidence ] ."))


def test_c11_06_parties_are_occupancy_versions_fixed_at_arising() -> None:
    identity = "ex:occ a bhv:Occasion ; bhv:occasionOf ex:duty ; bhv:forCase ex:case ; bhv:occasionParty ex:who . ex:who a fnd:PersistentIdentity ."
    assert "occ" in _violations(_data(identity))
    superseded = OCCASION + "ex:p fnd:supersededBy ex:p2 . ex:p2 a pty:RoleOccupancy ."
    assert "occ" not in _violations(_data(superseded))


def test_c11_07_every_new_property_states_subject_and_value_and_names_no_higher_layer() -> None:
    spec = _graph(CONFIG, RUNTIME)
    for name in NEW_PROPERTIES:
        comment = str(spec.value(BHV[name], RDFS.comment) or "")
        assert "Subject:" in comment and "Value:" in comment, name
        for rng in spec.objects(BHV[name], RDFS.range):
            assert "lattice/instrument" not in str(rng) and "lattice/wording" not in str(rng), name


def test_c11_08_the_occasion_state_space() -> None:
    """The six core states stand. C11a adds Live, which holds Pending and Arisen, so Pending is reached
    as the initial state of Live's region (C11a-Q1)."""
    vocab = _graph(VOCAB)
    states = set(vocab.subjects(BHV.inStateSpace, BHV.OccasionStates)) | set(vocab.subjects(BHV.inStateSpace, BHV.LiveStates))
    assert {s.split("#")[-1] for s in states} == {"Live", "Pending", "Arisen", "Performed", "Breached", "Ended", "Suspended"}
    assert vocab.value(BHV.OccasionStates, BHV.initialState) == BHV.Live
    assert vocab.value(BHV.LiveStates, BHV.initialState) == BHV.Pending


@pytest.mark.skipif(not reasoning.available(), reason="reasoning-testkit jar not built")
@pytest.mark.parametrize("example", EXAMPLES, ids=lambda p: p.stem)
def test_c11_09_examples_are_consistent(example: Path) -> None:
    graph = closure(Catalog(ROOT / "ontology" / "catalog-v001.xml"), LATTICE + "behaviour-vocab/0.13.1")
    graph += closure(Catalog(ROOT / "ontology" / "catalog-v001.xml"), LATTICE + "behaviour-runtime/0.13.1")
    assert reasoning.run("consistent", graphs=[graph, _graph(example)]) is True


def test_c11_10_release_rows_and_notes() -> None:
    register = (ROOT / "docs" / "architecture" / "ontology-releases.md").read_text()
    for tag in ("behaviour-v0.9.0", "behaviour-runtime-v0.9.0", "behaviour-vocab-v0.9.0", "behaviour-shapes-v0.3.0",
                "applied-capacity-execution-v0.9.0"):
        assert f"| {tag} |" in register, tag
    assert "Shapes 0.3.0 (breaking)" in (LAYER / "README.md").read_text()


def test_c11_12_an_initial_state_outside_its_space_fails() -> None:
    assert "space" in _violations(_data("ex:space a bhv:StateSpace ; bhv:initialState ex:s . "
                                        "ex:s a bhv:State ; bhv:inStateSpace ex:other ."))


def test_c11_13_configuration_adds_an_optional_initial_state() -> None:
    config = _graph(CONFIG)
    assert config.value(URIRef("https://www.nebularis.org/neuro-semantic/behaviour"), OWL.versionIRI) == URIRef(LATTICE + "behaviour/0.13.1")
    assert (BHV.initialState, RDF.type, OWL.ObjectProperty) in config
    for fixture in [*(LAYER / "test").glob("*.ttl"), ROOT / "test" / "conformance" / "cases" / "behaviour-bp1-transition.ttl"]:
        assert _violations(_graph(fixture)) == set(), fixture.name
