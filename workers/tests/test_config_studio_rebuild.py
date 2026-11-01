"""Tests for the Configuration Studio worker's rebuild job (ADR-A149 decision 14), against an in-memory store."""

from __future__ import annotations

import uuid

import re
from pathlib import Path

from rdflib import BNode, Dataset, Graph, Literal, Namespace, URIRef
from rdflib.namespace import RDF, RDFS, XSD

from lattice_workers.config_studio_jobs import CST
from lattice_workers.config_studio_rebuild import PROMOTED, RECORD, DatasetStore, _declarations, digests, rebuild
from lattice_workers.config_studio_worker import ConfigStudioWorker, WriterStore

from test_config_studio_worker import FakePublisher, FakeStore

PRM = Namespace("https://www.nebularis.org/neuro-semantic/lattice/config-studio/promotion#")
SRF = Namespace("https://www.nebularis.org/neuro-semantic/lattice/surface#")
PAT = "https://www.nebularis.org/neuro-semantic/lattice/persistence-store#"
SKOS = "http://www.w3.org/2004/02/skos/core#"
FND = "https://www.nebularis.org/neuro-semantic/lattice/foundation#"
JOB = "urn:lattice:studio:job:00000000-0000-0000-0000-0000000000f1"
WS = "urn:lattice:studio:ws:00000000-0000-0000-0000-000000000001"
DOC = f"{WS}:document:00000000-0000-0000-0000-000000000009"
A1 = "urn:lattice:studio:job:00000000-0000-0000-0000-0000000000a1"
LINEAGE = "https://example.org/scheme"
VERSION = f"{LINEAGE}/rev/1-0123456789abcdef"


class Store(DatasetStore):
    """A dataset that is also the worker's store, so a rebuild job reads what it is given and the writes are recorded."""

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
    turtle(JOB, f"<{JOB}> a cst:Job ; cst:kind cst:Rebuild ; cst:status cst:Running .")
    turtle("urn:lattice:studio:job:00000000-0000-0000-0000-0000000000a1:input", f"<{WS}> cst:workspace <urn:not-a-job> .")
    return ds


LINEAGE_GRAPH = f"urn:lattice:studio:lineage/{LINEAGE}"
SOURCES = ["urn:lattice:studio:description/a", LINEAGE_GRAPH, "urn:lattice:studio:version/v1", A1, JOB]
NOW = "2026-10-31T10:00:00Z"


def rows(name: str, ds: Dataset | None = None) -> set:
    return set(rebuild(Store(ds or small_store()), None, JOB, NOW)[PROMOTED + name])


def test_each_source_graph_has_its_own_partition_holding_only_its_promoted_rows():
    assert rows(LINEAGE_GRAPH) == {(URIRef(LINEAGE), PRM.current, URIRef(VERSION))}
    assert rows(A1) == {(URIRef(A1), PRM.workspace, URIRef(WS))}
    assert rows("urn:lattice:studio:description/a") == {
        (URIRef(WS), PRM.dependsOn, URIRef(LINEAGE)), (URIRef(WS), PRM.holdsImport, URIRef(f"urn:lattice:studio:import:{'a' * 64}"))}
    concept = URIRef(f"{LINEAGE}/c1")
    assert rows("urn:lattice:studio:version/v1") == {(concept, PRM.prefLabel, Literal("Fire")), (concept, PRM.inScheme, URIRef(VERSION))}
    assert rows(JOB) == set()


def test_a_graph_that_is_no_family_source_has_no_partition():
    out = rebuild(Store(small_store()), None, JOB, NOW)
    assert set(out) == {PROMOTED + name for name in SOURCES} | {RECORD}
    assert PROMOTED + "urn:g:meta/part" not in out and PROMOTED + f"{A1}:input" not in out


def test_a_partition_whose_source_is_gone_comes_back_empty_so_the_writer_clears_it():
    ds = small_store()
    gone = PROMOTED + "urn:lattice:studio:version/gone"
    ds.graph(URIRef(gone)).add((URIRef("urn:x"), PRM.prefLabel, Literal("stale")))
    out = rebuild(Store(ds), None, JOB, NOW)
    assert gone in out and len(out[gone]) == 0


def test_the_record_names_every_promotion_contract_with_a_digest_that_follows_its_triples():
    declarations = _declarations(str(Path(__file__).resolve().parents[2]))
    record = rebuild(Store(small_store()), None, JOB, NOW)[RECORD]
    contracts = digests(declarations)
    assert set(contracts) == {str(c) for c in declarations.subjects(RDF.type, SRF.PromotionContract)} and len(contracts) >= 6
    assert {(URIRef(c), CST.contractDigest, Literal(d)) for c, d in contracts.items()} == set(record)
    assert all(re.fullmatch(r"[0-9a-f]{64}", d) for d in contracts.values())
    changed = Graph() + declarations
    contract = URIRef(next(iter(contracts)))
    changed.add((contract, URIRef("urn:x:changed"), Literal(1)))
    after = digests(changed)
    assert after[str(contract)] != contracts[str(contract)]
    assert {c: d for c, d in after.items() if c != str(contract)} == {c: d for c, d in contracts.items() if c != str(contract)}


def test_no_partition_holds_a_blank_node():
    ds = small_store()
    ds.graph(URIRef("urn:lattice:studio:description/b")).parse(
        data=f"@prefix cst: <{CST}> . <{WS}b> cst:dependsOn [ a cst:Thing ] .", format="turtle")
    for graph in rebuild(Store(ds), None, JOB, NOW).values():
        assert not any(isinstance(term, BNode) for triple in graph for term in triple)


def test_a_refresh_job_hands_the_partitions_and_the_record_to_the_writer_in_one_update_and_names_no_workspace():
    store = Store(small_store())
    ConfigStudioWorker(store, None, lambda: NOW).handle(JOB)
    [final] = store.puts  # no update marks a rebuild running, since only the service reads it and waits for its end
    assert (URIRef(JOB), CST.status, CST.Succeeded) in final[1]
    assert set(final[2]) == {PROMOTED + name for name in SOURCES} | {RECORD}
    assert not list(final[1].objects(URIRef(JOB), CST.workspace))


def test_a_refresh_that_cannot_read_fails_the_job_and_sends_no_partition():
    class Broken(Store):
        def graph_names(self):
            raise OSError("store down")

    store = Broken(small_store())
    ConfigStudioWorker(store, None, lambda: NOW).handle(JOB)
    assert (URIRef(JOB), CST.status, CST.Failed) in store.puts[-1][1] and store.puts[-1][2] == {}


def test_a_refresh_job_goes_to_the_writer_of_its_own_id_with_the_partitions_beside_it():
    job = str(uuid.UUID("ffffffff-0000-4000-8000-000000000000"))
    iri = f"urn:lattice:studio:job:{job}"
    graph = Graph()
    graph.add((URIRef(iri), CST.kind, CST.Rebuild))
    publisher = FakePublisher()
    WriterStore(FakeStore(), publisher).put_graph(iri, graph, {RECORD: Graph()})
    _, key, headers, _ = publisher.sent[0]
    assert key == "7" and "workspace" not in headers and headers["job"] == job
