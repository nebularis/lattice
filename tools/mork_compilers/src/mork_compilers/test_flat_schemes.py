# SPDX-License-Identifier: MPL-2.0

"""
Hierarchical match over a scheme with no hierarchy (elg:L14, ADR-A100),
AIR-3.1 of the applied-insurance-reference epic.

The fixtures are the Eligibility examples ``flat-scheme-lending.ttl``, whose
one condition resolves to a hierarchical classification with no scope and to
a lender's flat list under that lender's scope, and
``flat-scheme-employment.ttl``, an exclusion-only condition over a flat list.
SPARQL is the reference. SHACL, SWRL and the plan's expansion must agree with
it, and the OWL backend must refuse.
"""

from __future__ import annotations

import unittest
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict

from rdflib import Graph, URIRef

from .eligibility_ir import ConceptPlan, IRCompileError, ResolutionContext, compile_concept_condition
from .namespaces import EXE
from .owl_backend import compile_classes
from .test_concept_backends import shacl, sparql, swrl, with_questions
from .test_hierarchical_conditions import EX, HEADER, graph

EXAMPLES = Path(__file__).resolve().parents[4] / "ontology/eligibility/examples"
AT = datetime(2026, 6, 1, tzinfo=timezone.utc)
CLASSIFICATION = ResolutionContext(at=AT)
LENDER_B = ResolutionContext(at=AT, scope=frozenset({EX["lender-b"]}))


def example(name: str) -> Graph:
    return Graph().parse(EXAMPLES / f"{name}.ttl")


def decisions(rows: Dict[URIRef, tuple]) -> Dict[str, str]:
    return {str(question).rsplit("/q-", 1)[1]: decision for question, (decision, _) in rows.items()}


class LendingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.data = example("flat-scheme-lending")

    def plan(self, context: ResolutionContext) -> ConceptPlan:
        return compile_concept_condition(self.data, EX["eligible-sector"], context)

    def test_classification_places_every_sector(self) -> None:
        # AIR31-01, and the contrast for AIR31-03: wholesale is Denied here
        plan = self.plan(CLASSIFICATION)
        self.assertFalse(plan.no_hierarchy)
        self.assertEqual(
            decisions(sparql(plan, self.data)),
            {"food-processing": "Permitted", "textiles": "Denied", "retail": "Permitted", "wholesale": "Denied"},
        )

    def test_lender_list_decides_the_named_sectors(self) -> None:
        # AIR31-02
        plan = self.plan(LENDER_B)
        self.assertEqual((plan.scheme.scheme, plan.scheme.binding), (EX["lender-b-sectors"], EX["lender-b-binding"]))
        rows = decisions(sparql(plan, self.data))
        self.assertEqual((rows["retail"], rows["textiles"]), ("Permitted", "Denied"))

    def test_lender_list_leaves_unnamed_sectors_undetermined(self) -> None:
        # AIR31-03
        plan = self.plan(LENDER_B)
        self.assertTrue(plan.no_hierarchy)
        rows = sparql(plan, self.data)
        for name in ("food-processing", "wholesale"):
            self.assertEqual(rows[EX[f"q-{name}"]], ("Undetermined", EXE.NoHierarchy), name)

    def test_candidate_outside_the_list_is_outside_the_scheme(self) -> None:
        # AIR31-05: manufacturing is in the classification, not in the lender's list
        plan = self.plan(LENDER_B)
        rows = sparql(plan, with_questions(self.data, plan.condition, {"outside": (EX.manufacturing,)}))
        self.assertEqual(rows[EX["q-outside"]], ("Undetermined", EXE.OutsideScheme))


class EmploymentTests(unittest.TestCase):
    def test_exclusion_only_over_a_flat_list_decides_the_exclusion_alone(self) -> None:
        # AIR31-04: L14 takes precedence over L12's default inclusion
        data = example("flat-scheme-employment")
        plan = compile_concept_condition(data, EX["benefit-roles"])
        self.assertTrue(plan.no_hierarchy)
        rows = sparql(plan, data)
        self.assertEqual(rows[EX["q-contractor"]], ("Denied", None))
        for name in ("ward-nurse", "site-agent"):
            self.assertEqual(rows[EX[f"q-{name}"]], ("Undetermined", EXE.NoHierarchy), name)


class ParityTests(unittest.TestCase):
    def cases(self):
        lending = example("flat-scheme-lending")
        employment = example("flat-scheme-employment")
        yield lending, compile_concept_condition(lending, EX["eligible-sector"], LENDER_B)
        yield employment, compile_concept_condition(employment, EX["benefit-roles"])

    def test_sparql_agrees_with_the_expansion_for_every_member(self) -> None:
        # AIR31-06
        for data, plan in self.cases():
            asked = with_questions(data, plan.condition, {f"m{i}": (concept,) for i, (concept, _) in enumerate(plan.expansion)})
            rows = sparql(plan, asked)
            for i, (concept, decision) in enumerate(plan.expansion):
                expected = (decision, EXE.NoHierarchy if decision == "Undetermined" else None)
                self.assertEqual(rows[EX[f"q-m{i}"]], expected, str(concept))

    def test_shacl_agrees_with_sparql(self) -> None:
        # AIR31-07
        for data, plan in self.cases():
            reference = {question: decision for question, (decision, _) in sparql(plan, data).items()}
            self.assertEqual(shacl(plan, data), reference, str(plan.condition))

    def test_swrl_derives_only_the_decided_members(self) -> None:
        # AIR31-08
        lending, plan = next(self.cases())
        self.assertEqual(swrl(plan, lending), {EX["q-retail"]: "Permitted", EX["q-textiles"]: "Denied"})


class OwlTests(unittest.TestCase):
    def test_owl_backend_refuses_a_plan_without_a_hierarchy(self) -> None:
        # AIR31-09: bound and claimed single-valued, so only L14 can refuse it
        data = example("flat-scheme-lending")
        data += graph(HEADER + """
            ex:sector-binding a elg:EvidenceBinding ;
                elg:bindsCondition ex:eligible-sector ;
                elg:subjectClass ex:Borrower ;
                elg:singleValued true ;
                elg:evidenceStep [ a elg:EvidenceStep ; elg:stepIndex 0 ;
                                   elg:stepProperty ex:hasSector ; elg:stepDirection elg:Forward ] .
        """)
        with self.assertRaisesRegex(IRCompileError, "L14"):
            compile_classes(compile_concept_condition(data, EX["eligible-sector"], LENDER_B))
        compile_classes(compile_concept_condition(data, EX["eligible-sector"], CLASSIFICATION))


if __name__ == "__main__":
    unittest.main()
