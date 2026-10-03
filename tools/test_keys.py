# SPDX-License-Identifier: MPL-2.0

"""External and natural keys (computable-contract-substrate F1, ADR-A114).
Row IDs are the F1 Validation Pack's. Reasoner rows skip when the ADR-A83
harness jar is not built."""

from __future__ import annotations

import re
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest
from pyshacl import validate
from rdflib import Graph, Namespace, URIRef
from rdflib.namespace import OWL, RDF, RDFS, SH

ROOT = Path(__file__).resolve().parents[1]
for source in ("tools/mork_compilers/src", "tools/persistence/src", "tools/surface/src", "packages/minting/python/src"):
    sys.path.insert(0, str(ROOT / source))
sys.path.insert(0, str(ROOT / "tools"))

import literate_extract  # noqa: E402
from lattice_minting import Minter, Recipe  # noqa: E402
from mork_compilers import reasoning  # noqa: E402
from persistence.compiler import compile_to_graph  # noqa: E402

LATTICE = "https://www.nebularis.org/neuro-semantic/lattice/"
FND = Namespace(LATTICE + "foundation#")
DAL = Namespace(LATTICE + "persistence#")
EX = Namespace("https://example.org/lattice/foundation/keys#")
FOUNDATION = ROOT / "ontology" / "foundation"
PERSISTENCE = ROOT / "ontology" / "persistence"
SPEC = FOUNDATION / "spec" / "foundation.ttl"
DAL_SPEC = PERSISTENCE / "spec" / "persistence.ttl"
PF_SPEC = PERSISTENCE / "spec" / "persistent-foundation.ttl"
FND_EXAMPLE = FOUNDATION / "examples" / "keys.ttl"
DAL_EXAMPLE = PERSISTENCE / "examples" / "persistent-foundation-keys.ttl"
SRF_EXAMPLE = ROOT / "ontology" / "surface" / "examples" / "keys.ttl"
NEW_PROPERTIES = ("keyValue", "keyScheme", "externalKey", "naturalKey", "reissuesValues", "sensitiveDataScheme",
                  "personalDataScheme", "valuePattern", "keyNormalisation")


def _graph(*sources) -> Graph:
    g = Graph()
    for source in sources:
        if isinstance(source, Path):
            g.parse(source)
        else:
            g.parse(data=source, format="turtle")
    return g


FND_SHAPES = _graph(FOUNDATION / "shapes" / "constraints.ttl")
PF_SHAPES = _graph(PERSISTENCE / "shapes" / "persistent-foundation.ttl")
PREFIXES = (f"@prefix fnd: <{FND}> .\n@prefix dal: <{DAL}> .\n@prefix ex: <{EX}> .\n"
            "@prefix owl: <http://www.w3.org/2002/07/owl#> .\n"
            "@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .\n")


def _results(data: Graph, shapes: Graph, severity=SH.Violation) -> list[tuple[str, str]]:
    _, report, _ = validate(data, shacl_graph=shapes, inference="none", advanced=True)
    return [(str(report.value(r, SH.focusNode)), str(report.value(r, SH.resultMessage)))
            for r in report.subjects(SH.resultSeverity, severity)]


def _reported(data: Graph, shapes: Graph, focus: str, fragment: str, severity=SH.Violation) -> bool:
    return any(f.endswith(focus) and fragment in m for f, m in _results(data, shapes, severity))


def _keyed(extra: str) -> Graph:
    """Foundation's spec, the example's schemes and keys, and a fragment."""
    return _graph(SPEC, FND_EXAMPLE, PREFIXES + extra)


# ---- F1-01: the spec --------------------------------------------------------

def test_f1_01_spec_version_comments_and_layer() -> None:
    spec = _graph(SPEC)
    assert spec.value(URIRef("https://www.nebularis.org/neuro-semantic/foundation"), OWL.versionIRI) == URIRef(LATTICE + "foundation/0.4.0")
    for name in NEW_PROPERTIES:
        utility = str(spec.value(FND[name], FND.utility))
        assert utility.startswith("Subject:") and "Value:" in utility, name
    text = SPEC.read_text()
    for layer in ("vocabulary", "quantification", "party", "eligibility", "wording", "behaviour", "instrument", "persistence"):
        assert f"lattice/{layer}" not in text, layer
    assert (FND.externalKey, OWL.propertyChainAxiom, None) in spec  # G2
    assert (FND.MergedOnNaturalKey, OWL.hasKey, None) in spec


# ---- F1-02: the examples conform --------------------------------------------

def test_f1_02_examples_conform() -> None:
    data = _graph(SPEC, DAL_SPEC, PF_SPEC, FND_EXAMPLE, DAL_EXAMPLE)
    assert _results(data, FND_SHAPES) == []
    assert _results(data, PF_SHAPES) == []
    assert validate(data, shacl_graph=_graph(PERSISTENCE / "shapes" / "constraints.ttl"), inference="none", advanced=True)[0]


# ---- F1-03, F1-04, F1-05, F1-13: reasoner -----------------------------------

needs_reasoner = pytest.mark.skipif(not reasoning.available(), reason="reasoning-testkit jar not built")
PAIR = """
ex:a a ex:{cls} ; fnd:naturalKey ex:k .
ex:b a ex:{cls} ; fnd:naturalKey ex:k .
ex:k a fnd:Key ; fnd:keyScheme ex:lei ; fnd:keyValue "5493001KJTIIGC8Y1R12" .
ex:a owl:differentFrom ex:b .
"""


@needs_reasoner
def test_f1_03_examples_are_consistent() -> None:
    assert reasoning.run("consistent", graphs=[_graph(SPEC, FND_EXAMPLE)]) is True
    assert reasoning.run("consistent", graphs=[_graph(SPEC, DAL_SPEC, PF_SPEC, FND_EXAMPLE, DAL_EXAMPLE)]) is True


@needs_reasoner
def test_f1_04_merged_on_natural_key_merges() -> None:
    """Two named members sharing a natural key are the same individual, so
    stating them different is inconsistent."""
    data = _graph(SPEC, FND_EXAMPLE, PREFIXES + "ex:Register rdfs:subClassOf fnd:MergedOnNaturalKey ."
                  + PAIR.format(cls="Register"))
    assert reasoning.run("consistent", graphs=[data]) is False


@needs_reasoner
def test_f1_05_persistence_keyed_does_not_merge() -> None:
    fragment = "ex:Register rdfs:subClassOf dal:PersistenceKeyed ." + PAIR.format(cls="Register")
    assert reasoning.run("consistent", graphs=[_graph(SPEC, PF_SPEC, FND_EXAMPLE, PREFIXES + fragment)]) is True
    data = _graph(SPEC, PF_SPEC, FND_EXAMPLE, PREFIXES + fragment)
    assert _reported(data, FND_SHAPES, "#a", "both have")
    assert not _results(data, FND_SHAPES, SH.Warning)


def test_f1_05_persistence_compiles_the_natural_key_constraint() -> None:
    _, compiled = compile_to_graph(_graph(DAL_SPEC, DAL_EXAMPLE), classes={EX.Company})
    ops = {o.operation for o in compiled[0].operations}
    assert "key-claim-write:company-natural-key-unique" in ops
    assert "key-claim-duplicate-audit:company-natural-key-unique" in ops


@needs_reasoner
def test_f1_13_versions_carry_their_identitys_keys() -> None:
    """The property chain: each version carries every key of its identity as
    fnd:externalKey, and never becomes fnd:NaturallyKeyed."""
    pairs = set(map(tuple, reasoning.run("values", str(FND.externalKey), graphs=[_graph(SPEC, FND_EXAMPLE)])))
    for version in (EX["facility-v1"], EX["facility-v2"]):
        carried = {o for s, o in pairs if s == str(version)}
        assert len(carried) == 3, carried
    not_keyed = PREFIXES + "ex:facility-v1 a [ owl:complementOf fnd:NaturallyKeyed ] ."
    assert reasoning.run("consistent", graphs=[_graph(SPEC, FND_EXAMPLE, not_keyed)]) is True


# ---- F1-06: Foundation's shapes ---------------------------------------------

@pytest.mark.parametrize("fragment, focus, message", [
    ('ex:k1 a fnd:Key ; fnd:keyValue "X" .', "#k1", "exactly one fnd:keyScheme"),
    ('ex:k2 a fnd:Key ; fnd:keyScheme ex:lei ; fnd:keyValue "5493001KJTIIGC8Y1R12" , "5493001KJTIIGC8Y1R13" .', "#k2", "exactly one fnd:keyValue"),
    ('ex:k3 a fnd:Key ; fnd:keyScheme ex:lei ; fnd:keyValue "not an LEI" .', "#k3", "does not match"),
    ('ex:s1 a fnd:KeyScheme ; fnd:reissuesValues false ; fnd:sensitiveDataScheme false ; fnd:keyNormalisation "Lowercase" .', "#s1", "names one of the minting"),
    ('ex:x a fnd:NaturallyKeyed ; fnd:naturalKey <https://example.org/lattice/foundation/keys/key/3f6a0c9e-2b7d-4e1f-a58c-06d9b2e47f13> .', "#x", "reissues values"),
    ('ex:s2 a fnd:KeyScheme ; fnd:reissuesValues false ; fnd:sensitiveDataScheme false ; fnd:personalDataScheme true .', "#s2", "Personal data is sensitive"),
    ('ex:s3 a fnd:KeyScheme ; fnd:reissuesValues false .', "#s3", "fnd:sensitiveDataScheme exactly once"),
])
def test_f1_06_foundation_shapes_report(fragment: str, focus: str, message: str) -> None:
    assert _reported(_keyed(fragment), FND_SHAPES, focus, message)


def test_f1_q1_merged_pair_is_a_warning_not_a_violation() -> None:
    """F1-Q1 (b): two fnd:MergedOnNaturalKey members sharing a natural key
    are the merge announced, at sh:Warning. Any other pair is a violation."""
    merged = _keyed("ex:Register rdfs:subClassOf fnd:MergedOnNaturalKey ." + PAIR.format(cls="Register"))
    assert not [r for r in _results(merged, FND_SHAPES) if "both have" in r[1]]
    assert _reported(merged, FND_SHAPES, "#a", "owl:sameAs", SH.Warning)
    plain = _keyed("ex:Register rdfs:subClassOf fnd:NaturallyKeyed ." + PAIR.format(cls="Register"))
    assert _reported(plain, FND_SHAPES, "#a", "both have")
    assert not _results(plain, FND_SHAPES, SH.Warning)


# ---- F1-07: key IRIs are minted by their recipes ----------------------------

INPUTS = {"AgreementNumberKey": "FA-2027-0412", "MarketReferenceKey": "MR-2027-000412", "CompanyNumberKey": "01234567",
          "LeiKey": "5493001KJTIIGC8Y1R12", "AccountNumberKey": "31926819", "NationalIdKey": "QQ123456C"}
RANDOM = {"AccountNumberKey": "3f6a0c9e2b7d4e1fa58c06d9b2e47f13", "NationalIdKey": "9b1d7e40c3a2456f8e0b1c2d3e4f5a6b"}
IRI_RE = re.compile(r"^[a-z][a-z0-9+.-]*:[A-Za-z0-9\-._~:/?#\[\]@!$&'()*+,;=%]+$")


def test_f1_07_example_key_iris_are_minted_by_their_recipes() -> None:
    example = _graph(FND_EXAMPLE)
    out, _ = compile_to_graph(_graph(DAL_SPEC, DAL_EXAMPLE))
    recipes = [str(doc) for doc in out.objects(None, DAL.recipeDocument)]
    assert len(recipes) == 6
    secrets = {"tenant-account-number-key-v1": b"test-secret-0001", "tenant-national-id-key-v1": b"test-secret-0002"}
    for document in recipes:
        recipe = Recipe.parse(document)
        key_class = next(name for name in INPUTS if f"#{name}" in document)
        request = {"key": [INPUTS[key_class]]}
        if key_class in RANDOM:
            request["randomHex"] = RANDOM[key_class]
        iri = Minter(recipe, secrets=secrets).mint(request).iri
        assert (URIRef(iri), RDF.type, EX[key_class]) in example, (key_class, iri)
        assert IRI_RE.match(iri), iri


# ---- F1-08, F1-14: persistent-foundation's shapes ---------------------------

def _configured(extra: str) -> Graph:
    return _graph(SPEC, DAL_SPEC, PF_SPEC, FND_EXAMPLE, DAL_EXAMPLE, PREFIXES + extra)


def test_f1_08_sensitive_schemes_are_claimed_and_not_public() -> None:
    hashed = ("ex:NationalIdKeyIdentity dal:identityStrategy dal:DerivedHashIdentity .")
    data = _configured(hashed)
    data.remove((EX.NationalIdKeyIdentity, DAL.identityStrategy, DAL.SurrogateClaimedIdentity))
    assert _reported(data, PF_SHAPES, "#national-id", "#DerivedHashIdentity")
    public = _configured("")
    public.remove((EX.AccountNumberKeyPrivacy, DAL.privacyClass, DAL.InternalData))
    public.add((EX.AccountNumberKeyPrivacy, DAL.privacyClass, DAL.PublicData))
    assert _reported(public, PF_SHAPES, "#account-number", "dal:PublicData one")
    internal = _configured("")
    internal.remove((EX.NationalIdKeyPrivacy, DAL.privacyClass, DAL.PersonalData))
    internal.add((EX.NationalIdKeyPrivacy, DAL.privacyClass, DAL.InternalData))
    assert _reported(internal, PF_SHAPES, "#national-id", "of dal:PersonalData")


@pytest.mark.parametrize("fragment, focus, message", [
    ('ex:orphan a fnd:KeyScheme ; fnd:reissuesValues false ; fnd:sensitiveDataScheme false .', "#orphan", "has 0 key classes"),
    ('ex:SecondLeiKey rdfs:subClassOf fnd:Key ; owl:equivalentClass [ owl:onProperty fnd:keyScheme ; owl:hasValue ex:lei ] .', "#lei", "has 2 key classes"),
    ('ex:x a fnd:Key , ex:LeiKey ; fnd:keyScheme ex:company-number ; fnd:keyValue "01234568" .', "#x", "the key class of"),
    ('ex:y a fnd:Key ; fnd:keyScheme ex:lei ; fnd:keyValue "5493001KJTIIGC8Y1R12" .', "#y", "not asserted a member"),
    ('ex:Register rdfs:subClassOf dal:PersistenceKeyed .', "#Register", "no dal:UniquenessConstraint"),
    ('ex:Company rdfs:subClassOf fnd:MergedOnNaturalKey .', "#Company", "Choose one"),
])
def test_f1_14_persistent_foundation_shapes_report(fragment: str, focus: str, message: str) -> None:
    assert _reported(_configured(fragment), PF_SHAPES, focus, message)


def test_f1_14_key_class_without_identity_profile() -> None:
    data = _configured("")
    data.remove((EX.LeiKeyIdentity, None, None))
    assert _reported(data, PF_SHAPES, "#lei", "no dal:IdentityProfile")


def test_f1_14_normalisation_mismatch() -> None:
    data = _configured("")
    data.remove((EX.LeiKeyUnique, DAL.normalizePipeline, DAL.NfkcTrimUppercase))
    data.add((EX.LeiKeyUnique, DAL.normalizePipeline, DAL.NfkcTrimCasefold))
    assert _reported(data, PF_SHAPES, "#lei", "must normalise")


# ---- F1-09: the lookup paths ------------------------------------------------

def test_f1_09_lookup_paths() -> None:
    g = _graph(FND_EXAMPLE)
    current = g.query(f"""PREFIX fnd: <{FND}> PREFIX ex: <{EX}>
        SELECT ?version WHERE {{
          ?key fnd:keyScheme ex:market-reference ; fnd:keyValue "MR-2027-000412" .
          ?version fnd:hasIdentity/fnd:naturalKey ?key .
          FILTER NOT EXISTS {{ ?version fnd:supersededBy ?later }} }}""")
    assert {row.version for row in current} == {EX["facility-v2"]}
    company = g.query(f"""PREFIX fnd: <{FND}> PREFIX ex: <{EX}>
        SELECT ?thing WHERE {{ ?key fnd:keyScheme ex:lei . ?thing fnd:hasIdentity?/fnd:naturalKey ?key }}""")
    assert {row.thing for row in company} == {EX.acme}
    located = g.query(f"""PREFIX fnd: <{FND}>
        SELECT ?thing WHERE {{ ?thing fnd:externalKey|fnd:naturalKey <https://example.org/lattice/foundation/keys/key/market-reference/MR-2027-000412> }}""")
    assert {row.thing for row in located} == {EX["facility-identity"], EX["drawdown-1"], EX["drawdown-2"], EX["transfer-1"]}


# ---- F1-10: the cascade -----------------------------------------------------

def test_f1_10_nothing_pins_foundation_0_3_0() -> None:
    pinned = subprocess.run(["git", "grep", "-l", "-F", LATTICE + "foundation/0.3.0", "--", "ontology", "tools", "packages"],
                            cwd=ROOT, capture_output=True, text=True).stdout.split()
    assert [p for p in pinned if not p.startswith("tools/fixtures/import_guard/")] == []


# ---- F1-11: literate source and release notes -------------------------------

def test_f1_11_readme_is_the_source_and_releases_are_recorded() -> None:
    assert literate_extract.main([str(FOUNDATION / "README.md"), "--layer", "foundation", "--root", str(ROOT),
                                  "--shapes", "shapes/constraints.ttl", "--check"]) == 0
    assert "**0.4.0** (additive, CCS F1" in (FOUNDATION / "README.md").read_text()
    register = (ROOT / "docs" / "architecture" / "ontology-releases.md").read_text()
    for tag in ("foundation-v0.4.0", "foundation-shapes-v0.2.0", "persistent-foundation-v0.1.0", "persistence-shapes-v0.2.0",
                "instrument-v0.8.0", "surface-v0.6.0", "mork-v0.5.0"):
        assert f"| {tag} |" in register, tag
    assert "persistent-foundation" in (PERSISTENCE / "README.md").read_text()


# ---- F1-15: the Surface promotions ------------------------------------------

def test_f1_15_surface_promotes_every_identity_key_onto_versions() -> None:
    from surface import cli

    with tempfile.TemporaryDirectory() as out:
        assert cli.main(["compile", "--contracts", str(SRF_EXAMPLE), "--sources", str(FND_EXAMPLE),
                         "--out", out, "--now", "2026-10-03T00:00:00Z"]) == 0
        generated = Graph()
        for path in Path(out).rglob("*.ttl"):
            generated.parse(path)
    natural = {URIRef("https://example.org/lattice/foundation/keys/key/agreement-number/FA-2027-0412"),
               URIRef("https://example.org/lattice/foundation/keys/key/market-reference/MR-2027-000412")}
    account = URIRef("https://example.org/lattice/foundation/keys/key/3f6a0c9e-2b7d-4e1f-a58c-06d9b2e47f13")
    for version in (EX["facility-v1"], EX["facility-v2"]):
        assert set(generated.objects(version, FND.externalKey)) == natural | {account}
        assert (version, FND.naturalKey, None) not in generated
        assert (version, RDF.type, FND.NaturallyKeyed) not in generated


def test_f1_15_one_contract_alone_misses_the_external_key() -> None:
    from surface import cli

    with tempfile.TemporaryDirectory() as out:
        assert cli.main(["compile", "--contracts", str(SRF_EXAMPLE), "--sources", str(FND_EXAMPLE), "--out", out,
                         "--now", "2026-10-03T00:00:00Z",
                         "--contract", "https://example.org/lattice/surface/keys#version-natural-keys"]) == 0
        generated = Graph()
        for path in Path(out).rglob("*.ttl"):
            generated.parse(path)
    account = URIRef("https://example.org/lattice/foundation/keys/key/3f6a0c9e-2b7d-4e1f-a58c-06d9b2e47f13")
    assert (EX["facility-v1"], FND.externalKey, account) not in generated
