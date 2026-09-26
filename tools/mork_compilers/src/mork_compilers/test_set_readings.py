# SPDX-License-Identifier: MPL-2.0

"""
Set readings and negation (ADR-A103, elg:L15, elg:L16), AIR-3.2 of the
applied-insurance-reference epic.

One hierarchical condition decides each value as a single candidate would: a
value under ``ex:a`` is Permitted, one elsewhere in the scheme Denied, and one
outside the scheme Undetermined. Each subject carries a known mix of those
outcomes, so each reading's strong Kleene table can be checked row by row.
SPARQL is the reference. SHACL must agree with it, and SWRL and OWL must
refuse until AIR-3.3.
"""

from __future__ import annotations

import unittest
from pathlib import Path
from typing import Dict, Optional, Tuple

from pyshacl import validate
from rdflib import Graph, Namespace, URIRef
from rdflib.namespace import RDF

from .common import mint
from .eligibility_ir import IRCompileError, compile_any_condition, compile_profile
from .namespaces import EXE, MORK, SH
from .owl_backend import compile_classes
from .shacl_backend import compile_shapes
from .sparql_backend import compile_query_template
from .swrl_backend import compile_rules

EXAMPLES = Path(__file__).resolve().parents[4] / "ontology/eligibility/examples"
EX = Namespace("https://example.org/lattice/eligibility/readings/")
ADM = Namespace("https://example.org/lattice/eligibility/admissions/")
TRIAL = Namespace("https://example.org/lattice/eligibility/trial/")

HEADER = """
@prefix elg: <https://www.nebularis.org/neuro-semantic/lattice/eligibility#> .
@prefix voc: <https://www.nebularis.org/neuro-semantic/lattice/vocabulary#> .
@prefix qnt: <https://www.nebularis.org/neuro-semantic/lattice/quantification#> .
@prefix skos: <http://www.w3.org/2004/02/skos/core#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
@prefix ex: <https://example.org/lattice/eligibility/readings/> .
"""

# ex:a and ex:a2 are Permitted, ex:b and ex:bx Denied, ex:stranger Undetermined (outside the scheme).
MIXES = {
    "pd": ("a", "b"),
    "dd": ("b", "bx"),
    "du": ("b", "stranger"),
    "pp": ("a", "a2"),
    "pu": ("a", "stranger"),
    "none": (),
}


def fixture(reading: Optional[str], negated: bool = False) -> Graph:
    subjects = "\n".join(
        f"ex:s-{name} a ex:Subject" + (" ; ex:has " + " , ".join(f"ex:{v}" for v in values) if values else "") + " ."
        for name, values in MIXES.items()
    )
    return Graph().parse(data=HEADER + f"""
ex:scheme a voc:ConceptScheme .
ex:contract a voc:SchemeContract ; voc:boundScheme ex:scheme .
ex:top a skos:Concept ; skos:inScheme ex:scheme .
ex:a a skos:Concept ; skos:inScheme ex:scheme ; skos:broader ex:top .
ex:a2 a skos:Concept ; skos:inScheme ex:scheme ; skos:broader ex:a .
ex:b a skos:Concept ; skos:inScheme ex:scheme ; skos:broader ex:top .
ex:bx a skos:Concept ; skos:inScheme ex:scheme ; skos:broader ex:b .
ex:stranger a skos:Concept .

ex:condition a elg:Condition ;
    elg:matchStrategy elg:HierarchicalMatch ;
    elg:compatibilityOperation elg:AllRequired ;
    elg:wildcardSemantics elg:NoWildcard ;
    elg:constrainedByContract ex:contract ;
    elg:requiredConcept ex:a {"; elg:negated true" if negated else ""} .
ex:binding a elg:EvidenceBinding ;
    elg:bindsCondition ex:condition ;
    elg:subjectClass ex:Subject ;
    {f"elg:valueReading elg:{reading} ;" if reading else ""}
    elg:evidenceStep [ a elg:EvidenceStep ; elg:stepIndex 0 ; elg:stepProperty ex:has ; elg:stepDirection elg:Forward ] .
{subjects}
""", format="turtle")


def sparql(plan, data: Graph) -> Dict[str, Tuple[str, Optional[URIRef]]]:
    artefact = compile_query_template(plan)
    template = next(artefact.subjects(RDF.type, MORK.QueryTemplate))
    rows = list(data.query(str(artefact.value(template, MORK.queryText))))
    keyed = {str(row[0]).rsplit("/", 1)[1]: (str(row.decision), row.diagnostic) for row in rows}
    assert len(keyed) == len(rows), "one decision per subject or question"
    return keyed


def decisions(rows) -> Dict[str, str]:
    return {name: decision for name, (decision, _) in rows.items()}


def shacl(plan, data: Graph, subjects) -> Dict[str, str]:
    """Read the decided shapes: determinacy reports Undetermined, admission Denied."""
    _, report, _ = validate(data, shacl_graph=compile_shapes(plan), advanced=True, inference="none")
    owner = plan.profile if hasattr(plan, "profile") else plan.condition
    roles = ("profile-undetermined", "profile-denied") if hasattr(plan, "profile") else ("determinacy", "admission")
    undetermined, denied = (mint(owner, f"{role}-shape") for role in roles)
    reported: Dict[URIRef, set] = {}
    for result in report.subjects(RDF.type, SH.ValidationResult):
        reported.setdefault(report.value(result, SH.focusNode), set()).add(report.value(result, SH.sourceShape))
    out = {}
    for subject in subjects:
        found = reported.get(subject, set())
        out[str(subject).rsplit("/", 1)[1]] = "Undetermined" if undetermined in found else "Denied" if denied in found else "Permitted"
    return out


class ReadingTests(unittest.TestCase):
    def test_some_value(self) -> None:
        # AIR32-01
        rows = decisions(sparql(compile_any_condition(data := fixture("SomeValue"), EX.condition), data))
        self.assertEqual(
            (rows["s-pd"], rows["s-dd"], rows["s-du"], rows["s-pu"]),
            ("Permitted", "Denied", "Undetermined", "Permitted"),
        )

    def test_every_value(self) -> None:
        # AIR32-02
        rows = decisions(sparql(compile_any_condition(data := fixture("EveryValue"), EX.condition), data))
        self.assertEqual(
            (rows["s-pp"], rows["s-pd"], rows["s-pu"], rows["s-du"]),
            ("Permitted", "Denied", "Undetermined", "Denied"),
        )

    def test_exclusion_read_every_value_denies_on_one_excluded_value(self) -> None:
        # AIR32-03
        data = Graph().parse(EXAMPLES / "set-reading-trial.ttl")
        rows = decisions(sparql(compile_any_condition(data, TRIAL["none-excluded"]), data))
        self.assertEqual(rows, {"pat-1": "Permitted", "pat-2": "Denied", "pat-3": "Permitted"})

    def test_no_value_is_undetermined_under_each_reading(self) -> None:
        # AIR32-04
        for reading in ("SomeValue", "EveryValue"):
            rows = sparql(compile_any_condition(data := fixture(reading), EX.condition), data)
            self.assertEqual(rows["s-none"], ("Undetermined", EXE.MissingCandidate), reading)

    def test_single_value_reading_is_unchanged(self) -> None:
        # AIR32-05: no reading, and an explicit SingleValue, behave as before
        for reading in (None, "SingleValue"):
            rows = sparql(compile_any_condition(data := fixture(reading), EX.condition), data)
            self.assertEqual(rows["s-pd"], ("Undetermined", EXE.SeveralCandidates), reading)
            self.assertEqual(rows["s-none"], ("Undetermined", EXE.MissingCandidate), reading)

    def test_undetermined_set_reports_a_value_diagnostic(self) -> None:
        rows = sparql(compile_any_condition(data := fixture("SomeValue"), EX.condition), data)
        self.assertEqual(rows["s-du"], ("Undetermined", EXE.OutsideScheme))


class NegationTests(unittest.TestCase):
    def test_negated_bound_condition_swaps_decided_outcomes(self) -> None:
        # AIR32-06, bound: SomeValue then negation
        plain = decisions(sparql(compile_any_condition(data := fixture("SomeValue"), EX.condition), data))
        rows = sparql(compile_any_condition(data := fixture("SomeValue", negated=True), EX.condition), data)
        swap = {"Permitted": "Denied", "Denied": "Permitted", "Undetermined": "Undetermined"}
        self.assertEqual(decisions(rows), {name: swap[decision] for name, decision in plain.items()})
        self.assertEqual(rows["s-du"], ("Undetermined", EXE.OutsideScheme))

    def test_negated_question_condition_swaps_decided_outcomes(self) -> None:
        # AIR32-06, question-based
        data = Graph().parse(data=HEADER + """
            ex:c a elg:Condition ; elg:matchStrategy elg:SetMembership ; elg:compatibilityOperation elg:AllRequired ;
                elg:wildcardSemantics elg:NoWildcard ; elg:requiredConcept ex:a ; elg:negated true .
            ex:q-in a elg:Question ; elg:forCondition ex:c ; elg:candidateConcept ex:a .
            ex:q-out a elg:Question ; elg:forCondition ex:c ; elg:candidateConcept ex:b .
            ex:q-absent a elg:Question ; elg:forCondition ex:c .
        """, format="turtle")
        rows = sparql(compile_any_condition(data, EX.c), data)
        self.assertEqual(rows["q-in"], ("Denied", None))
        self.assertEqual(rows["q-out"], ("Permitted", None))
        self.assertEqual(rows["q-absent"], ("Undetermined", EXE.MissingCandidate))

    def test_negated_some_value_refuses_a_medic(self) -> None:
        # AIR32-07
        data = Graph().parse(EXAMPLES / "set-reading-admissions.ttl")
        rows = decisions(sparql(compile_any_condition(data, ADM["no-medicine"]), data))
        self.assertEqual(rows, {"ada": "Permitted", "ben": "Permitted", "cai": "Undetermined", "dee": "Denied"})


class IntervalTests(unittest.TestCase):
    def test_interval_read_every_value(self) -> None:
        # AIR32-08
        data = Graph().parse(data=HEADER + """
            ex:space a qnt:ValueSpace .
            ex:ten a qnt:Quantity ; qnt:onSpace ex:space ; qnt:numericValue "10"^^xsd:decimal .
            ex:low a qnt:Bound ; qnt:onSpace ex:space ; qnt:boundValue ex:ten ; qnt:boundSense qnt:Lower ; qnt:boundClosure qnt:Closed .
            ex:range a qnt:Range ; qnt:onSpace ex:space ; qnt:lowerBound ex:low ; qnt:hasBound ex:low .
            ex:ranges a qnt:RangeSet ; qnt:onSpace ex:space ; qnt:hasRange ex:range .
            ex:c a elg:IntervalCondition ; elg:matchStrategy elg:IntervalContainment ; elg:compatibilityOperation elg:AllRequired ;
                elg:wildcardSemantics elg:NoWildcard ; elg:requiredRangeSet ex:ranges .
            ex:b a elg:EvidenceBinding ; elg:bindsCondition ex:c ; elg:subjectClass ex:Subject ; elg:readOnSpace ex:space ;
                elg:valueReading elg:EveryValue ;
                elg:evidenceStep [ a elg:EvidenceStep ; elg:stepIndex 0 ; elg:stepProperty ex:score ; elg:stepDirection elg:Forward ] .
            ex:s-high a ex:Subject ; ex:score 12 , 15 .
            ex:s-mixed a ex:Subject ; ex:score 12 , 4 .
        """, format="turtle")
        rows = decisions(sparql(compile_any_condition(data, EX.c), data))
        self.assertEqual(rows, {"s-high": "Permitted", "s-mixed": "Denied"})


class ProfileTests(unittest.TestCase):
    def test_all_required_over_a_set_read_and_a_negated_condition(self) -> None:
        # AIR32-09
        data = Graph().parse(EXAMPLES / "set-reading-admissions.ttl")
        rows = decisions(sparql(compile_profile(data, ADM["engineering-admission"]), data))
        self.assertEqual(rows, {"ada": "Permitted", "ben": "Denied", "cai": "Undetermined", "dee": "Denied"})


class ShaclTests(unittest.TestCase):
    def test_shacl_agrees_with_sparql_on_both_examples(self) -> None:
        # AIR32-10
        admissions = Graph().parse(EXAMPLES / "set-reading-admissions.ttl")
        trial = Graph().parse(EXAMPLES / "set-reading-trial.ttl")
        applicants = list(admissions.subjects(RDF.type, ADM.Applicant))
        patients = list(trial.subjects(RDF.type, TRIAL.Patient))
        cases = [
            (admissions, compile_any_condition(admissions, ADM["stem-qualification"]), applicants),
            (admissions, compile_any_condition(admissions, ADM["no-medicine"]), applicants),
            (admissions, compile_profile(admissions, ADM["engineering-admission"]), applicants),
            (trial, compile_any_condition(trial, TRIAL["all-permitted"]), patients),
            (trial, compile_any_condition(trial, TRIAL["none-excluded"]), patients),
        ]
        for data, plan, subjects in cases:
            self.assertEqual(shacl(plan, data, subjects), decisions(sparql(plan, data)), str(getattr(plan, "condition", None) or plan.profile))


class RefusalTests(unittest.TestCase):
    def test_swrl_and_owl_refuse_readings_and_negation(self) -> None:
        # AIR32-11
        data = Graph().parse(EXAMPLES / "set-reading-admissions.ttl")
        for plan in (
            compile_any_condition(data, ADM["stem-qualification"]),
            compile_any_condition(data, ADM["no-medicine"]),
            compile_profile(data, ADM["engineering-admission"]),
        ):
            with self.assertRaisesRegex(IRCompileError, "AIR-3.3"):
                compile_rules(plan)
            with self.assertRaisesRegex(IRCompileError, "AIR-3.3"):
                compile_classes(plan)


if __name__ == "__main__":
    unittest.main()
