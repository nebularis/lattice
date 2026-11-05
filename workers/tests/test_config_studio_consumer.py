"""The studio worker's consumer, against a broker that is scripted and not real (plan studio-worker-liveness). A real broker's heartbeat,
confirms and redelivery are driven by `mise run studio:liveness`."""

from __future__ import annotations

import threading
import time
from typing import Callable

import pytest

from lattice_workers.config_studio_consumer import ConnectionLost, Consumer, InvalidMessage

JOB = "urn:lattice:studio:job:00000000-0000-0000-0000-000000000001"
OTHER = "urn:lattice:studio:job:00000000-0000-0000-0000-000000000002"


def wait_for(condition: Callable[[], bool], seconds: float = 5.0) -> None:
    deadline = time.monotonic() + seconds
    while not condition():
        if time.monotonic() > deadline:
            pytest.fail("timed out waiting for the condition")
        time.sleep(0.01)


class FakeBroker:
    """A queue and what a connection does to it. A message delivered and not acknowledged goes back when the connection is lost."""

    def __init__(self) -> None:
        self.ready: list[bytes] = []
        self.unacked: dict[int, bytes] = {}
        self.sessions = 0
        self.refuse = 0
        self.kill = threading.Event()
        self.processed = 0
        self.published: list[tuple[str, str, dict, bytes, str]] = []
        self.settled: list[tuple[str, int]] = []
        self.next_tag = 0
        self.lock = threading.Lock()

    def open(self) -> "FakeSession":
        if self.refuse > 0:
            self.refuse -= 1
            raise OSError("connection refused")
        self.sessions += 1
        return FakeSession(self)


class FakeSession:
    def __init__(self, broker: FakeBroker) -> None:
        self.broker = broker
        self.on_message: Callable[[int, bytes], None] | None = None
        self.holding = False

    def consume(self, queue_name: str, on_message) -> None:  # type: ignore[no-untyped-def]
        self.on_message = on_message

    def stop_consuming(self) -> None:
        self.on_message = None

    def process(self, time_limit: float) -> None:
        broker = self.broker
        broker.processed += 1
        if broker.kill.is_set():
            broker.kill.clear()
            self._lose()
        time.sleep(min(time_limit, 0.01))
        with broker.lock:
            if self.on_message is not None and not self.holding and broker.ready:
                body = broker.ready.pop(0)
                broker.next_tag += 1
                broker.unacked[broker.next_tag] = body
                tag = broker.next_tag
                self.holding = True
            else:
                return
        self.on_message(tag, body)

    def _lose(self) -> None:
        with self.broker.lock:
            self.broker.ready[0:0] = list(self.broker.unacked.values())
            self.broker.unacked.clear()
        raise ConnectionLost("scripted loss")

    def publish(self, exchange: str, routing_key: str, headers: dict, body: bytes) -> None:
        self.broker.published.append((exchange, routing_key, headers, body, threading.current_thread().name))

    def ack(self, delivery_tag: int) -> None:
        self._settle("ack", delivery_tag)

    def nack(self, delivery_tag: int, requeue: bool) -> None:
        self._settle("requeue" if requeue else "reject", delivery_tag)

    def _settle(self, how: str, tag: int) -> None:
        with self.broker.lock:
            body = self.broker.unacked.pop(tag, None)
            if how == "requeue" and body is not None:
                self.broker.ready.insert(0, body)
        self.broker.settled.append((how, tag))
        self.holding = False

    def close(self) -> None:
        pass


class Handler:
    """The worker, as far as the consumer sees it. `script` says what a job does, on the job's thread."""

    def __init__(self, script: Callable[["Handler", str], object] | None = None) -> None:
        self.script = script or (lambda handler, iri: "ok")
        self.handled: list[tuple[str, str]] = []
        self.failed: list[tuple[str, str]] = []
        self.release = threading.Event()
        self.consumer: Consumer | None = None

    def accept(self, body: bytes) -> str:
        text = body.decode()
        if not text.startswith("urn:lattice:studio:job:"):
            raise InvalidMessage("not a job")
        return text

    def handle(self, iri: str):  # type: ignore[no-untyped-def]
        self.handled.append((iri, threading.current_thread().name))
        return self.script(self, iri)

    def fail(self, iri: str, message: str) -> None:
        self.failed.append((iri, message))


def started(broker: FakeBroker, handler: Handler, **options) -> tuple[Consumer, threading.Thread]:  # type: ignore[no-untyped-def]
    consumer = Consumer(broker.open, "lattice.studio.jobs", handler, poll=0.01, backoff=(0.01,), sleep=lambda s: time.sleep(0.001), **options)
    handler.consumer = consumer
    thread = threading.Thread(target=consumer.run, name="connection", daemon=True)
    thread.start()
    return consumer, thread


def stopped(consumer: Consumer, thread: threading.Thread) -> None:
    consumer.stop()
    thread.join(timeout=5)
    assert not thread.is_alive(), "the consumer did not end"


def test_a_job_runs_on_a_thread_of_its_own_while_the_connection_goes_on_answering_the_broker():
    broker, handler = FakeBroker(), Handler(lambda h, iri: h.release.wait(10))
    broker.ready.append(JOB.encode())
    consumer, thread = started(broker, handler)
    wait_for(lambda: handler.handled)
    assert handler.handled[0][1] == "job"
    before = broker.processed
    wait_for(lambda: broker.processed > before + 20)
    assert broker.settled == [], "the job is not finished, so it is not acknowledged"
    handler.release.set()
    wait_for(lambda: broker.settled == [("ack", 1)])
    stopped(consumer, thread)


def test_a_result_is_published_on_the_connection_thread_and_the_job_acknowledged_after_it():
    def script(handler, iri):
        handler.consumer.publish("lattice.studio.writes", "3", {"id": "c1"}, b"quads")
        return "wrote"

    broker, handler = FakeBroker(), Handler(script)
    broker.ready.append(JOB.encode())
    consumer, thread = started(broker, handler)
    wait_for(lambda: broker.settled)
    assert broker.published == [("lattice.studio.writes", "3", {"id": "c1"}, b"quads", "connection")]
    assert broker.settled == [("ack", 1)]
    stopped(consumer, thread)


@pytest.mark.parametrize("body", [b"urn:lattice:studio:ws:1", b"nonsense"])
def test_a_message_that_is_not_a_job_is_rejected_without_requeue_and_the_next_is_served(body):
    broker, handler = FakeBroker(), Handler()
    broker.ready.extend([body, JOB.encode()])
    consumer, thread = started(broker, handler)
    wait_for(lambda: len(broker.settled) == 2)
    assert broker.settled == [("reject", 1), ("ack", 2)]
    assert [iri for iri, _ in handler.handled] == [JOB]
    stopped(consumer, thread)


def test_a_job_the_worker_refuses_is_rejected_without_requeue_and_is_not_marked_failed():
    def script(handler, iri):
        raise InvalidMessage("the job names no workspace")

    broker, handler = FakeBroker(), Handler(script)
    broker.ready.extend([JOB.encode(), OTHER.encode()])
    consumer, thread = started(broker, handler)
    wait_for(lambda: len(broker.settled) == 2)
    assert broker.settled == [("reject", 1), ("reject", 2)]
    assert handler.failed == []
    stopped(consumer, thread)


def test_a_job_that_raises_is_marked_failed_and_rejected_so_the_queue_moves_on_and_the_worker_stays():
    def script(handler, iri):
        if iri == JOB:
            raise OSError("the store is down")
        return "ok"

    broker, handler = FakeBroker(), Handler(script)
    broker.ready.extend([JOB.encode(), OTHER.encode()])
    consumer, thread = started(broker, handler)
    wait_for(lambda: len(broker.settled) == 2)
    assert broker.settled == [("reject", 1), ("ack", 2)]
    assert len(handler.failed) == 1 and handler.failed[0][0] == JOB and "OSError" in handler.failed[0][1]
    assert thread.is_alive()
    stopped(consumer, thread)


def test_stopping_finishes_the_job_in_hand_takes_no_other_and_ends():
    broker, handler = FakeBroker(), Handler(lambda h, iri: h.release.wait(10))
    broker.ready.extend([JOB.encode(), OTHER.encode()])
    consumer, thread = started(broker, handler)
    wait_for(lambda: handler.handled)
    consumer.stop()
    time.sleep(0.2)
    assert thread.is_alive(), "it ended with a job in hand"
    handler.release.set()
    thread.join(timeout=5)
    assert not thread.is_alive()
    assert broker.settled == [("ack", 1)]
    assert [iri for iri, _ in handler.handled] == [JOB]


def test_a_broker_that_refuses_the_connection_is_tried_again_until_it_does_not():
    broker, handler = FakeBroker(), Handler()
    broker.refuse = 3
    delays: list[float] = []
    consumer = Consumer(broker.open, "q", handler, poll=0.01, backoff=(1.0, 2.0, 5.0), sleep=delays.append)
    broker.ready.append(JOB.encode())
    thread = threading.Thread(target=consumer.run, daemon=True)
    thread.start()
    wait_for(lambda: broker.settled)
    assert delays == [1.0, 2.0, 5.0]
    stopped(consumer, thread)


def test_a_lost_connection_does_not_stop_the_job_and_its_redelivery_is_taken_for_the_job_in_hand():
    broker, handler = FakeBroker(), Handler(lambda h, iri: h.release.wait(10))
    broker.ready.append(JOB.encode())
    consumer, thread = started(broker, handler)
    wait_for(lambda: handler.handled)
    broker.kill.set()
    wait_for(lambda: broker.sessions == 2)
    # The broker has the message again and delivers it to the second connection.
    wait_for(lambda: 2 in broker.unacked)
    time.sleep(0.1)
    assert [iri for iri, _ in handler.handled] == [JOB], "the redelivered job was started a second time"
    handler.release.set()
    wait_for(lambda: broker.settled == [("ack", 2)])
    assert thread.is_alive()
    stopped(consumer, thread)


def test_a_job_finished_while_the_connection_was_down_is_acknowledged_when_the_broker_delivers_it_again():
    script_calls: list[str] = []

    def script(handler, iri):
        script_calls.append(iri)
        if len(script_calls) == 1:
            handler.release.wait(10)
            return "wrote"
        return "already finished"  # what the worker does for a job the store holds as finished

    broker, handler = FakeBroker(), Handler(script)
    broker.ready.append(JOB.encode())
    broker.refuse = 0
    consumer, thread = started(broker, handler)
    wait_for(lambda: handler.handled)
    broker.refuse = 10**6
    broker.kill.set()
    wait_for(lambda: broker.ready)
    handler.release.set()
    wait_for(lambda: consumer._job is None)
    assert broker.settled == [], "a tag from the lost connection was used"
    broker.refuse = 0
    wait_for(lambda: broker.settled)
    assert broker.settled == [("ack", 2)]
    assert len(script_calls) == 2
    stopped(consumer, thread)


def test_a_result_published_while_the_connection_is_down_waits_for_the_next_one_and_is_sent_once():
    sent = threading.Event()

    def script(handler, iri):
        handler.release.wait(10)
        handler.consumer.publish("lattice.studio.writes", "3", {"id": "c1"}, b"quads")
        sent.set()
        return "wrote"

    broker, handler = FakeBroker(), Handler(script)
    broker.ready.append(JOB.encode())
    consumer, thread = started(broker, handler)
    wait_for(lambda: handler.handled)
    broker.refuse = 10**6
    broker.kill.set()
    wait_for(lambda: not consumer._connected.is_set())
    handler.release.set()
    time.sleep(0.3)
    assert broker.published == [] and not sent.is_set(), "the result was published with no connection"
    broker.refuse = 0
    wait_for(sent.is_set)
    assert [p[:4] for p in broker.published] == [("lattice.studio.writes", "3", {"id": "c1"}, b"quads")]
    wait_for(lambda: broker.settled)
    stopped(consumer, thread)


def test_each_job_is_logged_when_it_ends_with_its_duration_and_what_became_of_it(caplog):
    broker, handler = FakeBroker(), Handler(lambda h, iri: "Validate Persistence succeeded")
    broker.ready.append(JOB.encode())
    with caplog.at_level("INFO", logger="lattice_workers.consumer"):
        consumer, thread = started(broker, handler)
        wait_for(lambda: broker.settled)
        stopped(consumer, thread)
    ended = [r.message for r in caplog.records if " ended in " in r.message]
    assert len(ended) == 1 and JOB in ended[0] and "Validate Persistence succeeded" in ended[0]
