import pytest

from lattice_workers.surface_consumer import DuplicateSurfaceJobError, InMemoryProcessedSurfaceJobStore, SurfaceJobConsumer


def message(job_id="job-1"):
    graph = {"tenantId": "tenant", "projectId": "project", "graphIri": "https://example.test/graphs/contract", "revisionHash": "sha256:abc"}
    return {"jobId": job_id, "correlationId": "correlation-1", "jobType": "parity", "contractGraph": graph, "profileGraph": graph | {"graphIri": "https://example.test/graphs/profile"}, "sourceGraphs": []}


class Publisher:
    def __init__(self):
        self.published = []

    def publish(self, job_id, result):
        self.published.append((job_id, result))


def test_retry_republishes_cached_result_without_reexecuting():
    executions = []
    publisher = Publisher()
    consumer = SurfaceJobConsumer(
        lambda *arguments: (executions.append(arguments) or [], []),
        publisher,
        InMemoryProcessedSurfaceJobStore(),
    )

    first = consumer.consume(message())
    second = consumer.consume(message())

    assert first == second
    assert len(executions) == 1
    assert len(publisher.published) == 2


def test_reusing_job_id_for_different_request_is_rejected():
    consumer = SurfaceJobConsumer(lambda *arguments: ([], []), Publisher(), InMemoryProcessedSurfaceJobStore())
    consumer.consume(message())

    with pytest.raises(DuplicateSurfaceJobError, match="reused"):
        consumer.consume(message() | {"correlationId": "different"})


def test_publish_failure_does_not_mark_job_as_processed():
    executions = []

    class FailingPublisher:
        def publish(self, job_id, result):
            raise RuntimeError("broker unavailable")

    consumer = SurfaceJobConsumer(
        lambda *arguments: (executions.append(arguments) or [], []),
        FailingPublisher(),
        InMemoryProcessedSurfaceJobStore(),
    )

    with pytest.raises(RuntimeError, match="broker unavailable"):
        consumer.consume(message())

    assert len(executions) == 1