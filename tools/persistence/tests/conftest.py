# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

from __future__ import annotations

import os
from pathlib import Path

import pytest
from rdflib import Graph

REPO_ROOT = Path(__file__).resolve().parents[3]
ONTOLOGY_DIR = REPO_ROOT / "ontology" / "persistence"
SPEC_TTL = ONTOLOGY_DIR / "spec" / "persistence.ttl"
SHAPES_TTL = ONTOLOGY_DIR / "shapes" / "constraints.ttl"
EXAMPLES_DIR = ONTOLOGY_DIR / "examples"

PER_WORKER = 700 * 1024 ** 2
"""One worker's peak resident memory, measured at 649 MB for the whole suite in one process (FMH-TS-1)."""


def pytest_xdist_auto_num_workers(config):
    """What ``-n auto`` means for this suite. ``PYTEST_XDIST_AUTO_NUM_WORKERS`` decides when it is set. Otherwise mem_check gives as many
    workers as fit in the memory available, up to the machine's count and never fewer than two (ADR-A125)."""
    if os.environ.get("PYTEST_XDIST_AUTO_NUM_WORKERS"):
        return None
    try:
        import mem_check
    except ImportError:
        return None
    return mem_check.workers(os.cpu_count() or 1, PER_WORKER)


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
    config.addinivalue_line("markers", "oxigraph: runs on Oxigraph, the default engine (needs tools/testing/oxigraph, mise run bootstrap:testing-oxigraph)")
    config.addinivalue_line("markers", "rdflib: runs on rdflib, which PERSISTENCE_ENGINES must name (check:persistence-conformance does)")
    config.addinivalue_line("markers", "conformance: its subject is one engine's behaviour, not the generated SPARQL. check:persistence leaves it out and check:persistence-conformance runs it")
    if os.environ.get("PERSISTENCE_ENGINES_REQUIRED"):
        _require_engines_and_mem_check()


_PACKAGES = {"oxigraph": ("lattice_testing_oxigraph", "bootstrap:testing-oxigraph")}


def _require_engines_and_mem_check() -> None:
    """The check tasks set ``PERSISTENCE_ENGINES_REQUIRED``, so an engine they name, or mem_check, that is not installed stops the run
    instead of its cases being skipped. A run by hand still skips them. The tasks install nothing themselves, ``mise run bootstrap`` does."""
    import importlib.util

    import engines

    names = [p.values[0] if hasattr(p, "values") else p for p in engines.ENGINES]
    missing = [_PACKAGES[n] for n in names if n in _PACKAGES and importlib.util.find_spec(_PACKAGES[n][0]) is None]
    if importlib.util.find_spec("mem_check") is None:
        missing.append(("mem_check", "bootstrap:testing-mem-check"))
    if missing:
        raise pytest.UsageError("not installed: " + ", ".join(m for m, _ in missing) + ". Run mise run bootstrap, or "
                                + ", ".join(f"mise run {t}" for _, t in missing))


@pytest.fixture(params=__import__("engines").ENGINES)
def engine(request):
    """The engine a test that opts in with ``engines.each_engine`` runs on, one of the names ``PERSISTENCE_ENGINES`` gives (Oxigraph when
    it is unset). Oxigraph cases skip where it is absent in a run by hand. The check tasks stop instead (``_require_engines_and_mem_check``)."""
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


@pytest.fixture(autouse=True)
def _rdflib_only_runs_on_rdflib(request):
    """A test marked ``rdflib`` that has no ``engine`` parameter is pinned to rdflib (``engines.rdflib_only``), whatever ``PERSISTENCE_ENGINES`` says."""
    import engines

    if request.node.get_closest_marker("rdflib") is None or "engine" in request.fixturenames:
        yield
        return
    previous, engines.CURRENT = engines.CURRENT, "rdflib"
    yield
    engines.CURRENT = previous
