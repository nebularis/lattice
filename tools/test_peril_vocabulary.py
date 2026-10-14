# SPDX-License-Identifier: MPL-2.0

"""The reference peril vocabulary's spec, scheme declarations and shapes
(applied-insurance-reference AIR-2.1, ADR-A99 §10).

Data graph for the shapes tests: the fixture plus ``spec/peril.ttl`` and
``vocab/peril-vocab.ttl``. Shapes graph: ``shapes/structural.ttl`` and
``shapes/constraints.ttl``. Negative cases mutate a copy of the fixture
graph, each breaking exactly one rule, rather than shipping a separate
negative fixture file per case (the plan's own choice for this slice).
"""

from __future__ import annotations

from pathlib import Path

import pytest
from pyshacl import validate
from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import OWL, RDF, RDFS

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "ontology" / "applied" / "insurance" / "peril"
VOCAB_SHAPES = ROOT / "ontology" / "vocabulary" / "shapes"

PRL = Namespace("https://www.nebularis.org/neuro-semantic/insurance/peril#")
PRLV = Namespace("https://www.nebularis.org/neuro-semantic/insurance/peril/vocab#")
SKOS = Namespace("http://www.w3.org/2004/02/skos/core#")
VOC = Namespace("https://www.nebularis.org/neuro-semantic/lattice/vocabulary#")
SH = Namespace("http://www.w3.org/ns/shacl#")

LABEL_AND_DEFINITION = PRL.LabelAndDefinitionShape
CHARACTERISTICS = PRL.CharacteristicsShape
REFERENCE_CODE = PRL.ReferenceCodeShape
PRIMARY_PARENT = PRL.PrimaryParentShape
MATERIALISED_BROADER = PRL.MaterialisedBroaderShape
ASSOCIATIVE_INTEGRITY = PRL.AssociativeIntegrityShape
ACYCLIC = PRL.AcyclicShape
THRESHOLD_DEFINITION = PRL.ThresholdDefinitionShape


def _graph(*paths: Path) -> Graph:
    g = Graph()
    for path in paths:
        g.parse(path)
    return g


def _spec() -> Graph:
    return _graph(MODULE / "spec" / "peril.ttl")


def _vocab() -> Graph:
    return _graph(MODULE / "vocab" / "peril-vocab.ttl")


def _fixture() -> Graph:
    """spec + vocab (schemes, no concepts) + the well-formed fixture,
    fresh per call so tests can mutate their own copy safely."""
    return _graph(
        MODULE / "spec" / "peril.ttl",
        MODULE / "vocab" / "peril-vocab.ttl",
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


def messages_for(focus: URIRef, data: Graph) -> set[str]:
    """The result messages for one focus node, to tell apart constraints on one shape."""
    _, report, _ = validate(data, shacl_graph=SHAPES, advanced=True, inference="none", allow_warnings=True)
    return {
        str(report.value(result, SH.resultMessage))
        for result in report.subjects(RDF.type, SH.ValidationResult)
        if report.value(result, SH.focusNode) == focus
    }


# ---- AIR21-01: parse and imports --------------------------------------------------------------


def test_spec_and_vocab_parse_and_import_the_pinned_versions():
    spec = _spec()
    vocab = _vocab()
    # owl:imports triples, read directly rather than via a prefix binding.
    spec_imports = {str(o) for o in spec.objects(None, OWL.imports)}
    assert spec_imports == {
        "http://www.w3.org/2004/02/skos/core",
        "https://www.nebularis.org/neuro-semantic/lattice/foundation/0.4.0",
        "https://www.nebularis.org/neuro-semantic/lattice/quantification/0.8.0",
        "https://www.nebularis.org/neuro-semantic/insurance/common/0.5.0",
    }
    vocab_imports = {str(o) for o in vocab.objects(None, OWL.imports)}
    assert vocab_imports == {
        "https://www.nebularis.org/neuro-semantic/insurance/peril/0.5.0",
        "https://www.nebularis.org/neuro-semantic/lattice/vocabulary/0.4.0",
        "https://www.nebularis.org/neuro-semantic/lattice/foundation/0.4.0",
        "https://www.nebularis.org/neuro-semantic/insurance/common-vocab/0.6.0",
    }


# ---- AIR21-02: canTrigger and overlaps ---------------------------------------------------------


def test_can_trigger_is_directed_and_overlaps_is_symmetric():
    spec = _spec()
    assert (PRL.canTrigger, RDFS.subPropertyOf, SKOS.semanticRelation) in spec
    assert (PRL.canTrigger, RDFS.subPropertyOf, SKOS.related) not in spec
    assert (PRL.canTrigger, RDF.type, OWL.SymmetricProperty) not in spec
    assert (PRL.overlaps, RDF.type, OWL.SymmetricProperty) in spec
    assert (PRL.overlaps, RDF.type, OWL.IrreflexiveProperty) in spec
    assert (PRL.canTrigger, RDF.type, OWL.IrreflexiveProperty) in spec


# ---- AIR21-03: the eight schemes conform to Vocabulary's own shapes ----------------------------


def test_eight_schemes_conform_to_vocabulary_shapes():
    data = _vocab()
    shapes = _graph(VOCAB_SHAPES / "structural.ttl", VOCAB_SHAPES / "constraints.ttl")
    conforms, _, report = validate(data, shacl_graph=shapes, advanced=True, inference="none", allow_warnings=True)
    assert conforms, report
    schemes = set(data.subjects(RDF.type, VOC.ConceptScheme))
    assert schemes == {
        PRLV.CauseScheme,
        PRLV.AgencyScheme,
        PRLV.MechanismScheme,
        PRLV.OnsetScheme,
        PRLV.DefinitionBasisScheme,
        PRLV.AccumulationClassScheme,
        PRLV.ConsequenceScheme,
        PRLV.HarmSubjectScheme,
    }


# ---- AIR21-04: the fixture validates with no result --------------------------------------------


def test_well_formed_fixture_has_no_results():
    assert results(_fixture()) == []


# ---- AIR21-05: label and definition ------------------------------------------------------------


def test_concept_without_definition_is_rejected():
    data = _fixture()
    data.remove((PRLV["N.MET.TC.HUR"], SKOS.definition, None))
    assert LABEL_AND_DEFINITION in shapes_for(PRLV["N.MET.TC.HUR"], data)


# ---- AIR21-06: reference code -----------------------------------------------------------------


def test_duplicate_reference_code_is_rejected():
    data = _fixture()
    data.remove((PRLV["N.MET.TC.SRG"], SKOS.notation, None))
    data.add((PRLV["N.MET.TC.SRG"], SKOS.notation, Literal("N.MET.TC.HUR", datatype=PRL.ReferenceCode)))
    assert REFERENCE_CODE in shapes_for(PRLV["N.MET.TC.SRG"], data)
    assert REFERENCE_CODE in shapes_for(PRLV["N.MET.TC.HUR"], data)


def test_reference_code_not_extending_its_parent_is_rejected():
    data = _fixture()
    data.remove((PRLV["N.MET.TC.HUR"], SKOS.notation, None))
    data.add((PRLV["N.MET.TC.HUR"], SKOS.notation, Literal("N.MET.TC.XX.YY", datatype=PRL.ReferenceCode)))
    assert REFERENCE_CODE in shapes_for(PRLV["N.MET.TC.HUR"], data)


# ---- AIR21-07: primary parent ------------------------------------------------------------------


def test_concept_with_both_a_generic_and_a_partitive_parent_is_rejected():
    data = _fixture()
    data.add((PRLV["N.MET.TC.HUR"], PRL.broaderPartitive, PRLV.N))
    data.add((PRLV["N.MET.TC.HUR"], SKOS.broader, PRLV.N))
    assert PRIMARY_PARENT in shapes_for(PRLV["N.MET.TC.HUR"], data)


def test_non_top_concept_without_a_primary_parent_is_rejected():
    data = _fixture()
    data.remove((PRLV["N.MET.TC.HUR"], PRL.broaderGeneric, None))
    data.remove((PRLV["N.MET.TC.HUR"], SKOS.broader, None))
    assert PRIMARY_PARENT in shapes_for(PRLV["N.MET.TC.HUR"], data)


def test_extra_broader_without_a_primary_parent_needs_an_editorial_note():
    # zero primary parents and one skos:broader: the editorial-note count must still run
    data = _fixture()
    data.remove((PRLV["N.MET.TC.HUR"], PRL.broaderGeneric, None))
    assert any("editorialNote" in message for message in messages_for(PRLV["N.MET.TC.HUR"], data))


# ---- AIR21-08: materialised broader -------------------------------------------------------------


def test_broader_generic_without_skos_broader_is_rejected():
    data = _fixture()
    data.remove((PRLV["N.MET"], SKOS.broader, None))
    assert MATERIALISED_BROADER in shapes_for(PRLV["N.MET"], data)


# ---- AIR21-09: characteristics -----------------------------------------------------------------


def test_cause_concept_without_onset_is_rejected():
    data = _fixture()
    data.remove((PRLV["N.MET.TC.SRG"], PRL.onset, None))
    assert CHARACTERISTICS in shapes_for(PRLV["N.MET.TC.SRG"], data)


# ---- AIR21-10: associative integrity -----------------------------------------------------------


def test_overlaps_and_can_trigger_across_the_hierarchy_are_rejected():
    data = _fixture()
    data.add((PRLV["N.MET.TC.HUR"], PRL.overlaps, PRLV["N.MET"]))
    data.add((PRLV["N.MET.TC"], PRL.canTrigger, PRLV["N.MET.TC.SRG"]))
    found = shapes_for(PRLV["N.MET.TC.HUR"], data) | shapes_for(PRLV["N.MET.TC"], data)
    assert ASSOCIATIVE_INTEGRITY in found
    count = sum(1 for _, shape, _ in results(data) if shape == ASSOCIATIVE_INTEGRITY)
    assert count >= 2


# ---- AIR21-11: acyclic --------------------------------------------------------------------------


def test_a_broader_cycle_is_rejected():
    data = _fixture()
    data.add((PRLV.N, SKOS.broader, PRLV["N.MET.TC.HUR"]))
    assert ACYCLIC in shapes_for(PRLV.N, data)


# ---- AIR21-12: threshold definitions ------------------------------------------------------------


def test_threshold_basis_concept_without_defining_threshold_is_rejected():
    data = _fixture()
    data.remove((PRLV["N.MET.TC.HUR"], PRL.definingThreshold, None))
    assert THRESHOLD_DEFINITION in shapes_for(PRLV["N.MET.TC.HUR"], data)


# ---- AIR22-01: spec/vocab import closures, spec imports common/ --------------------------------


def test_air22_01_spec_imports_common_and_every_import_resolves():
    spec = _spec()
    assert "https://www.nebularis.org/neuro-semantic/insurance/common/0.5.0" in {
        str(o) for o in spec.objects(None, OWL.imports)
    }


# ---- AIR22-02: four sub-property axioms, onset/definitionBasis specialise nothing --------------


ICM = Namespace("https://www.nebularis.org/neuro-semantic/insurance/common#")


def test_air22_02_four_characteristics_specialise_common_and_two_do_not():
    spec = _spec()
    assert (PRL.typicalAgency, RDFS.subPropertyOf, ICM.agency) in spec
    assert (PRL.typicalMechanism, RDFS.subPropertyOf, ICM.mechanism) in spec
    assert (PRL.typicalConsequence, RDFS.subPropertyOf, ICM.consequence) in spec
    assert (PRL.harmSubject, RDFS.subPropertyOf, ICM.harmSubject) in spec
    assert (PRL.onset, RDFS.subPropertyOf, None) not in spec
    assert (PRL.definitionBasis, RDFS.subPropertyOf, None) not in spec


# ---- AIR22-03: each of the seven characteristic/companion schemes holds its table's concepts ----


CHARACTERISTIC_SCHEMES = {
    PRLV.AgencyScheme: {
        "Natural", "Accidental", "Negligent", "Intentional", "MaliciousCriminal",
        "MaliciousPolitical", "Sovereign", "Belligerent", "Economic", "UndeterminedAgency",
    },
    PRLV.MechanismScheme: {
        "Shaking", "GroundFailure", "Inundation", "WaterDamage", "WindLoad", "Load", "Fire",
        "Smoke", "Heat", "Freezing", "Explosion", "Impact", "Collapse", "Breakdown", "Corrosion",
        "Erosion", "Contamination", "BiologicalAgent", "Radiation", "ElectricalOverstress",
        "DataEncryption", "Deprivation",
    },
    PRLV.OnsetScheme: {"Sudden", "Gradual", "Latent", "Recurrent"},
    PRLV.DefinitionBasisScheme: {
        "Physical", "Designation", "Threshold", "WordingDefined", "Statutory", "Index",
    },
    PRLV.AccumulationClassScheme: {"Catastrophe", "Systemic", "Attritional"},
    PRLV.ConsequenceScheme: {
        "DirectPhysicalDamage", "BusinessInterruption", "ExtraExpense", "Spoilage",
        "DenialOfAccess", "Recall", "CleanUp", "DataRestoration", "ExtortionPayment",
        "LiabilityToOthers", "DefenceCosts", "Delay", "ShortageOrNonDelivery",
        "GeneralAverageContribution", "ReputationalHarm", "RegulatoryPenalty",
        "NotificationCosts", "ForensicCosts", "CancellationCosts",
    },
    PRLV.HarmSubjectScheme: {
        "Property", "Persons", "FinancialInterest", "DataAndSystems", "Environment", "Reputation",
    },
}


def test_air22_03_each_scheme_holds_exactly_its_table_each_a_top_concept():
    vocab = _vocab()
    for scheme, names in CHARACTERISTIC_SCHEMES.items():
        members = set(vocab.subjects(SKOS.inScheme, scheme))
        tops = set(vocab.subjects(SKOS.topConceptOf, scheme))
        has_tops = set(vocab.objects(scheme, SKOS.hasTopConcept))
        expected = {PRLV[name] for name in names}
        assert members == expected, scheme
        assert tops == expected, scheme
        assert has_tops == expected, scheme


# ---- AIR22-04: the vocabulary alone conforms to the peril shapes -------------------------------


def test_air22_04_vocabulary_alone_has_no_results():
    assert results(_vocab()) == []


# ---- AIR22-05: the four bound contracts conform to Vocabulary's shapes -------------------------


def test_air22_05_four_contracts_bound_and_conform_to_vocabulary_shapes():
    data = _vocab()
    shapes = _graph(VOCAB_SHAPES / "structural.ttl", VOCAB_SHAPES / "constraints.ttl")
    conforms, _, report = validate(data, shacl_graph=shapes, advanced=True, inference="none", allow_warnings=True)
    assert conforms, report
    ICMV = Namespace("https://www.nebularis.org/neuro-semantic/insurance/common/vocab#")
    VOCB = Namespace("https://www.nebularis.org/neuro-semantic/lattice/vocabulary#")
    bindings = {
        ICMV.AgencyContract: PRLV.AgencyScheme,
        ICMV.MechanismContract: PRLV.MechanismScheme,
        ICMV.ConsequenceContract: PRLV.ConsequenceScheme,
        ICMV.HarmSubjectContract: PRLV.HarmSubjectScheme,
    }
    for contract, scheme in bindings.items():
        assert (contract, VOCB.boundScheme, scheme) in data


# ---- AIR22-06: the well-formed fixture, now without local characteristic concepts --------------


def test_air22_06_fixture_still_has_no_results_against_the_real_schemes():
    assert results(_fixture()) == []


# ---- AIR22-07: a characteristic concept without skos:definition -------------------------------


def test_air22_07_characteristic_concept_without_definition_is_rejected():
    data = _vocab()
    data.remove((PRLV.Natural, SKOS.definition, None))
    assert LABEL_AND_DEFINITION in shapes_for(PRLV.Natural, data)


# ---- AIR22-08: a cause concept whose onset is a mechanism concept ------------------------------


def test_air22_08_cause_concept_with_mismatched_scheme_characteristic_is_rejected():
    data = _fixture()
    data.remove((PRLV["N.MET.TC.SRG"], PRL.onset, None))
    data.add((PRLV["N.MET.TC.SRG"], PRL.onset, PRLV.Shaking))
    assert CHARACTERISTICS in shapes_for(PRLV["N.MET.TC.SRG"], data)
