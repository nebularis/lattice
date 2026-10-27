"""Entry point for the Configuration Studio worker: `python -m lattice_workers.config_studio_main`."""

from __future__ import annotations

import os
import signal
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping, Optional

import pika
from pika.exceptions import AMQPConnectionError

from .config_studio_jobs import find_root
from .config_studio_worker import JOBS_QUEUE, TOPOLOGY, ConfigStudioWorker, RabbitMqConfigStudioWorker
from .fuseki_gsp import FusekiGraphStore
from .wording_analysis_worker import declare_topology

_RECONNECT_INTERVAL_SECONDS = 2


@dataclass(frozen=True)
class Config:
    amqp_uri: str
    fuseki_url: str
    fuseki_dataset: str
    fuseki_user: Optional[str]
    fuseki_password: Optional[str]
    root: Path


def read_config(env: Mapping[str, str]) -> Config:
    amqp_uri = env.get("LATTICE_AMQP_URI")
    if not amqp_uri:
        raise ValueError("LATTICE_AMQP_URI is required")
    fuseki_url = env.get("LATTICE_FUSEKI_URL")
    if not fuseki_url:
        raise ValueError("LATTICE_FUSEKI_URL is required")
    return Config(
        amqp_uri=amqp_uri,
        fuseki_url=fuseki_url,
        fuseki_dataset=env.get("LATTICE_FUSEKI_DATASET", "studio"),
        fuseki_user=env.get("LATTICE_FUSEKI_USER"),
        fuseki_password=env.get("LATTICE_FUSEKI_PASSWORD"),
        root=find_root(env.get("LATTICE_ROOT")),
    )


def _clock() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _connect(uri: str) -> pika.BlockingConnection:
    while True:
        try:
            return pika.BlockingConnection(pika.URLParameters(uri))
        except AMQPConnectionError:
            time.sleep(_RECONNECT_INTERVAL_SECONDS)


def main() -> None:
    config = read_config(os.environ)
    connection = _connect(config.amqp_uri)
    channel = connection.channel()
    declare_topology(channel, TOPOLOGY)
    channel.basic_qos(prefetch_count=1)

    store = FusekiGraphStore(config.fuseki_url, config.fuseki_dataset, config.fuseki_user, config.fuseki_password)
    worker = RabbitMqConfigStudioWorker(ConfigStudioWorker(store, config.root, _clock))

    def _on_message(ch: object, method: object, properties: object, body: bytes) -> None:
        worker.handle(channel, method.delivery_tag, body)

    def _stop(signum: int, frame: object) -> None:
        # Finishes the job in hand, then stops consuming, so no job is cut off half written.
        connection.add_callback_threadsafe(channel.stop_consuming)

    for name in ("SIGTERM", "SIGINT", "SIGBREAK"):
        if hasattr(signal, name):
            signal.signal(getattr(signal, name), _stop)

    channel.basic_consume(queue=JOBS_QUEUE, on_message_callback=_on_message, auto_ack=False)
    channel.start_consuming()
    connection.close()


if __name__ == "__main__":
    main()
