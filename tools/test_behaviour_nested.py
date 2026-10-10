# SPDX-License-Identifier: MPL-2.0

"""Nested states, history, internal transitions and concurrent regimes
(computable-contract-substrate C11a phase 2, the ADR-A106 addendum). Row IDs
are the C11a Validation Pack's. Reasoner rows skip when the ADR-A83 harness
jar is not built."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from pyshacl import validate
from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import OWL, PROV, SH

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent / "mork_compilers" / "src"))

import literate_extract  # noqa: E402
from mork_compilers import reasoning  # noqa: E402
from ontology_catalog import Catalog, closure  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
LAYER = ROOT / "ontology" / "behaviour"
LATTICE = "https://www.nebularis.org/neuro-semantic/lattice/"
BHV = Namespace(LATTICE + "behaviour#")
CONFIG, RUNTIME, VOCAB = LAYER / "spec" / "behaviour.ttl", LAYER / "spec" / "behaviour-runtime.ttl", LAYER / "vocab" / "behaviour-vocab.ttl"
NESTED = ["covenant-default", "run-off", "standstill", "garden-leave", "force-majeure",
          "occasion-refinement", "disputed-occasion", "ordered-draws"]
EXAMPLES = sorted((LAYER / "examples").glob("*.ttl"))


def _graph(*paths: Path) -> Graph:
    g = Graph()
    for path in paths:
        g.parse(path)
    return g


SHAPES = _graph(LAYER / "shapes" / "structural.ttl", LAYER / "shapes" / "constraints.ttl")
MODEL = _graph(CONFIG, RUNTIME, VOCAB)


@pytest.fixture(scope="module", autouse=True)
def _cached_graphs(request: pytest.FixtureRequest, graph_cache, validated) -> None:
    """TM1/TM2: shared, session-scoped graphs and validation cache
    (python-test-melting)."""
    module = request.module
    module.MODEL = graph_cache(CONFIG, RUNTIME, VOCAB)
    module.SHAPES = graph_cache(LAYER / "shapes" / "structural.ttl", LAYER / "shapes" / "constraints.ttl")
    module.validate = validated


def _reported(data: Graph, focus: str, message: str) -> bool:
    """Whether a violation on the focus node carries a message starting with the given text."""
    _, report, _ = validate(MODEL + data, shacl_graph=SHAPES, inference="none", advanced=True)
    return any(str(report.value(r, SH.focusNode)).endswith("/" + focus)
               and str(report.value(r, SH.resultMessage)).startswith(message)
               for r in report.subjects(SH.resultSeverity, SH.Violation))


def _conforms(data: Graph) -> bool:
    return validate(MODEL + data, shacl_graph=SHAPES, inference="none", advanced=True)[0]


PREFIXES = (f"@prefix bhv: <{BHV}> .\n@prefix fnd: <{LATTICE}foundation#> .\n"
            "@prefix ex: <https://example.org/n/> .\n")
POLICIES = "bhv:selectionPolicy bhv:SingleMatch ; bhv:activationPolicy bhv:ImmediateActivation"


def _data(text: str) -> Graph:
    return Graph().parse(data=PREFIXES + text, format="turtle")


def _example(name: str) -> Graph:
    return _graph(LAYER / "examples" / f"{name}.ttl")


# ---- C11a-05, C11a-06: the examples ---------------------------------------------

@pytest.mark.parametrize("example", EXAMPLES, ids=lambda p: p.stem)
def test_c11a_05_every_example_conforms(example: Path) -> None:
    assert _conforms(_graph(example))


def test_c11a_05_the_eight_worked_examples_exist() -> None:
    assert {p.stem for p in EXAMPLES} >= set(NESTED)


@pytest.mark.skipif(not reasoning.available(), reason="reasoning-testkit jar not built")
@pytest.mark.parametrize("name", NESTED)
def test_c11a_06_examples_are_consistent(name: str) -> None:
    catalog = Catalog(ROOT / "ontology" / "catalog-v001.xml")
    graph = closure(catalog, LATTICE + "behaviour-vocab/0.14.0") + closure(catalog, LATTICE + "behaviour-runtime/0.14.0")
    assert reasoning.run("consistent", graphs=[graph, _example(name)]) is True


# ---- C11a-07 to C11a-11: each rule reported --------------------------------------

STATE = "ex:{0} a bhv:State ; bhv:inStateSpace ex:{1} . "
SPACE = "ex:{0} a bhv:StateSpace . "


@pytest.mark.parametrize("data, focus, message", [
    # C11a-07: regions
    (SPACE.format("r") + "ex:r bhv:regionOf ex:a , ex:b . ex:a a bhv:State . ex:b a bhv:State .",
     "r", "A region refines at most one state"),
    (STATE.format("a", "r1") + STATE.format("b", "r2") + "ex:r1 a bhv:StateSpace ; bhv:regionOf ex:b . "
     "ex:r2 a bhv:StateSpace ; bhv:regionOf ex:a .", "a", "A state does not contain itself"),
    (STATE.format("from", "top") + STATE.format("to", "top") +
     f"ex:t a bhv:TransitionDefinition ; bhv:fromState ex:from ; bhv:toState ex:to ; bhv:hasTrigger ex:g ; "
     f"bhv:entryMode bhv:DeepHistory ; {POLICIES} .", "t", "A transition entering by history targets a state with a region"),
    # C11a-08: internal transitions and AllMatches
    (STATE.format("from", "top") + STATE.format("to", "top") +
     f"ex:t a bhv:TransitionDefinition ; bhv:fromState ex:from ; bhv:toState ex:to ; bhv:hasTrigger ex:g ; "
     f"bhv:transitionType bhv:Internal ; {POLICIES} .", "t", "Only a transition from a state to itself can be internal"),
    (STATE.format("from", "top") + STATE.format("to", "top") +
     "ex:t a bhv:TransitionDefinition ; bhv:fromState ex:from ; bhv:toState ex:to ; bhv:hasTrigger ex:g ; "
     "bhv:selectionPolicy bhv:AllMatches ; bhv:priority 1 ; bhv:activationPolicy bhv:ImmediateActivation .",
     "t", "AllMatches applies only to internal transitions"),
    (STATE.format("s", "top") +
     "ex:t a bhv:TransitionDefinition ; bhv:fromState ex:s ; bhv:toState ex:s ; bhv:hasTrigger ex:g ; "
     "bhv:selectionPolicy bhv:AllMatches ; bhv:priority 5 ; bhv:activationPolicy bhv:ImmediateActivation . "
     "ex:u a bhv:TransitionDefinition ; bhv:fromState ex:s ; bhv:toState ex:s ; bhv:hasTrigger ex:g ; "
     "bhv:selectionPolicy bhv:AllMatches ; bhv:priority 5 ; bhv:activationPolicy bhv:ImmediateActivation .",
     "t", "AllMatches transitions from one state on one trigger each declare a priority"),
    (STATE.format("s", "top") +
     "ex:t a bhv:TransitionDefinition ; bhv:fromState ex:s ; bhv:toState ex:s ; bhv:hasTrigger ex:g ; "
     "bhv:selectionPolicy bhv:AllMatches ; bhv:activationPolicy bhv:ImmediateActivation .",
     "t", "AllMatches transitions from one state on one trigger each declare a priority"),
    (STATE.format("s", "top") + STATE.format("a", "top") + STATE.format("b", "top") +
     f"ex:t a bhv:TransitionDefinition ; bhv:fromState ex:s ; bhv:toState ex:a ; bhv:hasTrigger ex:g ; {POLICIES} . "
     "ex:u a bhv:TransitionDefinition ; bhv:fromState ex:s ; bhv:toState ex:b ; bhv:hasTrigger ex:g ; "
     "bhv:selectionPolicy bhv:PriorityOrdered ; bhv:priority 1 ; bhv:activationPolicy bhv:ImmediateActivation .",
     "t", "State-changing transitions from one state on one trigger declare the same selection policy"),
    # C11a-09: B9
    (STATE.format("a", "one") + STATE.format("b", "two") + SPACE.format("one") + SPACE.format("two") +
     f"ex:t a bhv:TransitionDefinition ; bhv:fromState ex:a ; bhv:toState ex:b ; bhv:hasTrigger ex:g ; {POLICIES} .",
     "t", "A transition's source and target belong to one top-level state space"),
    (STATE.format("inner", "refinement") + "ex:refinement a bhv:StateSpace ; bhv:regionOf bhv:Arisen ; "
     "bhv:perOccasionOf ex:duty ; bhv:initialState ex:inner . "
     f"ex:t a bhv:TransitionDefinition ; bhv:fromState ex:inner ; bhv:toState bhv:Performed ; bhv:hasTrigger ex:g ; {POLICIES} .",
     "t", "A transition declared in a refinement of an occasion state stays inside that refinement"),
], ids=["region-of-two-states", "regions-in-a-cycle", "history-into-an-atomic-state",
        "internal-between-two-states", "all-matches-changing-state", "all-matches-same-priority",
        "all-matches-without-priority", "competitors-disagree", "between-two-top-level-spaces",
        "refinement-leaves-itself"])
def test_c11a_07_to_09_configuration_rules(data: str, focus: str, message: str) -> None:
    assert _reported(_data(data), focus, message)


OCCUPANCY = "ex:{0} a bhv:StateOccupancy ; bhv:forSubject ex:x ; bhv:occupiesState ex:{1} ; bhv:isHypothetical false ; bhv:isCurrent {2} ; "
EVIDENCE = "fnd:hasEvidence [ a fnd:Evidence ] . "
TREE = (SPACE.format("top") + "ex:top bhv:initialState ex:p . " + STATE.format("p", "top") + STATE.format("q", "top") +
        "ex:region a bhv:StateSpace ; bhv:regionOf ex:p ; bhv:initialState ex:c . " +
        STATE.format("c", "region") + STATE.format("d", "region") +
        f"ex:history a bhv:TransitionDefinition ; bhv:fromState ex:q ; bhv:toState ex:p ; bhv:hasTrigger ex:g ; "
        f"bhv:entryMode bhv:DeepHistory ; {POLICIES} . "
        f"ex:plain a bhv:TransitionDefinition ; bhv:fromState ex:q ; bhv:toState ex:p ; bhv:hasTrigger ex:h ; {POLICIES} . "
        "ex:s a bhv:Stimulus . ex:x1 a bhv:TransitionExecution ; bhv:causedByStimulus ex:s . "
        "ex:x2 a bhv:TransitionExecution ; bhv:executedTransition ex:history ; bhv:causedByStimulus ex:s . "
        "ex:x3 a bhv:TransitionExecution ; bhv:executedTransition ex:plain ; bhv:causedByStimulus ex:s . ")


@pytest.mark.parametrize("data, focus, message", [
    # C11a-10: B5
    (TREE + OCCUPANCY.format("old", "d", "false") + "bhv:exitedBy ex:x1 ; " + EVIDENCE +
     OCCUPANCY.format("new", "c", "false") + "bhv:enteredBy ex:x2 ; bhv:resumedFrom ex:old .",
     "new", "A resumed occupancy is of the same subject and state"),
    (TREE + OCCUPANCY.format("old", "d", "false") + EVIDENCE +
     OCCUPANCY.format("new", "d", "false") + "bhv:enteredBy ex:x2 ; bhv:resumedFrom ex:old .",
     "new", "A resumed occupancy is of the same subject and state"),
    (TREE + OCCUPANCY.format("old", "d", "false") + "bhv:exitedBy ex:x1 ; " + EVIDENCE +
     OCCUPANCY.format("new", "d", "false") + "bhv:enteredBy ex:x3 ; bhv:resumedFrom ex:old .",
     "new", "A resumed occupancy is of the same subject and state"),
    # C11a-11: B11
    (TREE + OCCUPANCY.format("child", "c", "true") + EVIDENCE, "child", "A current occupancy of a nested state has"),
    (TREE + OCCUPANCY.format("parent", "p", "true") + EVIDENCE, "parent", "A current occupancy of a composite state"),
    (TREE + OCCUPANCY.format("parent", "p", "true") + EVIDENCE + OCCUPANCY.format("one", "c", "true") + EVIDENCE +
     OCCUPANCY.format("two", "d", "true") + EVIDENCE, "one", "A non-hypothetical subject may not have more than one"),
    # B6 extended
    (TREE + "ex:bare a bhv:TransitionExecution . " + OCCUPANCY.format("o", "q", "false") + "bhv:exitedBy ex:bare ; " + EVIDENCE,
     "o", "An execution that ended a state names the stimulus"),
], ids=["resumes-another-state", "resumes-one-never-exited", "entered-by-a-default-transition",
        "child-without-parent", "composite-with-empty-region", "region-with-two-current-states", "exit-without-stimulus"])
def test_c11a_10_11_runtime_rules(data: str, focus: str, message: str) -> None:
    assert _reported(_data(data), focus, message)


def test_c11a_11_a_refinement_applies_only_to_its_relation_s_occasions() -> None:
    refinement = (STATE.format("inner", "refinement") + "ex:refinement a bhv:StateSpace ; bhv:regionOf bhv:Arisen ; "
                  "bhv:perOccasionOf ex:duty ; bhv:initialState ex:inner . "
                  "ex:x a bhv:Occasion ; bhv:occasionOf ex:other-duty ; bhv:forCase ex:case . "
                  "ex:p a ex:Party . ")
    arisen = ("ex:{0} a bhv:StateOccupancy , fnd:DerivedArtefact ; bhv:forSubject ex:x ; bhv:occupiesState bhv:{1} ; "
              "bhv:isHypothetical false ; bhv:isCurrent true ; fnd:hasEvidence [ a fnd:Evidence ] . ")
    data = _data(refinement + arisen.format("live", "Live") + arisen.format("arisen", "Arisen"))
    assert not _reported(data, "arisen", "A current occupancy of a composite state")


# ---- C11a-12, C11a-13: the examples read as their tables say --------------------

def test_c11a_12_deep_and_shallow_history_in_the_standstill() -> None:
    graph = _example("standstill")
    ex = Namespace("https://example.org/lattice/behaviour/standstill/")
    current = lambda subject: {graph.value(o, BHV.occupiesState) for o in graph.subjects(BHV.forSubject, subject)
                               if graph.value(o, BHV.isCurrent) == Literal(True)}
    assert current(ex["facility-a"]) == {ex.operative, ex.default, ex.uncured}
    assert current(ex["facility-b"]) == {ex.operative, ex.default, ex["cure-period"]}
    for occupancy in graph.subjects(BHV.enteredBy, ex["a-exec-4"]):
        resumed = graph.value(occupancy, BHV.resumedFrom)
        assert graph.value(resumed, BHV.exitedBy) == ex["a-exec-3"], occupancy
    assert graph.value(ex["b-occ-cure-period-2"], BHV.resumedFrom) is None


def test_c11a_13_ordered_draws_read_what_the_draw_before_left() -> None:
    graph = _example("ordered-draws")
    ex = Namespace("https://example.org/lattice/behaviour/ordered-draws/")
    assert ex["bundle-2"] in set(graph.objects(ex["alerts-1"], PROV.wasDerivedFrom))
    assert ex["p2-draw-a-seat"] in set(graph.objects(ex["bundle-2"], PROV.wasDerivedFrom))
    pass_3 = set(graph.subjects(BHV.causedByStimulus, ex["activation-3"]))
    assert pass_3 == {ex["p3-draw-a-seat"], ex["p3-draw-an-alert"], ex["p3-move-to-overage"]}
    assert set(graph.subjects(BHV.enteredBy, ex["p3-draw-a-seat"])) == set()   # internal: no occupancy
    priorities = {graph.value(graph.value(x, BHV.executedTransition), BHV.priority) for x in pass_3}
    assert {int(p) for p in priorities if p is not None} == {20, 10}


# ---- C11a-14, C11a-15: the vocab, the README ------------------------------------

def test_c11a_14_the_occasion_states_with_live() -> None:
    vocab = _graph(VOCAB)
    top = {s.split("#")[-1] for s in vocab.subjects(BHV.inStateSpace, BHV.OccasionStates)}
    live = {s.split("#")[-1] for s in vocab.subjects(BHV.inStateSpace, BHV.LiveStates)}
    assert top == {"Live", "Performed", "Breached", "Ended", "Suspended"}
    assert live == {"Pending", "Arisen"}
    assert vocab.value(BHV.OccasionStates, BHV.initialState) == BHV.Live
    assert vocab.value(BHV.LiveStates, BHV.regionOf) == BHV.Live
    assert vocab.value(BHV.LiveStates, BHV.initialState) == BHV.Pending
    for mode in ("DefaultEntry", "ShallowHistory", "DeepHistory"):
        assert (BHV[mode], None, BHV.EntryMode) in vocab
    for kind in ("Internal", "External"):
        assert (BHV[kind], None, BHV.TransitionType) in vocab


def test_c11a_15_readme_blocks_and_release_notes() -> None:
    assert literate_extract.main([str(LAYER / "README.md"), "--layer", "behaviour", "--root", str(ROOT),
                                  "--shapes", "shapes/structural.ttl", "--check"]) == 0
    readme = (LAYER / "README.md").read_text()
    assert "behaviour-vocab` 0.10.0 (breaking)" in readme and "Shapes 0.4.0 (breaking)" in readme
    for name in NESTED:
        assert f"examples/{name}.ttl" in readme, name


def test_c11a_15_versions_and_release_rows() -> None:
    config, runtime = _graph(CONFIG), _graph(RUNTIME)
    assert config.value(URIRef("https://www.nebularis.org/neuro-semantic/behaviour"), OWL.versionIRI) == URIRef(LATTICE + "behaviour/0.14.0")
    assert set(runtime.objects(None, OWL.imports)) == {URIRef(LATTICE + "behaviour/0.14.0")}
    register = (ROOT / "docs" / "architecture" / "ontology-releases.md").read_text()
    for tag in ("behaviour-v0.10.0", "behaviour-runtime-v0.10.0", "behaviour-vocab-v0.10.0", "behaviour-shapes-v0.4.0",
                "applied-capacity-execution-v0.10.0"):
        assert f"| {tag} |" in register, tag
