# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""identity-minting M1: minting recipes built by the compiler, emitted into
the compiled profile, and exported as JSON. The central check is that the
compiler reproduces the hand-authored anchor recipes in
contracts/identity/anchor-vectors.json byte for byte."""

from __future__ import annotations

import hashlib
import json
import random
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator
from referencing import Registry, Resource
from rdflib import Graph, URIRef

from persistence.compiler import CompileError, compile_to_graph
from persistence.namespaces import DAL
from persistence.recipes import export_recipes

REPO_ROOT = Path(__file__).resolve().parents[3]
SPEC_TTL = REPO_ROOT / "ontology" / "persistence" / "spec" / "persistence.ttl"
EXAMPLES_DIR = REPO_ROOT / "ontology" / "persistence" / "examples"
CONTRACTS = REPO_ROOT / "contracts" / "identity"
RDF_JSON = URIRef("http://www.w3.org/1999/02/22-rdf-syntax-ns#JSON")
T = "https://example.org/lending#"


def _graph(*fixtures: str, data: str = "") -> Graph:
    g = Graph()
    g.parse(SPEC_TTL, format="turtle")
    for f in fixtures:
        g.parse(EXAMPLES_DIR / f, format="turtle")
    if data:
        g.parse(data=data, format="turtle")
    return g


def _recipes(g: Graph) -> dict[str, dict]:
    out = {}
    for ct in compile_to_graph(g)[1]:
        for r in ct.recipes:
            out[r["strategy"]] = r
    return out


@pytest.fixture(scope="module")
def recipe_validator():
    schemas = [json.loads((CONTRACTS / n).read_text()) for n in ("recipe.schema.json", "vectors.schema.json")]
    registry = Registry().with_resources([(s["$id"], Resource.from_contents(s)) for s in schemas])
    return Draft202012Validator(schemas[0], registry=registry)


@pytest.fixture(scope="module")
def anchor_recipes() -> dict[str, dict]:
    doc = json.loads((CONTRACTS / "anchor-vectors.json").read_text(encoding="utf-8"))
    return {s["recipe"]["strategy"]: s["recipe"] for s in doc["sets"]}


# ---- The compiler reproduces the anchors ---------------------------------------------------------


def test_compiled_recipes_equal_the_hand_authored_anchor_recipes(anchor_recipes):
    compiled = _recipes(_graph("identity-minting-anchors.ttl"))
    assert set(compiled) == set(anchor_recipes)
    for strategy, recipe in anchor_recipes.items():
        assert compiled[strategy] == recipe, strategy


def test_every_emitted_recipe_satisfies_the_published_schema(recipe_validator):
    for fixture in ("identity-minting-anchors.ttl", "identity-epoch-privacy-profile.ttl"):
        for recipe in _recipes(_graph(fixture)).values():
            errors = [e.message for e in recipe_validator.iter_errors(recipe)]
            assert not errors, (recipe["strategy"], errors)


def test_recipe_digest_recomputed_independently():
    for recipe in _recipes(_graph("identity-minting-anchors.ttl")).values():
        body = {k: v for k, v in recipe.items() if k != "recipeDigest"}
        canonical = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        assert recipe["recipeDigest"] == "sha256:" + hashlib.sha256(canonical).hexdigest()


def test_recipe_digests_are_invariant_under_triple_order():
    g = _graph("identity-minting-anchors.ttl")
    triples = list(g)
    digests = None
    for seed in range(3):
        random.Random(seed).shuffle(triples)
        shuffled = Graph()
        for t in triples:
            shuffled.add(t)
        got = sorted(r["recipeDigest"] for r in _recipes(shuffled).values())
        assert digests is None or got == digests
        digests = got


# ---- Emission and export --------------------------------------------------------------------------


def test_recipes_are_emitted_as_canonical_json_literals():
    out, compiled = compile_to_graph(_graph("identity-minting-anchors.ttl"))
    nodes = list(out.subjects(predicate=DAL.recipeDigest))
    assert len(nodes) == sum(len(ct.recipes) for ct in compiled) == 7
    for node in nodes:
        doc = out.value(node, DAL.recipeDocument)
        assert doc.datatype == RDF_JSON
        recipe = json.loads(str(doc))
        assert str(out.value(node, DAL.recipeDigest)) == recipe["recipeDigest"]
        assert out.value(node, DAL.forRole) == DAL[recipe["role"]]


def test_export_recipes_writes_each_recipe_and_refuses_a_tampered_one(tmp_path, anchor_recipes):
    out, _ = compile_to_graph(_graph("identity-minting-anchors.ttl"))
    written = export_recipes(out, tmp_path)
    assert len(written) == 7
    exported = {json.loads(p.read_text())["strategy"]: json.loads(p.read_text()) for p in written}
    assert exported == anchor_recipes
    node = next(iter(out.subjects(predicate=DAL.recipeDocument)))
    doc = out.value(node, DAL.recipeDocument)
    out.set((node, DAL.recipeDocument, type(doc)(str(doc).replace("urn:", "urx:"), datatype=RDF_JSON)))
    with pytest.raises(ValueError):
        export_recipes(out, tmp_path / "tampered")


def test_export_recipes_cli(tmp_path):
    from persistence.cli import main

    compiled = tmp_path / "compiled.ttl"
    g = _graph("identity-minting-anchors.ttl")
    src = tmp_path / "config.ttl"
    g.serialize(destination=str(src), format="turtle")
    assert main(["compile", str(src), "--out", str(compiled)]) == 0
    assert main(["export-recipes", str(compiled), "--out", str(tmp_path / "recipes")]) == 0
    assert len(list((tmp_path / "recipes").glob("*.recipe.json"))) == 7


def test_content_addressed_recipes_carry_and_warn_the_caller_obligations():
    out, compiled = compile_to_graph(_graph("identity-minting-anchors.ttl"))
    contract = next(ct for ct in compiled if str(ct.target.cls) == T + "Contract")
    assert [o["id"] for o in contract.recipes[0]["callerObligations"]] == ["CA-1", "CA-2", "CA-3", "CA-4"]
    assert "ContentAddressedCallerObligations" in {d.kind for d in contract.diagnostics}


# ---- Rotation --------------------------------------------------------------------------------------

DUAL = """
@prefix dal: <https://www.nebularis.org/neuro-semantic/lattice/persistence#> .
@prefix ex:  <https://example.org/lending#> .
ex:PersonEmailSchemeV1 dal:schemeState dal:Dual .
ex:PersonEmailUnique dal:claimScheme ex:PersonEmailSchemeV2 .
ex:PersonEmailSchemeV2 a dal:ClaimScheme ; dal:schemeVersion "v2" ; dal:schemeState dal:Dual ;
    dal:claimKeyId "example-key-v2" ; dal:claimDigestScheme ex:PersonEmailMac ;
    dal:claimIriTemplate "urn:key:person-email:{schemeVersion}:{mac}" .
"""


def test_dual_rotation_emits_both_claims_in_version_order():
    g = _graph("identity-minting-anchors.ttl", data=DUAL)
    g.remove((URIRef(T + "PersonEmailSchemeV1"), DAL.schemeState, DAL.Accepting))
    claims = _recipes(g)["SurrogateClaimedIdentity"]["claims"]
    assert [(c["schemeVersion"], c["schemeState"], c["keyId"]) for c in claims] == [
        ("v1", "Dual", "example-key-v1"), ("v2", "Dual", "example-key-v2")]


def test_retiring_scheme_is_not_minted():
    g = _graph("identity-minting-anchors.ttl", data=DUAL)
    g.remove((URIRef(T + "PersonEmailSchemeV1"), DAL.schemeState, DAL.Accepting))
    g.remove((URIRef(T + "PersonEmailSchemeV1"), DAL.schemeState, DAL.Dual))
    g.add((URIRef(T + "PersonEmailSchemeV1"), DAL.schemeState, DAL.Retiring))
    claims = _recipes(g)["SurrogateClaimedIdentity"]["claims"]
    assert [c["schemeVersion"] for c in claims] == ["v2"]


# ---- Refusals: each member a self-contained recipe needs --------------------------------------------


def _without(subject: str, prop, value=None):
    def mutate(g: Graph):
        for o in list(g.objects(URIRef(T + subject), prop)):
            if value is None or o == value:
                g.remove((URIRef(T + subject), prop, o))
    return mutate


def _add(subject: str, prop, value):
    return lambda g: g.set((URIRef(T + subject), prop, value))


def _lit(v):
    from rdflib import Literal
    return Literal(v)


REFUSALS = [
    ("template missing", _without("ProductIdentity", DAL.mintedIriTemplate), "MintedIriTemplateRequired"),
    ("template wrong slot", _add("ProductIdentity", DAL.mintedIriTemplate, _lit("urn:ex:sku:{key}")), "MintedIriTemplateInvalid"),
    ("template extra slot", _add("PolicyIdentity", DAL.mintedIriTemplate, _lit("urn:ex:{key}/{digest}")), "MintedIriTemplateInvalid"),
    ("key constraint missing", _without("PolicyIdentity", DAL.keyConstraint), "KeyConstraintRequired"),
    ("key constraint of another class", _add("PolicyIdentity", DAL.keyConstraint, URIRef(T + "ProductSkuUnique")), "KeyConstraintNotApplicable"),
    ("tuple prefix missing", _without("ProductIdentity", DAL.tuplePrefix), "TuplePrefixRequired"),
    ("digest scheme missing", _without("ProductIdentity", DAL.digestScheme), "DigestSchemeRequired"),
    ("digest function wrong", _add("ProductDigest", DAL.digestFunction, _lit("SHA-512")), "DigestFunctionUnsupported"),
    ("claims constraint missing", _without("PersonIdentity", DAL.claimsConstraint), "ClaimedIdentityWithoutKey"),
    ("claims constraint of another class", _add("PersonIdentity", DAL.claimsConstraint, URIRef(T + "ProductSkuUnique")), "KeyConstraintNotApplicable"),
    ("surrogate kind missing", _without("PersonIdentity", DAL.surrogateKind), "SurrogateKindRequired"),
    ("caller pattern missing", _without("PersonIdentity", DAL.callerSuppliedPattern), "CallerSuppliedPatternRequired"),
    ("no minting claim scheme", _without("PersonEmailUnique", DAL.claimScheme), "ClaimSchemeIncomplete"),
    ("claim key id missing", _without("PersonEmailSchemeV1", DAL.claimKeyId), "ClaimSchemeIncomplete"),
    ("claim MAC is a plain digest", _add("PersonEmailMac", DAL.digestFunction, _lit("SHA-256")), "DigestFunctionUnsupported"),
    ("claim template without mac", _add("PersonEmailSchemeV1", DAL.claimIriTemplate, _lit("urn:key:{schemeVersion}")), "MintedIriTemplateInvalid"),
    ("pipeline missing", _without("PolicyNumberUnique", DAL.normalizePipeline), "NormalizePipelineRequired"),
    ("widths missing", _without("OrderEvents", DAL.epochWidth), "PositionWidthsRequired"),
    ("width too wide", _add("OrderEvents", DAL.sequenceWidth, _lit(20)), "PositionWidthsRequired"),
    ("self-reference rule missing", _without("ContractRevisions", DAL.selfReferenceRule), "ContentAddressedMembersRequired"),
    ("work budget missing", _without("ContractRevisions", DAL.canonicalizationWorkBudget), "ContentAddressedMembersRequired"),
]


@pytest.mark.parametrize("label,mutate,kind", REFUSALS, ids=[r[0] for r in REFUSALS])
def test_incomplete_recipe_is_refused(label, mutate, kind):
    g = _graph("identity-minting-anchors.ttl")
    mutate(g)
    with pytest.raises(CompileError) as e:
        compile_to_graph(g)
    assert e.value.__cause__.kind == kind, (label, e.value.__cause__)


ADOPTED = """
@prefix dal: <https://www.nebularis.org/neuro-semantic/lattice/persistence#> .
@prefix ex:  <https://example.org/lending#> .
ex:PartyScope a dal:ClassScope ; dal:priority 10 ; dal:targetClass ex:Party .
ex:PartyIdentity a dal:IdentityProfile ; dal:appliesTo ex:PartyScope ; dal:resourceRole dal:EntityRole ;
    dal:identityStrategy dal:AdoptedIdentity ; dal:namingAuthority "national party register" ;
    dal:acceptedIriPattern "^https://register[.]example/party/[0-9]{8}$" .
"""


def test_adopted_identity_recipe_validates_only(recipe_validator):
    recipe = _recipes(_graph(data=ADOPTED))["AdoptedIdentity"]
    assert "iriTemplate" not in recipe
    assert recipe["acceptedPattern"] == "^https://register[.]example/party/[0-9]{8}$"
    assert not list(recipe_validator.iter_errors(recipe))


def test_adopted_identity_without_pattern_is_refused():
    g = _graph(data=ADOPTED)
    g.remove((URIRef(T + "PartyIdentity"), DAL.acceptedIriPattern, None))
    with pytest.raises(CompileError) as e:
        compile_to_graph(g)
    assert e.value.__cause__.kind == "AcceptedPatternRequired"
