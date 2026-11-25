"""Governance policy for staged Surface Projection mappings.

The review a projection asks is the one its compilation records. `mork_rdf` names each by the kind it reviews, `DerivationReview` for a computed
value, `ExpansionReview` for a relation restated for each node it reaches or a node made for each member, and `MappingReview` for a join or an
identity read from the source, which merges the instances that share it. A construction with a node for each instance records none. The policy reads
those findings and never restates the rule that raises them, so it follows the compiler where the rule changes (ADR-A41, addendum of 2026-11-25)."""

from __future__ import annotations

from typing import Any, Iterable, Literal

ProjectionKind = Literal["derivation", "join", "expansion", "graph_construction"]
ReviewRequirement = Literal["DerivationReview", "ExpansionReview", "MappingReview"]

REVIEWS: tuple[ReviewRequirement, ...] = ("DerivationReview", "ExpansionReview", "MappingReview")


def review_requirements(findings: Iterable[Any]) -> tuple[ReviewRequirement, ...]:
    """The reviews a compilation asks, each once, in the order of their names. `findings` are the compile's findings, `mork_rdf`'s `Finding` or
    anything with a `code`, or the codes themselves. A finding that is no review is left out."""
    codes = {getattr(finding, "code", finding) for finding in findings}
    return tuple(review for review in REVIEWS if review in codes)


def handoff_policy(projection_kind: ProjectionKind, findings: Iterable[Any]) -> dict[str, Any]:
    """The policy a projection's handoff to MORK states: its kind, the reviews its compile findings ask, and that it is staged and never activated
    here. A projection that asks no review has an empty list."""
    if projection_kind not in {"derivation", "join", "expansion", "graph_construction"}:
        raise ValueError(f"unsupported Projection kind: {projection_kind}")
    return {
        "projectionKind": projection_kind,
        "reviewRequirements": list(review_requirements(findings)),
        "stagingOnly": True,
        "activationAuthority": "mork_governance_workflow",
    }
