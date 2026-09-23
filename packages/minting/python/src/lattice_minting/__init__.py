# SPDX-License-Identifier: MPL-2.0
"""LATTICE identity minting (ADR-A84).

Mints IRIs from a LATTICE minting recipe, exactly as the identity minting
specification defines, using only the Python standard library and tables
pinned to Unicode 16.0.0. Typical use::

    from lattice_minting import Recipe, Minter

    recipe = Recipe.parse(open("Person-EntityRole-….recipe.json").read())
    minter = Minter(recipe, secrets={"example-key-v1": secret_bytes})
    minted = minter.mint({"key": ["Ada@Example.org"], "scope": "acme", "surrogate": "8f2c…"})
    minted.iri, minted.claim_iris, minted.trace

A refusal raises :class:`MintError` with a named ``kind``.
"""

from .conformance import Report, verify
from .errors import MintError
from .minter import Minted, Minter
from .recipe import Recipe

__all__ = ["Recipe", "Minter", "Minted", "MintError", "verify", "Report"]
__version__ = "0.1.0"
