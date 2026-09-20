"""Thin MTP adapter over the normative MCN codebook."""

from __future__ import annotations

import mcn_codebook as _codebook

code_for = _codebook.code_for
codes_for = _codebook.codes_for
prefixes = _codebook.PREDECLARED_PREFIXES


def expand(curie: str) -> str:
    prefix, local = curie.split(":", 1)
    return prefixes[prefix] + local