# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""Namespaces and builders the tests share."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from rdflib import Graph, Namespace, URIRef

WRD = Namespace("https://www.nebularis.org/neuro-semantic/lattice/wording#")
FACILITY = Namespace("https://example.org/lattice/wording/facility-form/")
LICENCE = Namespace("https://example.org/lattice/wording/software-licence/")
AT = datetime(2026, 10, 28, 9, 0, tzinfo=timezone.utc)
FIXTURES = Path(__file__).parent / "fixtures"
PREFIXES = """
@prefix wrd: <https://www.nebularis.org/neuro-semantic/lattice/wording#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
@prefix f: <https://example.org/lattice/wording/facility-form/> .
@prefix l: <https://example.org/lattice/wording/software-licence/> .
"""


def counting_mint():
    """A minter whose identifiers depend only on how many it has given of each kind."""
    seen: dict = {}

    def mint(kind: str) -> URIRef:
        seen[kind] = seen.get(kind, 0) + 1
        return URIRef(f"urn:test:{kind}:{seen[kind]}")

    return mint


def settings(turtle: str) -> Graph:
    return Graph().parse(data=PREFIXES + turtle, format="turtle")
