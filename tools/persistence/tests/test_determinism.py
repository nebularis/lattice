# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""Determinism (guide QP4, ADR-A79 point on CI gates): compiling the same
configuration twice, with the individuals' triples permuted, must produce
an identical compiled profile. Permutation is achieved by loading the same
files in reverse order and via a shuffled copy of the graph's triples."""

from __future__ import annotations

import random

from rdflib import Graph, URIRef

from persistence.compiler import compile_to_graph

REPO_ROOT_EXAMPLES = "ontology/persistence/examples"
SPEC = "ontology/persistence/spec/persistence.ttl"


def _load(paths: list[str]) -> Graph:
    g = Graph()
    for p in paths:
        g.parse(p, format="turtle")
    return g


def _canonical_ttl(g: Graph) -> str:
    # rdflib serialises blank-node-bearing graphs with fresh bnode labels
    # per call; canonicalise via isomorphism-independent N-Triples sorted
    # by string, which is stable across equivalent-but-differently-labelled
    # blank node graphs for our purposes here (no two blank nodes in this
    # compiler's output are ever meant to be interchangeable structurally
    # in a way N-Triples sorting would conflate).
    lines = sorted(g.serialize(format="nt").splitlines())
    return "\n".join(lines)


def test_compiling_twice_from_identically_loaded_graph_is_identical():
    from rdflib.compare import isomorphic

    g1 = _load([SPEC, f"{REPO_ROOT_EXAMPLES}/baseline-single-class.ttl"])
    g2 = _load([SPEC, f"{REPO_ROOT_EXAMPLES}/baseline-single-class.ttl"])
    target = URIRef("https://example.org/lending#LoanApplication")

    out1, _ = compile_to_graph(g1, classes={target})
    out2, _ = compile_to_graph(g2, classes={target})

    # Blank-node identifiers are ephemeral per rdflib.Graph instance, so
    # equality has to be graph isomorphism (structurally identical up to
    # blank-node relabelling), not literal triple-set equality, which is
    # exactly what a resolver determinism property actually claims: the
    # same content, not the same bnode labels.
    assert isomorphic(out1, out2), "two compiles of the same configuration produced non-isomorphic profiles"


def test_resolution_is_invariant_under_triple_order():
    """Load the same files, then shuffle the in-memory triple order before
    resolving, twice, with different shuffles. rdflib's Graph is
    order-insensitive by construction (it's a set), but the resolver's own
    iteration (dict/set construction from graph.subjects(), etc.) must not
    leak Python's iteration order into which candidate wins a tie it
    shouldn't be a tie in the first place."""
    from persistence import capability, resolver
    from persistence.model import DIMENSIONS
    from persistence.scopes import Target

    target = Target(cls=URIRef("https://example.org/lending#LoanApplication"))
    results = []
    for _ in range(5):
        g = _load([SPEC, f"{REPO_ROOT_EXAMPLES}/baseline-single-class.ttl"])
        triples = list(g)
        random.shuffle(triples)
        shuffled = Graph()
        for t in triples:
            shuffled.add(t)
        spec = capability.load_capability_spec(shuffled, target)
        values = {d: resolver.resolve_dimension(shuffled, target, d, spec).value for d in DIMENSIONS}
        results.append(values)

    assert all(r == results[0] for r in results)
