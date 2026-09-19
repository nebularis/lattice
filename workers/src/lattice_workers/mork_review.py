"""Typed MORK review snapshot and decision semantics."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Decision = Literal["confirm", "retarget", "reshape", "decline", "teach", "defer"]


@dataclass(frozen=True)
class ReviewEffect:
    decision: Decision
    mapping_effect: str
    learning_effect: str
    changes_projection_statistics: bool


def decision_effect(decision: Decision) -> ReviewEffect:
    effects = {
        "confirm": ReviewEffect("confirm", "accept_snapshot_mapping", "reinforce_mapping_evidence", True),
        "retarget": ReviewEffect("retarget", "replace_target_concept", "record_retarget_evidence", True),
        "reshape": ReviewEffect("reshape", "request_mapping_structure_change", "record_structure_feedback", False),
        "decline": ReviewEffect("decline", "reject_snapshot_mapping", "record_negative_evidence", True),
        "teach": ReviewEffect("teach", "defer_to_teaching_reference", "add_teaching_evidence", True),
        "defer": ReviewEffect("defer", "leave_mapping_unresolved", "record_deferred_review", False),
    }
    if decision not in effects:
        raise ValueError(f"unsupported review decision: {decision}")
    return effects[decision]


def validate_snapshot_scope(snapshot: dict[str, object], tenant_id: str, project_id: str) -> None:
    if snapshot.get("tenantId") != tenant_id or snapshot.get("projectId") != project_id:
        raise PermissionError("reviewer cannot access a snapshot outside the tenant and project scope")