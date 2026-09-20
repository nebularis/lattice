"""Idempotent delivery boundary for Surface jobs received from a message transport."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Callable, Mapping, Protocol

from .graph_validation import InvalidJob
from .surface_jobs import process_surface_job


class SurfaceResultPublisher(Protocol):
    """Publishes results idempotently using the opaque Surface job ID."""

    def publish(self, job_id: str, result: Mapping[str, Any]) -> None:
        """Publish or confirm the result for job_id."""


class ProcessedSurfaceJobStore(Protocol):
    """Persists successfully published results to prevent repeat compiler execution."""

    def find(self, job_id: str, request_digest: str) -> Mapping[str, Any] | None:
        """Return a cached result for the exact request or reject key reuse."""

    def record(self, job_id: str, request_digest: str, result: Mapping[str, Any]) -> None:
        """Record a result after the publisher acknowledges it."""


class DuplicateSurfaceJobError(InvalidJob):
    """Raised when one opaque job ID is reused for different request content."""


class InMemoryProcessedSurfaceJobStore:
    """Test adapter. Production workers need durable storage or broker idempotency."""

    def __init__(self) -> None:
        self._results: dict[str, tuple[str, Mapping[str, Any]]] = {}

    def find(self, job_id: str, request_digest: str) -> Mapping[str, Any] | None:
        found = self._results.get(job_id)
        if found is None:
            return None
        if found[0] != request_digest:
            raise DuplicateSurfaceJobError("Surface job ID was reused for different request content")
        return found[1]

    def record(self, job_id: str, request_digest: str, result: Mapping[str, Any]) -> None:
        existing = self.find(job_id, request_digest)
        if existing is None:
            self._results[job_id] = (request_digest, dict(result))


class SurfaceJobConsumer:
    """Coordinates validated execution, idempotent result publication, and retry replay."""

    def __init__(
        self,
        execute: Callable[..., tuple[list[dict[str, str]], list[str]]],
        publisher: SurfaceResultPublisher,
        processed: ProcessedSurfaceJobStore,
    ) -> None:
        self._execute = execute
        self._publisher = publisher
        self._processed = processed

    def consume(self, message: Mapping[str, Any]) -> Mapping[str, Any]:
        job_id = self._job_id(message)
        request_digest = self._digest(message)
        cached = self._processed.find(job_id, request_digest)
        if cached is not None:
            self._publisher.publish(job_id, cached)
            return cached

        result = process_surface_job(message, self._execute)
        self._publisher.publish(job_id, result)
        self._processed.record(job_id, request_digest, result)
        return result

    @staticmethod
    def _job_id(message: Mapping[str, Any]) -> str:
        job_id = message.get("jobId")
        if not isinstance(job_id, str) or not job_id:
            raise InvalidJob("Surface job must contain a non-empty jobId")
        return job_id

    @staticmethod
    def _digest(message: Mapping[str, Any]) -> str:
        canonical = json.dumps(message, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
        return f"sha256:{hashlib.sha256(canonical).hexdigest()}"
