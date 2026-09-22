# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""Capability declarations, requirements, and self-checks (sketch §3.6).

Three artefacts, only the first ever mandatory:

* :class:`CapabilityRequirement` -- the compiler's own unconditional output,
  computed purely from a resolved profile. Never needs a live backend.
* :class:`CapabilitySpec` -- an adopter-authored, optional, unverified
  declaration of assumed backend capability. Never derived from a live SPI
  or a TCK run.
* :class:`CapabilityCheckResult` -- a comparison of the two, produced only
  when a spec was supplied.

This compiler never consults a live backend. That is the whole point.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from rdflib import RDF, Graph, URIRef

from .model import ResolvedDimension
from .namespaces import DAL
from .scopes import Target

_CAS_RANK = {"NONE": 0, "BEST_EFFORT": 1, "LINEARIZABLE": 2}
_UNIQUENESS_RANK = {"Advisory": 0, "Transactional": 1, "Strong": 2}


@dataclass(frozen=True)
class CapabilitySpec:
    iri: Optional[str]
    provides_cas: Optional[str] = None
    provides_reasoning: bool = False
    provides_commit_validation: Optional[str] = None
    provides_single_writer: Optional[bool] = None
    provides_statement_level_conflict_detection: Optional[bool] = None


def load_capability_spec(graph: Graph, target: Optional[Target] = None) -> Optional[CapabilitySpec]:
    """Find a ``dal:CapabilitySpec``. If more than one is present, prefer one
    whose ``dal:appliesToTarget`` matches ``target``; otherwise the first
    spec with no ``dal:appliesToTarget`` at all (a deployment-wide default).
    Returns ``None`` if no applicable spec exists, which is the ordinary
    case (sketch §3.6): absence never blocks anything."""
    specs = list(graph.subjects(RDF.type, DAL.CapabilitySpec))
    if not specs:
        return None

    def _build(iri: URIRef) -> CapabilitySpec:
        cas = graph.value(iri, DAL.providesCas)
        reasoning = graph.value(iri, DAL.providesReasoning)
        commit = graph.value(iri, DAL.providesCommitValidation)
        single_writer = graph.value(iri, DAL.providesSingleWriter)
        stmt_level = graph.value(iri, DAL.providesStatementLevelConflictDetection)
        return CapabilitySpec(
            iri=str(iri),
            provides_cas=str(cas) if cas is not None else None,
            provides_reasoning=bool(reasoning) if reasoning is not None else False,
            provides_commit_validation=str(commit) if commit is not None else None,
            provides_single_writer=bool(single_writer) if single_writer is not None else None,
            provides_statement_level_conflict_detection=(
                bool(stmt_level) if stmt_level is not None else None
            ),
        )

    if target is not None:
        for spec_iri in specs:
            if graph.value(spec_iri, DAL.appliesToTarget) == target.cls:
                return _build(spec_iri)
    for spec_iri in specs:
        if graph.value(spec_iri, DAL.appliesToTarget) is None:
            return _build(spec_iri)
    return None


@dataclass
class CapabilityRequirement:
    requires_cas: Optional[str] = None
    requires_reasoning_for: list[str] = field(default_factory=list)
    requires_uniqueness_level: Optional[str] = None


def compute_requirement(
    dimensions: dict[str, ResolvedDimension],
    uniqueness: list[dict],
) -> CapabilityRequirement:
    """Unconditional: computed purely from a resolved profile, no backend
    involved (sketch §3.6, ADR-A78 point 6)."""
    concurrency = dimensions.get("concurrencyProfile")
    requires_cas = None
    if concurrency is not None:
        strategy_local = str(concurrency.value).rsplit("#", 1)[-1] if concurrency.value else None
        if strategy_local == "Optimistic":
            level = concurrency.extra.get("minConcurrencyLevel")
            level_local = str(level).rsplit("#", 1)[-1] if level else "BEST_EFFORT"
            requires_cas = level_local.upper() if level_local.upper() in _CAS_RANK else "BEST_EFFORT"

    reasoning_for = [
        dim.won_by for dim in dimensions.values() if dim.won_by_requires_reasoning and dim.won_by
    ]

    highest_uniqueness = None
    for constraint in uniqueness:
        level = constraint.get("minEnforcementLevel")
        level_local = str(level).rsplit("#", 1)[-1] if level else None
        if level_local and (
            highest_uniqueness is None
            or _UNIQUENESS_RANK.get(level_local, 0) > _UNIQUENESS_RANK.get(highest_uniqueness, 0)
        ):
            highest_uniqueness = level_local

    return CapabilityRequirement(
        requires_cas=requires_cas,
        requires_reasoning_for=reasoning_for,
        requires_uniqueness_level=highest_uniqueness,
    )


@dataclass
class CapabilityCheckResult:
    verdict: str  # "PASS" | "FAIL"
    against: str  # the spec IRI
    failures: list[str] = field(default_factory=list)


def check_requirement(requirement: CapabilityRequirement, spec: CapabilitySpec) -> CapabilityCheckResult:
    failures: list[str] = []

    if requirement.requires_cas:
        required_rank = _CAS_RANK.get(requirement.requires_cas, 0)
        provided_rank = _CAS_RANK.get(spec.provides_cas or "NONE", 0)
        if provided_rank < required_rank:
            failures.append(
                f"requires concurrency {requirement.requires_cas}, spec provides "
                f"{spec.provides_cas or 'NONE'}"
            )

    if requirement.requires_reasoning_for and not spec.provides_reasoning:
        failures.append(
            f"requires reasoning for scope(s) {requirement.requires_reasoning_for}, "
            "spec declares providesReasoning=false"
        )

    if requirement.requires_uniqueness_level == "Strong":
        if spec.provides_commit_validation in (None, "NONE"):
            failures.append(
                "requires Strong uniqueness enforcement, spec provides no commit-time validation"
            )

    return CapabilityCheckResult(
        verdict="PASS" if not failures else "FAIL",
        against=spec.iri or "",
        failures=failures,
    )


__all__ = [
    "CapabilitySpec",
    "load_capability_spec",
    "CapabilityRequirement",
    "compute_requirement",
    "CapabilityCheckResult",
    "check_requirement",
]
