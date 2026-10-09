# SPDX-License-Identifier: MPL-2.0

"""The cross-domain classification module and the insurance domain's shared
contracts (applied-insurance-reference AIR-1.2, ADR-A98 decisions 1, 5, 6,
ADR-A102).

Full import-closure loading through ``tools/ontology_catalog.py`` needs the
root catalog regenerated first (``mise run build:ontology-catalog``, an
R-only step per the lanes plan), so AIR12-01 here checks each document's own
``owl:imports`` set against the pinned versions instead, the same proxy
AIR-2.1's own test used before its catalog stubs existed.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from pyshacl import validate
from rdflib import Graph, Namespace, URIRef
from rdflib.namespace import OWL, RDF

ROOT = Path(__file__).resolve().parents[1]
CLASSIFICATION = ROOT / "ontology" / "applied" / "classification"
COMMON = ROOT / "ontology" / "applied" / "insurance" / "common"
VOCAB_SHAPES = ROOT / "ontology" / "vocabulary" / "shapes"

CLS = Namespace("https://www.nebularis.org/neuro-semantic/lattice/applied/classification#")
CLSV = Namespace("https://www.nebularis.org/neuro-semantic/lattice/applied/classification/vocab#")
ICM = Namespace("https://www.nebularis.org/neuro-semantic/insurance/common#")
ICMV = Namespace("https://www.nebularis.org/neuro-semantic/insurance/common/vocab#")
VOC = Namespace("https://www.nebularis.org/neuro-semantic/lattice/vocabulary#")
PTY = Namespace("https://www.nebularis.org/neuro-semantic/lattice/party#")


def _graph(*paths: Path) -> Graph:
    g = Graph()
    for path in paths:
        g.parse(path)
    return g


def _classification_spec() -> Graph:
    return _graph(CLASSIFICATION / "spec" / "classification.ttl")


def _classification_vocab() -> Graph:
    return _graph(CLASSIFICATION / "vocab" / "classification-vocab.ttl")


def _common_spec() -> Graph:
    return _graph(COMMON / "spec" / "common.ttl")


def _common_vocab() -> Graph:
    return _graph(COMMON / "vocab" / "common-vocab.ttl")


def _all_contracts() -> Graph:
    return _graph(
        CLASSIFICATION / "spec" / "classification.ttl",
        CLASSIFICATION / "vocab" / "classification-vocab.ttl",
        COMMON / "spec" / "common.ttl",
        COMMON / "vocab" / "common-vocab.ttl",
    )


def _vocabulary_shapes() -> Graph:
    return _graph(VOCAB_SHAPES / "structural.ttl", VOCAB_SHAPES / "constraints.ttl")


@pytest.fixture(scope="module", autouse=True)
def _cached_validate(request: pytest.FixtureRequest, validated) -> None:
    """TM2: shared, session-scoped validation cache (python-test-melting).
    `_all_contracts`/`_vocabulary_shapes` stay plain functions (only two call
    sites, each already a module-level-cacheable graph elsewhere), since the
    files they build from are the same ones several Instrument-family
    modules' EVERY_SHAPE already pulls through `graph_cache`."""
    request.module.validate = validated


# ---- AIR12-01: parse and pinned imports -------------------------------------------------------


def test_classification_documents_parse_and_import_the_pinned_versions():
    spec_imports = {str(o) for o in _classification_spec().objects(None, OWL.imports)}
    assert spec_imports == {
        "https://www.nebularis.org/neuro-semantic/lattice/foundation/0.4.0",
        "https://www.nebularis.org/neuro-semantic/lattice/vocabulary/0.4.0",
    }
    vocab_imports = {str(o) for o in _classification_vocab().objects(None, OWL.imports)}
    assert vocab_imports == {"https://www.nebularis.org/neuro-semantic/lattice/applied/classification/0.2.0"}


def test_common_documents_parse_and_import_the_pinned_versions():
    spec_imports = {str(o) for o in _common_spec().objects(None, OWL.imports)}
    assert spec_imports == {
        "https://www.nebularis.org/neuro-semantic/lattice/foundation/0.4.0",
        "https://www.nebularis.org/neuro-semantic/lattice/vocabulary/0.4.0",
        "https://www.nebularis.org/neuro-semantic/lattice/party/0.8.0",
        "https://www.nebularis.org/neuro-semantic/lattice/applied/classification/0.2.0",
    }
    vocab_imports = {str(o) for o in _common_vocab().objects(None, OWL.imports)}
    assert vocab_imports == {"https://www.nebularis.org/neuro-semantic/insurance/common/0.4.0"}


# ---- AIR12-02: the nine contracts conform to Vocabulary's shapes ------------------------------


def test_nine_contracts_conform_to_vocabulary_shapes():
    data = _all_contracts()
    shapes = _vocabulary_shapes()
    conforms, _, report = validate(data, shacl_graph=shapes, advanced=True, inference="none", allow_warnings=True)
    assert conforms, report
    contracts = set(data.subjects(RDF.type, VOC.SchemeContract))
    assert contracts == {
        CLSV.TerritoryContract,
        CLSV.AssetClassContract,
        CLSV.IndustryContract,
        ICMV.PerilContract,
        ICMV.MechanismContract,
        ICMV.AgencyContract,
        ICMV.ConsequenceContract,
        ICMV.HarmSubjectContract,
        ICMV.PoolContract,
    }
    assert len(contracts) == 9


# ---- AIR12-03: a contract without voc:constrainsProperty is a violation -----------------------


def test_contract_without_constrains_property_is_rejected():
    data = _all_contracts()
    data.remove((ICMV.PoolContract, VOC.constrainsProperty, None))
    shapes = _vocabulary_shapes()
    conforms, _, report = validate(data, shacl_graph=shapes, advanced=True, inference="none", allow_warnings=True)
    assert not conforms, "removing voc:constrainsProperty should violate SchemeContractShape"


# ---- AIR12-04: the four roles are pty:Role individuals ----------------------------------------


def test_four_liability_roles_are_pty_role_individuals():
    data = _common_vocab()
    roles = {ICMV.HarmedParty, ICMV.LiableParty, ICMV.Claimant, ICMV.Payee}
    for role in roles:
        assert (role, RDF.type, PTY.Role) in data
        assert (role, RDF.type, OWL.NamedIndividual) in data


# ---- AIR12-05: classification's own imports name no insurance document ------------------------


def test_classification_imports_no_insurance_document():
    spec_imports = {str(o) for o in _classification_spec().objects(None, OWL.imports)}
    vocab_imports = {str(o) for o in _classification_vocab().objects(None, OWL.imports)}
    for iri in spec_imports | vocab_imports:
        assert "neuro-semantic/insurance/" not in iri


# ---- AIR12-06: no insurance term anywhere in classification/ ----------------------------------


def test_no_insurance_term_in_classification_module():
    needles = ("peril", "policy", "premium", "claim", "insur")
    for path in (CLASSIFICATION / "spec" / "classification.ttl", CLASSIFICATION / "vocab" / "classification-vocab.ttl"):
        text = path.read_text(encoding="utf-8").lower()
        for needle in needles:
            assert needle not in text, f"{needle!r} found in {path}"
