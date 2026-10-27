# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""
A hierarchical condition walks the relation it names, and a contract whose bindings apply at no
instant answers Undetermined (L9, L14, ADR-A85, ADR-A100).

The generated SPARQL runs on the engine ``MORK_SPARQL_ENGINE`` names: ``check:mork-compilers``
runs it on rdflib and ``check:mork-compilers-conformance`` on Oxigraph, so every test here runs
on both. The plan's own expansion is the parity oracle for each member of the scheme, and the
example file is the fixture, so what the README's table claims is what these tests execute.
"""

from __future__ import annotations

import unittest
from dataclasses import replace
from pathlib import Path
from typing import Dict

from rdflib import Graph, URIRef
from rdflib.collection import Collection
from rdflib.namespace import OWL, RDF, RDFS, SKOS

from . import reasoning
from .eligibility_ir import EvidencePath, IRCompileError, compile_any_condition, compile_concept_condition, compile_profile
from .namespaces import ELG, EXE
from .owl_backend import check, compile_classes, owl_class, within
from .shacl_backend import compile_shapes
from .swrl_backend import compile_rules
from .test_concept_backends import graph, shacl, sparql, with_questions
from .test_hierarchical_conditions import AFTER, EDITIONS, EX, HEADER, ask
from .sparql_backend import render_concept_query
from .test_owl_backend import declarations
from .test_evidence_bindings import EX as OWL_EX

EXAMPLE = Path(__file__).resolve().parents[4] / "ontology/eligibility/examples/hierarchy-relation.ttl"


def example() -> Graph:
    return Graph().parse(EXAMPLE)


def everyone(plan) -> Dict[str, URIRef]:
    return {str(concept): concept for concept, _ in plan.expansion}


KIND, PART, ANY = EX["kind-of-tumour"], EX["part-of-tumour"], EX["any-link-to-tumour"]


class NamedRelationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.data = example()

    def decisions(self, condition: URIRef) -> Dict[str, str]:
        plan = compile_concept_condition(self.data, condition)
        asked = ask(self.data, plan, {"carcinoma": EX["lung-carcinoma"], "margin": EX["tumour-margin"], "tumour": EX.tumour})
        return asked

    def test_a_kind_condition_refuses_the_part_link_the_old_walk_admitted(self) -> None:
        # C9b3c-07
        self.assertEqual(self.decisions(KIND)["carcinoma"], "Permitted")
        self.assertEqual(self.decisions(KIND)["margin"], "Denied")
        self.assertEqual(self.decisions(ANY)["margin"], "Permitted")

    def test_a_part_condition_admits_the_part_link_and_refuses_the_kind_link(self) -> None:
        # C9b3c-08
        self.assertEqual((self.decisions(PART)["margin"], self.decisions(PART)["carcinoma"]), ("Permitted", "Denied"))

    def test_a_condition_naming_no_relation_still_walks_broader(self) -> None:
        # C9b3c-09
        plan = compile_concept_condition(self.data, ANY)
        self.assertEqual(plan.relation, SKOS.broader)
        self.assertEqual(self.decisions(ANY), {"carcinoma": "Permitted", "margin": "Permitted", "tumour": "Permitted"})
        self.assertIn(f"<{SKOS.broader}>*", render_concept_query(plan))

    def test_the_generated_walk_is_a_constant_path_over_the_named_relation(self) -> None:
        # C9b3c-10: the query text carries the named IRI and never the other relation's
        text = render_concept_query(compile_concept_condition(self.data, KIND))
        self.assertIn(f"<{EX['kind-of']}>*", text)
        self.assertNotIn(str(EX["part-of"]), text)
        self.assertNotIn("skos:broader*", text)

    def test_sparql_and_the_expansion_agree_for_every_member_under_each_relation(self) -> None:
        # C9b3c-11
        for condition in (KIND, PART, ANY, EX["licensed-territory"]):
            plan = compile_concept_condition(self.data, condition)
            expected = {str(concept): decision for concept, decision in plan.expansion}
            self.assertEqual(ask(self.data, plan, everyone(plan)), expected, str(condition))

    def test_sparql_and_shacl_agree_for_every_member_under_each_relation(self) -> None:
        # C9b3c-12
        for condition in (KIND, PART, ANY):
            plan = compile_concept_condition(self.data, condition)
            asked = with_questions(self.data, condition, {name: (c,) for name, c in everyone(plan).items()})
            reference = {q: decision for q, (decision, _) in sparql(plan, asked).items()}
            self.assertEqual(shacl(plan, asked), reference, str(condition))

    def test_a_territory_licence_walks_two_part_steps(self) -> None:
        # C9b3c-13
        plan = compile_concept_condition(self.data, EX["licensed-territory"])
        decided = ask(self.data, plan, {"city": EX["city-in-country-a"], "overseas": EX["overseas-region"], "europe": EX.europe})
        self.assertEqual(decided, {"city": "Permitted", "overseas": "Denied", "europe": "Permitted"})

    def test_an_exclusion_is_read_over_the_named_relation(self) -> None:
        # C9b3c-27: L10 and L11 over kind links, the margin being part of the tumour and not a kind of it
        self.data += graph(HEADER + """
            ex:kind-except-carcinoma a elg:Condition ; elg:matchStrategy elg:HierarchicalMatch ;
                elg:wildcardSemantics elg:NoWildcard ; elg:constrainedByContract ex:diagnosis-contract ;
                elg:hierarchyRelation ex:kind-of ; elg:requiredConcept ex:tumour ; elg:excludedConcept ex:carcinoma .
        """)
        plan = compile_concept_condition(self.data, EX["kind-except-carcinoma"])
        decided = ask(self.data, plan, everyone(plan))
        self.assertEqual(decided, {
            str(EX.tumour): "Undetermined", str(EX.carcinoma): "Denied",
            str(EX["lung-carcinoma"]): "Denied", str(EX["tumour-margin"]): "Denied",
        })

    def test_a_relation_with_no_route_to_broader_is_refused_by_the_compiler(self) -> None:
        # C9b3c-14
        self.data.remove((EX["kind-of"], RDFS.subPropertyOf, None))
        with self.assertRaisesRegex(IRCompileError, "neither skos:broader"):
            compile_concept_condition(self.data, KIND)

    def test_two_relations_on_one_condition_are_refused(self) -> None:
        # C9b3c-15, cardinality above one
        self.data.add((KIND, ELG.hierarchyRelation, EX["part-of"]))
        with self.assertRaisesRegex(IRCompileError, "several hierarchy relations"):
            compile_concept_condition(self.data, KIND)


class RelationHasNoLinksTests(unittest.TestCase):
    """L14 reads the named relation. The scheme has part links only, so a kind condition meets a scheme
    with no hierarchy while a condition naming no relation meets one."""

    def setUp(self) -> None:
        self.data = example()
        for narrower, broader in list(self.data.subject_objects(EX["kind-of"])):
            self.data.remove((narrower, EX["kind-of"], broader))
            self.data.remove((narrower, SKOS.broader, broader))

    def test_the_named_relation_having_no_links_degrades_to_l14(self) -> None:
        # C9b3c-16, cardinality at zero links
        plan = compile_concept_condition(self.data, KIND)
        self.assertTrue(plan.no_hierarchy)
        decided = sparql(plan, with_questions(self.data, KIND, {"tumour": (EX.tumour,), "margin": (EX["tumour-margin"],)}))
        self.assertEqual(decided[EX["q-tumour"]][0], "Permitted")
        self.assertEqual(decided[EX["q-margin"]], ("Undetermined", EXE.NoHierarchy))

    def test_another_relation_over_the_same_scheme_still_has_its_hierarchy(self) -> None:
        # C9b3c-17
        self.assertFalse(compile_concept_condition(self.data, PART).no_hierarchy)
        self.assertFalse(compile_concept_condition(self.data, ANY).no_hierarchy)

    def test_a_cycle_is_refused_only_in_the_named_relation(self) -> None:
        # C9b3c-18
        data = example()
        data.add((EX.tumour, EX["part-of"], EX["tumour-margin"]))
        with self.assertRaisesRegex(IRCompileError, "cycle of .*part-of"):
            compile_concept_condition(data, PART)
        self.assertEqual(compile_concept_condition(data, KIND).relation, EX["kind-of"])


class NoApplicableBindingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.data = graph(EDITIONS)
        self.early = replace(AFTER, at=AFTER.at.replace(year=2024))  # before either edition

    def test_no_applicable_binding_compiles_to_a_plan_answering_undetermined(self) -> None:
        # C9b3c-19
        plan = compile_concept_condition(self.data, EX["engineering-benefit"], self.early)
        self.assertTrue(plan.unresolved)
        self.assertIsNone(plan.scheme)
        decided = sparql(plan, with_questions(
            self.data, EX["engineering-benefit"],
            {"data": (EX.data,), "platform": (EX.platform,), "two": (EX.data, EX.platform), "none": ()},
        ))
        self.assertEqual({k: v for k, v in decided.items()}, {
            EX["q-data"]: ("Undetermined", EXE.NoApplicableBinding),
            EX["q-platform"]: ("Undetermined", EXE.NoApplicableBinding),
            EX["q-two"]: ("Undetermined", EXE.NoApplicableBinding),
            EX["q-none"]: ("Undetermined", EXE.NoApplicableBinding),
        })

    def test_the_applicable_instants_still_resolve(self) -> None:
        # C9b3c-20
        self.assertFalse(compile_concept_condition(self.data, EX["engineering-benefit"], AFTER).unresolved)

    def test_shacl_reports_every_candidate_undetermined(self) -> None:
        # C9b3c-21
        plan = compile_concept_condition(self.data, EX["engineering-benefit"], self.early)
        asked = with_questions(self.data, EX["engineering-benefit"], {"data": (EX.data,), "platform": (EX.platform,)})
        self.assertEqual(shacl(plan, asked), {EX["q-data"]: "Undetermined", EX["q-platform"]: "Undetermined"})

    def test_conflicting_bindings_are_still_refused(self) -> None:
        # C9b3c-22: ADR-A85 makes equal-specificity bindings a conflict, not an absence
        self.data += graph(HEADER + """
            ex:binding-rival a voc:SchemeBinding ; voc:forContract ex:grade-contract ; voc:bindsScheme ex:grades-2025 ;
                fnd:hasTemporalScope [ a fnd:TemporalScope ; fnd:validFrom "2026-01-01T00:00:00Z"^^xsd:dateTime ] .
        """)
        with self.assertRaises(IRCompileError):
            compile_concept_condition(self.data, EX["engineering-benefit"], AFTER)

    def test_a_profile_over_an_unresolved_condition_is_undetermined(self) -> None:
        # C9b3c-23
        self.data += graph(HEADER + """
            ex:benefit-profile a elg:AdmissionProfile ; elg:hasCondition ex:engineering-benefit ;
                elg:compositionOperation elg:AllRequired .
        """)
        profile = compile_profile(self.data, EX["benefit-profile"], self.early)
        self.assertTrue(profile.conditions[0].unresolved)

    def test_owl_and_swrl_refuse_an_unresolved_plan_and_a_schemeless_hierarchical_plan(self) -> None:
        # C9b3c-24
        unresolved = compile_concept_condition(self.data, EX["engineering-benefit"], self.early)
        schemeless = replace(compile_concept_condition(self.data, EX["engineering-benefit"], AFTER), scheme=None)
        for plan in (unresolved, schemeless):
            with self.subTest(unresolved=plan.unresolved), self.assertRaisesRegex(IRCompileError, "no resolved scheme"):
                compile_rules(plan)
            with self.subTest(unresolved=plan.unresolved), self.assertRaisesRegex(IRCompileError, "no resolved scheme"):
                compile_classes(replace(plan, evidence=_bound(plan)))

    def test_sparql_and_shacl_still_refuse_a_hand_built_schemeless_plan_not_marked_unresolved(self) -> None:
        # C9b3c-25
        plan = replace(compile_concept_condition(self.data, EX["engineering-benefit"], AFTER), scheme=None)
        self.assertFalse(plan.unresolved)
        for backend in (render_concept_query, compile_shapes):
            with self.subTest(backend=backend.__name__), self.assertRaises(IRCompileError):
                backend(plan)


def _bound(plan):
    """The OWL backend compiles bound conditions only, so a plan built by hand needs an evidence path."""
    return EvidencePath(binding=EX.b, subject_class=EX.Employee, steps=((EX.grade, False),), single_valued=True)


BINDINGS = HEADER + """
    ex:kind-binding a elg:EvidenceBinding ; elg:bindsCondition ex:kind-of-tumour ; elg:subjectClass ex:Patient ;
        elg:singleValued true ;
        elg:evidenceStep [ a elg:EvidenceStep ; elg:stepIndex 0 ; elg:stepProperty ex:diagnosis ; elg:stepDirection elg:Forward ] .
    ex:part-binding a elg:EvidenceBinding ; elg:bindsCondition ex:part-of-tumour ; elg:subjectClass ex:Patient ;
        elg:singleValued true ;
        elg:evidenceStep [ a elg:EvidenceStep ; elg:stepProperty ex:diagnosis ; elg:stepIndex 0 ; elg:stepDirection elg:Forward ] .
    ex:any-binding a elg:EvidenceBinding ; elg:bindsCondition ex:any-link-to-tumour ; elg:subjectClass ex:Patient ;
        elg:singleValued true ;
        elg:evidenceStep [ a elg:EvidenceStep ; elg:stepIndex 0 ; elg:stepProperty ex:diagnosis ; elg:stepDirection elg:Forward ] .
"""
BROADER_WITHIN = {
    "tumour": "https://example.org/lattice/eligibility/tumour-within",
    "carcinoma": "https://example.org/lattice/eligibility/carcinoma-within",
}
PART_WITHIN = "https://example.org/lattice/eligibility/{}-within-part-of"
KIND_WITHIN = "https://example.org/lattice/eligibility/{}-within-kind-of"


def module_of(*conditions: URIRef, disjoint: bool = False):
    data = example()
    data += graph(BINDINGS)
    return compile_classes(*[compile_concept_condition(data, c) for c in conditions], disjoint_siblings=disjoint)


def within_classes(module: Graph) -> set:
    return {str(s) for s in module.subjects(RDF.type, OWL.Class) if isinstance(s, URIRef) and "-within" in str(s)}


class OwlModuleTests(unittest.TestCase):
    def test_a_kind_and_a_part_condition_compile_into_separate_within_classes(self) -> None:
        # C9b3c-OWL-01
        module = module_of(KIND, PART)
        members = ("tumour", "carcinoma", "lung-carcinoma", "tumour-margin")
        self.assertEqual(within_classes(module), {t.format(m) for m in members for t in (KIND_WITHIN, PART_WITHIN)})
        kind, part = (lambda m: URIRef(KIND_WITHIN.format(m))), (lambda m: URIRef(PART_WITHIN.format(m)))
        self.assertIn((kind("carcinoma"), RDFS.subClassOf, kind("tumour")), module)
        self.assertIn((kind("lung-carcinoma"), RDFS.subClassOf, kind("carcinoma")), module)
        self.assertIn((part("tumour-margin"), RDFS.subClassOf, part("tumour")), module)
        self.assertNotIn((kind("tumour-margin"), RDFS.subClassOf, kind("tumour")), module)
        self.assertNotIn((part("carcinoma"), RDFS.subClassOf, part("tumour")), module)
        self.assertNotIn((part("lung-carcinoma"), RDFS.subClassOf, part("carcinoma")), module)

    def test_a_skos_broader_condition_keeps_the_iri_it_always_had(self) -> None:
        # C9b3c-OWL-02
        for concept, iri in BROADER_WITHIN.items():
            self.assertEqual(within(EX[concept]), URIRef(iri))
        module = module_of(ANY)
        self.assertEqual(within_classes(module), {f"https://example.org/lattice/eligibility/{m}-within"
                                                  for m in ("tumour", "carcinoma", "lung-carcinoma", "tumour-margin")})
        self.assertEqual(within(EX.tumour, SKOS.broader), URIRef(BROADER_WITHIN["tumour"]))

    def test_sibling_disjointness_is_computed_per_relation(self) -> None:
        # C9b3c-OWL-03
        module = module_of(KIND, PART, disjoint=True)
        groups = [{str(m) for m in Collection(module, module.value(node, OWL.members))}
                  for node in module.subjects(RDF.type, OWL.AllDisjointClasses)]
        kind_roots = {KIND_WITHIN.format(m) for m in ("tumour", "tumour-margin")}
        part_roots = {PART_WITHIN.format(m) for m in ("tumour", "carcinoma", "lung-carcinoma")}
        self.assertCountEqual(groups, [kind_roots, part_roots])

    def test_one_relation_placing_a_member_differently_in_two_schemes_is_refused(self) -> None:
        # C9b3c-OWL-04
        data = example()
        data += graph(BINDINGS)
        kind = compile_concept_condition(data, KIND)
        edition = replace(kind, hierarchy=tuple((m, (EX.carcinoma,) if m == EX["tumour-margin"] else above) for m, above in kind.hierarchy))
        with self.assertRaisesRegex(IRCompileError, rf"different members above it by {EX['kind-of']}"):
            compile_classes(kind, edition)
        compile_classes(kind, compile_concept_condition(data, PART))  # different relations never conflict

    def test_a_module_with_no_hierarchical_condition_mints_no_within_class(self) -> None:
        # C9b3c-OWL-05
        data = declarations()
        module = compile_classes(compile_any_condition(data, OWL_EX["long-tenure"]))
        self.assertEqual({s for s in module.subjects() if "-within" in str(s)}, set())

    def test_two_relations_with_one_local_name_are_refused(self) -> None:
        # C9b3c-OWL-06
        data = example()
        data += graph(BINDINGS)
        kind = compile_concept_condition(data, KIND)
        other = replace(kind, relation=URIRef("https://example.org/other/kind-of"))
        with self.assertRaisesRegex(IRCompileError, "share the local name"):
            compile_classes(kind, other)


REASONER_CONTEXT = Graph().parse(data="""
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
@prefix ex: <https://example.org/lattice/eligibility/> .
ex:Patient a owl:Class .
ex:diagnosis a owl:ObjectProperty .
""" + "".join(f"""
ex:{name} a owl:Class ; owl:equivalentClass [ a owl:Class ; owl:intersectionOf ( ex:Patient
    [ a owl:Restriction ; owl:onProperty ex:diagnosis ; owl:maxCardinality "1"^^xsd:nonNegativeInteger ]
    [ a owl:Restriction ; owl:onProperty ex:diagnosis ; owl:someValuesFrom [ a owl:Class ; owl:oneOf ( ex:{concept} ) ] ] ) ] .
""" for name, concept in (("MarginPatient", "tumour-margin"), ("CarcinomaPatient", "lung-carcinoma"))), format="turtle")


@unittest.skipUnless(reasoning.available(), "reasoning-testkit jar not built")
class OwlReasonerTests(unittest.TestCase):
    def subsumed(self, patient: str, condition: URIRef) -> bool:
        holds, _ = check(module_of(KIND, PART), "subsumption", EX[patient], owl_class(condition), [REASONER_CONTEXT])
        return holds

    def test_a_part_linked_member_is_not_under_the_kind_relation_class(self) -> None:
        # C9b3c-OWL-07
        self.assertTrue(self.subsumed("MarginPatient", PART))
        self.assertFalse(self.subsumed("MarginPatient", KIND))

    def test_a_kind_linked_member_is_not_under_the_part_relation_class(self) -> None:
        # C9b3c-OWL-08
        self.assertTrue(self.subsumed("CarcinomaPatient", KIND))
        self.assertFalse(self.subsumed("CarcinomaPatient", PART))


if __name__ == "__main__":
    unittest.main()
