# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""persistence-compiler-iri-sync Slice 3: dal:IdentityProfile resolved per
resource role (plan decision 1), emitted into the compiled profile with no
SPARQL generated (decision 2), and checked (decision 3)."""

from __future__ import annotations

from pathlib import Path

import pytest
from rdflib import Graph, URIRef

from persistence import resolver
from persistence.compiler import CompileError, compile_to_graph
from persistence.model import DIMENSIONS, CrossAxisViolation, ProfileAmbiguityError
from persistence.namespaces import DAL
from persistence.scopes import Target
from persistence.validator import check_identity

REPO_ROOT = Path(__file__).resolve().parents[3]
SPEC_TTL = REPO_ROOT / "ontology" / "persistence" / "spec" / "persistence.ttl"
EXAMPLES_DIR = REPO_ROOT / "ontology" / "persistence" / "examples"

CLS = URIRef("https://example.org/lending#Thing")
BASE = """
@prefix dal: <https://www.nebularis.org/neuro-semantic/lattice/persistence#> .
@prefix ex:  <https://example.org/lending#> .
ex:ThingScope a dal:ClassScope ; dal:priority 20 ; dal:targetClass ex:Thing .
ex:Wide a dal:NamespaceScope ; dal:priority 1 ; dal:iriPrefix "https://example.org/lending#" .
"""
KEY = """
ex:ThingKey a dal:UniquenessConstraint ; dal:constraintId "thing-key" ; dal:appliesTo ex:ThingScope ;
    dal:keyProperty ( ex:code ) ; dal:normalizePipeline dal:NfkcTrimUppercase ; dal:onViolation dal:Reject .
"""
# identity-minting M1: a claimed identity is complete only with a claim scheme
# on the constraint it names, plus a template and a surrogate kind.
CLAIM_SCHEME = """
ex:ThingKey dal:claimScheme ex:ThingScheme .
ex:ThingScheme a dal:ClaimScheme ; dal:schemeVersion "v1" ; dal:schemeState dal:Accepting ;
    dal:claimKeyId "thing-key-v1" ; dal:claimDigestScheme ex:ThingMac ;
    dal:claimIriTemplate "urn:key:thing:{schemeVersion}:{mac}" .
ex:ThingMac a dal:DigestScheme ; dal:digestFunction "HMAC-SHA-256" ; dal:digestWidthBits 128 ; dal:digestEncoding "base32" .
"""
CLAIMED = '; dal:surrogateKind dal:UuidV4Surrogate ; dal:mintedIriTemplate "urn:thing:{surrogate}" '
DIGEST = 'ex:D a dal:DigestScheme ; dal:digestFunction "SHA-256" ; dal:digestWidthBits 128 ; dal:digestEncoding "lowercase-hex" .'


def _graph(extra: str) -> Graph:
    g = Graph()
    g.parse(SPEC_TTL, format="turtle")
    g.parse(data=BASE + extra, format="turtle")
    return g


def _identity(extra: str) -> dict:
    return resolver.resolve_identity(_graph(extra), Target(CLS), None)


def _local(v) -> str:
    return str(v).rsplit("#", 1)[-1]


def _profile(name: str, role: str, strategy: str, scope: str = "ex:ThingScope", more: str = "") -> str:
    return (f"ex:{name} a dal:IdentityProfile ; dal:appliesTo {scope} ; dal:resourceRole dal:{role} ; "
            f"dal:identityStrategy dal:{strategy} {more}.\n")


def _check(extra: str, uniqueness: list | None = None):
    g = _graph(extra)
    target = Target(CLS)
    dims = {d: resolver.resolve_dimension(g, target, d, None) for d in DIMENSIONS}
    ident = resolver.resolve_identity(g, target, None)
    return check_identity(g, target, dims, ident, uniqueness if uniqueness is not None else [])


# ---- Decision 1: role-qualified resolution ----------------------------------------------------

ROLES = ["EntityRole", "AggregateRootRole", "ComponentRole", "LineageRole", "ContentRevisionRole",
         "GraphLocatorRole", "KeyClaimRole", "EventOccurrenceRole"]


@pytest.mark.parametrize("role", ROLES)
def test_every_role_resolves_as_its_own_dimension(role):
    ident = _identity(_profile("P", role, "RandomSurrogateIdentity"))
    assert list(ident) == [f"identity:{role}"]
    assert _local(ident[f"identity:{role}"].value) == "RandomSurrogateIdentity"


def test_one_class_resolves_different_strategies_per_role():
    extra = _profile("Own", "EntityRole", "RandomSurrogateIdentity") + _profile(
        "Events", "EventOccurrenceRole", "ExternalRegistryIdentity")
    ident = _identity(extra)
    assert _local(ident["identity:EntityRole"].value) == "RandomSurrogateIdentity"
    assert _local(ident["identity:EventOccurrenceRole"].value) == "ExternalRegistryIdentity"


def test_class_profile_overrides_namespace_default_per_role_only():
    extra = (
        _profile("NsEntity", "EntityRole", "RandomSurrogateIdentity", scope="ex:Wide")
        + _profile("NsEvents", "EventOccurrenceRole", "RandomSurrogateIdentity", scope="ex:Wide")
        + _profile("ClassEntity", "EntityRole", "NaturalKeyIdentity")
    )
    ident = _identity(extra)
    assert _local(ident["identity:EntityRole"].won_by) == "ClassEntity"
    assert _local(ident["identity:EventOccurrenceRole"].won_by) == "NsEvents"


def test_equal_priority_within_one_role_is_ambiguous():
    extra = _profile("A", "EntityRole", "NaturalKeyIdentity") + _profile("B", "EntityRole", "RandomSurrogateIdentity")
    with pytest.raises(ProfileAmbiguityError):
        _identity(extra)


def test_equal_priority_across_roles_is_not_ambiguous():
    extra = _profile("A", "EntityRole", "NaturalKeyIdentity") + _profile("B", "LineageRole", "NaturalKeyIdentity")
    assert len(_identity(extra)) == 2


def test_winning_node_carries_its_own_digest_scheme():
    """The digest scheme never mixes across nodes: a lower-priority node's
    scheme does not attach to a higher-priority node's strategy."""
    extra = DIGEST + "\n" + _profile("Low", "ContentRevisionRole", "ContentAddressedIdentity", scope="ex:Wide",
                                     more="; dal:digestScheme ex:D ") + _profile(
        "High", "ContentRevisionRole", "ContentAddressedIdentity")
    rd = _identity(extra)["identity:ContentRevisionRole"]
    assert _local(rd.won_by) == "High"
    assert rd.extra.get("digestScheme") is None


def test_undeclared_role_has_no_default():
    assert _identity("") == {}


def test_identity_dimensions_are_emitted_to_the_compiled_profile():
    g = Graph()
    g.parse(SPEC_TTL, format="turtle")
    g.parse(EXAMPLES_DIR / "identity-epoch-privacy-profile.ttl", format="turtle")
    out, _ = compile_to_graph(g, classes={URIRef("https://example.org/lending#Claimant")})
    by_dim = {str(out.value(n, DAL.dimension)): n for n in out.subjects(DAL.dimension, None)}
    assert _local(out.value(by_dim["identity:EntityRole"], DAL.resolvedValue)) == "SurrogateClaimedIdentity"
    assert _local(out.value(by_dim["identity:EntityRole"], DAL.wonBy)) == "ClaimantIdentity"
    assert _local(out.value(by_dim["identity:EventOccurrenceRole"], DAL.resolvedValue)) == "DerivedHashIdentity"
    assert "identity:KeyClaimRole" not in by_dim


def test_identity_generates_no_operations():
    """Decision 2: resolve, check, emit. The operation set is unchanged by an identity profile."""
    plain = compile_to_graph(_graph(KEY), classes={CLS})[1][0].operations
    complete = KEY + CLAIM_SCHEME + _profile("P", "EntityRole", "SurrogateClaimedIdentity",
                                             more=CLAIMED + "; dal:claimsConstraint ex:ThingKey ")
    with_identity = compile_to_graph(_graph(complete), classes={CLS})[1][0].operations
    assert [o.template_id for o in plain] == [o.template_id for o in with_identity]


# ---- Decision 3: checks, one positive and one negative each -----------------------------------


@pytest.mark.parametrize("strategy", ["DerivedHashIdentity", "ContentAddressedIdentity"])
def test_digest_scheme_required(strategy):
    with pytest.raises(CrossAxisViolation) as e:
        _check(_profile("P", "ContentRevisionRole", strategy))
    assert e.value.kind == "DigestSchemeRequired"
    _check(DIGEST + "\n" + _profile("P", "ContentRevisionRole", strategy, more="; dal:digestScheme ex:D "))


@pytest.mark.parametrize(
    "width,encoding",
    [("100", "lowercase-hex"), ("0", "lowercase-hex"), ("128", "hex"), ("128", "Base32")],
)
def test_digest_scheme_malformed(width, encoding):
    scheme = f'ex:D a dal:DigestScheme ; dal:digestFunction "SHA-256" ; dal:digestWidthBits {width} ; dal:digestEncoding "{encoding}" .'
    with pytest.raises(CrossAxisViolation) as e:
        _check(scheme + "\n" + _profile("P", "ContentRevisionRole", "DerivedHashIdentity", more="; dal:digestScheme ex:D "))
    assert e.value.kind == "DigestSchemeMalformed"


POSITION = "; dal:eventIdentityStrategy dal:PositionDerivedEvent "
WITNESS = "; dal:uniquenessWitnessRequired true "
DERIVATION = "; dal:occurrenceNamespaceDerivation dal:HashedTargetDerivation "
SAFE_EPOCH = "ex:E a dal:EpochProfile ; dal:appliesTo ex:ThingScope ; dal:epochGuardScope dal:DatasetLevelGuard ; dal:epochAuthority dal:ExternalHighWaterMark .\n"


def test_position_derived_event_requires_witness():
    with pytest.raises(CrossAxisViolation) as e:
        _check(_profile("P", "EventOccurrenceRole", "RandomSurrogateIdentity", more=POSITION + DERIVATION))
    assert e.value.kind == "UniquenessWitnessRequired"


def test_position_derived_event_requires_namespace_derivation():
    with pytest.raises(CrossAxisViolation) as e:
        _check(_profile("P", "EventOccurrenceRole", "RandomSurrogateIdentity", more=POSITION + WITNESS))
    assert e.value.kind == "OccurrenceNamespaceDerivationRequired"


def test_complete_position_derived_event_under_safe_epoch_passes_cleanly():
    kinds = {d.kind for d in _check(SAFE_EPOCH + _profile("P", "EventOccurrenceRole", "RandomSurrogateIdentity",
                                                          more=POSITION + WITNESS + DERIVATION))}
    assert "PositionEventUnsafeEpoch" not in kinds


@pytest.mark.parametrize(
    "epoch",
    [
        "",  # baseline: RowLevelGuardOnly
        "ex:E a dal:EpochProfile ; dal:appliesTo ex:ThingScope ; dal:epochGuardScope dal:DatasetLevelGuard ; dal:epochAuthority dal:StoreLocalEpoch .\n",
    ],
)
def test_position_derived_event_warns_under_unsafe_epoch(epoch):
    kinds = {d.kind for d in _check(epoch + _profile("P", "EventOccurrenceRole", "RandomSurrogateIdentity",
                                                     more=POSITION + WITNESS + DERIVATION))}
    assert "PositionEventUnsafeEpoch" in kinds


@pytest.mark.parametrize("role", ["EntityRole", "AggregateRootRole", "ComponentRole"])
def test_claimed_identity_requires_a_named_key(role):
    """identity-minting M1 replaced Slice 3's interim check (at least one
    uniqueness constraint on the target, entity and aggregate roles only)
    with the exact one: dal:claimsConstraint must name an applicable
    constraint, on every role that uses a claimed surrogate, because the
    recipe cannot be built otherwise."""
    without = KEY + CLAIM_SCHEME + _profile("P", role, "SurrogateClaimedIdentity", more=CLAIMED)
    with pytest.raises(CompileError) as e:
        compile_to_graph(_graph(without), classes={CLS})
    assert e.value.__cause__.kind == "ClaimedIdentityWithoutKey"
    complete = KEY + CLAIM_SCHEME + _profile("P", role, "SurrogateClaimedIdentity",
                                             more=CLAIMED + "; dal:claimsConstraint ex:ThingKey ")
    compiled = compile_to_graph(_graph(complete), classes={CLS})[1][0]
    assert [r["strategy"] for r in compiled.recipes] == ["SurrogateClaimedIdentity"]


@pytest.mark.parametrize(
    "fixture,kind",
    [
        ("invalid-claimed-identity-without-key.ttl", "ClaimedIdentityWithoutKey"),
        ("invalid-position-event-without-derivation.ttl", "OccurrenceNamespaceDerivationRequired"),
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


@pytest.mark.parametrize("width,encoding,conforms", [("128", "base32", True), ("100", "base32", False), ("128", "hex", False)])
def test_digest_scheme_well_formed_shape(width, encoding, conforms):
    import pyshacl

    shapes = Graph()
    shapes.parse(SPEC_TTL, format="turtle")
    shapes.parse(REPO_ROOT / "ontology" / "persistence" / "shapes" / "constraints.ttl", format="turtle")
    data = _graph(f'ex:D a dal:DigestScheme ; dal:digestFunction "SHA-256" ; dal:digestWidthBits {width} ; dal:digestEncoding "{encoding}" .')
    result, _, report = pyshacl.validate(data, shacl_graph=shapes, inference="none", advanced=True, allow_warnings=True)
    assert result is conforms, report
