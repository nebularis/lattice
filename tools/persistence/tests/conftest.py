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


@pytest.fixture(scope="session", autouse=True)
def _sparql_translated_once(sparql_translated_once) -> None:
    """pySHACL parses and translates a constraint query for every focus node, and the tests run one generated read many times. Do both
    once per text (efficient-queries-and-shapes H1). Evaluation is unchanged, so a test of rdflib's behaviour still sees it."""


@pytest.fixture
def example():
    return load_example


# ---- engines (H2.4b, ADR-A125) -------------------------------------------------------------------------------------


def pytest_configure(config):
    config.addinivalue_line("markers", "oxigraph: runs on Oxigraph (needs tools/testing/oxigraph, see check:persistence-oxigraph)")


@pytest.fixture(params=__import__("engines").ENGINES)
def engine(request):
    """The engine a test that opts in with ``engines.each_engine`` runs on. Oxigraph cases skip where it is absent."""
    import engines

    if request.param == "oxigraph":
        pytest.importorskip("lattice_testing_oxigraph", reason="mise run bootstrap:testing-oxigraph")
    previous, engines.CURRENT = engines.CURRENT, request.param
    yield request.param
    engines.CURRENT = previous


@pytest.fixture(params=[True, False], ids=["guards", "no-guards"])
def guard_axis(request):
    """Whether a test that opts in with ``engines.each_engine_and_guards`` runs its updates with the parameter guards on or off."""
    import engines

    previous, engines.GUARDS = engines.GUARDS, request.param
    yield request.param
    engines.GUARDS = previous
