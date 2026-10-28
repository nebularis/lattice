"""Tests for the Configuration Studio worker (ADR-A136), against an in-memory store."""

from __future__ import annotations

import json
import uuid
from importlib import resources
from pathlib import Path

import pytest
from rdflib import Graph, Literal, URIRef
from rdflib.compare import to_isomorphic
from rdflib.namespace import RDF, XSD

from lattice_workers import config_studio_jobs as jobs
from lattice_workers.config_studio_jobs import CST, SH
from lattice_workers.config_studio_worker import ConfigStudioWorker, RabbitMqConfigStudioWorker, WriterStore
from lattice_workers.fuseki_gsp import GraphNotFound

CATALOGUE = jobs.catalogue()
ROOT = jobs.find_root()
PERSISTENCE_EXAMPLES = CATALOGUE.module("persistence").directory("examples")
SURFACE_EXAMPLES = CATALOGUE.module("surface").directory("examples")


class FakeStore:
    def __init__(self) -> None:
        self.graphs: dict[str, Graph] = {}
        self.history: list[tuple[str, Graph]] = []

    def get_graph(self, graph_iri: str) -> Graph:
        if graph_iri not in self.graphs:
            raise GraphNotFound(graph_iri)
        return Graph() + self.graphs[graph_iri]

    def put_graph(self, graph_iri: str, graph: Graph) -> None:
        self.graphs[graph_iri] = Graph() + graph
        self.history.append((graph_iri, Graph() + graph))


class FakeChannel:
    def __init__(self) -> None:
        self.calls: list[tuple] = []

    def basic_ack(self, delivery_tag: int) -> None:
        self.calls.append(("ack", delivery_tag))

    def basic_nack(self, delivery_tag: int, requeue: bool) -> None:
        self.calls.append(("nack", delivery_tag, requeue))


def _clock():
    ticks = iter(range(10_000))
    return lambda: f"2026-10-27T10:00:{next(ticks) % 60:02d}Z"


def submit(store: FakeStore, kind: str, target: str, config_file: Path | None, baseline: Graph | None = None) -> str:
    job_id = str(uuid.uuid4())
    iri = f"urn:lattice:studio:job:{job_id}"
    config = Graph()
    if config_file is not None:
        config.parse(config_file, format="turtle")
    store.graphs[f"{iri}:input"] = config
    store.graphs["urn:lattice:studio:ws:00000000-0000-0000-0000-000000000001:baseline:1"] = baseline or Graph()
    job = URIRef(iri)
    g = Graph()
    g.add((job, RDF.type, CST.Job))
    g.add((job, CST.kind, CST[kind.capitalize()]))
    g.add((job, CST.target, CST[target.capitalize()]))
    g.add((job, CST.configGraph, URIRef(f"{iri}:input")))
    g.add((job, CST.baselineGraph, URIRef("urn:lattice:studio:ws:00000000-0000-0000-0000-000000000001:baseline:1")))
    g.add((job, CST.status, CST.Queued))
    g.add((job, CST.submittedAt, Literal("2026-10-27T10:00:00Z", datatype=XSD.dateTime)))
    store.graphs[iri] = g
    return iri


def run(kind: str, target: str, config_file: Path | None, store: FakeStore | None = None) -> tuple[Graph, URIRef]:
    store = store or FakeStore()
    iri = submit(store, kind, target, config_file)
    ConfigStudioWorker(store, ROOT, _clock()).handle(iri)
    return store.graphs[iri], URIRef(iri)


def results(g: Graph, job: URIRef, severity: URIRef) -> list:
    report = g.value(job, CST.report)
    return [r for r in g.objects(report, SH.result) if (r, SH.resultSeverity, severity) in g]


def artefacts(g: Graph, job: URIRef) -> dict[str, tuple[str, str, str]]:
    return {
        str(g.value(a, CST.path)): (str(g.value(a, CST.mediaType)), str(g.value(a, CST.content)), str(g.value(a, CST.group)))
        for a in g.objects(job, CST.artefact)
    }


def test_persistence_validate_conforming():
    g, job = run("validate", "persistence", PERSISTENCE_EXAMPLES / "baseline-single-class.ttl")
    assert g.value(job, CST.status) == CST.Succeeded
    assert g.value(job, CST.conforms) == Literal(True)
    assert g.value(job, CST.finishedAt) is not None


def test_persistence_validate_violation_has_focus_node():
    g, job = run("validate", "persistence", PERSISTENCE_EXAMPLES / "invalid-lagwindow-missing.ttl")
    assert g.value(job, CST.status) == CST.Succeeded
    assert g.value(job, CST.conforms) == Literal(False)
    found = results(g, job, SH.Violation)
    assert found and all(g.value(r, SH.focusNode) is not None for r in found)


def test_persistence_validate_reports_a_refusal_the_shapes_cannot_see(tmp_path):
    # The dal: shapes target dal:PrivacyProfile, so personal data without erasure declared on a
    # dal:DataAccessProfile passes SHACL. Validation also compiles, so the refusal still shows.
    config = tmp_path / "convenience.ttl"
    config.write_text(
        (PERSISTENCE_EXAMPLES / "baseline-single-class.ttl").read_text(encoding="utf-8")
        + "\nex:LoanApplicationStrongProfile dal:privacyClass dal:PersonalData ; dal:erasureStrategy dal:NoErasure .\n",
        encoding="utf-8",
    )
    g, job = run("validate", "persistence", config)
    assert g.value(job, CST.conforms) == Literal(False)
    (violation,) = results(g, job, SH.Violation)
    assert str(g.value(violation, CST.code)) == "CrossAxisViolation"
    assert g.value(violation, SH.focusNode) == URIRef("https://example.org/lending#LoanApplication")


def test_surface_validate_conforming():
    g, job = run("validate", "surface", SURFACE_EXAMPLES / "employment-job-family.ttl")
    assert g.value(job, CST.status) == CST.Succeeded
    assert g.value(job, CST.conforms) == Literal(True)


def test_persistence_compile():
    g, job = run("compile", "persistence", PERSISTENCE_EXAMPLES / "baseline-single-class.ttl")
    assert g.value(job, CST.status) == CST.Succeeded
    assert g.value(job, CST.conforms) == Literal(True)
    files = artefacts(g, job)
    assert files["compiled-profile.ttl"][0] == "text/turtle"
    assert files["compiled-profile.ttl"][2] == "profile"
    queries = [p for p in files if p.endswith((".rq", ".ru"))]
    assert queries and all(files[p][0].startswith("application/sparql-") and "/" in p for p in queries)
    gaps = list(g.objects(job, CST.gap))
    assert gaps and all(g.value(x, CST.obligation) and g.value(x, CST.message) for x in gaps)


def test_persistence_compile_refusal():
    g, job = run("compile", "persistence", PERSISTENCE_EXAMPLES / "invalid-personaldata-no-erasure.ttl")
    assert g.value(job, CST.status) == CST.Succeeded
    assert g.value(job, CST.conforms) == Literal(False)
    (violation,) = results(g, job, SH.Violation)
    assert str(g.value(violation, CST.code)).isidentifier()
    assert g.value(violation, SH.resultMessage)
    assert not list(g.objects(job, CST.artefact))


def test_surface_compile():
    g, job = run("compile", "surface", SURFACE_EXAMPLES / "employment-job-family.ttl")
    assert g.value(job, CST.status) == CST.Succeeded
    assert g.value(job, CST.conforms) == Literal(True)
    files = artefacts(g, job)
    assert files and all(media == "text/turtle" and path.endswith(".ttl") and group == path.split("/")[0]
                         for path, (media, _, group) in files.items())


def _without_times(g: Graph) -> Graph:
    out = Graph()
    for s, p, o in g:
        if p not in (CST.startedAt, CST.finishedAt):
            out.add((s, p, o))
    return out


@pytest.mark.parametrize("target,name", [("persistence", "baseline-single-class.ttl"), ("surface", "employment-job-family.ttl")])
def test_same_job_twice_gives_same_graph(target, name):
    examples = PERSISTENCE_EXAMPLES if target == "persistence" else SURFACE_EXAMPLES
    store = FakeStore()
    iri = submit(store, "compile", target, examples / name)
    worker = ConfigStudioWorker(store, ROOT, _clock())
    worker.handle(iri)
    first = _without_times(store.graphs[iri])
    worker.handle(iri)
    assert to_isomorphic(first) == to_isomorphic(_without_times(store.graphs[iri]))


def test_status_passes_queued_running_succeeded():
    store = FakeStore()
    iri = submit(store, "validate", "persistence", PERSISTENCE_EXAMPLES / "baseline-single-class.ttl")
    job = URIRef(iri)
    assert store.graphs[iri].value(job, CST.status) == CST.Queued
    ConfigStudioWorker(store, ROOT, _clock()).handle(iri)
    writes = [g for i, g in store.history if i == iri]
    assert [g.value(job, CST.status) for g in writes] == [CST.Running, CST.Succeeded]
    assert writes[0].value(job, CST.startedAt) is not None and writes[0].value(job, CST.finishedAt) is None
    assert store.graphs[iri].value(job, CST.kind) == CST.Validate


def test_missing_input_graph_fails():
    store = FakeStore()
    iri = submit(store, "validate", "persistence", None)
    del store.graphs[f"{iri}:input"]
    ConfigStudioWorker(store, ROOT, _clock()).handle(iri)
    g, job = store.graphs[iri], URIRef(iri)
    assert g.value(job, CST.status) == CST.Failed
    assert "not found" in str(g.value(job, CST.failureMessage))
    assert g.value(job, CST.finishedAt) is not None


@pytest.mark.parametrize("predicate, iri", [
    (CST.configGraph, "urn:lattice:studio:job:00000000-0000-0000-0000-000000000009:input"),
    (CST.configGraph, "urn:lattice:studio:ws:00000000-0000-0000-0000-000000000001:surface"),
    (CST.baselineGraph, "urn:lattice:studio:ws:00000000-0000-0000-0000-000000000001:surface"),
    (CST.baselineGraph, "https://example.org/elsewhere"),
])
def test_a_job_naming_a_graph_outside_its_own_fails_without_reading_it(predicate, iri):
    store = FakeStore()
    job_iri = submit(store, "validate", "persistence", None)
    job = URIRef(job_iri)
    store.graphs[job_iri].set((job, predicate, URIRef(iri)))
    store.graphs[iri] = Graph()
    ConfigStudioWorker(store, ROOT, _clock()).handle(job_iri)
    g = store.graphs[job_iri]
    assert g.value(job, CST.status) == CST.Failed
    assert "not one this job may read" in str(g.value(job, CST.failureMessage))


@pytest.mark.parametrize("body", [
    b"urn:lattice:studio:ws:" + str(uuid.uuid4()).encode(),
    b"urn:lattice:studio:job:" + str(uuid.uuid4()).upper().encode(),
    b"urn:lattice:studio:job:" + str(uuid.uuid4()).encode() + b"\n",
    b"urn:lattice:studio:job:" + str(uuid.uuid4()).encode() + b" extra",
    b"urn:lattice:studio:job:\xff\xfe",
])
def test_malformed_message_is_nacked_without_requeue(body):
    store, channel = FakeStore(), FakeChannel()
    RabbitMqConfigStudioWorker(ConfigStudioWorker(store, ROOT, _clock())).handle(channel, 7, body)
    assert channel.calls == [("nack", 7, False)]
    assert not store.history


def test_acks_after_final_write_and_requeues_on_store_error():
    store, channel = FakeStore(), FakeChannel()
    iri = submit(store, "validate", "persistence", PERSISTENCE_EXAMPLES / "baseline-single-class.ttl")
    adapter = RabbitMqConfigStudioWorker(ConfigStudioWorker(store, ROOT, _clock()))
    adapter.handle(channel, 1, iri.encode())
    assert channel.calls == [("ack", 1)]

    def broken(*_):
        raise OSError("store down")

    store.put_graph = broken
    with pytest.raises(OSError):
        adapter.handle(channel, 2, iri.encode())
    assert channel.calls[-1] == ("nack", 2, True)


def test_topology_copy_equals_contract():
    packaged = resources.files("lattice_workers").joinpath("config-studio-topology.json").read_text(encoding="utf-8")
    contract = (ROOT / CATALOGUE.area("contracts") / "config-studio" / "amqp-topology.json").read_text(encoding="utf-8")
    assert packaged == contract
    assert json.loads(packaged)["queues"][0]["name"] == "lattice.studio.jobs"


class FakePublisher:
    def __init__(self) -> None:
        self.sent: list[tuple[str, str, dict, bytes]] = []

    def publish(self, exchange: str, routing_key: str, headers: dict, body: bytes) -> None:
        self.sent.append((exchange, routing_key, headers, body))


def test_a_job_graph_goes_to_its_workspace_writer_not_the_store():
    from rdflib import Dataset

    ws, job = str(uuid.uuid4()), str(uuid.uuid4())
    iri = f"urn:lattice:studio:job:{job}"
    graph = Graph()
    graph.add((URIRef(iri), CST.workspace, URIRef(f"urn:lattice:studio:ws:{ws}")))
    graph.add((URIRef(iri), CST.status, CST.Running))
    reader, publisher = FakeStore(), FakePublisher()
    WriterStore(reader, publisher).put_graph(iri, graph)
    assert reader.history == []
    exchange, key, headers, body = publisher.sent[0]
    assert (exchange, key) == ("lattice.studio.writes", ws)
    assert headers == {"command": "job-update", "workspace": ws, "job": job}
    sent = Dataset().parse(data=body.decode("utf-8"), format="nquads")
    assert to_isomorphic(sent.graph(URIRef(iri))) == to_isomorphic(graph)


def test_a_graph_naming_no_workspace_is_never_sent():
    iri = f"urn:lattice:studio:job:{uuid.uuid4()}"
    publisher = FakePublisher()
    with pytest.raises(ValueError):
        WriterStore(FakeStore(), publisher).put_graph(iri, Graph())
    assert publisher.sent == []
