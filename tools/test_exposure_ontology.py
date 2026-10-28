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
import lattice_repo_catalogue
from rdflib import BNode, Graph, Literal, Namespace, URIRef
from rdflib.namespace import OWL, RDF, RDFS, XSD

ROOT = Path(__file__).resolve().parents[1]
RELEASE = lattice_repo_catalogue.load(ROOT).release_version
MODULE = ROOT / "ontology" / "applied" / "insurance" / "exposure"
VOCAB_SHAPES = ROOT / "ontology" / "vocabulary" / "shapes"

AEO = Namespace("https://www.nebularis.org/neuro-semantic/lattice/insurance/exposure#")
AEOV = Namespace("https://www.nebularis.org/neuro-semantic/lattice/insurance/exposure/vocab#")
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
CONTROL_RELATION = AEO.ControlRelationShape
DOCUMENTATION = AEO.DocumentationShape

# AIR-4.2
ZONE_DESIGNATION = AEO.ZoneDesignationShape
ZONE_IN_TERRITORY = AEO.ZoneInTerritoryShape
SPATIAL_JOIN = AEO.SpatialJoinShape
POOL_PARTICIPATION = AEO.PoolParticipationShape
ASSESSMENT = AEO.AssessmentShape
ATTRIBUTE_VALUE = AEO.AttributeValueShape
SINGLE_VALUED_TYPES = AEO.SingleValuedTypesShape
SCREENING = AEO.ScreeningShape
PERIL_COMPLETENESS = AEO.PerilCompletenessShape
GEO_PRECISION_FOR_PERIL = AEO.GeoPrecisionForPerilShape
CONSTRUCTION_PROTECTION_PROFILE = AEO.ConstructionProtectionProfileShape
CONSTRUCTION_PROTECTION_PROFILE_OUTSIDE_FAMILY = AEO.ConstructionProtectionProfileOutsideFamilyShape
CYBER_POSTURE_PROFILE = AEO.CyberPostureProfileShape
CYBER_POSTURE_PROFILE_OUTSIDE_FAMILY = AEO.CyberPostureProfileOutsideFamilyShape

PRL = Namespace("https://www.nebularis.org/neuro-semantic/lattice/insurance/peril#")
PRLV = Namespace("https://www.nebularis.org/neuro-semantic/lattice/insurance/peril/vocab#")


def _graph(*paths: Path) -> Graph:
    g = Graph()
    for path in paths:
        g.parse(path)
    return g


def _spec() -> Graph:
    return _graph(MODULE / "spec" / "exposure.ttl")


def _vocab() -> Graph:
    return _graph(MODULE / "vocab" / "exposure-vocab.ttl")


PERIL = ROOT / "ontology" / "applied" / "insurance" / "peril"


FIXTURE_PATHS = (
    MODULE / "spec" / "exposure.ttl",
    MODULE / "vocab" / "exposure-vocab.ttl",
    PERIL / "spec" / "peril.ttl",
    PERIL / "vocab" / "peril-vocab.ttl",
    PERIL / "vocab" / "peril-intensity.ttl",
    MODULE / "examples" / "core.ttl",
    MODULE / "examples" / "attributes.ttl",
)
_FIXTURE_GRAPH: Graph | None = None  # the parsed FIXTURE_PATHS, set by _cached_graphs


def _fixture() -> Graph:
    """spec + vocab + peril's vocab and intensity documents (for
    prl:relevantAttribute / prl:minimumGeoPrecision, AIR-4.2) + the core
    and attributes fixtures, fresh per call so tests can mutate their own
    copy safely. The seven files are parsed once for the session and each
    call copies them: parsing took about 0.55s a call, 11s over the file."""
    return Graph() + _FIXTURE_GRAPH


SHAPE_PATHS = (
    MODULE / "shapes" / "structural.ttl",
    MODULE / "shapes" / "constraints.ttl",
    MODULE / "shapes" / "profiles" / "construction-protection.ttl",
    MODULE / "shapes" / "profiles" / "cyber-posture.ttl",
)


def _shapes() -> Graph:
    return _graph(*SHAPE_PATHS)


SHAPES = _shapes()


@pytest.fixture(scope="module", autouse=True)
def _cached_graphs(request: pytest.FixtureRequest, graph_cache, validated) -> None:
    """TM1/TM2: shared, session-scoped shapes graph and validation cache
    (python-test-melting)."""
    module = request.module
    module.SHAPES = graph_cache(*SHAPE_PATHS)
    module._FIXTURE_GRAPH = graph_cache(*FIXTURE_PATHS)
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


# ---- AIR42-01: spec/vocab import closures, every import resolves (supersedes AIR41-01's ----
# ---- "peril not imported" check, now obsolete: AIR-4.2 imports peril-vocab deliberately) -----


def test_air42_01_spec_and_vocab_parse_every_import_resolves():
    spec = _spec()
    vocab = _vocab()
    spec_imports = {str(o) for o in spec.objects(None, OWL.imports)}
    assert spec_imports == {
        f"https://www.nebularis.org/neuro-semantic/lattice/foundation/{RELEASE}",
        f"https://www.nebularis.org/neuro-semantic/lattice/vocabulary/{RELEASE}",
        f"https://www.nebularis.org/neuro-semantic/lattice/quantification/{RELEASE}",
        f"https://www.nebularis.org/neuro-semantic/lattice/party/{RELEASE}",
        "https://www.nebularis.org/neuro-semantic/lattice/insurance/common/0.8.0",
        f"https://www.nebularis.org/neuro-semantic/lattice/eligibility/{RELEASE}",
    }
    vocab_imports = {str(o) for o in vocab.objects(None, OWL.imports)}
    assert vocab_imports == {
        "https://www.nebularis.org/neuro-semantic/lattice/insurance/exposure/0.3.1",
        f"https://www.nebularis.org/neuro-semantic/lattice/vocabulary/{RELEASE}",
        f"https://www.nebularis.org/neuro-semantic/lattice/foundation/{RELEASE}",
        "https://www.nebularis.org/neuro-semantic/lattice/insurance/common-vocab/0.8.0",
        "https://www.nebularis.org/neuro-semantic/lattice/insurance/peril-vocab/0.7.0",
        "https://www.nebularis.org/neuro-semantic/lattice/applied/classification-vocab/0.4.0",
    }


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
    assert schemes >= {
        AEOV.GeoPrecisionScheme,
        AEOV.ControlKindScheme,
        AEOV.InterestKindScheme,
        AEOV.ValueTypeScheme,
        AEOV.ValuationBasisScheme,
        AEOV.ValuationMethodScheme,
        AEOV.LegalFormScheme,
        AEOV.ProgrammeRoleScheme,
    }, "AIR-4.1's eight schemes, now a subset of a larger vocabulary (AIR-4.2 adds many more)"


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


# ---- AIR41-09 (restated by AIR-4.2a, TD-49): a location in two exposure set versions ----------------


def test_air41_09_location_in_two_exposure_sets_is_shared_not_rejected():
    data = _fixture()
    other = EX["other-schedule"]
    data.add((other, RDF.type, AEO.ExposureSet))
    data.add((other, AEO.hasLocation, EX.factory))
    assert not shapes_for(EX.factory, data)


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


# ==== AIR-4.2: zones, pool participation, attributes, assessments ================================

# ---- AIR42-02: this slice's bound contracts conform and are bound to their reference scheme ------


def test_air42_02_bound_contracts_conform_and_bound():
    data = _vocab()
    conforms, _, report = validate(
        data, shacl_graph=_graph(VOCAB_SHAPES / "structural.ttl", VOCAB_SHAPES / "constraints.ttl"),
        advanced=True, inference="none", allow_warnings=True,
    )
    assert conforms, report
    bound = {
        AEOV.AttributeTypeContract: AEOV.AttributeTypeScheme,
        AEOV.DesignationSourceContract: AEOV.DesignationSourceScheme,
        AEOV.AssessmentKindContract: AEOV.AssessmentKindScheme,
        AEOV.ProfileFamilyContract: AEOV.ProfileFamilyScheme,
        AEOV.FrequencyScaleContract: AEOV.FrequencyScale,
        AEOV.SusceptibilityContract: AEOV.SusceptibilityScale,
        AEOV.SprinklerSystemContract: AEOV.SprinklerSystemScheme,
        AEOV.MfaCoverageContract: AEOV.MfaCoverageScheme,
        AEOV.BackupStrategyContract: AEOV.BackupStrategyScheme,
        AEOV.SanctionsScreeningOutcomeContract: AEOV.SanctionsScreeningOutcomeScheme,
    }
    for contract, scheme in bound.items():
        assert (contract, VOC.boundScheme, scheme) in data, contract
    # Market-only contracts stay unbound at this stage (AIR-4.6 binds a scheme per market).
    for unbound in (AEOV.ConstructionClassContract, AEOV.OccupancyClassContract, AEOV.PublicProtectionClassContract):
        assert (unbound, VOC.boundScheme, None) not in data, unbound


# ---- AIR42-03: every attribute type has a form, a family, and the space/contract/datatype it needs


def test_air42_03_every_attribute_type_has_form_family_and_its_value_slot():
    vocab = _vocab()
    types = set(vocab.subjects(SKOS.inScheme, AEOV.AttributeTypeScheme))
    assert types, "expected at least one attribute type"
    for t in types:
        form = vocab.value(t, AEO.valueForm)
        assert form is not None, t
        assert vocab.value(t, AEO.attributeFamily) is not None, t
        if form == AEOV.QuantityForm:
            assert vocab.value(t, AEO.valueSpace) is not None, t
        elif form == AEOV.ConceptForm:
            assert vocab.value(t, AEO.valueContract) is not None, t
        elif form == AEOV.LiteralForm:
            assert vocab.value(t, AEO.literalDatatype) is not None, t
        else:
            pytest.fail(f"{t} has an unrecognised value form {form}")


# ---- AIR42-04: the example conforms, no result, no warning ---------------------------------------


def test_air42_04_example_has_no_results():
    assert results(_fixture()) == []


# ---- AIR42-05: an attribute value with both a concept and a quantity -----------------------------


def test_air42_05_attribute_value_with_concept_and_quantity_is_rejected():
    data = _fixture()
    data.add(
        (
            EX["warehouse-construction-class"],
            AEO.quantityValue,
            data.value(EX["warehouse-storeys"], AEO.quantityValue),
        )
    )
    assert ATTRIBUTE_VALUE in shapes_for(EX["warehouse-construction-class"], data)


# ---- AIR42-06: FirstFloorHeight with a quantity on the wrong space --------------------------------


def test_air42_06_first_floor_height_on_count_space_is_rejected():
    data = _fixture()
    qv = data.value(EX["warehouse-first-floor-height"], AEO.quantityValue)
    data.remove((qv, QNT.onSpace, None))
    data.add((qv, QNT.onSpace, AEOV.Count))
    assert ATTRIBUTE_VALUE in shapes_for(EX["warehouse-first-floor-height"], data)


# ---- AIR42-07: a zone designation whose zone is in a scheme bound only for another territory -------


def test_air42_07_zone_in_scheme_bound_for_another_territory_is_rejected():
    data = _fixture()
    other_scheme = EX["other-territory-flood-scheme"]
    data.add((other_scheme, RDF.type, VOC.ConceptScheme))
    data.add((AEOV.FloodZoneContract, VOC.boundScheme, other_scheme))
    assert ZONE_IN_TERRITORY in shapes_for(EX["warehouse-flood-zone"], data)


# ---- AIR42-08: the example without its first-floor height ------------------------------------------


def test_air42_08_example_without_first_floor_height_warns_once_for_flood():
    data = _fixture()
    data.remove((EX["warehouse-survey"], AEO.hasAttribute, EX["warehouse-first-floor-height"]))
    data.remove((EX["warehouse-first-floor-height"], None, None))
    found = [(sev, shape, focus) for sev, shape, focus in results(data) if shape == PERIL_COMPLETENESS]
    assert len(found) == 1, found
    assert found[0][2] == EX.warehouse


# ---- AIR42-09: the example with the flood location at Postcode precision --------------------------


def test_air42_09_flood_location_at_postcode_precision_warns_once():
    data = _fixture()
    data.remove((EX.warehouse, AEO.geoPrecision, None))
    data.add((EX.warehouse, AEO.geoPrecision, AEOV.Postcode))
    found = [(sev, shape, focus) for sev, shape, focus in results(data) if shape == GEO_PRECISION_FOR_PERIL]
    assert len(found) == 1, found


# ---- AIR42-10: a sanctions outcome in a questionnaire, not a screening run -------------------------


def test_air42_10_sanctions_outcome_outside_screening_run_is_rejected():
    data = _fixture()
    av = EX["acme-sanctions-outcome"]
    data.add((av, RDF.type, AEO.AttributeValue))
    data.add((av, AEO.attributeType, AEOV.SanctionsScreeningOutcome))
    data.add((av, AEO.conceptValue, AEOV.NoMatch))
    data.add((EX["acme-cyber-questionnaire"], AEO.hasAttribute, av))
    assert SCREENING in shapes_for(EX["acme-cyber-questionnaire"], data)


# ---- AIR42-11: a cyber posture assessment without MfaCoverage --------------------------------------


def test_air42_11_cyber_posture_assessment_without_mfa_coverage_is_rejected():
    data = _fixture()
    data.remove((EX["acme-cyber-questionnaire"], AEO.hasAttribute, EX["acme-mfa-coverage"]))
    data.remove((EX["acme-mfa-coverage"], None, None))
    assert CYBER_POSTURE_PROFILE in shapes_for(EX["acme-cyber-questionnaire"], data)


# ---- AIR42-12: a link stated on N.HYD.FLD is read over a location exposed to N.HYD.FLD.PLU ----------


def test_air42_12_completeness_shape_reads_a_link_stated_on_a_broader_cause():
    data = _fixture()
    data.add((EX.unassessed, RDF.type, AEO.Location))
    data.add((EX["unassessed-identity"], RDF.type, AEO.LocationIdentity))
    data.add((EX["unassessed-identity"], RDF.type, FND.PersistentIdentity))
    data.add((EX.unassessed, FND.hasIdentity, EX["unassessed-identity"]))
    data.add((EX.unassessed, AEO.territory, EX["great-britain"]))
    pp = EX["unassessed-flood-pool"]
    data.add((pp, RDF.type, AEO.PoolParticipation))
    data.add((EX.unassessed, AEO.poolParticipation, pp))
    scope = BNode()
    data.add((scope, RDF.type, FND.TemporalScope))
    data.add((scope, FND.validFrom, Literal("2027-01-01T00:00:00Z", datatype=XSD.dateTime)))
    data.add((pp, FND.hasTemporalScope, scope))
    data.add((pp, AEO.pool, EX["flood-reinsurance-pool"]))
    data.add((pp, AEO.perilScope, PRLV["N.HYD.FLD.PLU"]))
    found = [(sev, shape, focus) for sev, shape, focus in results(data) if shape == PERIL_COMPLETENESS]
    assert any(focus == EX.unassessed for _, _, focus in found), found


# ---- AIR42-13: every concept of this slice has a note ----------------------------------------------


def test_air42_13_documentation_shape_has_no_results():
    found = [shape for _, shape, _ in results(_fixture()) if shape == DOCUMENTATION]
    assert found == []


def _without_english_note(data: Graph, concept: URIRef, replacement: Literal | None) -> Graph:
    for note in list(data.objects(concept, SKOS.note)):
        data.remove((concept, SKOS.note, note))
    if replacement is not None:
        data.add((concept, SKOS.note, replacement))
    return data


@pytest.mark.parametrize("replacement", [None, Literal("une note", lang="fr"), Literal("a note", lang="en-GB"), Literal("a note")])
def test_air42_13_a_concept_with_no_english_note_is_rejected(replacement):
    """Only a note tagged exactly @en counts, so no note, a note in another language, a regional
    tag and an untagged note are each a missing note."""
    data = _without_english_note(_fixture(), AEOV.Rooftop, replacement)
    assert shapes_for(AEOV.Rooftop, data) == {DOCUMENTATION}


def test_air42_13_a_concept_of_another_vocabulary_is_not_checked_by_this_shape():
    """The peril concepts in the fixture are checked by the peril shapes, not this one."""
    concept = next(iter(_fixture().subjects(SKOS.inScheme, PRLV.CauseScheme)))
    data = _without_english_note(_fixture(), concept, None)
    assert DOCUMENTATION not in shapes_for(concept, data)


# ---- AIR-66 (TD-66): versions are never edited, and content names identities -------------------------

VERSIONS = MODULE / "examples" / "versions.ttl"
EXPOSURE_SET_SHAPE = AEO.ExposureSetShape


def _versions() -> Graph:
    return _graph(MODULE / "spec" / "exposure.ttl", MODULE / "vocab" / "exposure-vocab.ttl", VERSIONS)


def test_air66_01_located_at_and_value_of_range_over_identities():
    spec = _spec()
    assert (AEO.locatedAt, RDFS.range, AEO.LocationIdentity) in spec
    union = spec.value(AEO.valueOf, RDFS.range)
    members = set(spec.items(spec.value(union, OWL.unionOf)))
    assert members == {AEO.AssetIdentity, AEO.LocationIdentity}


def test_air66_02_versions_example_conforms():
    assert results(_versions()) == []


def test_air66_03_succession_does_not_edit_version_1():
    data = _versions()
    v1, v2 = EX["schedule-v1"], EX["schedule-v2"]
    assert (v1, FND.supersededBy, v2) in data
    assert list(data.objects(v1, FND.hasGovernanceState)) == [FND.Active]
    for scope in data.objects(v1, FND.hasTemporalScope):
        assert (scope, FND.validTo, None) not in data
    assert not list(data.triples((None, FND.validTo, None)))


def test_air66_04_one_location_changing_writes_one_version_and_shares_the_rest():
    data = _versions()
    v1, v2 = EX["schedule-v1"], EX["schedule-v2"]
    assert set(data.objects(v1, AEO.hasAsset)) == set(data.objects(v2, AEO.hasAsset))
    assert set(data.objects(v1, AEO.hasValuation)) == set(data.objects(v2, AEO.hasValuation))
    assert set(data.objects(v1, AEO.hasLocation)) ^ set(data.objects(v2, AEO.hasLocation)) == {
        EX["warehouse-v1"],
        EX["warehouse-v2"],
    }
    assert len(set(data.subjects(FND.hasIdentity, EX["warehouse-identity"]))) == 2
    assert len(set(data.subjects(RDF.type, AEO.Asset))) == 2
    assert len(set(data.subjects(RDF.type, AEO.Valuation))) == 2


def test_air66_05_asset_naming_a_location_version_is_rejected():
    data = _versions()
    data.set((EX["warehouse-stock"], AEO.locatedAt, EX["warehouse-v2"]))
    assert ASSET in shapes_for(EX["warehouse-stock"], data)


def test_air66_06_valuation_naming_an_asset_version_is_rejected():
    data = _versions()
    data.set((EX["stock-valuation"], AEO.valueOf, EX["warehouse-stock"]))
    assert VALUATION in shapes_for(EX["stock-valuation"], data)


def test_air66_07_set_listing_an_asset_whose_location_identity_it_does_not_list_is_rejected():
    data = _versions()
    data.remove((EX["schedule-v2"], AEO.hasLocation, EX["warehouse-v2"]))
    assert EXPOSURE_SET_SHAPE in shapes_for(EX["schedule-v2"], data)
    assert EXPOSURE_SET_SHAPE not in shapes_for(EX["schedule-v1"], data)


def test_air66_08_set_listing_two_versions_of_one_location_identity_is_rejected():
    data = _versions()
    data.add((EX["schedule-v2"], AEO.hasLocation, EX["warehouse-v1"]))
    assert EXPOSURE_SET_SHAPE in shapes_for(EX["schedule-v2"], data)


def test_air66_09_set_listing_a_valuation_whose_asset_identity_it_does_not_list_is_rejected():
    data = _versions()
    data.remove((EX["schedule-v2"], AEO.hasAsset, EX["warehouse-stock"]))
    assert EXPOSURE_SET_SHAPE in shapes_for(EX["schedule-v2"], data)
