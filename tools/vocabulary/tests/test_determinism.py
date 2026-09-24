# SPDX-License-Identifier: MPL-2.0
"""Determinism (validation-pack VTB-11): resolving against the same graph
content, loaded via differently ordered serialisations, must produce an
identical outcome. rdflib's Graph is a set, so two Graph instances built
from the same triples in different textual/insertion order are the same
graph; this test additionally re-serialises with N-Triples lines shuffled
before re-parsing, so the resolver itself is exercised against a genuinely
different in-memory triple insertion order, not just a different file.
"""

from __future__ import annotations

import random
from datetime import datetime, timezone

from rdflib import Graph, URIRef

from vocabulary import resolve

EX = "https://example.org/lattice/vocabulary/examples#"


def _permuted_copy(graph: Graph, seed: int) -> Graph:
    lines = graph.serialize(format="nt").splitlines()
    rng = random.Random(seed)
    rng.shuffle(lines)
    permuted = Graph()
    permuted.parse(data="\n".join(lines), format="nt")
    return permuted


def test_resolution_is_invariant_under_triple_order(example):
    g = example("conjunctive-scopes.ttl")
    contract = URIRef(EX + "cnj-contract")
    north = URIRef(EX + "cnj-region-north")
    gold = URIRef(EX + "cnj-tier-gold")
    at = datetime(2026, 3, 1, tzinfo=timezone.utc)

    baseline = resolve(g, contract, context=[north, gold], at=at)

    for seed in (1, 2, 3):
        permuted = _permuted_copy(g, seed)
        result = resolve(permuted, contract, context=[north, gold], at=at)
        assert result.scheme == baseline.scheme
        assert result.winning_binding == baseline.winning_binding
        assert result.used_fallback == baseline.used_fallback
        assert {c.node for c in result.candidates} == {
            c.node for c in baseline.candidates
        }
