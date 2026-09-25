# SPDX-License-Identifier: MPL-2.0

"""
Hierarchical match, exclusion-only conditions and scheme resolution through
the shared IR (ADR-A85, ADR-A87, ADR-A89).

Decisions are checked by executing the generated SPARQL with rdflib. The
plan's own expansion is the oracle for parity: every member of the resolved
scheme is asked once through SPARQL and must receive the expansion's decision.
"""

from __future__ import annotations

import unittest
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict

from rdflib import Graph, Namespace, URIRef
from rdflib.namespace import RDF

from .eligibility_ir import (
    ConceptPlan,
    IRCompileError,
    ResolutionContext,
    compile_concept_condition,
)
from .namespaces import ELG, EXE, MORK
from .sparql_backend import compile_query_template

EX = Namespace("https://example.org/lattice/eligibility/")

HEADER = """
@prefix elg: <https://www.nebularis.org/neuro-semantic/lattice/eligibility#> .
@prefix voc: <https://www.nebularis.org/neuro-semantic/lattice/vocabulary#> .
@prefix fnd: <https://www.nebularis.org/neuro-semantic/lattice/foundation#> .
@prefix skos: <http://www.w3.org/2004/02/skos/core#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
@prefix ex: <https://example.org/lattice/eligibility/> .
"""

# A trial admits solid tumours except those of the central nervous system.
DIAGNOSES = HEADER + """
ex:diagnoses-2026 a voc:ConceptScheme .
ex:neoplasm a skos:Concept ; skos:inScheme ex:diagnoses-2026 .
ex:solid-tumour a skos:Concept ; skos:inScheme ex:diagnoses-2026 ; skos:broader ex:neoplasm .
ex:cns-tumour a skos:Concept ; skos:inScheme ex:diagnoses-2026 ; skos:broader ex:solid-tumour .
ex:glioma a skos:Concept ; skos:inScheme ex:diagnoses-2026 ; skos:broader ex:cns-tumour .
ex:lung-tumour a skos:Concept ; skos:inScheme ex:diagnoses-2026 ; skos:broader ex:solid-tumour .
ex:haematological a skos:Concept ; skos:inScheme ex:diagnoses-2026 ; skos:broader ex:neoplasm .
ex:unlisted a skos:Concept .

ex:diagnosis-contract a voc:SchemeContract ; voc:boundScheme ex:diagnoses-2026 .

ex:solid-tumour-arm a elg:Condition ;
    elg:matchStrategy elg:HierarchicalMatch ;
    elg:compatibilityOperation elg:AllRequired ;
    elg:wildcardSemantics elg:NoWildcard ;
    elg:constrainedByContract ex:diagnosis-contract ;
    elg:requiredConcept ex:solid-tumour ;
    elg:excludedConcept ex:cns-tumour .

ex:non-haematological a elg:Condition ;
    elg:matchStrategy elg:HierarchicalMatch ;
    elg:compatibilityOperation elg:AllRequired ;
    elg:wildcardSemantics elg:NoWildcard ;
    elg:constrainedByContract ex:diagnosis-contract ;
    elg:excludedConcept ex:haematological .

ex:not-haematological-flat a elg:SetMembershipCondition ;
    elg:matchStrategy elg:SetMembership ;
    elg:compatibilityOperation elg:AllRequired ;
    elg:wildcardSemantics elg:NoWildcard ;
    elg:constrainedByContract ex:diagnosis-contract ;
    elg:excludedConcept ex:haematological .
"""

# One contract, two editions, handed over at the start of 2026.
EDITIONS = HEADER + """
ex:grades-2025 a voc:ConceptScheme .
ex:grades-2026 a voc:ConceptScheme .
ex:engineering a skos:Concept ; skos:inScheme ex:grades-2025 , ex:grades-2026 .
ex:platform a skos:Concept ; skos:inScheme ex:grades-2025 , ex:grades-2026 ; skos:broader ex:engineering .
ex:data a skos:Concept ; skos:inScheme ex:grades-2026 ; skos:broader ex:engineering .

ex:grade-contract a voc:SchemeContract .
ex:binding-2025 a voc:SchemeBinding ; voc:forContract ex:grade-contract ; voc:bindsScheme ex:grades-2025 ;
    fnd:hasTemporalScope [ a fnd:TemporalScope ;
        fnd:validFrom "2025-01-01T00:00:00Z"^^xsd:dateTime ; fnd:validTo "2026-01-01T00:00:00Z"^^xsd:dateTime ] .
ex:binding-2026 a voc:SchemeBinding ; voc:forContract ex:grade-contract ; voc:bindsScheme ex:grades-2026 ;
    fnd:hasTemporalScope [ a fnd:TemporalScope ; fnd:validFrom "2026-01-01T00:00:00Z"^^xsd:dateTime ] .

ex:engineering-benefit a elg:Condition ;
    elg:matchStrategy elg:HierarchicalMatch ;
    elg:compatibilityOperation elg:AllRequired ;
    elg:wildcardSemantics elg:NoWildcard ;
    elg:constrainedByContract ex:grade-contract ;
    elg:requiredConcept ex:engineering .
"""

BEFORE = ResolutionContext(at=datetime(2025, 6, 1, tzinfo=timezone.utc))
AFTER = ResolutionContext(at=datetime(2026, 6, 1, tzinfo=timezone.utc))


def graph(text: str) -> Graph:
    return Graph().parse(data=text, format="turtle")


def ask(data: Graph, plan: ConceptPlan, candidates: Dict[str, URIRef]) -> Dict[str, str]:
    """Add one question per candidate, run the plan's SPARQL, return name -> decision."""
    asked = Graph()
    asked += data
    for name, concept in candidates.items():
        question = EX[f"q-{name}"]
        asked.add((question, RDF.type, ELG.Question))
        asked.add((question, ELG.forCondition, plan.condition))
        if concept is not None:
            asked.add((question, ELG.candidateConcept, concept))
    artefact = compile_query_template(plan)
    template = next(artefact.subjects(RDF.type, MORK.QueryTemplate))
    rows = asked.query(str(artefact.value(template, MORK.queryText)))
    by_question = {row.question: str(row.decision) for row in rows}
    return {name: by_question[EX[f"q-{name}"]] for name in candidates}


class HierarchicalDecisionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.data = graph(DIAGNOSES)
        self.plan = compile_concept_condition(self.data, EX["solid-tumour-arm"])
        self.decisions = ask(
            self.data,
            self.plan,
            {
                "lung": EX["lung-tumour"],
                "glioma": EX.glioma,
                "cns": EX["cns-tumour"],
                "solid": EX["solid-tumour"],
                "neoplasm": EX.neoplasm,
                "haematological": EX.haematological,
                "unlisted": EX.unlisted,
                "absent": None,
            },
        )

    def test_candidate_below_a_required_concept_is_permitted(self) -> None:
        self.assertEqual(self.decisions["lung"], "Permitted")

    def test_candidate_at_or_below_an_exclusion_is_denied(self) -> None:
        # L10, at and below
        self.assertEqual((self.decisions["cns"], self.decisions["glioma"]), ("Denied", "Denied"))

    def test_candidate_above_an_exclusion_is_undetermined(self) -> None:
        # L11: solid-tumour is required and stands above cns-tumour
        self.assertEqual(self.decisions["solid"], "Undetermined")

    def test_candidate_outside_every_inclusion_is_denied(self) -> None:
        self.assertEqual((self.decisions["neoplasm"], self.decisions["haematological"]), ("Denied", "Denied"))

    def test_candidate_outside_the_scheme_and_absent_candidate_are_undetermined(self) -> None:
        self.assertEqual((self.decisions["unlisted"], self.decisions["absent"]), ("Undetermined", "Undetermined"))

    def test_plan_records_the_scheme_and_its_provenance(self) -> None:
        self.assertEqual(self.plan.scheme.scheme, EX["diagnoses-2026"])
        self.assertIsNone(self.plan.scheme.binding)
        artefact = compile_query_template(self.plan)
        plan_node = next(artefact.subjects(RDF.type, EXE.ConceptMatchPlan))
        vocabulary = set(artefact.objects(plan_node, EXE.derivedFromVocabularyNode))
        self.assertTrue({EX["diagnosis-contract"], EX["diagnoses-2026"]} <= vocabulary)


class ExclusionOnlyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.data = graph(DIAGNOSES)

    def test_hierarchical_exclusion_only_admits_the_rest_of_the_scheme(self) -> None:
        plan = compile_concept_condition(self.data, EX["non-haematological"])
        decisions = ask(
            self.data, plan,
            {"lung": EX["lung-tumour"], "haematological": EX.haematological, "neoplasm": EX.neoplasm, "unlisted": EX.unlisted},
        )
        # L12 admits lung, L10 denies haematological, L11 leaves neoplasm undetermined
        self.assertEqual(
            decisions,
            {"lung": "Permitted", "haematological": "Denied", "neoplasm": "Undetermined", "unlisted": "Undetermined"},
        )

    def test_flat_exclusion_only_admits_every_other_member(self) -> None:
        plan = compile_concept_condition(self.data, EX["not-haematological-flat"])
        decisions = ask(
            self.data, plan,
            {"neoplasm": EX.neoplasm, "haematological": EX.haematological, "unlisted": EX.unlisted},
        )
        self.assertEqual(decisions, {"neoplasm": "Permitted", "haematological": "Denied", "unlisted": "Undetermined"})

    def test_exclusion_only_without_a_contract_is_refused(self) -> None:
        self.data.remove((EX["non-haematological"], ELG.constrainedByContract, None))
        with self.assertRaises(IRCompileError):
            compile_concept_condition(self.data, EX["non-haematological"])


class ParityTests(unittest.TestCase):
    def test_sparql_agrees_with_the_expansion_for_every_member(self) -> None:
        data = graph(DIAGNOSES)
        for condition in (EX["solid-tumour-arm"], EX["non-haematological"], EX["not-haematological-flat"]):
            plan = compile_concept_condition(data, condition)
            expected = {str(concept): decision for concept, decision in plan.expansion}
            asked = ask(data, plan, {str(concept): concept for concept, _ in plan.expansion})
            self.assertEqual(asked, expected, str(condition))


class ResolutionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.data = graph(EDITIONS)

    def test_contract_with_bindings_needs_an_explicit_instant(self) -> None:
        with self.assertRaises(IRCompileError):
            compile_concept_condition(self.data, EX["engineering-benefit"])

    def test_instants_either_side_of_the_handover_resolve_different_editions(self) -> None:
        before = compile_concept_condition(self.data, EX["engineering-benefit"], BEFORE)
        after = compile_concept_condition(self.data, EX["engineering-benefit"], AFTER)
        self.assertEqual((before.scheme.scheme, before.scheme.binding), (EX["grades-2025"], EX["binding-2025"]))
        self.assertEqual((after.scheme.scheme, after.scheme.binding), (EX["grades-2026"], EX["binding-2026"]))
        self.assertEqual(ask(self.data, before, {"data": EX.data}), {"data": "Undetermined"})
        self.assertEqual(ask(self.data, after, {"data": EX.data}), {"data": "Permitted"})

    def test_conflicting_bindings_are_refused(self) -> None:
        self.data += graph(HEADER + """
            ex:binding-rival a voc:SchemeBinding ; voc:forContract ex:grade-contract ; voc:bindsScheme ex:grades-2025 ;
                fnd:hasTemporalScope [ a fnd:TemporalScope ; fnd:validFrom "2026-01-01T00:00:00Z"^^xsd:dateTime ] .
        """)
        with self.assertRaises(IRCompileError):
            compile_concept_condition(self.data, EX["engineering-benefit"], AFTER)

    def test_cyclic_scheme_is_refused(self) -> None:
        self.data.add((EX.engineering, URIRef("http://www.w3.org/2004/02/skos/core#broader"), EX.platform))
        with self.assertRaises(IRCompileError):
            compile_concept_condition(self.data, EX["engineering-benefit"], AFTER)



class ExampleTests(unittest.TestCase):
    def test_hierarchical_example_reaches_its_recorded_decision(self) -> None:
        example = Path(__file__).resolve().parents[4] / "ontology/eligibility/examples/hierarchical-match.ttl"
        data = Graph().parse(example)
        plan = compile_concept_condition(data, EX["hierarchical-condition"])
        artefact = compile_query_template(plan)
        template = next(artefact.subjects(RDF.type, MORK.QueryTemplate))
        rows = {row.question: str(row.decision) for row in data.query(str(artefact.value(template, MORK.queryText)))}
        recorded = data.value(EX.decision, ELG.decisionValue)
        self.assertEqual(rows, {EX["subject-question"]: "Permitted"})
        self.assertEqual(recorded, ELG.Permitted)


if __name__ == "__main__":
    unittest.main()
