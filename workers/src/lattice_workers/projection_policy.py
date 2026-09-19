"""Governance policy for staged Surface Projection mappings."""

from __future__ import annotations

from typing import Literal

ProjectionKind = Literal["derivation", "join", "expansion"]
ReviewRequirement = Literal["engineering_review", "mapping_review"]


def review_requirement(projection_kind: ProjectionKind) -> ReviewRequirement:
    """Require engineering review for computed/expanded projections and mapping review for joins."""
    if projection_kind not in {"derivation", "join", "expansion"}:
        raise ValueError(f"unsupported Projection kind: {projection_kind}")
    return "mapping_review" if projection_kind == "join" else "engineering_review"


def handoff_policy(projection_kind: ProjectionKind) -> dict[str, str | bool]:
    return {"projectionKind": projection_kind, "reviewRequirement": review_requirement(projection_kind), "stagingOnly": True, "activationAuthority": "mork_governance_workflow"}