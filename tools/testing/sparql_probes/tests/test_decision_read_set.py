# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""
The profile read set's dependence on ``?decision`` never being unbound, on rdflib, Oxigraph and Jena (TSD-60, TSD-61, MSC-3).

``mork_compilers.sparql_backend._read_set`` aggregates ``IF(?decision = "...", ...)`` over a record's per-value rows (audit items
4 to 6 of the C9b3 aggregate-errors Validation Pack). A row whose ``?decision`` is unbound makes that aggregate an error, which is
unbound on Oxigraph and Jena. These probes use the three aggregate expressions of the generated query on a ``VALUES`` block whose
``?decision`` is computed from a value the test can make erroring, and record what each engine returns. They do not run or change
the generated query. Test IDs are MSC3-nn.

Two ways to leave ``?decision`` unbound are used. "ordering" is the audit's own, ``"abc" >= 5``, which is an error on the
specification's reading and a boolean on rdflib (TSD-61). "arithmetic" is ``?c + 1 > 5``, an error on every engine.
"""

from __future__ import annotations

import os
import unittest

from rdflib import Graph, Literal

from sparql_probes.engines import REGISTRY, available, run_query

AVAILABLE = available()
ENGINES = tuple(engine for engine in REGISTRY if AVAILABLE[engine])

FORMS = {"ordering": "?c >= 5", "arithmetic": "?c + 1 > 5"}
# the three aggregate expressions of _read_set, audit items 4, 5 and 6, as written by the generator with ?decision's value "Permitted"
AGGREGATES = {
    "flag": 'SUM(IF(?decision = "Permitted", 1, 0))',
    "missing flag": 'SUM(IF(?decision = "Permitted" && COALESCE(STR(?diagnostic), "") = "", 1, 0))',
    "reason": 'MAX(IF(?decision = "Permitted", COALESCE(STR(?diagnostic), "z"), ""))',
    # the remedy audit item 4 proposed, COALESCE(?decision, "")
    "coalesced": 'SUM(IF(COALESCE(?decision, "") = "Permitted", 1, 0))',
}

EXPECTED = {
    # (form, aggregate): {engine: result}
    ("ordering", "flag"): {"rdflib": "2", "oxigraph": "unbound", "jena": "unbound"},
    ("ordering", "missing flag"): {"rdflib": "2", "oxigraph": "unbound", "jena": "unbound"},
    ("ordering", "reason"): {"rdflib": "z", "oxigraph": "unbound", "jena": "unbound"},
    ("ordering", "coalesced"): {"rdflib": "2", "oxigraph": "1", "jena": "1"},
    ("arithmetic", "flag"): {"rdflib": "raises AttributeError", "oxigraph": "unbound", "jena": "unbound"},
    ("arithmetic", "missing flag"): {"rdflib": "raises AttributeError", "oxigraph": "unbound", "jena": "unbound"},
    ("arithmetic", "reason"): {"rdflib": "no row", "oxigraph": "unbound", "jena": "unbound"},
    ("arithmetic", "coalesced"): {"rdflib": "1", "oxigraph": "1", "jena": "1"},
}


def query(form: str, aggregate: str) -> str:
    return (
        f'SELECT ({AGGREGATES[aggregate]} AS ?r) WHERE {{ VALUES ?c {{ 7 "abc" }} '
        f'BIND(IF({FORMS[form]}, "Permitted", "Denied") AS ?decision) }}'
    )


def outcome(engine: str, text: str) -> str:
    try:
        rows = run_query(Graph(), text, engine)
    except AttributeError as error:
        return f"raises {type(error).__name__}"
    if not rows:
        return "no row"
    value = rows[0].asdict().get("r")
    return "unbound" if value is None else str(value)


def bound(engine: str, expression: str):
    rows = run_query(Graph(), f"SELECT ?r WHERE {{ BIND(({expression}) AS ?r) }}", engine)
    return rows[0].asdict().get("r")


class ReadSetTests(unittest.TestCase):
    def test_each_engine_returns_what_is_recorded_for_an_unbound_decision(self) -> None:
        # MSC3-11: strict, so an engine fixed upstream fails here and the record is revised
        for (form, name), per_engine in EXPECTED.items():
            for engine in ENGINES:
                with self.subTest(form=form, aggregate=name, engine=engine):
                    self.assertEqual(outcome(engine, query(form, name)), per_engine[engine])

    def test_oxigraph_and_jena_agree_in_every_form(self) -> None:
        # MSC3-12: the two engines that follow the specification give one answer, so the dependence is a property of the query
        for (form, name), per_engine in EXPECTED.items():
            with self.subTest(form=form, aggregate=name):
                self.assertEqual(per_engine["oxigraph"], per_engine["jena"])

    def test_a_coalesced_decision_gives_one_answer_where_the_error_is_arithmetic(self) -> None:
        # MSC3-13: COALESCE(?decision, "") counts the row as none of the outcomes on all three engines
        self.assertEqual(set(EXPECTED[("arithmetic", "coalesced")].values()), {"1"})

    def test_rdflib_orders_a_string_against_a_number_where_the_others_raise_an_error(self) -> None:
        # MSC3-14: TSD-61
        for expression, rdflib_value in (('"abc" >= 5', Literal(True)), ('"abc" < 5', Literal(False)), ('5 < "abc"', Literal(True))):
            for engine in ENGINES:
                with self.subTest(expression=expression, engine=engine):
                    self.assertEqual(bound(engine, expression), rdflib_value if engine == "rdflib" else None)

    def test_an_equality_of_a_string_with_a_number_is_false_on_every_engine(self) -> None:
        # MSC3-15: the control, so TSD-61 is about ordering only
        for engine in ENGINES:
            with self.subTest(engine=engine):
                self.assertEqual(bound(engine, '"abc" = 5'), Literal(False))

    def test_every_engine_is_available_where_all_are_required(self) -> None:
        # MSC3-16
        if os.environ.get("SPARQL_PROBES_REQUIRED") == "1":
            self.assertEqual(ENGINES, REGISTRY)
