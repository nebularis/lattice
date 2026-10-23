# SPDX-License-Identifier: MPL-2.0
from __future__ import annotations

import json
from pathlib import Path

import pytest
from rdflib import Graph

PACKAGE = Path(__file__).resolve().parents[1]
REPO = PACKAGE.parents[2]
CONTRACTS = REPO / "contracts" / "persistence"
DATA = Path(__file__).resolve().parent / "data"


@pytest.fixture(scope="session")
def vectors() -> dict:
    return json.loads((CONTRACTS / "vectors.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def profiles() -> dict:
    """The compiled profiles in tests/data, by example name."""
    return {p.name.removesuffix(".compiled.ttl"): Graph().parse(p) for p in sorted(DATA.glob("*.compiled.ttl"))}
