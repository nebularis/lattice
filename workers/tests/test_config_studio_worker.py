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

    def put_graph(self, graph_iri: str, graph: Graph, others=None) -> None:
        self.graphs[graph_iri] = Graph() + graph
        self.history.append((graph_iri, Graph() + graph))
        for name, other in (others or {}).items():
            self.graphs[name] = Graph() + other


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
    g.add((job, CST.workspace, URIRef("urn:lattice:studio:ws:00000000-0000-0000-0000-000000000001")))
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


MAPPING = """@prefix mork: <http://www.nebularis.org/ontologies/Mork#> .
@prefix ins: <https://www.nebularis.org/neuro-semantic/lattice/instrument#> .
@prefix ex: <https://example.org/m#> .
ex:S a mork:MappingScheme ; mork:compilationMode mork:ReviewMode .
ex:Rule a mork:Entity .
ex:RuleMapping a mork:Datum ; mork:mappingScheme ex:S ; mork:mappingFor ex:Rule ; mork:exactTBoxMatch ins:Obligatio ; mork:conceptName "rule" .
ex:Rule_Act a mork:DataMapping ; mork:mappingScheme ex:S ; mork:compositeBroaderMapping ex:RuleMapping ; mork:exactRBoxMatch ins:activity ;
    mork:dataRef "ex:act(" .
"""


def test_a_mapping_validates_by_compiling_with_mork_rdf_each_finding_on_its_mapping(tmp_path):
    config = tmp_path / "mapping.ttl"
    config.write_text(MAPPING, encoding="utf-8")
    g, job = run("validate", "mapping", config)
    assert (job, CST.conforms, Literal(False)) in g
    found = {(str(g.value(r, CST.code)), str(g.value(r, SH.focusNode))) for r in results(g, job, SH.Violation)}
    assert found == {("UnknownTarget", "https://example.org/m#RuleMapping"), ("BadPath", "https://example.org/m#Rule_Act")}


def test_a_mapping_compiles_to_its_compiled_form_and_queries(tmp_path):
    config = tmp_path / "mapping.ttl"
    config.write_text(MAPPING.replace("ins:Obligatio ", "ins:Obligation ").replace('"ex:act("', '"<http://www.w3.org/2000/01/rdf-schema#label>"'), encoding="utf-8")
    g, job = run("compile", "mapping", config)
    assert (job, CST.conforms, Literal(True)) in g
    assert sorted(artefacts(g, job)) == ["S.compiled.ttl", "S.rq"]
    assert "CONSTRUCT" in artefacts(g, job)["S.rq"][1]


def test_a_mapping_runs_over_a_sample_writing_each_mapping_s_output_by_stratum(tmp_path):
    odrl = ROOT / "contracts" / "config-studio" / "odrl"
    config = Graph().parse(odrl / "odrl-instrument.mork.ttl")
    document = URIRef("urn:lattice:studio:ws:00000000-0000-0000-0000-000000000001:import/1")
    config.add((document, RDF.type, CST.ImportDocument))
    config.add((document, CST.documentContent, Literal((odrl / "trial" / "software-licence.ttl").read_text(encoding="utf-8"))))
    config.add((document, CST.documentMediaType, Literal("text/turtle")))
    path = tmp_path / "mapping.ttl"
    config.serialize(path, format="turtle")
    store = FakeStore()
    iri = submit(store, "validate", "mapping", path)
    job = URIRef(iri)
    store.graphs[iri].set((job, CST.kind, CST.DryRunJob))
    ConfigStudioWorker(store, ROOT, _clock()).handle(iri)
    g = store.graphs[iri]
    assert (job, CST.status, CST.Succeeded) in g
    out = {str(g.value(a, CST.group)).rsplit("#", 1)[-1]: (int(g.value(a, CST.stratum)), str(g.value(a, CST.content))) for a in g.objects(job, CST.artefact)}
    # The licence's one permission becomes a stated term and a permission, each written by its own mapping.
    assert out["Permission"][0] == 0
    assert "instrument#Term>" in out["Permission"][1] and "instrument#Permission>" in out["Permission_Relation"][1]


def test_a_mapping_s_dry_run_refuses_a_sample_given_as_json_ld(tmp_path):
    config = Graph()
    document = URIRef("urn:lattice:studio:ws:00000000-0000-0000-0000-000000000001:import/1")
    config.add((document, RDF.type, CST.ImportDocument))
    config.add((document, CST.documentContent, Literal("{}")))
    config.add((document, CST.documentMediaType, Literal("application/ld+json")))
    path = tmp_path / "mapping.ttl"
    config.serialize(path, format="turtle")
    store = FakeStore()
    iri = submit(store, "validate", "mapping", path)
    store.graphs[iri].set((URIRef(iri), CST.kind, CST.DryRunJob))
    ConfigStudioWorker(store, ROOT, _clock()).handle(iri)
    assert "Turtle or N-Triples" in str(store.graphs[iri].value(URIRef(iri), CST.failureMessage))


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
    (CST.contextGraph, "urn:lattice:studio:ws:00000000-0000-0000-0000-000000000002:surface"),
    (CST.contextGraph, "urn:lattice:studio:ws:00000000-0000-0000-0000-000000000001:baseline:1"),
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
    assert (exchange, key) == ("lattice.studio.writes", str(int(ws[:8], 16) % 8))
    assert uuid.UUID(headers.pop("id")).version == 4
    assert headers == {"sender": "worker", "command": "job-update", "workspace": ws, "job": job}
    sent = Dataset().parse(data=body.decode("utf-8"), format="nquads")
    assert to_isomorphic(sent.graph(URIRef(iri))) == to_isomorphic(graph)


def test_a_graph_naming_no_workspace_is_never_sent():
    iri = f"urn:lattice:studio:job:{uuid.uuid4()}"
    publisher = FakePublisher()
    with pytest.raises(ValueError):
        WriterStore(FakeStore(), publisher).put_graph(iri, Graph())
    assert publisher.sent == []


def test_the_partition_is_the_one_java_computes():
    from lattice_workers.config_studio_worker import routing_key

    # The same ids as the service's TopologyTest.
    assert routing_key("ffffffff-0000-4000-8000-000000000000") == "7"
    assert routing_key("00000000-ffff-4000-8000-000000000000") == "0"
    assert routing_key("0000000d-0000-4000-8000-000000000000") == "5"


def test_an_analysis_gives_the_analysis_view_and_the_proposals_of_its_document():
    store = FakeStore()
    iri = submit(store, "analyse", "persistence", None)
    job = URIRef(iri)
    store.graphs[iri].remove((job, CST.target, None))
    document = Graph()
    document.parse(ROOT / "contracts" / "xml" / "document-to-wording" / "1.0.0" / "expected" / "software-licence.nt", format="nt")
    store.graphs[f"{iri}:input"] = document
    ConfigStudioWorker(store, ROOT, _clock()).handle(iri)
    g = store.graphs[iri]
    assert g.value(job, CST.status) == CST.Succeeded, g.value(job, CST.failureMessage)
    found = artefacts(g, job)
    assert set(found) == {"analysis.json", "proposals.ttl"}
    view = json.loads(found["analysis.json"][1])
    assert view["elements"] and "graphView" in view
    assert len(Graph().parse(data=found["proposals.ttl"][1], format="turtle")) > 0


def test_an_analysis_of_a_graph_holding_no_wording_fails():
    store = FakeStore()
    iri = submit(store, "analyse", "persistence", None)
    ConfigStudioWorker(store, ROOT, _clock()).handle(iri)
    g = store.graphs[iri]
    assert g.value(URIRef(iri), CST.status) == CST.Failed
    assert "0 wordings" in str(g.value(URIRef(iri), CST.failureMessage))


WORDING_EXAMPLES = CATALOGUE.module("wording").directory("examples")
ASSEMBLY = """
@prefix cst: <https://www.nebularis.org/neuro-semantic/lattice/config-studio#> .
@prefix wrd: <https://www.nebularis.org/neuro-semantic/lattice/wording#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
@prefix f: <https://example.org/lattice/wording/facility-form/> .
@prefix a: <https://example.org/assembly/> .
a:facility a cst:Assembly ; cst:assembles f:form ; cst:choice f:cl-5-2b ; cst:setting a:lenders , a:jurisdictions .
a:lenders a wrd:VariableValue ; wrd:forVariable f:gv-lender-count ; wrd:literalValue "{count}"^^xsd:decimal .
a:jurisdictions a wrd:VariableValue ; wrd:forVariable f:var-jurisdictions ; wrd:value f:uk , f:ie .
"""


def _facility_form() -> Graph:
    g = Graph().parse(ROOT / WORDING_EXAMPLES / "facility-form.ttl")
    wrd = "https://www.nebularis.org/neuro-semantic/lattice/wording#"
    for record in list(g.subjects(RDF.type, URIRef(wrd + "AssembledWording"))):
        for value in list(g.objects(record, URIRef(wrd + "hasValue"))):
            g.remove((value, None, None))
        g.remove((record, None, None))
    return g


def _assemble(count: str) -> tuple[FakeStore, URIRef]:
    store = FakeStore()
    iri = submit(store, "assemble", "persistence", None)
    job = URIRef(iri)
    store.graphs[iri].remove((job, CST.target, None))
    store.graphs[iri].add((job, CST.target, CST.AssemblyTarget))
    store.graphs[f"{iri}:input"] = _facility_form() + Graph().parse(data=ASSEMBLY.replace("{count}", count), format="turtle")
    ConfigStudioWorker(store, ROOT, _clock()).handle(iri)
    return store, job


def test_an_assembly_gives_its_record_and_document_and_writes_the_record():
    store, job = _assemble("3")
    g = store.graphs[str(job)]
    assert g.value(job, CST.status) == CST.Succeeded, g.value(job, CST.failureMessage)
    assert g.value(job, CST.conforms) == Literal(True)
    found = artefacts(g, job)
    assert set(found) == {"record.ttl", "document.xml"}
    assert found["document.xml"][1].startswith("<") and "https://www.nebularis.org/neuro-semantic/lattice/document/1" in found["document.xml"][1]
    record = store.graphs[f"{job}:record"]
    wrd = "https://www.nebularis.org/neuro-semantic/lattice/wording#"
    assert len(list(record.subjects(RDF.type, URIRef(wrd + "AssembledWording")))) == 1
    assert all(str(s).startswith(f"{job}:record/") for s in record.subjects(RDF.type, URIRef(wrd + "AssembledWording")))


def test_the_same_job_assembles_the_same_record():
    first, job = _assemble("3")
    again = FakeStore()
    again.graphs = {k: Graph() + v for k, v in first.graphs.items() if not k.endswith(":record")}
    again.graphs[str(job)] = Graph() + first.history[0][1]
    again.graphs[str(job)].remove((job, CST.status, None))
    again.graphs[str(job)].add((job, CST.status, CST.Queued))
    ConfigStudioWorker(again, ROOT, _clock()).handle(str(job))
    assert to_isomorphic(first.graphs[f"{job}:record"]) == to_isomorphic(again.graphs[f"{job}:record"])


def test_an_assembly_without_its_settings_is_refused_with_no_record():
    store = FakeStore()
    iri = submit(store, "assemble", "persistence", None)
    store.graphs[f"{iri}:input"] = _facility_form() + Graph().parse(data=ASSEMBLY.split("a:lenders a")[0].replace(" , a:jurisdictions", "").replace("cst:setting a:lenders", "cst:choice f:cl-5-2b"), format="turtle")
    ConfigStudioWorker(store, ROOT, _clock()).handle(iri)
    g = store.graphs[iri]
    assert g.value(URIRef(iri), CST.conforms) == Literal(False)
    assert results(g, URIRef(iri), SH.Violation)
    assert f"{iri}:record" not in store.graphs


def test_a_library_validates_each_form():
    store = FakeStore()
    iri = submit(store, "validate", "persistence", None)
    job = URIRef(iri)
    store.graphs[iri].remove((job, CST.target, None))
    store.graphs[iri].add((job, CST.target, CST.Library))
    store.graphs[f"{iri}:input"] = _facility_form()
    ConfigStudioWorker(store, ROOT, _clock()).handle(iri)
    g = store.graphs[iri]
    assert g.value(job, CST.status) == CST.Succeeded, g.value(job, CST.failureMessage)
    assert g.value(job, CST.conforms) == Literal(True), [str(g.value(r, SH.resultMessage)) for r in results(g, job, SH.Violation)]


def test_a_library_validated_beside_its_assemblies_reports_nothing_of_theirs():
    store = FakeStore()
    iri = submit(store, "validate", "persistence", None)
    job = URIRef(iri)
    store.graphs[iri].remove((job, CST.target, None))
    store.graphs[iri].add((job, CST.target, CST.Library))
    store.graphs[f"{iri}:input"] = _facility_form() + Graph().parse(data=ASSEMBLY.replace("{count}", "3"), format="turtle")
    ConfigStudioWorker(store, ROOT, _clock()).handle(iri)
    g = store.graphs[iri]
    assert g.value(job, CST.conforms) == Literal(True), [str(g.value(r, SH.resultMessage)) for r in results(g, job, SH.Violation)]


def _validate_meaning(input_graph: Graph) -> tuple[Graph, URIRef]:
    store = FakeStore()
    iri = submit(store, "validate", "persistence", None)
    job = URIRef(iri)
    store.graphs[iri].remove((job, CST.target, None))
    store.graphs[iri].add((job, CST.target, CST.Meaning))
    store.graphs[f"{iri}:input"] = input_graph
    ConfigStudioWorker(store, ROOT, _clock()).handle(iri)
    return store.graphs[iri], job


def _builder_sample() -> Graph:
    g = Graph()
    for part in ("builder-assemblies.ttl", "builder-meaning.ttl"):
        g.parse(ROOT / CATALOGUE.area("contracts") / "config-studio" / "samples" / part)
    return g + _facility_form()


def test_stated_meaning_is_checked_with_instruments_shapes():
    g, job = _validate_meaning(_builder_sample())
    assert g.value(job, CST.status) == CST.Succeeded, g.value(job, CST.failureMessage)
    assert g.value(job, CST.conforms) == Literal(True), [str(g.value(r, SH.resultMessage)) for r in results(g, job, SH.Violation)]


def test_a_template_naming_no_element_is_a_violation():
    sample = _builder_sample()
    ins = "https://www.nebularis.org/neuro-semantic/lattice/instrument#"
    sample.remove((URIRef("https://example.org/lattice/studio/meaning/term-9-1"), URIRef(ins + "expressedIn"), None))
    g, job = _validate_meaning(sample)
    assert g.value(job, CST.conforms) == Literal(False)
    assert any("term-9-1" in str(g.value(r, SH.focusNode)) for r in results(g, job, SH.Violation))


# ---- proposers (CB3) --------------------------------------------------------------------------------------------------


def _propose(target, env=None) -> tuple[FakeStore, URIRef]:
    import os
    from unittest import mock

    store = FakeStore()
    iri = submit(store, "propose", "persistence", None)
    job = URIRef(iri)
    store.graphs[iri].remove((job, CST.target, None))
    store.graphs[iri].add((job, CST.target, target))
    # The roles are in the baseline, as the browser splits the sample, and the input holds the configurations.
    sample = _builder_sample()
    roles = Graph()
    pty = "https://www.nebularis.org/neuro-semantic/lattice/party#"
    for role in sample.subjects(RDF.type, URIRef(pty + "Role")):
        for triple in sample.triples((role, None, None)):
            roles.add(triple)
    store.graphs[f"{iri}:input"] = sample - roles
    store.graphs["urn:lattice:studio:ws:00000000-0000-0000-0000-000000000001:baseline:1"] = roles
    with mock.patch.dict(os.environ, env or {}, clear=False):
        ConfigStudioWorker(store, ROOT, _clock()).handle(iri)
    return store, job


def _review(store: FakeStore, job: URIRef) -> Graph:
    found = artefacts(store.graphs[str(job)], job)
    return Graph().parse(data=found["review.ttl"][1], format="turtle")


def test_the_sentence_form_proposer_proposes_for_clauses_with_no_meaning_and_none_waiting():
    store, job = _propose(CST.SentenceFormProposer)
    g = store.graphs[str(job)]
    assert g.value(job, CST.status) == CST.Succeeded, g.value(job, CST.failureMessage)
    review = _review(store, job)
    spans = {str(review.value(p, CST.span)).rsplit("/", 1)[-1] for p in review.subjects(RDF.type, CST.Proposal)}
    assert not spans & {"cl-5-1", "cl-9-1", "cl-5-3"}, "a clause with meaning or a waiting proposal is not proposed for"
    assert spans == {"cl-12-1"}, "the two interest-period variants read no relation"
    assert {str(review.value(p, CST.evidence)) for p in review.subjects(RDF.type, CST.Proposal)} == {"The borrower may operate in {permitted-jurisdictions}"}
    for p in review.subjects(RDF.type, CST.Proposal):
        assert review.value(p, CST.decision) is None
        assert str(review.value(p, CST.proposer)) == "sentence-forms"
        payload = Graph().parse(data=str(review.value(p, CST.payload)), format="turtle")
        ins = "https://www.nebularis.org/neuro-semantic/lattice/instrument#"
        assert (None, URIRef(ins + "expressedIn"), review.value(p, CST.span)) in payload
        assert (None, RDF.type, URIRef(ins + "Permission")) in payload
        assert (None, URIRef(ins + "holder"), URIRef("https://example.org/lattice/studio/roles/Borrower")) in payload


def test_the_same_proposals_come_from_the_same_job():
    first, job = _propose(CST.SentenceFormProposer)
    again, job2 = _propose(CST.SentenceFormProposer)
    strip = lambda s, j: str(artefacts(s.graphs[str(j)], j)["review.ttl"][1]).replace(str(j), "JOB")
    assert strip(first, job) == strip(again, job2)


def test_a_language_model_proposer_without_configuration_fails_saying_so():
    store, job = _propose(CST.LanguageModelProposer, {"LATTICE_PROPOSER_URL": "", "LATTICE_PROPOSER_MODEL": "", "LATTICE_PROPOSER_PACK": ""})
    g = store.graphs[str(job)]
    assert g.value(job, CST.status) == CST.Failed
    assert "no language model is configured" in str(g.value(job, CST.failureMessage))


def test_a_language_model_proposer_asks_its_endpoint_with_its_pack_and_keeps_only_declared_labels():
    import http.server
    import threading

    asked = []

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            asked.append((self.path, self.headers.get("Authorization"), body))
            clause = body["messages"][1]["content"].strip()
            reply = {"candidates": [{"kind": "Permission", "role": "Borrower", "counterRole": "Lender", "activity": "Teleport",
                                     "evidence": clause[:20]}]}
            out = json.dumps({"choices": [{"message": {"content": "```json\n" + json.dumps(reply) + "\n```"}}]}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(out)))
            self.end_headers()
            self.wfile.write(out)

        def log_message(self, *args):
            pass

    server = http.server.HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        store, job = _propose(CST.LanguageModelProposer, {
            "LATTICE_PROPOSER_URL": f"http://127.0.0.1:{server.server_port}/v1", "LATTICE_PROPOSER_MODEL": "test-model",
            "LATTICE_PROPOSER_PACK": str(Path(__file__).parent / "fixtures" / "proposer-pack"), "LATTICE_PROPOSER_KEY": "secret",
        })
    finally:
        server.shutdown()
    g = store.graphs[str(job)]
    assert g.value(job, CST.status) == CST.Succeeded, g.value(job, CST.failureMessage)
    assert asked and asked[0][0] == "/v1/chat/completions" and asked[0][1] == "Bearer secret"
    assert asked[0][2]["model"] == "test-model" and "Borrower" in asked[0][2]["messages"][0]["content"]
    review = _review(store, job)
    proposals = list(review.subjects(RDF.type, CST.Proposal))
    assert proposals
    p = proposals[0]
    assert "pack test-echo 0" in str(review.value(p, CST.proposerVersion))
    assert "no activity 'Teleport' is declared" in str(review.value(p, CST.evidence))
    payload = Graph().parse(data=str(review.value(p, CST.payload)), format="turtle")
    ins = "https://www.nebularis.org/neuro-semantic/lattice/instrument#"
    assert (None, URIRef(ins + "holder"), URIRef("https://example.org/lattice/studio/roles/Borrower")) in payload
    assert not list(payload.objects(None, URIRef(ins + "activity")))


# ---- dry run (CB4) -----------------------------------------------------------------------------------------------------

F = "https://example.org/lattice/wording/facility-form/"


def _dry_run(facts: str) -> tuple[Graph, URIRef]:
    store = FakeStore()
    iri = submit(store, "dry-run", "persistence", None)
    job = URIRef(iri)
    store.graphs[iri].remove((job, CST.target, None))
    store.graphs[iri].add((job, CST.target, CST.Meaning))
    store.graphs[iri].remove((job, CST.kind, None))
    store.graphs[iri].add((job, CST.kind, CST.DryRunJob))
    request = Graph().parse(data=f"""
        @prefix cst: <https://www.nebularis.org/neuro-semantic/lattice/config-studio#> .
        @prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
        <urn:x:run> a cst:DryRun ; cst:term <https://example.org/lattice/studio/meaning/term-9-1> {facts} .
        """, format="turtle")
    store.graphs[f"{iri}:input"] = _builder_sample() + request
    ConfigStudioWorker(store, ROOT, _clock()).handle(iri)
    return store.graphs[iri], job


def _decisions(g: Graph, job: URIRef) -> dict:
    return {str(g.value(r, CST.condition)).rsplit("/", 1)[-1]: str(g.value(r, CST.decision)).rsplit("#", 1)[-1] for r in g.objects(job, CST.testResult)}


@pytest.mark.parametrize("count, decision", [("3", "Permitted"), ("1", "Denied")])
def test_a_dry_run_decides_the_terms_condition_over_a_sample_number(count, decision):
    g, job = _dry_run(f'; cst:fact [ cst:forCondition <{F}when-syndicated-more-than-one-lender> ; cst:number "{count}"^^xsd:decimal ]')
    assert g.value(job, CST.status) == CST.Succeeded, g.value(job, CST.failureMessage)
    assert _decisions(g, job) == {"when-syndicated-more-than-one-lender": decision}


def test_a_dry_run_without_a_fact_reads_undetermined_and_says_so():
    g, job = _dry_run("")
    assert _decisions(g, job) == {"when-syndicated-more-than-one-lender": "Undetermined"}
    assert any("No sample fact" in str(g.value(r, SH.resultMessage)) for r in results(g, job, SH.Info))


def test_a_fact_for_a_condition_the_term_does_not_read_is_reported():
    g, job = _dry_run(f'; cst:fact [ cst:forCondition <{F}elsewhere> ; cst:number "1"^^xsd:decimal ]')
    assert any("does not read" in str(g.value(r, SH.resultMessage)) for r in results(g, job, SH.Info))


# ---- the ODRL proposer (CB5a) -----------------------------------------------------------------------------------------

ODRL_SAMPLE = ROOT / "contracts" / "config-studio" / "odrl" / "software-licence.odrl.jsonld"
INS_NS = "https://www.nebularis.org/neuro-semantic/lattice/instrument#"


def _import(content: str, media: str = "application/ld+json", profile: str = "http://www.w3.org/ns/odrl/2/", clause=None):
    from rdflib.namespace import DCTERMS

    store = FakeStore()
    iri = submit(store, "propose", "persistence", None)
    job = URIRef(iri)
    store.graphs[iri].remove((job, CST.target, None))
    store.graphs[iri].add((job, CST.target, CST.OdrlProposer))
    doc = URIRef(f"{iri}:document")
    source = Graph()
    source.add((doc, RDF.type, CST.ImportDocument))
    source.add((doc, CST.documentContent, Literal(content)))
    source.add((doc, CST.documentMediaType, Literal(media)))
    source.add((doc, DCTERMS.conformsTo, URIRef(profile)))
    if clause is not None:
        source.add((doc, CST.importInto, URIRef(clause)))
    store.graphs[f"{iri}:input"] = source
    ConfigStudioWorker(store, ROOT, _clock()).handle(iri)
    return store.graphs[iri], job


def _parts(g: Graph, job: URIRef) -> dict[str, Graph]:
    return {path: Graph().parse(data=content, format="turtle") for path, (_, content, _) in artefacts(g, job).items()}


def test_an_odrl_policy_gives_a_proposal_for_each_rule_and_the_prohibition_its_permission_excepts():
    g, job = _import(ODRL_SAMPLE.read_text())
    assert g.value(job, CST.status) == CST.Succeeded, g.value(job, CST.failureMessage)
    parts = _parts(g, job)
    assert set(parts) == {"review.ttl", "eligibility.ttl", "quantification.ttl", "baseline.ttl", "vocabulary.ttl", "library.ttl"}
    review, library = parts["review.ttl"], parts["library.ttl"]
    proposals = list(review.subjects(RDF.type, CST.Proposal))
    assert len(proposals) == 4, "a permission, the prohibition it excepts, a prohibition and an obligation"
    kinds = set()
    for p in proposals:
        payload = Graph().parse(data=str(review.value(p, CST.payload)), format="turtle")
        assert {str(o) for o in payload.objects(None, RDF.type)} <= {INS_NS + k for k in ("Term", "Template", "Permission", "Prohibition", "Obligation", "OnAct")}
        assert (review.value(p, CST.span), RDF.type, URIRef("https://www.nebularis.org/neuro-semantic/lattice/wording#Text")) in library
        kinds |= {str(o).rsplit("#", 1)[-1] for o in payload.objects(None, RDF.type)}
        if (None, URIRef(INS_NS + "excepts"), None) in payload:
            assert (None, URIRef(INS_NS + "arisesOn"), None) in payload, "the permission arises on the act of its duty"
    assert {"Permission", "Prohibition", "Obligation"} <= kinds
    assert len(set(parts["baseline.ttl"].subjects())) == 2, "one role for each party"
    qnt = "https://www.nebularis.org/neuro-semantic/lattice/quantification#"
    bounds = parts["quantification.ttl"]
    bound = next(bounds.subjects(RDF.type, URIRef(qnt + "Bound")))
    assert (bound, URIRef(qnt + "boundSense"), URIRef(qnt + "Upper")) in bounds and (bound, URIRef(qnt + "boundClosure"), URIRef(qnt + "Open")) in bounds
    assert str(bounds.value(bounds.value(bound, URIRef(qnt + "boundValue")), URIRef(qnt + "numericValue"))) == "2030-01-01"
    assert not results(g, job, SH.Warning), "the guards leave nothing for the reviewer to complete in the sample"


def test_an_odrl_import_into_a_picked_clause_proposes_every_term_on_it():
    clause = "https://example.org/lattice/studio/library/cl-1"
    g, job = _import(ODRL_SAMPLE.read_text(), clause=clause)
    parts = _parts(g, job)
    assert "library.ttl" not in parts
    assert {str(o) for o in parts["review.ttl"].objects(None, CST.span)} == {clause}


@pytest.mark.parametrize("change, message", [
    (dict(profile="http://example.org/other"), "not ODRL 2.2"),
    (dict(media="application/xml"), "not application/xml"),
    (dict(content=ODRL_SAMPLE.read_text().replace("http://www.w3.org/ns/odrl.jsonld", "https://example.org/context.jsonld")), "remote context"),
])
def test_an_odrl_import_refuses_a_document_that_does_not_say_it_is_odrl(change, message):
    arguments = dict(content=ODRL_SAMPLE.read_text())
    arguments.update(change)
    g, job = _import(**arguments)
    assert g.value(job, CST.status) == CST.Failed and message in str(g.value(job, CST.failureMessage))


def test_the_same_policy_gives_the_same_proposals():
    first, job = _import(ODRL_SAMPLE.read_text())
    again, job2 = _import(ODRL_SAMPLE.read_text())
    strip = lambda g, j: artefacts(g, j)["review.ttl"][1].replace(str(j), "JOB")
    assert strip(first, job) == strip(again, job2)


def test_an_odrl_party_named_as_a_workspace_role_reuses_that_role():
    from rdflib.namespace import DCTERMS, RDFS
    pty = "https://www.nebularis.org/neuro-semantic/lattice/party#"
    store = FakeStore()
    iri = submit(store, "propose", "persistence", None)
    job = URIRef(iri)
    store.graphs[iri].remove((job, CST.target, None))
    store.graphs[iri].add((job, CST.target, CST.OdrlProposer))
    doc = URIRef(f"{iri}:document")
    source = Graph()
    for p, o in ((RDF.type, CST.ImportDocument), (CST.documentContent, Literal(ODRL_SAMPLE.read_text())),
                 (CST.documentMediaType, Literal("application/ld+json")), (DCTERMS.conformsTo, URIRef("http://www.w3.org/ns/odrl/2/"))):
        source.add((doc, p, o))
    store.graphs[f"{iri}:input"] = source
    licensee = URIRef("https://example.org/lattice/studio/roles/Licensee")
    baseline = Graph()
    baseline.add((licensee, RDF.type, URIRef(pty + "Role")))
    baseline.add((licensee, RDFS.label, Literal("fernwood analytics ltd")))
    store.graphs["urn:lattice:studio:ws:00000000-0000-0000-0000-000000000001:baseline:1"] = baseline
    ConfigStudioWorker(store, ROOT, _clock()).handle(iri)
    g = store.graphs[iri]
    assert g.value(job, CST.status) == CST.Succeeded, g.value(job, CST.failureMessage)
    parts = _parts(g, job)
    assert len(set(parts["baseline.ttl"].subjects())) == 1, "only the licensor's role is new"
    payloads = [Graph().parse(data=str(o), format="turtle") for o in parts["review.ttl"].objects(None, CST.payload)]
    assert any((None, URIRef(INS_NS + "holder"), licensee) in p for p in payloads)


def test_a_publish_job_names_the_version_of_the_unit_it_names():
    """ADR-A149: the worker answers a publish job with the version, and fails one that names no unit."""
    store = FakeStore()
    job_iri = submit(store, "validate", "vocabulary", None)
    job = URIRef(job_iri)
    g = store.graphs[job_iri]
    g.set((job, CST.kind, CST.Publish))
    g.set((job, CST.unit, URIRef("https://example.org/perils")))
    store.graphs[f"{job_iri}:input"] = Graph().parse(data="""
        @prefix skos: <http://www.w3.org/2004/02/skos/core#> .
        <https://example.org/perils> a skos:ConceptScheme . <https://example.org/fire> skos:inScheme <https://example.org/perils> .""",
        format="turtle")
    ConfigStudioWorker(store, ROOT, _clock()).handle(job_iri)
    done = store.graphs[job_iri]
    assert done.value(job, CST.status) == CST.Succeeded
    assert str(done.value(job, CST.version)).startswith("https://example.org/perils/rev/1-")
    g = store.graphs[job_iri]
    g.set((job, CST.status, CST.Queued))
    g.set((job, CST.unit, URIRef("https://example.org/fire")))
    ConfigStudioWorker(store, ROOT, _clock()).handle(job_iri)
    assert store.graphs[job_iri].value(job, CST.status) == CST.Failed


def test_a_dependency_s_version_is_read_as_context_under_its_version_and_its_lineage():
    """ADR-A149: a draft that follows a lineage names the lineage, so its version is read under both IRIs."""
    store = FakeStore()
    job_iri = submit(store, "validate", "vocabulary", None)
    job = URIRef(job_iri)
    graph_iri = "urn:lattice:studio:pub:" + "a" * 32 + ":rev:" + "b" * 16
    lineage, version = URIRef("https://example.org/perils"), URIRef("https://example.org/perils/rev/1-" + "b" * 16)
    v = Graph()
    v.add((version, URIRef("https://www.nebularis.org/neuro-semantic/lattice/foundation#hasIdentity"), lineage))
    v.add((URIRef("https://example.org/fire"), URIRef("http://www.w3.org/2004/02/skos/core#inScheme"), version))
    store.graphs[graph_iri] = v
    store.graphs[job_iri].add((job, CST.contextGraph, URIRef(graph_iri)))
    context = ConfigStudioWorker(store, ROOT, _clock())._context(store.graphs[job_iri], job)
    fire, in_scheme = URIRef("https://example.org/fire"), URIRef("http://www.w3.org/2004/02/skos/core#inScheme")
    assert (fire, in_scheme, version) in context and (fire, in_scheme, lineage) in context
