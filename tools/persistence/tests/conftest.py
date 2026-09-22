# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

from __future__ import annotations

from pathlib import Path

import pytest
from rdflib import Graph

REPO_ROOT = Path(__file__).resolve().parents[3]
ONTOLOGY_DIR = REPO_ROOT / "ontology" / "persistence"
SPEC_TTL = ONTOLOGY_DIR / "spec" / "persistence.ttl"
SHAPES_TTL = ONTOLOGY_DIR / "shapes" / "constraints.ttl"
EXAMPLES_DIR = ONTOLOGY_DIR / "examples"


@pytest.fixture(scope="session")
def spec_graph() -> Graph:
    g = Graph()
    g.parse(SPEC_TTL, format="turtle")
    return g


def load_example(name: str) -> Graph:
    g = Graph()
    g.parse(SPEC_TTL, format="turtle")
    g.parse(EXAMPLES_DIR / name, format="turtle")
    return g


@pytest.fixture
def example():
    return load_example
