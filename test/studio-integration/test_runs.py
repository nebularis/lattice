# SPDX-License-Identifier: MPL-2.0
"""The run protocol's failure cases on a real stack (slice SVA-R5, ADR-A154, the sketch's section 4.3).

One writer, the Python worker for compile jobs, the run worker and two service instances share one broker and one store, with events served over Web MQTT.
A tab is a subscriber that connects as the studio's browser does. A run is held or ended by stopping, continuing or killing the run worker's process and a
service instance's, and the worker and the service are the production code, with no hook for a test. Run by `mise run studio:runs`, on demand and never a
dependency of `check`.

Two helpers watch the broker beside the tab. `FrameSpy` reads every run frame published to the events exchange, so a test can say what the worker published
whether or not an instance forwarded it. `publish_frame` publishes a frame in the worker's shape, for the one case (R5-T6) that needs a run to stop between two of
its frames, which the real worker never does since it publishes a run's frames in one burst."""

from __future__ import annotations

import itertools
import json
import math
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import pika
import pytest

from lattice_testing_studio_harness import Client, Topology
from lattice_testing_studio_harness.tab import FRAME_TYPE, Tab, settle

pytestmark = pytest.mark.studio_runs

RUNS = "lattice.studio.runs"
RDF_RUNS = "lattice.studio.runs.rdf"
INTERACTIVE = "lattice.studio.runs.interactive"
EVENTS = "lattice.studio.events"
GRACE = 2.0
SAMPLE_XML = """<?xml version="1.0" encoding="UTF-8"?>
<p:policies xmlns:p="urn:example:policy">
  <p:policy number="P-1">
    <p:holder>Ann "Annie" Lee</p:holder>
    <p:cover><p:code>FIRE</p:code></p:cover>
    <p:cover><p:code>FLOOD</p:code></p:cover>
  </p:policy>
  <p:policy number="P-2">
    <p:holder>Bo</p:holder>
    <p:cover><p:code>FIRE</p:code></p:cover>
    <p:cover><p:code>QUAKE</p:code></p:cover>
  </p:policy>
</p:policies>
"""
TOPOLOGY = "test/studio-integration/topologies/runs.toml"
_workers = itertools.count(2)


# --- the stack and what a test needs of it -------------------------------------------------------------


@pytest.fixture(scope="module")
def studio():
    with Topology.load(TOPOLOGY).start() as running:
        yield running
    assert not running.leftovers(), "the run left processes behind"


@pytest.fixture(scope="module")
def compiled(studio):
    """A workspace from the sample "Policies from XML and JSON" and the id of a finished compile job of its mapping part."""
    client = studio.client()
    ws = client.workspace_id(client.create_workspace("runs"))
    sample = client.request("GET", "/api/samples/policies-transforms", headers={"Accept": "text/turtle"})
    assert client.save_part(ws, "mapping", sample.text, 0).status == 204
    part = client.read_part(ws, "mapping")
    submitted = client.submit_job(ws, "compile", "mapping", part.text)
    assert submitted.status == 202, submitted.text
    job = client.job_id(submitted)
    assert "Succeeded" in client.wait_job(job, timeout=120).text
    return ws, job


@pytest.fixture(scope="module")
def persistence_compiled(studio):
    """A workspace from the facility sample and the id of a finished compile job of its persistence part, whose operations a simulated step runs."""
    client = studio.client()
    ws = client.workspace_id(client.create_workspace("steps", sample="facility"))
    part = client.read_part(ws, "persistence")
    submitted = client.submit_job(ws, "compile", "persistence", part.text)
    assert submitted.status == 202, submitted.text
    job = client.job_id(submitted)
    assert "Succeeded" in client.wait_job(job, timeout=180).text
    return ws, job


_MM, _SRC, _TGT, _REC = ("http://example.org/mapping#", "http://example.org/src#", "http://example.org/tgt#", "http://example.org/records/")
# A mapping scheme over an RDF source with two strata, a lookup that reads what an earlier stratum wrote and a closure that writes an OWL list.
RDF_MAPPING = f"""@prefix mork: <http://www.nebularis.org/ontologies/Mork#> .
@prefix sh: <http://www.w3.org/ns/shacl#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> . @prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix mm: <{_MM}> . @prefix src: <{_SRC}> . @prefix tgt: <{_TGT}> .
mm:S a mork:MappingScheme ; sh:declare [ sh:prefix "src" ; sh:namespace "{_SRC}"^^xsd:anyURI ] .
src:Thing a mork:Entity . mm:C a mork:DataConcept ; mork:representedAs src:Thing .
mm:Root a mork:Datum ; mork:mappingScheme mm:S ; mork:mappingFor mm:C ; mork:exactTBoxMatch tgt:Thing .
src:Species a mork:Entity . mm:SC a mork:DataConcept ; mork:representedAs src:Species .
src:Animal a mork:Entity . mm:AC a mork:DataConcept ; mork:representedAs src:Animal .
mm:GenSpecies a mork:DataMapping ; mork:mappingScheme mm:S ; mork:mappingFor mm:SC ; mork:broadTBoxCategoryMatch tgt:Animal ;
    mork:conceptNameTemplate "${{src:name}}" .
mm:Yield_Species a mork:DeferredContext ; mork:mappingScheme mm:S ; mork:yieldConcept mm:GenSpecies .
mm:Animal a mork:Datum ; mork:mappingScheme mm:S ; mork:mappingFor mm:AC ; mork:conceptName "animal" ;
    mork:exactTBoxMatch tgt:Animal ; mork:referenceDataMapping mm:AnimalSpecies .
mm:AnimalSpecies a mork:Lookup ; mork:mappingScheme mm:S ; mork:exactRBoxMatch rdf:type ;
    mork:exactTBoxMatch mm:Yield_Species ; mork:dataRef "src:species" ; mork:dataInline "" .
mm:Knows a mork:DataMapping ; mork:mappingScheme mm:S ; mork:broadRBoxCategoryMatch owl:topObjectProperty ;
    mork:conceptName "#knows" ; mork:assertsPropertyDomains mm:Yield_Species , tgt:A .
"""
RDF_SAMPLE = f"""<{_REC}s1> a <{_SRC}Species> ; <{_SRC}name> "Falcon" . <{_REC}s2> a <{_SRC}Species> ; <{_SRC}name> "Owl" .
<{_REC}a7> a <{_SRC}Animal> ; <{_SRC}species> "Falcon" . <{_REC}a8> a <{_SRC}Animal> ; <{_SRC}species> "Dodo" .
<{_REC}t> a <{_SRC}Thing> .
"""


@pytest.fixture(scope="module")
def rdf_compiled(studio):
    """A workspace whose mapping part maps an RDF source in two strata, and the id of a finished compile job of that part, which `mork_rdf` compiled."""
    client = studio.client()
    ws = client.workspace_id(client.create_workspace("rdf runs"))
    saved = client.save_part(ws, "mapping", RDF_MAPPING, 0)
    assert saved.status == 204, f"{saved.status} {saved.text[:300]}"
    part = client.read_part(ws, "mapping")
    submitted = client.submit_job(ws, "compile", "mapping", part.text)
    assert submitted.status == 202, submitted.text
    job = client.job_id(submitted)
    assert "Succeeded" in client.wait_job(job, timeout=180).text
    return ws, job


@pytest.fixture
def alone(studio):
    """The stack with no run worker, an empty run queue and both service instances up."""
    def clear() -> None:
        for name in [n for n in studio.pids if n.startswith("run-worker-")]:
            studio.stop_worker(name, kill=True)
        for queue in (RUNS, INTERACTIVE, RDF_RUNS):
            studio.purge(queue)
        for name in studio.service_ports:
            if not studio.worker_running(name):
                studio.start_service(name)
                studio.wait_service(name)
    clear()
    yield studio
    clear()


def start_worker(studio, warm: Optional[tuple] = None) -> str:
    """Starts a run worker and waits until it consumes the run queue. With `warm` as `(workspace, job)` it also runs one run, so the engine is warm and a test's deadline need not allow for a cold one."""
    name = f"run-worker-{next(_workers)}"
    before = studio.consumers(RUNS)
    studio.start_run_worker(name)
    wait(lambda: studio.consumers(RUNS) > before, 90, f"{name} did not consume {RUNS}")
    if warm:
        ws, job = warm
        reply = studio.client().submit_run(ws, job, "warmup", SAMPLE_XML, "application/xml", wait=True)
        assert reply.status == 200, reply.text[:300]
    return name


def wait(done, seconds: float, why: str, interval: float = 0.1) -> None:
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        if done():
            return
        time.sleep(interval)
    if not done():
        pytest.fail(why)


def held(studio, count: int = 1, queue: str = RUNS) -> None:
    """Waits until the broker has delivered `count` messages of `queue` to a consumer that has not acknowledged them, as a stopped worker holds them."""
    wait(lambda: studio.queue_counts(queue, "messages_unacknowledged")["messages_unacknowledged"] >= count, 20, f"the broker did not deliver {count} run to the stopped worker")


def at(seconds: float) -> tuple:
    """A deadline `seconds` ahead, rounded up to a whole second, as the text the contract gives and as seconds since the epoch."""
    moment = math.ceil(time.time() + seconds)
    return datetime.fromtimestamp(moment, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), float(moment)


def submit(studio, compiled, tab: str, instance: int = 0, principal: str = "developer", deadline: Optional[str] = None, **more: Any):
    ws, job = compiled
    return studio.client(principal, instance).submit_run(ws, job, tab, SAMPLE_XML, "application/xml", deadline=deadline, **more)


def accepted(reply) -> str:
    """The run's IRI of a `202`."""
    assert reply.status == 202, f"{reply.status} {reply.text[:300]}"
    iri = Client.run_iri(reply)
    assert iri, reply.text[:300]
    return iri


def until(epoch: float) -> None:
    time.sleep(max(0.0, epoch - time.time()))


class FrameSpy:
    """Every run frame published to the events exchange, whoever forwards it, read through a queue of its own."""

    def __init__(self, studio) -> None:
        self.connection = pika.BlockingConnection(pika.URLParameters(studio.amqp_uri(heartbeat=0)))
        self.channel = self.connection.channel()
        self.queue = self.channel.queue_declare("", exclusive=True).method.queue
        self.channel.queue_bind(self.queue, EVENTS, FRAME_TYPE)
        self.seen: List[Dict[str, Any]] = []

    def frames(self, run: str) -> List[Dict[str, Any]]:
        while True:
            method, _, body = self.channel.basic_get(self.queue, auto_ack=True)
            if method is None:
                break
            self.seen.append(json.loads(body))
        return [f for f in self.seen if f.get("run") == run]

    def wait_last(self, run: str, seconds: float) -> List[Dict[str, Any]]:
        wait(lambda: any(f.get("last") for f in self.frames(run)), seconds, "the worker published no last frame of the run")
        return self.frames(run)

    def close(self) -> None:
        self.connection.close()

    def publish_frame(self, run: str, frame: Dict[str, Any]) -> None:
        """Publishes `frame` to the events exchange in the worker's shape, a CloudEvent in the AMQP binding's binary mode."""
        headers = {"cloudEvents:specversion": "1.0", "cloudEvents:id": str(uuid.uuid4()), "cloudEvents:source": "urn:lattice:studio:run-worker",
                   "cloudEvents:type": FRAME_TYPE, "cloudEvents:subject": run, "cloudEvents:time": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")}
        properties = pika.BasicProperties(content_type="application/json", headers=headers, delivery_mode=2)
        self.channel.basic_publish(EVENTS, FRAME_TYPE, json.dumps({"run": run, **frame}).encode(), properties)


@pytest.fixture
def spy(alone):
    watching = FrameSpy(alone)
    yield watching
    watching.close()


def seqs(frames: List[Dict[str, Any]]) -> List[int]:
    return [f["seq"] for f in frames]


def without_run(frames: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """The frames with each mention of their run's IRI, in `run` and in the text of a part that names it, replaced, so two runs of one input compare equal."""
    return [json.loads(json.dumps(f).replace(f["run"], "RUN")) for f in frames]


# --- the tests ---------------------------------------------------------------------------------------------


def test_r5_t1_a_whole_run_reaches_the_tab_once_and_in_order_through_either_instance(alone, compiled, spy) -> None:
    """R5-T1. The tab subscribes through the first instance. A run sent to either instance reaches it frame by frame, each `seq` once and in order, ending succeeded, and
    the instance that did not accept the run forwards nothing of it, which a second copy of a frame would show."""
    start_worker(alone, warm=compiled)
    with Tab(alone.urls[0]) as tab:
        for instance in (0, 1):
            run = accepted(submit(alone, compiled, tab.tab, instance))
            tab.wait_last(run, 60)
            time.sleep(1.5)
            frames = tab.frames(run)
            assert seqs(frames) == list(range(len(frames))), f"instance {instance}: the tab's frames were {seqs(frames)}"
            assert len(frames) > 1 and frames[-1]["last"] is True and frames[-1]["status"] == "succeeded", frames[-1]
            assert not any(f["last"] for f in frames[:-1])
            published = spy.frames(run)
            assert seqs(published) == seqs(frames), "the worker published other frames than the tab received"
            assert without_run(published) == without_run(frames)


def test_r5_t2_wait_answers_the_frames_a_tab_would_receive(alone, compiled) -> None:
    """R5-T2. With `wait=true` the accepting instance answers `200` with the frames as a JSON array, equal but for the run's IRI, which the text of the report names, to what the tab received for the same input."""
    start_worker(alone, warm=compiled)
    with Tab(alone.urls[0]) as tab:
        run = accepted(submit(alone, compiled, tab.tab))
        seen = tab.wait_last(run, 60)
    reply = submit(alone, compiled, "tabwaiting", instance=1, wait=True)
    assert reply.status == 200, f"{reply.status} {reply.text[:300]}"
    assert reply.headers["content-type"].startswith("application/json")
    waited = json.loads(reply.text)
    assert seqs(waited) == list(range(len(waited)))
    assert waited[-1]["last"] is True and waited[-1]["status"] == "succeeded"
    assert without_run(waited) == without_run(seen)


def test_r5_t3_a_worker_that_stops_mid_run_does_not_run_it_twice(alone, compiled, spy) -> None:
    """R5-T3 (case 1). The worker holds the run unacknowledged and is killed. The broker redelivers it to a new worker, which does not run it. It publishes one failed frame
    saying a worker stopped, the tab receives that frame, and the worker published no other."""
    first = start_worker(alone)
    with Tab(alone.urls[0]) as tab:
        alone.signal(first, "STOP")
        run = accepted(submit(alone, compiled, tab.tab, deadline=at(90)[0]))
        held(alone)
        alone.stop_worker(first, kill=True)
        start_worker(alone)
        frames = tab.wait_last(run, 40)
        time.sleep(2)
        frames = tab.frames(run)
    assert len(frames) == 1, f"the tab received {len(frames)} frames: {frames}"
    assert frames[0]["seq"] == 0 and frames[0]["last"] is True and frames[0]["status"] == "failed"
    assert "worker stopped" in frames[0]["message"].lower(), frames[0]["message"]
    assert len(spy.frames(run)) == 1, "the run was published more than the one failed frame, so it ran"
    wait(lambda: alone.queue_counts(RUNS, "messages")["messages"] == 0, 10, "the redelivered run was not acknowledged")


def test_r5_t4_an_instance_that_stops_takes_its_runs_with_it(alone, compiled, spy) -> None:
    """R5-T4 (case 2). The accepting instance is killed while the worker is stopped. The worker then publishes its frames and no instance forwards them, since the other holds no
    entry for the run, so the tab hears nothing for it, not even a failed frame, over the deadline and the grace."""
    worker = start_worker(alone, warm=compiled)
    with Tab(alone.urls[0], tab="tabinstancestop") as tab:
        alone.signal(worker, "STOP")
        deadline, epoch = at(20)
        run = accepted(submit(alone, compiled, tab.tab, deadline=deadline))
        held(alone)
        alone.stop_worker("service", kill=True)
        alone.signal(worker, "CONT")
        published = spy.wait_last(run, 15)
        assert published[-1]["status"] == "succeeded", "the worker did not publish the run's frames, so there was nothing to withhold"
        until(epoch + GRACE + 1)
        assert tab.frames(run) == [], "the tab received frames of a run whose accepting instance had stopped"
        assert tab.frames() == []


def test_r5_t5_a_workspace_locked_during_a_run_hears_nothing_more(alone, compiled, spy) -> None:
    """R5-T5 (case 5). A principal's run is held, the workspace's owner locks it against that principal, and the worker is let go. The frames are withheld from the tab and so is the
    failed frame the service sends at the deadline, so the tab hears nothing."""
    ws, _ = compiled
    owner, other = alone.client("developer"), alone.client("reviewer")
    worker = start_worker(alone, warm=compiled)
    with Tab(alone.urls[0], principal="reviewer") as tab:
        alone.signal(worker, "STOP")
        deadline, epoch = at(20)
        run = accepted(submit(alone, compiled, tab.tab, principal="reviewer", deadline=deadline))
        held(alone)
        assert other.get_workspace(ws).status == 200, "the principal could not read the workspace before it was locked"
        try:
            assert owner.set_access(ws, "locked").status == 200
            assert other.get_workspace(ws).status == 404, "the lock did not shut the workspace to the principal"
            alone.signal(worker, "CONT")
            published = spy.wait_last(run, 15)
            assert published[-1]["status"] == "succeeded", "the worker did not publish the run's frames, so there was nothing to withhold"
            until(epoch + GRACE + 1)
            assert tab.frames(run) == [], "the tab received a frame of a run in a workspace locked against it"
            assert tab.frames() == []
        finally:
            assert owner.set_access(ws, "shared").status == 200


def test_r5_t6_a_tab_that_was_away_misses_frames_and_still_learns_the_run_failed(alone, compiled, spy) -> None:
    """R5-T6 (case 4). The tab disconnects after frame 0 and reconnects on a clean session after two more frames were published, which the broker dropped, since a tab not
    connected has no queue. No last frame comes, so at the deadline the accepting instance sends a failed frame, with `seq` one past the last it forwarded. The tab receives only
    that frame, and a client applying the contract's rule shows the run as failed with the service's message, from the frames it holds."""
    with Tab(alone.urls[0]) as tab:
        deadline, epoch = at(12)
        run = accepted(submit(alone, compiled, tab.tab, deadline=deadline))
        spy.publish_frame(run, {"seq": 0, "last": False, "part": {"index": 0, "role": "report", "mediaType": "text/turtle"}, "text": "a"})
        tab.wait_for(lambda: len(tab.frames(run)) == 1, 10)
        before = tab.frames(run)
        assert seqs(before) == [0]
        tab.stop()
        spy.publish_frame(run, {"seq": 1, "last": False, "text": "b"})
        spy.publish_frame(run, {"seq": 2, "last": False, "text": "c"})
        wait(lambda: seqs(spy.frames(run)) == [0, 1, 2], 10, "the frames were not published")
        time.sleep(1.5)
        tab.start()
        tab.wait_for(lambda: bool(tab.frames(run)), epoch - time.time() + GRACE + 5)
        received = time.time()
        after = tab.frames(run)
    assert received >= epoch - 1.0, "the failed frame came before the deadline"
    assert seqs(after) == [3], f"the tab received {seqs(after)} after it reconnected, not the failed frame alone"
    assert after[0]["last"] is True and after[0]["status"] == "failed" and "deadline" in after[0]["message"].lower(), after[0]
    shown = settle(before + after)
    assert shown == {"state": "failed", "message": after[0]["message"], "missing": [1, 2]}, shown


def test_r5_t7_a_run_no_worker_takes_expires(alone, compiled) -> None:
    """R5-T7. With no run worker the message sits in the queue. At the deadline the tab receives the service's failed frame, and the broker has dropped the message, so the queue is empty."""
    with Tab(alone.urls[0]) as tab:
        deadline, epoch = at(5)
        run = accepted(submit(alone, compiled, tab.tab, deadline=deadline))
        assert alone.queue_counts(RUNS, "messages")["messages"] == 1
        frames = tab.wait_last(run, epoch - time.time() + GRACE + 5)
        arrived = time.time()
        time.sleep(1.5)
        frames = tab.frames(run)
    assert arrived >= epoch - 1.0, "the failed frame came before the deadline"
    assert len(frames) == 1 and frames[0]["seq"] == 0 and frames[0]["last"] is True and frames[0]["status"] == "failed", frames
    assert "deadline" in frames[0]["message"].lower(), frames[0]["message"]
    wait(lambda: alone.queue_counts(RUNS, "messages")["messages"] == 0, 10, "the run's message did not expire")


def test_r5_t8_the_message_is_not_persistent_and_expires_at_the_deadline(alone, compiled) -> None:
    """R5-T8. The message a service publishes to a run queue is not persistent and carries an `expiration` close to the time left to the deadline, with the headers the contract names.
    It is read with no worker, by a basic_get that is then rejected without requeue, and only its properties are checked."""
    sent = time.time()
    deadline, epoch = at(30)
    run = accepted(submit(alone, compiled, "tabproperties", deadline=deadline))
    connection = pika.BlockingConnection(pika.URLParameters(alone.amqp_uri(heartbeat=0)))
    try:
        channel = connection.channel()
        method, properties, body = channel.basic_get(RUNS, auto_ack=False)
        assert method is not None, "the run queue held no message"
        channel.basic_reject(method.delivery_tag, requeue=False)
    finally:
        connection.close()
    assert properties.delivery_mode != 2, f"the message is persistent: {properties.delivery_mode}"
    expected = (epoch - sent) * 1000
    assert abs(int(properties.expiration) - expected) < 3000, f"expiration {properties.expiration} ms, the deadline is {expected:.0f} ms away"
    assert properties.content_type == "application/xml"
    headers = {k: v.decode() if isinstance(v, bytes) else v for k, v in properties.headers.items()}
    assert headers == {"run": run, "job": f"urn:lattice:studio:job:{compiled[1]}", "kind": "sample", "target": "mapping", "deadline": deadline}, headers
    assert body == SAMPLE_XML.encode()
    assert alone.queue_counts(RUNS, "messages")["messages"] == 0


def test_r5_t9_a_tab_holds_at_most_four_runs(alone, compiled) -> None:
    """R5-T9. With the worker stopped a tab's fifth run answers `429` with `Retry-After`, and a sixth is accepted once the earliest of the four has passed its deadline."""
    worker = start_worker(alone)
    alone.signal(worker, "STOP")
    tab = "tabfour"
    soon, first = at(6)
    later = at(90)[0]
    runs = [accepted(submit(alone, compiled, tab, deadline=soon))]
    runs += [accepted(submit(alone, compiled, tab, deadline=later)) for _ in range(3)]
    fifth = submit(alone, compiled, tab, deadline=later)
    assert fifth.status == 429, f"{fifth.status} {fifth.text[:200]}"
    retry = int(fifth.headers["retry-after"])
    assert 1 <= retry <= 7, f"Retry-After {retry} for an earliest deadline about {first - time.time():.1f} s away"
    until(first + 1.5)
    sixth = submit(alone, compiled, tab, deadline=later)
    assert sixth.status == 202, f"{sixth.status} {sixth.text[:200]}"
    assert len(set(runs)) == 4


def test_r5_t10_a_persistence_step_runs_on_the_interactive_queue_and_gives_its_four_parts(alone, persistence_compiled) -> None:
    """R5-T10 (SVA-P3). A `simulate` run of target `persistence` over the facility sample's create step is answered on the interactive queue with the check, the request, the
    delta and the outcome of the step, in that order, ending succeeded, and the same step sent again gives the same frames but for the run's IRI."""
    step = (Path(__file__).resolve().parents[2] / "contracts" / "config-studio" / "samples" / "facility-step-create.trig").read_text(encoding="utf-8")
    start_worker(alone)
    ws, job = persistence_compiled
    frames = []
    for tab in ("stepone", "steptwo"):
        reply = alone.client().submit_run(ws, job, tab, step, "application/trig", kind="simulate", target="persistence", wait=True)
        assert reply.status == 200, f"{reply.status} {reply.text[:300]}"
        frames.append(json.loads(reply.text))
    first = frames[0]
    assert seqs(first) == list(range(len(first)))
    assert first[-1]["last"] is True and first[-1]["status"] == "succeeded", first[-1]
    assert [f["part"]["role"] for f in first if "part" in f] == ["check", "request", "delta", "outcome"]
    outcome = json.loads("".join(f.get("text", "") for f in first[[i for i, f in enumerate(first) if f.get("part", {}).get("role") == "outcome"][0]:-1]))
    assert outcome["outcome"] == "applied", outcome
    assert without_run(frames[0]) == without_run(frames[1])


def test_r5_t11_a_sample_over_rdf_is_answered_by_the_python_worker_from_its_own_queue(alone, rdf_compiled) -> None:
    """R5-T11 (SVA-M3a). With no Java run worker at all, a `sample` run over Turtle and one over N-Triples are answered, with the frames the contract gives, since the service routes
    an RDF sample to `lattice.studio.runs.rdf`, which the studio's Python worker consumes. The report names `mork_rdf` on Oxigraph as the engine, the artefacts are what each mapping wrote
    at each of the two strata, a repeat gives the same frames but for the run's IRI, and the sample as N-Triples gives the frames the Turtle did. A sample over XML waits in the Java queue,
    which nothing consumes."""
    from rdflib import Graph

    triples = Graph().parse(data=RDF_SAMPLE, format="turtle").serialize(format="nt")
    ws, job = rdf_compiled
    assert alone.consumers(RDF_RUNS) >= 1 and alone.consumers(RUNS) == 0, "a Python worker consumes the RDF queue and no run worker is running"
    client = alone.client()
    answers = []
    for tab, body, media in (("rdfone", RDF_SAMPLE, "text/turtle"), ("rdftwo", RDF_SAMPLE, "text/turtle"), ("rdfthree", triples, "application/n-triples")):
        reply = client.submit_run(ws, job, tab, body, media, wait=True)
        assert reply.status == 200, f"{reply.status} {reply.text[:300]}"
        answers.append(json.loads(reply.text))
    first = answers[0]
    assert seqs(first) == list(range(len(first)))
    assert first[-1]["last"] is True and first[-1]["status"] == "succeeded" and first[-1]["conforms"] is True, first[-1]
    roles = [f["part"]["role"] for f in first if "part" in f]
    assert roles[0] == "report" and set(roles) == {"report", "artefact"} and roles.count("artefact") >= 5, roles
    report = "".join(f.get("text", "") for f in first[:[i for i, f in enumerate(first) if f.get("part", {}).get("index") == 1][0]])
    assert 'cst:engine "mork_rdf ' in report and " on Oxigraph " in report, report
    artefacts = [f["part"] for f in first if f.get("part", {}).get("role") == "artefact"]
    assert {p["step"] for p in artefacts} == {0, 1}, "a mapping at each of the two strata"
    assert all(p["mediaType"] == "application/n-triples" and p["path"].startswith(f"{p['step']}/") for p in artefacts)
    assert [(p["group"], p["step"]) for p in artefacts] == sorted((p["group"], p["step"]) for p in artefacts), "in the order of mapping and stratum"
    assert "_:" in "".join(f.get("text", "") for f in first), "the closure's OWL list, named the same on every run"
    assert without_run(answers[0]) == without_run(answers[1]) == without_run(answers[2])
    queued = alone.client().submit_run(ws, job, "rdfxml", SAMPLE_XML, "application/xml")
    assert queued.status == 202, queued.text
    assert alone.queue_counts(RUNS, "messages")["messages"] == 1 and alone.queue_counts(RDF_RUNS, "messages")["messages"] == 0
