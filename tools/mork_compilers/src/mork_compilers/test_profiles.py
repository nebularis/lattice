# SPDX-License-Identifier: MPL-2.0

"""
Profile aggregation across SPARQL, SHACL and SWRL (ADR-A89 item 5).

Two conditions: a diagnosis condition (solid tumours, excluding CNS tumours)
and a consent condition. Each record answers some of them. The expected
outcomes below are strong Kleene conjunction (AllRequired) and disjunction
(AnySufficient), with an unanswered condition counted as Undetermined.
"""

from __future__ import annotations

import unittest
from pathlib import Path
from typing import Dict, Tuple

from pyshacl import validate
from rdflib import Graph, URIRef
from rdflib.compare import isomorphic
from rdflib.namespace import RDF

from .common import mint
from .eligibility_ir import IRCompileError, ProfilePlan, compile_profile
from .namespaces import ELG, EXE, MORK, SH
from .shacl_backend import compile_shapes
from .sparql_backend import compile_query_template
from .swrl_backend import compile_rules
from .test_concept_backends import apply_rules
from .test_hierarchical_conditions import DIAGNOSES, EX

ROOT = Path(__file__).resolve().parents[4]

PROFILES = DIAGNOSES + """
ex:consented a skos:Concept .
ex:refused a skos:Concept .

ex:consent a elg:SetMembershipCondition ;
    elg:matchStrategy elg:SetMembership ;
    elg:compatibilityOperation elg:AllRequired ;
    elg:wildcardSemantics elg:NoWildcard ;
    elg:requiredConcept ex:consented .

ex:all-arm a elg:AdmissionProfile ;
    elg:hasCondition ex:solid-tumour-arm , ex:consent ;
    elg:matchStrategy elg:SetMembership ;
    elg:compatibilityOperation elg:AllRequired ;
    elg:wildcardSemantics elg:NoWildcard .

ex:any-arm a elg:AdmissionProfile ;
    elg:hasCondition ex:solid-tumour-arm , ex:consent ;
    elg:matchStrategy elg:SetMembership ;
    elg:compatibilityOperation elg:AnySufficient ;
    elg:wildcardSemantics elg:NoWildcard .
"""

# record -> (diagnosis candidate or None, consent candidate or None)
RECORDS: Dict[str, Tuple[URIRef, URIRef]] = {
    "r1": (EX["lung-tumour"], EX.consented),
    "r2": (EX.glioma, EX.consented),
    "r3": (EX["solid-tumour"], EX.consented),
    "r4": (EX["solid-tumour"], EX.refused),
    "r5": (EX.glioma, EX.refused),
    "r6": (EX["lung-tumour"], None),
    "r7": (None, None),
    "r8": (EX.glioma, None),
}

EXPECTED = {
    "all-arm": {"r1": "Permitted", "r2": "Denied", "r3": "Undetermined", "r4": "Denied",
                "r5": "Denied", "r6": "Undetermined", "r7": "Undetermined", "r8": "Denied"},
    "any-arm": {"r1": "Permitted", "r2": "Permitted", "r3": "Permitted", "r4": "Undetermined",
                "r5": "Denied", "r6": "Permitted", "r7": "Undetermined", "r8": "Undetermined"},
}


def records(profile: str) -> Graph:
    data = Graph().parse(data=PROFILES, format="turtle")
    for name, (diagnosis, consent) in RECORDS.items():
        record = EX[f"{profile}-{name}"]
        data.add((record, RDF.type, ELG.EligibilityDecision))
        data.add((record, ELG.forProfile, EX[profile]))
        for condition, candidate in ((EX["solid-tumour-arm"], diagnosis), (EX.consent, consent)):
            if candidate is None:
                continue
            question = EX[f"{profile}-{name}-{condition.split('/')[-1]}"]
            data.add((question, RDF.type, ELG.Question))
            data.add((question, ELG.forCondition, condition))
            data.add((question, ELG.candidateConcept, candidate))
            data.add((record, ELG.hasQuestion, question))
    return data


def name_of(profile: str, record: URIRef) -> str:
    return str(record).rsplit(f"{profile}-", 1)[1]


def sparql(plan: ProfilePlan, data: Graph, profile: str) -> Dict[str, Tuple[str, object]]:
    artefact = compile_query_template(plan)
    template = next(artefact.subjects(RDF.type, MORK.QueryTemplate))
    rows = data.query(str(artefact.value(template, MORK.queryText)))
    return {name_of(profile, row.record): (str(row.decision), row.diagnostic) for row in rows}


def shacl(plan: ProfilePlan, data: Graph, profile: str) -> Dict[str, str]:
    _, report, _ = validate(data, shacl_graph=compile_shapes(plan), advanced=True, inference="none")
    reported = {}
    for result in report.subjects(RDF.type, SH.ValidationResult):
        reported[report.value(result, SH.focusNode)] = report.value(result, SH.sourceShape)
    outcome = {
        mint(plan.profile, "profile-undetermined-shape"): "Undetermined",
        mint(plan.profile, "profile-denied-shape"): "Denied",
    }
    return {
        name_of(profile, record): outcome.get(reported.get(record), "Permitted")
        for record in data.subjects(ELG.forProfile, EX[profile])
    }


class ProfileTests(unittest.TestCase):
    def test_sparql_aggregates_by_strong_kleene_logic(self) -> None:
        for profile in ("all-arm", "any-arm"):
            data = records(profile)
            decisions = {n: d for n, (d, _) in sparql(compile_profile(data, EX[profile]), data, profile).items()}
            self.assertEqual(decisions, EXPECTED[profile], profile)

    def test_undetermined_records_carry_a_diagnostic(self) -> None:
        data = records("all-arm")
        rows = sparql(compile_profile(data, EX["all-arm"]), data, "all-arm")
        self.assertEqual(rows["r7"][1], EXE.MissingCandidate)  # nothing answered
        self.assertEqual(rows["r6"][1], EXE.MissingCandidate)  # consent unanswered
        self.assertEqual(rows["r3"][1], EXE.AboveExclusion)  # diagnosis above the exclusion
        for decision, diagnostic in rows.values():
            self.assertEqual(decision == "Undetermined", diagnostic is not None)

    def test_shacl_agrees_with_sparql(self) -> None:
        for profile in ("all-arm", "any-arm"):
            data = records(profile)
            plan = compile_profile(data, EX[profile])
            self.assertEqual(shacl(plan, data, profile), EXPECTED[profile], profile)

    def test_swrl_derives_only_decided_outcomes(self) -> None:
        # The consent condition has no scheme and no exclusion, so SWRL cannot
        # deny "refused" from a positive fact (ADR-A24). It derives a sound
        # subset of the decided outcomes, exactly these:
        derivable = {
            "all-arm": {"r1": "Permitted", "r2": "Denied", "r5": "Denied", "r8": "Denied"},
            "any-arm": {"r1": "Permitted", "r2": "Permitted", "r3": "Permitted", "r6": "Permitted"},
        }
        for profile in ("all-arm", "any-arm"):
            data = records(profile)
            plan = compile_profile(data, EX[profile])
            rules = Graph()
            for part in list(plan.conditions) + [plan]:
                rules += compile_rules(part)
            derived = apply_rules(data, rules)
            outcomes = {
                name_of(profile, record): {ELG.Permitted: "Permitted", ELG.Denied: "Denied"}[decision]
                for record, _, decision in derived.triples((None, EXE.impliesProfileDecision, None))
            }
            for name, decision in outcomes.items():
                self.assertEqual(decision, EXPECTED[profile][name], f"{profile} {name}")  # sound
            self.assertEqual(outcomes, derivable[profile], profile)

    def test_dimension_consistent_is_refused(self) -> None:
        data = records("all-arm")
        data.set((EX["all-arm"], ELG.compatibilityOperation, ELG.DimensionConsistent))
        with self.assertRaises(IRCompileError):
            compile_profile(data, EX["all-arm"])

    def test_profile_plan_links_its_condition_plans(self) -> None:
        data = records("all-arm")
        artefact = compile_query_template(compile_profile(data, EX["all-arm"]))
        plan_node = next(artefact.subjects(RDF.type, EXE.ProfilePlan))
        self.assertEqual(
            set(artefact.objects(plan_node, EXE.hasConditionPlan)),
            {mint(EX["solid-tumour-arm"], "execplan"), mint(EX.consent, "execplan")},
        )
        self.assertEqual(artefact.value(plan_node, EXE.usesCompatibilityOperation), ELG.AllRequired)

    def test_interval_profile_compiles_and_evaluates(self) -> None:
        data = Graph().parse(ROOT / "ontology/eligibility/examples/interval-containment.ttl")
        artefact = compile_query_template(compile_profile(data, EX["profile-a"]))
        template = next(artefact.subjects(RDF.type, MORK.QueryTemplate))
        rows = [(row.record, str(row.decision), row.diagnostic) for row in data.query(str(artefact.value(template, MORK.queryText)))]
        self.assertEqual(rows, [(EX["decision-1"], "Permitted", None)])

    def test_profile_artefacts_are_deterministic(self) -> None:
        plan = compile_profile(records("any-arm"), EX["any-arm"])
        for backend in (compile_query_template, compile_shapes, compile_rules):
            self.assertTrue(isomorphic(backend(plan), backend(plan)))


if __name__ == "__main__":
    unittest.main()
