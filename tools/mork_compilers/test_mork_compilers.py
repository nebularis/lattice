# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""
Tests for the MORK backend compiler family.

Run from the repository root::

    python3 -m unittest tools.mork_compilers.test_mork_compilers -v

Requires rdflib. **These have not been executed** — no Python interpreter was
available in the environment this revision was written in (see
``mork/docs/eligibility-executable-compiler.md``). Treat a first run as part
of review, not as a regression check, exactly as ``tools/surface``'s own test
module already states for itself.
"""

from __future__ import annotations

import unittest
from pathlib import Path

from rdflib import Graph, URIRef
from rdflib.namespace import RDF

from .common import dependency_order, resolve_parameters
from .eligibility_ir import IntervalPlan, IRCompileError, RequiredInterval, compile_condition, compile_profile
from .namespaces import ELG, EXE, MORK, SH, SWRL, SWRLB
from .shacl_backend import compile_shapes
from .sparql_backend import compile_query_template
from .swrl_backend import compile_rules

ROOT = Path(__file__).resolve().parents[2]
INTERVAL_EXAMPLE = ROOT / "eligibility" / "examples" / "interval-containment.ttl"

CONDITION = URIRef("https://example.org/lattice/eligibility/minimum-credit-condition")
PROFILE = URIRef("https://example.org/lattice/eligibility/profile-a")


def load() -> Graph:
    graph = Graph()
    graph.parse(str(INTERVAL_EXAMPLE), format="turtle")
    return graph


class IntervalIRTests(unittest.TestCase):
    def test_compiles_the_worked_example(self) -> None:
        plan = compile_condition(load(), CONDITION)
        self.assertEqual(len(plan.required), 1)
        interval = plan.required[0]
        self.assertEqual(interval.lower, 700.0)
        self.assertTrue(interval.lower_closed)
        self.assertEqual(interval.upper, 850.0)
        self.assertTrue(interval.upper_closed)

    def test_source_nodes_cover_the_full_provenance_chain(self) -> None:
        plan = compile_condition(load(), CONDITION)
        names = {str(n) for n in plan.source_nodes}
        for expected in (
            "minimum-credit-condition",
            "required-rangeset",
            "required-range",
            "lower-bound",
            "upper-bound",
            "lower-value",
            "upper-value",
            "credit-score-space",
        ):
            self.assertTrue(
                any(expected in name for name in names), f"missing source node: {expected}"
            )

    def test_wrong_match_strategy_is_refused(self) -> None:
        graph = Graph().parse(
            data="""
            @prefix elg: <https://www.nebularis.org/neuro-semantic/lattice/eligibility#> .
            @prefix ex: <https://example.org/x#> .
            ex:c a elg:IntervalCondition ; elg:matchStrategy elg:SetMembership .
            """,
            format="turtle",
        )
        with self.assertRaisesRegex(IRCompileError, "IntervalContainment"):
            compile_condition(graph, URIRef("https://example.org/x#c"))

    def test_non_default_wildcard_semantics_is_refused(self) -> None:
        graph = Graph().parse(
            data="""
            @prefix elg: <https://www.nebularis.org/neuro-semantic/lattice/eligibility#> .
            @prefix qnt: <https://www.nebularis.org/neuro-semantic/lattice/quantification#> .
            @prefix ex: <https://example.org/x#> .
            ex:c a elg:IntervalCondition ;
                elg:matchStrategy elg:IntervalContainment ;
                elg:wildcardSemantics elg:SomeOtherWildcard ;
                elg:requiredRangeSet ex:rs .
            ex:rs qnt:onSpace ex:space .
            """,
            format="turtle",
        )
        with self.assertRaisesRegex(IRCompileError, "wildcard"):
            compile_condition(graph, URIRef("https://example.org/x#c"))

    def test_compiles_the_profile(self) -> None:
        plan = compile_profile(load(), PROFILE)
        self.assertEqual(plan.aggregation, ELG.AllRequired)
        self.assertEqual(len(plan.conditions), 1)


class SparqlBackendTests(unittest.TestCase):
    def test_query_binds_the_declared_bounds(self) -> None:
        plan = compile_condition(load(), CONDITION)
        graph = compile_query_template(plan)
        templates = list(graph.subjects(RDF.type, MORK.QueryTemplate))
        self.assertEqual(len(templates), 1)
        text = str(graph.value(templates[0], MORK.queryText))
        self.assertIn("700.0", text)
        self.assertIn("850.0", text)
        self.assertIn("Undetermined", text)
        self.assertIn(">=", text)
        self.assertIn("<=", text)

    def test_open_bound_uses_strict_comparison(self) -> None:
        plan = IntervalPlan(
            condition=CONDITION,
            value_space=URIRef("https://example.org/space"),
            required=(RequiredInterval(700.0, False, 850.0, True),),
            source_nodes=(CONDITION,),
        )
        graph = compile_query_template(plan)
        text = str(next(graph.objects(None, MORK.queryText)))
        self.assertIn("?candLower > 700.0", text)
        self.assertIn("?candUpper <= 850.0", text)


class ShaclBackendTests(unittest.TestCase):
    def test_emits_readiness_and_containment_shapes(self) -> None:
        plan = compile_condition(load(), CONDITION)
        graph = compile_shapes(plan)
        shapes = list(graph.subjects(RDF.type, SH.NodeShape))
        self.assertEqual(len(shapes), 2)
        mappings = list(graph.subjects(RDF.type, MORK.DataMapping))
        self.assertEqual(len(mappings), 1)
        self.assertEqual(
            len(list(graph.objects(mappings[0], MORK.generatesShapeDefinition))), 2
        )

    def test_containment_select_references_the_condition(self) -> None:
        plan = compile_condition(load(), CONDITION)
        graph = compile_shapes(plan)
        selects = [str(o) for o in graph.objects(None, SH.select)]
        self.assertTrue(any(str(CONDITION) in text for text in selects))


class SwrlBackendTests(unittest.TestCase):
    def test_emits_one_imp_per_required_interval(self) -> None:
        plan = compile_condition(load(), CONDITION)
        graph = compile_rules(plan)
        imps = list(graph.subjects(RDF.type, SWRL.Imp))
        self.assertEqual(len(imps), 1)
        mappings = list(graph.subjects(RDF.type, MORK.DataMapping))
        self.assertEqual(len(mappings), 1)
        self.assertEqual(
            len(list(graph.objects(mappings[0], MORK.generatesRuleDefinition))), 1
        )

    def test_rule_uses_closed_bound_builtins(self) -> None:
        plan = compile_condition(load(), CONDITION)
        graph = compile_rules(plan)
        builtins = {str(b) for b in graph.objects(None, SWRL.builtin)}
        self.assertIn(str(SWRLB.greaterThanOrEqual), builtins)
        self.assertIn(str(SWRLB.lessThanOrEqual), builtins)

    def test_head_asserts_implies_decision_permitted(self) -> None:
        plan = compile_condition(load(), CONDITION)
        graph = compile_rules(plan)
        imp = next(graph.subjects(RDF.type, SWRL.Imp))
        head_list = graph.value(imp, SWRL.head)
        atoms = list(graph.items(head_list))
        self.assertEqual(len(atoms), 1)
        self.assertEqual(graph.value(atoms[0], SWRL.propertyPredicate), EXE.impliesDecision)
        self.assertEqual(graph.value(atoms[0], SWRL.argument2), ELG.Permitted)


class CommonCoreTests(unittest.TestCase):
    def test_resolve_parameters_reads_name_value_pairs(self) -> None:
        graph = Graph().parse(
            data="""
            @prefix mork: <http://www.nebularis.org/ontologies/Mork#> .
            @prefix ex: <https://example.org/x#> .
            ex:m mork:hasParameterBinding ex:p .
            ex:p mork:paramName "lowerBound" ; mork:paramValue "700"^^<http://www.w3.org/2001/XMLSchema#decimal> .
            """,
            format="turtle",
        )
        params = resolve_parameters(graph, URIRef("https://example.org/x#m"))
        self.assertEqual(str(params["lowerBound"]), "700")

    def test_dependency_order_puts_dependencies_first(self) -> None:
        graph = Graph().parse(
            data="""
            @prefix mork: <http://www.nebularis.org/ontologies/Mork#> .
            @prefix ex: <https://example.org/x#> .
            ex:a mork:dependsOnMapping ex:b .
            ex:b mork:dependsOnMapping ex:c .
            """,
            format="turtle",
        )
        a, b, c = (URIRef("https://example.org/x#" + n) for n in "abc")
        ordered = dependency_order(graph, [a, b, c])
        self.assertEqual(ordered, [c, b, a])

    def test_dependency_cycle_is_refused(self) -> None:
        from .common import DependencyCycleError

        graph = Graph().parse(
            data="""
            @prefix mork: <http://www.nebularis.org/ontologies/Mork#> .
            @prefix ex: <https://example.org/x#> .
            ex:a mork:dependsOnMapping ex:b .
            ex:b mork:dependsOnMapping ex:a .
            """,
            format="turtle",
        )
        a, b = (URIRef("https://example.org/x#" + n) for n in "ab")
        with self.assertRaises(DependencyCycleError):
            dependency_order(graph, [a, b])


if __name__ == "__main__":
    unittest.main()
