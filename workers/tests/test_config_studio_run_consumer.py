"""The consumer of the queue of RDF sample runs, against a broker that is scripted and not real (ADR-A154, addendum of 2026-11-20). A real
broker's confirms, redelivery and prefetch are driven by `test/studio-integration/test_runs.py`."""

from __future__ import annotations

import json
import threading
import time
from datetime import datetime, timezone
from queue import Empty, Queue
from typing import Any, Callable

import pytest

from lattice_workers import config_studio_run_consumer as consumer
from lattice_workers.config_studio_consumer import ConnectionLost
from lattice_workers.config_studio_run_consumer import PikaSession, RunConsumer, concurrency
from lattice_workers.config_studio_runs import Message, Outcome
from lattice_workers.config_studio_worker import TOPOLOGY


def wait_for(condition: Callable[[], bool], seconds: float = 5.0) -> None:
    deadline = time.monotonic() + seconds
    while not condition():
        if time.monotonic() > deadline:
            pytest.fail("timed out waiting for the condition")
        time.sleep(0.005)


class Broker:
    """One queue. A message delivered and not settled goes back, marked redelivered, when its connection is lost. At most `prefetch` messages are
    unsettled on a connection."""

    def __init__(self, prefetch: int = 2) -> None:
        self.prefetch = prefetch
        self.ready: list[Message] = []
        self.unsettled: dict[int, Message] = {}
        self.log: list[tuple] = []
        self.sessions: list[Session] = []
        self.refuse = 0
        self.lock = threading.Lock()
        self.confirm_fails = 0

    def put(self, tag: int, body: bytes = b"", redelivered: bool = False) -> None:
        self.ready.append(Message(tag, redelivered, {}, "text/turtle", body))

    def open(self) -> "Session":
        if self.refuse:
            self.refuse -= 1
            raise OSError("connection refused")
        session = Session(self)
        self.sessions.append(session)
        return session


class Session:
    def __init__(self, broker: Broker) -> None:
        self.broker = broker
        self.calls: "Queue[tuple[Callable[[], Any], threading.Event, dict]]" = Queue()
        self.on_message: Callable[[Message], None] | None = None
        self.mine: set[int] = set()
        self.lost = False
        self.closed = False
        self.consuming = False

    def consume(self, queue_name: str, on_message: Callable[[Message], None]) -> None:
        self.on_message = on_message
        self.consuming = True
        self.broker.log.append(("consume", queue_name))

    def stop_consuming(self) -> None:
        self.consuming = False

    def process(self, time_limit: float) -> None:
        if self.lost:
            raise ConnectionLost("gone")
        end = time.monotonic() + min(time_limit, 0.02)
        while time.monotonic() < end:
            try:
                function, done, held = self.calls.get(timeout=0.005)
            except Empty:
                function = None
            if function is not None:
                try:
                    held["value"] = function()
                except BaseException as error:
                    held["error"] = error
                done.set()
            with self.broker.lock:
                while self.consuming and self.broker.ready and len(self.broker.unsettled) < self.broker.prefetch:
                    message = self.broker.ready.pop(0)
                    self.broker.unsettled[message.tag] = message
                    self.mine.add(message.tag)
                    assert self.on_message is not None
                    self.on_message(message)

    def call(self, function: Callable[[], Any]) -> Any:
        if self.lost or self.closed:
            raise ConnectionLost("gone")
        done, held = threading.Event(), {}
        self.calls.put((function, done, held))
        if not done.wait(5):
            raise ConnectionLost("not made")
        if "error" in held:
            raise held["error"]
        return held.get("value")

    def publish_frames(self, run: str, frames: list[str]) -> None:
        if self.broker.confirm_fails:
            self.broker.confirm_fails -= 1
            raise ConnectionLost("not confirmed")
        self.broker.log.append(("publish", run, tuple(frames)))

    def ack(self, tag: int) -> None:
        with self.broker.lock:
            self.broker.unsettled.pop(tag)
        self.broker.log.append(("ack", tag))

    def reject(self, tag: int, requeue: bool) -> None:
        with self.broker.lock:
            message = self.broker.unsettled.pop(tag)
            if requeue:
                self.broker.ready.insert(0, Message(message.tag, True, message.headers, message.content_type, message.body))
        self.broker.log.append(("reject", tag, requeue))

    def close(self) -> None:
        self.closed = True
        with self.broker.lock:
            for tag in sorted(self.mine & set(self.broker.unsettled), reverse=True):
                m = self.broker.unsettled.pop(tag)
                self.broker.ready.insert(0, Message(m.tag, True, m.headers, m.content_type, m.body))


class Handler:
    """Stands for `RdfRunWorker`: what it does with a message is scripted."""

    def __init__(self, outcome: Outcome = Outcome.ACK, publish: bool = True) -> None:
        self.outcome = outcome
        self.publish = publish
        self.seen: list[Message] = []
        self.running = 0
        self.most = 0
        self.gate: threading.Event | None = None
        self.entered = threading.Semaphore(0)
        self.lock = threading.Lock()

    def handle(self, message: Message, sink: Any) -> Outcome:
        with self.lock:
            self.seen.append(message)
            self.running += 1
            self.most = max(self.most, self.running)
        self.entered.release()
        try:
            if self.gate is not None:
                assert self.gate.wait(5)
            if self.publish:
                sink.publish(f"run-{message.tag}", [json.dumps({"seq": 0})])
            return self.outcome
        finally:
            with self.lock:
                self.running -= 1


def start(broker: Broker, handler: Handler, n: int = 2) -> tuple[RunConsumer, threading.Thread]:
    c = RunConsumer(broker.open, "lattice.studio.runs.rdf", handler, n, poll=0.01, backoff=(0.01,), sleep=lambda s: time.sleep(0.005))  # type: ignore[arg-type]
    t = threading.Thread(target=c.run, daemon=True)
    t.start()
    return c, t


def stop(c: RunConsumer, t: threading.Thread) -> None:
    c.stop()
    t.join(5)
    assert not t.is_alive()


def test_it_consumes_the_queue_it_is_given_and_nothing_else():
    broker = Broker()
    c, t = start(broker, Handler())
    wait_for(lambda: ("consume", "lattice.studio.runs.rdf") in broker.log)
    stop(c, t)
    assert [e for e in broker.log if e[0] == "consume"] == [("consume", "lattice.studio.runs.rdf")]


def test_the_frames_are_published_before_the_message_is_acknowledged():
    broker = Broker()
    for tag in (1, 2, 3):
        broker.put(tag)
    c, t = start(broker, Handler())
    wait_for(lambda: sum(e[0] == "ack" for e in broker.log) == 3)
    stop(c, t)
    for tag in (1, 2, 3):
        assert broker.log.index(("publish", f"run-{tag}", ('{"seq": 0}',))) < broker.log.index(("ack", tag))


def test_at_most_the_bound_runs_are_handled_at_once():
    broker = Broker(prefetch=2)
    for tag in range(1, 7):
        broker.put(tag)
    handler = Handler()
    handler.gate = threading.Event()
    c, t = start(broker, handler, n=2)
    assert handler.entered.acquire(timeout=5) and handler.entered.acquire(timeout=5)
    time.sleep(0.2)
    assert handler.most == 2 and len(handler.seen) == 2, "the other four wait in the broker, which prefetch holds back"
    assert len(broker.ready) == 4
    handler.gate.set()
    wait_for(lambda: sum(e[0] == "ack" for e in broker.log) == 6)
    stop(c, t)
    assert handler.most == 2


def test_a_run_never_holds_the_jobs_consumer_since_it_owns_a_connection_a_thread_and_a_queue():
    # The consumer's only connection is the one it opens, and its threads are its pool's and its own, so nothing here is shared with the jobs consumer.
    broker = Broker()
    c, t = start(broker, Handler())
    wait_for(lambda: broker.sessions)
    assert len(broker.sessions) == 1 and t.name != "MainThread"
    stop(c, t)


@pytest.mark.parametrize("outcome, expected", [(Outcome.REJECT, ("reject", 1, False)), (Outcome.REQUEUE, ("reject", 1, True))])
def test_a_message_the_handler_refuses_is_rejected_and_one_it_wants_again_is_requeued(outcome, expected):
    broker = Broker()
    broker.put(1)
    handler = Handler(outcome, publish=False)
    c, t = start(broker, handler)
    wait_for(lambda: expected in broker.log)
    stop(c, t)
    assert ("ack", 1) not in broker.log


def test_a_handler_that_raises_has_its_message_rejected_without_requeuing_and_the_next_is_served():
    broker = Broker()
    broker.put(1)
    broker.put(2)

    class Raises(Handler):
        def handle(self, message: Message, sink: Any) -> Outcome:
            if message.tag == 1:
                raise RuntimeError("a defect")
            return super().handle(message, sink)

    c, t = start(broker, Raises())
    wait_for(lambda: ("ack", 2) in broker.log)
    stop(c, t)
    assert ("reject", 1, False) in broker.log


def test_a_publish_the_broker_did_not_confirm_leaves_it_to_the_handler_which_asks_for_the_message_again():
    broker = Broker()
    broker.put(1)
    broker.confirm_fails = 1

    class Asks(Handler):
        def handle(self, message: Message, sink: Any) -> Outcome:
            try:
                sink.publish("run-1", ["{}"])
                return Outcome.ACK
            except ConnectionLost:
                return Outcome.REQUEUE

    c, t = start(broker, Asks())
    wait_for(lambda: ("reject", 1, True) in broker.log)
    # It comes again, marked redelivered, and is then published and acknowledged.
    wait_for(lambda: ("ack", 1) in broker.log)
    stop(c, t)


def test_a_lost_connection_is_opened_again_and_the_message_in_hand_comes_back_marked_redelivered():
    broker = Broker()
    broker.put(1)
    handler = Handler()
    handler.gate = threading.Event()
    c, t = start(broker, handler)
    assert handler.entered.acquire(timeout=5)
    broker.sessions[0].lost = True
    wait_for(lambda: len(broker.sessions) == 2)
    wait_for(lambda: len(handler.seen) == 2)
    assert [m.redelivered for m in handler.seen] == [False, True]
    handler.gate.set()
    wait_for(lambda: ("ack", 1) in broker.log)
    stop(c, t)
    # The run of the lost connection could not publish or settle on the new one, so its frames did not reach the broker twice.
    assert sum(1 for e in broker.log if e[0] == "publish") == 1


def test_a_broker_that_is_not_reachable_is_tried_again_with_a_back_off():
    broker = Broker()
    broker.refuse = 3
    broker.put(1)
    c, t = start(broker, Handler())
    wait_for(lambda: ("ack", 1) in broker.log)
    stop(c, t)
    assert len(broker.sessions) == 1


def test_stopping_lets_the_run_in_hand_finish_and_settle_before_it_returns():
    broker = Broker()
    broker.put(1)
    handler = Handler()
    handler.gate = threading.Event()
    c, t = start(broker, handler)
    assert handler.entered.acquire(timeout=5)
    c.stop()
    time.sleep(0.1)
    assert t.is_alive(), "it waits for the run in hand"
    handler.gate.set()
    t.join(5)
    assert not t.is_alive() and ("ack", 1) in broker.log


def test_the_concurrency_setting_is_a_whole_number_from_one_and_defaults_to_two():
    assert concurrency({}) == 2 and concurrency({"LATTICE_RUNS_RDF_CONCURRENCY": " "}) == 2
    assert concurrency({"LATTICE_RUNS_RDF_CONCURRENCY": "5"}) == 5
    for bad in ("0", "-1", "two", "1.5"):
        with pytest.raises(ValueError, match="whole number from 1"):
            concurrency({"LATTICE_RUNS_RDF_CONCURRENCY": bad})


def test_the_queue_the_consumer_reads_is_the_one_the_contract_declares():
    topology = TOPOLOGY
    (declared,) = [q for q in topology["queues"] if q["name"] == consumer.RDF_RUNS_QUEUE]
    assert declared["routingKey"] == consumer.RDF_RUNS_QUEUE and declared["deadLetter"] is False and declared["bindTo"] == "exchange"


def test_each_frame_is_published_as_a_cloud_event_in_the_binary_mode_to_the_events_exchange_by_the_frame_type():
    published: list[dict] = []

    class Channel:
        def basic_publish(self, exchange: str, routing_key: str, body: bytes, properties: Any) -> None:
            published.append({"exchange": exchange, "key": routing_key, "body": body, "properties": properties})

    session = object.__new__(PikaSession)
    session._frames = Channel()
    session._clock = lambda: datetime(2026, 11, 20, 10, 5, 3, 120000, tzinfo=timezone.utc)
    ids = iter(__import__("uuid").UUID(int=n) for n in range(10))
    session._ids = lambda: next(ids)
    run = "urn:lattice:studio:run:3f2b8c1e-5a47-4d0e-9b1a-6c7d8e9f0a1b"
    session.publish_frames(run, ['{"seq":0}', '{"seq":1}'])
    assert [p["body"] for p in published] == [b'{"seq":0}', b'{"seq":1}']
    for p in published:
        assert p["exchange"] == "lattice.studio.events" and p["key"] == "org.nebularis.lattice.studio.run.frame"
        props = p["properties"]
        assert props.content_type == "application/json" and props.delivery_mode == 2
        assert props.headers == {
            "cloudEvents:specversion": "1.0", "cloudEvents:id": props.message_id, "cloudEvents:source": "urn:lattice:studio:run-worker",
            "cloudEvents:type": "org.nebularis.lattice.studio.run.frame", "cloudEvents:subject": run, "cloudEvents:time": "2026-11-20T10:05:03.120000Z",
        }
    assert published[0]["properties"].message_id != published[1]["properties"].message_id


def test_the_cloud_event_attributes_equal_what_the_java_publisher_and_the_relay_read():
    from pathlib import Path

    from lattice_workers.config_studio_jobs import find_root

    root = find_root()
    java = (root / "platform" / "platform-outbox" / "src" / "main" / "java" / "org" / "nebularis" / "lattice" / "outbox" / "RabbitMqEventPublisher.java").read_text(encoding="utf-8")
    for name in ("specversion", "id", "source", "type", "subject", "time"):
        assert f'"cloudEvents:{name}"' in java
    sink = (root / "platform" / "config-studio-transforms" / "src" / "main" / "java" / "org" / "nebularis" / "lattice" / "studio" / "transforms" / "AmqpFrameSink.java").read_text(encoding="utf-8")
    assert f'"{consumer.FRAME_TYPE}"' in sink and f'"{consumer.SOURCE}"' in sink
    core = (root / "platform" / "config-studio-core" / "src" / "main" / "java" / "org" / "nebularis" / "lattice" / "studio" / "writes" / "StudioEvents.java").read_text(encoding="utf-8")
    assert f'"{consumer.EVENTS_EXCHANGE}"' in core
