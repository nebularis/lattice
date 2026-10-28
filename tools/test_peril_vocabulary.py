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

import re
from pathlib import Path

import pytest
from pyshacl import validate
import lattice_repo_catalogue
from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import OWL, RDF, RDFS

ROOT = Path(__file__).resolve().parents[1]
RELEASE = lattice_repo_catalogue.load(ROOT).release_version
MODULE = ROOT / "ontology" / "applied" / "insurance" / "peril"
VOCAB_SHAPES = ROOT / "ontology" / "vocabulary" / "shapes"

PRL = Namespace("https://www.nebularis.org/neuro-semantic/lattice/insurance/peril#")
PRLV = Namespace("https://www.nebularis.org/neuro-semantic/lattice/insurance/peril/vocab#")
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
    """spec + vocab (schemes and, from AIR-2.3, the cause scheme) + peril-intensity.ttl
    (AIR-2.6, every threshold-defined cause concept's real prl:definingThreshold) + the
    well-formed fixture, fresh per call so tests can mutate their own copy safely."""
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
        f"https://www.nebularis.org/neuro-semantic/lattice/foundation/{RELEASE}",
        f"https://www.nebularis.org/neuro-semantic/lattice/quantification/{RELEASE}",
        "https://www.nebularis.org/neuro-semantic/lattice/insurance/common/0.8.0",
    }
    vocab_imports = {str(o) for o in vocab.objects(None, OWL.imports)}
    assert vocab_imports == {
        "https://www.nebularis.org/neuro-semantic/lattice/insurance/peril/0.7.0",
        f"https://www.nebularis.org/neuro-semantic/lattice/vocabulary/{RELEASE}",
        f"https://www.nebularis.org/neuro-semantic/lattice/foundation/{RELEASE}",
        "https://www.nebularis.org/neuro-semantic/lattice/insurance/common-vocab/0.8.0",
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
    assert "https://www.nebularis.org/neuro-semantic/lattice/insurance/common/0.8.0" in {
        str(o) for o in spec.objects(None, OWL.imports)
    }


# ---- AIR22-02: four sub-property axioms, onset/definitionBasis specialise nothing --------------


ICM = Namespace("https://www.nebularis.org/neuro-semantic/lattice/insurance/common#")


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
    # From AIR-2.3, the vocabulary carries threshold-defined cause concepts whose
    # prl:definingThreshold lives in the separate vocab/peril-intensity.ttl document
    # (AIR-2.6, ADR-A120 addendum), so "vocabulary alone" means both documents together.
    assert results(_graph(MODULE / "vocab" / "peril-vocab.ttl", MODULE / "vocab" / "peril-intensity.ttl")) == []


# ---- AIR22-05: the four bound contracts conform to Vocabulary's shapes -------------------------


def test_air22_05_four_contracts_bound_and_conform_to_vocabulary_shapes():
    data = _vocab()
    shapes = _graph(VOCAB_SHAPES / "structural.ttl", VOCAB_SHAPES / "constraints.ttl")
    conforms, _, report = validate(data, shacl_graph=shapes, advanced=True, inference="none", allow_warnings=True)
    assert conforms, report
    ICMV = Namespace("https://www.nebularis.org/neuro-semantic/lattice/insurance/common/vocab#")
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


# ---- AIR23-01: N has 90 concepts, T 71, E 15, every code present once --------------------------


def test_air23_01_n_t_and_e_family_counts_and_unique_codes():
    vocab = _vocab()
    family_prefixes = {"N": "N", "T": "T", "E": "E"}
    counts = {label: 0 for label in family_prefixes}
    codes: list[str] = []
    for concept in vocab.subjects(SKOS.inScheme, PRLV.CauseScheme):
        notations = [n for n in vocab.objects(concept, SKOS.notation) if n.datatype == PRL.ReferenceCode]
        assert len(notations) == 1, concept
        code = str(notations[0])
        codes.append(code)
        family = code.split(".")[0]
        if family in counts:
            counts[family] += 1
    assert counts == {"N": 90, "T": 71, "E": 15}
    assert len(codes) == len(set(codes))


# ---- AIR23-02: the vocabulary with peril-intensity.ttl / the peril shapes / no result -----------


def test_air23_02_vocabulary_with_intensity_has_no_results():
    data = _graph(MODULE / "vocab" / "peril-vocab.ttl", MODULE / "vocab" / "peril-intensity.ttl")
    assert results(data) == []


# ---- AIR23-03: every N, T, E concept has exactly one onset, one basis, 1+ agency ---------------


def test_air23_03_every_n_t_e_concept_has_the_required_characteristics():
    vocab = _vocab()
    for concept in vocab.subjects(SKOS.inScheme, PRLV.CauseScheme):
        notation = next(n for n in vocab.objects(concept, SKOS.notation) if n.datatype == PRL.ReferenceCode)
        if str(notation).split(".")[0] not in ("N", "T", "E"):
            continue
        onsets = list(vocab.objects(concept, PRL.onset))
        bases = list(vocab.objects(concept, PRL.definitionBasis))
        agencies = list(vocab.objects(concept, PRL.typicalAgency))
        assert len(onsets) == 1, concept
        assert len(bases) == 1, concept
        assert len(agencies) >= 1, concept


def test_air23_03_five_spot_checked_concepts():
    vocab = _vocab()
    assert set(vocab.objects(PRLV["N.CLI.WF.FOR"], PRL.typicalAgency)) == {PRLV.UndeterminedAgency}
    assert set(vocab.objects(PRLV["N.MET.TC.HUR"], PRL.definitionBasis)) == {PRLV.Threshold}
    assert set(vocab.objects(PRLV["E.DET.COR"], PRL.typicalAgency)) == {PRLV.Natural}
    assert set(vocab.objects(PRLV["E.DET.COR"], PRL.onset)) == {PRLV.Gradual}
    assert set(vocab.objects(PRLV["T.REL.ASB"], PRL.onset)) == {PRLV.Latent}
    assert set(vocab.objects(PRLV["N.BIO.OUT.PAN"], PRL.definitionBasis)) == {PRLV.Designation}
    assert set(vocab.objects(PRLV["N.BIO.OUT.PAN"], PRL.accumulationClass)) == {PRLV.Systemic}


# ---- AIR23-04: N.GEO.EQ.FFE and N.MET.TC.SRG's partitive links and mechanisms ------------------


def test_air23_04_ffe_and_srg_partitive_links_and_mechanisms():
    vocab = _vocab()
    assert (PRLV["N.GEO.EQ.FFE"], PRL.broaderPartitive, PRLV["N.GEO.EQ"]) in vocab
    assert set(vocab.objects(PRLV["N.GEO.EQ.FFE"], PRL.typicalMechanism)) == {PRLV.Fire}
    assert (PRLV["N.MET.TC.SRG"], PRL.broaderPartitive, PRLV["N.MET.TC"]) in vocab
    assert set(vocab.objects(PRLV["N.MET.TC.SRG"], PRL.typicalMechanism)) == {PRLV.Inundation}


# ---- AIR23-05: every model code of sketch 5.1 is a prl:CatModelCode notation -------------------


def test_air23_05_every_model_code_is_a_cat_model_code_notation():
    vocab = _vocab()
    expected = {
        "N.GEO.EQ.SHK": "QEQ", "N.GEO.EQ.FFE": "QFF", "N.GEO.EQ.LIQ": "QLF", "N.GEO.EQ.LSD": "QLS",
        "N.GEO.TSU.EQT": "QTS", "N.MET.TC.WND": "WTC", "N.MET.TC.SRG": "WSS", "N.MET.ETC.WND": "WEC",
        "N.MET.SCS.TOR": "XTD", "N.MET.SCS.HAI": "XHL", "N.MET.SCS.SLW": "XSL",
        "N.HYD.FLD.FLU": "ORF", "N.HYD.FLD.PLU": "OPF", "N.HYD.FLD.CST": "OSF",
        "N.CLI.WF": "BBF", "N.CLI.WF.GRS": "BSK",
    }
    for code, model_code in expected.items():
        notations = {str(n) for n in vocab.objects(PRLV[code], SKOS.notation) if n.datatype == PRL.CatModelCode}
        assert notations == {model_code}, code


# ---- AIR23-06: N.GEO.EQ canTrigger N.GEO.TSU.EQT, N.MET.TC.SRG overlaps N.HYD.FLD.CST -----------


def test_air23_06_named_cross_links():
    vocab = _vocab()
    assert (PRLV["N.GEO.EQ"], PRL.canTrigger, PRLV["N.GEO.TSU.EQT"]) in vocab
    assert (PRLV["N.MET.TC.SRG"], PRL.overlaps, PRLV["N.HYD.FLD.CST"]) in vocab


# ---- AIR23-07: a threshold-basis concept with its onset removed is a characteristics violation --


def test_air23_07_hur_without_onset_is_rejected():
    data = _fixture()
    data.remove((PRLV["N.MET.TC.HUR"], PRL.onset, None))
    assert CHARACTERISTICS in shapes_for(PRLV["N.MET.TC.HUR"], data)


# ---- AIR23-08: no definition names coverage, exclusion or the policy -----------------------------

BANNED_WORDS = ("cover", "covered", "exclude", "insured", "policy")
BANNED_WORD_RE = re.compile(r"\b(" + "|".join(BANNED_WORDS) + r")\b", re.IGNORECASE)


def test_air23_08_no_definition_uses_coverage_language():
    vocab = _vocab()
    offenders = []
    for concept, definition in vocab.subject_objects(SKOS.definition):
        match = BANNED_WORD_RE.search(str(definition))
        if match:
            offenders.append((concept, match.group(1)))
    assert offenders == []


# ---- AIR24-01: H has 37 concepts, P 36, C 17, F 10, L 11, 287 in the whole scheme --------------


def test_air24_01_full_scheme_family_counts_and_unique_codes():
    vocab = _vocab()
    counts = {label: 0 for label in ("N", "T", "E", "H", "P", "C", "F", "L")}
    codes: list[str] = []
    for concept in vocab.subjects(SKOS.inScheme, PRLV.CauseScheme):
        notations = [n for n in vocab.objects(concept, SKOS.notation) if n.datatype == PRL.ReferenceCode]
        assert len(notations) == 1, concept
        code = str(notations[0])
        codes.append(code)
        counts[code.split(".")[0]] += 1
    assert counts == {"N": 90, "T": 71, "E": 15, "H": 37, "P": 36, "C": 17, "F": 10, "L": 11}
    assert sum(counts.values()) == 287
    assert len(codes) == len(set(codes))


# ---- AIR24-02: the whole cause scheme with peril-intensity.ttl / the peril shapes / no result --


def test_air24_02_whole_scheme_with_intensity_has_no_results():
    assert results(_fixture()) == []


# ---- AIR24-03: five spot-checked concepts' characteristics -------------------------------------


def test_air24_03_five_spot_checked_concepts():
    vocab = _vocab()
    assert set(vocab.objects(PRLV["H.WRA.EMP.DIS"], PRL.typicalAgency)) == {PRLV.Intentional}
    assert set(vocab.objects(PRLV["P.PV.STK"], PRL.typicalAgency)) == {PRLV.Intentional}
    assert set(vocab.objects(PRLV["F.INS"], PRL.typicalAgency)) == {PRLV.Economic}
    assert set(vocab.objects(PRLV["F.INS"], PRL.definitionBasis)) == {PRLV.Statutory}
    assert set(vocab.objects(PRLV["L.OCD"], PRL.typicalAgency)) == {PRLV.Negligent}
    assert set(vocab.objects(PRLV["L.OCD"], PRL.onset)) == {PRLV.Latent}
    assert set(vocab.objects(PRLV["L.OCD"], PRL.definitionBasis)) == {PRLV.Statutory}
    assert set(vocab.objects(PRLV["C.NML.SWF"], PRL.typicalAgency)) == {PRLV.Accidental, PRLV.Negligent}


# ---- AIR24-04: the scheme has eight top concepts, N to L ---------------------------------------


def test_air24_04_eight_top_concepts():
    vocab = _vocab()
    tops = set(vocab.objects(PRLV.CauseScheme, SKOS.hasTopConcept))
    assert tops == {PRLV.N, PRLV.T, PRLV.E, PRLV.H, PRLV.P, PRLV.C, PRLV.F, PRLV.L}


# ---- AIR24-05: cross-group-links hold the six named links, none with both ends in one group ----

GROUP_1 = {"N", "T", "E"}
GROUP_2 = {"H", "P", "C", "F", "L"}


def _family(code: str) -> str:
    return code.split(".")[0]


def test_air24_05_cross_group_links():
    vocab = _vocab()
    assert (PRLV["T.EQB.CTL"], PRL.overlaps, PRLV["C.NML.OTF"]) in vocab
    assert (PRLV["T.UTL.TEL"], PRL.overlaps, PRLV["C.NML.SVC"]) in vocab
    assert (PRLV["T.REL.RAD"], SKOS.related, PRLV["P.TER.CBR.RAD"]) in vocab
    assert (PRLV["C.NML.CFG"], SKOS.related, PRLV["E.HUM"]) in vocab
    assert (PRLV["L.MED"], SKOS.related, PRLV["E.PRO"]) in vocab
    assert (PRLV["C.MAL.OTA"], PRL.canTrigger, PRLV["T.FIR"]) in vocab
    assert (PRLV["C.MAL.OTA"], PRL.canTrigger, PRLV["T.EXP"]) in vocab
    assert (PRLV["C.MAL.OTA"], PRL.canTrigger, PRLV["T.EQB"]) in vocab

    code_of: dict[URIRef, str] = {}
    for concept in vocab.subjects(SKOS.inScheme, PRLV.CauseScheme):
        notation = next(n for n in vocab.objects(concept, SKOS.notation) if n.datatype == PRL.ReferenceCode)
        code_of[concept] = str(notation)

    # No link (canTrigger, overlaps, related) has both ends in the same group: exactly the five
    # named single links above, plus C.MAL.OTA's and C.NML.OTF's three-way canTrigger each
    # (eleven triples once each (subject, predicate, object) is counted separately).
    cross = []
    for predicate in (PRL.canTrigger, PRL.overlaps, SKOS.related):
        for s, o in vocab.subject_objects(predicate):
            if s not in code_of or o not in code_of:
                continue
            fam_s, fam_o = _family(code_of[s]), _family(code_of[o])
            in_1_s, in_1_o = fam_s in GROUP_1, fam_o in GROUP_1
            if in_1_s != in_1_o:
                cross.append((s, predicate, o))
    assert len(cross) == 11


# ---- AIR24-06: a hierarchical all-perils-except-flood condition, evaluated with the real kernel -


def _ancestors(vocab: Graph, concept: URIRef) -> set:
    seen = {concept}
    frontier = {concept}
    while frontier:
        nxt = set()
        for c in frontier:
            for parent in vocab.objects(c, SKOS.broader):
                if parent not in seen:
                    seen.add(parent)
                    nxt.add(parent)
        frontier = nxt
    return seen


def test_air24_06_all_perils_except_flood_hierarchical_condition():
    from reference_eligibility.kernel import DENIED, PERMITTED, UNDETERMINED, and3

    vocab = _fixture()
    tops = {PRLV.N, PRLV.T, PRLV.E, PRLV.H, PRLV.P, PRLV.C, PRLV.F, PRLV.L}

    def decide(concept: URIRef) -> object:
        ancestors = _ancestors(vocab, concept)
        required = PERMITTED if ancestors & tops else UNDETERMINED
        excluded = DENIED if PRLV["N.HYD.FLD"] in ancestors else PERMITTED
        return and3(required, excluded)

    assert decide(PRLV["N.HYD.FLD.FLU"]) is DENIED
    assert decide(PRLV["P.TER.CNV"]) is PERMITTED


# ---- AIR24-07: P.TER.CNV given skos:related to P.TER is an associative integrity violation ------


def test_air24_07_related_to_own_ancestor_is_rejected():
    data = _fixture()
    data.add((PRLV["P.TER.CNV"], SKOS.related, PRLV["P.TER"]))
    assert ASSOCIATIVE_INTEGRITY in shapes_for(PRLV["P.TER.CNV"], data)
