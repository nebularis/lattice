# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""persistence-compiler-iri-sync Slice 4: dal:PrivacyProfile's three
properties and dal:ReceiptProfile's dal:perSubjectScoped resolved as their
own dimensions (one per property, matching Slice 2's style -- this is a new
profile class in the same shape as dal:EpochProfile, not a resource-role
situation like Slice 3's identity dimensions), dal:epochAuthority promoted
out of dal:epochGuardScope's extras into its own dimension, and the two
privacy/erasure cross-axis checks."""

from __future__ import annotations

from pathlib import Path

import pytest
from rdflib import Graph, URIRef

from persistence import resolver
from persistence.compiler import CompileError, compile_to_graph
from persistence.model import DIMENSIONS, CrossAxisViolation
from persistence.namespaces import DAL
from persistence.scopes import Target
from persistence.validator import check_cross_axis

REPO_ROOT = Path(__file__).resolve().parents[3]
SPEC_TTL = REPO_ROOT / "ontology" / "persistence" / "spec" / "persistence.ttl"
EXAMPLES_DIR = REPO_ROOT / "ontology" / "persistence" / "examples"

PREFIXES = """
@prefix dal: <https://www.nebularis.org/neuro-semantic/lattice/persistence#> .
@prefix ex:  <https://example.org/lending#> .
"""
CLS = URIRef("https://example.org/lending#Thing")

BASE = PREFIXES + """
ex:ThingScope a dal:ClassScope ; dal:priority 10 ; dal:targetClass ex:Thing .
"""


def _graph(extra: str = "", base: str = BASE) -> Graph:
    g = Graph()
    g.parse(SPEC_TTL, format="turtle")
    g.parse(data=base + extra, format="turtle")
    return g


def _dims(g: Graph) -> dict:
    target = Target(CLS)
    return {d: resolver.resolve_dimension(g, target, d, None) for d in DIMENSIONS}


def _local(v) -> str | None:
    return None if v is None else str(v).rsplit("#", 1)[-1]


def _diagnostics(extra: str = "", base: str = BASE):
    g = _graph(extra, base)
    return check_cross_axis(g, Target(CLS), _dims(g), [])


# ---- epochAuthority promoted to its own dimension ---------------------------------------------


def test_epoch_authority_resolves_from_its_own_epoch_profile_node():
    g = _graph("ex:E a dal:EpochProfile ; dal:appliesTo ex:ThingScope ; dal:epochAuthority dal:ExternalHighWaterMark .")
    rd = _dims(g)["epochAuthority"]
    assert _local(rd.value) == "ExternalHighWaterMark"
    assert rd.won_by == "https://example.org/lending#E"


def test_epoch_authority_is_absent_with_no_default_when_undeclared():
    g = _graph()
    rd = _dims(g)["epochAuthority"]
    assert rd.value is None
    assert rd.candidate_count == 0


def test_epoch_authority_and_epoch_guard_scope_resolve_independently():
    # persistence-compiler-iri-sync Slice 4: epochAuthority no longer rides
    # on epochGuardScope's extras, so a node declaring only one of the two
    # still resolves that one; the other stays absent, not silently copied.
    g = _graph("ex:E a dal:EpochProfile ; dal:appliesTo ex:ThingScope ; dal:epochGuardScope dal:DatasetLevelGuard .")
    dims = _dims(g)
    assert _local(dims["epochGuardScope"].value) == "DatasetLevelGuard"
    assert dims["epochAuthority"].value is None


# ---- Per-property resolution of the three PrivacyProfile properties and perSubjectScoped -------


@pytest.mark.parametrize(
    "dim,prop,value",
    [
        ("privacyClass", "dal:privacyClass", "dal:PersonalData"),
        ("erasureStrategy", "dal:erasureStrategy", "dal:PerSubjectGraphDrop"),
        ("erasurePrecedence", "dal:erasurePrecedence", "dal:ErasureWins"),
    ],
)
def test_privacy_property_resolves_on_its_own_node(dim, prop, value):
    g = _graph(f"ex:P a dal:PrivacyProfile ; dal:appliesTo ex:ThingScope ; {prop} {value} .")
    rd = _dims(g)[dim]
    assert _local(rd.value) == value.split(":", 1)[1]
    assert rd.won_by == "https://example.org/lending#P"


def test_per_subject_scoped_resolves_from_receipt_profile_node():
    g = _graph("ex:R a dal:ReceiptProfile ; dal:appliesTo ex:ThingScope ; dal:receiptModel dal:PatchLog ; "
               "dal:perSubjectScoped true .")
    rd = _dims(g)["perSubjectScoped"]
    assert bool(rd.value) is True


def test_privacy_property_on_a_lower_priority_node_is_still_resolved():
    # Mirrors Slice 2's "declared on a separate/lower-priority node" case:
    # a privacyClass on a namespace-wide node must not be dropped just
    # because a higher-priority, class-scoped node wins another dimension.
    extra = """
ex:Wide a dal:NamespaceScope ; dal:priority 1 ; dal:iriPrefix "https://example.org/lending#" .
ex:WidePrivacy a dal:PrivacyProfile ; dal:appliesTo ex:Wide ; dal:privacyClass dal:PersonalData .
ex:NarrowConcurrency a dal:DataAccessProfile ; dal:appliesTo ex:ThingScope ; dal:concurrencyProfile dal:Optimistic .
"""
    g = _graph(extra)
    dims = _dims(g)
    assert _local(dims["concurrencyProfile"].value) == "Optimistic"
    assert dims["concurrencyProfile"].won_by == "https://example.org/lending#NarrowConcurrency"
    assert _local(dims["privacyClass"].value) == "PersonalData"
    assert dims["privacyClass"].won_by == "https://example.org/lending#WidePrivacy"


def test_no_default_for_any_slice_4_privacy_dimension():
    g = _graph()
    dims = _dims(g)
    for dim in ("privacyClass", "erasureStrategy", "erasurePrecedence", "perSubjectScoped"):
        assert dims[dim].value is None
        assert dims[dim].candidate_count == 0


# ---- PersonalDataRequiresErasure (mirrors dal:PersonalDataRequiresErasureShape) ----------------


def test_personal_data_with_no_erasure_is_refused():
    extra = "ex:P a dal:PrivacyProfile ; dal:appliesTo ex:ThingScope ; dal:privacyClass dal:PersonalData ; " \
            "dal:erasureStrategy dal:NoErasure ."
    with pytest.raises(CrossAxisViolation) as e:
        _diagnostics(extra)
    assert e.value.kind == "PersonalDataRequiresErasure"


@pytest.mark.parametrize("strategy", ["dal:PerSubjectGraphDrop", "dal:CryptoShred"])
def test_personal_data_with_a_lawful_erasure_strategy_passes(strategy):
    extra = f"ex:P a dal:PrivacyProfile ; dal:appliesTo ex:ThingScope ; dal:privacyClass dal:PersonalData ; " \
            f"dal:erasureStrategy {strategy} ."
    kinds = {d.kind for d in _diagnostics(extra)}
    assert "PersonalDataRequiresErasure" not in kinds


def test_no_erasure_is_not_checked_without_personal_data():
    extra = "ex:P a dal:PrivacyProfile ; dal:appliesTo ex:ThingScope ; dal:privacyClass dal:InternalData ; " \
            "dal:erasureStrategy dal:NoErasure ."
    kinds = {d.kind for d in _diagnostics(extra)}
    assert "PersonalDataRequiresErasure" not in kinds


# ---- PersonalDataReceiptConflict (mirrors dal:PersonalDataReceiptCompatibilityShape) -----------


@pytest.mark.parametrize("receipt_model", ["dal:PatchLog", "dal:SnapshotPerRevision"])
def test_personal_data_with_replay_receipts_and_no_scoping_or_shred_is_refused(receipt_model):
    extra = f"""
ex:P a dal:PrivacyProfile ; dal:appliesTo ex:ThingScope ; dal:privacyClass dal:PersonalData ;
    dal:erasureStrategy dal:PerSubjectGraphDrop .
ex:R a dal:ReceiptProfile ; dal:appliesTo ex:ThingScope ; dal:receiptModel {receipt_model} .
"""
    with pytest.raises(CrossAxisViolation) as e:
        _diagnostics(extra)
    assert e.value.kind == "PersonalDataReceiptConflict"


def test_personal_data_with_replay_receipts_and_per_subject_scoping_passes():
    extra = """
ex:P a dal:PrivacyProfile ; dal:appliesTo ex:ThingScope ; dal:privacyClass dal:PersonalData ;
    dal:erasureStrategy dal:PerSubjectGraphDrop .
ex:R a dal:ReceiptProfile ; dal:appliesTo ex:ThingScope ; dal:receiptModel dal:PatchLog ;
    dal:perSubjectScoped true .
"""
    kinds = {d.kind for d in _diagnostics(extra)}
    assert "PersonalDataReceiptConflict" not in kinds


def test_personal_data_with_replay_receipts_and_crypto_shred_passes():
    extra = """
ex:P a dal:PrivacyProfile ; dal:appliesTo ex:ThingScope ; dal:privacyClass dal:PersonalData ;
    dal:erasureStrategy dal:CryptoShred .
ex:R a dal:ReceiptProfile ; dal:appliesTo ex:ThingScope ; dal:receiptModel dal:SnapshotPerRevision .
"""
    kinds = {d.kind for d in _diagnostics(extra)}
    assert "PersonalDataReceiptConflict" not in kinds


def test_personal_data_with_receipt_only_model_is_never_checked():
    extra = """
ex:P a dal:PrivacyProfile ; dal:appliesTo ex:ThingScope ; dal:privacyClass dal:PersonalData ;
    dal:erasureStrategy dal:PerSubjectGraphDrop .
ex:R a dal:ReceiptProfile ; dal:appliesTo ex:ThingScope ; dal:receiptModel dal:ReceiptOnly .
"""
    kinds = {d.kind for d in _diagnostics(extra)}
    assert "PersonalDataReceiptConflict" not in kinds


def test_privacy_and_receipts_declared_on_separate_nodes_are_still_joined():
    """The genuine cross-profile-class join (plan Slice 4): dal:PrivacyProfile
    and dal:ReceiptProfile are declared on two different individuals here,
    which the node-local SHACL shape's shared dal:appliesTo match already
    handles, and so does this Python check, on resolved values."""
    extra = """
ex:PrivacyNode a dal:PrivacyProfile ; dal:appliesTo ex:ThingScope ; dal:privacyClass dal:PersonalData ;
    dal:erasureStrategy dal:PerSubjectGraphDrop .
ex:ReceiptNode a dal:ReceiptProfile ; dal:appliesTo ex:ThingScope ; dal:receiptModel dal:PatchLog .
"""
    with pytest.raises(CrossAxisViolation) as e:
        _diagnostics(extra)
    assert e.value.kind == "PersonalDataReceiptConflict"


@pytest.mark.parametrize(
    "fixture,kind",
    [
        ("invalid-personaldata-no-erasure.ttl", "PersonalDataRequiresErasure"),
        ("invalid-personaldata-receipt-conflict.ttl", "PersonalDataReceiptConflict"),
    ],
)
def test_negative_fixtures_fail_for_the_right_reason(fixture, kind):
    g = Graph()
    g.parse(SPEC_TTL, format="turtle")
    g.parse(EXAMPLES_DIR / fixture, format="turtle")
    with pytest.raises(CompileError) as e:
        compile_to_graph(g)
    assert isinstance(e.value.__cause__, CrossAxisViolation)
    assert e.value.__cause__.kind == kind


def test_positive_fixture_compiles_cleanly():
    g = Graph()
    g.parse(SPEC_TTL, format="turtle")
    g.parse(EXAMPLES_DIR / "privacy-receipt-compatible.ttl", format="turtle")
    target = URIRef("https://example.org/lending#Beneficiary")
    _, compiled = compile_to_graph(g, classes={target})
    kinds = {d.kind for ct in compiled for d in ct.diagnostics}
    assert "PersonalDataRequiresErasure" not in kinds
    assert "PersonalDataReceiptConflict" not in kinds


def test_per_subject_scoped_is_emitted_with_resolved_literal():
    g = Graph()
    g.parse(SPEC_TTL, format="turtle")
    g.parse(EXAMPLES_DIR / "privacy-receipt-compatible.ttl", format="turtle")
    target = URIRef("https://example.org/lending#Beneficiary")
    out, _ = compile_to_graph(g, classes={target})
    by_dim = {str(out.value(n, DAL.dimension)): n for n in out.subjects(DAL.dimension, None)}
    assert out.value(by_dim["perSubjectScoped"], DAL.resolvedLiteral).toPython() is True
    assert out.value(by_dim["perSubjectScoped"], DAL.resolvedValue) is None


def test_worked_example_4_privacy_profile_resolves_and_is_emitted():
    """ontology/persistence/README.md §9's worked example, handed over from
    Slice 3: its privacy profile (dal:PersonalData, dal:PerSubjectGraphDrop,
    dal:ErasureWins) now resolves and is emitted into the compiled profile,
    and its ReceiptProfile's dal:perSubjectScoped true keeps its
    dal:ReceiptOnly model uncontested."""
    g = Graph()
    g.parse(SPEC_TTL, format="turtle")
    g.parse(EXAMPLES_DIR / "identity-epoch-privacy-profile.ttl", format="turtle")
    target = URIRef("https://example.org/lending#Claimant")
    _, compiled = compile_to_graph(g, classes={target})
    assert len(compiled) == 1
    dims = compiled[0].dimensions
    assert _local(dims["privacyClass"].value) == "PersonalData"
    assert _local(dims["erasureStrategy"].value) == "PerSubjectGraphDrop"
    assert _local(dims["erasurePrecedence"].value) == "ErasureWins"
    assert bool(dims["perSubjectScoped"].value) is True
    assert _local(dims["epochAuthority"].value) == "ExternalHighWaterMark"
    kinds = {d.kind for d in compiled[0].diagnostics}
    assert "PersonalDataRequiresErasure" not in kinds
    assert "PersonalDataReceiptConflict" not in kinds
