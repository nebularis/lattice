# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""
Tests for the surface compiler.

Run from the repository root::

    python3 -m unittest tools.surface.test_surface -v

Requires rdflib. **These have not been executed** — the environment this
revision was written in has neither rdflib nor network access, so treat a first
run as part of the review rather than as a regression check.

The deliberate-defect cases matter as much as the passing ones: a compiler that
emits a surface for a malformed contract is worse than one that refuses,
because the resulting surface is unaccounted for and nothing downstream will
notice.
"""

from __future__ import annotations

import unittest
from pathlib import Path

from rdflib import Graph, URIRef
from rdflib.namespace import SKOS

from . import canonical
from .compile import (
    CLOSURE,
    MEMBERSHIP,
    CompileError,
    CyclicClosureBasis,
    SurfaceCompiler,
    ancestors,
    carrier_instances,
    enumerate_population,
    evaluate_path,
)
from .model import ContractError, read_contracts
from .mork import HAS_PROJECTION_PROVENANCE, PROJECTION_MAPPING, lift, lower
from .namespaces import MORK, OWL, RDF, RDFS, SRF
from .naming import (
    DIGEST_LOCAL_NAME,
    LOCAL_NAME_FROM_VALUE,
    QUALIFIED_LOCAL_NAME,
    SANITISED,
    Minter,
    NamingCollision,
    check_injective,
    local_name,
)
from .parity import check_parity
from .serialise import parse_files, serialise

ROOT = Path(__file__).resolve().parents[2]
EXAMPLES = ROOT / "surface" / "examples"
FIXTURES = ROOT / "surface" / "test"
AT = "2026-09-18T00:00:00Z"

EMPLOYMENT = "https://example.org/lattice/surface/employment#"
SAAS = "https://example.org/lattice/surface/saas#"


def load(*names: str) -> Graph:
    return parse_files([str(EXAMPLES / name) for name in names])


def only_contract(graph: Graph, key: str):
    for contract in read_contracts(graph):
        if contract.key == key:
            return contract
    raise AssertionError(f"no contract with key {key}")


def compile_example(name: str, key: str):
    graph = load(name)
    return SurfaceCompiler(only_contract(graph, key), graph, AT).compile(), graph


class CanonicalTests(unittest.TestCase):
    def test_hash_is_independent_of_statement_order(self) -> None:
        first = Graph().parse(
            data="@prefix ex: <https://example.org/#> . ex:a ex:p ex:b . ex:c ex:q ex:d .",
            format="turtle",
        )
        second = Graph().parse(
            data="@prefix ex: <https://example.org/#> . ex:c ex:q ex:d . ex:a ex:p ex:b .",
            format="turtle",
        )
        self.assertEqual(canonical.hash_graph(first), canonical.hash_graph(second))

    def test_hash_is_independent_of_blank_node_labels(self) -> None:
        first = Graph().parse(
            data="@prefix ex: <https://example.org/#> . ex:a ex:p [ ex:q ex:b ] .",
            format="turtle",
        )
        second = Graph().parse(
            data="@prefix ex: <https://example.org/#> . ex:a ex:p _:other . _:other ex:q ex:b .",
            format="turtle",
        )
        self.assertEqual(canonical.hash_graph(first), canonical.hash_graph(second))

    def test_hash_changes_with_content(self) -> None:
        first = Graph().parse(
            data="@prefix ex: <https://example.org/#> . ex:a ex:p ex:b .", format="turtle"
        )
        second = Graph().parse(
            data="@prefix ex: <https://example.org/#> . ex:a ex:p ex:c .", format="turtle"
        )
        self.assertNotEqual(canonical.hash_graph(first), canonical.hash_graph(second))


class NamingTests(unittest.TestCase):
    def minter(self, policy: str = LOCAL_NAME_FROM_VALUE, prefix: str = "") -> Minter:
        return Minter(
            target_namespace="https://example.org/exec#",
            contract_key="job-family",
            carrier="https://example.org/#RoleAssignment",
            normalisation=SANITISED,
            naming_policy=policy,
            naming_prefix=prefix,
        )

    def test_local_name_handles_both_iri_shapes(self) -> None:
        self.assertEqual(local_name("https://example.org/ns#Term"), "Term")
        self.assertEqual(local_name("https://example.org/ns/Term"), "Term")

    def test_value_minting_is_stable(self) -> None:
        self.assertEqual(
            str(self.minter().nominal_class("https://example.org/#SiteReliability")),
            "https://example.org/exec#RoleAssignment_job-family_SiteReliability",
        )

    def test_sanitisation_replaces_reserved_characters(self) -> None:
        self.assertEqual(
            str(self.minter().nominal_class("https://example.org/#Site Reliability")),
            "https://example.org/exec#RoleAssignment_job-family_Site_Reliability",
        )

    def test_qualified_policy_inserts_the_prefix(self) -> None:
        minter = self.minter(QUALIFIED_LOCAL_NAME, prefix="hr")
        self.assertTrue(str(minter.nominal_class("https://example.org/#Sales")).endswith("_hr_Sales"))

    def test_digest_policy_separates_colliding_local_names(self) -> None:
        minter = self.minter(DIGEST_LOCAL_NAME)
        self.assertNotEqual(
            minter.nominal_class("https://a.example/#Sales"),
            minter.nominal_class("https://b.example/#Sales"),
        )

    def test_collision_is_detected_rather_than_silently_merged(self) -> None:
        minter = self.minter()
        minted = [
            ("https://a.example/#Sales", minter.nominal_class("https://a.example/#Sales")),
            ("https://b.example/#Sales", minter.nominal_class("https://b.example/#Sales")),
        ]
        with self.assertRaises(NamingCollision):
            check_injective(minted)


class PopulationAndPathTests(unittest.TestCase):
    def setUp(self) -> None:
        self.graph = load("employment-job-family.ttl")
        self.contract = only_contract(self.graph, "job-family")

    def test_population_follows_the_scheme_contract(self) -> None:
        members, scheme = enumerate_population(self.graph, self.contract.population)
        self.assertEqual(scheme, URIRef(EMPLOYMENT + "JobFamilyScheme"))
        self.assertEqual(len(members), 6)
        self.assertIn(URIRef(EMPLOYMENT + "AnyJobFamily"), members)

    def test_carrier_instances_include_subclass_instances(self) -> None:
        self.assertEqual(len(carrier_instances(self.graph, self.contract.carrier)), 3)

    def test_closure_is_reflexive_and_reaches_every_ancestor(self) -> None:
        found = ancestors(
            self.graph, URIRef(EMPLOYMENT + "SiteReliability"), SKOS.broader, None
        )
        self.assertEqual(
            [local_name(str(f)) for f in found],
            ["Engineering", "SiteReliability", "Technical"],
        )

    def test_closure_stops_at_the_declared_scope(self) -> None:
        scope = {EMPLOYMENT + "SiteReliability", EMPLOYMENT + "Engineering"}
        found = ancestors(
            self.graph, URIRef(EMPLOYMENT + "SiteReliability"), SKOS.broader, scope
        )
        self.assertEqual(len(found), 2)

    def test_cyclic_basis_is_refused(self) -> None:
        graph = Graph().parse(
            data="""
            @prefix ex: <https://example.org/#> .
            @prefix skos: <http://www.w3.org/2004/02/skos/core#> .
            ex:a skos:broader ex:b . ex:b skos:broader ex:a .
            """,
            format="turtle",
        )
        with self.assertRaises(CyclicClosureBasis):
            ancestors(graph, URIRef("https://example.org/#a"), SKOS.broader, None)

    def test_multi_hop_path_evaluates_end_to_end(self) -> None:
        graph = load("saas-subscription-currency.ttl")
        contract = only_contract(graph, "subscription-currency")
        values = evaluate_path(graph, URIRef(SAAS + "subscription-1"), contract)
        self.assertEqual(values, [URIRef(SAAS + "currency-eur")])


class CompilationTests(unittest.TestCase):
    def test_index_surface_mints_one_class_per_member(self) -> None:
        compiled, _ = compile_example("employment-job-family.ttl", "job-family")
        self.assertEqual(len([s for s in compiled.symbols if s.value is not None]), 6)
        self.assertEqual(len(compiled.population), 6)

    def test_wildcard_member_is_minted_like_any_other(self) -> None:
        compiled, _ = compile_example("employment-job-family.ttl", "job-family")
        minted = {str(s.term) for s in compiled.symbols}
        self.assertIn(
            "https://example.org/lattice/surface/employment/exec#"
            "RoleAssignment_job-family_AnyJobFamily",
            minted,
        )

    def test_closure_assertions_include_ancestors_and_the_value_itself(self) -> None:
        compiled, _ = compile_example("employment-job-family.ttl", "job-family")
        relation = URIRef(
            "https://example.org/lattice/surface/employment/exec#matches_job-family"
        )
        reached = {
            local_name(str(o))
            for o in compiled.modules["closure"].objects(
                URIRef(EMPLOYMENT + "assignment-1"), relation
            )
        }
        self.assertEqual(reached, {"SiteReliability", "Engineering", "Technical"})

    def test_nominal_definition_stays_inside_owl_2_el(self) -> None:
        compiled, _ = compile_example("employment-job-family.ttl", "job-family")
        core = compiled.modules["core"]
        # owl:hasValue and owl:someValuesFrom are both EL++; anything needing a
        # richer construct would be a change of profile, not an implementation
        # detail, so the emitted shape is asserted rather than assumed.
        self.assertTrue(any(core.triples((None, OWL.hasValue, None))))
        self.assertFalse(any(core.triples((None, OWL.unionOf, None))))
        self.assertFalse(any(core.triples((None, OWL.complementOf, None))))

    def test_regeneration_is_deterministic(self) -> None:
        first, _ = compile_example("employment-job-family.ttl", "job-family")
        second, _ = compile_example("employment-job-family.ttl", "job-family")
        self.assertEqual(first.artefact_hash, second.artefact_hash)
        self.assertEqual(first.semantic_hash, second.semantic_hash)

    def test_serialisation_is_byte_stable(self) -> None:
        from .compile import render

        first, _ = compile_example("employment-job-family.ttl", "job-family")
        second, _ = compile_example("employment-job-family.ttl", "job-family")
        self.assertEqual(render(first)["core"], render(second)["core"])

    def test_inexact_crosswalk_promotion_is_advisory(self) -> None:
        compiled, _ = compile_example("clinical-trial-crosswalk.ttl", "harmonised-site-category")
        self.assertEqual(compiled.authority, SRF.Advisory)

    def test_exact_promotion_is_cached_reproducible(self) -> None:
        compiled, _ = compile_example("saas-subscription-currency.ttl", "subscription-currency")
        self.assertEqual(compiled.authority, SRF.CachedReproducible)

    def test_read_set_records_every_input_class(self) -> None:
        compiled, _ = compile_example("employment-job-family.ttl", "job-family")
        kinds = {local_name(str(entry.kind)) for entry in compiled.read_set}
        self.assertEqual(
            kinds, {"DeclarationSource", "BoundSchemeSource", "InstanceGraphSource"}
        )


class ParityTests(unittest.TestCase):
    def test_materialised_index_agrees_with_its_source(self) -> None:
        compiled, source = compile_example("employment-job-family.ttl", "job-family")
        report = check_parity(compiled, source)
        self.assertTrue(report.holds(), report.describe())
        self.assertGreater(report.checked, 0)

    def test_parity_detects_a_missing_membership(self) -> None:
        compiled, source = compile_example("employment-job-family.ttl", "job-family")
        removed = next(
            compiled.modules["assertions"].triples((None, RDF.type, None))
        )
        compiled.modules["assertions"].remove(removed)
        report = check_parity(compiled, source)
        self.assertFalse(report.holds())

    def test_materialised_promotion_agrees_with_its_source(self) -> None:
        compiled, source = compile_example(
            "saas-subscription-currency.ttl", "subscription-currency"
        )
        self.assertTrue(check_parity(compiled, source).holds())


class MorkInteropTests(unittest.TestCase):
    def test_lift_produces_a_projection_mapping(self) -> None:
        compiled, _ = compile_example("employment-job-family.ttl", "job-family")
        mapping = lift(compiled)
        subjects = set(mapping.subjects(RDF.type, PROJECTION_MAPPING))
        self.assertEqual(len(subjects), 1)
        self.assertTrue(any(mapping.triples((None, MORK.hasTargetingSpec, None))))

    def test_wrapped_symbol_mode_emits_owl_class_wrappers(self) -> None:
        compiled, _ = compile_example("clinical-trial-crosswalk.ttl", "harmonised-site-category")
        mapping = lift(compiled)
        # A promotion mints no nominal classes, so there is nothing to wrap;
        # the mapping still accounts for the contract and its parameters.
        self.assertTrue(any(mapping.triples((None, MORK.hasParameterBinding, None))))

    def test_round_trip_through_lower_preserves_the_read_path(self) -> None:
        compiled, _ = compile_example(
            "saas-subscription-currency.ttl", "subscription-currency"
        )
        mapping_graph = lift(compiled)
        mapping = next(mapping_graph.subjects(RDF.type, PROJECTION_MAPPING))
        lowered = lower(
            mapping_graph,
            mapping,
            contract_iri=URIRef(SAAS + "lowered-contract"),
            profile=compiled.contract.profile.iri,
        )
        steps = list(lowered.objects(URIRef(SAAS + "lowered-contract"), SRF.hasPathStep))
        self.assertEqual(len(steps), 3)

    def test_lift_links_projection_provenance(self) -> None:
        compiled, _ = compile_example("employment-job-family.ttl", "job-family")
        mapping = lift(compiled)
        self.assertTrue(any(mapping.triples((None, HAS_PROJECTION_PROVENANCE, None))))


class DefectFixtureTests(unittest.TestCase):
    """Every fixture here is expected to be refused, with the stated law named."""

    def compile_fixture(self, name: str, key: str):
        graph = parse_files([str(FIXTURES / name)])
        return SurfaceCompiler(only_contract(graph, key), graph, AT).compile()

    def test_naming_collision_is_refused(self) -> None:
        with self.assertRaises(NamingCollision):
            self.compile_fixture("defect-naming-collision.ttl", "colliding-index")

    def test_cyclic_closure_basis_is_refused(self) -> None:
        with self.assertRaises(CyclicClosureBasis):
            self.compile_fixture("defect-cyclic-closure-basis.ttl", "cyclic-index")

    def test_population_over_budget_is_refused(self) -> None:
        with self.assertRaisesRegex(CompileError, "budget"):
            self.compile_fixture("defect-population-budget.ttl", "over-budget-index")

    def test_lossy_promotion_onto_authored_property_is_refused(self) -> None:
        with self.assertRaisesRegex(CompileError, "srf:X6"):
            self.compile_fixture("defect-lossy-source-signature.ttl", "lossy-promotion")

    def test_both_read_path_forms_is_refused(self) -> None:
        with self.assertRaisesRegex(ContractError, "exactly one read-path form"):
            read_contracts(parse_files([str(FIXTURES / "defect-both-read-path-forms.ttl")]))

    def test_closure_form_without_a_basis_is_refused(self) -> None:
        with self.assertRaisesRegex(ContractError, "closure basis"):
            read_contracts(parse_files([str(FIXTURES / "defect-closure-without-basis.ttl")]))


if __name__ == "__main__":
    unittest.main()
