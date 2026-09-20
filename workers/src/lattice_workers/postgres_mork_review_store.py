"""PostgreSQL persistence adapter for immutable MORK review snapshots and decisions."""

from __future__ import annotations

import json
from contextlib import closing
from typing import Any, Callable, Mapping

from .mork_review_lifecycle import StaleReviewSnapshotError


class PostgresMorkReviewStore:
    def __init__(self, connection_factory: Callable[[], Any]) -> None:
        self._connection_factory = connection_factory

    def register_snapshot(self, snapshot: Mapping[str, Any], version: int) -> None:
        with closing(self._connection_factory()) as connection, connection.cursor() as cursor:
            cursor.execute("select snapshot_version from mork_review_snapshot where snapshot_id = %s", (snapshot["snapshotId"],))
            row = cursor.fetchone()
            if row is not None and version <= row[0]:
                raise StaleReviewSnapshotError("review snapshot version is not newer")
            cursor.execute("insert into mork_review_snapshot (snapshot_id, tenant_id, project_id, mapping_graph_iri, mapping_graph_hash, snapshot_hash, section_id, snapshot_version, evidence_json) values (%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb) on conflict (snapshot_id) do update set mapping_graph_iri=excluded.mapping_graph_iri, mapping_graph_hash=excluded.mapping_graph_hash, snapshot_hash=excluded.snapshot_hash, section_id=excluded.section_id, snapshot_version=excluded.snapshot_version, evidence_json=excluded.evidence_json, recorded_at=current_timestamp", (snapshot["snapshotId"], snapshot["tenantId"], snapshot["projectId"], snapshot["mappingGraph"]["graphIri"], snapshot["mappingGraph"]["revisionHash"], snapshot["snapshotHash"], snapshot["sectionId"], version, json.dumps(snapshot.get("evidenceProjection", []))))
            connection.commit()

    def record_decision(self, tenant_id: str, project_id: str, decision: Mapping[str, str], reviewer_role: str) -> None:
        with closing(self._connection_factory()) as connection, connection.cursor() as cursor:
            cursor.execute("select snapshot_hash from mork_review_snapshot where snapshot_id = %s and tenant_id = %s and project_id = %s", (decision["snapshotId"], tenant_id, project_id))
            row = cursor.fetchone()
            if row is None or row[0] != decision["snapshotHash"]:
                raise StaleReviewSnapshotError("review snapshot is stale or unavailable")
            cursor.execute("insert into mork_review_decision (snapshot_id, snapshot_hash, decision, rationale, reviewer_role) values (%s,%s,%s,%s,%s)", (decision["snapshotId"], decision["snapshotHash"], decision["decision"], decision["rationale"], reviewer_role))
            connection.commit()