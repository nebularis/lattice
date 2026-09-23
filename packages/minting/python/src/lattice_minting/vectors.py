# SPDX-License-Identifier: MPL-2.0
"""Conformance vector generation (identity-minting-specification.md §10).

This library is the reference implementation from which vectors are
generated. Vectors generated here can only show that another implementation
agrees with this one, which is why every implementation must also pass the
independently verified anchors in ``contracts/identity/anchor-vectors.json``.

Generation is deterministic: random surrogates use fixed ``randomHex``
inputs, and each claim key gets a published test secret derived from its key
id, labelled as never for production use.
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Mapping

from .errors import MintError
from .minter import MAX_POSITION, Minter
from .recipe import Recipe

VECTORS_FORMAT = "lattice-minting-vectors/1"

# Key component corpus: (category, value). Each is placed in the first key
# component, with the other components held at plain ASCII values.
KEY_CORPUS = [
    ("ascii", "Sample-Value"),
    ("case", "SAMPLE-value"),
    ("white-space-trim", '  Sample-Value' + chr(0x3000) + chr(0x00A0)),
    ("whitespace-disagreement", "Sample-Value\u001f"),
    ("nfd-vs-nfc", 'Cafe' + chr(0x0301)),
    ("nfc", 'Caf' + chr(0x00E9)),
    ("compatibility-forms", chr(0xFF33) + chr(0xFF41) + chr(0xFF4D) + chr(0xFF50) + chr(0xFF4C) + chr(0xFF45)),
    ("ligature", chr(0xFB01) + 'le'),
    ("default-ignorable-zwsp", 'Sam' + chr(0x200B) + 'ple'),
    ("default-ignorable-soft-hyphen", 'Sam' + chr(0x00AD) + 'ple'),
    ("default-ignorable-variation-selector", 'Sample' + chr(0xFE0F)),
    ("sharp-s", 'Stra' + chr(0x00DF) + 'e'),
    ("final-sigma", chr(0x039F) + chr(0x0394) + chr(0x039F) + chr(0x03A3)),
    ("dotted-capital-i", chr(0x0130) + 'stanbul'),
    ("non-bmp-compatibility", "\U0001d400bc"),
    ("non-bmp-emoji", "sample\U0001f600"),
    ("unicode-16-addition", chr(0x1C89)),
    ("reserved-characters", "a/b c%d?e#f"),
    ("tuple-lookalike", "2:v13:x"),
    ("long", "x" * 256),
]
KEY_NEGATIVES = [
    ("empty", "", "EmptyKeyComponent"),
    ("white-space-only", ' ' + chr(0x3000) + chr(0x00A0), "EmptyKeyComponent"),
    ("unassigned", 'sample' + chr(0x0378), "UnassignedCodePoint"),
]
# Default-ignorable code points only. NFKC_Casefold removes them, so the
# casefold pipeline refuses this as empty, while NFKC keeps them and the
# uppercase and lowercase pipelines mint from them (specification §4).
DEFAULT_IGNORABLE_ONLY = chr(0x200B) + chr(0x00AD)
SCOPES = ["acme", 'tenant-' + chr(0x00DF)]
RANDOM_HEX = ["00112233445566778899aabbccddeeff", "ffffffffffffffffffffffffffffffff", "0f1e2d3c4b5a69788796a5b4c3d2e1f0"]
POSITIONS = [(0, 0), (3, 42), (1, 10**18), (MAX_POSITION, MAX_POSITION)]
NQUADS = [
    '<urn:order:1> <https://example.org/ns#status> "paid" <urn:g:orders/1> .\n',
    '<urn:order:1> <https://example.org/ns#note> "café \U0001f600" .\n'
    '<urn:order:1> <https://example.org/ns#status> "paid" .\n',
]


def test_secret(key_id: str) -> bytes:
    """The published test secret for a key id. Never use in production."""
    return hashlib.sha256(("lattice-minting-test-secret/" + key_id).encode("utf-8")).digest()


class _Doc:
    def __init__(self, recipe: Recipe, secrets: Mapping[str, bytes]):
        self.recipe = recipe
        self.secrets = dict(secrets)
        self.positive: list[dict] = []
        self.negative: list[dict] = []
        self.format: list[dict] = []

    def ok(self, vid: str, category: str, inputs: dict) -> None:
        minted = Minter(self.recipe, self.secrets).mint(inputs)
        vec = {"id": vid, "category": category, "inputs": inputs, "trace": minted.trace, "iri": minted.iri}
        if self.recipe.strategy == "SurrogateClaimedIdentity":
            vec["claimIris"] = minted.claim_iris
        self.positive.append(vec)

    def refused(self, vid: str, category: str, inputs: dict, error: str) -> None:
        call_inputs = dict(inputs)
        omit = call_inputs.pop("omitSecret", None)
        secrets = {k: v for k, v in self.secrets.items() if k != omit}
        try:
            Minter(self.recipe, secrets).mint(call_inputs)
        except MintError as e:
            if e.kind != error:
                raise AssertionError(f"{vid}: expected {error}, reference raised {e.kind}") from e
            self.negative.append({"id": vid, "category": category, "inputs": inputs, "error": error})
            return
        raise AssertionError(f"{vid}: expected {error}, reference minted")


def _key_vectors(doc: _Doc, key: Mapping, extra: dict) -> None:
    n = len(key["properties"])
    scoped = bool(key.get("scopeProperty"))
    rest = [f"part-{i}" for i in range(1, n)]
    base = dict(extra)
    for i, (category, value) in enumerate(KEY_CORPUS):
        inputs = {**base, "key": [value, *rest]}
        if scoped:
            inputs["scope"] = SCOPES[i % len(SCOPES)]
        doc.ok(f"key-{i:02d}-{category}", category, inputs)
    invisible = {**base, "key": [DEFAULT_IGNORABLE_ONLY, *rest]}
    if scoped:
        invisible["scope"] = SCOPES[0]
    if "nfkc_casefold" in key["pipeline"]["steps"]:
        doc.refused("neg-default-ignorable-only", "default-ignorable-only", invisible, "EmptyKeyComponent")
    else:
        doc.ok("key-default-ignorable-only-survives", "default-ignorable-only-survives-nfkc", invisible)
    for category, value, error in KEY_NEGATIVES:
        inputs = {**base, "key": [value, *rest]}
        if scoped:
            inputs["scope"] = SCOPES[0]
        doc.refused(f"neg-{category}", category, inputs, error)
    short = {**base, "key": ["Sample-Value"] * (n - 1)}
    if scoped:
        short["scope"] = SCOPES[0]
    doc.refused("neg-missing-component", "missing", short, "MissingKeyComponent")
    if scoped:
        doc.refused("neg-missing-scope", "missing", {**base, "key": ["Sample-Value", *rest]}, "MissingKeyComponent")


def generate(recipe: Recipe | Mapping, description: str | None = None) -> dict:
    """Generate a conformance vectors document for one recipe."""
    if not isinstance(recipe, Recipe):
        recipe = Recipe.parse(recipe)
    r = recipe.data
    s = recipe.strategy
    key_ids = [c["keyId"] for c in r.get("claims", [])]
    secrets = {k: test_secret(k) for k in key_ids}
    doc = _Doc(recipe, secrets)

    if s in ("NaturalKeyIdentity", "DerivedHashIdentity"):
        _key_vectors(doc, r["key"], {})
    elif s == "SurrogateClaimedIdentity":
        if r["surrogate"]["kind"] == "CallerSuppliedSurrogate":
            extra = {"surrogate": "8f2c1b7e-3e4a-4f7c-9a6d-2b1e0c5d7f90"}
        else:
            extra = {"randomHex": RANDOM_HEX[0]}
        _key_vectors(doc, r["claims"][0]["key"], extra)
        base = {**extra, "key": ["Sample-Value"] * len(r["claims"][0]["key"]["properties"])}
        if r["claims"][0]["key"].get("scopeProperty"):
            base["scope"] = SCOPES[0]
        for key_id in key_ids:
            doc.refused(f"neg-missing-secret-{key_id}", "secret", {**base, "omitSecret": key_id}, "MissingSecret")
        if r["surrogate"]["kind"] == "CallerSuppliedSurrogate":
            doc.refused("neg-surrogate-pattern", "pattern", {**base, "surrogate": "not-a-surrogate"}, "PatternMismatch")
    elif s == "RandomSurrogateIdentity":
        for i, h in enumerate(RANDOM_HEX):
            doc.ok(f"random-{i}", "supplied-randomness", {"randomHex": h})
    elif s == "PositionDerivedEvent":
        hashed = r["namespace"]["derivation"] == "HashedTargetDerivation"
        where = {"target": "urn:g:orders/1"} if hashed else {"namespaceToken": "orders-1"}
        for i, (epoch, seq) in enumerate(POSITIONS):
            doc.ok(f"position-{i}", "position", {**where, "epoch": epoch, "seq": seq})
        if hashed:
            doc.ok("position-other-target", "position", {"target": "urn:g:orders/2", "epoch": 3, "seq": 42})
            doc.ok("position-non-ascii-target", "position", {"target": 'urn:g:commandes/' + chr(0x00E9) + 't' + chr(0x00E9), "epoch": 3, "seq": 42})
        else:
            doc.refused("neg-bad-token", "pattern", {"namespaceToken": "orders 1", "epoch": 3, "seq": 42}, "PatternMismatch")
        doc.refused("neg-negative-seq", "range", {**where, "epoch": 3, "seq": -1}, "PositionOutOfRange")
        doc.refused("neg-seq-too-large", "range", {**where, "epoch": 3, "seq": MAX_POSITION + 1}, "PositionOutOfRange")
        doc.refused("neg-negative-epoch", "range", {**where, "epoch": -1, "seq": 1}, "PositionOutOfRange")
    elif s == "ContentAddressedIdentity":
        for i, nq in enumerate(NQUADS):
            doc.ok(f"content-{i}", "already-canonical", {"canonicalNQuads": nq, "canonicalizer": "declared by the vector generator"})
        doc.refused("neg-no-canonicalizer", "caller-obligation", {"canonicalNQuads": NQUADS[0]}, "CanonicalizerNotDeclared")
    elif s in ("AdoptedIdentity", "ExternalRegistryIdentity"):
        doc.refused("neg-empty", "pattern", {"iri": ""}, "PatternMismatch")
        doc.refused("neg-missing", "pattern", {}, "PatternMismatch")

    if s in ("RandomSurrogateIdentity",) or (s == "SurrogateClaimedIdentity" and r["surrogate"]["kind"] == "UuidV4Surrogate"):
        prefix, _, suffix = r["iriTemplate"].partition("{surrogate}")
        uuid = "[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}"
        doc.format.append({"id": "surrogate-format", "pattern": "^" + re.escape(prefix) + uuid + re.escape(suffix) + "$",
                           "accept": [prefix + "2b6f9e34-9a41-4d7a-8b2e-3f6c1a9d7e40" + suffix],
                           "reject": [prefix + "2B6F9E34-9A41-4D7A-8B2E-3F6C1A9D7E40" + suffix,
                                      prefix + "2b6f9e34-9a41-7d7a-8b2e-3f6c1a9d7e40" + suffix]})

    return {
        "vectorsFormat": VECTORS_FORMAT,
        "description": description or f"Generated by lattice_minting for {r['role']} of {r['target']['class']} ({s}).",
        "recipe": dict(r),
        "testSecrets": {k: {"hex": v.hex(), "note": "Published test secret, derived from the key id. Never use in production."} for k, v in secrets.items()},
        "positive": doc.positive,
        "negative": doc.negative,
        "format": doc.format,
    }
