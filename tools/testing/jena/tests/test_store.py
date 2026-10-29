# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""The Jena test-support engine (ADR-A125). Test IDs are JE-Tn. They skip where the testkit jar is not built."""

from __future__ import annotations

import pytest
from rdflib import BNode, Literal, URIRef
from rdflib.namespace import XSD

import lattice_testing_jena as jena
from lattice_testing_jena import JenaError, JenaStore, bind_parameters, iri, literal

pytestmark = pytest.mark.skipif(not jena.available(), reason="mise run bootstrap:sparql-testkit")

P, S, G = iri("urn:p"), iri("urn:s"), iri("urn:g")


@pytest.fixture
def store():
    with JenaStore() as s:
        yield s


def test_je_t1_bind_parameters_replaces_both_spellings_and_leaves_other_names_alone():
    bound = bind_parameters("INSERT { ?root <urn:p> $value . ?other <urn:q> ?x } WHERE { $root <urn:r> ?x }", {"root": iri("urn:a"), "value": literal(1)})
    assert '<urn:a> <urn:p> "1"^^' in bound and "?other" in bound and "?x" in bound
    assert "$root" not in bound and "?root" not in bound
    with pytest.raises(ValueError, match="misspelt"):
        bind_parameters("SELECT * WHERE { $root ?p ?o }", {"misspelt": iri("urn:a")})


def test_je_t2_an_update_runs_with_its_parameters_and_the_quads_come_back(store):
    store.update("INSERT { GRAPH <urn:g> { $root <urn:p> $value } } WHERE {}", {"root": iri("urn:a"), "value": literal("v")})
    (quad,) = store.quads(G)
    assert (quad.subject, quad.predicate, quad.object, quad.graph) == (iri("urn:a"), P, literal("v"), G)
    assert store.count("urn:p") == 1 and store.count("urn:p", iri("urn:other")) == 0


def test_je_t3_a_parameter_left_out_stays_an_unbound_variable(store):
    store.update("INSERT { GRAPH <urn:g> { $root <urn:p> $value } } WHERE {}", {"root": iri("urn:a")})
    assert store.quads() == []  # the triple with an unbound variable is skipped


def test_je_t4_select_returns_bound_variables_only_and_remove_graph_empties_one_graph(store):
    store.add(S, P, literal(1), G)
    store.add(S, P, literal(2))
    rows = store.select("SELECT ?o ?missing WHERE { GRAPH <urn:g> { $s <urn:p> ?o } OPTIONAL { ?s <urn:none> ?missing } }", {"s": S})
    assert rows == [{"o": literal(1)}]
    store.remove_graph(G)
    assert store.quads(G) == [] and [q.object for q in store.quads(default=True)] == [literal(2)]
    store.remove_graph(None)
    assert store.quads() == []


def test_je_t5_the_default_graph_is_not_the_union_of_the_named_graphs(store):
    store.add(S, P, literal("named"), G)
    assert store.select("SELECT ?o WHERE { ?s ?p ?o }") == []
    assert store.select("SELECT ?o WHERE { GRAPH ?g { ?s ?p ?o } }") == [{"o": literal("named")}]
    assert [q.graph for q in store.quads()] == [G]


def test_je_t6_literals_keep_their_datatype_and_language_tag(store):
    terms = [literal(1), Literal("1.5", datatype=XSD.decimal), Literal("2026-10-27", datatype=XSD.date), Literal("x", datatype=URIRef("urn:dt")),
             Literal("plain"), Literal("hello", lang="en"), Literal('quote " backslash \\ newline \n tab \t é ☃')]
    for index, term in enumerate(terms):
        store.add(S, iri(f"urn:p{index}"), term)
    got = {str(q.predicate): q.object for q in store.quads()}
    assert [got[f"urn:p{i}"] for i in range(len(terms))] == terms
    assert got["urn:p4"].datatype is None and got["urn:p5"].language == "en"
    assert got["urn:p0"].datatype == XSD.integer


def test_je_t7_a_blank_node_label_is_one_node_across_calls_and_the_answer_is_a_bnode(store):
    store.add(BNode("x"), P, literal(1))
    store.add(BNode("x"), iri("urn:q"), literal(2))
    assert store.ask('ASK { ?b <urn:p> 1 . ?b <urn:q> 2 }')
    (row,) = store.select("SELECT ?b WHERE { ?b <urn:p> 1 }")
    assert isinstance(row["b"], BNode)


def test_je_t8_ask_and_construct_and_load(store):
    store.load('<urn:s> <urn:p> "1" <urn:g> .\n')
    store.load("@prefix : <urn:> . :t :p 2 . GRAPH :h { :t :p 3 }", format="trig")
    assert store.ask("ASK { GRAPH <urn:g> { <urn:s> <urn:p> ?o } }") and not store.ask("ASK { <urn:nope> ?p ?o }")
    graph = store.construct("CONSTRUCT { ?s <urn:r> ?o } WHERE { GRAPH ?g { ?s <urn:p> ?o } }")
    assert (S, iri("urn:r"), Literal("1")) in graph and len(graph) == 2
    assert len(store.quads()) == 3


def test_je_t9_reset_empties_every_graph_and_stores_are_separate(store):
    store.add(S, P, literal(1), G)
    other = JenaStore()
    other.add(S, P, literal(2))
    assert len(store.quads()) == 1 and [q.object for q in other.quads()] == [literal(2)]
    store.reset()
    assert store.quads() == [] and len(other.quads()) == 1
    other.close()


def test_je_t10_a_query_error_is_an_exception_and_the_store_still_works(store):
    store.add(S, P, literal(1))
    with pytest.raises(JenaError, match="QueryParseException"):
        store.select("SELECT WHERE {")
    with pytest.raises(JenaError):
        store.update("INSERT DATA {")
    with pytest.raises(JenaError, match="ask was given"):
        store.ask("SELECT * WHERE { ?s ?p ?o }")
    assert store.count("urn:p") == 1


def test_je_t11_an_update_that_fails_part_way_leaves_the_dataset_as_it_was(store):
    store.add(S, P, literal(1))
    with pytest.raises(JenaError):
        # the second operation fails while it runs, after the first has changed the dataset
        store.update("INSERT DATA { <urn:a> <urn:p> 2 } ; INSERT { <urn:b> <urn:p> 3 } WHERE { SERVICE <http://localhost:1/sparql> { ?s ?p ?o } }")
    assert [q.object for q in store.quads()] == [literal(1)]


def test_je_t12_a_bad_load_adds_nothing(store):
    with pytest.raises(JenaError):
        store.load('<urn:a> <urn:p> "1" .\n<urn:broken')
    assert store.quads() == []


def test_je_t13_the_jar_path_can_be_overridden_and_a_missing_jar_is_not_available(monkeypatch, tmp_path):
    monkeypatch.setenv("LATTICE_SPARQL_TESTKIT", str(tmp_path / "missing.jar"))
    assert jena.jar() == tmp_path / "missing.jar" and not jena.available()


def test_je_t14_a_killed_jvm_fails_the_next_call_and_the_one_after_starts_another_with_empty_datasets(store):
    store.add(S, P, literal(1))
    starts = jena._SERVER.starts
    jena._SERVER._process.kill()
    jena._SERVER._process.wait()
    with pytest.raises(JenaError, match="datasets with it"):
        store.select("SELECT * WHERE { ?s ?p ?o }")
    assert store.quads() == [] and jena._SERVER.starts == starts + 1
