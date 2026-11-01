# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""
The open store questions a third engine could answer, on rdflib, Oxigraph and Jena (MSC-5, TSD-15, TSD-16, TSD-17, TSD-18, TSD-34, TSD-54, TSD-55).

Every probe states what each engine returns, so a divergence shows and an engine that changes shows too. Test IDs are MSC5-nn. An engine that is
not available here is skipped, and ``SPARQL_PROBES_REQUIRED=1`` makes MSC5-12 fail instead.
"""

from __future__ import annotations

import os
import unittest
import warnings

from rdflib import Dataset, Literal

from sparql_probes.engines import REGISTRY, available

AVAILABLE = available()
ENGINES = tuple(engine for engine in REGISTRY if AVAILABLE[engine])
XSD = "http://www.w3.org/2001/XMLSchema#"


def run_quads(engine: str, nquads: str, text: str) -> list[tuple]:
    """``text`` run on ``engine`` over ``nquads``, as one tuple of N3 strings per solution, in the engine's order, None for unbound."""
    if engine == "rdflib":
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            dataset = Dataset()
            dataset.parse(data=nquads, format="nquads")
            return [tuple(None if v is None else v.n3() for v in row) for row in dataset.query(text)]
    if engine == "oxigraph":
        import pyoxigraph as ox

        store = ox.Store()
        store.load(input=nquads.encode(), format=ox.RdfFormat.N_QUADS)
        return [tuple(None if v is None else str(v) for v in solution) for solution in store.query(text)]
    from lattice_testing_jena import JenaStore

    with JenaStore() as store:
        store.load(nquads)
        variables, solutions = store.solutions(text)
        return [tuple(None if solution.get(v) is None else solution[v].n3() for v in variables) for solution in solutions]


def integer(n: int) -> str:
    return f'"{n}"^^<{XSD}integer>'


def quads(*rows: tuple) -> str:
    return "".join(" ".join(row) + " .\n" for row in rows)


G15 = quads(*[(f"<urn:s{i}>", "<urn:p>", f"<urn:o{i}>", "<urn:g2>") for i in (1, 2, 3)], ("<urn:a>", "<urn:p>", "<urn:b>", "<urn:g1>"), ("<urn:c>", "<urn:p>", "<urn:d>", "<urn:g1>"))
G16 = quads(*[("<urn:c>", "<urn:p>", f"<urn:o:{i}>", "<urn:g>") for i in (2, 10, 1)])
G34 = quads(
    ("<urn:v3>", "<urn:prev>", "<urn:v2>", "<urn:g>"),
    ("<urn:v2>", "<urn:prev>", "<urn:v1>", "<urn:g>"),
    ("<urn:v1>", "<urn:cp>", "<urn:t>", "<urn:g>"),
    ("<urn:v1>", "<urn:has>", "<urn:a>", "<urn:g>"),
    ("<urn:v1>", "<urn:has>", "<urn:b>", "<urn:g>"),
    ("<urn:v2>", "<urn:drops>", "<urn:a>", "<urn:g>"),
    ("<urn:v2>", "<urn:adds>", "<urn:c>", "<urn:g>"),
)
Q34 = """SELECT ?m WHERE { GRAPH <urn:g> {
  { SELECT ?cp WHERE { ?cp <urn:cp> ?t } }
  <urn:v3> <urn:prev>* ?w . ?w <urn:prev>* ?cp .
  { ?w <urn:has> ?m } UNION { ?w <urn:adds> ?m }
  FILTER NOT EXISTS { ?x <urn:drops> ?m ; <urn:prev> ?z . ?z <urn:prev>* ?w . <urn:v3> <urn:prev>* ?x }
} }"""


class SubSelectAndOrderingTests(unittest.TestCase):
    def test_a_sub_select_does_not_see_an_outer_binding_except_on_rdflib(self) -> None:
        # MSC5-01: TSD-15, the count with ?s bound outside the sub-select. The specification says 3.
        q = "SELECT ?c WHERE { VALUES ?s { <urn:s1> } { SELECT (COUNT(*) AS ?c) WHERE { GRAPH <urn:g2> { ?s <urn:p> ?o } } } }"
        expected = {"rdflib": [(integer(1),)], "oxigraph": [(integer(3),)], "jena": [(integer(3),)]}
        for engine in ENGINES:
            with self.subTest(engine=engine):
                self.assertEqual(run_quads(engine, G15, q), expected[engine])

    def test_a_sub_select_inside_graph_reads_that_graph_everywhere(self) -> None:
        # MSC5-02: TSD-15, the count inside GRAPH <urn:g1>
        q = "SELECT ?c WHERE { GRAPH <urn:g1> { { SELECT (COUNT(*) AS ?c) WHERE { ?s ?p ?o } } } }"
        for engine in ENGINES:
            with self.subTest(engine=engine):
                self.assertEqual(run_quads(engine, G15, q), [(integer(2),)])

    def test_min_and_max_over_iris_are_iris_except_on_rdflib(self) -> None:
        # MSC5-03: TSD-16. Both choose by the IRI text, so urn:o:10 sorts before urn:o:2
        q = "SELECT (MIN(?o) AS ?l) (MAX(?o) AS ?h) WHERE { GRAPH <urn:g> { <urn:c> <urn:p> ?o } }"
        expected = {"rdflib": [('"urn:o:1"', '"urn:o:2"')], "oxigraph": [("<urn:o:1>", "<urn:o:2>")], "jena": [("<urn:o:1>", "<urn:o:2>")]}
        for engine in ENGINES:
            with self.subTest(engine=engine):
                self.assertEqual(run_quads(engine, G16, q), expected[engine])

    def test_iri_of_min_of_str_is_an_iri_everywhere(self) -> None:
        # MSC5-04: TSD-16, the form the merge-rewrite uses
        q = "SELECT (IRI(MIN(STR(?o))) AS ?l) WHERE { GRAPH <urn:g> { <urn:c> <urn:p> ?o } }"
        for engine in ENGINES:
            with self.subTest(engine=engine):
                self.assertEqual(run_quads(engine, G16, q), [("<urn:o:1>",)])

    def test_a_chain_of_arithmetic_is_grouped_from_the_left(self) -> None:
        # MSC5-05: TSD-17, on the installed versions. A division of integers is a decimal, whose lexical form an engine chooses
        q = "SELECT ((10 - 3 + 2) AS ?a) ((10 - 3 - 2) AS ?b) ((8 / 4 / 2) AS ?c) WHERE {}"
        for engine in ENGINES:
            with self.subTest(engine=engine):
                [(a, b, c)] = run_quads(engine, "", q)
                self.assertEqual((a, b), (integer(9), integer(5)))
                self.assertEqual(float(c.split('"')[1]), 1.0)

    def test_count_distinct_over_a_long_and_an_integer_term(self) -> None:
        # MSC5-06: TSD-18, a VALUES row of 1^^long and 1^^integer. Oxigraph canonicalises both to integer
        q = f'SELECT (COUNT(DISTINCT ?o) AS ?n) WHERE {{ VALUES ?o {{ "1"^^<{XSD}long> "1"^^<{XSD}integer> }} }}'
        expected = {"rdflib": 2, "oxigraph": 1, "jena": 2}
        for engine in ENGINES:
            with self.subTest(engine=engine):
                self.assertEqual(run_quads(engine, "", q), [(integer(expected[engine]),)])


class ExistsInGraphTests(unittest.TestCase):
    def test_not_exists_in_a_graph_block_with_a_sub_select_and_a_union_tests_the_blocks_graph(self) -> None:
        # MSC5-07: TSD-34, the Jena half of TSD-Q19. rdflib's answer depends on the hash seed, so it is not asserted here
        for engine in ENGINES:
            if engine == "rdflib":
                continue
            with self.subTest(engine=engine):
                self.assertEqual(sorted(run_quads(engine, G34, Q34)), [("<urn:b>",), ("<urn:c>",)])

    def test_the_same_query_without_the_sub_select_gives_the_same_members_on_jena_and_oxigraph(self) -> None:
        # MSC5-08: the control, the sub-select replaced by a pattern
        q = Q34.replace("{ SELECT ?cp WHERE { ?cp <urn:cp> ?t } }", "?cp <urn:cp> ?t .")
        for engine in ENGINES:
            with self.subTest(engine=engine):
                self.assertEqual(sorted(run_quads(engine, G34, q)), [("<urn:b>",), ("<urn:c>",)])


class ParsingTests(unittest.TestCase):
    def test_a_blank_node_label_loaded_twice_is_one_node_only_where_the_loader_asks(self) -> None:
        # MSC5-09: TSD-54. Each engine's N-Quads loader is given the same line twice. Jena's own default is a fresh node per parse (Bn.java in the Validation Pack), and the kit asks for labels to be kept
        line = '_:b <urn:p> "x" .\n'
        count = "SELECT (COUNT(DISTINCT ?s) AS ?n) WHERE { ?s <urn:p> ?o }"
        for engine, nodes in {"rdflib": 1, "oxigraph": 2, "jena": 1}.items():
            if engine not in ENGINES:
                continue
            with self.subTest(engine=engine):
                if engine == "rdflib":
                    with warnings.catch_warnings():
                        warnings.simplefilter("ignore")
                        dataset = Dataset()
                        dataset.parse(data=line, format="nquads")
                        dataset.parse(data=line, format="nquads")
                        self.assertEqual(int(next(iter(dataset.query(count)))[0]), nodes)
                elif engine == "oxigraph":
                    import pyoxigraph as ox

                    store = ox.Store()
                    for _ in range(2):
                        store.load(input=line.encode(), format=ox.RdfFormat.N_QUADS)
                    self.assertEqual(int(next(iter(store.query(count)))[0].value), nodes)
                else:
                    from lattice_testing_jena import JenaStore

                    with JenaStore() as store:
                        store.load(line)
                        store.load(line)
                        self.assertEqual(int(store.select(count)[0]["n"]), nodes)

    def test_rdflib_n3_writes_a_multi_line_literal_in_triple_quotes_which_n_quads_refuses(self) -> None:
        # MSC5-10: TSD-55. rdflib's n3() is Notation3 and not N-Quads. The N-Triples serialiser escapes the newline
        text = Literal("a\nb")
        self.assertEqual(text.n3(), '"""a\nb"""')
        line = f"<urn:s> <urn:p> {text.n3()} .\n"
        if "oxigraph" in ENGINES:
            import pyoxigraph as ox

            with self.assertRaises(SyntaxError):
                ox.Store().load(input=line.encode(), format=ox.RdfFormat.N_QUADS)
        if "jena" in ENGINES:
            from lattice_testing_jena import JenaError, JenaStore

            with JenaStore() as store, self.assertRaises(JenaError):
                store.load(line)
        from rdflib import Graph, URIRef

        graph = Graph()
        graph.add((URIRef("urn:s"), URIRef("urn:p"), text))
        self.assertIn(r'"a\nb"', graph.serialize(format="nt"))

    def test_max_and_min_over_a_group_with_an_unbound_row(self) -> None:
        # MSC5-11: TSD-Q21's remainder. Max over {2, no value}: rdflib 2, Oxigraph and Jena unbound. Min over the same: unbound on Oxigraph and Jena
        q = "SELECT (MAX(?y) AS ?mx) (MIN(?y) AS ?mn) WHERE { VALUES ?y { 2 UNDEF } }"
        expected = {"oxigraph": (None, None), "jena": (None, None)}
        for engine in ENGINES:
            with self.subTest(engine=engine):
                rows = run_quads(engine, "", q)
                if engine == "rdflib":
                    self.assertEqual(rows[0][0], integer(2))
                else:
                    self.assertEqual(rows, [expected[engine]])

    def test_every_engine_is_available_where_all_are_required(self) -> None:
        # MSC5-12
        if os.environ.get("SPARQL_PROBES_REQUIRED") == "1":
            self.assertEqual(ENGINES, REGISTRY)


if __name__ == "__main__":
    unittest.main()
