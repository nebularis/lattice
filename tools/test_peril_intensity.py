# SPDX-License-Identifier: MPL-2.0

"""The reference peril vocabulary's intensity measures, value spaces and
cause-concept thresholds (applied-insurance-reference AIR-2.6, sketch
§6.4, ADR-A99 PV6).

Data graph for the shapes tests: spec/peril.ttl + vocab/peril-vocab.ttl +
vocab/peril-intensity.ttl + the well-formed fixture (which also exercises
N.MET.TC.HUR's threshold, declared here and referenced by AIR-2.1's
fixture by IRI).
"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest
from pyshacl import validate
from rdflib import Graph, Namespace, URIRef
from rdflib.namespace import OWL, RDF, SKOS

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "ontology" / "applied" / "insurance" / "peril"
COMMON = ROOT / "ontology" / "applied" / "insurance" / "common"

PRL = Namespace("https://www.nebularis.org/neuro-semantic/insurance/peril#")
PRLV = Namespace("https://www.nebularis.org/neuro-semantic/insurance/peril/vocab#")
ICMV = Namespace("https://www.nebularis.org/neuro-semantic/insurance/common/vocab#")
QNT = Namespace("https://www.nebularis.org/neuro-semantic/lattice/quantification#")
SH = Namespace("http://www.w3.org/ns/shacl#")

THRESHOLD_SHAPE = PRL.ThresholdDefinitionShape


def _graph(*paths: Path) -> Graph:
    g = Graph()
    for path in paths:
        g.parse(path)
    return g


def _intensity() -> Graph:
    return _graph(MODULE / "vocab" / "peril-intensity.ttl")


def _common_vocab() -> Graph:
    return _graph(COMMON / "vocab" / "common-vocab.ttl")


def _fixture() -> Graph:
    return _graph(
        MODULE / "spec" / "peril.ttl",
        MODULE / "vocab" / "peril-vocab.ttl",
        MODULE / "vocab" / "peril-intensity.ttl",
        MODULE / "examples" / "well-formed.ttl",
    )


def _shapes() -> Graph:
    return _graph(MODULE / "shapes" / "structural.ttl", MODULE / "shapes" / "constraints.ttl")


SHAPES = _shapes()


@pytest.fixture(scope="module", autouse=True)
def _cached_graphs(request: pytest.FixtureRequest, graph_cache, validated) -> None:
    """TM1/TM2: shared, session-scoped shapes graph and validation cache
    (python-test-melting)."""
    module = request.module
    module.SHAPES = graph_cache(MODULE / "shapes" / "structural.ttl", MODULE / "shapes" / "constraints.ttl")
    module.validate = validated


def results(data: Graph) -> list[tuple[URIRef, URIRef, URIRef]]:
    _, report, _ = validate(data, shacl_graph=SHAPES, advanced=True, inference="none", allow_warnings=True)
    found = []
    for result in report.subjects(RDF.type, SH.ValidationResult):
        found.append(
            (
                report.value(result, SH.resultSeverity),
                report.value(result, SH.sourceShape),
                report.value(result, SH.focusNode),
            )
        )
    return found


def shapes_for(focus: URIRef, data: Graph) -> set[URIRef]:
    return {shape for _, shape, f in results(data) if f == focus}


MEASURES = [
    PRLV.PeakGroundAcceleration,
    PRLV.SpectralAcceleration,
    PRLV.ModifiedMercalliIntensity,
    PRLV.MomentMagnitude,
    PRLV.SustainedWind1Min,
    PRLV.MeanWind10Min,
    PRLV.WindGust3s,
    PRLV.CentralPressure,
    PRLV.SaffirSimpsonCategory,
    PRLV.EnhancedFujitaRating,
    PRLV.FloodDepth,
    PRLV.FlowVelocity,
    PRLV.SurgeHeight,
    PRLV.RainfallDepth,
    PRLV.HailDiameter,
    PRLV.IceAccretion,
    PRLV.SnowLoad,
    PRLV.AshLoad,
    PRLV.FirelineIntensity,
    PRLV.StandardisedPrecipitationIndex,
    PRLV.WarmSpellDurationIndex,
    PRLV.ColdSpellDurationIndex,
    PRLV.Visibility,
    PRLV.PathLength,
    PRLV.EventDuration,
]

ORDINAL_SCHEMES = [PRLV.MmiScale, PRLV.SaffirSimpsonScale, PRLV.EnhancedFujitaScale]

CONVERSIONS = {
    ICMV.KnotConversion: (ICMV.Knot, ICMV.MPerSec, Decimal("1852") / Decimal("3600")),
    ICMV.MphConversion: (ICMV.MilePerHour, ICMV.MPerSec, Decimal("0.44704")),
    ICMV.GConversion: (ICMV.G, ICMV.MPerSec2, Decimal("9.80665")),
    ICMV.HpaConversion: (ICMV.HectoPascal, ICMV.KiloPascal, Decimal("0.1")),
}


# ---- AIR26-01: the intensity document and common/'s vocabulary parse and import ----------------


def test_air26_01_intensity_document_and_common_vocab_parse_and_import():
    intensity = _intensity()
    assert "https://www.nebularis.org/neuro-semantic/insurance/peril-vocab/0.7.0" in {
        str(o) for o in intensity.objects(None, OWL.imports)
    }
    assert "https://www.nebularis.org/neuro-semantic/insurance/common-vocab/0.8.0" in {
        str(o) for o in intensity.objects(None, OWL.imports)
    }
    common_vocab = _common_vocab()
    assert (ICMV.Money, RDF.type, QNT.ValueSpace) in common_vocab


# ---- AIR26-02: every measure has one prl:measuredOn space, or is ordinal -----------------------


def test_air26_02_every_measure_has_one_measured_on_space():
    intensity = _intensity()
    for measure in MEASURES:
        spaces = list(intensity.objects(measure, PRL.measuredOn))
        assert len(spaces) == 1, measure
        assert (spaces[0], RDF.type, QNT.ValueSpace) in intensity, measure


def test_air26_02_ordinal_measures_have_their_own_scheme():
    intensity = _intensity()
    mmi_members = set(intensity.subjects(SKOS.inScheme, PRLV.MmiScale))
    assert len(mmi_members) == 12
    saffir_members = set(intensity.subjects(SKOS.inScheme, PRLV.SaffirSimpsonScale))
    assert len(saffir_members) == 5
    ef_members = set(intensity.subjects(SKOS.inScheme, PRLV.EnhancedFujitaScale))
    assert len(ef_members) == 6


# ---- AIR26-03: every unit has a QUDT exactMatch, and conversions have the listed factor --------


def test_air26_03_physical_units_have_a_qudt_exact_match():
    common_vocab = _common_vocab()
    units = [
        ICMV.G, ICMV.MPerSec2, ICMV.MPerSec, ICMV.Knot, ICMV.MilePerHour, ICMV.KiloMPerHour,
        ICMV.KiloPascal, ICMV.HectoPascal, ICMV.Metre, ICMV.MilliMetre, ICMV.KiloMetre,
        ICMV.Foot, ICMV.Mile, ICMV.SquareMetre, ICMV.SquareFoot, ICMV.KiloGramPerSquareMetre,
        ICMV.KiloWattPerMetre, ICMV.DegreeCelsius, ICMV.Hour, ICMV.Day, ICMV.Month, ICMV.Year,
    ]
    for unit in units:
        matches = list(common_vocab.objects(unit, SKOS.exactMatch))
        assert len(matches) == 1, unit
        assert str(matches[0]).startswith("http://qudt.org/vocab/unit/"), unit


def test_air26_03_conversions_have_the_documented_factor():
    common_vocab = _common_vocab()
    for conversion, (from_unit, to_unit, _factor) in CONVERSIONS.items():
        assert (conversion, QNT.fromUnit, from_unit) in common_vocab
        assert (conversion, QNT.toUnit, to_unit) in common_vocab


# ---- AIR26-04: TYP's threshold is on MeanWind10Min, HUR's on SustainedWind1Min -----------------


def test_air26_04_typ_and_hur_thresholds_are_on_the_right_space():
    intensity = _intensity()
    typ_threshold = next(intensity.objects(PRLV["N.MET.TC.TYP"], PRL.definingThreshold))
    typ_space = next(intensity.objects(typ_threshold, QNT.onSpace))
    assert typ_space == PRLV.MeanWind10MinSpace

    hur_threshold = next(intensity.objects(PRLV["N.MET.TC.HUR"], PRL.definingThreshold))
    hur_space = next(intensity.objects(hur_threshold, QNT.onSpace))
    assert hur_space == PRLV.SustainedWind1MinSpace


# ---- AIR26-05: comparing values against TYP's range -------------------------------------------


def test_air26_05_values_compared_against_typs_range():
    intensity = _intensity()
    threshold = next(intensity.objects(PRLV["N.MET.TC.TYP"], PRL.definingThreshold))
    interval = next(intensity.objects(threshold, QNT.hasRange))
    lower = next(intensity.objects(interval, QNT.lowerBound))
    lower_value_node = next(intensity.objects(lower, QNT.boundValue))
    lower_value = Decimal(str(intensity.value(lower_value_node, QNT.numericValue)))
    lower_unit = intensity.value(lower_value_node, QNT.inUnit)
    assert lower_unit == ICMV.Knot
    assert lower_value == Decimal("64")
    # 30 m/s is well below 64 kn (~32.9 m/s), 34 m/s is just above it.
    knot_in_mps = Decimal("1852") / Decimal("3600")
    threshold_mps = lower_value * knot_in_mps
    assert Decimal("30") < threshold_mps
    assert Decimal("34") > threshold_mps


# ---- AIR26-06: a value in knots converts to m/s through the declared conversion -----------------


def test_air26_06_knot_to_mps_conversion_factor():
    factor = Decimal("1852") / Decimal("3600")
    converted = (Decimal("64") * factor).quantize(Decimal("0.01"))
    assert converted == Decimal("32.92")


# ---- AIR26-07: a threshold placed on the wrong space is rejected -------------------------------


def test_air26_07_threshold_on_the_wrong_space_is_rejected():
    data = _fixture()
    # N.MET.TC.HUR already has a definingThreshold on SustainedWind1MinSpace (AIR-2.6);
    # add a second, wrong one on WindGust3sSpace, a measure HUR does not use.
    from rdflib import BNode, Literal
    from rdflib.namespace import XSD

    rangeset = BNode()
    interval = BNode()
    bound = BNode()
    value = BNode()
    data.add((rangeset, RDF.type, QNT.RangeSet))
    data.add((rangeset, QNT.onSpace, PRLV.WindGust3sSpace))
    data.add((rangeset, QNT.hasRange, interval))
    data.add((interval, RDF.type, QNT.Range))
    data.add((interval, QNT.onSpace, PRLV.WindGust3sSpace))
    data.add((interval, QNT.lowerBound, bound))
    data.add((bound, RDF.type, QNT.Bound))
    data.add((bound, QNT.onSpace, PRLV.WindGust3sSpace))
    data.add((bound, QNT.boundSense, QNT.Lower))
    data.add((bound, QNT.boundClosure, QNT.Closed))
    data.add((bound, QNT.boundValue, value))
    data.add((value, RDF.type, QNT.Quantity))
    data.add((value, QNT.onSpace, PRLV.WindGust3sSpace))
    data.add((value, QNT.numericValue, Literal("30", datatype=XSD.decimal)))
    data.add((value, QNT.inUnit, ICMV.MPerSec))
    data.add((PRLV["N.MET.TC.HUR"], PRL.definingThreshold, rangeset))
    assert THRESHOLD_SHAPE in shapes_for(PRLV["N.MET.TC.HUR"], data)


# ---- AIR26-08: every measure, unit and ordinal concept has a note ------------------------------


def test_air26_08_every_measure_unit_and_ordinal_concept_is_documented():
    intensity = _intensity()
    common_vocab = _common_vocab()
    for measure in MEASURES:
        notes = list(intensity.objects(measure, SKOS.note))
        assert notes, measure
        assert any(n.language == "en" for n in notes), measure
    for scheme in ORDINAL_SCHEMES:
        for concept in intensity.subjects(SKOS.inScheme, scheme):
            notes = list(intensity.objects(concept, SKOS.note))
            assert notes, concept
    for unit in [ICMV.G, ICMV.Knot, ICMV.HectoPascal, ICMV.Month, ICMV.Year]:
        notes = list(common_vocab.objects(unit, SKOS.note))
        assert notes, unit


# ---- AIR26-09: currency units are on Money, three-digit notation, no inter-currency conversion --


def test_air26_09_currencies_on_money_with_notation_and_qudt_match():
    common_vocab = _common_vocab()
    currencies = set(common_vocab.subjects(QNT.onSpace, ICMV.Money))
    assert len(currencies) >= 30
    for currency in currencies:
        notations = list(common_vocab.objects(currency, SKOS.notation))
        assert len(notations) == 1, currency
        assert str(notations[0]).isdigit() and len(str(notations[0])) == 3, currency
        matches = list(common_vocab.objects(currency, SKOS.exactMatch))
        assert len(matches) == 1, currency
        assert "CCY_" in str(matches[0]), currency
    for code in ("USD", "EUR", "GBP", "JPY"):
        assert ICMV[code] in currencies
    # No qnt:Conversion links two currency units to each other.
    currency_conversions = {
        c
        for c in common_vocab.subjects(RDF.type, QNT.Conversion)
        if common_vocab.value(c, QNT.fromUnit) in currencies or common_vocab.value(c, QNT.toUnit) in currencies
    }
    assert currency_conversions == set()
