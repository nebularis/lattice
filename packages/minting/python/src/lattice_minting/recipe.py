# SPDX-License-Identifier: MPL-2.0
"""Recipe loading and verification (identity-minting-specification.md §2)."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass

from . import ucd
from .canonical import canonical_json
from .errors import MintError

RECIPE_FORMAT = "lattice-minting-recipe/1"
STRATEGIES = frozenset({
    "NaturalKeyIdentity", "DerivedHashIdentity", "SurrogateClaimedIdentity", "RandomSurrogateIdentity",
    "PositionDerivedEvent", "ContentAddressedIdentity", "AdoptedIdentity", "ExternalRegistryIdentity",
})


def _check_pipeline(p: Mapping) -> None:
    if p.get("unicodeVersion") != ucd.VERSION:
        raise MintError("UnsupportedRecipeFormat", f"pipeline Unicode {p.get('unicodeVersion')}, this library supports {ucd.VERSION}")
    steps = p.get("steps") or []
    if not steps or steps[0] != "reject_unassigned" or any(s not in ucd.STEPS for s in steps):
        raise MintError("UnsupportedRecipeFormat", f"pipeline steps {steps} are not a supported sequence")


@dataclass(frozen=True)
class Recipe:
    """A verified recipe. Construct with :meth:`parse`, which checks the
    format, the Unicode version of every pipeline, and the digest."""

    data: Mapping

    @property
    def strategy(self) -> str:
        return self.data["strategy"]

    @property
    def digest(self) -> str:
        return self.data["recipeDigest"]

    @classmethod
    def parse(cls, source: str | bytes | Mapping) -> "Recipe":
        data = json.loads(source) if isinstance(source, (str, bytes)) else dict(source)
        if data.get("recipeFormat") != RECIPE_FORMAT:
            raise MintError("UnsupportedRecipeFormat", f"recipeFormat {data.get('recipeFormat')!r}")
        if data.get("strategy") not in STRATEGIES:
            raise MintError("UnsupportedRecipeFormat", f"strategy {data.get('strategy')!r}")
        body = {k: v for k, v in data.items() if k != "recipeDigest"}
        want = "sha256:" + hashlib.sha256(canonical_json(body)).hexdigest()
        if data.get("recipeDigest") != want:
            raise MintError("RecipeDigestMismatch", f"recipe says {data.get('recipeDigest')}, content is {want}")
        claims = data.get("claims", [])
        if any(c.get("key") != claims[0].get("key") for c in claims):
            raise MintError("UnsupportedRecipeFormat", "every claim must carry the same key, which is normalized once")
        for pipeline in ([data["key"]["pipeline"]] if "key" in data else []) + [c["key"]["pipeline"] for c in data.get("claims", [])]:
            _check_pipeline(pipeline)
        return cls(data)
