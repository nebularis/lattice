#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Independent verifier for anchor-vectors.json.

Recomputes every byte of every anchor vector without any LATTICE code:
digests and MACs with the `openssl` command line tool, and JSON, base32,
base64url, hex and percent-encoding with the Python standard library.
It deliberately shares no code with the minting libraries, so an error in a
library cannot be mirrored here.

What it checks, per vector set:
  - the recipe digest (SHA-256 over RFC 8785 canonical JSON, recipeDigest removed)
  - every trace step after normalization: tuple bytes, digest or MAC,
    truncation, output encoding, percent-encoding, padding, surrogate
    pattern, and the rendered IRIs
  - that tuple components are exactly what the recipe prescribes
  - that each negative vector names an error from the specification, and
    that UnassignedCodePoint inputs really contain a code point unassigned
    in Unicode 16.0.0
  - format vectors against their patterns

What it does not check: the normalization steps themselves. Their outputs
cite the UCD 16.0.0 lines that justify them, and the minting libraries test
their pinned tables against the UCD directly.

Usage: python3 verify-anchors.py [anchor-vectors.json] [--openssl PATH]
Exit status 0 when every check passes.
"""

from __future__ import annotations

import base64
import hashlib
import json
import re
import subprocess
import sys
import unicodedata
import urllib.parse
from pathlib import Path

ERRORS = {
    "UnassignedCodePoint", "EmptyKeyComponent", "MissingKeyComponent", "MissingSecret",
    "PatternMismatch", "PositionOutOfRange", "RecipeDigestMismatch", "UnsupportedRecipeFormat",
    "RuntimeUnicodeTooOld", "CanonicalizerNotDeclared",
}


class Openssl:
    def __init__(self, exe: str):
        self.exe = exe

    def _run(self, args: list[str], data: bytes) -> bytes:
        out = subprocess.run([self.exe, *args], input=data, capture_output=True, check=True).stdout
        return bytes.fromhex(out.decode().strip().split()[-1])

    def sha256(self, data: bytes) -> bytes:
        return self._run(["dgst", "-sha256"], data)

    def hmac_sha256(self, key: bytes, data: bytes, key_utf8: str | None) -> bytes:
        try:
            return self._run(["dgst", "-sha256", "-mac", "HMAC", "-macopt", f"hexkey:{key.hex()}"], data)
        except subprocess.CalledProcessError:
            if key_utf8 is None:  # LibreSSL has no -macopt; -hmac needs a text key
                raise
            return self._run(["dgst", "-sha256", "-hmac", key_utf8], data)


def enc(components: list[str]) -> bytes:
    out = bytearray()
    for c in components:
        b = c.encode("utf-8")
        out += str(len(b)).encode("ascii") + b":" + b
    return bytes(out)


def encode(data: bytes, encoding: str) -> str:
    if encoding == "lowercase-hex":
        return data.hex()
    if encoding == "base32":
        return base64.b32encode(data).decode("ascii").rstrip("=")
    if encoding == "base64url":
        return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")
    raise ValueError(encoding)


def jcs(obj) -> bytes:
    # RFC 8785 reduces to this for recipes: ASCII keys, no non-integer numbers.
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def render(template: str, slots: dict[str, str]) -> str:
    return re.sub(r"\{([a-zA-Z]+)\}", lambda m: slots[m.group(1)], template)


class Checker:
    def __init__(self, openssl: Openssl):
        self.ossl = openssl
        self.failures: list[str] = []
        self.passed = 0

    def check(self, where: str, ok: bool, detail: str = "") -> None:
        if ok:
            self.passed += 1
        else:
            self.failures.append(f"{where}: {detail}")

    def recipe_digest(self, where: str, recipe: dict) -> None:
        body = {k: v for k, v in recipe.items() if k != "recipeDigest"}
        want = "sha256:" + self.ossl.sha256(jcs(body)).hex()
        self.check(f"{where} recipeDigest", recipe["recipeDigest"] == want, f"{recipe['recipeDigest']} != {want}")

    def positive(self, where: str, recipe: dict, secrets: dict, vec: dict) -> None:
        strategy = recipe["strategy"]
        normalized: list[str] = []
        prev_bytes = b""
        encoded: dict[int | None, str] = {}
        rendered: dict[int | None, str] = {}
        claims = recipe.get("claims", [])
        for i, step in enumerate(vec["trace"]):
            at = f"{where} {vec['id']} step {i} ({step['step']})"
            kind = step["step"]
            claim_ix = step.get("claim")
            if kind == "normalize":
                self.check(at, step["after"][-1]["output"] == step["output"], "output differs from last step")
                normalized.append(step["output"])
            elif kind == "tuple":
                comps = step["components"]
                if strategy == "DerivedHashIdentity":
                    scope = [vec["inputs"]["scope"]] if recipe["key"]["scopeProperty"] else []
                    want = recipe["tuplePrefix"] + scope + normalized
                elif strategy == "SurrogateClaimedIdentity":
                    c = claims[claim_ix]
                    scope = vec["inputs"].get("scope") or ""
                    want = [c["schemeVersion"], c["constraintId"], scope, *normalized]
                elif strategy == "PositionDerivedEvent":
                    want = ["occurrence-namespace/1", vec["inputs"]["target"]]
                else:
                    want = comps
                self.check(at, comps == want, f"components {comps} != {want}")
                prev_bytes = enc(comps)
                self.check(at, step["hex"] == prev_bytes.hex(), "tuple bytes differ")
            elif kind == "digest":
                data = prev_bytes if strategy != "ContentAddressedIdentity" else vec["inputs"]["canonicalNQuads"].encode("utf-8")
                got = self.ossl.sha256(data)
                self.check(at, step["hex"] == got.hex(), f"{step['hex']} != {got.hex()}")
                prev_bytes = got
            elif kind == "mac":
                c = claims[claim_ix]
                s = secrets[c["keyId"]]
                got = self.ossl.hmac_sha256(bytes.fromhex(s["hex"]), prev_bytes, s.get("utf8"))
                self.check(at, step["hex"] == got.hex(), f"{step['hex']} != {got.hex()}")
                prev_bytes = got
            elif kind == "truncate":
                spec = claims[claim_ix]["mac"] if claim_ix is not None else (
                    recipe["namespace"]["digest"] if strategy == "PositionDerivedEvent" else recipe["digest"])
                self.check(at, step["widthBits"] == spec["widthBits"], "width differs from recipe")
                prev_bytes = prev_bytes[: spec["widthBits"] // 8]
                self.check(at, step["hex"] == prev_bytes.hex(), "truncated bytes differ")
            elif kind == "encode":
                want = encode(prev_bytes, step["encoding"])
                self.check(at, step["value"] == want, f"{step['value']} != {want}")
                encoded[claim_ix] = want
            elif kind == "percent-encode":
                scope = [vec["inputs"]["scope"]] if recipe["key"]["scopeProperty"] else []
                want = [urllib.parse.quote(n.encode("utf-8"), safe="-._~") for n in scope + normalized]
                self.check(at, step["components"] == want, f"{step['components']} != {want}")
                encoded[None] = "/".join(want)
            elif kind == "pad":
                inp = vec["inputs"]
                self.check(at, step["epoch"] == f"{inp['epoch']:0{recipe['epochWidth']}d}", "epoch padding")
                self.check(at, step["seq"] == f"{inp['seq']:0{recipe['sequenceWidth']}d}", "seq padding")
            elif kind == "validate-surrogate":
                self.check(at, re.fullmatch(recipe["surrogate"]["pattern"], step["value"]) is not None, "pattern")
            elif kind == "generate-surrogate":
                b = bytearray(bytes.fromhex(step["randomHex"]))
                b[6] = (b[6] & 0x0F) | 0x40
                b[8] = (b[8] & 0x3F) | 0x80
                h = b.hex()
                want = f"{h[0:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:32]}"
                self.check(at, step["randomHex"] == vec["inputs"]["randomHex"], "randomHex differs from input")
                self.check(at, step["value"] == want, f"{step['value']} != {want}")
                encoded["surrogate"] = want
            elif kind == "validate-iri":
                self.check(at, step["pattern"] == recipe["acceptedPattern"], "pattern differs from recipe")
                self.check(at, re.fullmatch(recipe["acceptedPattern"], step["value"]) is not None, "pattern")
                rendered[None] = step["value"]
            elif kind == "render":
                if claim_ix is not None:
                    c = claims[claim_ix]
                    want = render(c["iriTemplate"], {"constraintId": c["constraintId"],
                                                     "schemeVersion": c["schemeVersion"], "mac": encoded[claim_ix]})
                else:
                    slots = {"digest": encoded.get(None, ""), "key": encoded.get(None, ""),
                             "surrogate": vec["inputs"].get("surrogate", encoded.get("surrogate", ""))}
                    if strategy == "PositionDerivedEvent":
                        slots.update(namespace=encoded[None],
                                     epoch=f"{vec['inputs']['epoch']:0{recipe['epochWidth']}d}",
                                     seq=f"{vec['inputs']['seq']:0{recipe['sequenceWidth']}d}")
                    want = render(recipe["iriTemplate"], slots)
                self.check(at, step["iri"] == want, f"{step['iri']} != {want}")
                rendered[claim_ix] = want
        self.check(f"{where} {vec['id']} iri", vec["iri"] == rendered.get(None), "final IRI")
        if "claimIris" in vec:
            self.check(f"{where} {vec['id']} claimIris",
                       vec["claimIris"] == [rendered[i] for i in range(len(vec["claimIris"]))], "claim IRIs")

    def negative(self, where: str, vec: dict, recipe: dict | None = None) -> None:
        at = f"{where} {vec['id']}"
        self.check(at, vec["error"] in ERRORS, f"unknown error {vec['error']}")
        if vec["error"] == "PatternMismatch" and recipe is not None and "iri" in vec["inputs"]:
            self.check(at, re.fullmatch(recipe["acceptedPattern"], vec["inputs"]["iri"]) is None, "input matches the pattern")
        if vec["error"] == "UnassignedCodePoint" and unicodedata.unidata_version == "16.0.0":
            text = "".join(vec["inputs"].get("key", []))
            self.check(at, any(unicodedata.category(ch) == "Cn" for ch in text), "no unassigned code point in input")

    def format(self, where: str, vec: dict) -> None:
        for s in vec["accept"]:
            self.check(f"{where} {vec['id']} accept", re.fullmatch(vec["pattern"], s) is not None, s)
        for s in vec["reject"]:
            self.check(f"{where} {vec['id']} reject", re.fullmatch(vec["pattern"], s) is None, s)


def main(argv: list[str]) -> int:
    path = Path(__file__).with_name("anchor-vectors.json")
    exe = "openssl"
    args = iter(argv)
    for a in args:
        if a == "--openssl":
            exe = next(args)
        else:
            path = Path(a)
    doc = json.loads(path.read_text(encoding="utf-8"))
    checker = Checker(Openssl(exe))
    for n, s in enumerate(doc["sets"]):
        where = f"set {n} ({s['recipe']['strategy']})"
        checker.recipe_digest(where, s["recipe"])
        for v in s["positive"]:
            checker.positive(where, s["recipe"], s["testSecrets"], v)
        for v in s["negative"]:
            checker.negative(where, v, s["recipe"])
        for v in s["format"]:
            checker.format(where, v)
    for f in checker.failures:
        print("FAIL", f)
    print(f"{checker.passed} checks passed, {len(checker.failures)} failed ({path.name}, Unicode data {unicodedata.unidata_version})")
    return 1 if checker.failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
