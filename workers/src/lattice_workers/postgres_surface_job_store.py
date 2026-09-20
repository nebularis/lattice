"""PostgreSQL implementation of durable processed Surface job state."""

from __future__ import annotations

import json
from contextlib import closing
from typing import Any, Callable, Mapping

from .surface_consumer import DuplicateSurfaceJobError


class PostgresProcessedSurfaceJobStore:
    """Stores idempotent worker results after publisher acknowledgement."""

    def __init__(self, connection_factory: Callable[[], Any]) -> None:
        self._connection_factory = connection_factory

    def find(self, job_id: str, request_digest: str) -> Mapping[str, Any] | None:
        with closing(self._connection_factory()) as connection, connection.cursor() as cursor:
            cursor.execute("select request_digest, result_json from processed_surface_job where job_id = %s", (job_id,))
            row = cursor.fetchone()
        if row is None:
            return None
        found_digest, result = row
        if found_digest != request_digest:
            raise DuplicateSurfaceJobError("Surface job ID was reused for different request content")
        return result if isinstance(result, dict) else json.loads(result)

    def record(self, job_id: str, request_digest: str, result: Mapping[str, Any]) -> None:
        with closing(self._connection_factory()) as connection, connection.cursor() as cursor:
            cursor.execute(
                "insert into processed_surface_job (job_id, request_digest, result_json) values (%s, %s, %s::jsonb) on conflict (job_id) do nothing",
                (job_id, request_digest, json.dumps(result, sort_keys=True, separators=(",", ":"))),
            )
            connection.commit()
        persisted = self.find(job_id, request_digest)
        if persisted is None:
            raise RuntimeError("processed Surface job was not persisted")
