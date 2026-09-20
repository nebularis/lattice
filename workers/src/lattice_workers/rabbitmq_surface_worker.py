"""RabbitMQ transport adapter for the transport-neutral Surface job consumer."""

from __future__ import annotations

import json
from typing import Any, Mapping, Protocol

from .surface_consumer import SurfaceJobConsumer


class RabbitMqChannel(Protocol):
    """Subset of the pika channel API required by the worker adapter."""

    def basic_ack(self, delivery_tag: int) -> None:
        """Acknowledge a successfully handled delivery."""

    def basic_nack(self, delivery_tag: int, requeue: bool) -> None:
        """Reject a delivery for configured retry or dead-letter handling."""

    def basic_publish(self, exchange: str, routing_key: str, body: bytes, properties: Any) -> None:
        """Publish a result event."""


class RabbitMqSurfaceResultPublisher:
    """Publishes content-type-marked result events using the job ID as message ID."""

    def __init__(self, channel: RabbitMqChannel, exchange: str, routing_key: str, properties_factory: Any) -> None:
        self._channel = channel
        self._exchange = exchange
        self._routing_key = routing_key
        self._properties_factory = properties_factory

    def publish(self, job_id: str, result: Mapping[str, Any]) -> None:
        properties = self._properties_factory(content_type="application/json", message_id=job_id, correlation_id=result["correlationId"], delivery_mode=2)
        body = json.dumps(result, sort_keys=True, separators=(",", ":")).encode("utf-8")
        self._channel.basic_publish(self._exchange, self._routing_key, body, properties)


class RabbitMqSurfaceWorker:
    """Acknowledges only after consumer execution, publication, and durable recording succeed."""

    def __init__(self, consumer: SurfaceJobConsumer) -> None:
        self._consumer = consumer

    def handle(self, channel: RabbitMqChannel, delivery_tag: int, body: bytes) -> None:
        try:
            message = json.loads(body)
            if not isinstance(message, dict):
                raise ValueError("Surface job message must be a JSON object")
            self._consumer.consume(message)
        except (ValueError, UnicodeDecodeError, json.JSONDecodeError):
            channel.basic_nack(delivery_tag, requeue=False)
        except Exception:
            channel.basic_nack(delivery_tag, requeue=True)
            raise
        else:
            channel.basic_ack(delivery_tag)
