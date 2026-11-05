"""The Configuration Studio worker's consumer: one thread that owns the broker connection, and a thread for each job (plan studio-worker-liveness).

Pika's blocking connection answers the broker's heartbeats only while its own thread is inside the library, so a job run on that thread
for longer than the broker's timeout loses the connection. Here the connection thread does nothing but `process`, which answers heartbeats
and delivers messages, and runs every call a job thread asks of it: a publish, which waits for the broker's confirm, and an acknowledgement.
A job thread never touches the connection. A connection that is lost while a job runs does not stop the job: the connection thread opens
another, the broker delivers the job's message again, and the consumer recognises it as the job in hand and takes its new delivery tag.
A call the job thread made while the connection was down waits for the next one and is made again, so a finished result is held until it
is published. The command carries its id, so the writer applies a result that was published twice once.

The broker is reached through a `BrokerSession`, so the rules here are tested without a broker (`tests/test_config_studio_consumer.py`),
and against one by `mise run studio:liveness`.
"""

from __future__ import annotations

import logging
import queue
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Optional, Protocol

LOG = logging.getLogger("lattice_workers.consumer")


class ConnectionLost(Exception):
    """The broker connection, or the channel a call needed, is gone."""


class InvalidMessage(ValueError):
    """The message is not a job this worker can read. It is refused without requeuing."""


class BrokerSession(Protocol):
    """One live connection. Every method is called on the connection thread, and only there."""

    def consume(self, queue_name: str, on_message: Callable[[int, bytes], None]) -> None:
        """Starts delivering the queue's messages, one unacknowledged at a time, to `on_message(delivery_tag, body)`."""

    def stop_consuming(self) -> None:
        """Stops delivery. A message already delivered stays unacknowledged until it is acknowledged here."""

    def process(self, time_limit: float) -> None:
        """Answers the broker's heartbeats and delivers messages for up to `time_limit` seconds. Raises `ConnectionLost`."""

    def publish(self, exchange: str, routing_key: str, headers: dict, body: bytes) -> None:
        """Publishes persistently and returns once the broker has confirmed. Raises `ConnectionLost`."""

    def ack(self, delivery_tag: int) -> None:
        ...

    def nack(self, delivery_tag: int, requeue: bool) -> None:
        ...

    def close(self) -> None:
        ...


class JobHandler(Protocol):
    def accept(self, body: bytes) -> str:
        """The job IRI the message names, or `InvalidMessage`."""

    def handle(self, job_iri: str) -> Any:
        """Runs the job and writes its result through the publisher. Raises `InvalidMessage` for a job that cannot be written."""

    def fail(self, job_iri: str, message: str) -> None:
        """Marks an unfinished job `Failed` with `message`, if it is not finished."""


@dataclass
class _Call:
    function: Callable[[BrokerSession], Any]
    done: threading.Event = field(default_factory=threading.Event)
    result: Any = None
    error: Optional[BaseException] = None


@dataclass
class _Job:
    iri: str
    tag: int
    generation: int
    thread: Optional[threading.Thread] = None


class Consumer:
    """Consumes one queue. `run` blocks on the thread that calls it, which is the connection thread."""

    def __init__(
        self, open_session: Callable[[], BrokerSession], queue_name: str, handler: JobHandler,
        poll: float = 0.25, backoff: tuple[float, ...] = (1.0, 2.0, 5.0, 10.0), sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._open = open_session
        self._queue = queue_name
        self._handler = handler
        self._poll = poll
        self._backoff = backoff
        self._sleep = sleep
        self._calls: "queue.Queue[_Call]" = queue.Queue()
        self._connected = threading.Event()
        self._stopping = threading.Event()
        self._lock = threading.Lock()
        self._generation = 0
        self._job: Optional[_Job] = None
        self._session: Optional[BrokerSession] = None

    # --- the connection thread ---------------------------------------------------------------

    def run(self) -> None:
        """Serves until `stop`, then until the job in hand has finished."""
        attempt = 0
        while not self._finished():
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
                LOG.warning("the broker connection was lost (%s)%s", error, ", the job in hand goes on" if self._job else "")
            finally:
                self._connected.clear()
                self._session = None
                try:
                    session.close()
                except Exception:  # the connection is already gone
                    pass
                self._fail_waiting_calls()
        job = self._job
        if job is not None and job.thread is not None:
            job.thread.join()

    def _finished(self) -> bool:
        return self._stopping.is_set() and self._job is None

    def _serve(self, session: BrokerSession) -> None:
        with self._lock:
            self._generation += 1
        self._session = session
        consuming = False
        if not self._stopping.is_set():
            session.consume(self._queue, lambda tag, body: self._on_message(session, tag, body))
            consuming = True
        self._connected.set()
        LOG.info("consuming %s", self._queue)
        while True:
            session.process(self._poll)
            self._drain(session)
            if self._stopping.is_set():
                if consuming:
                    session.stop_consuming()
                    consuming = False
                if self._job is None:
                    return

    def _drain(self, session: BrokerSession) -> None:
        while True:
            try:
                call = self._calls.get_nowait()
            except queue.Empty:
                return
            try:
                call.result = call.function(session)
            except BaseException as error:  # handed to the thread that asked
                call.error = error
            call.done.set()
            if isinstance(call.error, ConnectionLost):
                raise call.error

    def _fail_waiting_calls(self) -> None:
        while True:
            try:
                call = self._calls.get_nowait()
            except queue.Empty:
                return
            call.error = ConnectionLost("the connection closed before the call was made")
            call.done.set()

    def _on_message(self, session: BrokerSession, tag: int, body: bytes) -> None:
        try:
            iri = self._handler.accept(body)
        except InvalidMessage as error:
            LOG.warning("refused a message that is not a job: %s", error)
            session.nack(tag, False)
            return
        with self._lock:
            generation = self._generation
            job = self._job
            if job is not None and job.iri == iri:
                # The broker delivers again the job this worker still runs, after a lost connection. Its result goes on this tag.
                job.tag, job.generation = tag, generation
                LOG.info("%s was delivered again while it runs here, and goes on", iri)
                return
            if job is not None or self._stopping.is_set():
                session.nack(tag, True)
                return
            job = self._job = _Job(iri, tag, generation)
        job.thread = threading.Thread(target=self._run_job, args=(job,), name="job", daemon=False)
        job.thread.start()

    # --- the job thread ----------------------------------------------------------------------

    def _run_job(self, job: _Job) -> None:
        started = time.monotonic()
        outcome: tuple[str, bool] = ("ack", False)
        try:
            handled = self._handler.handle(job.iri)
            LOG.info("%s ended in %.1f s: %s", job.iri, time.monotonic() - started, handled)
        except InvalidMessage as error:
            LOG.warning("%s was refused after %.1f s: %s", job.iri, time.monotonic() - started, error)
            outcome = ("nack", False)
        except Exception as error:  # the job could not be run or its result could not be written, and trying again would repeat it
            LOG.exception("%s failed after %.1f s", job.iri, time.monotonic() - started)
            try:
                self._handler.fail(job.iri, f"the worker could not run the job: {type(error).__name__}: {error}")
            except Exception:
                LOG.exception("%s could not be marked failed", job.iri)
            outcome = ("nack", False)
        self._settle(job, outcome)

    def _settle(self, job: _Job, outcome: tuple[str, bool]) -> None:
        """Acknowledges or rejects on the tag the job now holds, then lets the next one in. A tag from a connection since lost is
        not used: the broker has the message again, and the worker finds the job finished and acknowledges that."""
        def settle(session: BrokerSession) -> None:
            with self._lock:
                valid = job.generation == self._generation
                tag = job.tag
                self._job = None
            if valid:
                (session.ack(tag) if outcome[0] == "ack" else session.nack(tag, outcome[1]))

        if self._connected.is_set():
            try:
                self._call(settle, retry=False)
                return
            except ConnectionLost:
                pass
        with self._lock:
            self._job = None

    # --- calls from a job thread -------------------------------------------------------------

    def _call(self, function: Callable[[BrokerSession], Any], retry: bool = True) -> Any:
        """Runs `function` on the connection thread and returns what it returned. While the connection is down, with `retry`, waits for
        the next one and runs it again."""
        while True:
            if not self._connected.wait(timeout=None if retry else 0):
                raise ConnectionLost("not connected")
            call = _Call(function)
            self._calls.put(call)
            call.done.wait()
            if isinstance(call.error, ConnectionLost):
                if retry:
                    time.sleep(0.05)
                    continue
                raise call.error
            if call.error is not None:
                raise call.error
            return call.result

    def publish(self, exchange: str, routing_key: str, headers: dict, body: bytes) -> None:
        """For a job thread: publishes and returns once the broker has confirmed, waiting out a lost connection."""
        self._call(lambda session: session.publish(exchange, routing_key, headers, body))

    def stopping(self) -> bool:
        return self._stopping.is_set()

    def stop(self) -> None:
        """Stops taking jobs and ends `run` when the job in hand has finished. Safe from a signal handler or another thread."""
        self._stopping.set()
