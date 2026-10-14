# SPDX-License-Identifier: MPL-2.0

"""The asset exposure ontology's core spec, vocabulary and shapes
(applied-insurance-reference AIR-4.1).

Data graph for the shapes tests: the fixture plus ``spec/exposure.ttl`` and
``vocab/exposure-vocab.ttl``. Shapes graph: ``shapes/structural.ttl`` and
``shapes/constraints.ttl``. Negative cases mutate a copy of the fixture
graph, each breaking exactly one rule, modelled on
``tools/test_peril_vocabulary.py``.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from pyshacl import validate
from rdflib import BNode, Graph, Literal, Namespace, URIRef
from rdflib.namespace import OWL, RDF, XSD

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "ontology" / "applied" / "insurance" / "exposure"
VOCAB_SHAPES = ROOT / "ontology" / "vocabulary" / "shapes"

AEO = Namespace("https://www.nebularis.org/neuro-semantic/insurance/exposure#")
AEOV = Namespace("https://www.nebularis.org/neuro-semantic/insurance/exposure/vocab#")
EX = Namespace("https://example.org/lattice/insurance/exposure/examples#")
SKOS = Namespace("http://www.w3.org/2004/02/skos/core#")
VOC = Namespace("https://www.nebularis.org/neuro-semantic/lattice/vocabulary#")
FND = Namespace("https://www.nebularis.org/neuro-semantic/lattice/foundation#")
QNT = Namespace("https://www.nebularis.org/neuro-semantic/lattice/quantification#")
SH = Namespace("http://www.w3.org/ns/shacl#")

EXPOSURE_SET = AEO.ExposureSetShape
LOCATION = AEO.LocationShape
ASSET = AEO.AssetShape
INTEREST = AEO.InterestShape
VALUATION = AEO.ValuationShape
LEGAL_ENTITY = AEO.LegalEntityShape
MEMBERSHIP = AEO.MembershipShape
CONTROL_RELATION = AEO.ControlRelationShape
DOCUMENTATION = AEO.DocumentationShape


def _graph(*paths: Path) -> Graph:
    g = Graph()
    for path in paths:
        g.parse(path)
    return g


def _spec() -> Graph:
    return _graph(MODULE / "spec" / "exposure.ttl")


def _vocab() -> Graph:
    return _graph(MODULE / "vocab" / "exposure-vocab.ttl")


def _fixture() -> Graph:
    """spec + vocab + the core fixture, fresh per call so tests can mutate
    their own copy safely."""
    return _graph(
        MODULE / "spec" / "exposure.ttl",
        MODULE / "vocab" / "exposure-vocab.ttl",
        MODULE / "examples" / "core.ttl",
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
    """(severity, source shape, focus node) for every validation result."""
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


# ---- AIR41-01: spec/vocab import closures, peril/ not imported ---------------------------------


def test_air41_01_spec_and_vocab_parse_peril_not_imported():
    spec = _spec()
    vocab = _vocab()
    spec_imports = {str(o) for o in spec.objects(None, OWL.imports)}
    assert spec_imports == {
        "https://www.nebularis.org/neuro-semantic/lattice/foundation/0.4.0",
        "https://www.nebularis.org/neuro-semantic/lattice/vocabulary/0.4.0",
        "https://www.nebularis.org/neuro-semantic/lattice/quantification/0.8.0",
        "https://www.nebularis.org/neuro-semantic/lattice/party/0.9.0",
        "https://www.nebularis.org/neuro-semantic/insurance/common/0.5.0",
    }
    vocab_imports = {str(o) for o in vocab.objects(None, OWL.imports)}
    assert vocab_imports == {
        "https://www.nebularis.org/neuro-semantic/insurance/exposure/0.1.0",
        "https://www.nebularis.org/neuro-semantic/lattice/vocabulary/0.4.0",
        "https://www.nebularis.org/neuro-semantic/lattice/foundation/0.4.0",
        "https://www.nebularis.org/neuro-semantic/insurance/common-vocab/0.5.0",
    }
    assert not any("peril" in i for i in spec_imports | vocab_imports)


# ---- AIR41-02: the seven contracts conform and are bound to their reference scheme --------------


def test_air41_02_seven_contracts_conform_and_bound():
    data = _vocab()
    shapes = _graph(VOCAB_SHAPES / "structural.ttl", VOCAB_SHAPES / "constraints.ttl")
    conforms, _, report = validate(data, shacl_graph=shapes, advanced=True, inference="none", allow_warnings=True)
    assert conforms, report
    VOCB = Namespace("https://www.nebularis.org/neuro-semantic/lattice/vocabulary#")
    bindings = {
        AEOV.GeoPrecisionContract: AEOV.GeoPrecisionScheme,
        AEOV.ControlKindContract: AEOV.ControlKindScheme,
        AEOV.InterestKindContract: AEOV.InterestKindScheme,
        AEOV.ValueTypeContract: AEOV.ValueTypeScheme,
        AEOV.ValuationBasisContract: AEOV.ValuationBasisScheme,
        AEOV.ValuationMethodContract: AEOV.ValuationMethodScheme,
        AEOV.LegalFormContract: AEOV.LegalFormScheme,
    }
    for contract, scheme in bindings.items():
        assert (contract, RDF.type, VOCB.SchemeContract) in data
        assert (contract, VOCB.boundScheme, scheme) in data
    schemes = set(data.subjects(RDF.type, VOC.ConceptScheme))
    assert schemes == {
        AEOV.GeoPrecisionScheme,
        AEOV.ControlKindScheme,
        AEOV.InterestKindScheme,
        AEOV.ValueTypeScheme,
        AEOV.ValuationBasisScheme,
        AEOV.ValuationMethodScheme,
        AEOV.LegalFormScheme,
        AEOV.ProgrammeRoleScheme,
    }


# ---- AIR41-03: aeo:territory and aeo:assetClass specialise cls: properties ----------------------


CLS = Namespace("https://www.nebularis.org/neuro-semantic/lattice/applied/classification#")


def test_air41_03_territory_and_asset_class_specialise_classification():
    from rdflib.namespace import RDFS

    spec = _spec()
    assert (AEO.territory, RDFS.subPropertyOf, CLS.territory) in spec
    assert (AEO.assetClass, RDFS.subPropertyOf, CLS.assetClass) in spec


# ---- AIR41-04: the example conforms -------------------------------------------------------------


def test_air41_04_example_has_no_results():
    assert results(_fixture()) == []


# ---- AIR41-05: location without a territory ------------------------------------------------------


def test_air41_05_location_without_territory_is_rejected():
    data = _fixture()
    data.remove((EX.warehouse, AEO.territory, None))
    assert LOCATION in shapes_for(EX.warehouse, data)


# ---- AIR41-06: asset with both locatedAt and presence --------------------------------------------


def test_air41_06_asset_with_locatedat_and_presence_is_rejected():
    data = _fixture()
    presence = BNode()
    data.add((presence, RDF.type, AEO.Presence))
    data.add((presence, AEO.presenceLocation, EX.warehouse))
    data.add((EX["factory-building"], AEO.presence, presence))
    assert ASSET in shapes_for(EX["factory-building"], data)


# ---- AIR41-07: valuation with both, and with neither ----------------------------------------------


def test_air41_07_valuation_with_both_amount_and_rate_is_rejected():
    data = _fixture()
    data.add(
        (
            EX["building-valuation"],
            AEO.rate,
            Literal("1", datatype=XSD.decimal),
        )
    )
    assert VALUATION in shapes_for(EX["building-valuation"], data)


def test_air41_07_valuation_with_neither_amount_nor_rate_is_rejected():
    data = _fixture()
    data.remove((EX["contents-valuation"], AEO.amount, None))
    assert VALUATION in shapes_for(EX["contents-valuation"], data)


# ---- AIR41-08: control cycle ---------------------------------------------------------------------


def test_air41_08_control_cycle_is_rejected():
    data = _fixture()
    cycle = BNode()
    data.add((cycle, RDF.type, AEO.ControlRelation))
    data.add((cycle, AEO.controller, EX["acme-manufacturing"]))
    data.add((cycle, AEO.controlled, EX["acme-holdings"]))
    data.add((cycle, AEO.controlKind, AEOV.Subsidiary))
    found = {shape for _, shape, _ in results(data) if shape == CONTROL_RELATION}
    assert CONTROL_RELATION in found


# ---- AIR41-09: a location in two exposure set versions --------------------------------------------


def test_air41_09_location_in_two_exposure_sets_is_rejected():
    data = _fixture()
    other = EX["other-schedule"]
    data.add((other, RDF.type, AEO.ExposureSet))
    data.add((other, AEO.hasLocation, EX.factory))
    assert MEMBERSHIP in shapes_for(EX.factory, data)


# ---- AIR41-10: exposure set without a reporting unit -----------------------------------------------


def test_air41_10_exposure_set_without_reporting_unit_is_rejected():
    data = _fixture()
    data.remove((EX["schedule-2027"], AEO.reportingUnit, None))
    assert EXPOSURE_SET in shapes_for(EX["schedule-2027"], data)


# ---- AIR41-11: every region of later slices is present and empty -----------------------------------


def test_air41_11_every_region_of_later_slices_is_present_and_empty():
    readme = (MODULE / "README.md").read_text(encoding="utf-8")
    for region in (
        "zones-attributes-assessments",
        "dependencies-metrics-units",
        "losses-requirements-cover",
        "liability",
    ):
        begin = f"# ==== BEGIN README SECTION {region}"
        end = f"# ==== END README SECTION {region} ===="
        assert begin in readme, region
        assert end in readme, region
        assert readme.index(begin) < readme.index(end), region


# ---- AIR41-12: aeo:industry, aeo:domicile specialise cls: properties, legal form bound -----------


def test_air41_12_industry_and_domicile_specialise_classification():
    from rdflib.namespace import RDFS

    spec = _spec()
    assert (AEO.industry, RDFS.subPropertyOf, CLS.industry) in spec
    assert (AEO.domicile, RDFS.subPropertyOf, CLS.territory) in spec


# ---- AIR41-13: a legal entity with two domiciles --------------------------------------------------


def test_air41_13_legal_entity_with_two_domiciles_is_rejected():
    data = _fixture()
    data.add((EX["acme-manufacturing"], AEO.domicile, EX["second-domicile"]))
    assert LEGAL_ENTITY in shapes_for(EX["acme-manufacturing"], data)


# ---- AIR41-14: LendersLossPayee is broader-linked to LossPayee, every role/form has a note --------


def test_air41_14_lenders_loss_payee_broader_and_every_role_and_form_documented():
    vocab = _vocab()
    assert (AEOV.LendersLossPayee, SKOS.broader, AEOV.LossPayee) in vocab
    roles = set(vocab.subjects(RDF.type, URIRef("https://www.nebularis.org/neuro-semantic/lattice/party#Role")))
    legal_forms = set(vocab.subjects(SKOS.inScheme, AEOV.LegalFormScheme))
    for node in roles | legal_forms:
        notes = list(vocab.objects(node, SKOS.note))
        assert notes, node
        assert any(n.language == "en" for n in notes), node
