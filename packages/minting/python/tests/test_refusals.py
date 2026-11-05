# SPDX-License-Identifier: MPL-2.0
"""Refusals outside the vector files: recipe loading, the runtime Unicode
check and error naming (identity-minting-specification.md §9)."""

from __future__ import annotations

import json
import re
import unicodedata

import pytest

from conftest import RECIPE_FILES, load
from lattice_minting import Minter, MintError, Recipe


def _recipe(prefix: str) -> dict:
    return load(next(p for p in RECIPE_FILES if p.name.startswith(prefix)))


def _kind(fn) -> str:
    with pytest.raises(MintError) as e:
        fn()
    return e.value.kind


def test_unknown_recipe_format():
    r = _recipe("Product") | {"recipeFormat": "lattice-minting-recipe/2"}
    assert _kind(lambda: Recipe.parse(r)) == "UnsupportedRecipeFormat"


def test_unknown_strategy():
    r = _recipe("Product") | {"strategy": "GuessedIdentity"}
    assert _kind(lambda: Recipe.parse(r)) == "UnsupportedRecipeFormat"


def test_any_change_breaks_the_digest():
    r = _recipe("Product")
    r["iriTemplate"] = r["iriTemplate"].replace("sku", "SKU")
    assert _kind(lambda: Recipe.parse(json.dumps(r))) == "RecipeDigestMismatch"


def test_whitespace_and_member_order_do_not_affect_the_digest():
    r = _recipe("Product")
    shuffled = json.dumps(dict(reversed(list(r.items()))), indent=7)
    assert Recipe.parse(shuffled).digest == r["recipeDigest"]


def test_pipeline_of_another_unicode_version_is_refused():
    r = _recipe("Product")
    r["key"]["pipeline"]["unicodeVersion"] = "15.1.0"
    assert _kind(lambda: Recipe.parse(_reseal(r))) == "UnsupportedRecipeFormat"


def _reseal(r: dict) -> dict:
    from lattice_minting.canonical import canonical_json
    import hashlib
    body = {k: v for k, v in r.items() if k != "recipeDigest"}
    return r | {"recipeDigest": "sha256:" + hashlib.sha256(canonical_json(body)).hexdigest()}


def test_claims_with_different_keys_are_refused():
    r = _recipe("Person")
    second = json.loads(json.dumps(r["claims"][0])) | {"schemeVersion": "v2", "schemeState": "Dual"}
    second["key"]["pipeline"] = _recipe("Product")["key"]["pipeline"]
    r["claims"][0]["schemeState"] = "Dual"
    r["claims"].append(second)
    assert _kind(lambda: Recipe.parse(_reseal(r))) == "UnsupportedRecipeFormat"


def test_older_runtime_unicode_is_refused(monkeypatch):
    recipe = Recipe.parse(_recipe("Product"))
    monkeypatch.setattr(unicodedata, "unidata_version", "15.1.0")
    assert _kind(lambda: Minter(recipe)) == "RuntimeUnicodeTooOld"


def test_error_kinds_are_closed():
    with pytest.raises(ValueError):
        MintError("SomethingElse", "not in the specification")


def test_random_surrogates_use_the_supplied_source():
    recipe = Recipe.parse(_recipe("LineItem"))
    minted = Minter(recipe, random_bytes=lambda n: bytes(n)).mint({})
    assert minted.iri == "urn:ex:line-item:00000000-0000-4000-8000-000000000000"
    uuid = re.compile(r"urn:ex:line-item:[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}")
    minter = Minter(recipe)
    assert len({minter.mint({}).iri for _ in range(50)}) == 50
    assert all(uuid.fullmatch(minter.mint({}).iri) for _ in range(50))


def test_minter_does_not_share_secrets_with_the_caller():
    recipe = Recipe.parse(_recipe("Person"))
    secrets = {"example-key-v1": b"k" * 32}
    minter = Minter(recipe, secrets)
    secrets.clear()
    minted = minter.mint({"key": ["ada@example.org"], "scope": "acme",
                          "surrogate": "8f2c1b7e-3e4a-4f7c-9a6d-2b1e0c5d7f90"})
    assert minted.claim_iris


def test_an_empty_secret_is_no_secret():
    recipe = Recipe.parse(_recipe("Person"))
    minter = Minter(recipe, {"example-key-v1": b""})
    assert _kind(lambda: minter.mint({"key": ["ada@example.org"], "scope": "acme",
                                      "surrogate": "8f2c1b7e-3e4a-4f7c-9a6d-2b1e0c5d7f90"})) == "MissingSecret"


def test_a_blank_canonicalizer_is_judged_by_white_space():
    """Blank means White_Space only, the same in every language (NO-BREAK
    SPACE is White_Space, INFORMATION SEPARATOR ONE is not)."""
    minter = Minter(Recipe.parse(_recipe("Contract")))
    nquads = '<urn:a> <urn:b> "c" .\n'
    assert _kind(lambda: minter.mint({"canonicalNQuads": nquads, "canonicalizer": chr(0x00A0)})) == "CanonicalizerNotDeclared"
    assert minter.mint({"canonicalNQuads": nquads, "canonicalizer": chr(0x1F)}).iri


def _scoped_natural_key() -> dict:
    r = _recipe("Policy")
    r["key"]["scopeProperty"] = "https://example.org/lending#tenant"
    return _reseal(r)


@pytest.mark.parametrize("component", [".", "..", chr(0xFF0E) * 2])
def test_a_dot_segment_is_refused_in_a_natural_key(component):
    minter = Minter(Recipe.parse(_scoped_natural_key()))
    assert _kind(lambda: minter.mint({"key": [component, "p-1"], "scope": "acme"})) == "DotSegment"
    if component in (".", ".."):  # a scope is not normalized, so only the literal forms are segments
        assert _kind(lambda: minter.mint({"key": ["acme", "p-1"], "scope": component})) == "DotSegment"
    assert minter.mint({"key": ["acme", "..."], "scope": "acme"}).iri.endswith("/ACME/...")


def test_a_dot_segment_is_fine_in_a_hashed_key():
    assert Minter(Recipe.parse(_recipe("Product"))).mint({"key": [".."]}).iri


def test_an_empty_scope_is_refused():
    minter = Minter(Recipe.parse(_scoped_natural_key()))
    assert _kind(lambda: minter.mint({"key": ["acme", "p-1"], "scope": ""})) == "EmptyScope"
    claimed = Minter(Recipe.parse(_recipe("Person")), {"example-key-v1": b"k" * 32})
    assert _kind(lambda: claimed.mint({"key": ["ada@example.org"], "scope": "",
                                       "surrogate": "8f2c1b7e-3e4a-4f7c-9a6d-2b1e0c5d7f90"})) == "EmptyScope"


def _permissive_surrogate(pattern: str) -> Minter:
    r = _recipe("Person")
    r["surrogate"]["pattern"] = pattern
    return Minter(Recipe.parse(_reseal(r)), {"example-key-v1": b"k" * 32})


@pytest.mark.parametrize("surrogate", ["a/b", "a#b", "a?b", "a b", "a%2Fb", "", "caf" + chr(0xE9)])
def test_a_surrogate_outside_the_unreserved_set_is_refused(surrogate):
    minter = _permissive_surrogate(".*")
    inputs = {"key": ["ada@example.org"], "scope": "acme", "surrogate": surrogate}
    assert _kind(lambda: minter.mint(inputs)) == "UnsafeSurrogate"


def test_an_unreserved_surrogate_is_accepted_and_dot_segments_are_not():
    minter = _permissive_surrogate(".+")
    inputs = {"key": ["ada@example.org"], "scope": "acme"}
    assert minter.mint(inputs | {"surrogate": "A-b.c_d~9"}).iri == "urn:person:A-b.c_d~9"
    assert _kind(lambda: minter.mint(inputs | {"surrogate": ".."})) == "DotSegment"


def test_a_position_wider_than_its_width_is_refused_with_both_numbers():
    minter = Minter(Recipe.parse(_recipe("Shipment")))
    with pytest.raises(MintError) as e:
        minter.mint({"namespaceToken": "ship-1", "epoch": 10000, "seq": 1})
    assert e.value.kind == "PositionWidthOverflow"
    assert "10000" in str(e.value) and "4" in str(e.value)
    assert minter.mint({"namespaceToken": "ship-1", "epoch": 9999, "seq": 1}).iri
    assert _kind(lambda: minter.mint({"namespaceToken": "..", "epoch": 1, "seq": 1})) == "DotSegment"
