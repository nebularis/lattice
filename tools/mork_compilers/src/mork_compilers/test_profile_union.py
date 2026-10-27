# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""
The profile query's ``?closures`` on both engines (TSD-41, STD-279), CCS C9b3.

An aggregate over an expression that errors on some row of its group is an error for ``GROUP_CONCAT``,
``SUM``, ``AVG``, ``MIN`` and ``MAX`` under SPARQL 1.1 §18.5.1. Oxigraph returns no value for the
group and rdflib skips the row. Each probe names its engine, so it holds under both
``check:mork-compilers`` and ``check:mork-compilers-conformance``. The probes pin what each engine
does now, so a change in either fails here, and the profile tests run the generated query on both.
"""

from __future__ import annotations

import unittest
from typing import Optional

from rdflib import Graph
from rdflib.namespace import RDF

from .eligibility_ir import compile_profile
from .engines import REGISTRY, run_query
from .namespaces import ELG, MORK
from .sparql_backend import compile_query_template, render_profile_query
from .test_closure_readings import ADM, example

UNDEF = "VALUES ?x { %s UNDEF }"


def one(engine: str, aggregate: str, body: str) -> Optional[str]:
    """The single value of ``aggregate`` over ``body`` on ``engine``, None when unbound or no row."""
    rows = run_query(Graph(), f"SELECT ({aggregate} AS ?g) WHERE {{ {body} }}", engine)
    return None if not rows or rows[0].g is None else str(rows[0].g)


class ProbeTests(unittest.TestCase):
    """TSD-41's minimal query, with no UNION, no sub-select and no GROUP BY."""

    def test_group_concat_over_a_row_with_no_value_is_unbound_on_oxigraph_and_skipped_on_rdflib(self) -> None:
        # PU-01
        for aggregate in ('GROUP_CONCAT(STR(?x))', 'GROUP_CONCAT(DISTINCT STR(?x))', "GROUP_CONCAT(?x)"):
            with self.subTest(aggregate=aggregate):
                body = UNDEF % "<urn:a>"
                self.assertEqual(one("rdflib", aggregate, body), "urn:a")
                self.assertIsNone(one("oxigraph", aggregate, body))

    def test_sum_avg_min_and_max_are_unbound_on_oxigraph_and_skip_the_row_on_rdflib(self) -> None:
        # PU-02
        for name in ("SUM", "AVG", "MIN", "MAX"):
            with self.subTest(aggregate=name):
                self.assertEqual(one("rdflib", f"{name}(?x)", UNDEF % "1"), "1")
                self.assertIsNone(one("oxigraph", f"{name}(?x)", UNDEF % "1"))

    def test_count_of_an_erroring_expression_differs_from_both_the_specification_and_each_other(self) -> None:
        # PU-03: §18.5.1.2 removes errors before counting, so the answer is 1. rdflib counts the row, Oxigraph poisons.
        self.assertEqual(one("rdflib", "COUNT(STR(?x))", UNDEF % "<urn:a>"), "2")
        self.assertIsNone(one("oxigraph", "COUNT(STR(?x))", UNDEF % "<urn:a>"))
        self.assertEqual(one("rdflib", "COUNT(?x)", UNDEF % "<urn:a>"), "1")
        self.assertEqual(one("oxigraph", "COUNT(?x)", UNDEF % "<urn:a>"), "1")

    def test_coalescing_the_argument_gives_the_same_group_on_both_engines(self) -> None:
        # PU-04
        aggregate = 'GROUP_CONCAT(DISTINCT COALESCE(STR(?x), ""))'
        for engine in REGISTRY:
            with self.subTest(engine=engine):
                self.assertEqual(one(engine, aggregate, UNDEF % "<urn:a>").split(), ["urn:a"])

    def test_an_empty_group_concatenates_to_the_empty_string_on_both_engines(self) -> None:
        # PU-05
        for engine in REGISTRY:
            with self.subTest(engine=engine):
                self.assertEqual(one(engine, "GROUP_CONCAT(STR(?x))", "?s <urn:nothing> ?x"), "")


def closures_on(engine: str, data: Graph) -> dict:
    artefact = compile_query_template(compile_profile(data, ADM["engineering-admission"]))
    text = str(next(artefact.objects(None, MORK.queryText)))
    return {
        str(row.record).rsplit("/", 1)[1]: (str(row.decision), None if row.closures is None else str(row.closures))
        for row in run_query(data, text, engine)
    }


class ProfileTests(unittest.TestCase):
    def test_a_profile_row_names_the_same_closures_on_both_engines(self) -> None:
        # PU-06: ada relies through one condition only, so one of its two rows has no closure
        data = example("admissions")
        closure = str(ADM["registry-closure"])
        expected = {"ada": closure, "ben": closure, "cai": closure, "dee": None}
        for engine in REGISTRY:
            with self.subTest(engine=engine):
                rows = closures_on(engine, data)
                self.assertEqual({record: closures for record, (_, closures) in rows.items()}, expected)

    def test_two_closures_are_named_once_each_in_iri_order_on_both_engines(self) -> None:
        # PU-07: the stem condition now relies on a second closure, so ben and cai name both and ada one
        data = example("admissions")
        second = ADM["registry-second-closure"]
        data.add((second, RDF.type, ELG.Closure))
        data.add((second, ELG.licensedBy, ADM["admissions-profile"]))
        data.set((ADM["stem-binding"], ELG.closedUnder, second))
        first = str(ADM["registry-closure"])
        both = f"{first} {second}"
        expected = {"ada": first, "ben": both, "cai": both, "dee": None}
        for engine in REGISTRY:
            with self.subTest(engine=engine):
                rows = closures_on(engine, data)
                self.assertEqual({record: closures for record, (_, closures) in rows.items()}, expected)

    def test_the_template_has_no_aggregate_over_the_rows_closure(self) -> None:
        # PU-08: no GROUP_CONCAT, and every aggregate over ?relied coalesces it first
        text = render_profile_query(compile_profile(example("admissions"), ADM["engineering-admission"]))
        self.assertNotIn("GROUP_CONCAT(DISTINCT STR(?relied)", text)
        self.assertNotIn("GROUP_CONCAT(STR(?relied)", text)
        self.assertEqual(text.count("COALESCE(STR(?relied)"), 1)

    def test_a_profile_with_no_closure_has_no_closures(self) -> None:
        # PU-09
        data = example("admissions", closed=False)
        for engine in REGISTRY:
            with self.subTest(engine=engine):
                rows = closures_on(engine, data)
                self.assertTrue(all(closures is None for _, closures in rows.values()))
                self.assertEqual(set(rows), {"ada", "ben", "cai", "dee"})


if __name__ == "__main__":
    unittest.main()
