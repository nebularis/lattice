"""Transport-neutral consumer and RabbitMQ adapter for wording analysis jobs (plan WA7).

Reads a Wording graph, proposes an `ins:` meaning graph via `wording_le`, writes it back through
a Graph Store Protocol client, and publishes a `wording-analysis-result` event.
"""

from __future__ import annotations

import hashlib
import json
from importlib import resources
from typing import Any, Callable, Mapping, Protocol

from .fuseki_gsp import GraphNotFound
from .graph_validation import GraphReference, InvalidJob
from .rabbitmq_surface_worker import RabbitMqChannel
from .wording_le.analyse import analyse_wording
from .wording_le.forms import FormProfile
from .wording_le.model import load_wording
from .wording_le.proposal import graph_view, proposal_graph

TOPOLOGY: dict[str, Any] = json.loads(
    resources.files("lattice_workers").joinpath("amqp-topology.json").read_text(encoding="utf-8")
)
REQUESTED_QUEUE = "lattice.authoring.analysis.requested"
RESULT_EXCHANGE = "lattice.authoring"
RESULT_ROUTING_KEY = "lattice.authoring.analysis.completed"

_REQUEST_FIELD_TYPES: dict[str, type] = {
    "jobId": str,
    "correlationId": str,
    "documentId": str,
    "revision": int,
    "wordingGraph": dict,
    "wordingIri": str,
    "proposalGraphIri": str,
    "requestedAt": str,
}


class GraphStore(Protocol):
    """Subset of `FusekiGraphStore` required by the consumer."""

    def get_graph(self, graph_iri: str) -> Any:
        """Read a named graph, raising `GraphNotFound` when it does not exist."""

    def put_graph(self, graph_iri: str, graph: Any) -> None:
        """Write a named graph, replacing any prior content."""


class ResultPublisher(Protocol):
    """Publishes one `wording-analysis-result` event, keyed by job ID."""

    def publish(self, job_id: str, result: Mapping[str, Any]) -> None:
        """Publish result, which must already validate against `wording-analysis-result`."""


def _validate_request(message: Mapping[str, Any]) -> None:
    if set(message) != set(_REQUEST_FIELD_TYPES):
        raise InvalidJob("message fields do not match wording-analysis-request 0.1.0")
    for field, expected_type in _REQUEST_FIELD_TYPES.items():
        value = message[field]
        if expected_type is int:
            if not isinstance(value, int) or isinstance(value, bool):
                raise InvalidJob(f"{field} must be an integer")
        elif not isinstance(value, expected_type):
            raise InvalidJob(f"{field} must be a {expected_type.__name__}")
    GraphReference.from_payload(message["wordingGraph"])


def _graph_hash(graph: Any) -> str:
    """A worker-local content hash over the graph's sorted N-Triples lines, not comparable with
    the Java service's `CanonicalHash` (different library, same shape of guarantee)."""
    lines = sorted(line.strip() for line in graph.serialize(format="nt").splitlines() if line.strip())
    canonical = ("\n".join(lines) + "\n").encode("utf-8")
    return f"sha256:{hashlib.sha256(canonical).hexdigest()}"


class WordingAnalysisConsumer:
    """Validates, reads, analyses, writes back and publishes one wording analysis job."""

    def __init__(
        self,
        store: GraphStore,
        publisher: ResultPublisher,
        profile: FormProfile,
        clock: Callable[[], str],
    ) -> None:
        self._store = store
        self._publisher = publisher
        self._profile = profile
        self._clock = clock

    def consume(self, message: Mapping[str, Any]) -> dict[str, Any]:
        _validate_request(message)
        job_id = message["jobId"]

        try:
            graph = self._store.get_graph(message["wordingGraph"]["graphIri"])
        except GraphNotFound:
            result = self._failed(message, "wording graph not found")
            self._publisher.publish(job_id, result)
            return result

        try:
            wording = load_wording(graph, message["wordingIri"])
        except ValueError as error:
            result = self._failed(message, str(error))
            self._publisher.publish(job_id, result)
            return result

        proposal_graph_iri = message["proposalGraphIri"]
        analysis = analyse_wording(wording, self._profile)
        proposal = proposal_graph(wording, analysis["elements"], proposal_graph_iri, self._profile)
        analysis_with_view = {**analysis, "graphView": graph_view(wording, proposal)}

        self._store.put_graph(proposal_graph_iri, proposal)

        result = {
            "jobId": job_id,
            "correlationId": message["correlationId"],
            "documentId": message["documentId"],
            "revision": message["revision"],
            "status": "completed",
            "error": None,
            "proposalGraph": {
                "tenantId": "poc",
                "projectId": "word-authoring",
                "graphIri": proposal_graph_iri,
                "revisionHash": _graph_hash(proposal),
            },
            "analysis": analysis_with_view,
            "completedAt": self._clock(),
        }
        self._publisher.publish(job_id, result)
        return result

    def _failed(self, message: Mapping[str, Any], error: str) -> dict[str, Any]:
        return {
            "jobId": message["jobId"],
            "correlationId": message["correlationId"],
            "documentId": message["documentId"],
            "revision": message["revision"],
            "status": "failed",
            "error": error,
            "proposalGraph": None,
            "analysis": None,
            "completedAt": self._clock(),
        }


class RabbitMqResultPublisher:
    """Publishes a `wording-analysis-result` event with the job ID as message and correlation id."""

    def __init__(self, channel: RabbitMqChannel, properties_factory: Any) -> None:
        self._channel = channel
        self._properties_factory = properties_factory

    def publish(self, job_id: str, result: Mapping[str, Any]) -> None:
        properties = self._properties_factory(
            content_type="application/json",
            message_id=job_id,
            correlation_id=job_id,
            delivery_mode=2,
        )
        body = json.dumps(result, sort_keys=True, separators=(",", ":")).encode("utf-8")
        self._channel.basic_publish(RESULT_EXCHANGE, RESULT_ROUTING_KEY, body, properties)


class RabbitMqWordingAnalysisWorker:
    """Acknowledges only after the consumer has validated, processed and published successfully."""

    def __init__(self, consumer: WordingAnalysisConsumer) -> None:
        self._consumer = consumer

    def handle(self, channel: RabbitMqChannel, delivery_tag: int, body: bytes) -> None:
        try:
            message = json.loads(body)
            if not isinstance(message, dict):
                raise ValueError("wording analysis message must be a JSON object")
            self._consumer.consume(message)
        except (ValueError, UnicodeDecodeError, json.JSONDecodeError):
            channel.basic_nack(delivery_tag, requeue=False)
        except Exception:
            channel.basic_nack(delivery_tag, requeue=True)
            raise
        else:
            channel.basic_ack(delivery_tag)


def declare_topology(channel: Any, topology: Mapping[str, Any]) -> None:
    """Declares the exchanges, queues and bindings of `topology`. Idempotent."""
    exchange = topology["exchange"]
    dead_letter_exchange = topology["deadLetterExchange"]
    channel.exchange_declare(exchange=exchange, exchange_type="topic", durable=True)
    channel.exchange_declare(exchange=dead_letter_exchange, exchange_type="topic", durable=True)
    for queue in topology["queues"]:
        if queue["deadLetter"]:
            channel.queue_declare(
                queue=queue["name"], durable=True, arguments={"x-dead-letter-exchange": dead_letter_exchange}
            )
            channel.queue_bind(queue=queue["name"], exchange=exchange, routing_key=queue["routingKey"])
        else:
            channel.queue_declare(queue=queue["name"], durable=True)
            channel.queue_bind(queue=queue["name"], exchange=dead_letter_exchange, routing_key=queue["routingKey"])
