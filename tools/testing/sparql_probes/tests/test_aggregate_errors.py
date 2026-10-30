# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""
What an aggregate does with a row that has no value or errors, on rdflib, Oxigraph and Jena, and what each remedy does (TSD-41, TSD-43, CCS C9b3, MSC-1).

The cases are in ``sparql_probes.aggregate_error_cases`` and what each engine returned is in ``sparql_probes.aggregate_error_expected``.
Every probe names its engine, so it holds under any task. Test IDs are AE-nn. An engine that is not installed or built here is skipped, and
``SPARQL_PROBES_REQUIRED=1`` (set by ``check:sparql-probes-conformance``) makes AE-23 fail instead.
"""

from __future__ import annotations

import os
import unittest

from rdflib import Graph

from sparql_probes.aggregate_error_cases import REMEDY_STATES, all_cases, cell, graph, matrix_cases, run
from sparql_probes.aggregate_error_expected import EXPECTED
from sparql_probes.engines import REGISTRY, available, run_query

AVAILABLE = available()
ENGINES = tuple(engine for engine in REGISTRY if AVAILABLE[engine])
CELLS = {engine: None for engine in REGISTRY}


def cells(engine: str) -> dict[str, str]:
    if CELLS[engine] is None:
        CELLS[engine] = run(engine)
    return CELLS[engine]


def row(engine: str, name: str) -> list[str]:
    return [EXPECTED[engine][f"{name} | {state}"] for state in REMEDY_STATES]


class MatrixTests(unittest.TestCase):
    def test_every_cell_is_as_recorded_on_each_engine(self) -> None:
        # AE-01
        self.assertEqual(set(EXPECTED["rdflib"]), set(all_cases()))
        for engine in ENGINES:
            for name, value in cells(engine).items():
                with self.subTest(engine=engine, case=name):
                    self.assertEqual(value, EXPECTED[engine][name])

    def test_the_matrix_has_every_aggregate_in_every_state(self) -> None:
        # AE-02
        self.assertEqual(len(matrix_cases()), 13 * len(REMEDY_STATES))

    def test_every_engine_is_available_where_all_are_required(self) -> None:
        # AE-23: check:sparql-probes-conformance sets SPARQL_PROBES_REQUIRED, so a missing engine cannot pass as a skip
        if os.environ.get("SPARQL_PROBES_REQUIRED") == "1":
            self.assertEqual(ENGINES, REGISTRY, f"not available: {[e for e in REGISTRY if not AVAILABLE[e]]}")


class FilterTests(unittest.TestCase):
    def test_a_type_guarded_filter_gives_one_answer_on_every_engine_in_every_state(self) -> None:
        # AE-03: remedy (a), FILTER(isNumeric(?x)), for the numeric aggregates. The last state is left out for
        # rdflib, which returns a row there (AE-17)
        for aggregate in ("SUM", "AVG", "MIN", "MAX"):
            with self.subTest(aggregate=aggregate):
                name = f"a2 filter numeric | {aggregate}"
                self.assertEqual(row("rdflib", name)[:6], row("oxigraph", name)[:6])
                self.assertEqual(row("oxigraph", name), row("jena", name))

    def test_filter_bound_does_not_remove_a_value_of_the_wrong_type(self) -> None:
        # AE-04: an IRI is bound, so SUM is still an error (unbound) on Oxigraph and Jena, and rdflib raises.
        self.assertEqual(EXPECTED["oxigraph"]["a filter | SUM | iri"], "unbound")
        self.assertEqual(EXPECTED["jena"]["a filter | SUM | iri"], "unbound")
        self.assertTrue(EXPECTED["rdflib"]["a filter | SUM | iri"].startswith("refused"))

    def test_filtering_the_rows_out_also_removes_them_from_count_star(self) -> None:
        # AE-05
        for engine in ENGINES:
            with self.subTest(engine=engine):
                self.assertEqual(cells(engine)["COUNT(*) | one unbound"], "3")
                self.assertEqual(cells(engine)["a filter | COUNT(*) | one unbound"], "2")


class CoalesceTests(unittest.TestCase):
    def test_coalescing_to_zero_cannot_tell_a_missing_value_from_a_zero(self) -> None:
        # AE-06: SUM over one unbound row is the sum of the others, the same as the filter gives
        for engine in ENGINES:
            with self.subTest(engine=engine):
                self.assertEqual(cells(engine)["b coalesce | SUM(COALESCE(?x, 0)) | one unbound"], "3")
                self.assertEqual(cells(engine)["a filter | SUM | one unbound"], "3")

    def test_coalescing_changes_the_denominator_of_an_average(self) -> None:
        # AE-07
        for engine in ENGINES:
            with self.subTest(engine=engine):
                self.assertEqual(cells(engine)["b coalesce | AVG(COALESCE(?x, 0)) | one unbound"], "1^dec")
                self.assertEqual(cells(engine)["a filter | AVG | one unbound"], "1.5^dec")

    def test_coalescing_a_group_concat_leaves_an_empty_element_and_a_stray_separator(self) -> None:
        # AE-08: the sorted elements of "1  2" or " 1 2" start with the empty one
        for engine in ENGINES:
            with self.subTest(engine=engine):
                self.assertEqual(cells(engine)["b coalesce | GROUP_CONCAT(COALESCE(STR(?x), '')) | one unbound"], " 1 2")

    def test_coalescing_does_not_hide_a_value_of_the_wrong_type_from_sum(self) -> None:
        # AE-09
        self.assertEqual(EXPECTED["oxigraph"]["b coalesce | SUM(COALESCE(?x, 0)) | iri"], "unbound")


class DetectTests(unittest.TestCase):
    def test_the_count_of_missing_rows_is_the_same_on_every_engine(self) -> None:
        # AE-10: remedy (c), COUNT(*) - COUNT(?x)
        name = "c detect | COUNT(*) - COUNT(?x)"
        self.assertEqual(row("rdflib", name)[:6], row("oxigraph", name)[:6])
        self.assertEqual(row("rdflib", name), ["0", "1", "0", "0", "2", "0", "unbound"])
        self.assertEqual(row("oxigraph", name), row("jena", name))

    def test_counting_an_expression_to_detect_missing_rows_is_not_portable(self) -> None:
        # AE-11: COUNT(STR(?x)) is an error on Oxigraph, counts the row on rdflib, and skips it on Jena
        name = "c detect | COUNT(*) - COUNT(STR(?x))"
        self.assertEqual(EXPECTED["rdflib"][f"{name} | one unbound"], "0")
        self.assertEqual(EXPECTED["oxigraph"][f"{name} | one unbound"], "unbound")
        self.assertEqual(EXPECTED["jena"][f"{name} | one unbound"], "1")

    def test_the_guarded_aggregate_is_unknown_when_a_row_is_missing_and_known_when_none_is(self) -> None:
        # AE-12: IF(COUNT(?x) = COUNT(*), agg, 1/0), on a group with and without a missing row
        for engine in ENGINES:
            with self.subTest(engine=engine):
                for name in ("SUM(COALESCE(?x, 0))", "MAX(?x)"):
                    guarded = f"c detect | IF(COUNT(?x) = COUNT(*), {name}, 1/0)"
                    self.assertNotEqual(cells(engine)[f"{guarded} | bound"], "unbound")
                    self.assertEqual(cells(engine)[f"{guarded} | one unbound"], "unbound")
                    self.assertEqual(cells(engine)[f"{guarded} | all unbound"], "unbound")

    def test_an_empty_group_has_nothing_missing_so_the_guarded_sum_is_the_neutral_element(self) -> None:
        # AE-13
        for engine in ENGINES:
            with self.subTest(engine=engine):
                self.assertEqual(cells(engine)["c detect | IF(COUNT(?x) = COUNT(*), SUM(COALESCE(?x, 0)), 1/0) | empty"], "0")


class SubSelectTests(unittest.TestCase):
    def test_computing_the_value_in_a_sub_select_does_not_remove_an_unbound_row(self) -> None:
        # AE-14: remedy (d) alone leaves SUM(?v) as bare SUM is, on each engine
        name = "d sub-select | SUM(?v) over BIND(?x + 0) | one unbound"
        self.assertEqual(cells("oxigraph")[name], "unbound")
        self.assertEqual(cells("rdflib")[name], "3")

    def test_a_filter_on_the_sub_selects_value_gives_one_answer_on_every_engine(self) -> None:
        # AE-15
        name = "d sub-select | SUM(?v) over BIND(?x + 0), FILTER(BOUND(?v))"
        self.assertEqual(row("rdflib", name)[:6], row("oxigraph", name)[:6])


class GroupsTests(unittest.TestCase):
    """``GROUP BY ?s`` over three subjects, the second with no value (``s1=3, s2=none, s3=5``)."""

    def test_a_filter_removes_the_group_with_no_value_where_a_coalesce_keeps_it_at_zero(self) -> None:
        # AE-19
        for engine in ENGINES:
            with self.subTest(engine=engine):
                self.assertEqual(cells(engine)["groups | a filter BOUND, SUM"], "s1=3;s3=5")
                self.assertEqual(cells(engine)["groups | a filter BOUND, COUNT(*)"], "s1=2;s3=1")
                self.assertEqual(cells(engine)["groups | b coalesce, SUM"], "s1=3;s2=0;s3=5")

    def test_a_bare_sum_over_the_group_with_no_value_is_zero_on_rdflib_and_unbound_on_the_others(self) -> None:
        # AE-20: §18.5.1.3 gives an error, since the group has an error element
        self.assertEqual(EXPECTED["rdflib"]["groups | bare SUM"], "s1=3;s2=0;s3=5")
        self.assertEqual(EXPECTED["oxigraph"]["groups | bare SUM"], "s1=3;s2=unbound;s3=5")
        self.assertEqual(EXPECTED["jena"]["groups | bare SUM"], "s1=3;s2=unbound;s3=5")

    def test_the_guarded_sum_is_unbound_for_the_group_with_no_value_on_every_engine(self) -> None:
        # AE-21
        for engine in EXPECTED:
            with self.subTest(engine=engine):
                self.assertEqual(EXPECTED[engine]["groups | c detect, SUM"], "s1=3;s2=unbound;s3=5")

    def test_a_coalesced_average_has_a_zero_for_the_group_with_no_value_on_every_engine(self) -> None:
        # AE-22
        for engine in EXPECTED:
            with self.subTest(engine=engine):
                self.assertEqual(EXPECTED[engine]["groups | b coalesce, AVG"], "s1=1.5^dec;s2=0^dec;s3=5^dec")


class EngineDefectTests(unittest.TestCase):
    def test_oxigraph_counts_an_erroring_expression_as_an_error_where_the_specification_removes_it(self) -> None:
        # AE-16: §18.5.1.2. Jena removes the row, rdflib counts it
        self.assertEqual(EXPECTED["oxigraph"]["COUNT(expr) | one unbound"], "unbound")
        self.assertEqual(EXPECTED["rdflib"]["COUNT(expr) | one unbound"], "3")
        self.assertEqual(EXPECTED["jena"]["COUNT(expr) | one unbound"], "2")

    def test_rdflib_returns_a_row_for_a_grouped_query_over_no_rows(self) -> None:
        # AE-17: the specification has no group, so no row. Oxigraph and Jena return none
        self.assertEqual(EXPECTED["rdflib"]["COUNT(*) | empty grouped"], "unbound")
        self.assertEqual(EXPECTED["oxigraph"]["COUNT(*) | empty grouped"], "none")
        self.assertEqual(EXPECTED["jena"]["COUNT(*) | empty grouped"], "none")

    def test_rdflib_raises_for_sum_over_an_iri(self) -> None:
        # AE-18
        with self.assertRaises(Exception):
            list(run_query(graph("iri"), "SELECT (SUM(?x) AS ?g) WHERE { ?s a <urn:T> . OPTIONAL { ?s <urn:p> ?x } }", "rdflib"))
        self.assertTrue(isinstance(graph("iri"), Graph))


if __name__ == "__main__":
    unittest.main()
