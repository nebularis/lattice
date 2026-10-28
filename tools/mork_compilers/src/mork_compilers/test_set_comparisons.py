# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""
Set comparisons (``elg:SetComparison``, elg:L18). The three examples are the fixtures for what the
README's tables claim, and a generated fixture sweeps each comparison over the tested and reference
closures. SPARQL is the reference for the backends and SHACL must agree with it. OWL and SWRL
must refuse. The generated SPARQL runs on the engine ``MORK_SPARQL_ENGINE`` names, so every test
here runs on each engine ``check:mork-compilers`` and ``check:mork-compilers-conformance`` use.
"""

from __future__ import annotations

import unittest
from pathlib import Path
from typing import Dict, Optional, Sequence

from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import RDF

from .eligibility_ir import IRCompileError, SetComparisonPlan, compile_any_condition, compile_profile, compile_set_comparison
from .engines import run_query
from .namespaces import ELG, EXE, MORK
from .owl_backend import compile_classes
from .shacl_backend import compile_shapes
from .sparql_backend import compile_query_template
from .swrl_backend import compile_rules
from .test_set_readings import decisions, shacl, sparql

EXAMPLES = Path(__file__).resolve().parents[4] / "ontology/eligibility/examples"
LIC = Namespace("https://example.org/lattice/eligibility/licensing/")
MED = Namespace("https://example.org/lattice/eligibility/medications/")
RES = Namespace("https://example.org/lattice/eligibility/resolution/")
EX = Namespace("https://example.org/lattice/eligibility/comparison/")

HEADER = """
@prefix elg: <https://www.nebularis.org/neuro-semantic/lattice/eligibility#> .
@prefix fnd: <https://www.nebularis.org/neuro-semantic/lattice/foundation#> .
@prefix voc: <https://www.nebularis.org/neuro-semantic/lattice/vocabulary#> .
@prefix skos: <http://www.w3.org/2004/02/skos/core#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix ex: <https://example.org/lattice/eligibility/comparison/> .
"""

# tested and reference sets of each subject, over the values a, b and c
SUBJECTS = {
    "s-in": (("a",), ("a", "b")),  # every tested value found
    "s-part": (("a", "c"), ("a", "b")),  # one found, one not
    "s-out": (("c",), ("a", "b")),  # none found
    "s-empty": ((), ("a",)),  # nothing tested
    "s-noref": (("a",), ()),  # nothing to look in
}


def fixture(
    comparison: str,
    tested_closed: bool = True,
    reference_closed: bool = True,
    negated: bool = False,
    hierarchical: bool = False,
    unresolved: bool = False,
    links: bool = True,
) -> Graph:
    """One comparison over ``SUBJECTS``. Hierarchical, ``ex:c`` is part of ``ex:b`` and nothing else is
    related, so a tested ``c`` is found among reference values containing ``b``."""
    data = "\n".join(
        f"ex:{name} a ex:Subject"
        + "".join(f" ; ex:tested ex:{v}" for v in tested)
        + "".join(f" ; ex:ref ex:{v}" for v in reference)
        + " ."
        for name, (tested, reference) in SUBJECTS.items()
    )
    contract = (
        """
        ex:scheme a voc:ConceptScheme .
        ex:contract a voc:SchemeContract ; voc:boundScheme ex:scheme .
        ex:part-of rdfs:subPropertyOf skos:broader .
        """
        + "".join(f"ex:{v} a skos:Concept ; skos:inScheme ex:scheme .\n" for v in "ab")
        + "ex:c a skos:Concept ; skos:inScheme ex:scheme"
        + (" ; ex:part-of ex:b ; skos:broader ex:b .\n" if links else " .\n")
    )
    if unresolved:
        contract = contract.replace(
            "ex:contract a voc:SchemeContract ; voc:boundScheme ex:scheme .",
            "ex:contract a voc:SchemeContract .\nex:binding a voc:SchemeBinding ; voc:forContract ex:contract ; voc:bindsScheme ex:scheme ;"
            ' fnd:hasTemporalScope [ fnd:validFrom "2030-01-01T00:00:00Z"^^<http://www.w3.org/2001/XMLSchema#dateTime> ] .',
        )
    return Graph().parse(
        data=HEADER
        + (contract if hierarchical else "")
        + f"""
        ex:comparison a elg:SetComparison ;
            elg:matchStrategy elg:{"HierarchicalMatch" if hierarchical else "ExactMatch"} ;
            elg:wildcardSemantics elg:NoWildcard ;
            {"elg:constrainedByContract ex:contract ; elg:hierarchyRelation ex:part-of ;" if hierarchical else ""}
            elg:comparison elg:{comparison} ;
            {"elg:negated true ;" if negated else ""}
            elg:testedBinding ex:tested-binding ;
            elg:referenceBinding ex:reference-binding .
        ex:tested-binding a elg:EvidenceBinding ; elg:bindsCondition ex:comparison ; elg:subjectClass ex:Subject ;
            {"elg:closedUnder ex:tested-closure ;" if tested_closed else ""}
            elg:evidenceStep [ a elg:EvidenceStep ; elg:stepIndex 0 ; elg:stepProperty ex:tested ; elg:stepDirection elg:Forward ] .
        ex:reference-binding a elg:EvidenceBinding ; elg:bindsCondition ex:comparison ; elg:subjectClass ex:Subject ;
            {"elg:closedUnder ex:reference-closure ;" if reference_closed else ""}
            elg:evidenceStep [ a elg:EvidenceStep ; elg:stepIndex 0 ; elg:stepProperty ex:ref ; elg:stepDirection elg:Forward ] .
        ex:tested-closure a elg:Closure ; elg:licensedBy ex:tested-register .
        ex:reference-closure a elg:Closure ; elg:licensedBy ex:reference-register .
        {data}
        """,
        format="turtle",
    )


def expected(comparison: str, tested: Sequence[str], reference: Sequence[str], tc: bool, rc: bool, found=None) -> str:
    """An oracle written in the test, not read from the reference package: each value, then the reading."""
    found = found or (lambda v: v in reference)
    per_value = ["Permitted" if found(v) else "Denied" if rc else "Undetermined" for v in tested]
    if comparison == "Subset":
        if "Denied" in per_value:
            return "Denied"
        return "Permitted" if tc and all(o == "Permitted" for o in per_value) else "Undetermined"
    if "Permitted" in per_value:
        outcome = "Permitted"
    elif tc and all(o == "Denied" for o in per_value):
        outcome = "Denied"
    else:
        outcome = "Undetermined"
    swap = {"Permitted": "Denied", "Denied": "Permitted", "Undetermined": "Undetermined"}
    return swap[outcome] if comparison == "Disjoint" else outcome


def run(data: Graph, condition: URIRef = EX.comparison):
    return sparql(compile_any_condition(data, condition), data)


def text_of(plan) -> str:
    artefact = compile_query_template(plan)
    return str(artefact.value(next(artefact.subjects(RDF.type, MORK.QueryTemplate)), MORK.queryText))


class ExampleTests(unittest.TestCase):
    """The README's tables, executed."""

    def test_licensing_hierarchical_subset(self) -> None:
        # C9b3a-21: Paris is part of France, part of Europe. Both sets closed.
        data = Graph().parse(EXAMPLES / "set-comparison-licensing.ttl")
        rows = decisions(run(data, LIC["distribution-within-grant"]))
        self.assertEqual(rows, {"lic-1": "Permitted", "lic-2": "Denied", "lic-3": "Denied", "lic-4": "Permitted"})

    def test_licensing_with_the_grant_open_is_never_denied(self) -> None:
        # C9b3a-22: a territory not found is not yet shown inside, so the Denied rows are Undetermined
        data = Graph().parse(EXAMPLES / "set-comparison-licensing.ttl")
        data.remove((LIC["grant-binding"], ELG.closedUnder, None))
        rows = run(data, LIC["distribution-within-grant"])
        self.assertEqual(decisions(rows), {"lic-1": "Permitted", "lic-2": "Undetermined", "lic-3": "Undetermined", "lic-4": "Permitted"})
        self.assertEqual(rows["lic-2"][1], EXE.NoClosureLicence)

    def test_trial_disjoint_over_a_two_step_reference_path(self) -> None:
        # C9b3a-23
        data = Graph().parse(EXAMPLES / "set-comparison-trial.ttl")
        rows = decisions(run(data, MED["no-prohibited-medication"]))
        self.assertEqual(rows, {"pat-1": "Permitted", "pat-2": "Denied", "pat-3": "Permitted"})

    def test_bonds_with_an_open_reference_set(self) -> None:
        # C9b3a-24: the consents are open, so a holder not found leaves the outcome Undetermined
        data = Graph().parse(EXAMPLES / "set-comparison-bonds.ttl")
        self.assertEqual(
            decisions(run(data, RES["all-consented"])),
            {"bond-1": "Permitted", "bond-2": "Undetermined", "bond-3": "Undetermined", "bond-4": "Permitted"},
        )
        self.assertEqual(
            decisions(run(data, RES["some-consented"])),
            {"bond-1": "Permitted", "bond-2": "Permitted", "bond-3": "Undetermined", "bond-4": "Denied"},
        )


class ClosureTableTests(unittest.TestCase):
    def test_each_comparison_over_neither_one_and_both_closures(self) -> None:
        # C9b3a-25: Permitted, Denied and Undetermined rows, against an oracle in the test
        for comparison in ("Subset", "Intersects", "Disjoint"):
            for tc in (False, True):
                for rc in (False, True):
                    rows = decisions(run(fixture(comparison, tc, rc)))
                    for name, (tested, reference) in SUBJECTS.items():
                        self.assertEqual(rows[name], expected(comparison, tested, reference, tc, rc), (comparison, tc, rc, name))

    def test_the_oracle_itself_reads_the_known_rows(self) -> None:
        # C9b3a-26: a few rows written out, so a wrong oracle cannot hide a wrong compiler
        rows = decisions(run(fixture("Subset", True, True)))
        self.assertEqual((rows["s-in"], rows["s-part"], rows["s-empty"]), ("Permitted", "Denied", "Permitted"))
        rows = decisions(run(fixture("Intersects", True, False)))
        self.assertEqual((rows["s-in"], rows["s-out"], rows["s-empty"]), ("Permitted", "Undetermined", "Denied"))
        rows = decisions(run(fixture("Disjoint", False, True)))
        self.assertEqual((rows["s-in"], rows["s-out"]), ("Denied", "Undetermined"))

    def test_an_empty_tested_set_under_each_comparison(self) -> None:
        # C9b3a-27: L15's reading of no value, closed and open
        for comparison, closed, open_ in (
            ("Subset", "Permitted", "Undetermined"),
            ("Intersects", "Denied", "Undetermined"),
            ("Disjoint", "Permitted", "Undetermined"),
        ):
            self.assertEqual(run(fixture(comparison, True, False))["s-empty"], (closed, None), comparison)
            rows = run(fixture(comparison, False, True))
            self.assertEqual(rows["s-empty"], (open_, EXE.MissingCandidate), comparison)

    def test_hierarchical_membership_walks_part_of(self) -> None:
        # C9b3a-28: ex:c is part of ex:b, which s-part's reference set holds
        rows = decisions(run(fixture("Subset", True, True, hierarchical=True)))
        self.assertEqual((rows["s-part"], rows["s-out"], rows["s-in"]), ("Permitted", "Permitted", "Permitted"))
        flat = decisions(run(fixture("Subset", True, True)))
        self.assertEqual((flat["s-part"], flat["s-out"]), ("Denied", "Denied"))

    def test_a_value_the_scheme_cannot_place_is_undetermined_and_a_reference_value_matches_nothing(self) -> None:
        # C9b3a-46: a reference value outside the scheme is no match for a member that walks to it,
        # and a tested value outside the scheme is Undetermined with exe:OutsideScheme (L9), however it is linked
        data = fixture("Subset", True, True, hierarchical=True)
        data.parse(
            data=HEADER + """
            ex:x a skos:Concept . ex:c ex:part-of ex:x ; skos:broader ex:x .
            ex:stranger a skos:Concept ; ex:part-of ex:b ; skos:broader ex:b .
            ex:s-ghost a ex:Subject ; ex:tested ex:c ; ex:ref ex:x .
            ex:s-stranger a ex:Subject ; ex:tested ex:stranger ; ex:ref ex:b .
            """,
            format="turtle",
        )
        rows = decisions(run(data))
        self.assertEqual((rows["s-ghost"], rows["s-stranger"]), ("Denied", "Undetermined"))
        self.assertEqual(sparql(compile_any_condition(data, EX.comparison), data)["s-stranger"], ("Undetermined", EXE.OutsideScheme))
        self.assertEqual(shacl(compile_any_condition(data, EX.comparison), data, [EX["s-ghost"], EX["s-stranger"]]),
                         {"s-ghost": "Denied", "s-stranger": "Undetermined"})

    def test_a_negated_subset_swaps_permitted_and_denied(self) -> None:
        # C9b3a-29
        plain = decisions(run(fixture("Subset", True, True)))
        negated = decisions(run(fixture("Subset", True, True, negated=True)))
        swap = {"Permitted": "Denied", "Denied": "Permitted", "Undetermined": "Undetermined"}
        self.assertEqual(negated, {name: swap[d] for name, d in plain.items()})

    def test_the_undetermined_reason_is_the_missing_closure(self) -> None:
        # C9b3a-30: a value not found in an open reference set
        rows = run(fixture("Subset", True, False))
        self.assertEqual(rows["s-out"], ("Undetermined", EXE.NoClosureLicence))
        self.assertEqual(rows["s-noref"], ("Undetermined", EXE.NoClosureLicence))

    def test_a_decision_names_the_closures_it_relied_on(self) -> None:
        # C9b3a-31: Subset Permitted relies on the tested closure, Denied on the reference closure.
        # Each is its own IRI column, ?closure and ?referenceClosure
        def columns(comparison: str) -> Dict[str, tuple]:
            data = fixture(comparison)
            rows = run_query(data, text_of(compile_any_condition(data, EX.comparison)))
            return {str(r[0]).rsplit("/", 1)[1]: (r.asdict().get("closure"), r.asdict().get("referenceClosure")) for r in rows}

        subset = columns("Subset")
        self.assertEqual(subset["s-in"], (EX["tested-closure"], None))
        self.assertEqual(subset["s-part"], (None, EX["reference-closure"]))
        intersects = columns("Intersects")
        self.assertEqual(intersects["s-in"], (None, None))
        self.assertEqual(intersects["s-out"], (EX["tested-closure"], EX["reference-closure"]))
        self.assertEqual(intersects["s-empty"], (EX["tested-closure"], None))
        self.assertTrue(all(isinstance(v, URIRef) for pair in intersects.values() for v in pair if v is not None))

    def test_over_a_scheme_with_no_hierarchy_only_an_equal_value_is_found(self) -> None:
        # C9b3a-50: L14 for a comparison. No member has a link, so an unfound member is Undetermined
        # with exe:NoHierarchy whatever the closures, an equal value is found, and zero links is the case
        plan = compile_any_condition(fixture("Subset", hierarchical=True, links=False), EX.comparison)
        self.assertTrue(plan.no_hierarchy)
        self.assertFalse(compile_any_condition(fixture("Subset", hierarchical=True), EX.comparison).no_hierarchy)
        for comparison in ("Subset", "Intersects", "Disjoint"):
            for tc in (False, True):
                for rc in (False, True):
                    data = fixture(comparison, tc, rc, hierarchical=True, links=False)
                    rows = run(data)
                    # s-in finds a, s-part finds a but not c, s-out finds nothing, c being a member and not b
                    per_value = {
                        name: ["Permitted" if v in reference else "Undetermined" for v in tested]
                        for name, (tested, reference) in SUBJECTS.items()
                    }
                    for name, outcomes in per_value.items():
                        self.assertEqual(rows[name][0], self.read(comparison, outcomes, tc), (comparison, tc, rc, name))
                    self.assertEqual(rows["s-out"], ("Undetermined", EXE.NoHierarchy), (comparison, tc, rc))

    @staticmethod
    def read(comparison: str, outcomes, tc: bool) -> str:
        if comparison == "Subset":
            return "Permitted" if tc and all(o == "Permitted" for o in outcomes) else "Undetermined"
        outcome = "Permitted" if "Permitted" in outcomes else "Denied" if tc and all(o == "Denied" for o in outcomes) else "Undetermined"
        return {"Permitted": "Denied", "Denied": "Permitted", "Undetermined": "Undetermined"}[outcome] if comparison == "Disjoint" else outcome

    def test_the_same_member_is_denied_once_the_scheme_has_a_link(self) -> None:
        # C9b3a-51: zero links against one link, c not found in the reference set {a, b} when c is unlinked to b
        flat = decisions(run(fixture("Subset", True, True, hierarchical=True, links=False)))
        linked = decisions(run(fixture("Subset", True, True, hierarchical=True)))
        self.assertEqual((flat["s-out"], linked["s-out"]), ("Undetermined", "Permitted"))
        data = fixture("Subset", True, True, hierarchical=True)
        data.parse(data=HEADER + "ex:s-x a ex:Subject ; ex:tested ex:b ; ex:ref ex:a .", format="turtle")
        self.assertEqual(run(data)["s-x"], ("Denied", None))


class ProfileTests(unittest.TestCase):
    def test_a_comparison_in_a_profile(self) -> None:
        # C9b3a-32: AllRequired over both bond comparisons, and the closures the record relied on
        data = Graph().parse(EXAMPLES / "set-comparison-bonds.ttl")
        data.parse(
            data=HEADER + "ex:profile a elg:AdmissionProfile ; elg:compositionOperation elg:AllRequired ;"
            " elg:hasCondition <https://example.org/lattice/eligibility/resolution/all-consented> ,"
            " <https://example.org/lattice/eligibility/resolution/some-consented> .",
            format="turtle",
        )
        plan = compile_profile(data, EX.profile)
        rows = {str(r[0]).rsplit("/", 1)[1]: r for r in run_query(data, text_of(plan))}
        self.assertEqual(
            {name: str(row.decision) for name, row in rows.items()},
            {"bond-1": "Permitted", "bond-2": "Undetermined", "bond-3": "Undetermined", "bond-4": "Denied"},
        )
        self.assertEqual(str(rows["bond-1"].closures), str(RES["register-closure"]))
        self.assertEqual(shacl(plan, data, list(rows and [RES[n] for n in rows])), {n: str(r.decision) for n, r in rows.items()})

    def test_a_profile_lists_both_closures_of_a_comparison(self) -> None:
        # C9b3a-33
        data = Graph().parse(EXAMPLES / "set-comparison-trial.ttl")
        data.parse(
            data=HEADER + "ex:profile a elg:AdmissionProfile ; elg:compositionOperation elg:AllRequired ;"
            " elg:hasCondition <https://example.org/lattice/eligibility/medications/no-prohibited-medication> .",
            format="turtle",
        )
        rows = {str(r[0]).rsplit("/", 1)[1]: r for r in run_query(data, text_of(compile_profile(data, EX.profile)))}
        self.assertEqual(str(rows["pat-1"].closures), f"{MED['logging-closure']} {MED['schedule-closure']}")
        self.assertEqual(str(rows["pat-3"].closures), str(MED["logging-closure"]))


class AgreementTests(unittest.TestCase):
    def test_shacl_agrees_with_sparql(self) -> None:
        # C9b3a-34: the examples and every comparison over every closure combination
        for name, condition in (
            ("set-comparison-licensing", LIC["distribution-within-grant"]),
            ("set-comparison-trial", MED["no-prohibited-medication"]),
            ("set-comparison-bonds", RES["all-consented"]),
            ("set-comparison-bonds", RES["some-consented"]),
        ):
            data = Graph().parse(EXAMPLES / f"{name}.ttl")
            plan = compile_any_condition(data, condition)
            subjects = sorted(data.subjects(RDF.type, plan.tested.subject_class))
            self.assertEqual(shacl(plan, data, subjects), decisions(sparql(plan, data)), str(condition))
        for comparison in ("Subset", "Intersects", "Disjoint"):
            for tc in (False, True):
                for rc in (False, True):
                    data = fixture(comparison, tc, rc, hierarchical=(tc == rc))
                    plan = compile_any_condition(data, EX.comparison)
                    subjects = [EX[name] for name in SUBJECTS]
                    self.assertEqual(shacl(plan, data, subjects), decisions(sparql(plan, data)), (comparison, tc, rc))


class UnresolvedTests(unittest.TestCase):
    def test_a_contract_with_no_applicable_binding_is_undetermined_for_every_subject(self) -> None:
        # C9b3a-35: one binding, valid from 2030, resolved at an earlier instant
        from datetime import datetime, timezone

        from .eligibility_ir import ResolutionContext

        data = fixture("Subset", hierarchical=True, unresolved=True)
        plan = compile_any_condition(data, EX.comparison, ResolutionContext(at=datetime(2026, 1, 1, tzinfo=timezone.utc)))
        self.assertTrue(plan.unresolved)
        rows = sparql(plan, data)
        self.assertEqual(set(rows.values()), {("Undetermined", EXE.NoApplicableBinding)})
        self.assertEqual(len(rows), len(SUBJECTS))
        self.assertEqual(shacl(plan, data, [EX[name] for name in SUBJECTS]), {name: "Undetermined" for name in SUBJECTS})
        later = compile_any_condition(data, EX.comparison, ResolutionContext(at=datetime(2031, 1, 1, tzinfo=timezone.utc)))
        self.assertFalse(later.unresolved)

    def test_owl_and_swrl_refuse_a_comparison_whatever_its_scheme(self) -> None:
        # C9b3a-36
        plan = compile_any_condition(fixture("Subset"), EX.comparison)
        self.assertIsInstance(plan, SetComparisonPlan)
        with self.assertRaisesRegex(IRCompileError, r"OWL 2 DL cannot relate .*ADR-A90"):
            compile_classes(plan)
        with self.assertRaisesRegex(IRCompileError, r"SWRL cannot test absence.*ADR-A90"):
            compile_rules(plan)

    def test_owl_and_swrl_refuse_a_profile_holding_a_comparison(self) -> None:
        # C9b3a-37
        data = Graph().parse(EXAMPLES / "set-comparison-trial.ttl")
        data.parse(
            data=HEADER + "ex:profile a elg:AdmissionProfile ; elg:compositionOperation elg:AllRequired ;"
            " elg:hasCondition <https://example.org/lattice/eligibility/medications/no-prohibited-medication> .",
            format="turtle",
        )
        plan = compile_profile(data, EX.profile)
        with self.assertRaisesRegex(IRCompileError, "set comparison"):
            compile_classes(plan)
        with self.assertRaisesRegex(IRCompileError, "set comparison"):
            compile_rules(plan)


class RefusalTests(unittest.TestCase):
    def refused(self, mutate, message: str) -> None:
        data = fixture("Subset")
        mutate(data)
        with self.assertRaisesRegex(IRCompileError, message):
            compile_set_comparison(data, EX.comparison)

    def test_what_the_shapes_refuse_the_compiler_refuses(self) -> None:
        # C9b3a-38: each shape violation of the model, as a compile error
        c, t, r = EX.comparison, EX["tested-binding"], EX["reference-binding"]
        cases = {
            "no comparison": (lambda d: d.remove((c, ELG.comparison, None)), "0 comparisons"),
            "two comparisons": (lambda d: d.add((c, ELG.comparison, ELG.Disjoint)), "2 comparisons"),
            "no tested binding": (lambda d: d.remove((c, ELG.testedBinding, None)), "0 tested bindings"),
            "no reference binding": (lambda d: d.remove((c, ELG.referenceBinding, None)), "0 reference bindings"),
            "one binding for both": (lambda d: d.set((c, ELG.referenceBinding, t)), "are one binding"),
            "a binding not naming the comparison": (lambda d: d.remove((r, ELG.bindsCondition, None)), "must be bound by exactly"),
            "a stray binding": (lambda d: d.add((EX.stray, ELG.bindsCondition, c)), "must be bound by exactly"),
            "another subject class": (lambda d: d.set((r, ELG.subjectClass, EX.Other)), "different subject classes"),
            "a value reading": (lambda d: d.add((t, ELG.valueReading, ELG.SomeValue)), "value reading or a value space"),
            "a value space": (lambda d: d.add((r, ELG.readOnSpace, EX.space)), "value reading or a value space"),
            "another strategy": (lambda d: d.set((c, ELG.matchStrategy, ELG.SetMembership)), "ExactMatch"),
            "a required concept": (lambda d: d.add((c, ELG.requiredConcept, EX.a)), "required or excluded"),
            "an excluded concept": (lambda d: d.add((c, ELG.excludedConcept, EX.a)), "required or excluded"),
            "a closure that is none": (lambda d: d.set((t, ELG.closedUnder, EX.a)), "NoClosureLicence"),
        }
        for name, (mutate, message) in cases.items():
            with self.subTest(name):
                self.refused(mutate, message)

    def test_a_condition_that_is_not_a_comparison_is_refused(self) -> None:
        # C9b3a-39
        data = fixture("Subset")
        data.remove((EX.comparison, RDF.type, ELG.SetComparison))
        with self.assertRaisesRegex(IRCompileError, "not an elg:SetComparison"):
            compile_set_comparison(data, EX.comparison)


class QueryTextTests(unittest.TestCase):
    def test_the_reference_lookup_starts_from_the_bound_subject_over_a_constant_path(self) -> None:
        # C9b3a-40: STD-033 and no variable predicate
        text = text_of(compile_any_condition(fixture("Subset", hierarchical=True), EX.comparison))
        self.assertIn(f"EXISTS {{ ?question <{EX.ref}> ?reference . ?offered <{EX['part-of']}>* ?reference .", text)
        self.assertNotIn("skos:broader*", text)
        flat = text_of(compile_any_condition(fixture("Subset"), EX.comparison))
        self.assertIn(f"EXISTS {{ ?question <{EX.ref}> ?offered }}", flat)

    def test_every_subject_gets_one_decision_and_the_plan_is_typed(self) -> None:
        # C9b3a-41: ?decision is bound on every row, including a subject that tests nothing
        for comparison in ("Subset", "Intersects", "Disjoint"):
            data = fixture(comparison)
            artefact = compile_query_template(compile_any_condition(data, EX.comparison))
            self.assertIn((None, RDF.type, EXE.SetComparisonPlan), artefact)
            rows = run_query(data, text_of(compile_any_condition(data, EX.comparison)))
            self.assertEqual(len(rows), len(SUBJECTS))
            self.assertTrue(all(row.asdict().get("decision") is not None for row in rows))

    def test_the_shapes_are_typed_as_a_set_comparison_plan(self) -> None:
        # C9b3a-42
        shapes = compile_shapes(compile_any_condition(fixture("Subset"), EX.comparison))
        self.assertIn((None, RDF.type, EXE.SetComparisonPlan), shapes)


class ExecutableTests(unittest.TestCase):
    def test_executable_declares_the_plan_and_no_new_diagnostic(self) -> None:
        # C9b3a-43: the pinned diagnostic set is test_concept_backends', and the plan class is disjoint from the others
        executable = Graph().parse(Path(__file__).resolve().parents[4] / "ontology/mork/spec/Executable.ttl")
        plan = EXE.SetComparisonPlan
        self.assertIn((plan, RDF.type, URIRef("http://www.w3.org/2002/07/owl#Class")), executable)
        self.assertIn((plan, URIRef("http://www.w3.org/2002/07/owl#disjointWith"), EXE.ConceptMatchPlan), executable)


if __name__ == "__main__":
    unittest.main()
