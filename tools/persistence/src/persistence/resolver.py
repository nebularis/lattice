# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""The precedence and resolution algorithm (sketch §3.4).

Runs per target, per dimension, never per whole profile. ``dal:DataAccessProfile``
is decomposed here, not by rewriting the graph: an individual asserting both
``a dal:DataAccessProfile`` and a dimension's property (e.g.
``dal:concurrencyProfile``) is treated as a candidate for that dimension at
the same scope and priority a dedicated ``dal:ConcurrencyProfile`` individual
would be.
"""

from __future__ import annotations

from typing import Optional

from rdflib import RDF, Graph, URIRef

from .capability import CapabilitySpec
from .model import BASELINE_DEFAULTS, Candidate, ProfileAmbiguityError, ResolvedDimension
from .namespaces import DAL
from .scopes import Target, all_scopes, matches

# dimension -> (dedicated profile class, value property, extra properties to carry)
_DIMENSION_SPEC: dict[str, tuple[URIRef, URIRef, tuple[URIRef, ...]]] = {
    "aggregateBoundary": (
        DAL.AggregateBoundaryProfile,
        DAL.strategy,
        (DAL.graphIriTemplate, DAL.boundaryShape, DAL.maxTraversalDepth, DAL.valueGuardProperty),
    ),
    "concurrencyProfile": (
        DAL.ConcurrencyProfile,
        DAL.concurrencyProfile,
        (DAL.minConcurrencyLevel, DAL.valueGuardProperty),
    ),
    "orderingGrain": (
        DAL.OrderingProfile,
        DAL.orderingGrain,
        (DAL.opSeqRequired, DAL.datasetTierModel),
    ),
    "receiptModel": (
        DAL.ReceiptProfile,
        DAL.receiptModel,
        (),
    ),
    "metaTopology": (
        DAL.MetaTopologyProfile,
        DAL.metaTopology,
        (DAL.metaShards, DAL.priorMetaShards, DAL.epochBumpAcknowledged),
    ),
    # Added by persistence-compiler-iri-sync Slice 1. dal:epochAuthority is
    # carried as an extra, not the resolved value: dal:epochGuardScope is
    # what determines the generated SPARQL's guard shape (guide §19.1),
    # while dal:epochAuthority governs the restore runbook, not the write
    # path. dal:epochCoordinatorBinding/erasureRegisterBinding/
    # erasureReplayOnRestore are deferred to Slice 4 of the same plan.
    "epochGuardScope": (
        DAL.EpochProfile,
        DAL.epochGuardScope,
        (DAL.epochAuthority,),
    ),
}


def _extras(graph: Graph, subject: URIRef, props: tuple[URIRef, ...]) -> dict:
    out = {}
    for prop in props:
        value = graph.value(subject, prop)
        if value is not None:
            local = str(prop).rsplit("#", 1)[-1]
            out[local] = value
    return out


def collect_candidates(graph: Graph, target: Target, dimension: str) -> list[Candidate]:
    dedicated_class, value_prop, extra_props = _DIMENSION_SPEC[dimension]
    scopes_by_iri = {s.iri: s for s in all_scopes(graph)}
    candidates: list[Candidate] = []

    subjects = set(graph.subjects(RDF.type, dedicated_class)) | set(graph.subjects(RDF.type, DAL.DataAccessProfile))
    for subject in subjects:
        value = graph.value(subject, value_prop)
        if value is None:
            continue
        scope_iri = graph.value(subject, DAL.appliesTo)
        if scope_iri is None:
            continue
        scope = scopes_by_iri.get(scope_iri)
        if scope is None:
            continue
        if not matches(graph, scope, target):
            continue
        candidates.append(
            Candidate(
                scope=str(scope.iri),
                scope_kind=scope.kind,
                priority=scope.priority,
                requires_reasoning=scope.requires_reasoning,
                profile=str(subject),
                value=value,
                extra=_extras(graph, subject, extra_props),
            )
        )
    return candidates


def resolve_dimension(
    graph: Graph,
    target: Target,
    dimension: str,
    capability_spec: Optional[CapabilitySpec],
) -> ResolvedDimension:
    candidates = collect_candidates(graph, target, dimension)

    dropped: list[str] = []
    if capability_spec is not None:
        kept = []
        for c in candidates:
            if c.requires_reasoning and not capability_spec.provides_reasoning:
                dropped.append(c.scope)
                continue
            kept.append(c)
        candidates = kept
    # capability_spec is None: nothing is dropped on capability grounds
    # (sketch §3.6). The requirement record still notes what was used.

    if not candidates:
        return ResolvedDimension(
            dimension=dimension,
            value=BASELINE_DEFAULTS.get(dimension),
            won_by=None,
            candidate_count=0,
            dropped_for_reasoning=dropped,
        )

    max_priority = max(c.priority for c in candidates)
    top = [c for c in candidates if c.priority == max_priority]

    if len(top) > 1:
        non_reasoning = [c for c in top if not c.requires_reasoning]
        if len(non_reasoning) == 1:
            top = non_reasoning
        elif len(non_reasoning) > 1:
            raise ProfileAmbiguityError(str(target), dimension, non_reasoning)
        else:
            raise ProfileAmbiguityError(str(target), dimension, top)

    winner = top[0]
    extra = dict(winner.extra)
    if dimension == "aggregateBoundary" and str(winner.value).endswith("CompositePropertyBoundary"):
        boundary_shape = extra.get("boundaryShape")
        if boundary_shape is not None:
            from .boundary import walk_boundary_shape

            max_depth = int(extra.get("maxTraversalDepth", 8))
            closure = walk_boundary_shape(graph, boundary_shape, max_depth)
            extra["compositeProperties"] = closure.composite_properties

    return ResolvedDimension(
        dimension=dimension,
        value=winner.value,
        won_by=winner.profile,
        candidate_count=len(candidates),
        extra=extra,
        dropped_for_reasoning=dropped,
        won_by_requires_reasoning=winner.requires_reasoning,
    )


def resolve_uniqueness(graph: Graph, target: Target) -> list[dict]:
    """Uniqueness is many-valued, not single-winner (sketch §3.3): a target
    may carry zero, one, or several distinct keyed constraints."""
    out = []
    scopes_by_iri = {s.iri: s for s in all_scopes(graph)}
    for constraint in graph.subjects(RDF.type, DAL.UniquenessConstraint):
        scope_iri = graph.value(constraint, DAL.appliesTo)
        if scope_iri is None:
            continue
        scope = scopes_by_iri.get(scope_iri)
        if scope is None or not matches(graph, scope, target):
            continue
        key_list_head = graph.value(constraint, DAL.keyProperty)
        key_props = list(graph.items(key_list_head)) if key_list_head is not None else []
        out.append(
            {
                "constraint": str(constraint),
                "constraintId": str(graph.value(constraint, DAL.constraintId) or ""),
                "keyProperty": [str(k) for k in key_props],
                "scopeProperty": graph.value(constraint, DAL.scopeProperty),
                "onViolation": graph.value(constraint, DAL.onViolation),
                "minEnforcementLevel": graph.value(constraint, DAL.minEnforcementLevel),
            }
        )
    return out


__all__ = ["resolve_dimension", "resolve_uniqueness", "collect_candidates"]
