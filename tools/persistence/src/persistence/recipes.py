# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""Minting recipes (identity-minting M1).

Builds one self-contained recipe per resolved identity role
(``identity:<Role>``, persistence-compiler-iri-sync Slice 3), in the format
defined by ``docs/architecture/identity-minting-specification.md`` and
``contracts/identity/recipe.schema.json``. A recipe carries everything a
minter needs and nothing about the configuration graph it came from
(identity-minting decision C). Building a recipe is also its validation:
any member a self-contained recipe would lack is a named
:class:`~persistence.model.CrossAxisViolation`, never a silent default.

The recipe digest is SHA-256 over RFC 8785 canonical JSON. Recipes contain
only strings, integers, booleans, null, arrays and objects with ASCII keys
(plan decision P5), for which RFC 8785 reduces to sorted keys, no
whitespace, and JSON's standard string escapes.
"""

from __future__ import annotations

import hashlib
import json
import re

from rdflib import Graph, URIRef

from .model import CrossAxisViolation, ResolvedDimension
from .namespaces import DAL
from .scopes import Target

RECIPE_FORMAT = "lattice-minting-recipe/1"
TUPLE_ENCODING = "length-prefixed-utf8/1"
UNICODE_VERSION = "16.0.0"

PIPELINE_STEPS = {
    "NfkcTrimCasefold": ["reject_unassigned", "nfkc_casefold", "trim_white_space"],
    "NfkcTrimUppercase": ["reject_unassigned", "nfkc", "trim_white_space", "uppercase_full", "nfkc"],
    "NfkcTrimLowercase": ["reject_unassigned", "nfkc", "trim_white_space", "lowercase_full", "nfkc"],
}
DIGEST_ENCODINGS = ("lowercase-hex", "base32", "base64url")

# The caller's obligations for content-addressed identity, carried in every
# such recipe (identity-minting sketch §6a, specification §7). The same text
# appears in contracts/identity/anchor-vectors.json.
CALLER_OBLIGATIONS = [
    {"id": "CA-1", "text": "The bytes are the output of an RDFC-1.0 implementation that passes the W3C RDFC-1.0 test suite, serialized as canonical N-Quads in UTF-8, one line per quad, each terminated by a single LF, with no other bytes."},
    {"id": "CA-2", "text": "The recipe's self-reference rule is applied before canonicalization."},
    {"id": "CA-3", "text": "Canonicalization stops at the recipe's work budget and the graph is refused, never hashed on a best-effort basis."},
    {"id": "CA-4", "text": "Where verifyFullDigest is true, the full digest is stored and compared on every re-registration of the identifier."},
]
SELF_REFERENCE = {
    "SelfReferenceDisallowed": "disallowed",
    "ExcludeHeaderSubgraph": "exclude-header-subgraph",
    "PlaceholderSubstitution": "placeholder-substitution",
}
MINTING_SCHEME_STATES = ("Accepting", "Dual")

# Slots each strategy's template must contain, and may contain.
TEMPLATE_SLOTS = {
    "NaturalKeyIdentity": ({"key"}, {"key"}),
    "DerivedHashIdentity": ({"digest"}, {"digest"}),
    "SurrogateClaimedIdentity": ({"surrogate"}, {"surrogate"}),
    "RandomSurrogateIdentity": ({"surrogate"}, {"surrogate"}),
    "ContentAddressedIdentity": ({"digest"}, {"digest"}),
    "PositionDerivedEvent": ({"namespace", "epoch", "seq"}, {"namespace", "epoch", "seq"}),
}
CLAIM_TEMPLATE_SLOTS = ({"mac"}, {"mac", "constraintId", "schemeVersion"})
SLOT = re.compile(r"\{([A-Za-z]+)\}")


def canonical_json(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def seal(recipe: dict) -> dict:
    body = {k: v for k, v in recipe.items() if k != "recipeDigest"}
    body["recipeDigest"] = "sha256:" + hashlib.sha256(canonical_json(body)).hexdigest()
    return body


def _local(value) -> str | None:
    return str(value).rsplit("#", 1)[-1] if value is not None else None


class _Builder:
    def __init__(self, graph: Graph, target: Target, uniqueness: list[dict]):
        self.g = graph
        self.target = target
        self.applicable = {c["constraint"] for c in uniqueness}

    def fail(self, kind: str, where: str, message: str):
        raise CrossAxisViolation(kind, str(self.target), f"{where}: {message}")

    def template(self, where: str, template, slots: tuple[set, set]) -> str:
        if template is None:
            self.fail("MintedIriTemplateRequired", where, "an identity strategy that mints needs dal:mintedIriTemplate")
        text = str(template)
        present = set(SLOT.findall(text))
        required, allowed = slots
        if not required <= present or not present <= allowed:
            self.fail("MintedIriTemplateInvalid", where,
                      f"template {text!r} must contain {sorted(required)} and may contain only {sorted(allowed)}")
        return text

    def digest(self, where: str, scheme, function: str) -> dict:
        if scheme is None:
            self.fail("DigestSchemeRequired", where, "a dal:DigestScheme is required")
        fn = self.g.value(scheme, DAL.digestFunction)
        width = self.g.value(scheme, DAL.digestWidthBits)
        encoding = self.g.value(scheme, DAL.digestEncoding)
        if fn is None or width is None or encoding is None:
            self.fail("DigestSchemeRequired", where, "the digest scheme needs a function, width and encoding")
        if str(fn) != function:
            self.fail("DigestFunctionUnsupported", where, f"digest function must be {function}, got {fn}")
        w = int(width)
        if w <= 0 or w % 8 or w > 256 or str(encoding) not in DIGEST_ENCODINGS:
            self.fail("DigestSchemeMalformed", where, f"width {w} or encoding {encoding} is not valid")
        return {"function": function, "widthBits": w, "encoding": str(encoding)}

    def key(self, where: str, constraint) -> dict:
        pipeline = self.g.value(constraint, DAL.normalizePipeline)
        pid = _local(pipeline)
        if pid not in PIPELINE_STEPS:
            self.fail("NormalizePipelineRequired", where,
                      f"constraint {constraint} needs one of {sorted(PIPELINE_STEPS)} as dal:normalizePipeline")
        version = self.g.value(pipeline, DAL.unicodeVersion)
        if str(version) != UNICODE_VERSION:
            self.fail("UnsupportedUnicodeVersion", where, f"pipeline {pid} declares Unicode {version}, recipes support {UNICODE_VERSION}")
        head = self.g.value(constraint, DAL.keyProperty)
        props = [str(p) for p in self.g.items(head)] if head is not None else []
        if not props:
            self.fail("KeyPropertiesRequired", where, f"constraint {constraint} declares no dal:keyProperty")
        scope = self.g.value(constraint, DAL.scopeProperty)
        return {"properties": props, "scopeProperty": str(scope) if scope is not None else None,
                "pipeline": {"id": pid, "unicodeVersion": UNICODE_VERSION, "steps": list(PIPELINE_STEPS[pid])}}

    def constraint(self, where: str, prop: URIRef, constraint, missing_kind: str) -> URIRef:
        if constraint is None:
            self.fail(missing_kind, where, f"dal:{_local(prop)} is required")
        if str(constraint) not in self.applicable:
            self.fail("KeyConstraintNotApplicable", where,
                      f"{constraint} does not apply to this target, so the key it names is not the entity's key")
        return constraint

    def claims(self, where: str, constraint) -> list[dict]:
        cid = self.g.value(constraint, DAL.constraintId)
        key = self.key(where, constraint)
        out = []
        for scheme in self.g.objects(constraint, DAL.claimScheme):
            state = _local(self.g.value(scheme, DAL.schemeState))
            if state not in MINTING_SCHEME_STATES:
                continue
            at = f"{where}, claim scheme {scheme}"
            version = self.g.value(scheme, DAL.schemeVersion)
            key_id = self.g.value(scheme, DAL.claimKeyId)
            if version is None or key_id is None or cid is None:
                self.fail("ClaimSchemeIncomplete", at, "needs dal:schemeVersion, dal:claimKeyId and the constraint's dal:constraintId")
            out.append({
                "constraintId": str(cid), "schemeVersion": str(version), "schemeState": state,
                "keyId": str(key_id), "key": key, "tupleEncoding": TUPLE_ENCODING,
                "mac": self.digest(at, self.g.value(scheme, DAL.claimDigestScheme), "HMAC-SHA-256"),
                "iriTemplate": self.template(at, self.g.value(scheme, DAL.claimIriTemplate), CLAIM_TEMPLATE_SLOTS),
            })
        if not 1 <= len(out) <= 2:
            self.fail("ClaimSchemeIncomplete", where,
                      f"constraint {constraint} needs one claim scheme in state Accepting, or two in state Dual; found {len(out)}")
        return sorted(out, key=lambda c: c["schemeVersion"])

    def build(self, name: str, rd: ResolvedDimension) -> dict:
        profile = URIRef(rd.won_by)
        g = self.g
        where = f"{name} (won by {rd.won_by})"
        role = name.split(":", 1)[1]
        strategy = _local(rd.value)
        if _local(g.value(profile, DAL.eventIdentityStrategy)) == "PositionDerivedEvent":
            strategy = "PositionDerivedEvent"
        recipe: dict = {
            "recipeFormat": RECIPE_FORMAT, "role": role,
            "target": {"class": str(self.target.cls),
                       "deployment": str(self.target.deployment) if self.target.deployment is not None else None},
            "strategy": strategy,
        }
        template = g.value(profile, DAL.mintedIriTemplate)
        if strategy in ("AdoptedIdentity", "ExternalRegistryIdentity"):
            pattern = g.value(profile, DAL.acceptedIriPattern)
            authority = g.value(profile, DAL.namingAuthority)
            if pattern is None or authority is None:
                self.fail("AcceptedPatternRequired", where, "needs dal:acceptedIriPattern and dal:namingAuthority")
            recipe.update(namingAuthority=str(authority), acceptedPattern=str(pattern))
            return seal(recipe)
        if strategy not in TEMPLATE_SLOTS:
            self.fail("IdentityStrategyUnsupported", where, f"no recipe format for {strategy}")
        recipe["iriTemplate"] = self.template(where, template, TEMPLATE_SLOTS[strategy])
        if strategy in ("NaturalKeyIdentity", "DerivedHashIdentity"):
            constraint = self.constraint(where, DAL.keyConstraint, g.value(profile, DAL.keyConstraint), "KeyConstraintRequired")
            recipe["key"] = self.key(where, constraint)
            if strategy == "DerivedHashIdentity":
                head = g.value(profile, DAL.tuplePrefix)
                prefix = [str(p) for p in g.items(head)] if head is not None else []
                if not prefix:
                    self.fail("TuplePrefixRequired", where, "dal:DerivedHashIdentity needs a non-empty dal:tuplePrefix")
                recipe.update(tuplePrefix=prefix, tupleEncoding=TUPLE_ENCODING,
                              digest=self.digest(where, g.value(profile, DAL.digestScheme), "SHA-256"))
        elif strategy == "SurrogateClaimedIdentity":
            kind = _local(g.value(profile, DAL.surrogateKind))
            if kind == "UuidV4Surrogate":
                recipe["surrogate"] = {"kind": kind}
            elif kind == "CallerSuppliedSurrogate":
                pattern = g.value(profile, DAL.callerSuppliedPattern)
                if pattern is None:
                    self.fail("CallerSuppliedPatternRequired", where, "dal:CallerSuppliedSurrogate needs dal:callerSuppliedPattern")
                recipe["surrogate"] = {"kind": kind, "pattern": str(pattern)}
            else:
                self.fail("SurrogateKindRequired", where, "dal:SurrogateClaimedIdentity needs dal:surrogateKind")
            constraint = self.constraint(where, DAL.claimsConstraint, g.value(profile, DAL.claimsConstraint), "ClaimedIdentityWithoutKey")
            recipe["claims"] = self.claims(where, constraint)
        elif strategy == "RandomSurrogateIdentity":
            recipe["surrogate"] = {"kind": "UuidV4Surrogate"}
        elif strategy == "PositionDerivedEvent":
            derivation = _local(g.value(profile, DAL.occurrenceNamespaceDerivation))
            if derivation == "HashedTargetDerivation":
                recipe["namespace"] = {"derivation": derivation,
                                       "digest": self.digest(where, g.value(profile, DAL.digestScheme), "SHA-256")}
            else:
                recipe["namespace"] = {"derivation": derivation}
            widths = []
            for prop in (DAL.epochWidth, DAL.sequenceWidth):
                v = g.value(profile, prop)
                if v is None or not 1 <= int(v) <= 19:
                    self.fail("PositionWidthsRequired", where, "dal:epochWidth and dal:sequenceWidth, each from 1 to 19, are required")
                widths.append(int(v))
            recipe.update(epochWidth=widths[0], sequenceWidth=widths[1])
        elif strategy == "ContentAddressedIdentity":
            scheme = g.value(profile, DAL.digestScheme)
            rule = SELF_REFERENCE.get(_local(g.value(profile, DAL.selfReferenceRule)))
            budget = g.value(profile, DAL.canonicalizationWorkBudget)
            if rule is None or budget is None or int(budget) <= 0:
                self.fail("ContentAddressedMembersRequired", where,
                          "needs dal:selfReferenceRule and a positive dal:canonicalizationWorkBudget")
            full = g.value(scheme, DAL.verifyFullDigestOnWrite) if scheme is not None else None
            recipe.update(digest=self.digest(where, scheme, "SHA-256"),
                          canonicalization={"algorithm": "RDFC-1.0", "serialization": "canonical-n-quads-utf8"},
                          selfReference=rule, workBudget=int(budget),
                          verifyFullDigest=bool(full.toPython()) if full is not None else False,
                          callerObligations=CALLER_OBLIGATIONS)
        return seal(recipe)


def export_recipes(compiled: Graph, out_dir, vectors: bool = False) -> list:
    """Write one ``<class>-<role>-<digest prefix>.recipe.json`` per
    ``dal:MintingRecipe`` in a compiled profile. Each document is the
    recipe exactly as the compiled profile holds it (plan decision P1),
    re-checked against its digest before it is written, and pretty-printed
    for reading: the digest is defined over the canonical form, so layout
    does not matter."""
    from pathlib import Path

    from rdflib import RDF

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    written = []
    for node in sorted(compiled.subjects(RDF.type, DAL.MintingRecipe), key=lambda n: str(compiled.value(n, DAL.recipeDigest))):
        recipe = json.loads(str(compiled.value(node, DAL.recipeDocument)))
        if seal(recipe)["recipeDigest"] != recipe["recipeDigest"]:
            raise ValueError(f"recipe {recipe.get('recipeDigest')} does not match its digest")
        cls = recipe["target"]["class"].rstrip("/#").replace("#", "/").rsplit("/", 1)[-1]
        name = f"{cls}-{recipe['role']}-{recipe['recipeDigest'][7:19]}.recipe.json"
        path = out / name
        path.write_text(json.dumps(recipe, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        written.append(path)
        if vectors:
            # identity-minting M2: the Python minting library is the reference
            # implementation vectors are generated from (a design-time use).
            try:
                from lattice_minting.vectors import generate
            except ImportError as e:  # pragma: no cover - environment problem
                raise RuntimeError("vector generation needs packages/minting/python installed "
                                   "(mise run bootstrap:minting-python)") from e
            vpath = out / name.replace(".recipe.json", ".vectors.json")
            vpath.write_text(json.dumps(generate(recipe), indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
            written.append(vpath)
    return written


def build_recipes(graph: Graph, target: Target, identity: dict[str, ResolvedDimension], uniqueness: list[dict]) -> list[dict]:
    """One sealed recipe per resolved identity role, in role order."""
    builder = _Builder(graph, target, uniqueness)
    return [builder.build(name, rd) for name, rd in identity.items()]


__all__ = ["build_recipes", "export_recipes", "canonical_json", "seal", "CALLER_OBLIGATIONS", "RECIPE_FORMAT"]
