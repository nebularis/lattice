"""Entry point for the Configuration Studio worker: `python -m lattice_workers.config_studio_main`."""

from __future__ import annotations

import logging
import os
import signal
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping, Optional

import pika
from pika.exceptions import AMQPConnectionError, ChannelClosed, ChannelWrongStateError, StreamLostError

from .config_studio_consumer import ConnectionLost, Consumer
from .config_studio_jobs import find_root
from .config_studio_secrets import secret
from .config_studio_worker import JOBS_QUEUE, TOPOLOGY, ConfigStudioWorker, WriterStore, declare_topology, declare_writes
from .fuseki_gsp import FusekiGraphStore


@dataclass(frozen=True)
class Config:
    amqp_uri: str
    fuseki_url: str
    fuseki_dataset: str
    queue: str
    fuseki_user: Optional[str]
    fuseki_password: Optional[str]
    root: Path


def read_config(env: Mapping[str, str]) -> Config:
    amqp_uri = secret(env, "LATTICE_AMQP_URI")
    if not amqp_uri:
        raise ValueError("LATTICE_AMQP_URI is required")
    fuseki_url = env.get("LATTICE_FUSEKI_URL")
    if not fuseki_url:
        raise ValueError("LATTICE_FUSEKI_URL is required")
    return Config(
        amqp_uri=amqp_uri,
        fuseki_url=fuseki_url,
        fuseki_dataset=env.get("LATTICE_FUSEKI_DATASET", "studio"),
        queue=env.get("LATTICE_WORKER_QUEUE") or JOBS_QUEUE,
        fuseki_user=env.get("LATTICE_FUSEKI_USER"),
        fuseki_password=secret(env, "LATTICE_FUSEKI_PASSWORD"),
        root=find_root(env.get("LATTICE_ROOT")),
    )


def _clock() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class PikaSession:
    """A pika blocking connection as the consumer uses it, and the one place the worker touches pika. Every method runs on the connection
    thread. The writes go out on a channel of their own in confirm mode, so a job is finished only once its result is the broker's."""

    LOST = (AMQPConnectionError, ChannelWrongStateError, ChannelClosed, StreamLostError, OSError)

    def __init__(self, uri: str, queue_name: str) -> None:
        self._queue = queue_name
        self._connection = pika.BlockingConnection(pika.URLParameters(uri))
        self._channel = self._connection.channel()
        declare_topology(self._channel, TOPOLOGY)
        self._channel.basic_qos(prefetch_count=1)
        declare_writes(self._channel)
        self._writes = self._connection.channel()
        self._writes.confirm_delivery()

    def consume(self, queue_name: str, on_message) -> None:  # type: ignore[no-untyped-def]
        try:
            self._channel.basic_consume(
                queue=queue_name, on_message_callback=lambda ch, method, properties, body: on_message(method.delivery_tag, body), auto_ack=False,
            )
        except self.LOST as error:
            raise ConnectionLost(str(error)) from error

    def stop_consuming(self) -> None:
        try:
            self._channel.cancel()
        except self.LOST:
            pass

    def process(self, time_limit: float) -> None:
        try:
            self._connection.process_data_events(time_limit=time_limit)
        except self.LOST as error:
            raise ConnectionLost(str(error)) from error

    def publish(self, exchange: str, routing_key: str, headers: dict, body: bytes) -> None:
        # In confirm mode, basic_publish raises if the broker refuses or cannot route the message.
        try:
            self._writes.basic_publish(
                exchange=exchange, routing_key=routing_key, body=body, mandatory=True,
                properties=pika.BasicProperties(content_type="application/n-quads", delivery_mode=2, headers=headers),
            )
        except self.LOST as error:
            raise ConnectionLost(str(error)) from error

    def ack(self, delivery_tag: int) -> None:
        try:
            self._channel.basic_ack(delivery_tag)
        except self.LOST as error:
            raise ConnectionLost(str(error)) from error

    def nack(self, delivery_tag: int, requeue: bool) -> None:
        try:
            self._channel.basic_nack(delivery_tag, requeue=requeue)
        except self.LOST as error:
            raise ConnectionLost(str(error)) from error

    def close(self) -> None:
        if self._connection.is_open:
            self._connection.close()


class _Publisher:
    """The writes of a job thread, made on the connection thread by the consumer."""

    def __init__(self, consumer: Consumer) -> None:
        self._consumer = consumer

    def publish(self, exchange: str, routing_key: str, headers: dict, body: bytes) -> None:
        self._consumer.publish(exchange, routing_key, headers, body)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s", stream=sys.stdout)
    config = read_config(os.environ)
    holder: dict = {}
    consumer = Consumer(lambda: PikaSession(config.amqp_uri, config.queue), config.queue, _Late(holder))
    reader = FusekiGraphStore(config.fuseki_url, config.fuseki_dataset, config.fuseki_user, config.fuseki_password)
    holder["worker"] = ConfigStudioWorker(WriterStore(reader, _Publisher(consumer)), config.root, _clock)

    def _stop(signum: int, frame: object) -> None:
        # The first signal finishes the job in hand and stops consuming, so no job is cut off half written. A second ends the process.
        if consumer.stopping():
            os._exit(1)
        logging.getLogger("lattice_workers.main").info("stopping after the job in hand")
        consumer.stop()

    for name in ("SIGTERM", "SIGINT", "SIGBREAK"):
        if hasattr(signal, name):
            signal.signal(getattr(signal, name), _stop)
    logging.getLogger("lattice_workers.main").info("worker for %s, root %s", config.queue, config.root)
    consumer.run()


class _Late:
    """The consumer's handler, which is the worker once the worker exists: the worker needs the consumer's publisher, and the consumer its handler."""

    def __init__(self, holder: dict) -> None:
        self._holder = holder

    def accept(self, body: bytes) -> str:
        return ConfigStudioWorker.accept(body)

    def handle(self, job_iri: str):  # type: ignore[no-untyped-def]
        return self._holder["worker"].handle(job_iri)

    def fail(self, job_iri: str, message: str) -> None:
        self._holder["worker"].fail(job_iri, message)


if __name__ == "__main__":
    main()
