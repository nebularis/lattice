# SPDX-License-Identifier: MPL-2.0
"""The resolution algorithm itself. See the package README and
ontology/vocabulary/README.md §4 for the law this implements.
"""

from __future__ import annotations

from datetime import datetime
from typing import Iterable, List, Optional

from rdflib import Graph, URIRef

from .model import (
    Binding,
    BindingConflictError,
    CandidateTrace,
    NoApplicableBindingError,
    Resolution,
)
from .namespaces import FND, VOC


def _read_bindings(graph: Graph, contract: URIRef) -> List[Binding]:
    """Read every voc:SchemeBinding naming `contract`, in a stable order
    (sorted by node IRI) so that downstream logic never depends on
    rdflib's graph iteration order. A binding missing bindsScheme or a
    temporal scope is skipped here — that is a structural defect for
    ontology/vocabulary/shapes/structural.ttl to report, not a reason for
    the resolver to raise a different, less specific error."""
    nodes = sorted(graph.subjects(VOC.forContract, contract), key=str)
    bindings: List[Binding] = []
    for node in nodes:
        scheme = graph.value(node, VOC.bindsScheme)
        if scheme is None:
            continue
        scope_node = graph.value(node, FND.hasTemporalScope)
        if scope_node is None:
            continue
        valid_from_literal = graph.value(scope_node, FND.validFrom)
        if valid_from_literal is None:
            continue
        valid_to_literal = graph.value(scope_node, FND.validTo)
        scopes = frozenset(graph.objects(node, VOC.bindingScope))
        bindings.append(
            Binding(
                node=node,
                contract=contract,
                scheme=scheme,
                scopes=scopes,
                valid_from=valid_from_literal.toPython(),
                valid_to=(
                    valid_to_literal.toPython()
                    if valid_to_literal is not None
                    else None
                ),
            )
        )
    return bindings


def _maximal(applicable: Iterable[Binding]) -> List[Binding]:
    """The bindings not strictly dominated by another applicable binding's
    scope set. A strict superset always dominates a strict subset; two
    equal or two incomparable scope sets dominate neither, so both survive
    here and the caller reports a conflict."""
    candidates = list(applicable)
    return [
        b
        for b in candidates
        if not any(other is not b and b.scopes < other.scopes for other in candidates)
    ]


def resolve(
    graph: Graph,
    contract: URIRef,
    context: Iterable[URIRef] = (),
    at: Optional[datetime] = None,
) -> Resolution:
    """Resolve the voc:ConceptScheme that applies to `contract` given the
    caller's active `context` (a set of voc:BindingScope IRIs) at time `at`.

    Raises `BindingConflictError` when more than one applicable binding
    survives strict-superset precedence, and `NoApplicableBindingError` when
    no binding applies and the contract has no voc:boundScheme fallback.
    Deterministic under any permutation of the input graph's triples: every
    decision below is a set-membership or value comparison over `Binding`
    instances, never an ordering derived from the graph's own iteration.
    """
    if at is None:
        raise ValueError("at (the resolution time) is required")

    context_set = frozenset(context)
    all_bindings = _read_bindings(graph, contract)

    trace: List[CandidateTrace] = []
    applicable: List[Binding] = []
    for binding in all_bindings:
        scope_match = binding.scope_matches(context_set)
        temporal_match = binding.temporal_matches(at)
        is_applicable = scope_match and temporal_match
        trace.append(
            CandidateTrace(
                node=binding.node,
                scopes=binding.scopes,
                scope_match=scope_match,
                temporal_match=temporal_match,
                applicable=is_applicable,
            )
        )
        if is_applicable:
            applicable.append(binding)

    if applicable:
        maximal = _maximal(applicable)
        if len(maximal) == 1:
            winner = maximal[0]
            return Resolution(
                contract=contract,
                scheme=winner.scheme,
                used_fallback=False,
                winning_binding=winner.node,
                candidates=tuple(trace),
            )
        raise BindingConflictError(
            contract, tuple(sorted(maximal, key=lambda b: str(b.node)))
        )

    fallback = graph.value(contract, VOC.boundScheme)
    if fallback is not None:
        return Resolution(
            contract=contract,
            scheme=fallback,
            used_fallback=True,
            winning_binding=None,
            candidates=tuple(trace),
        )

    raise NoApplicableBindingError(contract)
