"""Tests the worker runtime: Fuseki GSP client, RabbitMQ adapter, entry point (ADR-A118, plan WA7).

Covers S7-01 to S7-08 of docs/developer/plans/word-authoring-poc.md section "WA7".
"""

from __future__ import annotations

import http.server
import json
import threading
from pathlib import Path
from typing import Any

import pytest
import rdflib
from jsonschema import Draft202012Validator
from referencing import Registry, Resource

from lattice_workers.fuseki_gsp import FusekiGraphStore, GraphNotFound
from lattice_workers.wording_analysis_main import read_config
from lattice_workers.wording_analysis_worker import (
    TOPOLOGY,
    RabbitMqResultPublisher,
    RabbitMqWordingAnalysisWorker,
    WordingAnalysisConsumer,
)
from lattice_workers.wording_le.forms import load_profile

REPO = Path(__file__).resolve().parents[2]
CONTRACTS = REPO / "contracts"
WORDING_FIXTURES = CONTRACTS / "authoring" / "fixtures" / "wording"

BASE = "https://example.org/lattice/authoring/"
FACILITY_DOC_ID = "00000001-0000-4000-8000-000000000000"
WORDING_IRI = f"{BASE}doc/{FACILITY_DOC_ID}/wording"
WORDING_GRAPH_IRI = f"{BASE}doc/{FACILITY_DOC_ID}/rev/1/wording-graph"
PROPOSAL_GRAPH_IRI = f"{BASE}doc/{FACILITY_DOC_ID}/rev/1/proposal-graph"


def _facility_graph() -> rdflib.Graph:
    graph = rdflib.Graph()
    graph.parse(WORDING_FIXTURES / "facility-agreement.nt", format="nt")
    return graph


def _request(**overrides: Any) -> dict[str, Any]:
    message = {
        "jobId": "00000009-0000-4000-8000-000000000099",
        "correlationId": "00000009-0000-4000-8000-000000000099",
        "documentId": FACILITY_DOC_ID,
        "revision": 1,
        "wordingGraph": {
            "tenantId": "poc",
            "projectId": "word-authoring",
            "graphIri": WORDING_GRAPH_IRI,
            "revisionHash": "sha256:" + "ab" * 32,
        },
        "wordingIri": WORDING_IRI,
        "proposalGraphIri": PROPOSAL_GRAPH_IRI,
        "requestedAt": "2026-10-01T00:00:00Z",
    }
    message.update(overrides)
    return message


class FakeStore:
    def __init__(self, graphs: dict[str, rdflib.Graph] | None = None) -> None:
        self._graphs = dict(graphs or {})
        self.put_calls: list[tuple[str, rdflib.Graph]] = []
        self.put_graph_raises: Exception | None = None

    def get_graph(self, graph_iri: str) -> rdflib.Graph:
        if graph_iri not in self._graphs:
            raise GraphNotFound(graph_iri)
        return self._graphs[graph_iri]

    def put_graph(self, graph_iri: str, graph: rdflib.Graph) -> None:
        if self.put_graph_raises is not None:
            raise self.put_graph_raises
        self._graphs[graph_iri] = graph
        self.put_calls.append((graph_iri, graph))


class FakePublisher:
    def __init__(self) -> None:
        self.published: list[tuple[str, dict]] = []

    def publish(self, job_id: str, result: dict) -> None:
        self.published.append((job_id, result))


class FakeChannel:
    def __init__(self) -> None:
        self.acked: list[int] = []
        self.nacked: list[tuple[int, bool]] = []
        self.published: list[tuple[str, str, bytes, Any]] = []

    def basic_ack(self, delivery_tag: int) -> None:
        self.acked.append(delivery_tag)

    def basic_nack(self, delivery_tag: int, requeue: bool) -> None:
        self.nacked.append((delivery_tag, requeue))

    def basic_publish(self, exchange: str, routing_key: str, body: bytes, properties: Any) -> None:
        self.published.append((exchange, routing_key, body, properties))


def _result_schema_registry() -> Registry:
    resources = []
    for path in sorted((CONTRACTS / "authoring").glob("*.schema.json")):
        schema = json.loads(path.read_text(encoding="utf-8"))
        resources.append((schema["$id"], Resource.from_contents(schema)))
    for name in ("wording-analysis-request.schema.json", "wording-analysis-result.schema.json"):
        schema = json.loads((CONTRACTS / "events" / name).read_text(encoding="utf-8"))
        resources.append((schema["$id"], Resource.from_contents(schema)))
    return Registry().with_resources(resources)


def _validate_result(result: dict) -> list[str]:
    registry = _result_schema_registry()
    schema_id = "https://schemas.nebularis.org/lattice/events/wording-analysis-result/0.1.0"
    validator = Draft202012Validator({"$ref": schema_id}, registry=registry)
    return [str(error) for error in validator.iter_errors(result)]


# S7-01 --------------------------------------------------------------------------------------------


def test_a_valid_request_is_analysed_proposed_published_and_acked():
    store = FakeStore({WORDING_GRAPH_IRI: _facility_graph()})
    publisher = FakePublisher()
    consumer = WordingAnalysisConsumer(store, publisher, load_profile(), lambda: "2026-10-01T00:00:01Z")
    worker = RabbitMqWordingAnalysisWorker(consumer)
    channel = FakeChannel()

    worker.handle(channel, 1, json.dumps(_request()).encode("utf-8"))

    assert channel.acked == [1]
    assert channel.nacked == []
    assert len(publisher.published) == 1
    job_id, result = publisher.published[0]
    assert job_id == _request()["jobId"]
    assert result["status"] == "completed"
    assert result["proposalGraph"]["graphIri"] == PROPOSAL_GRAPH_IRI
    assert result["proposalGraph"]["revisionHash"].startswith("sha256:")
    assert result["analysis"]["elements"]
    assert _validate_result(result) == []
    assert store.put_calls and store.put_calls[0][0] == PROPOSAL_GRAPH_IRI


# S7-02 --------------------------------------------------------------------------------------------


def test_a_missing_wording_graph_gives_a_failed_result_and_acks():
    store = FakeStore()
    publisher = FakePublisher()
    consumer = WordingAnalysisConsumer(store, publisher, load_profile(), lambda: "2026-10-01T00:00:01Z")
    worker = RabbitMqWordingAnalysisWorker(consumer)
    channel = FakeChannel()

    worker.handle(channel, 2, json.dumps(_request()).encode("utf-8"))

    assert channel.acked == [2]
    assert channel.nacked == []
    job_id, result = publisher.published[0]
    assert result["status"] == "failed"
    assert result["error"] == "wording graph not found"
    assert result["proposalGraph"] is None
    assert result["analysis"] is None
    assert _validate_result(result) == []


# S7-03 --------------------------------------------------------------------------------------------


def test_malformed_json_is_nacked_without_requeue_and_nothing_is_published():
    publisher = FakePublisher()
    consumer = WordingAnalysisConsumer(FakeStore(), publisher, load_profile(), lambda: "2026-10-01T00:00:01Z")
    worker = RabbitMqWordingAnalysisWorker(consumer)
    channel = FakeChannel()

    worker.handle(channel, 3, b"not-json")

    assert channel.acked == []
    assert channel.nacked == [(3, False)]
    assert publisher.published == []


def test_a_request_missing_a_required_field_is_nacked_without_requeue_and_nothing_is_published():
    publisher = FakePublisher()
    consumer = WordingAnalysisConsumer(FakeStore(), publisher, load_profile(), lambda: "2026-10-01T00:00:01Z")
    worker = RabbitMqWordingAnalysisWorker(consumer)
    channel = FakeChannel()
    message = _request()
    del message["proposalGraphIri"]

    worker.handle(channel, 4, json.dumps(message).encode("utf-8"))

    assert channel.acked == []
    assert channel.nacked == [(4, False)]
    assert publisher.published == []


# S7-04 --------------------------------------------------------------------------------------------


def test_a_put_graph_failure_is_nacked_with_requeue_propagates_and_publishes_nothing():
    store = FakeStore({WORDING_GRAPH_IRI: _facility_graph()})
    store.put_graph_raises = OSError("fuseki unreachable")
    publisher = FakePublisher()
    consumer = WordingAnalysisConsumer(store, publisher, load_profile(), lambda: "2026-10-01T00:00:01Z")
    worker = RabbitMqWordingAnalysisWorker(consumer)
    channel = FakeChannel()

    with pytest.raises(OSError, match="fuseki unreachable"):
        worker.handle(channel, 5, json.dumps(_request()).encode("utf-8"))

    assert channel.acked == []
    assert channel.nacked == [(5, True)]
    assert publisher.published == []


# S7-05 --------------------------------------------------------------------------------------------


def test_the_packaged_topology_matches_the_committed_contract():
    committed = json.loads((CONTRACTS / "authoring" / "amqp-topology.json").read_text(encoding="utf-8"))
    assert TOPOLOGY == committed


# S7-06 --------------------------------------------------------------------------------------------


class _FusekiStubHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002 - matches base signature
        pass

    def do_GET(self) -> None:
        self.server.requests.append(("GET", self.path, dict(self.headers)))  # type: ignore[attr-defined]
        if "missing" in self.path:
            self.send_response(404)
            self.end_headers()
            return
        body = b"<urn:s> <urn:p> <urn:o> .\n"
        self.send_response(200)
        self.send_header("Content-Type", "text/turtle")
        self.end_headers()
        self.wfile.write(body)

    def do_PUT(self) -> None:
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)
        self.server.requests.append(("PUT", self.path, dict(self.headers), body))  # type: ignore[attr-defined]
        self.send_response(204)
        self.end_headers()


@pytest.fixture()
def fuseki_stub():
    server = http.server.HTTPServer(("127.0.0.1", 0), _FusekiStubHandler)
    server.requests = []  # type: ignore[attr-defined]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server
    finally:
        server.shutdown()
        thread.join()


def test_get_graph_url_carries_the_encoded_graph_iri(fuseki_stub):
    base_url = f"http://127.0.0.1:{fuseki_stub.server_port}"
    store = FusekiGraphStore(base_url, "authoring")

    graph = store.get_graph(WORDING_GRAPH_IRI)

    assert len(graph) == 1
    method, path, _headers = fuseki_stub.requests[-1]
    assert method == "GET"
    assert path == f"/authoring/data?graph=https%3A%2F%2Fexample.org%2Flattice%2Fauthoring%2Fdoc%2F00000001-0000-4000-8000-000000000000%2Frev%2F1%2Fwording-graph"


def test_put_graph_sends_turtle_with_content_type(fuseki_stub):
    base_url = f"http://127.0.0.1:{fuseki_stub.server_port}"
    store = FusekiGraphStore(base_url, "authoring")
    graph = rdflib.Graph()
    graph.add((rdflib.URIRef("urn:s"), rdflib.URIRef("urn:p"), rdflib.URIRef("urn:o")))

    store.put_graph(PROPOSAL_GRAPH_IRI, graph)

    method, path, headers, body = fuseki_stub.requests[-1]
    assert method == "PUT"
    assert "graph=https%3A%2F%2F" in path
    assert headers["Content-Type"] == "text/turtle"
    sent = rdflib.Graph()
    sent.parse(data=body, format="turtle")
    assert (rdflib.URIRef("urn:s"), rdflib.URIRef("urn:p"), rdflib.URIRef("urn:o")) in sent


def test_basic_auth_header_is_present_when_configured(fuseki_stub):
    base_url = f"http://127.0.0.1:{fuseki_stub.server_port}"
    store = FusekiGraphStore(base_url, "authoring", user="alice", password="secret")

    store.get_graph(WORDING_GRAPH_IRI)

    _method, _path, headers = fuseki_stub.requests[-1]
    assert headers["Authorization"] == "Basic YWxpY2U6c2VjcmV0"


def test_no_auth_header_when_not_configured(fuseki_stub):
    base_url = f"http://127.0.0.1:{fuseki_stub.server_port}"
    store = FusekiGraphStore(base_url, "authoring")

    store.get_graph(WORDING_GRAPH_IRI)

    _method, _path, headers = fuseki_stub.requests[-1]
    assert "Authorization" not in headers


def test_a_404_raises_graph_not_found(fuseki_stub):
    base_url = f"http://127.0.0.1:{fuseki_stub.server_port}"
    store = FusekiGraphStore(base_url, "authoring")

    with pytest.raises(GraphNotFound):
        store.get_graph(f"{BASE}doc/missing/wording-graph")


# S7-07 --------------------------------------------------------------------------------------------


def test_config_reader_requires_the_amqp_uri():
    with pytest.raises(ValueError, match="LATTICE_AMQP_URI"):
        read_config({})


def test_config_reader_requires_the_fuseki_url():
    with pytest.raises(ValueError, match="LATTICE_FUSEKI_URL"):
        read_config({"LATTICE_AMQP_URI": "amqp://guest:guest@localhost:5672/"})


def test_config_reader_defaults_the_optional_variables():
    config = read_config({
        "LATTICE_AMQP_URI": "amqp://guest:guest@localhost:5672/",
        "LATTICE_FUSEKI_URL": "http://localhost:3030",
    })

    assert config.fuseki_dataset == "authoring"
    assert config.fuseki_user is None
    assert config.fuseki_password is None


def test_config_reader_reads_every_optional_variable_when_present():
    config = read_config({
        "LATTICE_AMQP_URI": "amqp://guest:guest@localhost:5672/",
        "LATTICE_FUSEKI_URL": "http://localhost:3030",
        "LATTICE_FUSEKI_DATASET": "other",
        "LATTICE_FUSEKI_USER": "alice",
        "LATTICE_FUSEKI_PASSWORD": "secret",
    })

    assert config.fuseki_dataset == "other"
    assert config.fuseki_user == "alice"
    assert config.fuseki_password == "secret"


# S7-08 --------------------------------------------------------------------------------------------


def test_the_publisher_sets_the_four_message_properties():
    channel = FakeChannel()
    captured_properties: dict = {}

    def properties_factory(**kwargs: Any) -> dict:
        captured_properties.update(kwargs)
        return kwargs

    publisher = RabbitMqResultPublisher(channel, properties_factory)

    publisher.publish("job-1", {"jobId": "job-1", "status": "completed"})

    assert channel.published
    exchange, routing_key, body, properties = channel.published[0]
    assert exchange == "lattice.authoring"
    assert routing_key == "lattice.authoring.analysis.completed"
    assert json.loads(body) == {"jobId": "job-1", "status": "completed"}
    assert captured_properties == {
        "content_type": "application/json",
        "message_id": "job-1",
        "correlation_id": "job-1",
        "delivery_mode": 2,
    }
    assert properties is captured_properties or properties == captured_properties
