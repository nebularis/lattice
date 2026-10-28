"""Consumer and RabbitMQ adapter for Configuration Studio jobs (ADR-A136).

Reads a job graph, marks it running, runs the job and hands the whole graph back with its final
status, per `contracts/config-studio/README.md`.
"""

from __future__ import annotations

import json
import re
import uuid
from importlib import resources
from pathlib import Path
from typing import Any, Callable, Protocol

from rdflib import Dataset, Graph, Literal, URIRef
from rdflib.namespace import XSD

from .config_studio_jobs import CST, run_job
from .fuseki_gsp import GraphNotFound
from .rabbitmq_surface_worker import RabbitMqChannel

TOPOLOGY: dict[str, Any] = json.loads(
    resources.files("lattice_workers").joinpath("config-studio-topology.json").read_text(encoding="utf-8")
)
JOBS_QUEUE = "lattice.studio.jobs"

_UUID = r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
_MESSAGE = re.compile(rf"urn:lattice:studio:job:{_UUID}")
_BASELINE = re.compile(rf"urn:lattice:studio:ws:{_UUID}:baseline:[1-9][0-9]*")
_KINDS = {CST.Validate: "validate", CST.Compile: "compile"}
_TARGETS = {
    CST.Persistence: "persistence", CST.Surface: "surface", CST.Vocabulary: "vocabulary",
    CST.Quantification: "quantification", CST.Eligibility: "eligibility",
}
# What the worker writes, so that a rerun starts from what the service wrote.
_WORKER_PREDICATES = (
    CST.status, CST.startedAt, CST.finishedAt, CST.failureMessage, CST.conforms, CST.report, CST.artefact, CST.gap,
    CST.resolution, CST.expansion, CST.testResult,
)


class InvalidMessage(ValueError):
    """The message is not a job this worker can read. It is refused without requeuing."""


class GraphStore(Protocol):
    def get_graph(self, graph_iri: str) -> Graph:
        """Read a named graph, raising `GraphNotFound` when it does not exist."""

    def put_graph(self, graph_iri: str, graph: Graph) -> None:
        """Write a named graph, replacing any prior content."""


def _time(value: str) -> Literal:
    return Literal(value, datatype=XSD.dateTime)


class ConfigStudioWorker:
    def __init__(self, store: GraphStore, root: Path | str, clock: Callable[[], str]) -> None:
        self._store = store
        self._root = root
        self._clock = clock

    @staticmethod
    def accept(body: bytes) -> str:
        """The job IRI the message names, or `InvalidMessage`."""
        try:
            text = body.decode("utf-8")
        except UnicodeDecodeError as error:
            raise InvalidMessage("message is not UTF-8") from error
        if not _MESSAGE.fullmatch(text):
            raise InvalidMessage("message is not a studio job IRI")
        return text

    def handle(self, job_iri: str) -> None:
        job = URIRef(job_iri)
        try:
            written = self._store.get_graph(job_iri)
        except GraphNotFound as error:
            raise InvalidMessage(f"job graph {job_iri} not found") from error
        graph = Graph()
        for triple in written.triples((job, None, None)):
            if triple[1] not in _WORKER_PREDICATES:
                graph.add(triple)

        running = Graph() + graph
        running.add((job, CST.status, CST.Running))
        running.add((job, CST.startedAt, _time(self._clock())))
        self._store.put_graph(job_iri, running)

        final = Graph() + running
        final.remove((job, CST.status, None))
        try:
            final += self._run(job, graph)
            final.add((job, CST.status, CST.Succeeded))
        except Exception as error:  # the job could not run, which the author reads as a failure
            for predicate in (CST.conforms, CST.report, CST.artefact, CST.gap, CST.resolution, CST.expansion, CST.testResult):
                final.remove((job, predicate, None))
            final.add((job, CST.status, CST.Failed))
            final.add((job, CST.failureMessage, Literal(str(error) or type(error).__name__)))
        final.add((job, CST.finishedAt, _time(self._clock())))
        self._store.put_graph(job_iri, final)

    def _run(self, job: URIRef, graph: Graph) -> Graph:
        kind = _KINDS.get(graph.value(job, CST.kind))
        target = _TARGETS.get(graph.value(job, CST.target))
        submitted = graph.value(job, CST.submittedAt)
        if kind is None or target is None or submitted is None:
            raise ValueError("job lacks a known kind, a known target or a submission time")
        # The job graph is the service's, but the worker reads only what a job of its own may name (STD-279).
        return run_job(
            job, kind, target,
            self._read(graph, job, CST.configGraph, "configuration", allowed=lambda iri: iri == f"{job}:input"),
            self._read(graph, job, CST.baselineGraph, "baseline", allowed=_BASELINE.fullmatch, empty_if_missing=True),
            self._root, str(submitted),
        )

    def _read(
        self, graph: Graph, job: URIRef, predicate: URIRef, what: str, allowed: Callable[[str], Any], empty_if_missing: bool = False,
    ) -> Graph:
        """A graph the job names. A baseline may be empty, and the store keeps no empty graph, so a
        missing baseline reads as empty. A missing configuration fails the job, since the service
        writes the input of every job it publishes."""
        iri = graph.value(job, predicate)
        if iri is None:
            raise ValueError(f"job names no {what} graph")
        if not allowed(str(iri)):
            raise ValueError(f"{what} graph {iri} is not one this job may read")
        try:
            return self._store.get_graph(str(iri))
        except GraphNotFound as error:
            if empty_if_missing:
                return Graph()
            raise ValueError(f"{what} graph {iri} not found") from error


_WORKSPACE = re.compile(rf"urn:lattice:studio:ws:({_UUID})")
WRITES = TOPOLOGY["writes"]


class Publisher(Protocol):
    def publish(self, exchange: str, routing_key: str, headers: dict[str, Any], body: bytes) -> None:
        """Publish persistently, returning once the broker has confirmed it."""


class WriterStore:
    """Reads from the store, and writes a job's graph through the writer of its workspace (ADR-A136, partitioned
    writers): a `job-update` command on the consistent-hash exchange, keyed by the workspace's id, which the writer
    checks and applies. The worker never writes the store itself."""

    def __init__(self, reader: GraphStore, publisher: Publisher) -> None:
        self._reader = reader
        self._publisher = publisher

    def get_graph(self, graph_iri: str) -> Graph:
        return self._reader.get_graph(graph_iri)

    def put_graph(self, graph_iri: str, graph: Graph) -> None:
        job = _MESSAGE.fullmatch(graph_iri)
        workspace = _WORKSPACE.fullmatch(str(graph.value(URIRef(graph_iri), CST.workspace) or ""))
        if job is None or workspace is None:
            raise ValueError(f"{graph_iri} is not a job graph naming its workspace")
        dataset = Dataset()
        named = dataset.graph(URIRef(graph_iri))
        for triple in graph:
            named.add(triple)
        # The id names the command's receipt, so a publish repeated after a broker failure is applied once.
        headers = {
            "id": str(uuid.uuid4()), "sender": "worker", "command": "job-update",
            "workspace": workspace.group(1), "job": graph_iri.rsplit(":", 1)[1],
        }
        self._publisher.publish(WRITES["exchange"], workspace.group(1), headers, dataset.serialize(format="nquads").encode("utf-8"))


class RabbitMqConfigStudioWorker:
    """Acknowledges after the final write. Refuses a malformed message without requeuing."""

    def __init__(self, worker: ConfigStudioWorker) -> None:
        self._worker = worker

    def handle(self, channel: RabbitMqChannel, delivery_tag: int, body: bytes) -> None:
        try:
            self._worker.handle(self._worker.accept(body))
        except InvalidMessage:
            channel.basic_nack(delivery_tag, requeue=False)
        except Exception:
            channel.basic_nack(delivery_tag, requeue=True)
            raise
        else:
            channel.basic_ack(delivery_tag)
