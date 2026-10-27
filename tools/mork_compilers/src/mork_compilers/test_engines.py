# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""The engine wrapper's own behaviour on each engine (MSC-3). Test IDs are MSC3-nn.

Each test names its engine, so it holds under any task (STD-153). Jena is skipped where its test kit is not built, and
``check:mork-compilers-conformance:jena`` builds it first.
"""

from __future__ import annotations

import unittest

from rdflib import BNode, Graph, Literal, URIRef
from rdflib.namespace import XSD

from mork_compilers.engines import REGISTRY, run_query

try:
    import lattice_testing_jena

    JENA = lattice_testing_jena.available()
except ImportError:
    JENA = False

DATA = """
@prefix ex: <urn:ex:> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
ex:a ex:p "plain", "tagged"@en, "7"^^xsd:integer, "2.5"^^xsd:decimal, ex:b, "line\\none" .
ex:b ex:q _:n .
"""
QUERY = "SELECT ?o ?x WHERE { <urn:ex:a> <urn:ex:p> ?o OPTIONAL { ?o <urn:ex:q> ?x } } ORDER BY STR(?o)"


class EngineTests(unittest.TestCase):
    def graph(self) -> Graph:
        return Graph().parse(data=DATA, format="turtle")

    def test_jena_is_in_the_registry(self) -> None:
        # MSC3-01
        self.assertIn("jena", REGISTRY)

    def test_an_unknown_engine_is_refused(self) -> None:
        # MSC3-02
        with self.assertRaises(ValueError):
            run_query(self.graph(), QUERY, engine="no-such-engine")

    @unittest.skipUnless(JENA, "the Jena test kit is not built")
    def test_jena_returns_the_rows_rdflib_does_with_the_same_terms(self) -> None:
        # MSC3-03: literals keep their datatype and language, IRIs and blank nodes keep their kind, an unbound variable stays unbound
        def terms(engine: str) -> list:
            return [(row.o, row.asdict().get("x") is not None, row[0]) for row in run_query(self.graph(), QUERY, engine=engine)]

        self.assertEqual(terms("jena"), terms("rdflib"))
        by_jena = {row.o for row in run_query(self.graph(), QUERY, engine="jena")}
        self.assertIn(Literal("7", datatype=XSD.integer), by_jena)
        self.assertIn(Literal("tagged", lang="en"), by_jena)
        self.assertIn(Literal("plain"), by_jena)
        self.assertIn(URIRef("urn:ex:b"), by_jena)

    @unittest.skipUnless(JENA, "the Jena test kit is not built")
    def test_jena_row_access_matches_the_other_engines(self) -> None:
        # MSC3-04: by attribute, by name, by position, and as a dict without the unbound variables
        row = run_query(self.graph(), "SELECT ?o ?x WHERE { <urn:ex:a> <urn:ex:p> ?o OPTIONAL { ?o <urn:ex:q> ?x } FILTER(?o = <urn:ex:b>) }", engine="jena")[0]
        self.assertEqual((row.o, row["o"], row[0]), (URIRef("urn:ex:b"), URIRef("urn:ex:b"), URIRef("urn:ex:b")))
        self.assertIsInstance(row.x, BNode)
        none = run_query(self.graph(), "SELECT ?o ?x WHERE { <urn:ex:a> <urn:ex:p> ?o OPTIONAL { ?o <urn:ex:q> ?x } FILTER(?o = 'plain') }", engine="jena")[0]
        self.assertEqual(set(none.asdict()), {"o"})

    @unittest.skipUnless(JENA, "the Jena test kit is not built")
    def test_a_query_error_on_jena_is_an_exception(self) -> None:
        # MSC3-05
        with self.assertRaises(lattice_testing_jena.JenaError):
            run_query(self.graph(), "SELECT ?o WHERE {", engine="jena")
