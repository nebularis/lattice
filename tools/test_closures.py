# SPDX-License-Identifier: MPL-2.0

"""Closures (computable-contract-substrate HQ-6a.1, ADR-A105, L15 as restated, L17).
Row IDs are the HQ-6a.1 Validation Pack's. Each example's stated outcomes are read by a small
reference evaluator over the example graph: it follows each binding's path and decides it with the
reference semantics (`tools/reference/eligibility`), as the compilers will in HQ-6a.2."""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest
from pyshacl import validate
from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import RDF, SH, XSD

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools" / "reference" / "eligibility" / "src"))

from reference_eligibility.denotation import decide_condition  # noqa: E402
from reference_eligibility.kernel import DENIED, PERMITTED, UNDETERMINED  # noqa: E402

ONTOLOGY = ROOT / "ontology"
LAYER = ONTOLOGY / "eligibility"
ELG = Namespace("https://www.nebularis.org/neuro-semantic/lattice/eligibility#")
FND = Namespace("https://www.nebularis.org/neuro-semantic/lattice/foundation#")
INS = Namespace("https://www.nebularis.org/neuro-semantic/lattice/instrument#")
ADM = Namespace("https://example.org/lattice/eligibility/admissions/")
TRI = Namespace("https://example.org/lattice/eligibility/trial/")
USE = Namespace("https://example.org/lattice/eligibility/usage-reports/")
FAC = Namespace("https://example.org/lattice/instrument/facility-requests/")
FAM = Namespace("https://example.org/lattice/instrument/facility-amendment/")
REI = Namespace("https://example.org/lattice/instrument/reinsurance-claims-cooperation/")
EXAMPLES = {
    "admissions": LAYER / "examples" / "set-reading-admissions.ttl",
    "trial": LAYER / "examples" / "set-reading-trial.ttl",
    "usage": LAYER / "examples" / "closure-usage-reports.ttl",
    "facility": ONTOLOGY / "instrument" / "examples" / "facility-requests.ttl",
    "reinsurance": ONTOLOGY / "instrument" / "examples" / "reinsurance-claims-cooperation.ttl",
}
READINGS = {ELG.SingleValue: "SingleValue", ELG.SomeValue: "SomeValue", ELG.EveryValue: "EveryValue"}
PREFIXES = f"@prefix elg: <{ELG}> .\n@prefix ex: <https://example.org/lattice/eligibility/probe/> .\n"


@pytest.fixture(scope="module", autouse=True)
def _cached_graphs(request: pytest.FixtureRequest, graph_cache, validated) -> None:
    """Shared, session-scoped graphs and validation cache (python-test-melting). Never mutate them."""
    module = request.module
    module.SHAPES = graph_cache(*[LAYER / "shapes" / f"{name}.ttl" for name in ("structural", "constraints", "rules")])
    module.SPEC = graph_cache(LAYER / "spec" / "eligibility.ttl")
    module.validate = validated


def _graph(*sources) -> Graph:
    g = Graph()
    for source in sources:
        g.parse(source) if isinstance(source, Path) else g.parse(data=source, format="turtle")
    return g


def _violations(data: Graph) -> list[tuple[str, str]]:
    _, report, _ = validate(data, shacl_graph=SHAPES, ont_graph=SPEC, inference="none", advanced=True)
    return [(str(report.value(r, SH.focusNode)), str(report.value(r, SH.resultMessage)))
            for r in report.subjects(SH.resultSeverity, SH.Violation)]


# ---- A reference reading of a bound condition ----------------------------------------

def in_force(g: Graph, closure: URIRef, at: datetime) -> bool:
    """L17: a closure is in force from its source's effective time. A source with no stated
    valid time is in force throughout."""
    source = g.value(closure, ELG.licensedBy)
    if source is None:
        return False
    start = g.value(g.value(source, FND.hasTemporalScope), FND.validFrom)
    return start is None or start.toPython() <= at


def values(g: Graph, binding: URIRef, subject: URIRef) -> list:
    nodes = [subject]
    steps = sorted(g.objects(binding, ELG.evidenceStep), key=lambda s: int(g.value(s, ELG.stepIndex)))
    for step in steps:
        prop, inverse = g.value(step, ELG.stepProperty), g.value(step, ELG.stepDirection) == ELG.Inverse
        nodes = [n for node in nodes for n in (g.subjects(prop, node) if inverse else g.objects(node, prop))]
    return nodes


def decide(g: Graph, binding: URIRef, subject: URIRef, at: datetime = datetime(2030, 1, 1, tzinfo=timezone.utc)):
    condition = g.value(binding, ELG.bindsCondition)
    closure = g.value(binding, ELG.closedUnder)
    return decide_condition(
        values(g, binding, subject),
        reading=READINGS[g.value(binding, ELG.valueReading, default=ELG.SingleValue)],
        negated=bool(g.value(condition, ELG.negated, default=Literal(False)).toPython()),
        closed=closure is not None and in_force(g, closure, at),
        hierarchical=False,
        required=set(g.objects(condition, ELG.requiredConcept)),
        excluded=set(g.objects(condition, ELG.excludedConcept)),
    )


def without_closures(g: Graph) -> Graph:
    """A copy of the example with every binding's closure removed."""
    copy = Graph()
    for triple in g:
        if triple[1] != ELG.closedUnder:
            copy.add(triple)
    return copy


# ---- HQ6a1-01 to 03, 11: the shapes ---------------------------------------------------

@pytest.mark.parametrize(("text", "rejected"), [
    ("ex:c a elg:Closure ; elg:licensedBy ex:registry .", False),
    ("ex:c a elg:Closure .", True),                                                        # zero sources
    ("ex:c a elg:Closure ; elg:licensedBy ex:registry , ex:clause .", True),               # two
])
def test_hq6a1_01_a_closure_names_one_source(text: str, rejected: bool) -> None:
    found = [m for f, m in _violations(_graph(PREFIXES + text)) if "exactly one source" in m]
    assert bool(found) is rejected


BINDING = """ex:b a elg:EvidenceBinding ; elg:bindsCondition ex:cond ; elg:subjectClass ex:Thing ;
    elg:evidenceStep [ a elg:EvidenceStep ; elg:stepIndex 0 ; elg:stepProperty ex:p ; elg:stepDirection elg:Forward ] ;
    {reading} elg:closedUnder ex:c .
ex:c a elg:Closure ; elg:licensedBy ex:registry ."""


@pytest.mark.parametrize(("reading", "rejected"), [
    ("elg:valueReading elg:SomeValue ;", False),
    ("elg:valueReading elg:EveryValue ;", False),
    ("elg:valueReading elg:SingleValue ;", True),
    ("", True),                                                                             # the default, a single value
])
def test_hq6a1_02_only_a_set_reading_names_a_closure(reading: str, rejected: bool) -> None:
    found = [m for f, m in _violations(_graph(PREFIXES + BINDING.format(reading=reading)))
             if "names a closure" in m]
    assert bool(found) is rejected


def test_hq6a1_03_a_binding_names_only_a_closure() -> None:
    text = PREFIXES + BINDING.format(reading="elg:valueReading elg:SomeValue ;").replace(
        "ex:c a elg:Closure ; elg:licensedBy ex:registry .", "ex:c ex:note \"not a closure\" .")
    assert [m for f, m in _violations(_graph(text)) if "is an elg:Closure" in m]


DECISION = """ex:profile a elg:AdmissionProfile ; elg:hasCondition ex:cond ;
    elg:matchStrategy elg:ExactMatch ; elg:compatibilityOperation elg:AllRequired ; elg:wildcardSemantics elg:NoWildcard .
ex:cond a elg:Condition ; elg:matchStrategy elg:ExactMatch ; elg:compatibilityOperation elg:AllRequired ;
    elg:wildcardSemantics elg:NoWildcard ; elg:requiredConcept ex:x .
ex:other a elg:Closure ; elg:licensedBy ex:clause .
ex:d a elg:EligibilityDecision ; elg:forProfile ex:profile ; elg:hasQuestion ex:q ; elg:decisionValue elg:Permitted ;
    elg:usesOperationalProfile ex:op ; elg:closureReliedOn {relied} ."""


@pytest.mark.parametrize(("relied", "rejected"), [("ex:c", False), ("ex:other", True)])
def test_hq6a1_11_a_decision_relies_only_on_its_bindings_closures(relied: str, rejected: bool) -> None:
    text = PREFIXES + BINDING.format(reading="elg:valueReading elg:SomeValue ;") + "\n" + DECISION.format(relied=relied)
    found = [m for f, m in _violations(_graph(text)) if "profile's conditions names" in m]
    assert bool(found) is rejected


# ---- HQ6a1-04 to 09: the examples' outcomes, with and without their closures ----------

def test_hq6a1_04_to_06_admissions() -> None:
    g = _graph(EXAMPLES["admissions"])
    closed = {"ada": (PERMITTED, PERMITTED), "ben": (DENIED, PERMITTED),
              "cai": (DENIED, PERMITTED), "dee": (PERMITTED, DENIED)}
    open_ = {"ada": (PERMITTED, UNDETERMINED), "ben": (UNDETERMINED, UNDETERMINED),
             "cai": (UNDETERMINED, UNDETERMINED), "dee": (PERMITTED, DENIED)}
    for graph, table in ((g, closed), (without_closures(g), open_)):
        for applicant, expected in table.items():
            got = tuple(decide(graph, ADM[b], ADM[applicant]) for b in ("stem-binding", "medicine-binding"))
            assert got == expected, applicant


def test_hq6a1_07_trial_every_value() -> None:
    g = _graph(EXAMPLES["trial"])
    closed = {"pat-1": (PERMITTED, PERMITTED), "pat-2": (DENIED, DENIED), "pat-3": (PERMITTED, PERMITTED)}
    open_ = {"pat-1": (UNDETERMINED, UNDETERMINED), "pat-2": (DENIED, DENIED), "pat-3": (UNDETERMINED, UNDETERMINED)}
    for graph, table in ((g, closed), (without_closures(g), open_)):
        for patient, expected in table.items():
            got = tuple(decide(graph, TRI[b], TRI[patient]) for b in ("permitted-binding", "excluded-binding"))
            assert got == expected, patient


def test_hq6a1_08_a_closure_not_yet_in_force_decides_nothing() -> None:
    g = _graph(EXAMPLES["usage"])
    g.add((USE["reporting-clause"], FND.hasTemporalScope, USE.scope))
    g.add((USE.scope, FND.validFrom, Literal("2031-01-01T00:00:00Z", datatype=XSD.dateTime)))
    before, after = datetime(2030, 6, 1, tzinfo=timezone.utc), datetime(2031, 6, 1, tzinfo=timezone.utc)
    assert decide(g, USE["no-use-binding"], USE["lic-3"], before) is UNDETERMINED
    assert decide(g, USE["no-use-binding"], USE["lic-3"], after) is PERMITTED


def test_hq6a1_09_objections_register_at_a_vote() -> None:
    g = _graph(EXAMPLES["facility"])
    closed = {"request-1": PERMITTED, "request-2": DENIED, "request-3": PERMITTED}
    open_ = {"request-1": UNDETERMINED, "request-2": DENIED, "request-3": UNDETERMINED}
    for graph, table in ((g, closed), (without_closures(g), open_)):
        for request, expected in table.items():
            assert decide(graph, FAC["no-objection-binding"], FAC[request]) is expected, request


def test_hq6a1_09_usage_reports_and_the_claims_file() -> None:
    usage = _graph(EXAMPLES["usage"])
    for graph, table in ((usage, {"lic-1": PERMITTED, "lic-2": DENIED, "lic-3": PERMITTED}),
                         (without_closures(usage), {"lic-1": UNDETERMINED, "lic-2": DENIED, "lic-3": UNDETERMINED})):
        for licence, expected in table.items():
            assert decide(graph, USE["no-use-binding"], USE[licence]) is expected, licence
    claims = _graph(EXAMPLES["reinsurance"])
    for graph, table in ((claims, {"claim-1": PERMITTED, "claim-2": DENIED}),
                         (without_closures(claims), {"claim-1": PERMITTED, "claim-2": UNDETERMINED})):
        for claim, expected in table.items():
            assert decide(graph, REI["settled-with-approval-binding"], REI[claim]) is expected, claim


# ---- HQ6a1-10: every example conforms to Eligibility's shapes -------------------------

@pytest.mark.parametrize("name", sorted(EXAMPLES))
def test_hq6a1_10_examples_conform(name: str) -> None:
    assert _violations(_graph(EXAMPLES[name])) == []
