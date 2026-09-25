# SPDX-License-Identifier: MPL-2.0

"""
Design-time OWL classes (ADR-A90), over ``ontology/eligibility/examples/evidence-binding.ttl``.

Compilation, refusals and the single-valued shape run in process (L1). The
subsumption, satisfiability and overlap checks run through the ADR-A83
harness (L4) and skip when its jar is not built.
"""

from __future__ import annotations

import unittest
from pathlib import Path

from pyshacl import validate
from rdflib import Graph, URIRef
from rdflib.compare import isomorphic
from rdflib.namespace import OWL, RDF

from . import reasoning
from .eligibility_ir import IRCompileError, compile_any_condition, compile_profile
from .namespaces import EXE, SH
from .owl_backend import check, compile_classes, owl_class
from .test_evidence_bindings import EX, fixture

ROOT = Path(__file__).resolve().parents[4]
PREFIXES = """
@prefix elg: <https://www.nebularis.org/neuro-semantic/lattice/eligibility#> .
@prefix ex: <https://example.org/lattice/eligibility/employment/> .
"""


def condition(name: str, required: str, excluded: str = "", claimed: bool = True) -> str:
    """A hierarchical job-family condition bound like ex:engineering-family."""
    exclusion = f"elg:excludedConcept ex:{excluded} ;" if excluded else ""
    claim = "elg:singleValued true ;" if claimed else ""
    return f"""
ex:{name} a elg:Condition ; elg:matchStrategy elg:HierarchicalMatch ;
    elg:compatibilityOperation elg:AllRequired ; elg:wildcardSemantics elg:NoWildcard ;
    elg:constrainedByContract ex:job-family-contract ; elg:requiredConcept ex:{required} ; {exclusion} .
ex:{name}-binding a elg:EvidenceBinding ; elg:bindsCondition ex:{name} ; elg:subjectClass ex:Employee ; {claim}
    elg:evidenceStep [ elg:stepIndex 0 ; elg:stepProperty ex:holdsRole ; elg:stepDirection elg:Forward ] ,
                     [ elg:stepIndex 1 ; elg:stepProperty ex:inJobFamily ; elg:stepDirection elg:Forward ] .
"""


EXTRA = PREFIXES + "".join([
    condition("any-engineering", "engineering"),
    condition("platform-only", "platform-engineering"),
    condition("contractor-only", "contractor-engineering"),
    condition("excluded-inclusion", "platform-engineering", excluded="engineering"),
    condition("unclaimed", "engineering", claimed=False),
]) + """
@prefix qnt: <https://www.nebularis.org/neuro-semantic/lattice/quantification#> .
ex:five-years a qnt:Quantity ; qnt:onSpace ex:tenure-space ; qnt:numericValue 5 .
ex:at-least-five a qnt:Bound ; qnt:onSpace ex:tenure-space ; qnt:boundValue ex:five-years ;
    qnt:boundSense qnt:Lower ; qnt:boundClosure qnt:Closed .
ex:five-or-more a qnt:Range ; qnt:onSpace ex:tenure-space ; qnt:lowerBound ex:at-least-five ; qnt:hasBound ex:at-least-five .
ex:long-tenure-set a qnt:RangeSet ; qnt:onSpace ex:tenure-space ; qnt:hasRange ex:five-or-more .
ex:long-tenure a elg:IntervalCondition ; elg:matchStrategy elg:IntervalContainment ;
    elg:compatibilityOperation elg:AllRequired ; elg:wildcardSemantics elg:NoWildcard ; elg:requiredRangeSet ex:long-tenure-set .
ex:long-tenure-binding a elg:EvidenceBinding ; elg:bindsCondition ex:long-tenure ; elg:subjectClass ex:Employee ;
    elg:singleValued true ; elg:readOnSpace ex:tenure-space ;
    elg:evidenceStep [ elg:stepIndex 0 ; elg:stepProperty ex:tenureYears ; elg:stepDirection elg:Forward ] .

ex:revised-benefit a elg:AdmissionProfile ; elg:hasCondition ex:any-engineering , ex:minimum-tenure ;
    elg:matchStrategy elg:HierarchicalMatch ; elg:compatibilityOperation elg:AllRequired ; elg:wildcardSemantics elg:NoWildcard .
"""

# The applied ontology's declarations and Quantification's, without the data.
CONTEXT = [Graph().parse(data="""
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix ex: <https://example.org/lattice/eligibility/employment/> .
ex:Employee a owl:Class .
ex:holdsRole a owl:ObjectProperty .
ex:inJobFamily a owl:ObjectProperty .
ex:tenureYears a owl:DatatypeProperty .
""", format="turtle"), Graph().parse(ROOT / "ontology/quantification/spec/quantification.ttl")]


def declarations() -> Graph:
    return fixture().parse(data=EXTRA, format="turtle")


class OwlCompilationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.data = declarations()

    def test_profile_module_names_its_classes_and_provenance(self) -> None:
        module = compile_classes(compile_profile(self.data, EX["relocation-benefit"]))
        artefact = next(module.subjects(RDF.type, EXE.OwlArtefact))
        self.assertIn((owl_class(EX["relocation-benefit"]), RDF.type, OWL.Class), module)
        self.assertEqual(len(set(module.subjects(EXE.producesArtefact, artefact))), 3)
        self.assertEqual(str(module.value(artefact, EXE.owlProfile)), "http://www.w3.org/ns/owl-profile/DL")

    def test_generation_is_deterministic(self) -> None:
        plan = compile_profile(self.data, EX["relocation-benefit"])
        self.assertTrue(isomorphic(compile_classes(plan), compile_classes(plan)))

    def test_unclaimed_path_is_refused(self) -> None:
        with self.assertRaisesRegex(IRCompileError, "singleValued"):
            compile_classes(compile_any_condition(self.data, EX.unclaimed))

    def test_unbound_condition_is_refused(self) -> None:
        data = Graph().parse(ROOT / "ontology/eligibility/examples/hierarchical-match.ttl")
        with self.assertRaisesRegex(IRCompileError, "bound conditions only"):
            compile_classes(compile_any_condition(data, URIRef("https://example.org/lattice/eligibility/hierarchical-condition")))

    def test_single_valued_shape_reports_a_subject_with_two_values(self) -> None:
        module = compile_classes(compile_any_condition(self.data, EX["engineering-family"]))
        conforms, report, _ = validate(self.data, shacl_graph=module, inference="none")
        focus = set(report.objects(None, SH.focusNode))
        self.assertFalse(conforms)
        self.assertEqual(focus, {EX.gina})


@unittest.skipUnless(reasoning.available(), "reasoning-testkit jar not built")
class OwlCheckTests(unittest.TestCase):
    def setUp(self) -> None:
        self.data = declarations()

    def ask(self, kind: str, checked: str, against: str = None, disjoint: bool = False) -> bool:
        names = [checked] + ([against] if against else [])
        plans = [compile_profile(self.data, EX[n]) if n.endswith("benefit") else compile_any_condition(self.data, EX[n]) for n in names]
        module = compile_classes(*plans, disjoint_siblings=disjoint)
        holds, record = check(module, kind, owl_class(EX[checked]), owl_class(EX[against]) if against else None, CONTEXT)
        self.assertEqual(next(record.objects(None, EXE.checkHolds)).toPython(), holds)
        return holds

    def test_revision_that_admits_a_new_concept_is_not_subsumed(self) -> None:
        self.assertFalse(self.ask("subsumption", "revised-benefit", "relocation-benefit"))
        self.assertTrue(self.ask("subsumption", "relocation-benefit", "revised-benefit"))

    def test_a_narrower_interval_is_subsumed(self) -> None:
        self.assertTrue(self.ask("subsumption", "long-tenure", "minimum-tenure"))
        self.assertFalse(self.ask("subsumption", "minimum-tenure", "long-tenure"))

    def test_exclusion_covering_the_only_inclusion_is_unsatisfiable(self) -> None:
        self.assertTrue(self.ask("satisfiability", "relocation-benefit"))
        self.assertFalse(self.ask("satisfiability", "excluded-inclusion"))

    def test_siblings_overlap_unless_declared_disjoint(self) -> None:
        self.assertTrue(self.ask("overlap", "platform-only", "contractor-only"))
        self.assertFalse(self.ask("overlap", "platform-only", "contractor-only", disjoint=True))
        self.assertTrue(self.ask("overlap", "platform-only", "any-engineering", disjoint=True))


if __name__ == "__main__":
    unittest.main()
