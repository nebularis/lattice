# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""An unconditional write needs a named-graph boundary (technical debt TD-02, decided with the H1.4b
gap report). Test IDs are TD02-Tn."""

from __future__ import annotations

import pytest
from rdflib import Graph, URIRef

from persistence import witness
from persistence.compiler import CompileError, compile_targets

from conftest import EXAMPLES_DIR

DAL = "https://www.nebularis.org/neuro-semantic/lattice/persistence#"
EX = "https://example.org/lending#"
CONCURRENCY = URIRef(EX + "OrderStatusConcurrencyProfile")


def _value_based(concurrency: str, ordering: str | None = None) -> Graph:
    graph = witness._load_fixture(EXAMPLES_DIR / "value-based-cas.ttl")
    graph.set((CONCURRENCY, URIRef(DAL + "concurrencyProfile"), URIRef(DAL + concurrency)))
    graph.remove((CONCURRENCY, URIRef(DAL + "valueGuardProperty"), None))
    if ordering is not None:
        graph.add((CONCURRENCY, URIRef(DAL + "orderingGrain"), URIRef(DAL + ordering)))
    return graph


@pytest.mark.parametrize("concurrency", ["ProvidedConcurrency", "LockingConcurrency"])
def test_td02_t1_an_unconditional_write_with_no_boundary_is_refused(concurrency):
    with pytest.raises(CompileError) as error:
        compile_targets(_value_based(concurrency))
    assert error.value.cause.kind == "UnconditionalWriteRequiresNamedGraph"
    assert "NoBoundary" in str(error.value.cause)


def test_td02_t2_the_same_concurrency_with_a_named_graph_boundary_compiles_to_the_write():
    graph = _value_based("ProvidedConcurrency")
    profile = URIRef(EX + "OrderStatusBoundaryProfile")
    graph.set((profile, URIRef(DAL + "strategy"), URIRef(DAL + "NamedGraphBoundary")))
    (compiled,) = compile_targets(graph)
    assert "unconditional-write" in {o.operation for o in compiled.operations}


def test_td02_t3_the_refusal_does_not_apply_where_the_target_is_not_an_unconditional_write():
    """Optimistic concurrency is checked elsewhere, and event grain generates an append, not this write."""
    assert compile_targets(witness._load_fixture(EXAMPLES_DIR / "value-based-cas.ttl"))


def test_td02_t4_the_witness_triggers_exactly_this_refusal():
    observed = witness.observe_compile([witness.WITNESS_DIR / "refusal-UnconditionalWriteRequiresNamedGraph.ttl"])
    assert set(observed) == {witness.Rule(witness.REFUSAL, "UnconditionalWriteRequiresNamedGraph")}
