# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""Plain data types shared across the resolver, validator, capability, and
compiler modules. Deliberately not RDF: these are the compiler's internal
working representation. RDF serialisation of the outcome happens only in
:mod:`persistence.compiler`'s emit step.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


# The original six dimension names (sketch §3.3), used as plain strings
# throughout, never as IRIs -- ``dal:dimension`` is an ``xsd:string``
# property. ``epochGuardScope`` was added by the persistence-compiler-iri-
# sync unit (Slice 1, 2026-09-23) to resolve ``dal:EpochProfile``'s
# ``dal:epochGuardScope``, added to ``ontology/persistence`` by commit
# c276afb (iri-identity-patterns.md §10.3).
#
# Slice 2 of the same unit adds one dimension per extension property
# (plan decision 1): each is resolved by the same precedence algorithm as
# the original six, from any node that declares it, instead of being read
# only as an "extra" of whichever node won a related dimension.
#
# Slice 4 promotes ``epochAuthority`` out of ``epochGuardScope``'s extras
# into its own dimension, for the same reason Slice 2 gave the other
# extension properties their own dimension: read only as an extra, a
# property declared on a node other than the one that wins
# ``epochGuardScope`` would be dropped silently. Slice 4 also wires
# ``dal:PrivacyProfile``'s three properties and ``dal:ReceiptProfile``'s
# ``dal:perSubjectScoped`` into resolution, one dimension per property,
# matching Slice 2's per-property style: ``dal:PrivacyProfile`` is a new
# profile class in the same shape as ``dal:EpochProfile``, not a
# resource-role situation like Slice 3's identity dimensions, so there is
# no reason for a whole-node-wins model here.
DIMENSIONS = (
    "aggregateBoundary",
    "concurrencyProfile",
    "orderingGrain",
    "receiptModel",
    "metaTopology",
    "epochGuardScope",
    "firstWrite",
    "etagForm",
    "etagRepresentation",
    "deadlockPolicy",
    "globalReadStrategy",
    "lagWindowMillis",
    "contiguityCheckMode",
    "retentionMode",
    "asOfFloorSource",
    "txnShards",
    "logShards",
    "keyShards",
    "registryGraph",
    # Slice 4 (2026-09-23).
    "epochAuthority",
    "privacyClass",
    "erasureStrategy",
    "erasurePrecedence",
    "perSubjectScoped",
)

# Dimensions whose resolved value is an RDF literal, emitted with
# ``dal:resolvedLiteral`` rather than ``dal:resolvedValue``.
LITERAL_DIMENSIONS = frozenset(
    {"lagWindowMillis", "asOfFloorSource", "txnShards", "logShards", "keyShards", "registryGraph",
     "perSubjectScoped"}
)

# Platform baseline defaults (sketch §3.4.1). Every dimension resolves to
# one of these when no scope matches a target.
#
# ``epochGuardScope`` defaults to ``RowLevelGuardOnly`` deliberately: this
# is the shape every existing template already generated before Slice 1 of
# persistence-compiler-iri-sync, so declaring it as the explicit baseline
# changes no existing deployment's generated SPARQL. It is the shape
# ``dal:RowLevelGuardOnlyWarningShape`` calls discouraged, and this
# baseline default is not exempt from that warning: see
# ``validator.check_cross_axis``'s epoch-guard-scope row, which fires
# whether the value came from an explicit ``dal:EpochProfile`` or from
# this default, so the discouraged shape is never generated silently.
BASELINE_DEFAULTS: dict[str, str] = {
    "aggregateBoundary": "NamedGraphBoundary",
    "concurrencyProfile": "ProvidedConcurrency",
    "orderingGrain": "CommitGrain",
    "receiptModel": "ReceiptOnly",
    "metaTopology": "SharedSharded",
    "epochGuardScope": "RowLevelGuardOnly",
    # Slice 2 (plan decision 2). No default for globalReadStrategy,
    # lagWindowMillis, asOfFloorSource, the shard counts or registryGraph:
    # their absence is itself meaningful and checked where it matters.
    "firstWrite": "AbsentRow",
    "etagForm": "StrongEtag",
    "etagRepresentation": "SingleRepresentation",
    "deadlockPolicy": "EngineDetectAndRetry",
    "contiguityCheckMode": "BlockingContiguityCheck",
    "retentionMode": "PrefixOnlyRetention",
    # Slice 4 (plan decision, following Slice 2 decision 2's precedent): no
    # default for epochAuthority, privacyClass, erasureStrategy,
    # erasurePrecedence or perSubjectScoped. An undeclared dal:PrivacyProfile
    # means "this scope declares no privacy stance", not "this scope is
    # PublicData": absence is itself meaningful, checked only where a
    # dal:PrivacyProfile actually exists (validator._check_slice_4).
}


@dataclass(frozen=True)
class Candidate:
    """One profile individual's declared value for one dimension at one
    target, before priority resolution."""

    scope: str  # scope individual's IRI
    scope_kind: str  # "GraphPatternScope" | "NamespaceScope" | "ClassScope" | "ShapeScope" | "EquivalentClassScope"
    priority: int
    requires_reasoning: bool
    profile: str  # the profile individual asserting this value (for provenance)
    value: Any
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class ResolvedDimension:
    dimension: str
    value: Optional[Any]
    won_by: Optional[str]
    candidate_count: int
    extra: dict[str, Any] = field(default_factory=dict)
    dropped_for_reasoning: list[str] = field(default_factory=list)
    won_by_requires_reasoning: bool = False


@dataclass
class Diagnostic:
    kind: str
    message: str
    severity: str  # "WARNING" | "ERROR"
    target: Optional[str] = None


@dataclass
class ResolvedTarget:
    target: str
    dimensions: dict[str, ResolvedDimension]
    uniqueness: list[dict[str, Any]]
    diagnostics: list[Diagnostic] = field(default_factory=list)


class ProfileAmbiguityError(Exception):
    """A dimension had more than one candidate at the highest priority,
    and none was preferred by the non-reasoning-over-reasoning tiebreak."""

    def __init__(self, target: str, dimension: str, tied: list[Candidate]):
        self.target = target
        self.dimension = dimension
        self.tied = tied
        scopes = ", ".join(c.scope for c in tied)
        super().__init__(
            f"ambiguous resolution for dimension {dimension!r} at target {target!r}: "
            f"tied candidates at equal priority from scopes [{scopes}]"
        )


class CrossAxisViolation(Exception):
    """A named, structured cross-axis consistency failure (sketch §3.5)."""

    def __init__(self, kind: str, target: str, message: str):
        self.kind = kind
        self.target = target
        super().__init__(f"{kind} at {target}: {message}")


class BoundaryConflict(Exception):
    """A resource belongs to two aggregates under incompatible boundary
    strategies (sketch §4.6)."""

    def __init__(self, message: str):
        super().__init__(message)


__all__ = [
    "DIMENSIONS",
    "BASELINE_DEFAULTS",
    "LITERAL_DIMENSIONS",
    "Candidate",
    "ResolvedDimension",
    "Diagnostic",
    "ResolvedTarget",
    "ProfileAmbiguityError",
    "CrossAxisViolation",
    "BoundaryConflict",
]
