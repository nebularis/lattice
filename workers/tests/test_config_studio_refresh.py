"""Tests for the Configuration Studio worker's refresh job (ADR-A149 decision 14), against an in-memory store."""

from __future__ import annotations

import uuid

from rdflib import BNode, Dataset, Graph, Literal, URIRef
from rdflib.namespace import RDF, RDFS, XSD

from lattice_workers.config_studio_jobs import CST
from lattice_workers.config_studio_refresh import KEYS, PRJ, PROJECTION, DatasetStore, refresh
from lattice_workers.config_studio_worker import ConfigStudioWorker, WriterStore

from test_config_studio_worker import FakePublisher, FakeStore

PAT = "https://www.nebularis.org/neuro-semantic/lattice/persistence-store#"
SKOS = "http://www.w3.org/2004/02/skos/core#"
FND = "https://www.nebularis.org/neuro-semantic/lattice/foundation#"
JOB = "urn:lattice:studio:job:00000000-0000-0000-0000-0000000000f1"
WS = "urn:lattice:studio:ws:00000000-0000-0000-0000-000000000001"
DOC = f"{WS}:document:00000000-0000-0000-0000-000000000009"
LINEAGE = "https://example.org/scheme"
VERSION = f"{LINEAGE}/rev/1-0123456789abcdef"


class Store(DatasetStore):
    """A dataset that is also the worker's store, so a refresh job reads what it is given and the writes are recorded."""

    def __init__(self, dataset: Dataset) -> None:
        super().__init__(dataset)
        self.puts: list[tuple[str, Graph, dict]] = []

    def put_graph(self, graph_iri: str, graph: Graph, others=None) -> None:
        self.puts.append((graph_iri, Graph() + graph, dict(others or {})))


def small_store() -> Dataset:
    ds = Dataset()
    turtle = lambda name, text: ds.graph(URIRef(name)).parse(
        data=f"@prefix cst: <{CST}> . @prefix rdfs: <{RDFS}> . @prefix skos: <{SKOS}> . @prefix fnd: <{FND}> . @prefix pat: <{PAT}> .\n" + text,
        format="turtle")
    turtle("urn:lattice:studio:description/a", f"""
        <{WS}> a cst:Workspace ; rdfs:label "Alpha" ; cst:modifiedAt "2026-10-27T10:00:00Z"^^<{XSD.dateTime}> ; cst:owner "ann" ; cst:mode cst:locked ;
            cst:dependsOn <{LINEAGE}> ; cst:holdsImport <urn:lattice:studio:import:{'a' * 64}> ; cst:document <{DOC}> .""")
    turtle("urn:g:meta/part", f"""
        <{WS}/part/baseline> pat:seq 3 . <{WS}/part/library> pat:seq 2 ; pat:deleted true . <{DOC}> pat:seq 5 .""")
    turtle(f"urn:lattice:studio:lineage/{LINEAGE}", f"<{LINEAGE}> a fnd:PersistentIdentity ; cst:current <{VERSION}> .")
    turtle("urn:lattice:studio:version/v1", f"""
        <{LINEAGE}/c1> a skos:Concept ; skos:prefLabel "Fire" ; skos:inScheme <{VERSION}> .
        <{LINEAGE}/other> a skos:ConceptScheme ; skos:prefLabel "Not a concept" .""")
    turtle("urn:lattice:studio:job:00000000-0000-0000-0000-0000000000a1", f"""
        <urn:lattice:studio:job:00000000-0000-0000-0000-0000000000a1> a cst:Job ; cst:workspace <{WS}> ; cst:status cst:Queued .""")
    turtle(JOB, f"<{JOB}> a cst:Job ; cst:kind cst:Refresh ; cst:status cst:Running .")
    turtle("urn:lattice:studio:job:00000000-0000-0000-0000-0000000000a1:input", f"<{WS}> cst:workspace <urn:not-a-job> .")
    return ds


def content(graph: Graph) -> set:
    return {t for t in graph if not str(t[0]).startswith(PROJECTION)}


def test_each_promotion_restates_its_property_and_nothing_of_a_refresh_job():
    out = refresh(Store(small_store()), None, JOB, "2026-10-31T10:00:00Z")
    assert set(out) == {PROJECTION + key for key in KEYS}
    assert content(out[PROJECTION + "registry"]) == {(URIRef(LINEAGE), PRJ.current, URIRef(VERSION))}
    assert content(out[PROJECTION + "jobs"]) == {(URIRef("urn:lattice:studio:job:00000000-0000-0000-0000-0000000000a1"), PRJ.workspace, URIRef(WS))}
    assert content(out[PROJECTION + "holders"]) == {
        (URIRef(WS), PRJ.dependsOn, URIRef(LINEAGE)), (URIRef(WS), PRJ.holdsImport, URIRef(f"urn:lattice:studio:import:{'a' * 64}"))}
    concept = URIRef(f"{LINEAGE}/c1")
    assert content(out[PROJECTION + "terms"]) == {(concept, PRJ.prefLabel, Literal("Fire")), (concept, PRJ.inScheme, URIRef(VERSION))}


def test_the_summaries_give_the_workspace_and_the_sequence_of_each_live_row_or_nought():
    summary = content(refresh(Store(small_store()), None, JOB, "2026-10-31T10:00:00Z")[PROJECTION + "summaries"])
    ws, cst = URIRef(WS), lambda name: URIRef(str(CST) + name)
    revision = lambda name: next(o for s, p, o in summary if s == ws and p == cst(name + "Revision"))
    assert (ws, RDFS.label, Literal("Alpha")) in summary
    assert (ws, cst("owner"), Literal("ann")) in summary and (ws, cst("mode"), CST.locked) in summary
    assert (revision("baseline"), revision("library"), revision("persistence")) == (Literal(3), Literal(0), Literal(0))
    assert (ws, cst("dependsOn"), URIRef(LINEAGE)) in summary and (ws, cst("holdsImport"), URIRef(f"urn:lattice:studio:import:{'a' * 64}")) in summary
    assert (URIRef(DOC), cst("revision"), Literal(5)) in summary and (ws, cst("document"), URIRef(DOC)) in summary
    assert len(summary) == 1 + 4 + 11 + 2 + 2 and not any(s == URIRef(f"{WS}/part/baseline") for s, _, _ in summary)


def test_each_projection_carries_one_refresh_node_naming_the_job_and_the_time_read():
    for name, graph in refresh(Store(small_store()), None, JOB, "2026-10-31T10:00:00Z").items():
        node = URIRef(name)
        assert (node, RDF.type, PRJ.Refresh) in graph
        assert list(graph.objects(node, PRJ.job)) == [URIRef(JOB)]
        assert [o.toPython().isoformat() for o in graph.objects(node, PRJ.readAt)] == ["2026-10-31T10:00:00+00:00"]
        assert not any(isinstance(term, BNode) for triple in graph for term in triple)


def test_a_refresh_job_hands_the_five_projections_to_the_writer_and_names_no_workspace():
    store = Store(small_store())
    ConfigStudioWorker(store, None, lambda: "2026-10-31T10:00:00Z").handle(JOB)
    running, final = store.puts
    assert (URIRef(JOB), CST.status, CST.Running) in running[1] and running[2] == {}
    assert (URIRef(JOB), CST.status, CST.Succeeded) in final[1]
    assert set(final[2]) == {PROJECTION + key for key in KEYS}
    assert not list(final[1].objects(URIRef(JOB), CST.workspace))


def test_a_refresh_that_cannot_read_fails_the_job_and_sends_no_projection():
    class Broken(Store):
        def graph_names(self):
            raise OSError("store down")

    store = Broken(small_store())
    ConfigStudioWorker(store, None, lambda: "2026-10-31T10:00:00Z").handle(JOB)
    assert (URIRef(JOB), CST.status, CST.Failed) in store.puts[-1][1] and store.puts[-1][2] == {}


def test_a_refresh_job_goes_to_the_writer_of_its_own_id_with_the_projections_beside_it():
    job = str(uuid.UUID("ffffffff-0000-4000-8000-000000000000"))
    iri = f"urn:lattice:studio:job:{job}"
    graph = Graph()
    graph.add((URIRef(iri), CST.kind, CST.Refresh))
    publisher = FakePublisher()
    WriterStore(FakeStore(), publisher).put_graph(iri, graph, {PROJECTION + "registry": Graph()})
    _, key, headers, _ = publisher.sent[0]
    assert key == "7" and "workspace" not in headers and headers["job"] == job
