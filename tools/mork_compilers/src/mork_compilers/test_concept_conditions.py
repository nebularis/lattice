# SPDX-License-Identifier: MPL-2.0

"""
Concept conditions through the shared IR (ADR-A87, ADR-A89).

Every decision is checked by executing the generated SPARQL against a
fixture graph with rdflib's own engine, not by inspecting query text.

Run from the repository root::

    python -m pytest tools/mork_compilers -q
"""

from __future__ import annotations

import unittest
from pathlib import Path
from typing import Dict

from rdflib import Graph, Namespace, URIRef
from rdflib.compare import isomorphic
from rdflib.namespace import RDF

from .eligibility_ir import ConceptPlan, IRCompileError, compile_concept_condition
from .namespaces import ELG, EXE, MORK
from .sparql_backend import compile_query_template

ROOT = Path(__file__).resolve().parents[4]
EXAMPLES = ROOT / "ontology" / "eligibility" / "examples"
EX = Namespace("https://example.org/lattice/eligibility/")

PREFIXES = """
@prefix elg: <https://www.nebularis.org/neuro-semantic/lattice/eligibility#> .
@prefix skos: <http://www.w3.org/2004/02/skos/core#> .
@prefix ex: <https://example.org/lattice/eligibility/> .
"""

# A subscription entitlement: premium and enterprise tiers qualify, except the
# legacy enterprise tier, which a separate policy governs.
ENTITLEMENT = PREFIXES + """
ex:tier-free a skos:Concept .
ex:tier-premium a skos:Concept .
ex:tier-enterprise a skos:Concept .
ex:tier-enterprise-legacy a skos:Concept .

ex:entitlement a elg:SetMembershipCondition ;
    elg:matchStrategy elg:SetMembership ;
    elg:compatibilityOperation elg:AllRequired ;
    elg:wildcardSemantics elg:NoWildcard ;
    elg:requiredConcept ex:tier-premium , ex:tier-enterprise , ex:tier-enterprise-legacy ;
    elg:excludedConcept ex:tier-enterprise-legacy .

ex:q-premium a elg:Question ; elg:forCondition ex:entitlement ; elg:candidateConcept ex:tier-premium .
ex:q-free a elg:Question ; elg:forCondition ex:entitlement ; elg:candidateConcept ex:tier-free .
ex:q-legacy a elg:Question ; elg:forCondition ex:entitlement ; elg:candidateConcept ex:tier-enterprise-legacy .
ex:q-absent a elg:Question ; elg:forCondition ex:entitlement .
ex:q-two a elg:Question ; elg:forCondition ex:entitlement ;
    elg:candidateConcept ex:tier-premium , ex:tier-enterprise .
"""


def graph(text: str) -> Graph:
    return Graph().parse(data=text, format="turtle")


def run(plan: ConceptPlan, data: Graph) -> Dict[URIRef, str]:
    """Execute the plan's generated SPARQL over ``data``: question -> decision."""
    artefact = compile_query_template(plan)
    template = next(artefact.subjects(RDF.type, MORK.QueryTemplate))
    query = str(artefact.value(template, MORK.queryText))
    return {row.question: str(row.decision) for row in data.query(query)}


class ConceptIRTests(unittest.TestCase):
    def test_plan_reads_required_and_excluded_concepts(self) -> None:
        plan = compile_concept_condition(graph(ENTITLEMENT), EX.entitlement)
        self.assertEqual(plan.required, (EX["tier-enterprise"], EX["tier-enterprise-legacy"], EX["tier-premium"]))
        self.assertEqual(plan.excluded, (EX["tier-enterprise-legacy"],))

    def test_condition_without_concepts_is_refused(self) -> None:
        data = graph(ENTITLEMENT)
        data.remove((EX.entitlement, None, EX["tier-premium"]))
        data.remove((EX.entitlement, None, EX["tier-enterprise"]))
        data.remove((EX.entitlement, None, EX["tier-enterprise-legacy"]))
        with self.assertRaises(IRCompileError):
            compile_concept_condition(data, EX.entitlement)

    def test_wildcard_condition_is_refused(self) -> None:
        data = graph(ENTITLEMENT)
        data.set((EX.entitlement, ELG.wildcardSemantics, ELG.SingleDimensionWildcard))
        with self.assertRaises(IRCompileError):
            compile_concept_condition(data, EX.entitlement)

    def test_interval_strategy_is_refused(self) -> None:
        data = graph(ENTITLEMENT)
        data.set((EX.entitlement, ELG.matchStrategy, ELG.IntervalContainment))
        with self.assertRaises(IRCompileError):
            compile_concept_condition(data, EX.entitlement)



class ConceptSparqlTests(unittest.TestCase):
    def setUp(self) -> None:
        self.data = graph(ENTITLEMENT)
        self.decisions = run(compile_concept_condition(self.data, EX.entitlement), self.data)

    def test_required_candidate_is_permitted(self) -> None:
        self.assertEqual(self.decisions[EX["q-premium"]], "Permitted")

    def test_candidate_outside_every_required_concept_is_denied(self) -> None:
        self.assertEqual(self.decisions[EX["q-free"]], "Denied")

    def test_exclusion_takes_precedence_over_inclusion(self) -> None:
        # L10: legacy is both required and excluded
        self.assertEqual(self.decisions[EX["q-legacy"]], "Denied")

    def test_absent_candidate_is_undetermined(self) -> None:
        self.assertEqual(self.decisions[EX["q-absent"]], "Undetermined")

    def test_several_candidates_are_undetermined(self) -> None:
        self.assertEqual(self.decisions[EX["q-two"]], "Undetermined")

    def test_provenance_names_the_plan_kind_and_every_concept(self) -> None:
        artefact = compile_query_template(compile_concept_condition(self.data, EX.entitlement))
        plan_node = next(artefact.subjects(RDF.type, EXE.ConceptMatchPlan))
        self.assertEqual(
            set(artefact.objects(plan_node, EXE.derivedFromVocabularyNode)),
            {EX["tier-premium"], EX["tier-enterprise"], EX["tier-enterprise-legacy"]},
        )

    def test_compilation_is_deterministic(self) -> None:
        plan = compile_concept_condition(self.data, EX.entitlement)
        self.assertTrue(isomorphic(compile_query_template(plan), compile_query_template(plan)))


class ExampleTests(unittest.TestCase):
    def test_exact_condition_example_compiles_and_evaluates(self) -> None:
        data = Graph().parse(EXAMPLES / "condition-taxonomy.ttl")
        data += graph(PREFIXES + """
            ex:q-full a elg:Question ; elg:forCondition ex:exact-condition ; elg:candidateConcept ex:full-time .
            ex:q-part a elg:Question ; elg:forCondition ex:exact-condition ; elg:candidateConcept ex:part-time .
        """)
        decisions = run(compile_concept_condition(data, EX["exact-condition"]), data)
        self.assertEqual(decisions, {EX["q-full"]: "Permitted", EX["q-part"]: "Denied"})


if __name__ == "__main__":
    unittest.main()
