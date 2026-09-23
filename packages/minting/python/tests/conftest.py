# SPDX-License-Identifier: MPL-2.0
from __future__ import annotations

import json
from pathlib import Path

import pytest

MINTING = Path(__file__).resolve().parents[2]
REPO = MINTING.parents[1]
ANCHORS = REPO / "contracts" / "identity" / "anchor-vectors.json"
TESTDATA = MINTING / "testdata"
VECTOR_FILES = sorted(TESTDATA.glob("*.vectors.json"))
RECIPE_FILES = sorted(TESTDATA.glob("*.recipe.json"))


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def anchors() -> dict:
    return load(ANCHORS)
