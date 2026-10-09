# SPDX-License-Identifier: MPL-2.0

"""Tests for `tools/conftest.py`'s shared graph and validation caches
(python-test-melting, TM1/TM2)."""

from __future__ import annotations

from pathlib import Path

import pytest
from rdflib import Graph, Namespace
from rdflib.namespace import SH

from conftest import GraphCache, ValidationCache

ROOT = Path(__file__).resolve().parents[1]
FOUNDATION_SPEC = ROOT / "ontology" / "foundation" / "spec" / "foundation.ttl"
VOCAB_SPEC = ROOT / "ontology" / "vocabulary" / "spec" / "vocabulary.ttl"
FOUNDATION_SHAPES = ROOT / "ontology" / "foundation" / "shapes" / "constraints.ttl"
EX = Namespace("https://example.org/lattice/test-graph-cache/")


def test_same_arguments_return_the_same_object() -> None:
    cache = GraphCache()
    first = cache(FOUNDATION_SPEC)
    second = cache(FOUNDATION_SPEC)
    assert first is second


def test_different_paths_return_different_graphs() -> None:
    cache = GraphCache()
    assert cache(FOUNDATION_SPEC) is not cache(VOCAB_SPEC)


def test_the_same_sources_in_a_different_order_share_one_object() -> None:
    cache = GraphCache()
    assert cache(FOUNDATION_SPEC, VOCAB_SPEC) is cache(VOCAB_SPEC, FOUNDATION_SPEC)


def test_inline_turtle_sources_are_cached_by_their_text() -> None:
    cache = GraphCache()
    text = "@prefix ex: <https://example.org/> .\nex:a a ex:Thing .\n"
    first = cache(text)
    second = cache(text)
    assert first is second
    assert len(first) == 1


def test_a_mutated_cached_graph_is_detected() -> None:
    cache = GraphCache()
    graph = cache(FOUNDATION_SPEC)
    graph.add((EX.a, EX.b, EX.c))
    mutated = cache.mutated()
    assert len(mutated) == 1
    (before, after), = mutated.values()
    assert after == before + 1


def test_an_unmutated_cache_reports_nothing() -> None:
    cache = GraphCache()
    cache(FOUNDATION_SPEC)
    cache(VOCAB_SPEC)
    assert cache.mutated() == {}


def test_building_a_fresh_graph_from_a_cached_one_does_not_mutate_it() -> None:
    """The pattern every mutation helper in the suite already uses: `cached + data`
    builds a new graph, so adding to the result never touches the cached graph
    itself (rdflib's own `Graph.__add__` semantics, not this cache's)."""
    cache = GraphCache()
    cached = cache(FOUNDATION_SPEC)
    before = len(cached)
    data = Graph()
    data.add((EX.a, EX.b, EX.c))
    combined = cached + data
    combined.add((EX.d, EX.e, EX.f))
    assert len(cached) == before
    assert cache.mutated() == {}


def test_validated_is_a_cache_hit_on_a_repeated_call(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = []
    import conftest as conftest_module

    def fake_validate(data, shacl_graph, **options):
        calls.append((id(data), id(shacl_graph), tuple(sorted(options.items()))))
        return ("ok", "report", "text")

    monkeypatch.setattr(conftest_module, "_pyshacl_validate", fake_validate)
    cache = ValidationCache()
    graph_cache = GraphCache()
    data = graph_cache(FOUNDATION_SPEC)
    shapes = graph_cache(FOUNDATION_SHAPES)
    first = cache(data, shapes, advanced=True, inference="none")
    second = cache(data, shapes, advanced=True, inference="none")
    assert first is second
    assert len(calls) == 1


def test_a_different_shape_set_or_option_is_a_cache_miss(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = []
    import conftest as conftest_module

    def fake_validate(data, shacl_graph, **options):
        calls.append((id(data), id(shacl_graph), tuple(sorted(options.items()))))
        return (True, Graph(), "")

    monkeypatch.setattr(conftest_module, "_pyshacl_validate", fake_validate)
    cache = ValidationCache()
    graph_cache = GraphCache()
    data = graph_cache(FOUNDATION_SPEC)
    shapes_a = graph_cache(FOUNDATION_SHAPES)
    shapes_b = graph_cache(VOCAB_SPEC)  # stands in for "a different shape set"

    cache(data, shapes_a, advanced=True, inference="none")
    cache(data, shapes_a, advanced=True, inference="none")  # same key, no new call
    cache(data, shapes_b, advanced=True, inference="none")  # different shapes, new call
    cache(data, shapes_a, advanced=False, inference="none")  # different option, new call

    assert len(calls) == 3


def test_a_mutated_data_graph_bypasses_the_cache_safely(monkeypatch: pytest.MonkeyPatch) -> None:
    """A test that builds a fresh composite graph per call (as every existing
    mutation helper does) never collides with a cache entry: each fresh object
    has its own id(), so it is always a genuine cache miss, never a stale hit."""
    calls = []
    import conftest as conftest_module

    def fake_validate(data, shacl_graph, **options):
        calls.append(len(data))
        return (True, Graph(), "")

    monkeypatch.setattr(conftest_module, "_pyshacl_validate", fake_validate)
    cache = ValidationCache()
    graph_cache = GraphCache()
    base = graph_cache(FOUNDATION_SPEC)
    shapes = graph_cache(FOUNDATION_SHAPES)

    for i in range(3):
        fresh = Graph() + base
        fresh.add((EX[f"item{i}"], EX.marker, EX.value))
        cache(fresh, shapes, advanced=True, inference="none")

    assert len(calls) == 3  # every fresh graph is its own cache entry, none reused


def test_a_failing_shape_still_reports_through_the_cached_path() -> None:
    cache = ValidationCache()
    graph_cache = GraphCache()
    shapes = graph_cache(
        "@prefix sh: <http://www.w3.org/ns/shacl#> .\n"
        "@prefix ex: <https://example.org/lattice/test-graph-cache/> .\n"
        "ex:ThingShape a sh:NodeShape ; sh:targetClass ex:Thing ;\n"
        "  sh:property [ sh:path ex:requiredProp ; sh:minCount 1 ] .\n"
    )
    bad = graph_cache(
        "@prefix ex: <https://example.org/lattice/test-graph-cache/> .\n"
        "ex:thing a ex:Thing .\n"
    )
    conforms, report, _ = cache(bad, shapes, advanced=True, inference="none")
    assert conforms is False
    assert any(report.subjects(SH.resultSeverity, SH.Violation))
