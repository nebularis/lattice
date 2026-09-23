# SPDX-License-Identifier: MPL-2.0
"""Named minting errors (identity-minting-specification.md §9)."""

from __future__ import annotations

KINDS = frozenset({
    "UnsupportedRecipeFormat", "RecipeDigestMismatch", "RuntimeUnicodeTooOld",
    "MissingKeyComponent", "UnassignedCodePoint", "EmptyKeyComponent", "MissingSecret",
    "PatternMismatch", "PositionOutOfRange", "CanonicalizerNotDeclared",
})


class MintError(Exception):
    """A named refusal. ``kind`` is one of the specification's error names;
    conformance vectors compare on it, never on the message."""

    def __init__(self, kind: str, message: str):
        if kind not in KINDS:
            raise ValueError(f"unknown error kind {kind!r}")
        super().__init__(f"{kind}: {message}")
        self.kind = kind
