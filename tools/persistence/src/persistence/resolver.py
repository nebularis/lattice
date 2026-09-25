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
    # Added by persistence-compiler-iri-sync Slice 1, revised by Slice 4.
    # dal:epochGuardScope is what determines the generated SPARQL's guard
    # shape (guide §19.1). dal:epochAuthority governs the restore runbook,
    # not the write path, and was originally carried as an extra of this
    # dimension; Slice 4 promotes it to its own dimension below, for the
    # same reason Slice 2 gave every other extension property its own
    # dimension (an extra is silently dropped if declared on a node other
    # than the one that wins the dimension it rides on).
    "epochGuardScope": (
        DAL.EpochProfile,
        DAL.epochGuardScope,
        (),
    ),
    # Slice 2 (plan decision 1): one dimension per extension property, so
    # a property declared on its own profile node, or on a lower-priority
    # node than the one that wins a related dimension, is still resolved.
    "firstWrite": (DAL.AggregateBoundaryProfile, DAL.firstWrite, ()),
    "etagForm": (DAL.ConcurrencyProfile, DAL.etagForm, ()),
    "etagRepresentation": (DAL.ConcurrencyProfile, DAL.etagRepresentation, ()),
    "deadlockPolicy": (DAL.ConcurrencyProfile, DAL.deadlockPolicy, ()),
    "globalReadStrategy": (DAL.OrderingProfile, DAL.globalReadStrategy, ()),
    "lagWindowMillis": (DAL.OrderingProfile, DAL.lagWindowMillis, ()),
    "contiguityCheckMode": (DAL.OrderingProfile, DAL.contiguityCheckMode, ()),
    "retentionMode": (DAL.ReceiptProfile, DAL.retentionMode, ()),
    "asOfFloorSource": (DAL.ReceiptProfile, DAL.asOfFloorSource, ()),
    "txnShards": (DAL.MetaTopologyProfile, DAL.txnShards, ()),
    "logShards": (DAL.MetaTopologyProfile, DAL.logShards, ()),
    "keyShards": (DAL.MetaTopologyProfile, DAL.keyShards, ()),
    "registryGraph": (DAL.MetaTopologyProfile, DAL.registryGraph, ()),
    # Slice 4 (2026-09-23). epochAuthority carries the remaining restore-
    # surface properties as extras: they are all read from the same
    # dal:EpochProfile node and none of them needs its own cross-axis
    # check yet, unlike epochAuthority itself (checked against
    # eventIdentityStrategy in check_identity, and against StoreLocalEpoch
    # in check_cross_axis).
    "epochAuthority": (
        DAL.EpochProfile,
        DAL.epochAuthority,
        (DAL.epochCoordinatorBinding, DAL.erasureRegisterBinding, DAL.erasureReplayOnRestore),
    ),
    "privacyClass": (DAL.PrivacyProfile, DAL.privacyClass, ()),
    "erasureStrategy": (DAL.PrivacyProfile, DAL.erasureStrategy, ()),
    "erasurePrecedence": (DAL.PrivacyProfile, DAL.erasurePrecedence, ()),
    "perSubjectScoped": (DAL.ReceiptProfile, DAL.perSubjectScoped, ()),
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
    subjects = set(graph.subjects(RDF.type, dedicated_class)) | set(graph.subjects(RDF.type, DAL.DataAccessProfile))
    return _candidates_from(graph, target, subjects, value_prop, extra_props)


def _candidates_from(
    graph: Graph, target: Target, subjects, value_prop: URIRef, extra_props: tuple[URIRef, ...]
) -> list[Candidate]:
    scopes_by_iri = {s.iri: s for s in all_scopes(graph)}
    candidates: list[Candidate] = []
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
    return _select(graph, target, dimension, candidates, capability_spec, BASELINE_DEFAULTS.get(dimension))


def _select(
    graph: Graph,
    target: Target,
    dimension: str,
    candidates: list[Candidate],
    capability_spec: Optional[CapabilitySpec],
    default,
) -> ResolvedDimension:
    """The precedence algorithm (sketch §3.4), shared by every dimension:
    capability filtering, highest priority, non-reasoning over reasoning,
    and a refusal on any remaining tie."""
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
            value=default,
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


# persistence-compiler-iri-sync Slice 3 (plan decision 1): identity is
# resolved per resource role. Each role is its own dimension, named
# identity:<RoleLocalName>, and the winning dal:IdentityProfile node wins as
# a unit, so its digest scheme and event settings always travel with the
# strategy they qualify. Only dal:IdentityProfile nodes are candidates: a
# role-less dal:DataAccessProfile cannot say which role it configures.
IDENTITY_EXTRAS: tuple[URIRef, ...] = (
    DAL.digestScheme,
    DAL.occurrenceNamespaceDerivation,
    DAL.eventIdentityStrategy,
    DAL.uniquenessWitnessRequired,
    DAL.namingAuthority,
)


def identity_dimension(role: URIRef) -> str:
    return "identity:" + str(role).rsplit("#", 1)[-1]


def resolve_identity(
    graph: Graph, target: Target, capability_spec: Optional[CapabilitySpec]
) -> dict[str, ResolvedDimension]:
    """Returns one resolved dimension per resource role that at least one
    matching dal:IdentityProfile declares, keyed by ``identity:<Role>`` and
    ordered by role IRI. Undeclared roles are absent: there is no baseline
    identity strategy (ADR-A82)."""
    by_role: dict[URIRef, list[URIRef]] = {}
    for profile in graph.subjects(RDF.type, DAL.IdentityProfile):
        role = graph.value(profile, DAL.resourceRole)
        if isinstance(role, URIRef):
            by_role.setdefault(role, []).append(profile)
    out: dict[str, ResolvedDimension] = {}
    for role in sorted(by_role, key=str):
        name = identity_dimension(role)
        candidates = _candidates_from(graph, target, by_role[role], DAL.identityStrategy, IDENTITY_EXTRAS)
        if not candidates:
            continue
        resolved = _select(graph, target, name, candidates, capability_spec, None)
        if resolved.value is not None:
            out[name] = resolved
    return out


# persistence-compiler-iri-sync Slice 5: the states recipes.py's own
# claims() already treats as an active minting scheme (identity-minting
# M1). A constraint's dal:claimScheme is a dal:Dual rotation, for the
# write-time template's purposes, exactly when two of its claim schemes
# are active at once -- mirroring that existing filter rather than a
# second, potentially divergent rule (for example "any scheme is Dual").
_MINTING_ACTIVE_STATES = frozenset({"Accepting", "Dual"})


def _local_name(value) -> str | None:
    return str(value).rsplit("#", 1)[-1] if value is not None else None


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
        active_schemes = [
            s
            for s in graph.objects(constraint, DAL.claimScheme)
            if _local_name(graph.value(s, DAL.schemeState)) in _MINTING_ACTIVE_STATES
        ]
        out.append(
            {
                "constraint": str(constraint),
                "constraintId": str(graph.value(constraint, DAL.constraintId) or ""),
                "keyProperty": [str(k) for k in key_props],
                "scopeProperty": graph.value(constraint, DAL.scopeProperty),
                "onViolation": graph.value(constraint, DAL.onViolation),
                "minEnforcementLevel": graph.value(constraint, DAL.minEnforcementLevel),
                # persistence-compiler-iri-sync Slice 5 (G7 items 2 and 3).
                "mergeRelation": graph.value(constraint, DAL.mergeRelation),
                "dualClaimScheme": len(active_schemes) == 2,
            }
        )
    return out


__all__ = [
    "resolve_dimension",
    "resolve_uniqueness",
    "resolve_identity",
    "identity_dimension",
    "collect_candidates",
    "IDENTITY_EXTRAS",
]
