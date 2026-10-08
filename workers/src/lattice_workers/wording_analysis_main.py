"""Entry point for the wording analysis worker: `python -m lattice_workers.wording_analysis_main`."""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Mapping, Optional

import pika
from pika.exceptions import AMQPConnectionError

from .fuseki_gsp import FusekiGraphStore
from .wording_analysis_worker import (
    TOPOLOGY,
    REQUESTED_QUEUE,
    RabbitMqResultPublisher,
    RabbitMqWordingAnalysisWorker,
    WordingAnalysisConsumer,
    declare_topology,
)
from .wording_le.forms import load_profile

_RECONNECT_INTERVAL_SECONDS = 2


@dataclass(frozen=True)
class Config:
    amqp_uri: str
    fuseki_url: str
    fuseki_dataset: str
    fuseki_user: Optional[str]
    fuseki_password: Optional[str]


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
        fuseki_dataset=env.get("LATTICE_FUSEKI_DATASET", "authoring"),
        fuseki_user=env.get("LATTICE_FUSEKI_USER"),
        fuseki_password=env.get("LATTICE_FUSEKI_PASSWORD"),
    )


def _clock() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


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
    publisher = RabbitMqResultPublisher(channel, pika.BasicProperties)
    consumer = WordingAnalysisConsumer(store, publisher, load_profile(), _clock)
    worker = RabbitMqWordingAnalysisWorker(consumer)

    def _on_message(ch: object, method: object, properties: object, body: bytes) -> None:
        worker.handle(channel, method.delivery_tag, body)

    channel.basic_consume(queue=REQUESTED_QUEUE, on_message_callback=_on_message, auto_ack=False)
    channel.start_consuming()


if __name__ == "__main__":
    main()
