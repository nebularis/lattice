# SPDX-License-Identifier: MPL-2.0

"""Quantification: additivity (computable-contract-substrate C9b2, consent sketch §2.4).
Row IDs are the C9b2 Validation Pack's. The sums are read by `sum_of`, a reference reading of
Quantification §9.9 over the example graph, as the evaluator will read them. Reasoner rows skip
when the ADR-A83 harness jar is not built."""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

import pytest
from pyshacl import validate
from rdflib import Graph, Namespace, URIRef
from rdflib.namespace import OWL, RDF, SH

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "tools" / "mork_compilers" / "src"))

import literate_extract  # noqa: E402
from conftest import repo_files  # noqa: E402
from mork_compilers import reasoning  # noqa: E402

LATTICE = "https://www.nebularis.org/neuro-semantic/lattice/"
QNT = Namespace(LATTICE + "quantification#")
VOC = Namespace(LATTICE + "vocabulary#")
FND = Namespace(LATTICE + "foundation#")
EX = Namespace("https://example.org/lattice/quantification/additivity/")
ONTOLOGY = ROOT / "ontology"
QLAYER = ONTOLOGY / "quantification"
EXAMPLE = QLAYER / "examples" / "additivity.ttl"
LOWER = ["foundation/spec/foundation.ttl", "vocabulary/spec/vocabulary.ttl", "quantification/spec/quantification.ttl",
         "quantification/vocab/quantification-vocab.ttl"]
ALL_SHAPES = [ONTOLOGY / layer / "shapes" / f"{kind}.ttl"
              for layer in ("foundation", "vocabulary", "quantification", "party", "eligibility", "wording", "behaviour",
                            "instrument")
              for kind in ("structural", "constraints")]


def _graph(*sources) -> Graph:
    g = Graph()
    for source in sources:
        g.parse(source) if isinstance(source, Path) else g.parse(data=source, format="turtle")
    return g


@pytest.fixture(scope="module", autouse=True)
def _cached_graphs(request: pytest.FixtureRequest, graph_cache, validated) -> None:
    """Shared, session-scoped graphs and validation cache (python-test-melting). Never mutate them."""
    module = request.module
    module.MODEL = graph_cache(*[ONTOLOGY / p for p in LOWER])
    module.QSHAPES = graph_cache(QLAYER / "shapes" / "constraints.ttl")
    module.EVERY_SHAPE = graph_cache(*ALL_SHAPES)
    module.DATA = graph_cache(EXAMPLE)
    module.validate = validated


MARCH, APRIL = (datetime(2027, m, d, 12, tzinfo=timezone.utc) for m, d in ((3, 31), (4, 30)))
needs_reasoner = pytest.mark.skipif(not reasoning.available(), reason="reasoning-testkit jar not built")


def _messages(text: str) -> list[str]:
    prefixes = f"@prefix qnt: <{QNT}> .\n@prefix ex: <{EX}> .\n"
    _, report, _ = validate(MODEL + _graph(prefixes + text), shacl_graph=QSHAPES, inference="none", advanced=True)
    return [str(report.value(r, SH.resultMessage)) for r in report.subjects(SH.resultSeverity, SH.Violation)]


# ---- A reference reading of Quantification §9.9 -------------------------------

def _space(g: Graph, value: URIRef) -> URIRef:
    return g.value(value, QNT.onSpace)


def _capability(g: Graph, kind: URIRef, *spaces: URIRef) -> URIRef | None:
    """The result space of a declared capability with these operand spaces, in order (law Q7)."""
    for cap in g.subjects(QNT.operationKind, kind):
        operands = sorted((int(g.value(o, QNT.operandIndex)), g.value(o, QNT.operandSpace))
                          for o in g.objects(cap, QNT.hasOperand))
        if [s for _, s in operands] == list(spaces):
            return g.value(cap, QNT.resultSpace)
    return None


def _number(g: Graph, value: URIRef) -> Decimal:
    return Decimal(str(g.value(value, QNT.numericValue)))


def _rate(g: Graph, unit: URIRef, to: URIRef, at: datetime) -> Decimal | None:
    """The rate in force at the reference time, from a context for the declared conversion (§9.6)."""
    for conversion in g.subjects(QNT.fromUnit, unit):
        if g.value(conversion, QNT.toUnit) != to:
            continue
        for context in g.subjects(EX.forConversion, conversion):
            scope = g.value(context, FND.hasTemporalScope)
            start, end = g.value(scope, FND.validFrom).toPython(), g.value(scope, FND.validTo)
            if start <= at and (end is None or at < end.toPython()):
                return Decimal(str(g.value(context, EX.rate)))
    return None


def _base(g: Graph, value: URIRef, role: URIRef) -> URIRef | None:
    for binding in g.objects(g.value(value, EX.of), EX.resolves):
        if g.value(binding, EX.role) == role:
            return g.value(binding, EX.value)
    return None


def sum_of(g: Graph, values: list[URIRef], at: datetime) -> tuple[Decimal | None, URIRef | None, URIRef | None]:
    """(total, unit, None) or (None, None, the unresolved reason)."""
    space = _space(g, values[0])
    if {_space(g, v) for v in values} != {space} or _capability(g, QNT.Sum, space, space) != space:
        return None, None, QNT.OperationNotPermitted
    role = g.value(space, QNT.baseRole)
    if role is not None and len({_base(g, v, role) for v in values}) != 1:
        return None, None, QNT.MixedBases
    units = {g.value(v, QNT.inUnit) for v in values}
    if len(units) == 1:
        return sum(_number(g, v) for v in values), units.pop(), None
    base = g.value(g.value(space, QNT.unitContract), QNT.canonicalUnit)
    total = Decimal(0)
    for v in values:
        unit = g.value(v, QNT.inUnit)
        rate = Decimal(1) if unit == base else _rate(g, unit, base, at)
        if rate is None:
            return None, None, QNT.ConversionContextAbsent
        total += _number(g, v) * rate
    return total, base, None


def at_most(g: Graph, amount: Decimal, unit: URIRef, bound: URIRef) -> URIRef:
    """Upper-bound containment with alternative bounds, never converting (§9.2, ADR-A95)."""
    statements = {bound, *g.objects(bound, QNT.alternativeBound), *g.subjects(QNT.alternativeBound, bound)}
    for statement in statements:
        limit = g.value(statement, QNT.boundValue)
        if g.value(limit, QNT.inUnit) == unit:
            return QNT["True"] if amount <= _number(g, limit) else QNT["False"]
    return QNT.NoBoundInUnit


# ---- C9b2-01: the spec and vocabulary -----------------------------------------

def test_c9b2_01_terms() -> None:
    ontology = URIRef("https://www.nebularis.org/neuro-semantic/quantification")
    assert MODEL.value(ontology, OWL.versionIRI) == URIRef(LATTICE + "quantification/0.8.0")
    assert (QNT.additivity, RDF.type, OWL.FunctionalProperty) in MODEL
    assert MODEL.value(QNT.additivity, URIRef("http://www.w3.org/2000/01/rdf-schema#range")) == QNT.Additivity
    assert set(MODEL.subjects(RDF.type, QNT.Additivity)) == {QNT.Extensive, QNT.Intensive}
    assert (QNT.baseRole, RDF.type, OWL.FunctionalProperty) in MODEL
    assert "undeclared" in str(MODEL.value(QNT.additivity, FND.utility))
    assert (QNT.MixedBases, RDF.type, QNT.UnresolvedReason) in MODEL
    assert set(MODEL.objects(QNT.ContextRoleContract, VOC.constrainsProperty)) == {QNT.contextRole, QNT.baseRole}


# ---- C9b2-02: the examples ----------------------------------------------------

def test_c9b2_02_example_conforms_to_every_layer() -> None:
    _, report, _ = validate(MODEL + DATA, shacl_graph=EVERY_SHAPE, inference="none", advanced=True)
    assert not list(report.subjects(SH.resultSeverity, SH.Violation))


@needs_reasoner
def test_c9b2_02_example_is_consistent() -> None:
    assert reasoning.run("consistent", graphs=[MODEL, DATA]) is True


# ---- C9b2-03 to C9b2-07: the shapes -------------------------------------------

SPACE = 'ex:s a qnt:ValueSpace ; qnt:hasOperationCapability ex:c . '
SAME_SPACE_SUM = 'ex:c a qnt:OperationCapability ; qnt:operationKind qnt:Sum ; qnt:resultSpace ex:s .'


@pytest.mark.parametrize("text, rejected", [
    (SPACE + SAME_SPACE_SUM.replace("qnt:Sum", "qnt:Compare"), False),        # zero: optional
    (SPACE + "ex:s qnt:additivity qnt:Extensive , qnt:Intensive .", True),   # two
    (SPACE + "ex:s qnt:additivity qnt:Dense .", True),                       # not a kind of additivity
])
def test_c9b2_03_additivity_at_zero_and_two(text: str, rejected: bool) -> None:
    assert any("never both" in m for m in _messages(text)) is rejected


@pytest.mark.parametrize("text, rejected", [
    (SPACE + "ex:s qnt:additivity qnt:Extensive . " + SAME_SPACE_SUM, False),
    (SPACE + "ex:s qnt:additivity qnt:Intensive . " + SAME_SPACE_SUM, True),
    (SPACE + SAME_SPACE_SUM, True),                                           # undeclared
    (SPACE + "ex:c a qnt:OperationCapability ; qnt:operationKind qnt:Sum .", True),  # implied operands
    (SPACE + "ex:s qnt:additivity qnt:Intensive . ex:c a qnt:OperationCapability ; qnt:operationKind qnt:Sum ; "
             "qnt:hasOperand [ qnt:operandIndex 0 ; qnt:operandSpace ex:s ] , [ qnt:operandIndex 1 ; qnt:operandSpace ex:s ] .",
     True),
])
def test_c9b2_04_sum_within_one_space_needs_extensive(text: str, rejected: bool) -> None:
    assert any("law Q12" in m for m in _messages(text)) is rejected


def test_c9b2_05_date_plus_duration_is_still_valid() -> None:
    assert _capability(DATA, QNT.Sum, EX.dates, EX.durations) == EX.dates
    assert DATA.value(EX.dates, QNT.additivity) is None
    dates_only = DATA - _graph(f"@prefix ex: <{EX}> .\n@prefix qnt: <{QNT}> .\nex:durations qnt:additivity qnt:Extensive .")
    _, report, _ = validate(MODEL + dates_only, shacl_graph=QSHAPES, inference="none", advanced=True)
    focus = {report.value(r, SH.focusNode) for r in report.subjects(SH.resultSeverity, SH.Violation)}
    assert EX["date-plus-duration"] not in focus and EX["duration-sum"] in focus


def test_c9b2_06_count_on_an_intensive_space_is_valid() -> None:
    assert DATA.value(EX.severity, QNT.additivity) == QNT.Intensive
    assert _capability(DATA, QNT.Count, EX.severity) == EX.headcount
    assert _messages(SPACE + "ex:s qnt:additivity qnt:Intensive . ex:c a qnt:OperationCapability ; qnt:operationKind qnt:Count .") == []


@pytest.mark.parametrize("text, message", [
    ("ex:p a qnt:DerivedValueSpace ; qnt:numeratorSpace ex:m ; qnt:denominatorSpace ex:m ; qnt:baseRole ex:order . "
     "ex:m a qnt:ValueSpace .", None),
    ("ex:p a qnt:ValueSpace ; qnt:baseRole ex:order .", "Only a derived value space"),
    ("ex:p a qnt:DerivedValueSpace ; qnt:numeratorSpace ex:m ; qnt:denominatorSpace ex:m ; qnt:baseRole ex:a , ex:b . "
     "ex:m a qnt:ValueSpace .", "exactly one base role"),
])
def test_c9b2_07_a_proportions_base_role(text: str, message: str | None) -> None:
    found = _messages(text)
    assert found == [] if message is None else any(message in m for m in found)


# ---- C9b2-08 to C9b2-11: currencies -------------------------------------------

def test_c9b2_08_one_currency_sums() -> None:
    assert sum_of(DATA, [EX["commitment-1"], EX["commitment-2"]], APRIL) == (Decimal(90_000_000), EX.EUR, None)


def test_c9b2_09_mixed_currencies_convert_at_the_reference_time_then_sum() -> None:
    commitments = [EX[f"commitment-{n}"] for n in (1, 2, 3)]
    assert sum_of(DATA, commitments, MARCH) == (Decimal("109800000.0"), EX.EUR, None)


def test_c9b2_10_mixed_currencies_with_no_context_are_undetermined() -> None:
    commitments = [EX[f"commitment-{n}"] for n in (1, 2, 3)]
    assert sum_of(DATA, commitments, APRIL) == (None, None, QNT.ConversionContextAbsent)


def test_c9b2_11_a_limit_in_two_currencies_is_never_converted() -> None:
    total, unit, _ = sum_of(DATA, [EX[f"commitment-{n}"] for n in (1, 2, 3)], MARCH)
    assert at_most(DATA, total, unit, EX["limit-eur"]) == QNT["True"]
    usd_limit_converted = _number(DATA, DATA.value(EX["limit-usd"], QNT.boundValue)) * _rate(DATA, EX.USD, EX.EUR, MARCH)
    assert total > usd_limit_converted                                   # a converting reading would say False
    assert _rate(DATA, EX.GBP, EX.EUR, MARCH) is not None
    assert at_most(DATA, _number(DATA, EX["reported-total"]), EX.GBP, EX["limit-usd"]) == QNT.NoBoundInUnit


# ---- C9b2-12, C9b2-13: shares -------------------------------------------------

def test_c9b2_12_shares_of_one_base_sum_and_of_two_are_undetermined() -> None:
    lines = [EX[f"written-{x}"] for x in "ABCD"]
    assert sum_of(DATA, lines, MARCH)[0] == Decimal("1.6")
    assert _number(DATA, EX["order-1"]) == _number(DATA, EX["order-2"])  # same amount, different bases
    assert sum_of(DATA, [EX["written-A"], EX["written-E"]], MARCH) == (None, None, QNT.MixedBases)


def test_c9b2_13_signing_down_is_ratio_then_scale() -> None:
    lines = [EX[f"written-{x}"] for x in "ABCD"]
    written = sum_of(DATA, lines, MARCH)[0]
    assert _capability(DATA, QNT.Ratio, EX["line-share"], EX["line-share"]) == EX["signing-factor"]
    factor = _number(DATA, EX["whole-order-1"]) / written
    assert factor == Decimal("0.625")
    assert _capability(DATA, QNT.Scale, EX["line-share"], EX["signing-factor"]) == EX["line-share"]
    signed = [_number(DATA, line) * factor for line in lines]
    assert signed == [Decimal(x) for x in ("0.3125", "0.25", "0.1875", "0.25")] and sum(signed) == 1
    assert _capability(DATA, QNT.Scale, EX.money, EX["line-share"]) == EX.money
    assert _number(DATA, EX["order-1"]) * signed[0] == Decimal(3_125_000)
    assert DATA.value(EX["signing-factor"], QNT.additivity) == QNT.Intensive


# ---- C9b2-14, C9b2-15: the literate source and the cascade -------------------

def test_c9b2_14_readme_is_the_source_and_records_the_release() -> None:
    assert literate_extract.main([str(QLAYER / "README.md"), "--layer", "quantification", "--root", str(ROOT),
                                  "--shapes", "shapes/constraints.ttl", "--check"]) == 0
    readme = (QLAYER / "README.md").read_text()
    assert "**0.8.0** (additive, CCS C9b2" in readme and "Shapes 0.3.0 (breaking)" in readme
    assert "| `Sum` | yes, extensive | no, only plus an extent | no, intensive | yes, of one base | no |" in readme
    assert "Answered in principle (CCS C9b2)" in readme
    assert (QLAYER / "shapes" / ".version").read_text().strip() == "0.3.0"
    worked = (QLAYER / "examples" / "examples.md").read_text()
    assert worked.count("qnt:additivity qnt:Extensive") == 2


def test_c9b2_15_nothing_still_imports_quantification_0_7_0() -> None:
    found = repo_files(("ontology", "tools"), LATTICE + "quantification/0.7.0", fixed=True)
    assert [f for f in found if not f.endswith("catalog-v001.xml") and "fixtures/import_guard" not in f] == []
