# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""H2.4b: the engine facade the persistence tests use (ADR-A125). Test IDs are H2.4b-Tn."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
from rdflib import XSD, BNode, Literal, URIRef

import engines



@pytest.fixture
def ox():
    pytest.importorskip("lattice_testing_oxigraph", reason="mise run bootstrap:testing-oxigraph")


@pytest.mark.oxigraph
@pytest.mark.usefixtures("ox")
@pytest.mark.parametrize("term", [
    URIRef("urn:a"), BNode("b1"), Literal("plain"), Literal("tagged", lang="en"), Literal(7), Literal("x", datatype=XSD.date),
    Literal(True), Literal("1", datatype=XSD.decimal),
])
def test_h2_4b_t8_a_term_round_trips_through_oxigraph_unchanged(term):
    assert engines.from_ox(engines.to_ox(term)) == term


@pytest.mark.oxigraph
@pytest.mark.usefixtures("ox")
def test_h2_4b_t9_the_facade_answers_in_rdflib_terms_and_matches_patterns_with_wildcards():
    ds = engines.OxDataset()
    g = ds.graph(URIRef("urn:g"))
    g.add((URIRef("urn:a"), URIRef("urn:p"), Literal("v")))
    g.add((URIRef("urn:a"), URIRef("urn:q"), URIRef("urn:b")))
    assert (URIRef("urn:a"), URIRef("urn:p"), Literal("v")) in g
    assert (URIRef("urn:a"), None, None) in g and (URIRef("urn:z"), None, None) not in g
    assert list(g.objects(URIRef("urn:a"), URIRef("urn:q"))) == [URIRef("urn:b")] and len(g) == 2
    g.remove((URIRef("urn:a"), URIRef("urn:p"), None))
    assert len(g) == 1 and [gr.identifier for gr in ds.graphs()] == [URIRef("urn:g")]


@pytest.mark.oxigraph
@pytest.mark.usefixtures("ox")
def test_h2_4b_t10_the_default_graph_has_rdflibs_identifier_and_update_binds_parameters_as_text():
    ds = engines.OxDataset()
    ds.default_context.add((URIRef("urn:a"), URIRef("urn:p"), Literal(1)))
    assert {g.identifier for *_, g in ds.quads()} == {engines.DEFAULT_GRAPH}
    ds.update("INSERT { GRAPH <urn:g> { $s <urn:q> $o } } WHERE {}", initBindings={"s": URIRef("urn:a"), "o": Literal("v")})
    assert (URIRef("urn:a"), URIRef("urn:q"), Literal("v")) in ds.graph(URIRef("urn:g"))
    assert list(ds.query("SELECT ?o WHERE { GRAPH <urn:g> { $s <urn:q> ?o } }", initBindings={"s": URIRef("urn:a")})) == [(Literal("v"),)]


def test_h2_4b_t11_canon_maps_integer_derived_literals_to_xsd_integer_on_oxigraph_only(monkeypatch):
    long = Literal(3, datatype=XSD.long)
    monkeypatch.setattr(engines, "CURRENT", "rdflib")
    assert engines.canon(long) == long
    monkeypatch.setattr(engines, "CURRENT", "oxigraph")
    assert engines.canon(long) == Literal(3, datatype=XSD.integer) and engines.canon(Literal("x")) == Literal("x")


def test_h2_4b_t12_the_oxigraph_cases_skip_where_the_package_is_absent():
    """Run a probe test in a child process in which the package cannot be imported (ADR-A125 decision 4)."""
    code = (
        "import sys; sys.modules['lattice_testing_oxigraph'] = None; import pytest; "
        "sys.exit(pytest.main(['-q', '-p', 'no:cacheprovider', 'test_store_probes.py', '-k', 'test_h2_4b_t6']))"
    )
    result = subprocess.run([sys.executable, "-c", code], cwd=Path(__file__).parent, capture_output=True, text=True)
    assert "1 passed, 1 skipped" in result.stdout, result.stdout[-400:]
