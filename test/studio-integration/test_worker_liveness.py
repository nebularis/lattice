# SPDX-License-Identifier: MPL-2.0
"""The studio worker through a long job, a lost job and a message it cannot read, against a real broker (plan `studio-worker-liveness`, WL-1).

Each test starts the worker itself, on a broker whose heartbeat is two seconds, so what takes minutes in a real run takes seconds here.
A worker patched to run slowly or to die is a program of the test's own (`start_worker(code=...)`), and the worker's own code is untouched.
Run by `mise run studio:liveness`, on demand and never a dependency of `check`."""

from __future__ import annotations

import time
import urllib.parse
import urllib.request
import uuid

import pika
import pytest

from lattice_testing_studio_harness import Topology

pytestmark = pytest.mark.studio_liveness

CST = "https://www.nebularis.org/neuro-semantic/lattice/config-studio#"
BODY = "@prefix ex: <https://example.org/> .\nex:a ex:p ex:b .\n"
HEARTBEAT = 2
LONG = "lattice.studio.jobs.long"

# A worker whose every job first sleeps, like a proposal waiting on a model.
SLOW = """
import os, time
from lattice_workers import config_studio_worker as w, config_studio_main as m
run = w.ConfigStudioWorker._run
def slow(self, job, graph):
    time.sleep(float(os.environ["LATTICE_TEST_JOB_SECONDS"]))
    return run(self, job, graph)
w.ConfigStudioWorker._run = slow
m.main()
"""

# A worker that dies, without a goodbye, a moment after it has marked a job running.
DIES = """
import os, time
from lattice_workers import config_studio_worker as w, config_studio_main as m
def die(self, job, graph):
    time.sleep(2)
    os._exit(9)
w.ConfigStudioWorker._run = die
m.main()
"""


@pytest.fixture(scope="module")
def studio():
    with Topology(name="liveness", workers=0, long_workers=0).start() as running:
        yield running


@pytest.fixture
def alone(studio):
    """The studio with no worker and an empty jobs queue, and no worker left behind."""
    def clear() -> None:
        for name in [n for n in studio.pids if n.startswith("worker-")]:
            studio.stop_worker(name)
        studio.purge("lattice.studio.jobs")
        studio.purge(LONG)
    clear()
    yield studio
    clear()


def workspace(client) -> str:
    return client.workspace_id(client.create_workspace("liveness"))


def validate(client, ws: str) -> str:
    reply = client.submit_job(ws, "validate", "vocabulary", BODY)
    assert reply.status == 202, reply.text
    return client.job_id(reply)


def finished(client, job: str, seconds: float) -> str:
    """The job's graph once it has finished, or a failure saying what it was when the wait ended."""
    try:
        return client.wait_job(job, timeout=seconds).text
    except TimeoutError as error:
        pytest.fail(str(error)[:300])


def status(text: str) -> str:
    return "Succeeded" if f"{CST}Succeeded" in text or "cst:Succeeded" in text else "Failed" if "Failed" in text else "other"


def test_a_job_longer_than_the_brokers_timeout_finishes_on_one_connection(alone) -> None:
    """RC1. The broker closes a client silent for twice the heartbeat, here four seconds. A job of ten seconds is longer."""
    client = alone.client()
    alone.start_worker("worker-slow", env={"LATTICE_AMQP_URI": alone.amqp_uri(heartbeat=HEARTBEAT), "LATTICE_TEST_JOB_SECONDS": "10"}, code=SLOW)
    ws = workspace(client)
    text = finished(client, validate(client, ws), 90)
    assert status(text) == "Succeeded", text[:400]
    assert "missed heartbeats" not in alone.broker_log(), "the broker closed the worker's connection while it ran the job"
    assert alone.worker_running("worker-slow"), alone.log("worker-slow")[-600:]


def test_a_job_goes_on_through_a_lost_connection_and_its_result_is_kept(alone) -> None:
    """RC2. The broker closes the worker's connection three seconds into a job of eight. The job is neither failed nor run again."""
    client = alone.client()
    alone.start_worker("worker-lost", env={"LATTICE_TEST_JOB_SECONDS": "8"}, code=SLOW)
    ws = workspace(client)
    job = validate(client, ws)
    deadline = time.monotonic() + 30
    while f"{job} starts" not in alone.log("worker-lost") and time.monotonic() < deadline:
        time.sleep(0.2)
    time.sleep(3)
    assert alone.close_connections("config-studio-worker") == 1
    text = finished(client, job, 90)
    assert status(text) == "Succeeded", text[:400]
    log = alone.log("worker-lost")
    assert log.count(f"{job} starts") == 1, "the job was started again:\n" + log[-1500:]
    assert log.count("consuming lattice.studio.jobs") == 2, "the worker did not reconnect:\n" + log[-1500:]
    assert alone.worker_running("worker-lost")


def test_a_validation_finishes_while_a_long_job_is_still_running(alone) -> None:
    """RC4. A proposal by a language model goes to the long queue and its worker, and a validation submitted behind it to the other."""
    client = alone.client()
    alone.start_worker("worker-1")
    alone.start_worker("worker-long-1", env={"LATTICE_WORKER_QUEUE": LONG, "LATTICE_TEST_JOB_SECONDS": "25"}, code=SLOW)
    deadline = time.monotonic() + 60
    while (alone.consumers("lattice.studio.jobs") < 1 or alone.consumers(LONG) < 1) and time.monotonic() < deadline:
        time.sleep(0.3)
    ws = workspace(client)
    proposal = client.job_id(client.submit_job(ws, "propose", "language-model", BODY))
    time.sleep(1.5)
    started = time.monotonic()
    assert status(finished(client, validate(client, ws), 20)) == "Succeeded"
    assert time.monotonic() - started < 15, "the validation waited for the proposal"
    assert status(client.get_job(proposal).text) == "other", "the proposal had ended, so the validation did not overtake it"
    finished(client, proposal, 90)


def test_a_job_found_running_after_a_loss_is_failed_and_not_run_again(alone) -> None:
    """RC3. The worker dies after it marked the job running. The job comes back, and a second worker must not start it over."""
    client = alone.client()
    ws = workspace(client)
    alone.start_worker("worker-dies", code=DIES)
    job = validate(client, ws)
    deadline = time.monotonic() + 60
    while alone.worker_running("worker-dies") and time.monotonic() < deadline:
        time.sleep(0.5)
    assert not alone.worker_running("worker-dies"), "the patched worker did not die"
    alone.start_worker("worker-2")
    text = finished(client, job, 60)
    assert status(text) == "Failed", "a job the first worker had started was run again: " + text[:300]
    assert "stopped" in text, "the failure does not say the worker stopped while it ran: " + text[:300]


def test_a_message_of_a_kind_the_worker_does_not_know_does_not_stop_it(alone) -> None:
    """RC7. A job of the retired kind `cst:Refresh`, which names no workspace, is at the head of the queue."""
    client = alone.client()
    job = f"urn:lattice:studio:job:{uuid.uuid4()}"
    update = (f"PREFIX cst: <{CST}> PREFIX xsd: <http://www.w3.org/2001/XMLSchema#> INSERT DATA {{ GRAPH <{job}> {{ <{job}> a cst:Job ; "
              f"cst:kind cst:Refresh ; cst:status cst:Queued ; cst:submittedAt \"2026-11-01T10:00:00Z\"^^xsd:dateTime . }} }}")
    urllib.request.urlopen(urllib.request.Request(f"{alone.fuseki_url}/studio-write/update", data=urllib.parse.urlencode({"update": update}).encode(), method="POST"))
    connection = pika.BlockingConnection(pika.URLParameters(alone.amqp_uri()))
    connection.channel().basic_publish(exchange="", routing_key="lattice.studio.jobs", body=job.encode(), properties=pika.BasicProperties(delivery_mode=2))
    connection.close()
    alone.start_worker("worker-1")
    ws = workspace(client)
    text = finished(client, validate(client, ws), 60)
    assert status(text) == "Succeeded", text[:300]
    assert alone.worker_running("worker-1"), alone.log("worker-1")[-600:]
