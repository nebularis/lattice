"""Tests for the validation of a baseline, which warns of an import no held document declares (SVA-B2b, SVA-Q7)."""

from __future__ import annotations

from urllib.parse import quote

from rdflib import Graph, Literal, URIRef
from rdflib.namespace import OWL, XSD

from lattice_workers.config_studio_imports import missing_imports, validate_baseline
from lattice_workers.config_studio_jobs import CST, SH
from lattice_workers.config_studio_worker import ConfigStudioWorker
from test_config_studio_worker import BASELINE_1, ROOT, FakeStore, _clock, results, submit

PREFIX = "@prefix owl: <http://www.w3.org/2002/07/owl#> .\n"
OWN = "https://example.org/own"


def doc(body: str) -> Graph:
    return Graph().parse(data=PREFIX + body, format="turtle")


def held_graph(digit: str) -> str:
    return "urn:lattice:studio:imported/" + quote("urn:lattice:studio:import:" + digit * 64, safe="-_.~")


def run_baseline(baseline: str, *held: str) -> tuple[Graph, URIRef]:
    """The baseline job as the worker handles it, each held import a context graph of the job under its graph name."""
    store = FakeStore()
    iri = submit(store, "validate", "baseline", None)
    job = URIRef(iri)
    store.graphs[f"{iri}:input"] = doc(baseline)
    for n, text in enumerate(held):
        name = held_graph("abcdef"[n])
        store.graphs[name] = doc(text)
        store.graphs[iri].add((job, CST.contextGraph, URIRef(name)))
    # A configuration part is context too, and is never read as a held import.
    part = BASELINE_1.replace("baseline", "surface")
    store.graphs[part] = doc("<urn:x:s> a owl:Ontology ; owl:imports <urn:x:from-a-part> .")
    store.graphs[iri].add((job, CST.contextGraph, URIRef(part)))
    ConfigStudioWorker(store, ROOT, _clock()).handle(iri)
    return store.graphs[iri], job


def found(g: Graph, job: URIRef) -> list[tuple[str, str, str]]:
    return sorted(
        (str(g.value(r, SH.focusNode)), str(g.value(r, SH.value)), str(g.value(r, CST.code)))
        for r in results(g, job, SH.Warning)
    )


def test_an_import_held_by_its_ontology_iri_is_not_reported():
    g, job = run_baseline(f"<{OWN}> a owl:Ontology ; owl:imports <urn:x:one> .", "<urn:x:one> a owl:Ontology .")
    assert found(g, job) == []
    assert (job, CST.conforms, Literal(True, datatype=XSD.boolean)) in g


def test_an_import_held_by_its_version_iri_is_not_reported():
    g, job = run_baseline(
        f"<{OWN}> a owl:Ontology ; owl:imports <urn:x:one/1.0> .", "<urn:x:one> a owl:Ontology ; owl:versionIRI <urn:x:one/1.0> ."
    )
    assert found(g, job) == []


def test_a_missing_import_is_a_warning_on_its_statement_that_does_not_stop_the_baseline_conforming():
    g, job = run_baseline(f"<{OWN}> a owl:Ontology ; owl:imports <urn:x:absent> .")
    assert found(g, job) == [(OWN, "urn:x:absent", "ImportNotHeld")]
    [result] = results(g, job, SH.Warning)
    assert g.value(result, SH.resultPath) == OWL.imports
    message = str(g.value(result, SH.resultMessage))
    assert OWN in message and "urn:x:absent" in message
    assert (job, CST.conforms, Literal(True, datatype=XSD.boolean)) in g
    assert not results(g, job, SH.Violation)
    assert (job, CST.status, CST.Succeeded) in g


def test_an_import_a_held_import_states_and_nothing_holds_is_reported_on_the_held_ontology():
    g, job = run_baseline(
        f"<{OWN}> a owl:Ontology ; owl:imports <urn:x:one> .", "<urn:x:one> a owl:Ontology ; owl:imports <urn:x:deeper> ."
    )
    assert found(g, job) == [("urn:x:one", "urn:x:deeper", "ImportNotHeld")]


def test_a_held_import_that_imports_the_baseline_itself_is_not_reported():
    g, job = run_baseline(
        f"<{OWN}> a owl:Ontology ; owl:versionIRI <{OWN}/1> ; owl:imports <urn:x:one> .",
        f"<urn:x:one> a owl:Ontology ; owl:imports <{OWN}>, <{OWN}/1> .",
    )
    assert found(g, job) == []


def test_a_baseline_with_no_named_ontology_has_no_finding():
    g, job = run_baseline("[] a owl:Ontology ; owl:imports <urn:x:absent> . <urn:x:s> <urn:x:p> <urn:x:o> .")
    assert found(g, job) == []
    assert (job, CST.conforms, Literal(True, datatype=XSD.boolean)) in g
    g, job = run_baseline("<urn:x:s> <urn:x:p> <urn:x:o> .")
    assert found(g, job) == []


def test_a_part_of_the_workspace_is_never_read_as_a_held_import():
    g, job = run_baseline(f"<{OWN}> a owl:Ontology ; owl:imports <urn:x:from-a-part> .")
    assert found(g, job) == [(OWN, "urn:x:from-a-part", "ImportNotHeld")]


def test_a_document_declaring_no_single_named_ontology_holds_nothing():
    g, job = run_baseline(
        f"<{OWN}> a owl:Ontology ; owl:imports <urn:x:one> .", "<urn:x:one> a owl:Ontology . <urn:x:two> a owl:Ontology ."
    )
    assert found(g, job) == [(OWN, "urn:x:one", "ImportNotHeld")]


def test_the_findings_are_sorted_and_the_graph_is_the_same_on_a_repeat():
    baseline = f"<{OWN}> a owl:Ontology ; owl:imports <urn:x:z>, <urn:x:a>, <urn:x:m> ."
    one, job = run_baseline(baseline, "<urn:x:m> a owl:Ontology ; owl:imports <urn:x:b> .")
    two, _ = run_baseline(baseline, "<urn:x:m> a owl:Ontology ; owl:imports <urn:x:b> .")
    pairs = [(f, v) for f, v, _ in found(one, job)]
    assert pairs == sorted(pairs) and len(pairs) == 3
    # Minted result nodes follow the sorted order, so the two graphs hold the same triples under the same names.
    ordered = [str(one.value(URIRef(f"{job}#result-{n}"), SH.value)) for n in (1, 2, 3)]
    assert ordered == ["urn:x:a", "urn:x:z", "urn:x:b"]
    first = Graph() + validate_baseline(job, doc(baseline), [doc("<urn:x:m> a owl:Ontology ; owl:imports <urn:x:b> .")])
    second = Graph() + validate_baseline(job, doc(baseline), [doc("<urn:x:m> a owl:Ontology ; owl:imports <urn:x:b> .")])
    assert set(first) == set(second)
    assert first.serialize(format="nt") == second.serialize(format="nt")


def test_missing_imports_lists_each_pair_once():
    baseline = doc(f"<{OWN}> a owl:Ontology ; owl:imports <urn:x:a> .")
    assert missing_imports(baseline, [baseline]) == [(URIRef(OWN), URIRef("urn:x:a"))]
