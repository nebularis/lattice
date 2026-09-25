# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""persistence-compiler-iri-sync Slice 5: dal:onViolation resolved with a
baseline default of dal:Reject, three reconciler operations selected per
policy (decision 1, Option A -- the guarded write itself never branches),
dal:mergeRelation read and checked (mirrors dal:MergeRelationRequiredShape),
dal:ClaimScheme dal:Dual rotation selecting the dual-guard write template,
and the registry-token digest-scheme exemption in check_identity."""

from __future__ import annotations

from pathlib import Path

import pytest
from rdflib import Graph, URIRef

from persistence import resolver
from persistence.compiler import compile_to_graph
from persistence.model import DIMENSIONS, CrossAxisViolation
from persistence.namespaces import DAL
from persistence.render import load_template, render
from persistence.scopes import Target
from persistence.terms import Iri, Literal
from persistence.validator import check_cross_axis, check_identity

REPO_ROOT = Path(__file__).resolve().parents[3]
SPEC_TTL = REPO_ROOT / "ontology" / "persistence" / "spec" / "persistence.ttl"
EXAMPLES_DIR = REPO_ROOT / "ontology" / "persistence" / "examples"

PREFIXES = """
@prefix dal: <https://www.nebularis.org/neuro-semantic/lattice/persistence#> .
@prefix ex:  <https://example.org/lending#> .
"""
CLS = URIRef("https://example.org/lending#Thing")
BASE = PREFIXES + "ex:ThingScope a dal:ClassScope ; dal:priority 10 ; dal:targetClass ex:Thing .\n"


def _local(v) -> str | None:
    return None if v is None else str(v).rsplit("#", 1)[-1]


def _graph(extra: str) -> Graph:
    g = Graph()
    g.parse(SPEC_TTL, format="turtle")
    g.parse(data=BASE + extra, format="turtle")
    return g


def _uniqueness(extra: str) -> list[dict]:
    return resolver.resolve_uniqueness(_graph(extra), Target(CLS))


def _compile(fixture: str, cls: str):
    g = Graph()
    g.parse(SPEC_TTL, format="turtle")
    g.parse(EXAMPLES_DIR / fixture, format="turtle")
    return compile_to_graph(g, classes={URIRef(cls)})


# ---- resolve_uniqueness(): mergeRelation, dualClaimScheme --------------------------------------

CONSTRAINT = """
ex:ThingKey a dal:UniquenessConstraint ; dal:constraintId "thing-key" ; dal:appliesTo ex:ThingScope ;
    dal:keyProperty ( ex:code ) ; dal:normalizePipeline dal:NfkcTrimUppercase ;
"""


def test_on_violation_and_merge_relation_are_read():
    u = _uniqueness(CONSTRAINT + 'dal:onViolation dal:Merge ; dal:mergeRelation ex:supersededBy .')[0]
    assert _local(u["onViolation"]) == "Merge"
    assert str(u["mergeRelation"]) == "https://example.org/lending#supersededBy"


def test_merge_relation_is_none_when_undeclared():
    u = _uniqueness(CONSTRAINT + "dal:onViolation dal:Reject .")[0]
    assert u["mergeRelation"] is None


def test_on_violation_is_none_when_undeclared():
    u = _uniqueness(CONSTRAINT + "dal:onViolation dal:Reject .")[0]
    # onViolation itself is read as whatever is declared; the baseline
    # default of Reject is applied by operations.py, not the resolver.
    u2 = _uniqueness("""
        ex:ThingKey a dal:UniquenessConstraint ; dal:constraintId "thing-key" ;
            dal:appliesTo ex:ThingScope ; dal:keyProperty ( ex:code ) .
    """)[0]
    assert u2["onViolation"] is None


SCHEME_A = 'ex:A a dal:ClaimScheme ; dal:schemeVersion "v1" ; dal:schemeState {state} ; dal:claimKeyId "k1" ; dal:claimDigestScheme ex:Mac ; dal:claimIriTemplate "urn:key:t:v1:{{mac}}" .\n'
SCHEME_B = 'ex:B a dal:ClaimScheme ; dal:schemeVersion "v2" ; dal:schemeState {state} ; dal:claimKeyId "k2" ; dal:claimDigestScheme ex:Mac ; dal:claimIriTemplate "urn:key:t:v2:{{mac}}" .\n'
MAC = 'ex:Mac a dal:DigestScheme ; dal:digestFunction "HMAC-SHA-256" ; dal:digestWidthBits 128 ; dal:digestEncoding "base32" .\n'


@pytest.mark.parametrize(
    "state_a,state_b,expected",
    [
        ("dal:Dual", "dal:Dual", True),
        ("dal:Accepting", None, False),
        ("dal:Retiring", "dal:Accepting", False),
        ("dal:Retiring", "dal:Retired", False),
    ],
)
def test_dual_claim_scheme_mirrors_recipes_active_scheme_count(state_a, state_b, expected):
    schemes = "dal:claimScheme ex:A" + (", ex:B" if state_b else "") + " .\n"
    extra = CONSTRAINT + "dal:onViolation dal:Reject ; " + schemes
    extra += MAC + SCHEME_A.format(state=state_a)
    if state_b:
        extra += SCHEME_B.format(state=state_b)
    u = _uniqueness(extra)[0]
    assert u["dualClaimScheme"] is expected


def test_no_claim_scheme_is_not_dual():
    u = _uniqueness(CONSTRAINT + "dal:onViolation dal:Reject .")[0]
    assert u["dualClaimScheme"] is False


# ---- MergeRelationRequired (mirrors dal:MergeRelationRequiredShape) ----------------------------


def _check(uniqueness: list[dict]):
    g = _graph("")
    target = Target(CLS)
    dims = {d: resolver.resolve_dimension(g, target, d, None) for d in DIMENSIONS}
    return check_cross_axis(g, target, dims, uniqueness)


def test_merge_without_relation_is_refused():
    u = [{"constraintId": "thing-key", "onViolation": DAL.Merge, "mergeRelation": None}]
    with pytest.raises(CrossAxisViolation) as e:
        _check(u)
    assert e.value.kind == "MergeRelationRequired"


def test_merge_with_relation_passes():
    u = [{"constraintId": "thing-key", "onViolation": DAL.Merge, "mergeRelation": URIRef("https://example.org/lending#supersededBy")}]
    _check(u)  # no raise


def test_reject_needs_no_merge_relation():
    u = [{"constraintId": "thing-key", "onViolation": DAL.Reject, "mergeRelation": None}]
    _check(u)  # no raise


def test_undeclared_on_violation_needs_no_merge_relation():
    u = [{"constraintId": "thing-key", "onViolation": None, "mergeRelation": None}]
    _check(u)  # no raise


# ---- registry-token digest-scheme exemption (check_identity) -----------------------------------


def _identity_check(extra: str):
    g = _graph(extra)
    target = Target(CLS)
    dims = {d: resolver.resolve_dimension(g, target, d, None) for d in DIMENSIONS}
    identity = resolver.resolve_identity(g, target, None)
    return check_identity(g, target, dims, identity, [])


def _event_profile(namespace_derivation: str, with_digest: bool, width: int = 128, encoding: str = "base32") -> str:
    profile = (
        "ex:P a dal:IdentityProfile ; dal:appliesTo ex:ThingScope ; dal:resourceRole dal:EventOccurrenceRole ; "
        "dal:identityStrategy dal:DerivedHashIdentity ; dal:eventIdentityStrategy dal:PositionDerivedEvent ; "
        f"dal:occurrenceNamespaceDerivation dal:{namespace_derivation} ; dal:uniquenessWitnessRequired true"
    )
    if with_digest:
        profile += " ; dal:digestScheme ex:D"
    profile += " .\n"
    if with_digest:
        profile += (
            f'ex:D a dal:DigestScheme ; dal:digestFunction "SHA-256" ; '
            f'dal:digestWidthBits {width} ; dal:digestEncoding "{encoding}" .\n'
        )
    return profile


def test_registry_token_position_event_needs_no_digest_scheme():
    _identity_check(_event_profile("RegistryTokenDerivation", with_digest=False))  # no raise


def test_hashed_target_position_event_still_needs_a_digest_scheme():
    with pytest.raises(CrossAxisViolation) as e:
        _identity_check(_event_profile("HashedTargetDerivation", with_digest=False))
    assert e.value.kind == "DigestSchemeRequired"


def test_registry_token_position_event_with_a_declared_digest_is_still_checked_for_well_formedness():
    with pytest.raises(CrossAxisViolation) as e:
        _identity_check(_event_profile("RegistryTokenDerivation", with_digest=True, width=100))
    assert e.value.kind == "DigestSchemeMalformed"


def test_registry_token_position_event_with_a_well_formed_declared_digest_passes():
    _identity_check(_event_profile("RegistryTokenDerivation", with_digest=True))  # no raise


# ---- end-to-end: reconciler operation selection, dual-write selection -------------------------


def test_explicit_reject_generates_the_duplicate_audit():
    _, compiled = _compile("baseline-single-class.ttl", "https://example.org/lending#LoanApplication")
    ops = {o.operation: o.template_id for o in compiled[0].operations}
    # baseline-single-class.ttl declares dal:onViolation dal:Reject explicitly.
    assert any(op.startswith("key-claim-duplicate-audit:") for op in ops)
    assert all(t == "key-claim-duplicate-audit.mustache" for op, t in ops.items() if op.startswith("key-claim-duplicate-audit:"))


def test_undeclared_on_violation_also_defaults_to_the_duplicate_audit():
    """operations.py's own baseline default (Reject when dal:onViolation is
    entirely undeclared), exercised end to end through select_operations()
    rather than only through the resolver."""
    g = _graph(
        "ex:ThingKey a dal:UniquenessConstraint ; dal:constraintId \"thing-key\" ; "
        "dal:appliesTo ex:ThingScope ; dal:keyProperty ( ex:code ) .\n"
    )
    _, compiled = compile_to_graph(g, classes={CLS})
    ops = {o.operation: o.template_id for o in compiled[0].operations}
    assert ops["key-claim-duplicate-audit:thing-key"] == "key-claim-duplicate-audit.mustache"


def test_merge_policy_generates_the_merge_rewrite_operation_with_the_relation_bound():
    _, compiled = _compile("uniqueness-merge-policy.ttl", "https://example.org/lending#Customer")
    ops = {o.operation: o for o in compiled[0].operations}
    op = ops["key-claim-merge-rewrite:customer-email-unique"]
    assert op.template_id == "key-claim-merge-rewrite.mustache"
    binding = next(b for b in op.bindings if b.name == "mergeRelation")
    assert binding.value == "<https://example.org/lending#supersededBy>"


def test_quarantine_policy_generates_the_quarantine_operation():
    _, compiled = _compile("uniqueness-quarantine-policy.ttl", "https://example.org/lending#Device")
    ops = {o.operation: o.template_id for o in compiled[0].operations}
    assert ops["key-claim-quarantine:device-serial-unique"] == "key-claim-quarantine.mustache"


def test_dual_claim_scheme_selects_the_dual_write_template():
    _, compiled = _compile("claim-scheme-dual-rotation.ttl", "https://example.org/lending#Member")
    ops = {o.operation: o.template_id for o in compiled[0].operations}
    assert ops["key-claim-write:member-handle-unique"] == "key-claim-write-dual.mustache"


def test_single_claim_scheme_selects_the_plain_write_template():
    _, compiled = _compile("baseline-single-class.ttl", "https://example.org/lending#LoanApplication")
    ops = {o.operation: o.template_id for o in compiled[0].operations}
    assert ops["key-claim-write:loan-application-number-per-branch"] == "key-claim-write.mustache"


# ---- template rendering: the merge/quarantine/dual templates render as expected ----------------


def _render(name: str, **extra) -> str:
    ctx = {
        "keysGraph": Iri.encode("urn:g:keys"),
        "keyQuarantineGraph": Iri.encode("urn:g:key-quarantine"),
        "constraintId": Literal.encode("example-constraint"),
        **extra,
    }
    return render(load_template(name), ctx)


def test_merge_rewrite_uses_min_owner_as_canonical_and_guards_idempotently():
    text = _render("key-claim-merge-rewrite.mustache", mergeRelation=Iri.encode("https://example.org/lending#supersededBy"))
    assert "MIN(?owner) AS ?canonical" in text
    assert "FILTER NOT EXISTS" in text
    assert "<https://example.org/lending#supersededBy>" in text


def test_quarantine_writes_to_the_quarantine_graph_and_deletes_nothing():
    text = _render("key-claim-quarantine.mustache")
    assert "DELETE" not in text
    assert "<urn:g:key-quarantine>" in text
    assert "pat:quarantinedOwner" in text


def test_dual_write_guards_both_claim_iris_independently():
    text = _render("key-claim-write-dual.mustache")
    assert "$claimCurrent" in text and "$claimNext" in text
    assert text.count("FILTER NOT EXISTS") == 2
