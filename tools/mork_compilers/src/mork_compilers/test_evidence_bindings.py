# SPDX-License-Identifier: MPL-2.0

"""
Conditions and profiles evaluated through ``elg:EvidenceBinding`` (ADR-A91).

The fixture is ``ontology/eligibility/examples/evidence-binding.ttl`` plus
employees that exercise the Undetermined cases. SPARQL is the reference.
SHACL must agree with it, and SWRL must derive a sound subset.
"""

from __future__ import annotations

import unittest
from pathlib import Path
from typing import Dict

from pyshacl import validate
from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.compare import isomorphic
from rdflib.namespace import RDF

from .common import mint
from .eligibility_ir import IRCompileError, compile_any_condition, compile_profile
from .namespaces import ELG, EXE, MORK, SH
from .shacl_backend import compile_shapes
from .sparql_backend import compile_query_template
from .swrl_backend import compile_rules
from .test_concept_backends import apply_rules

ROOT = Path(__file__).resolve().parents[4]
EX = Namespace("https://example.org/lattice/eligibility/employment/")
DECISION = {ELG.Permitted: "Permitted", ELG.Denied: "Denied"}

EXTRA = """
@prefix qnt: <https://www.nebularis.org/neuro-semantic/lattice/quantification#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix ex: <https://example.org/lattice/eligibility/employment/> .

ex:Manager rdfs:subClassOf ex:Employee .
ex:other-space a qnt:ValueSpace .
ex:three-months a qnt:Quantity ; qnt:onSpace ex:other-space ; qnt:numericValue 3 .
ex:six-years a qnt:Quantity ; qnt:onSpace ex:tenure-space ; qnt:numericValue 6 .

ex:erin a ex:Employee ; ex:holdsRole [ ex:inJobFamily ex:platform-engineering ] ; ex:tenureYears ex:three-months .
ex:frank a ex:Employee ; ex:holdsRole [ ex:inJobFamily ex:platform-engineering ] .
ex:gina a ex:Employee ;
    ex:holdsRole [ ex:inJobFamily ex:platform-engineering ] , [ ex:inJobFamily ex:contractor-engineering ] ;
    ex:tenureYears 2 .
ex:hal a ex:Manager ; ex:holdsRole [ ex:inJobFamily ex:platform-engineering ] ; ex:tenureYears ex:six-years .
"""

FAMILY = {
    "alice": "Permitted", "bob": "Denied", "carol": "Permitted", "dan": "Undetermined",
    "erin": "Permitted", "frank": "Permitted", "gina": "Undetermined", "hal": "Permitted",
}
TENURE = {
    "alice": "Permitted", "bob": "Permitted", "carol": "Denied", "dan": "Permitted",
    "erin": "Undetermined", "frank": "Undetermined", "gina": "Permitted", "hal": "Permitted",
}
BENEFIT = {
    "alice": "Permitted", "bob": "Denied", "carol": "Denied", "dan": "Undetermined",
    "erin": "Undetermined", "frank": "Undetermined", "gina": "Undetermined", "hal": "Permitted",
}


def fixture() -> Graph:
    data = Graph().parse(ROOT / "ontology/eligibility/examples/evidence-binding.ttl")
    data.parse(data=EXTRA, format="turtle")
    return data


def local(node) -> str:
    return str(node).rsplit("/", 1)[-1]


def sparql(plan, data: Graph) -> Dict[str, tuple]:
    artefact = compile_query_template(plan)
    template = next(artefact.subjects(RDF.type, MORK.QueryTemplate))
    variable = "record" if hasattr(plan, "profile") else "question"
    return {
        local(row[variable]): (str(row.decision), row.diagnostic)
        for row in data.query(str(artefact.value(template, MORK.queryText)))
    }


def shacl(plan, data: Graph, roles) -> Dict[str, str]:
    """Read the report in the shapes' order: the first role that reports a
    subject gives its outcome, and an unreported subject is Permitted."""
    owner = plan.profile if hasattr(plan, "profile") else plan.condition
    _, report, _ = validate(data, shacl_graph=compile_shapes(plan), advanced=True, inference="none")
    reported: Dict[URIRef, set] = {}
    for result in report.subjects(RDF.type, SH.ValidationResult):
        reported.setdefault(report.value(result, SH.focusNode), set()).add(report.value(result, SH.sourceShape))
    decisions = {}
    for subject in set(data.subjects(RDF.type, EX.Employee)) | set(data.subjects(RDF.type, EX.Manager)):
        found = reported.get(subject, set())
        outcome = "Permitted"
        for role, decision in roles:
            if mint(owner, f"{role}-shape") in found:
                outcome = decision
                break
        decisions[local(subject)] = outcome
    return decisions


CONCEPT_ROLES = [("readiness", "Undetermined"), ("determinacy", "Undetermined"), ("admission", "Denied")]
INTERVAL_ROLES = [("readiness", "Undetermined"), ("determinacy", "Undetermined"), ("containment", "Denied")]
PROFILE_ROLES = [("profile-undetermined", "Undetermined"), ("profile-denied", "Denied")]


class BoundSparqlTests(unittest.TestCase):
    def setUp(self) -> None:
        self.data = fixture()

    def test_bound_concept_condition_reads_through_two_steps(self) -> None:
        rows = sparql(compile_any_condition(self.data, EX["engineering-family"]), self.data)
        self.assertEqual({k: d for k, (d, _) in rows.items()}, FAMILY)
        self.assertEqual(rows["dan"][1], EXE.AboveExclusion)
        self.assertEqual(rows["gina"][1], EXE.SeveralCandidates)

    def test_bound_interval_condition_reads_literals_and_quantities(self) -> None:
        rows = sparql(compile_any_condition(self.data, EX["minimum-tenure"]), self.data)
        self.assertEqual({k: d for k, (d, _) in rows.items()}, TENURE)
        self.assertEqual(rows["erin"][1], EXE.ValueSpaceMismatch)
        self.assertEqual(rows["frank"][1], EXE.MissingCandidate)

    def test_bound_profile_decides_each_subject(self) -> None:
        rows = sparql(compile_profile(self.data, EX["relocation-benefit"]), self.data)
        self.assertEqual({k: d for k, (d, _) in rows.items()}, BENEFIT)
        for decision, diagnostic in rows.values():
            self.assertEqual(decision == "Undetermined", diagnostic is not None)


class BoundShaclTests(unittest.TestCase):
    def setUp(self) -> None:
        self.data = fixture()

    def test_concept_shapes_agree_with_sparql(self) -> None:
        plan = compile_any_condition(self.data, EX["engineering-family"])
        self.assertEqual(shacl(plan, self.data, CONCEPT_ROLES), FAMILY)

    def test_interval_shapes_agree_with_sparql(self) -> None:
        plan = compile_any_condition(self.data, EX["minimum-tenure"])
        self.assertEqual(shacl(plan, self.data, INTERVAL_ROLES), TENURE)

    def test_profile_shapes_agree_with_sparql(self) -> None:
        plan = compile_profile(self.data, EX["relocation-benefit"])
        self.assertEqual(shacl(plan, self.data, PROFILE_ROLES), BENEFIT)


class BoundSwrlTests(unittest.TestCase):
    def test_rules_derive_a_sound_subset(self) -> None:
        data = fixture()
        data.remove((EX.gina, None, None))  # SWRL assumes one value per subject
        plan = compile_profile(data, EX["relocation-benefit"])
        rules = Graph()
        for part in list(plan.conditions) + [plan]:
            rules += compile_rules(part)
        derived = apply_rules(data, rules)
        outcomes = {local(s): DECISION[d] for s, _, d in derived.triples((None, EXE.impliesProfileDecision, None))}
        for name, decision in outcomes.items():
            self.assertEqual(decision, BENEFIT[name], name)
        # Tenure has no scheme or exclusion, so SWRL never denies carol. The
        # tenure binding reads a literal, so SWRL cannot read hal's quantity.
        # Bob is denied by his contractor family.
        self.assertEqual(outcomes, {"alice": "Permitted", "bob": "Denied"})
        self.assertIn((EX.carol, EXE.permittedUnder, EX["engineering-family"]), derived)
        self.assertNotIn((EX.carol, EXE.permittedUnder, EX["minimum-tenure"]), derived)


class BindingRefusalTests(unittest.TestCase):
    def setUp(self) -> None:
        self.data = fixture()

    def test_two_bindings_for_one_condition_are_refused(self) -> None:
        self.data.add((EX["second-binding"], ELG.bindsCondition, EX["minimum-tenure"]))
        with self.assertRaises(IRCompileError):
            compile_any_condition(self.data, EX["minimum-tenure"])

    def test_gap_in_step_indexes_is_refused(self) -> None:
        step = next(self.data.objects(EX["tenure-binding"], ELG.evidenceStep))
        self.data.set((step, ELG.stepIndex, Literal(1)))
        with self.assertRaises(IRCompileError):
            compile_any_condition(self.data, EX["minimum-tenure"])

    def test_reading_on_another_space_is_refused(self) -> None:
        self.data.set((EX["tenure-binding"], ELG.readOnSpace, EX["other-space"]))
        with self.assertRaises(IRCompileError):
            compile_any_condition(self.data, EX["minimum-tenure"])

    def test_profile_mixing_bound_and_question_conditions_is_refused(self) -> None:
        self.data.remove((EX["tenure-binding"], None, None))
        with self.assertRaises(IRCompileError):
            compile_profile(self.data, EX["relocation-benefit"])


class InverseStepTests(unittest.TestCase):
    def test_inverse_step_walks_from_object_to_subject(self) -> None:
        data = fixture()
        for step in list(data.objects(EX["family-binding"], ELG.evidenceStep)):
            data.remove((step, None, None))
        data.remove((EX["family-binding"], ELG.evidenceStep, None))
        data.parse(data="""
            @prefix elg: <https://www.nebularis.org/neuro-semantic/lattice/eligibility#> .
            @prefix ex: <https://example.org/lattice/eligibility/employment/> .
            ex:team-a ex:member ex:alice ; ex:inJobFamily ex:contractor-engineering .
            ex:family-binding elg:evidenceStep [ elg:stepIndex 0 ; elg:stepProperty ex:member ; elg:stepDirection elg:Inverse ] ,
                                               [ elg:stepIndex 1 ; elg:stepProperty ex:inJobFamily ; elg:stepDirection elg:Forward ] .
        """, format="turtle")
        plan = compile_any_condition(data, EX["engineering-family"])
        self.assertEqual(plan.evidence.steps, ((EX.member, True), (EX.inJobFamily, False)))
        rows = sparql(plan, data)
        self.assertEqual(rows["alice"][0], "Denied")  # her team is contractor engineering
        self.assertEqual(rows["bob"][0], "Undetermined")  # in no team


class BoundDeterminismTests(unittest.TestCase):
    def test_bound_artefacts_are_deterministic(self) -> None:
        data = fixture()
        for plan in (compile_any_condition(data, EX["minimum-tenure"]), compile_profile(data, EX["relocation-benefit"])):
            for backend in (compile_query_template, compile_shapes, compile_rules):
                self.assertTrue(isomorphic(backend(plan), backend(plan)))


if __name__ == "__main__":
    unittest.main()
