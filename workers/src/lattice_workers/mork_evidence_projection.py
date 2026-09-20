"""Role-restricted review evidence projection boundary."""

from __future__ import annotations

from typing import Any, Mapping


DOMAIN_STEWARD = "domain_steward"


def project_evidence(snapshot: Mapping[str, Any], role: str) -> dict[str, Any]:
    """Return review-safe evidence, excluding syntax, lint, and pack internals for stewards."""
    base = {"snapshotId": snapshot["snapshotId"], "snapshotHash": snapshot["snapshotHash"], "sectionId": snapshot["sectionId"], "evidenceProjection": snapshot.get("evidenceProjection", [])}
    if role == DOMAIN_STEWARD:
        return base
    if role in {"mapping_engineer", "governance_reviewer"}:
        return base | {"technicalDiagnostics": snapshot.get("technicalDiagnostics", []), "mcn": snapshot.get("mcn"), "dependencies": snapshot.get("dependencies", [])}
    raise PermissionError("unknown review role")