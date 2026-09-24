# SPDX-License-Identifier: MPL-2.0

from __future__ import annotations

from pathlib import Path

import pytest
from rdflib import Graph

REPO_ROOT = Path(__file__).resolve().parents[3]
ONTOLOGY_DIR = REPO_ROOT / "ontology" / "vocabulary"
STRUCTURAL_TTL = ONTOLOGY_DIR / "shapes" / "structural.ttl"
CONSTRAINTS_TTL = ONTOLOGY_DIR / "shapes" / "constraints.ttl"
EXAMPLES_DIR = ONTOLOGY_DIR / "examples"


def load_example(*names: str) -> Graph:
    g = Graph()
    for name in names:
        g.parse(EXAMPLES_DIR / name, format="turtle")
    return g


@pytest.fixture
def example():
    return load_example


@pytest.fixture(scope="session")
def shapes_graph() -> Graph:
    g = Graph()
    g.parse(STRUCTURAL_TTL, format="turtle")
    g.parse(CONSTRAINTS_TTL, format="turtle")
    return g
