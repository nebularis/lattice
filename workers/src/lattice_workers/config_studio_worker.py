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
from typing import Any, Callable, Mapping, Optional, Protocol

from rdflib import Dataset, Graph, Literal, URIRef
from rdflib.namespace import RDF
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
# The configuration parts a job may read as context, beside its target (ADR-A149 decision 7).
_HAS_IDENTITY = URIRef("https://www.nebularis.org/neuro-semantic/lattice/foundation#hasIdentity")
_VERSION_GRAPH = re.compile(r"urn:lattice:studio:pub:[0-9a-f]{32}:rev:[0-9a-f]{16}")
_PARTS = ("library", "assembly", "meaning", "review", "mapping", "vocabulary", "quantification", "eligibility", "surface", "persistence")
_KINDS = {CST.Validate: "validate", CST.Compile: "compile"}
_TARGETS = {
    CST.Persistence: "persistence", CST.Surface: "surface", CST.Vocabulary: "vocabulary",
    CST.Quantification: "quantification", CST.Eligibility: "eligibility", CST.Meaning: "meaning",
    CST.Mapping: "mapping",
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

    def put_graph(self, graph_iri: str, graph: Graph, others: Optional[Mapping[str, Graph]] = None) -> None:
        """Write a named graph, replacing any prior content, with any `others` in the same write."""


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
        self._record: Optional[Graph] = None
        try:
            final += self._run(job, graph)
            final.add((job, CST.status, CST.Succeeded))
        except Exception as error:  # the job could not run, which the author reads as a failure
            self._record = None
            for predicate in (CST.conforms, CST.report, CST.artefact, CST.gap, CST.resolution, CST.expansion, CST.testResult):
                final.remove((job, predicate, None))
            final.add((job, CST.status, CST.Failed))
            final.add((job, CST.failureMessage, Literal(str(error) or type(error).__name__)))
        final.add((job, CST.finishedAt, _time(self._clock())))
        if self._record is not None and len(self._record):
            self._store.put_graph(job_iri, final, {f"{job_iri}:record": self._record})
        else:
            self._store.put_graph(job_iri, final)

    def _run(self, job: URIRef, graph: Graph) -> Graph:
        from . import config_studio_assembly

        input_ = lambda what: self._read(graph, job, CST.configGraph, what, allowed=lambda iri: iri == f"{job}:input")
        if graph.value(job, CST.kind) == CST.ToolCall:
            from .config_studio_mork_tools import run_tool

            return run_tool(job, input_("configuration"))
        if graph.value(job, CST.kind) == CST.Publish:
            from .config_studio_publish import prepare

            root = graph.value(job, CST.unit)
            if not isinstance(root, URIRef):
                raise ValueError("a publish job names the root of its unit with cst:unit")
            return prepare(job, input_("configuration"), root, self._context(graph, job), self._registry)
        if graph.value(job, CST.kind) == CST.DryRunJob:
            from . import config_studio_dryrun
            from .config_studio_jobs import _spec

            baseline = self._read(graph, job, CST.baselineGraph, "baseline", allowed=_BASELINE.fullmatch, empty_if_missing=True)
            if graph.value(job, CST.target) == CST.Mapping:
                from .config_studio_jobs import run_mapping

                return run_mapping(job, input_("configuration"), baseline + self._context(graph, job), str(Path(self._root).resolve()),
                                   str(graph.value(job, CST.submittedAt)))
            spec = _spec(str(Path(self._root).resolve()), "meaning")
            return config_studio_dryrun.dry_run(job, input_("configuration") + baseline + self._context(graph, job), spec,
                                                str(graph.value(job, CST.submittedAt)))
        if graph.value(job, CST.kind) == CST.Propose:
            import os

            from . import config_studio_proposers as proposers
            from .config_studio_jobs import _spec

            target = graph.value(job, CST.target)
            if target == CST.OdrlProposer:
                from . import config_studio_odrl

                spec = _spec(str(Path(self._root).resolve()), "meaning")
                baseline = self._read(graph, job, CST.baselineGraph, "baseline", allowed=_BASELINE.fullmatch, empty_if_missing=True)
                config = input_("configuration") + baseline
                documents = sorted(config.subjects(RDF.type, CST.ImportDocument), key=str)
                if len(documents) != 1:
                    raise ValueError(f"an ODRL import reads exactly one cst:ImportDocument, and the input holds {len(documents)}")
                return config_studio_odrl.propose_odrl(job, config, spec, documents[0], str(graph.value(job, CST.submittedAt)))
            if target == CST.RmlImporter:
                from .config_studio_mork_tools import import_rml

                return import_rml(job, input_("configuration"))
            if target == CST.MappingLanguageModelProposer:
                from . import config_studio_mapping_proposer as mapping
                from .llm_providers import provider_from_env

                baseline = self._read(graph, job, CST.baselineGraph, "baseline", allowed=_BASELINE.fullmatch, empty_if_missing=True)
                rounds = int(os.environ.get("LATTICE_MAPPING_PROPOSER_ROUNDS") or 40)
                return mapping.propose_mapping(job, input_("configuration") + baseline, provider_from_env(os.environ),
                                               str(graph.value(job, CST.submittedAt)), rounds)
            if target == CST.SentenceFormProposer:
                proposer = proposers.SentenceFormProposer()
            elif target == CST.LanguageModelProposer:
                proposer = proposers.language_model_from_env(os.environ)
            else:
                raise ValueError(f"no proposer is named {target}")
            spec = _spec(str(Path(self._root).resolve()), "meaning")
            # Roles are the baseline's, so the job reads its baseline beside the configurations, as a validation does.
            baseline = self._read(graph, job, CST.baselineGraph, "baseline", allowed=_BASELINE.fullmatch, empty_if_missing=True)
            config = input_("configuration") + baseline
            return proposers.propose_all(job, config, spec, proposer, str(graph.value(job, CST.submittedAt)))
        if graph.value(job, CST.kind) == CST.Assemble:
            result, self._record = config_studio_assembly.assemble_all(job, input_("assembly"), str(graph.value(job, CST.submittedAt)))
            return result
        if graph.value(job, CST.kind) == CST.Validate and graph.value(job, CST.target) == CST.Library:
            return config_studio_assembly.validate_library(job, input_("library"))
        if graph.value(job, CST.kind) == CST.Validate and graph.value(job, CST.target) in (CST.AssemblyTarget, CST.Review):
            from .config_studio_jobs import _Result

            nothing = _Result(job)
            nothing.conforms(True)
            return nothing.graph
        if graph.value(job, CST.kind) == CST.Analyse:
            document = self._read(graph, job, CST.configGraph, "document", allowed=lambda iri: iri == f"{job}:input")
            return analyse_document(job, document)
        kind = _KINDS.get(graph.value(job, CST.kind))
        target = _TARGETS.get(graph.value(job, CST.target))
        submitted = graph.value(job, CST.submittedAt)
        if kind is None or target is None or submitted is None:
            raise ValueError("job lacks a known kind, a known target or a submission time")
        # The job graph is the service's, but the worker reads only what a job of its own may name (STD-298).
        return run_job(
            job, kind, target,
            self._read(graph, job, CST.configGraph, "configuration", allowed=lambda iri: iri == f"{job}:input"),
            self._read(graph, job, CST.baselineGraph, "baseline", allowed=_BASELINE.fullmatch, empty_if_missing=True),
            self._root, str(submitted), self._context(graph, job),
        )

    def _registry(self, iri: str) -> Graph:
        """A registry graph, which everyone may read, or an empty one when the registry holds none."""
        if not iri.startswith("urn:lattice:studio:pub:"):
            raise ValueError(f"{iri} is not a registry graph")
        try:
            return self._store.get_graph(iri)
        except GraphNotFound:
            return Graph()

    def _context(self, graph: Graph, job: URIRef) -> Graph:
        """The graphs a job names as its context: its own workspace's other configuration parts (STD-298), a part never
        saved reading as empty, and the published versions its workspace depends on (ADR-A149 decision 7)."""
        workspace = str(graph.value(job, CST.workspace) or "")
        allowed = re.compile(re.escape(workspace) + ":(" + "|".join(_PARTS) + ")") if _WORKSPACE.fullmatch(workspace) else None
        context = Graph()
        for iri in sorted(graph.objects(job, CST.contextGraph), key=str):
            # A published version is immutable and everyone's to read (ADR-A149 decision 4). A draft that follows its
            # lineage names the lineage, so the version is read under its lineage's IRI too.
            if _VERSION_GRAPH.fullmatch(str(iri)):
                version = self._registry(str(iri))
                context += version
                for v, lineage in list(version.subject_objects(_HAS_IDENTITY)):
                    for s, p, o in version:
                        if p != _HAS_IDENTITY:
                            context.add((lineage if s == v else s, p, lineage if o == v else o))
                continue
            if allowed is None or not allowed.fullmatch(str(iri)):
                raise ValueError(f"context graph {iri} is not one this job may read")
            try:
                context += self._store.get_graph(str(iri))
            except GraphNotFound:
                pass
        return context

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


def analyse_document(job: URIRef, document: Graph) -> Graph:
    """An analyse job's result: the document read as the sentence-form proposer reads it. Its artefacts are the analysis
    view, `analysis.json`, and the relations it proposes, `proposals.ttl` (contracts/config-studio/README.md)."""
    from .config_studio_jobs import _Result
    from .wording_le.analyse import analyse_wording
    from .wording_le.forms import load_profile
    from .wording_le.model import load_wording
    from .wording_le.namespaces import WRD
    from .wording_le.proposal import graph_view, proposal_graph

    wordings = [w for w in document.subjects(RDF.type, WRD.Wording) if isinstance(w, URIRef)]
    if len(wordings) != 1:
        raise ValueError(f"the document holds {len(wordings)} wordings, not one")
    profile = load_profile()
    wording = load_wording(document, str(wordings[0]))
    analysis = analyse_wording(wording, profile)
    proposal = proposal_graph(wording, analysis["elements"], f"{job}:proposals", profile)
    result = _Result(job)
    result.artefact("analysis.json", "application/json", json.dumps({**analysis, "graphView": graph_view(wording, proposal)}, sort_keys=True), "analysis")
    result.artefact("proposals.ttl", "text/turtle", proposal.serialize(format="turtle"), "analysis")
    result.conforms(True)
    return result.graph


_WORKSPACE = re.compile(rf"urn:lattice:studio:ws:({_UUID})")
WRITES = TOPOLOGY["writes"]


class Publisher(Protocol):
    def publish(self, exchange: str, routing_key: str, headers: dict[str, Any], body: bytes) -> None:
        """Publish persistently, returning once the broker has confirmed it."""


class WriterStore:
    """Reads from the store, and writes a job's graph through the writer of its workspace (ADR-A136): a `job-update`
    command on the writes super stream, in its workspace's partition, which the writer checks and applies. The worker
    never writes the store itself."""

    def __init__(self, reader: GraphStore, publisher: Publisher) -> None:
        self._reader = reader
        self._publisher = publisher

    def get_graph(self, graph_iri: str) -> Graph:
        return self._reader.get_graph(graph_iri)

    def put_graph(self, graph_iri: str, graph: Graph, others: Optional[Mapping[str, Graph]] = None) -> None:
        job = _MESSAGE.fullmatch(graph_iri)
        workspace = _WORKSPACE.fullmatch(str(graph.value(URIRef(graph_iri), CST.workspace) or ""))
        if job is None or workspace is None:
            raise ValueError(f"{graph_iri} is not a job graph naming its workspace")
        dataset = Dataset()
        named = dataset.graph(URIRef(graph_iri))
        for triple in graph:
            named.add(triple)
        for name, other in (others or {}).items():
            added = dataset.graph(URIRef(name))
            for triple in other:
                added.add(triple)
        # The id names the command's receipt, so a publish repeated after a broker failure is applied once.
        headers = {
            "id": str(uuid.uuid4()), "sender": "worker", "command": "job-update",
            "workspace": workspace.group(1), "job": graph_iri.rsplit(":", 1)[1],
        }
        key = routing_key(workspace.group(1))
        self._publisher.publish(WRITES["superStream"], key, headers, dataset.serialize(format="nquads").encode("utf-8"))


def declare_topology(channel: Any, topology: Mapping[str, Any]) -> None:
    """Declares the exchanges, queues and bindings of `topology`. Idempotent."""
    exchange = topology["exchange"]
    dead_letter_exchange = topology["deadLetterExchange"]
    channel.exchange_declare(exchange=exchange, exchange_type="topic", durable=True)
    channel.exchange_declare(exchange=dead_letter_exchange, exchange_type="topic", durable=True)
    for queue in topology["queues"]:
        if queue["deadLetter"]:
            channel.queue_declare(
                queue=queue["name"], durable=True, arguments={"x-dead-letter-exchange": dead_letter_exchange}
            )
            channel.queue_bind(queue=queue["name"], exchange=exchange, routing_key=queue["routingKey"])
        else:
            channel.queue_declare(queue=queue["name"], durable=True)
            channel.queue_bind(queue=queue["name"], exchange=dead_letter_exchange, routing_key=queue["routingKey"])


def routing_key(workspace: str) -> str:
    """The partition of a workspace's writes, as the Java side computes it: the id's first 32 bits, unsigned, modulo
    the partitions."""
    return str(int(workspace[:8], 16) % WRITES["partitions"])


def declare_writes(channel: Any) -> None:
    """Declares the writes super stream as the service and the writer do, from the packaged topology. Idempotent."""
    channel.exchange_declare(
        exchange=WRITES["superStream"], exchange_type=WRITES["exchangeType"], durable=True, arguments=WRITES["exchangeArguments"]
    )
    for i in range(WRITES["partitions"]):
        name = WRITES["partitionStream"].format(i=i)
        channel.queue_declare(queue=name, durable=True, arguments=WRITES["partitionArguments"])
        channel.queue_bind(queue=name, exchange=WRITES["superStream"], routing_key=str(i), arguments={"x-stream-partition-order": i})


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
