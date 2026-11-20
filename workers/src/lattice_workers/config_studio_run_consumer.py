# SPDX-License-Identifier: MPL-2.0
"""The consumer of the queue of RDF sample runs (ADR-A154, addendum of 2026-11-20, decision 3), and the one place of this run worker that touches pika.

It owns a connection of its own and a channel for the queue, taking at most `concurrency` runs at once, each handled on a thread of a pool of
that size. The jobs queue is consumed on another connection by another thread, so a sample run never holds the worker's jobs. A handler
returns what to do with its message, and the message is acknowledged or rejected only afterwards, on the connection's thread, so after the
handler published what it publishes. The frames go out on a channel of their own in confirm mode, and a frame the broker did not confirm fails
the run's publish, which leaves the message unacknowledged for the broker to redeliver, and a worker then says the run was lost (decision 7).

Pika's blocking connection is not safe for use from two threads. Every call on it is made on the thread that runs `run`, which a handler
thread asks for through `Session.call` and waits for. A connection that is lost does not stop the consumer: it opens another with a back-off.
A run in hand when the connection goes cannot publish or settle on it, and the broker delivers its message again with the redelivered flag.
The broker is reached through a `Session`, so the rules here are tested without one (`tests/test_config_studio_run_consumer.py`)."""

from __future__ import annotations

import logging
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Any, Callable, Protocol

import pika
from pika.exceptions import AMQPConnectionError, ChannelClosed, ChannelWrongStateError, ConnectionWrongStateError, StreamLostError

from .config_studio_consumer import ConnectionLost
from .config_studio_runs import FrameSink, Message, Outcome, RdfRunWorker
from .config_studio_worker import TOPOLOGY, declare_topology

LOG = logging.getLogger("lattice_workers.run_consumer")

EVENTS_EXCHANGE = "lattice.studio.events"
FRAME_TYPE = "org.nebularis.lattice.studio.run.frame"
SOURCE = "urn:lattice:studio:run-worker"
RDF_RUNS_QUEUE = "lattice.studio.runs.rdf"
CONCURRENCY_SETTING = "LATTICE_RUNS_RDF_CONCURRENCY"
DEFAULT_CONCURRENCY = 2
# How long a thread waits for the connection's thread to make a call, which is a publish the broker confirms or an acknowledgement.
CALL_SECONDS = 30.0


def concurrency(env: dict[str, str] | Any) -> int:
    """The runs handled at once, from the setting, at least 1."""
    value = env.get(CONCURRENCY_SETTING)
    if value is None or not value.strip():
        return DEFAULT_CONCURRENCY
    try:
        n = int(value.strip())
        if n >= 1:
            return n
    except ValueError:
        pass
    raise ValueError(f"{CONCURRENCY_SETTING} is a whole number from 1")


class Session(Protocol):
    """One live connection. Every method but `call` is called on the connection's thread, and only there."""

    def consume(self, queue_name: str, on_message: Callable[[Message], None]) -> None:
        """Starts delivering the queue's messages, at most the concurrency unacknowledged at once."""

    def stop_consuming(self) -> None:
        ...

    def process(self, time_limit: float) -> None:
        """Answers the broker's heartbeats and delivers messages for up to `time_limit` seconds. Raises `ConnectionLost`."""

    def call(self, function: Callable[[], Any]) -> Any:
        """Called from any thread. Runs `function` on the connection's thread and returns what it returns or raises what it raises, or raises
        `ConnectionLost` when the connection is gone before it ran."""

    def publish_frames(self, run: str, frames: list[str]) -> None:
        """Publishes each frame to the events exchange as a CloudEvent, in order, and returns once the broker has confirmed them all."""

    def ack(self, tag: int) -> None:
        ...

    def reject(self, tag: int, requeue: bool) -> None:
        ...

    def close(self) -> None:
        ...


class _SessionSink:
    """The sink of the runs of one session's messages. A run publishes on the connection its message came from and no other, so a run
    whose connection was lost cannot publish its frames on a new one and then be delivered again and said to be lost."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def publish(self, run: str, frames: list[str]) -> None:
        self._session.call(lambda: self._session.publish_frames(run, frames))


class RunConsumer:
    """Consumes the queue of RDF sample runs. `run` blocks on the thread that calls it, which is the connection's thread."""

    def __init__(
        self, open_session: Callable[[], Session], queue_name: str, worker: RdfRunWorker, concurrency: int = DEFAULT_CONCURRENCY,
        poll: float = 0.25, backoff: tuple[float, ...] = (1.0, 2.0, 5.0, 10.0), sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._open = open_session
        self._queue = queue_name
        self._worker = worker
        self._poll = poll
        self._backoff = backoff
        self._sleep = sleep
        self._pool = ThreadPoolExecutor(max_workers=concurrency, thread_name_prefix="rdf-runs")
        self._stopping = threading.Event()
        self._lock = threading.Lock()
        self._idle = threading.Condition(self._lock)
        self._handling = 0

    def stop(self) -> None:
        """Stops consuming. The runs in hand finish, each by its deadline at the latest, and then `run` returns."""
        self._stopping.set()

    def stopping(self) -> bool:
        return self._stopping.is_set()

    def run(self) -> None:
        attempt = 0
        while not self._stopping.is_set():
            try:
                session = self._open()
            except Exception as error:  # the broker is not reachable yet, or refused us
                delay = self._backoff[min(attempt, len(self._backoff) - 1)]
                attempt += 1
                LOG.warning("the broker is not reachable (%s), trying again in %.0f s", error, delay)
                self._sleep(delay)
                continue
            attempt = 0
            try:
                self._serve(session)
            except ConnectionLost as error:
                LOG.warning("the broker connection was lost (%s)", error)
                if not self._stopping.is_set():
                    self._sleep(self._backoff[0])
            finally:
                try:
                    session.close()
                except Exception:  # the connection is already gone
                    pass
        with self._idle:
            self._idle.wait_for(lambda: self._handling == 0)
        self._pool.shutdown(wait=True)

    def _serve(self, session: Session) -> None:
        session.consume(self._queue, lambda message: self._deliver(session, message))
        while not self._stopping.is_set():
            session.process(self._poll)
        session.stop_consuming()
        # A run in hand finishes and settles on this connection first, which needs the connection's thread to go on serving calls.
        while self._in_hand():
            session.process(self._poll)

    def _in_hand(self) -> int:
        with self._lock:
            return self._handling

    def _deliver(self, session: Session, message: Message) -> None:
        """Hands the delivery to the pool and returns at once, so the connection's thread is free for the next."""
        with self._lock:
            self._handling += 1
        try:
            self._pool.submit(self._work, session, message)
        except RuntimeError:
            self._done()

    def _work(self, session: Session, message: Message) -> None:
        try:
            try:
                outcome = self._worker.handle(message, _SessionSink(session))
            except Exception:
                # The message and what it says are not logged. The service sends the run's failed frame at its deadline.
                LOG.error("handling a message of %s failed", self._queue, exc_info=True)
                outcome = Outcome.REJECT
            try:
                if outcome is Outcome.ACK:
                    session.call(lambda: session.ack(message.tag))
                else:
                    session.call(lambda: session.reject(message.tag, outcome is Outcome.REQUEUE))
            except Exception:
                LOG.warning("settling a message of %s failed", self._queue, exc_info=True)
        finally:
            self._done()

    def _done(self) -> None:
        with self._idle:
            self._handling -= 1
            self._idle.notify_all()


class PikaSession:
    """A pika blocking connection as the consumer uses it."""

    LOST = (AMQPConnectionError, ChannelWrongStateError, ChannelClosed, StreamLostError, ConnectionWrongStateError, OSError)

    def __init__(
        self, uri: str, queue_name: str, prefetch: int, clock: Callable[[], datetime], ids: Callable[[], uuid.UUID] = uuid.uuid4,
    ) -> None:
        parameters = pika.URLParameters(uri)
        # Named, as the Java components name theirs, so the broker's own tools show which connection is the run consumer's, and apart from the
        # jobs consumer's, which a tool that closes a worker's connection by name must not close with it.
        parameters.client_properties = {"connection_name": f"config-studio-rdf-runs {queue_name}"}
        self._connection = pika.BlockingConnection(parameters)
        self._clock = clock
        self._ids = ids
        self._channel = self._connection.channel()
        declare_topology(self._channel, TOPOLOGY)
        self._channel.basic_qos(prefetch_count=prefetch)
        # The frames go out on a channel of their own, in confirm mode, so a run is finished only once its frames are the broker's.
        self._frames = self._connection.channel()
        self._frames.exchange_declare(exchange=EVENTS_EXCHANGE, exchange_type="topic", durable=True)
        self._frames.confirm_delivery()

    def consume(self, queue_name: str, on_message: Callable[[Message], None]) -> None:
        def deliver(channel: Any, method: Any, properties: Any, body: bytes) -> None:
            on_message(Message(method.delivery_tag, bool(method.redelivered), dict(properties.headers or {}), properties.content_type, body))

        try:
            self._channel.basic_consume(queue=queue_name, on_message_callback=deliver, auto_ack=False)
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

    def call(self, function: Callable[[], Any]) -> Any:
        done = threading.Event()
        held: dict[str, Any] = {}

        def on_thread() -> None:
            try:
                held["value"] = function()
            except BaseException as error:  # handed to the caller's thread
                held["error"] = error
            finally:
                done.set()

        try:
            self._connection.add_callback_threadsafe(on_thread)
        except self.LOST as error:
            raise ConnectionLost(str(error)) from error
        waited = 0.0
        while not done.wait(0.5):
            waited += 0.5
            if self._connection.is_closed or waited >= CALL_SECONDS:
                raise ConnectionLost("the connection closed, or did not make the call in time")
        if "error" in held:
            raise held["error"]
        return held.get("value")

    def publish_frames(self, run: str, frames: list[str]) -> None:
        # In confirm mode, basic_publish returns once the broker has confirmed the message and raises if it refused it.
        try:
            for frame in frames:
                event = str(self._ids())
                now = self._clock().astimezone(timezone.utc)
                headers = {
                    "cloudEvents:specversion": "1.0", "cloudEvents:id": event, "cloudEvents:source": SOURCE, "cloudEvents:type": FRAME_TYPE,
                    "cloudEvents:subject": run, "cloudEvents:time": now.strftime("%Y-%m-%dT%H:%M:%S.") + f"{now.microsecond:06d}Z",
                }
                self._frames.basic_publish(
                    exchange=EVENTS_EXCHANGE, routing_key=FRAME_TYPE, body=frame.encode("utf-8"),
                    properties=pika.BasicProperties(content_type="application/json", headers=headers, message_id=event, type=FRAME_TYPE, delivery_mode=2),
                )
        except self.LOST as error:
            raise ConnectionLost(str(error)) from error

    def ack(self, tag: int) -> None:
        try:
            self._channel.basic_ack(tag)
        except self.LOST as error:
            raise ConnectionLost(str(error)) from error

    def reject(self, tag: int, requeue: bool) -> None:
        try:
            self._channel.basic_nack(tag, requeue=requeue)
        except self.LOST as error:
            raise ConnectionLost(str(error)) from error

    def close(self) -> None:
        if self._connection.is_open:
            self._connection.close()


def start(
    uri: str, worker: RdfRunWorker, concurrency_: int, clock: Callable[[], datetime],
) -> tuple[RunConsumer, threading.Thread]:
    """Starts the consumer of the queue of RDF sample runs on a thread of its own, and returns both."""
    consumer = RunConsumer(lambda: PikaSession(uri, RDF_RUNS_QUEUE, concurrency_, clock), RDF_RUNS_QUEUE, worker, concurrency_)
    thread = threading.Thread(target=consumer.run, name="rdf-runs-consumer")
    thread.start()
    return consumer, thread
