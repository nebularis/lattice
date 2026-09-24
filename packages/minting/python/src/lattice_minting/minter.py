# SPDX-License-Identifier: MPL-2.0
"""Minting from a recipe (identity-minting-specification.md §6).

Every result carries a trace of every intermediate value, in the same shape
as the conformance vectors (§10.1), so a mismatch can be located at the
first step that differs."""

from __future__ import annotations

import re
import secrets as _secrets
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field

from . import ucd
from .canonical import encode, hmac_sha256, percent_encode, sha256, tuple_bytes, uuid4_from
from .errors import MintError
from .recipe import Recipe

MAX_POSITION = 9223372036854775807
TOKEN = re.compile(r"[A-Za-z0-9._~-]+")
SLOT = re.compile(r"\{([A-Za-z]+)\}")


def render(template: str, slots: Mapping[str, str]) -> str:
    return SLOT.sub(lambda m: slots[m.group(1)], template)


@dataclass
class Minted:
    iri: str
    claim_iris: list[str] = field(default_factory=list)
    trace: list[dict] = field(default_factory=list)
    canonicalizer: str | None = None


class Minter:
    """Mints IRIs from one verified recipe.

    ``secrets`` maps a claim scheme's key id to the secret's bytes, and is
    needed only for claimed identity. The minter does not retain it beyond
    the calls that use it. ``random_bytes`` returns n cryptographically
    secure random bytes; replace it only in tests.
    """

    def __init__(self, recipe: Recipe, secrets: Mapping[str, bytes] | None = None,
                 random_bytes: Callable[[int], bytes] = _secrets.token_bytes):
        ucd.check_runtime()
        self.recipe = recipe
        self.r = recipe.data
        self._secrets = dict(secrets or {})
        self._random = random_bytes

    # ---- shared steps -------------------------------------------------------------------------------

    def _normalize(self, pipeline: Mapping, raw, index: int, trace: list) -> str:
        if not isinstance(raw, str):
            raise MintError("MissingKeyComponent", f"key component {index} is missing")
        value, after = raw, []
        for step in pipeline["steps"]:
            value = ucd.STEPS[step](value)
            after.append({"step": step, "output": value})
        if value == "":
            raise MintError("EmptyKeyComponent", f"key component {index} is empty after normalization")
        trace.append({"step": "normalize", "component": index, "pipeline": pipeline["id"],
                      "input": raw, "after": after, "output": value})
        return value

    def _key(self, key: Mapping, inputs: Mapping, trace: list) -> tuple[list[str], list[str]]:
        values = list(inputs.get("key") or [])
        if len(values) < len(key["properties"]):
            raise MintError("MissingKeyComponent", f"{len(key['properties'])} key components needed, {len(values)} given")
        scope: list[str] = []
        if key.get("scopeProperty"):
            if not isinstance(inputs.get("scope"), str):
                raise MintError("MissingKeyComponent", "the key's scope value is missing")
            scope = [inputs["scope"]]
        normalized = [self._normalize(key["pipeline"], v, i, trace) for i, v in enumerate(values[: len(key["properties"])])]
        return scope, normalized

    def _digest(self, data: bytes, spec: Mapping, trace: list, mac_key: bytes | None = None,
                key_id: str | None = None, claim: int | None = None) -> str:
        tag = {} if claim is None else {"claim": claim}
        if mac_key is None:
            full = sha256(data)
            trace.append({"step": "digest", **tag, "function": "SHA-256", "hex": full.hex()})
        else:
            full = hmac_sha256(mac_key, data)
            trace.append({"step": "mac", **tag, "function": "HMAC-SHA-256", "keyId": key_id, "hex": full.hex()})
        cut = full[: spec["widthBits"] // 8]
        trace.append({"step": "truncate", **tag, "widthBits": spec["widthBits"], "hex": cut.hex()})
        value = encode(cut, spec["encoding"])
        trace.append({"step": "encode", **tag, "encoding": spec["encoding"], "value": value})
        return value

    def _match(self, pattern: str, value, what: str) -> str:
        if not isinstance(value, str) or re.fullmatch(pattern, value) is None:
            raise MintError("PatternMismatch", f"{what} {value!r} does not match {pattern}")
        return value

    def _uuid(self, inputs: Mapping, trace: list) -> str:
        random_hex = inputs.get("randomHex")
        raw = bytes.fromhex(random_hex) if random_hex is not None else self._random(16)
        value = uuid4_from(raw)
        trace.append({"step": "generate-surrogate", "randomHex": raw.hex(), "value": value})
        return value

    # ---- strategies -----------------------------------------------------------------------------------

    def mint(self, inputs: Mapping) -> Minted:
        """Mint (or, for adopted identity, validate) one identifier.

        ``inputs`` members: ``key`` (list of raw key values), ``scope``,
        ``surrogate`` (caller-supplied surrogates), ``target``, ``epoch``,
        ``seq``, ``namespaceToken`` (position-derived), ``canonicalNQuads``
        and ``canonicalizer`` (content-addressed), ``iri`` (adopted),
        ``randomHex`` (tests only: 16 bytes instead of fresh randomness).
        """
        s = self.r["strategy"]
        trace: list[dict] = []
        if s in ("AdoptedIdentity", "ExternalRegistryIdentity"):
            iri = self._match(self.r["acceptedPattern"], inputs.get("iri"), "identifier")
            trace.append({"step": "validate-iri", "pattern": self.r["acceptedPattern"], "value": iri})
            return Minted(iri, trace=trace)
        if s == "NaturalKeyIdentity":
            scope, normalized = self._key(self.r["key"], inputs, trace)
            parts = [percent_encode(v) for v in scope + normalized]
            trace.append({"step": "percent-encode", "components": parts})
            return self._done(render(self.r["iriTemplate"], {"key": "/".join(parts)}), trace)
        if s == "DerivedHashIdentity":
            scope, normalized = self._key(self.r["key"], inputs, trace)
            components = list(self.r["tuplePrefix"]) + scope + normalized
            data = tuple_bytes(components)
            trace.append({"step": "tuple", "components": components, "hex": data.hex()})
            return self._done(render(self.r["iriTemplate"], {"digest": self._digest(data, self.r["digest"], trace)}), trace)
        if s == "RandomSurrogateIdentity":
            return self._done(render(self.r["iriTemplate"], {"surrogate": self._uuid(inputs, trace)}), trace)
        if s == "SurrogateClaimedIdentity":
            return self._claimed(inputs, trace)
        if s == "PositionDerivedEvent":
            return self._position(inputs, trace)
        if s == "ContentAddressedIdentity":
            return self._content(inputs, trace)
        raise MintError("UnsupportedRecipeFormat", f"strategy {s}")

    def _done(self, iri: str, trace: list, **extra) -> Minted:
        trace.append({"step": "render", "iri": iri})
        return Minted(iri, trace=trace, **extra)

    def _claimed(self, inputs: Mapping, trace: list) -> Minted:
        sur = self.r["surrogate"]
        if sur["kind"] == "CallerSuppliedSurrogate":
            value = self._match(sur["pattern"], inputs.get("surrogate"), "surrogate")
            trace.append({"step": "validate-surrogate", "pattern": sur["pattern"], "value": value})
        else:
            value = self._uuid(inputs, trace)
        iri = render(self.r["iriTemplate"], {"surrogate": value})
        trace.append({"step": "render", "iri": iri})
        claims = self.r["claims"]
        scope, normalized = self._key(claims[0]["key"], inputs, trace)
        claim_iris = []
        for ix, c in enumerate(claims):
            key = self._secrets.get(c["keyId"])
            if not key:
                raise MintError("MissingSecret", f"no secret supplied for key id {c['keyId']!r}")
            components = [c["schemeVersion"], c["constraintId"], scope[0] if scope else "", *normalized]
            data = tuple_bytes(components)
            trace.append({"step": "tuple", "claim": ix, "components": components, "hex": data.hex()})
            mac = self._digest(data, c["mac"], trace, mac_key=key, key_id=c["keyId"], claim=ix)
            claim_iri = render(c["iriTemplate"], {"constraintId": c["constraintId"], "schemeVersion": c["schemeVersion"], "mac": mac})
            trace.append({"step": "render", "claim": ix, "iri": claim_iri})
            claim_iris.append(claim_iri)
        return Minted(iri, claim_iris=claim_iris, trace=trace)

    def _position(self, inputs: Mapping, trace: list) -> Minted:
        ns_spec = self.r["namespace"]
        if ns_spec["derivation"] == "HashedTargetDerivation":
            target = inputs.get("target")
            if not isinstance(target, str) or not target:
                raise MintError("MissingKeyComponent", "the target IRI is missing")
            components = ["occurrence-namespace/1", target]
            data = tuple_bytes(components)
            trace.append({"step": "tuple", "components": components, "hex": data.hex()})
            namespace = self._digest(data, ns_spec["digest"], trace)
        else:
            namespace = inputs.get("namespaceToken")
            if not isinstance(namespace, str) or TOKEN.fullmatch(namespace) is None:
                raise MintError("PatternMismatch", f"namespace token {namespace!r} is not [A-Za-z0-9._~-]+")
            trace.append({"step": "validate-token", "pattern": "^[A-Za-z0-9._~-]+$", "value": namespace})
        padded = []
        for name, width in (("epoch", self.r["epochWidth"]), ("seq", self.r["sequenceWidth"])):
            v = inputs.get(name)
            if isinstance(v, bool) or not isinstance(v, int):
                raise MintError("MissingKeyComponent", f"{name} is missing or not an integer")
            if not 0 <= v <= MAX_POSITION:
                raise MintError("PositionOutOfRange", f"{name} {v} is outside 0..{MAX_POSITION}")
            padded.append(f"{v:0{width}d}")
        trace.append({"step": "pad", "epoch": padded[0], "seq": padded[1]})
        iri = render(self.r["iriTemplate"], {"namespace": namespace, "epoch": padded[0], "seq": padded[1]})
        return self._done(iri, trace)

    def _content(self, inputs: Mapping, trace: list) -> Minted:
        canonicalizer = inputs.get("canonicalizer")
        if not isinstance(canonicalizer, str) or not ucd.trim_white_space(canonicalizer):
            raise MintError("CanonicalizerNotDeclared",
                            "content-addressed minting needs a statement of which RDFC-1.0 implementation produced "
                            "the bytes (identity-minting-specification.md §7, CA-1)")
        nquads = inputs.get("canonicalNQuads")
        if not isinstance(nquads, str):
            raise MintError("MissingKeyComponent", "canonicalNQuads is missing")
        value = self._digest(nquads.encode("utf-8"), self.r["digest"], trace)
        return self._done(render(self.r["iriTemplate"], {"digest": value}), trace, canonicalizer=canonicalizer)
