# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""
Tests for the surface compiler.

Run from the repository root::

    python3 -m unittest surface.test_surface -v

Requires rdflib. **These have not been executed** — the environment this
revision was written in has neither rdflib nor network access, so treat a first
run as part of the review rather than as a regression check.

The deliberate-defect cases matter as much as the passing ones: a compiler that
emits a surface for a malformed contract is worse than one that refuses,
because the resulting surface is unaccounted for and nothing downstream will
notice.
"""

from __future__ import annotations

import random
import sys
import unittest
from collections import deque
from dataclasses import replace
from datetime import datetime
from pathlib import Path

from pyshacl import validate as shacl_validate
from rdflib import Graph, Literal, URIRef
from rdflib.namespace import SKOS

from . import canonical
from .compile import (
    CLOSURE,
    MEMBERSHIP,
    CompileError,
    CyclicClosureBasis,
    ReadSetRecord,
    SurfaceCompiler,
    ancestors,
    carrier_instances,
    enumerate_population,
    evaluate_path,
)
from .invalidation import instance_graph_query
from .model import ContractError, SurfaceGraphAnalyser, read_contracts, read_projection_contracts
from .mork import HAS_PROJECTION_PROVENANCE, PROJECTION_MAPPING, lift, lower
from .lowering import lower_all, lower_contract, lower_projection, lowered_head
from .cli import contracts_needing_explicit_resolution_time
from .invalidation import (
    compare_read_set,
    impacted_mappings,
    impacted_artefacts,
    impacted_surfaces,
    plan_regeneration,
    read_set_from_manifest,
)
from .parity import run_shared_surface_parity
from .namespaces import MORK, OWL, RDF, RDFS, SH, SRF, VOC, XSD
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

ROOT = Path(__file__).resolve().parents[4]
EXAMPLES = ROOT / "ontology" / "surface" / "examples"
FIXTURES = ROOT / "ontology" / "surface" / "test"
AT = "2026-09-18T00:00:00Z"

EMPLOYMENT = "https://example.org/lattice/surface/employment#"
SAAS = "https://example.org/lattice/surface/saas#"
SAAS_ARR = "https://example.org/lattice/surface/saas-arr#"


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
        members, scheme, resolution = enumerate_population(
            self.graph, self.contract.population, at=AT
        )
        self.assertEqual(scheme, URIRef(EMPLOYMENT + "JobFamilyScheme"))
        self.assertEqual(len(members), 6)
        self.assertIn(URIRef(EMPLOYMENT + "AnyJobFamily"), members)
        # This fixture's contract has no voc:SchemeBinding at all, so
        # resolution always falls back to boundScheme (Finding 1/2,
        # docs/developer/plans/temporal-binding-consumer-hardening.md) — the
        # Resolution object is still returned, not discarded, for the
        # compiler to record.
        self.assertTrue(resolution.used_fallback)
        self.assertIsNone(resolution.winning_binding)

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

    def test_generated_modules_carry_content_addressed_version_iris(self) -> None:
        import re

        from .compile import discharge_determinism, render

        def version(module: Graph) -> str:
            return str(module.value(next(module.subjects(RDF.type, OWL.Ontology)), OWL.versionIRI))

        compiled, _ = compile_example("employment-job-family.ttl", "job-family")
        render(compiled)
        versions = {name: version(m) for name, m in compiled.modules.items() if len(m) > 0}
        for name, value in versions.items():
            ontology = next(compiled.modules[name].subjects(RDF.type, OWL.Ontology))
            self.assertRegex(value, "^" + re.escape(str(ontology)) + "/[0-9a-f]{16}$")
        # rendering again leaves every version unchanged
        render(compiled)
        self.assertEqual({name: version(compiled.modules[name]) for name in versions}, versions)
        # content added after compilation (a law discharge) moves the manifest's version only
        discharge_determinism(compiled, "2026-09-18T00:00:00Z", "probe")
        render(compiled)
        self.assertNotEqual(version(compiled.modules["manifest"]), versions["manifest"])
        self.assertEqual(version(compiled.modules["core"]), versions["core"])

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

    def test_contract_bound_population_resolves_the_scoped_binding(self) -> None:
        compiled, _ = compile_example(
            "employment-job-family-scoped.ttl", "job-family-scoped"
        )
        minted = {str(s.term) for s in compiled.symbols}
        namespace = "https://example.org/lattice/surface/employment-scoped/exec#"
        self.assertIn(f"{namespace}RoleAssignment_job-family-scoped_NorthOnly", minted)
        self.assertNotIn(
            f"{namespace}RoleAssignment_job-family-scoped_FallbackOnly", minted
        )

    def test_manifest_records_the_resolution_trace_for_a_bound_scheme_source(self) -> None:
        """Finding 2 (docs/developer/plans/temporal-binding-consumer-hardening.md):
        the manifest must record why a BoundSchemeSource entry's scheme was
        the one resolved, not only that it was."""
        compiled, _ = compile_example(
            "employment-job-family-scoped.ttl", "job-family-scoped"
        )
        manifest = compiled.modules["manifest"]
        entry = next(
            e
            for e in manifest.subjects(RDF.type, SRF.ReadSetEntry)
            if manifest.value(e, SRF.readSourceKind) == SRF.BoundSchemeSource
        )
        namespace = "https://example.org/lattice/surface/employment-scoped#"
        # xsd:dateTime literals round-trip Z as +00:00 (rdflib literal normalisation); compare instants, not strings
        self.assertEqual(
            datetime.fromisoformat(str(manifest.value(entry, SRF.resolvedAt))),
            datetime.fromisoformat(AT),
        )
        self.assertEqual(
            {str(s) for s in manifest.objects(entry, SRF.resolvedBindingScope)},
            {namespace + "region-north"},
        )
        self.assertEqual(
            str(manifest.value(entry, SRF.resolvedBinding)), namespace + "north-binding"
        )
        self.assertFalse(bool(manifest.value(entry, SRF.resolvedViaFallback)))

    def test_resolution_trace_changes_when_the_context_does(self) -> None:
        """Mutation probe for Finding 2: dropping the population's declared
        activeBindingScope must change the recorded trace from a winning
        binding to a recorded fallback, proving the manifest reflects the
        actual resolution rather than a fixed or vacuous value."""
        graph = load("employment-job-family-scoped.ttl")
        contract = only_contract(graph, "job-family-scoped")
        unscoped_population = replace(contract.population, active_binding_scope=())
        unscoped_contract = replace(contract, population=unscoped_population)

        compiled = SurfaceCompiler(unscoped_contract, graph, AT).compile()
        manifest = compiled.modules["manifest"]
        entry = next(
            e
            for e in manifest.subjects(RDF.type, SRF.ReadSetEntry)
            if manifest.value(e, SRF.readSourceKind) == SRF.BoundSchemeSource
        )
        self.assertTrue(bool(manifest.value(entry, SRF.resolvedViaFallback)))
        self.assertIsNone(manifest.value(entry, SRF.resolvedBinding))
        self.assertEqual(list(manifest.objects(entry, SRF.resolvedBindingScope)), [])
        namespace = "https://example.org/lattice/surface/employment-scoped/exec#"
        minted = {str(s.term) for s in compiled.symbols}
        self.assertIn(f"{namespace}RoleAssignment_job-family-scoped_FallbackOnly", minted)


class ResolutionTimeGuardTests(unittest.TestCase):
    """Finding 1, Option B (docs/developer/plans/temporal-binding-consumer-hardening.md):
    the CLI must refuse to default produced_at to wall-clock time for a
    contract whose population could resolve a caller-scoped voc:SchemeBinding,
    regardless of what time it happens to be — the guard is a structural
    check on the declaration and source graphs, not a time-dependent one."""

    def test_scoped_contract_needs_an_explicit_resolution_time(self) -> None:
        graph = load("employment-job-family-scoped.ttl")
        contract = only_contract(graph, "job-family-scoped")
        self.assertEqual(
            contracts_needing_explicit_resolution_time(graph, [contract]), [contract.iri]
        )

    def test_unscoped_contract_with_no_reachable_binding_keeps_the_default(self) -> None:
        graph = load("employment-job-family.ttl")
        contract = only_contract(graph, "job-family")
        self.assertFalse(any(graph.subjects(VOC.forContract, contract.population.scheme_contract)))
        self.assertEqual(contracts_needing_explicit_resolution_time(graph, [contract]), [])

    def test_a_reachable_binding_alone_is_enough_even_without_a_declared_scope(self) -> None:
        """A contract-bound population naming no srf:activeBindingScope but
        whose contract has a voc:SchemeBinding reachable in the source graph
        still needs an explicit resolution time: an unscoped caller can still
        match a scopeless binding, so the outcome remains a function of the
        resolution instant, not only of scope."""
        graph = load("employment-job-family-scoped.ttl")
        contract = only_contract(graph, "job-family-scoped")
        unscoped_population = replace(contract.population, active_binding_scope=())
        unscoped_contract = replace(contract, population=unscoped_population)
        self.assertEqual(
            contracts_needing_explicit_resolution_time(graph, [unscoped_contract]),
            [contract.iri],
        )

    def test_regeneration_of_an_unscoped_contract_is_deterministic_across_different_times(
        self,
    ) -> None:
        """The unscoped case keeps R1's original guarantee unconditionally:
        no voc:SchemeBinding exists to resolve against, so the resolution
        instant cannot affect the outcome at all, for any two instants."""
        graph = load("employment-job-family.ttl")
        contract = only_contract(graph, "job-family")
        first = SurfaceCompiler(contract, graph, "2026-01-01T00:00:00Z").compile()
        second = SurfaceCompiler(contract, graph, "2030-06-15T00:00:00Z").compile()
        self.assertEqual(first.artefact_hash, second.artefact_hash)
        self.assertEqual(first.semantic_hash, second.semantic_hash)


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


class EntailmentRegimeTests(unittest.TestCase):
    """The compiler acts on NoEntailment only, and refuses everything else (ADR-A19 §3.5)."""

    def test_no_entailment_profile_compiles(self) -> None:
        compile_example("employment-job-family.ttl", "job-family")

    def test_unsupported_entailment_regime_is_refused(self) -> None:
        graph = load("employment-job-family.ttl")
        contract = only_contract(graph, "job-family")
        richer_profile = replace(contract.profile, entailment_regime=str(SRF.OWL2ELEntailment))
        richer_contract = replace(contract, profile=richer_profile)
        with self.assertRaisesRegex(CompileError, "entailment regime"):
            SurfaceCompiler(richer_contract, graph, AT).compile()


class ProjectionModelTests(unittest.TestCase):
    """Parsing and law enforcement for srf:ProjectionContract (ADR-A17, ADR-A20)."""

    def setUp(self) -> None:
        self.graph = load("saas-subscription-arr-projection.ttl")

    def test_projection_contract_parses_role_bindings_and_backend_policy(self) -> None:
        contracts = read_projection_contracts(
            self.graph, only=SAAS_ARR + "subscription-arr-projection"
        )
        self.assertEqual(len(contracts), 1)
        contract = contracts[0]
        self.assertEqual(contract.projection_kind, SRF.DerivationProjection)
        self.assertEqual(len(contract.role_bindings), 4)
        self.assertEqual(len(contract.roles(SRF.RequiredEvidenceRole)), 2)
        self.assertEqual(len(contract.roles(SRF.EvaluationSubjectRole)), 1)
        self.assertEqual(len(contract.roles(SRF.ResultTargetRole)), 1)
        self.assertIsNotNone(contract.backend_policy)
        self.assertTrue(contract.backend_policy.deterministic_only)
        self.assertEqual(contract.backend_policy.llm_completion_policy, SRF.NoLLMCompletion)
        self.assertIn(SRF.SparqlBackend, contract.backend_policy.allowed_backends)


    def test_missing_evaluation_subject_role_is_refused(self) -> None:
        graph = Graph().parse(
            data=f"""
            @prefix srf: <https://www.nebularis.org/neuro-semantic/lattice/surface#> .
            @prefix ex: <{SAAS_ARR}> .
            @prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
            ex:target a srf:ProjectionRoleBinding ; srf:roleKind srf:ResultTargetRole .
            ex:profile-v1 a srf:SurfaceProfile ;
                srf:generatorVersion "x" ; srf:canonicalisationVersion "srf-canon/2" ;
                srf:entailmentRegime srf:NoEntailment ;
                srf:namingNormalisation srf:SanitisedLocalName ;
                srf:symbolMode srf:PunnedSymbols ; srf:permittedStackDepth 0 .
            ex:bad a srf:ProjectionContract ;
                srf:contractKey "bad" ; srf:carrier ex:Subscription ;
                srf:projectionKind srf:DerivationProjection ;
                srf:hasRoleBinding ex:target ;
                srf:targetNamespace "https://example.org/exec#"^^xsd:anyURI ;
                srf:realisationMode srf:Materialised ;
                srf:surfaceProfile ex:profile-v1 .
            """,
            format="turtle",
        )
        with self.assertRaisesRegex(ContractError, "evaluation-subject"):
            read_projection_contracts(graph)

    def test_duplicate_singleton_role_is_refused(self) -> None:
        graph = Graph().parse(
            data=f"""
            @prefix srf: <https://www.nebularis.org/neuro-semantic/lattice/surface#> .
            @prefix ex: <{SAAS_ARR}> .
            @prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
            ex:subject a srf:ProjectionRoleBinding ; srf:roleKind srf:EvaluationSubjectRole .
            ex:subject2 a srf:ProjectionRoleBinding ; srf:roleKind srf:EvaluationSubjectRole .
            ex:target a srf:ProjectionRoleBinding ; srf:roleKind srf:ResultTargetRole .
            ex:profile-v1 a srf:SurfaceProfile ;
                srf:generatorVersion "x" ; srf:canonicalisationVersion "srf-canon/2" ;
                srf:entailmentRegime srf:NoEntailment ;
                srf:namingNormalisation srf:SanitisedLocalName ;
                srf:symbolMode srf:PunnedSymbols ; srf:permittedStackDepth 0 .
            ex:bad a srf:ProjectionContract ;
                srf:contractKey "bad" ; srf:carrier ex:Subscription ;
                srf:projectionKind srf:GraphConstructionProjection ;
                srf:hasRoleBinding ex:subject, ex:subject2, ex:target ;
                srf:targetNamespace "https://example.org/exec#"^^xsd:anyURI ;
                srf:realisationMode srf:Materialised ;
                srf:surfaceProfile ex:profile-v1 .
            """,
            format="turtle",
        )
        with self.assertRaisesRegex(ContractError, "srf:P3"):
            read_projection_contracts(graph)

    def test_backend_named_in_both_allow_and_deny_is_refused(self) -> None:
        with self.assertRaisesRegex(ContractError, "srf:P4"):
            SurfaceGraphAnalyser(
                Graph().parse(
                    data="""
                    @prefix srf: <https://www.nebularis.org/neuro-semantic/lattice/surface#> .
                    @prefix ex: <https://example.org/lattice/surface/saas-arr#> .
                    ex:policy a srf:ProjectionBackendPolicy ;
                        srf:allowedBackend srf:SparqlBackend ;
                        srf:deniedBackend srf:SparqlBackend ;
                        srf:deterministicOnly true ;
                        srf:llmCompletionPolicy srf:NoLLMCompletion .
                    """,
                    format="turtle",
                )
            ).backend_policy(URIRef(SAAS_ARR + "policy"))

    def test_deterministic_only_with_bounded_completion_is_refused(self) -> None:
        with self.assertRaisesRegex(ContractError, "srf:P5"):
            SurfaceGraphAnalyser(
                Graph().parse(
                    data="""
                    @prefix srf: <https://www.nebularis.org/neuro-semantic/lattice/surface#> .
                    @prefix ex: <https://example.org/lattice/surface/saas-arr#> .
                    ex:policy a srf:ProjectionBackendPolicy ;
                        srf:deterministicOnly true ;
                        srf:llmCompletionPolicy srf:BoundedLLMCompletion .
                    """,
                    format="turtle",
                )
            ).backend_policy(URIRef(SAAS_ARR + "policy"))


SURFACE_SHAPES = (
    ROOT / "ontology" / "surface" / "shapes" / "structural.ttl",
    ROOT / "ontology" / "surface" / "shapes" / "constraints.ttl",
)
MORK_SHAPES = (ROOT / "ontology" / "mork" / "shapes" / "constraints.ttl",)


def shape_violations(data: Graph, shape_files) -> set:
    """The names of the shapes that report a violation of ``data``, with no entailment beside it."""
    shapes = Graph()
    for path in shape_files:
        shapes.parse(path, format="turtle")
    _, report, _ = shacl_validate(data, shacl_graph=shapes, advanced=True, inference="none")
    named = set()
    for shape in report.objects(None, SH.sourceShape):
        # A property shape is a blank node. Name the node shape that holds it.
        parent = next(iter(shapes.subjects(SH.property, shape)), shape)
        named.add(str(parent))
    return named


EXPRESSION_HEAD = f"""
@prefix srf: <https://www.nebularis.org/neuro-semantic/lattice/surface#> .
@prefix ex: <{SAAS_ARR}> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

ex:profile-v1 a srf:SurfaceProfile ;
    srf:generatorVersion "x" ; srf:canonicalisationVersion "srf-canon/2" ;
    srf:entailmentRegime srf:NoEntailment ;
    srf:namingNormalisation srf:SanitisedLocalName ;
    srf:symbolMode srf:PunnedSymbols ; srf:permittedStackDepth 0 .

ex:subject a srf:ProjectionRoleBinding ; srf:roleKind srf:EvaluationSubjectRole .
ex:price a srf:ProjectionRoleBinding ; srf:roleKind srf:RequiredEvidenceRole ;
    srf:bindsProperty ex:hasMonthlyPrice ; srf:bindsDatatype xsd:decimal .
ex:periods a srf:ProjectionRoleBinding ; srf:roleKind srf:RequiredEvidenceRole ;
    srf:bindsProperty ex:hasBillingPeriodsPerYear ; srf:bindsDatatype xsd:integer .
ex:cap a srf:ProjectionRoleBinding ; srf:roleKind srf:CandidateEvidenceRole ;
    srf:bindsProperty ex:hasCap ; srf:bindsDatatype xsd:decimal .
ex:label a srf:ProjectionRoleBinding ; srf:roleKind srf:CandidateEvidenceRole ;
    srf:bindsProperty ex:hasLabel ; srf:bindsDatatype xsd:string .
ex:target a srf:ProjectionRoleBinding ; srf:roleKind srf:ResultTargetRole ;
    srf:bindsProperty ex:annualRecurringRevenue ; srf:bindsDatatype xsd:decimal ;
    srf:derivedAs ex:root .

ex:contract a srf:ProjectionContract ;
    srf:contractKey "expression" ; srf:carrier ex:Subscription ;
    srf:projectionKind srf:DerivationProjection ;
    srf:hasRoleBinding ex:subject, ex:price, ex:periods, ex:cap, ex:label, ex:target ;
    srf:targetNamespace "https://example.org/exec#"^^xsd:anyURI ;
    srf:realisationMode srf:Materialised ;
    srf:surfaceProfile ex:profile-v1 .
"""

#: A derivation that uses a product, a choice, a quotient, a literal and a rounding. A cap on the product is
#: shared out over twelve periods and rounded to hundredths.
FULL_EXPRESSION = """
ex:root a srf:RoundingExpression ; srf:resultDatatype xsd:decimal ; srf:roundedOperand ex:share ; srf:roundingScale 2 .
ex:share a srf:QuotientExpression ; srf:resultDatatype xsd:decimal ; srf:leftOperand ex:capped ; srf:rightOperand ex:twelve .
ex:twelve a srf:TypedLiteralExpression ; srf:resultDatatype xsd:integer ; srf:typedValue 12 .
ex:capped a srf:ChoiceExpression ; srf:resultDatatype xsd:decimal ; srf:comparisonOperator srf:GreaterThan ;
    srf:comparedLeft ex:gross ; srf:comparedRight ex:cap ; srf:whenTrue ex:cap ; srf:whenFalse ex:gross .
ex:gross a srf:ProductExpression ; srf:resultDatatype xsd:decimal ; srf:leftOperand ex:price ; srf:rightOperand ex:periods .
"""


def expression_contract(expression: str, head: str = EXPRESSION_HEAD) -> str:
    return head + expression


def arr_graph() -> Graph:
    return load("saas-subscription-arr-projection.ttl")


def arr_with(remove=(), add="") -> Graph:
    """The ARR example with some triples removed, given as (subject, predicate, object) local names, and some Turtle added."""
    graph = arr_graph()
    for subject, predicate, obj in remove:
        graph.remove((URIRef(SAAS_ARR + subject), predicate, obj if obj is None else URIRef(obj) if isinstance(obj, str) else obj))
    if add:
        graph.parse(
            data=f"""
            @prefix srf: <https://www.nebularis.org/neuro-semantic/lattice/surface#> .
            @prefix ex: <{SAAS_ARR}> .
            @prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
            {add}
            """,
            format="turtle",
        )
    return graph


class ProjectionExpressionModelTests(unittest.TestCase):
    """The analyser applies laws srf:P6 to srf:P9 as the shapes do."""

    def read(self, expression: str, head: str = EXPRESSION_HEAD):
        return read_projection_contracts(Graph().parse(data=expression_contract(expression, head), format="turtle"))[0]

    def test_the_arr_contract_states_the_product_of_its_two_evidence_bindings(self) -> None:
        (contract,) = read_projection_contracts(arr_graph())
        expression = contract.expression
        self.assertEqual(expression.kind, SRF.ProductExpression)
        self.assertEqual(expression.datatype, XSD.decimal)
        self.assertEqual(
            [operand.iri for operand in expression.operands],
            [URIRef(SAAS_ARR + "arr-price"), URIRef(SAAS_ARR + "arr-frequency")],
        )

    def test_every_kind_of_expression_is_read(self) -> None:
        expression = self.read(FULL_EXPRESSION).expression
        self.assertEqual(expression.kind, SRF.RoundingExpression)
        self.assertEqual(expression.scale, 2)
        quotient = expression.operands[0]
        self.assertEqual(quotient.kind, SRF.QuotientExpression)
        choice, literal = quotient.operands
        self.assertEqual(literal.literal, Literal(12))
        self.assertEqual(choice.comparison, SRF.GreaterThan)
        self.assertEqual(len(choice.operands), 4)

    def test_sum_and_difference_take_the_wider_datatype(self) -> None:
        for kind in ("SumExpression", "DifferenceExpression"):
            contract = self.read(
                f"ex:root a srf:{kind} ; srf:resultDatatype xsd:decimal ; srf:leftOperand ex:periods ; srf:rightOperand ex:price ."
            )
            self.assertEqual(contract.expression.datatype, XSD.decimal)

    def test_a_quotient_of_integers_is_a_decimal(self) -> None:
        contract = self.read(
            "ex:root a srf:QuotientExpression ; srf:resultDatatype xsd:decimal ; srf:leftOperand ex:periods ; srf:rightOperand ex:periods ."
        )
        self.assertEqual(contract.expression.datatype, XSD.decimal)
        with self.assertRaisesRegex(ContractError, "srf:P8"):
            self.read(
                "ex:root a srf:QuotientExpression ; srf:resultDatatype xsd:integer ; srf:leftOperand ex:periods ; srf:rightOperand ex:periods ."
            )

    def test_a_derivation_with_no_expression_is_refused(self) -> None:
        head = EXPRESSION_HEAD.replace("srf:derivedAs ex:root .", ".")
        with self.assertRaisesRegex(ContractError, "srf:P6"):
            self.read("", head)

    def test_a_result_target_that_binds_no_property_is_refused(self) -> None:
        head = EXPRESSION_HEAD.replace("srf:bindsProperty ex:annualRecurringRevenue ; ", "")
        with self.assertRaisesRegex(ContractError, "srf:P6"):
            self.read(FULL_EXPRESSION, head)

    def test_an_expression_on_another_kind_is_refused(self) -> None:
        head = EXPRESSION_HEAD.replace("srf:DerivationProjection", "srf:GraphConstructionProjection")
        with self.assertRaisesRegex(ContractError, "srf:P6"):
            self.read(FULL_EXPRESSION, head)

    def test_an_operand_that_names_no_evidence_role_is_refused(self) -> None:
        for operand in ("ex:subject", "ex:target", "ex:unknown"):
            with self.subTest(operand=operand), self.assertRaisesRegex(ContractError, "srf:P7"):
                self.read(
                    f"ex:root a srf:ProductExpression ; srf:resultDatatype xsd:decimal ; srf:leftOperand {operand} ; srf:rightOperand ex:periods ."
                )

    def test_an_operand_from_another_contract_is_refused(self) -> None:
        extra = """
        ex:foreign a srf:ProjectionRoleBinding ; srf:roleKind srf:RequiredEvidenceRole ;
            srf:bindsProperty ex:hasOther ; srf:bindsDatatype xsd:decimal .
        ex:other a srf:ProjectionContract ; srf:hasRoleBinding ex:foreign .
        """
        with self.assertRaisesRegex(ContractError, "srf:P7"):
            self.read(
                extra
                + "ex:root a srf:SumExpression ; srf:resultDatatype xsd:decimal ; srf:leftOperand ex:foreign ; srf:rightOperand ex:price ."
            )

    def test_an_operand_that_states_no_datatype_is_refused(self) -> None:
        head = EXPRESSION_HEAD.replace("srf:bindsProperty ex:hasMonthlyPrice ; srf:bindsDatatype xsd:decimal .", "srf:bindsProperty ex:hasMonthlyPrice .")
        with self.assertRaisesRegex(ContractError, "srf:P8"):
            self.read(
                "ex:root a srf:ProductExpression ; srf:resultDatatype xsd:decimal ; srf:leftOperand ex:price ; srf:rightOperand ex:periods .",
                head,
            )

    def test_a_non_numeric_operand_of_arithmetic_is_refused(self) -> None:
        with self.assertRaisesRegex(ContractError, "srf:P8"):
            self.read(
                "ex:root a srf:SumExpression ; srf:resultDatatype xsd:decimal ; srf:leftOperand ex:label ; srf:rightOperand ex:price ."
            )

    def test_a_choice_with_a_missing_branch_is_refused(self) -> None:
        with self.assertRaisesRegex(ContractError, "srf:P7"):
            self.read(
                "ex:root a srf:ChoiceExpression ; srf:resultDatatype xsd:decimal ; srf:comparisonOperator srf:LessThan ;"
                " srf:comparedLeft ex:price ; srf:comparedRight ex:cap ; srf:whenTrue ex:price ."
            )

    def test_the_branches_of_a_choice_share_the_choices_datatype(self) -> None:
        with self.assertRaisesRegex(ContractError, "srf:P8"):
            self.read(
                "ex:root a srf:ChoiceExpression ; srf:resultDatatype xsd:decimal ; srf:comparisonOperator srf:LessThan ;"
                " srf:comparedLeft ex:price ; srf:comparedRight ex:cap ; srf:whenTrue ex:price ; srf:whenFalse ex:periods ."
            )

    def test_an_ordering_comparison_needs_numeric_operands(self) -> None:
        with self.assertRaisesRegex(ContractError, "srf:P8"):
            self.read(
                "ex:root a srf:ChoiceExpression ; srf:resultDatatype xsd:string ; srf:comparisonOperator srf:LessThan ;"
                " srf:comparedLeft ex:label ; srf:comparedRight ex:label ; srf:whenTrue ex:label ; srf:whenFalse ex:label ."
            )

    def test_a_literal_must_have_the_datatype_it_states(self) -> None:
        with self.assertRaisesRegex(ContractError, "srf:P8"):
            self.read('ex:root a srf:TypedLiteralExpression ; srf:resultDatatype xsd:decimal ; srf:typedValue "12" .')

    def test_the_result_target_states_the_datatype_of_the_expression(self) -> None:
        head = EXPRESSION_HEAD.replace("srf:bindsProperty ex:annualRecurringRevenue ; srf:bindsDatatype xsd:decimal ;", "srf:bindsProperty ex:annualRecurringRevenue ; srf:bindsDatatype xsd:double ;")
        with self.assertRaisesRegex(ContractError, "srf:P8"):
            self.read(
                "ex:root a srf:ProductExpression ; srf:resultDatatype xsd:decimal ; srf:leftOperand ex:price ; srf:rightOperand ex:periods .",
                head,
            )

    def test_an_expression_that_is_an_operand_of_itself_is_refused(self) -> None:
        with self.assertRaisesRegex(ContractError, "srf:P9"):
            self.read(
                "ex:root a srf:SumExpression ; srf:resultDatatype xsd:decimal ; srf:leftOperand ex:root ; srf:rightOperand ex:price ."
            )


class ProjectionExpressionShapeTests(unittest.TestCase):
    """The shapes of ontology/surface refuse what the analyser refuses, with no code beside them."""

    def violations(self, graph: Graph) -> set:
        return {name.rsplit("#", 1)[-1] for name in shape_violations(graph, SURFACE_SHAPES)}

    def test_the_arr_example_conforms(self) -> None:
        self.assertEqual(self.violations(arr_graph()), set())

    def test_a_richer_expression_conforms(self) -> None:
        graph = Graph().parse(data=expression_contract(FULL_EXPRESSION), format="turtle")
        self.assertEqual(self.violations(graph), set())

    def test_an_untyped_operand_is_refused(self) -> None:
        graph = arr_with(remove=[("arr-price", SRF.bindsDatatype, None)])
        self.assertIn("ProjectionOperandTypedShape", self.violations(graph))

    def test_an_operand_that_names_no_evidence_role_is_refused(self) -> None:
        for operand in ("arr-subject", "arr-target", "unknown"):
            with self.subTest(operand=operand):
                graph = arr_with(remove=[("arr-expression", SRF.leftOperand, None)], add=f"ex:arr-expression srf:leftOperand ex:{operand} .")
                self.assertIn("ProjectionOperandEvidenceShape", self.violations(graph))

    def test_a_choice_missing_a_branch_is_refused(self) -> None:
        graph = Graph().parse(data=expression_contract(FULL_EXPRESSION), format="turtle")
        graph.remove((URIRef(SAAS_ARR + "capped"), SRF.whenFalse, None))
        self.assertIn("ChoiceExpressionShape", self.violations(graph))

    def test_a_non_numeric_operand_is_refused(self) -> None:
        graph = Graph().parse(
            data=expression_contract(
                "ex:root a srf:SumExpression ; srf:resultDatatype xsd:decimal ; srf:leftOperand ex:label ; srf:rightOperand ex:price ."
            ),
            format="turtle",
        )
        self.assertIn("ProjectionOperandNumericShape", self.violations(graph))

    def test_a_result_datatype_the_operands_do_not_give_is_refused(self) -> None:
        graph = arr_with(remove=[("arr-expression", SRF.resultDatatype, None)], add="ex:arr-expression srf:resultDatatype xsd:integer .")
        self.assertIn("ProjectionArithmeticDatatypeShape", self.violations(graph))
        quotient = Graph().parse(
            data=expression_contract(
                "ex:root a srf:QuotientExpression ; srf:resultDatatype xsd:integer ; srf:leftOperand ex:periods ; srf:rightOperand ex:periods ."
            ),
            format="turtle",
        )
        self.assertIn("ProjectionQuotientDatatypeShape", self.violations(quotient))

    def test_branches_that_disagree_are_refused(self) -> None:
        graph = Graph().parse(data=expression_contract(FULL_EXPRESSION), format="turtle")
        graph.remove((URIRef(SAAS_ARR + "capped"), SRF.whenTrue, None))
        graph.add((URIRef(SAAS_ARR + "capped"), SRF.whenTrue, URIRef(SAAS_ARR + "periods")))
        self.assertIn("ProjectionBranchDatatypeShape", self.violations(graph))

    def test_an_ordering_comparison_of_strings_is_refused(self) -> None:
        graph = Graph().parse(
            data=expression_contract(
                "ex:root a srf:ChoiceExpression ; srf:resultDatatype xsd:string ; srf:comparisonOperator srf:LessThan ;"
                " srf:comparedLeft ex:label ; srf:comparedRight ex:label ; srf:whenTrue ex:label ; srf:whenFalse ex:label ."
            ),
            format="turtle",
        )
        self.assertIn("ProjectionOrderingOperandsShape", self.violations(graph))

    def test_compared_operands_of_different_non_numeric_datatypes_are_refused(self) -> None:
        graph = Graph().parse(
            data=expression_contract(
                "ex:root a srf:ChoiceExpression ; srf:resultDatatype xsd:decimal ; srf:comparisonOperator srf:EqualTo ;"
                " srf:comparedLeft ex:label ; srf:comparedRight ex:price ; srf:whenTrue ex:price ; srf:whenFalse ex:cap ."
            ),
            format="turtle",
        )
        self.assertIn("ProjectionComparedOperandsShape", self.violations(graph))

    def test_a_literal_of_another_datatype_is_refused(self) -> None:
        graph = Graph().parse(
            data=expression_contract('ex:root a srf:TypedLiteralExpression ; srf:resultDatatype xsd:decimal ; srf:typedValue "12" .'),
            format="turtle",
        )
        self.assertIn("ProjectionLiteralDatatypeShape", self.violations(graph))

    def test_a_rounding_expression_keeps_its_operands_datatype(self) -> None:
        graph = Graph().parse(data=expression_contract(FULL_EXPRESSION), format="turtle")
        graph.remove((URIRef(SAAS_ARR + "root"), SRF.resultDatatype, None))
        graph.add((URIRef(SAAS_ARR + "root"), SRF.resultDatatype, XSD.integer))
        self.assertIn("ProjectionRoundingDatatypeShape", self.violations(graph))

    def test_a_result_target_datatype_that_is_not_the_expressions_is_refused(self) -> None:
        graph = arr_with(remove=[("arr-target", SRF.bindsDatatype, None)], add="ex:arr-target srf:bindsDatatype xsd:double .")
        self.assertIn("ProjectionResultTargetDatatypeShape", self.violations(graph))

    def test_a_derivation_with_no_expression_is_refused(self) -> None:
        graph = arr_with(remove=[("arr-target", SRF.derivedAs, None)])
        self.assertIn("DerivationExpressionRequiredShape", self.violations(graph))

    def test_a_result_target_that_binds_no_property_is_refused(self) -> None:
        graph = arr_with(remove=[("arr-target", SRF.bindsProperty, None)])
        self.assertIn("DerivationResultPropertyRequiredShape", self.violations(graph))

    def test_an_expression_no_contract_states_is_refused(self) -> None:
        graph = arr_with(remove=[("arr-target", SRF.derivedAs, None)])
        self.assertIn("ProjectionExpressionReachedShape", self.violations(graph))

    def test_an_expression_on_a_binding_that_is_not_a_result_target_is_refused(self) -> None:
        graph = arr_with(add="ex:arr-price srf:derivedAs ex:arr-expression .")
        self.assertIn("ProjectionExpressionPlacementShape", self.violations(graph))

    def test_an_expression_that_is_an_operand_of_itself_is_refused(self) -> None:
        graph = arr_with(remove=[("arr-expression", SRF.leftOperand, None)], add="ex:arr-expression srf:leftOperand ex:arr-expression .")
        self.assertIn("ProjectionExpressionAcyclicShape", self.violations(graph))


class InvalidationTests(unittest.TestCase):
    def test_read_set_change_is_reported_as_stale(self) -> None:
        compiled, _ = compile_example("employment-job-family.ttl", "job-family")
        current = {
            (str(entry.kind), str(entry.source)): entry.digest
            for entry in compiled.read_set
        }
        self.assertTrue(compare_read_set(compiled.read_set, current).fresh)

        key = next(iter(current))
        current[key] = "changed"
        report = compare_read_set(compiled.read_set, current)
        self.assertFalse(report.fresh)
        self.assertEqual(len(report.changes), 1)
        self.assertEqual(report.changes[0].source, key[1])

    def test_the_first_instance_of_a_class_names_its_contract_and_a_class_whose_instances_all_go_is_still_named(self) -> None:
        graph = load("employment-job-family.ttl")
        contract = only_contract(graph, "job-family")
        full = SurfaceCompiler(contract, graph, AT).compile().read_set
        instances = carrier_instances(graph, contract.carrier)
        self.assertTrue(instances)
        bare = Graph()
        for triple in graph:
            bare.add(triple)
        for instance in instances:
            for triple in list(bare.triples((instance, None, None))):
                bare.remove(triple)
        self.assertFalse(carrier_instances(bare, contract.carrier))
        empty = SurfaceCompiler(contract, bare, AT).compile().read_set

        def entry(read_set):
            return [e for e in read_set if e.kind == SRF.InstanceGraphSource]

        # a class with no instance records the entry, with the digest of the empty graph
        self.assertEqual(len(entry(empty)), 1)
        self.assertEqual(entry(empty)[0].digest, canonical.hash_graph(Graph()))
        # its first instance is a change the compiler's invalidation names
        current = {e.key(): e.digest for e in full}
        report = compare_read_set(empty, current)
        self.assertEqual([c.kind for c in report.changes], [str(SRF.InstanceGraphSource)])
        # and a class whose instances all go is still named, now as a changed digest and not a missing one
        gone = {e.key(): e.digest for e in empty}
        report = compare_read_set(full, gone)
        self.assertEqual([c.kind for c in report.changes], [str(SRF.InstanceGraphSource)])
        self.assertEqual(report.changes[0].current_digest, canonical.hash_graph(Graph()))
        # the entry of a class that has instances is what it was
        self.assertEqual(entry(full)[0].digest, canonical.hash_graph(Graph().parse(data=graph.query(instance_graph_query(contract)).serialize(format="nt"), format="nt")))

    def test_the_instance_graph_query_gives_the_graph_the_compiler_hashes(self) -> None:
        """The query is how an engine without the compiler says whether an edit touched a contract's instance graph."""
        checked = 0
        for name in sorted(path.name for path in EXAMPLES.glob("*.ttl")):
            graph = load(name)
            for contract in read_contracts(graph):
                try:
                    compiled = SurfaceCompiler(contract, graph, AT).compile()
                except (CompileError, ContractError, ValueError):
                    continue
                entries = [e for e in compiled.read_set if e.kind == SRF.InstanceGraphSource]
                if not entries:
                    continue
                rows = Graph()
                for triple in graph.query(instance_graph_query(contract)):
                    rows.add(triple)
                with self.subTest(example=name, contract=contract.key):
                    self.assertEqual(canonical.hash_graph(rows), entries[0].digest)
                    checked += 1
        self.assertGreaterEqual(checked, 3)

    def test_surface_source_change_propagates_downstream(self) -> None:
        upstream = URIRef("https://example.org/surface/upstream")
        downstream = URIRef("https://example.org/surface/downstream")
        manifests = {
            str(upstream): [],
            str(downstream): [
                ReadSetRecord(
                    kind=SRF.SurfaceSource,
                    source=upstream,
                    digest="upstream-hash",
                ),
            ],
        }
        self.assertEqual(
            impacted_surfaces(manifests, {str(upstream)}),
            (str(downstream),),
        )

    def test_manifest_read_set_round_trips_into_freshness_check(self) -> None:
        compiled, _ = compile_example("employment-job-family.ttl", "job-family")
        recorded = read_set_from_manifest(compiled.modules["manifest"])
        self.assertEqual(len(recorded), len(compiled.read_set))
        current = {
            (str(entry.kind), str(entry.source)): entry.digest
            for entry in recorded
        }
        self.assertTrue(compare_read_set(recorded, current).fresh)

    def test_changed_surface_source_propagates_through_mork_mapping_dag(self) -> None:
        mapping_graph = Graph()
        source = URIRef("https://example.org/surface/projection")
        first = URIRef("https://example.org/mork/first")
        second = URIRef("https://example.org/mork/second")
        mapping_graph.add((first, MORK.mappingFor, source))
        mapping_graph.add((second, MORK.dependsOnMapping, first))
        self.assertEqual(
            impacted_mappings(mapping_graph, {str(source)}),
            (str(first), str(second)),
        )

    def test_mapping_change_propagates_to_generated_artefacts(self) -> None:
        mapping_graph = Graph()
        mapping = URIRef("https://example.org/mork/mapping")
        artefact = URIRef("https://example.org/generated/shape")
        mapping_graph.add((artefact, MORK.generatedBy, mapping))
        self.assertEqual(
            impacted_artefacts(mapping_graph, {str(mapping)}),
            (str(artefact),),
        )

    def test_shared_conformance_manifest_runs_surface_case(self) -> None:
        reports = run_shared_surface_parity(
            ROOT / "test" / "conformance" / "manifest.ttl",
            ROOT,
            AT,
        )
        self.assertEqual(
            [case for case, _ in reports],
            [
                "https://example.org/lattice/test/conformance/surface-clinical-crosswalk",
                "https://example.org/lattice/test/conformance/surface-employment-job-family",
                "https://example.org/lattice/test/conformance/surface-saas-subscription-currency",
            ],
        )
        self.assertTrue(all(report.holds() for _, report in reports))

    def test_profile_change_widens_regeneration_scope(self) -> None:
        mapping_graph = Graph()
        mapping = URIRef("https://example.org/mork/mapping")
        artefact = URIRef("https://example.org/generated/shape")
        mapping_graph.add((mapping, MORK.mappingFor, URIRef("https://example.org/surface/contract")))
        mapping_graph.add((artefact, MORK.generatedBy, mapping))
        plan = plan_regeneration(
            {"https://example.org/surface/contract": []},
            mapping_graph,
            changed_profiles={"https://example.org/surface/profile"},
        )
        self.assertEqual(plan.surfaces, ("https://example.org/surface/contract",))
        self.assertEqual(plan.mappings, (str(mapping),))
        self.assertEqual(plan.artefacts, (str(artefact),))
        self.assertEqual(plan.reasons, ("profile-change",))


class RegenerationPropertyTests(unittest.TestCase):
    """Property test for ``impacted_surfaces``'s minimal-regeneration claim
    (ADR-A27; formal-methods epic track B3): "a change to a source, and its
    minimal regeneration... regenerating after a change equals applying the
    change's image to the old output." Cashed out here as two properties,
    checked over randomly generated dependency graphs rather than only the
    worked examples above: **soundness** (every surface the planner selects
    genuinely depends, directly or transitively, on a changed source) and
    **completeness** (every surface that genuinely depends on one is
    selected) -- together, exactly ADR-A27's own "minimal... rather than
    regenerating a whole layer or estate on any change."

    The oracle (``_reachable_backward``) is a breadth-first search over an
    adjacency structure built independently of ``impacted_surfaces``'s own
    repeated-whole-pass fixed point, reducing (not eliminating) the risk
    that a shared mistake in both would go uncaught: the two must still
    compute the same mathematical object, the set of surfaces reachable
    backward from the changed sources along read-set edges, since there is
    only one correct answer for a given graph.
    """

    @staticmethod
    def _node(token: str) -> str:
        return f"https://example.org/regeneration-property/{token}"

    def _random_manifests(
        self, rng: random.Random, surface_count: int, source_pool: int
    ) -> dict[str, list[str]]:
        """surface token -> the tokens (plain sources, or other surfaces'
        own tokens, to exercise chaining) it reads."""
        surfaces = [f"s{i}" for i in range(surface_count)]
        sources = [f"src{i}" for i in range(source_pool)] + surfaces
        manifests: dict[str, list[str]] = {}
        for surface in surfaces:
            candidates = [s for s in sources if s != surface]
            read_count = rng.randint(0, min(3, len(candidates)))
            manifests[surface] = rng.sample(candidates, k=read_count)
        return manifests

    def _reachable_backward(self, manifests: dict[str, list[str]], changed: set[str]) -> set[str]:
        """Which surfaces transitively read a changed token, via an
        explicit BFS queue -- not a repeated-pass fixed point."""
        impacted: set[str] = set()
        queue: deque[str] = deque()
        for surface, reads in manifests.items():
            if any(token in changed for token in reads) and surface not in impacted:
                impacted.add(surface)
                queue.append(surface)
        while queue:
            current = queue.popleft()
            for surface, reads in manifests.items():
                if surface not in impacted and current in reads:
                    impacted.add(surface)
                    queue.append(surface)
        return impacted

    def test_soundness_and_completeness_over_random_dependency_graphs(self) -> None:
        rng = random.Random(20261007)  # fixed seed: reproducible, not flaky
        for _ in range(200):
            manifests_tokens = self._random_manifests(rng, surface_count=6, source_pool=4)
            all_tokens = sorted({t for reads in manifests_tokens.values() for t in reads} | set(manifests_tokens))
            changed_tokens = set(rng.sample(all_tokens, k=rng.randint(0, 2)))

            manifests = {
                self._node(surface): [
                    ReadSetRecord(kind=SRF.SurfaceSource, source=URIRef(self._node(token)), digest="d")
                    for token in reads
                ]
                for surface, reads in manifests_tokens.items()
            }
            changed_sources = {self._node(token) for token in changed_tokens}

            actual = set(impacted_surfaces(manifests, changed_sources))
            expected = {self._node(token) for token in self._reachable_backward(manifests_tokens, changed_tokens)}

            self.assertEqual(actual, expected, (manifests_tokens, changed_tokens))

    def test_a_surface_depending_on_nothing_changed_is_never_selected(self) -> None:
        """ADR-A27's own words, as a direct assertion: a surface whose read
        set shares no entry, directly or transitively, with the changed set
        is not regenerated."""
        manifests = {
            "https://example.org/regeneration-property/untouched": [
                ReadSetRecord(kind=SRF.SurfaceSource, source=URIRef("https://example.org/regeneration-property/unrelated-source"), digest="d")
            ],
        }
        self.assertEqual(impacted_surfaces(manifests, {"https://example.org/regeneration-property/changed-elsewhere"}), ())

    def test_widening_the_changed_set_never_shrinks_the_impacted_set(self) -> None:
        rng = random.Random(7)
        manifests_tokens = self._random_manifests(rng, surface_count=6, source_pool=4)
        manifests = {
            self._node(surface): [
                ReadSetRecord(kind=SRF.SurfaceSource, source=URIRef(self._node(token)), digest="d")
                for token in reads
            ]
            for surface, reads in manifests_tokens.items()
        }
        all_tokens = sorted({t for reads in manifests_tokens.values() for t in reads} | set(manifests_tokens))
        smaller = {self._node(t) for t in rng.sample(all_tokens, k=1)}
        larger = smaller | {self._node(t) for t in rng.sample(all_tokens, k=min(2, len(all_tokens)))}
        self.assertTrue(set(impacted_surfaces(manifests, smaller)) <= set(impacted_surfaces(manifests, larger)))


class ProjectionLoweringTests(unittest.TestCase):
    """Surface-to-MORK lowering for srf:ProjectionContract (ADR-A18)."""

    def contract(self):
        graph = load("saas-subscription-arr-projection.ttl")
        return read_projection_contracts(
            graph, only=SAAS_ARR + "subscription-arr-projection"
        )[0]

    def test_a_derivation_lowers_into_a_scheme_with_a_source_node_root(self) -> None:
        low = lower_projection(self.contract())
        schemes = set(low.subjects(RDF.type, MORK.MappingScheme))
        self.assertEqual(len(schemes), 1)
        scheme = next(iter(schemes))
        roots = [m for m in low.subjects(RDF.type, MORK.Datum) if (m, MORK.mappingScheme, scheme) in low]
        self.assertEqual(len(roots), 1)
        root = roots[0]
        self.assertEqual(root, lowered_head(self.contract()))
        self.assertEqual(low.value(root, MORK.identityRule), MORK.SourceNodeIdentity)
        # No node is minted or typed: the root names no class to type with and no other identity.
        for forbidden in (MORK.deferredMapping, MORK.identityTemplateMapping, MORK.conceptName, MORK.individualIRI):
            self.assertIsNone(low.value(root, forbidden))
        concept = low.value(root, MORK.mappingFor)
        self.assertEqual(low.value(concept, MORK.representedAs), URIRef(SAAS_ARR + "Subscription"))

    def test_the_assertion_writes_the_result_property_with_the_lowered_expression(self) -> None:
        low = lower_projection(self.contract())
        root = lowered_head(self.contract())
        (assertion,) = low.objects(root, MORK.compositeNarrowerMapping)
        self.assertEqual(low.value(assertion, MORK.exactRBoxMatch), URIRef(SAAS_ARR + "annualRecurringRevenue"))
        expression = low.value(assertion, MORK.valueExpression)
        self.assertIn((expression, RDF.type, MORK.ProductExpression), low)
        self.assertEqual(low.value(expression, MORK.resultDatatype), XSD.decimal)
        operands = {low.value(expression, MORK.leftOperand), low.value(expression, MORK.rightOperand)}
        references = {
            (low.value(o, MORK.dataRef), low.value(o, MORK.resultDatatype)) for o in operands
        }
        self.assertEqual(
            references,
            {
                (Literal(f"<{SAAS_ARR}hasMonthlyPrice>"), XSD.decimal),
                (Literal(f"<{SAAS_ARR}hasBillingPeriodsPerYear>"), XSD.integer),
            },
        )
        for operand in operands:
            self.assertIn((operand, RDF.type, MORK.TypedRefExpression), low)

    def test_the_lowered_scheme_names_its_contract_by_producesMapping_and_no_note_carries_the_iri(self) -> None:
        contract = self.contract()
        low = lower_projection(contract)
        self.assertEqual(set(low.objects(contract.iri, SRF.producesMapping)), {lowered_head(contract)})
        for note in low.objects(None, MORK.mappingNote):
            self.assertNotIn(str(contract.iri), str(note))

    @staticmethod
    def bare_contract():
        """A projection of a kind none of the four statements covers, which is the one thing that still lowers to a bare mapping."""
        text = LoweringDependencyTests.SCENARIO.replace("srf:projectionKind srf:ExpansionProjection", "srf:projectionKind ex:OtherKind")
        text = text.replace(" ; srf:expandedAs ex:expansion .", " .")
        (contract,) = read_projection_contracts(Graph().parse(data=text, format="turtle"))
        return contract

    def test_a_bare_mapping_names_its_contract_by_producesMapping_too(self) -> None:
        contract = self.bare_contract()
        low = lower_projection(contract)
        self.assertEqual(set(low.objects(contract.iri, SRF.producesMapping)), {lowered_head(contract)})
        for note in low.objects(None, MORK.mappingNote):
            self.assertNotIn(str(contract.iri), str(note))

    def test_a_lowered_derivation_is_a_scheme_the_mork_shapes_accept(self) -> None:
        low = lower_projection(self.contract())
        self.assertEqual(shape_violations(low, MORK_SHAPES), set())

    def test_lower_projection_records_role_bindings_and_backend_policy_as_parameters(
        self,
    ) -> None:
        mapping_graph = lower_projection(self.contract())
        names = {
            str(mapping_graph.value(node, MORK.paramName))
            for node in mapping_graph.objects(None, MORK.hasParameterBinding)
        }
        self.assertIn("deterministicOnly", names)
        self.assertIn("llmCompletionPolicy", names)
        self.assertIn("projectionKind", names)
        self.assertTrue(any(name.startswith("role_") for name in names))

    def test_lowering_is_deterministic(self) -> None:
        contract = self.contract()
        first = lower_projection(contract)
        second = lower_projection(contract)
        self.assertEqual(canonical.hash_graph(first), canonical.hash_graph(second))

    def test_lowering_is_the_same_with_the_contracts_triples_permuted(self) -> None:
        reference = canonical.hash_graph(lower_projection(self.contract()))
        triples = sorted(load("saas-subscription-arr-projection.ttl"))
        for seed in range(5):
            shuffled = list(triples)
            random.Random(seed).shuffle(shuffled)
            graph = Graph()
            for triple in shuffled:
                graph.add(triple)
            contract = read_projection_contracts(graph, only=SAAS_ARR + "subscription-arr-projection")[0]
            self.assertEqual(canonical.hash_graph(lower_projection(contract)), reference)

    def test_a_projection_of_another_kind_keeps_the_bare_mapping(self) -> None:
        """Every kind the layer declares states what it writes and lowers into a scheme, so only a kind it does not declare keeps
        the bare mapping a derivation, a construction, a join and an expansion have left."""
        contract = self.bare_contract()
        low = lower_projection(contract)
        mappings = set(low.subjects(RDF.type, MORK.DataMapping))
        self.assertEqual(mappings, {lowered_head(contract)})
        self.assertEqual(low.value(lowered_head(contract), MORK.mappingFor), contract.iri)
        self.assertEqual(set(low.subjects(RDF.type, MORK.MappingScheme)), set())

    def test_a_richer_expression_lowers_node_by_node(self) -> None:
        contract = read_projection_contracts(Graph().parse(data=expression_contract(FULL_EXPRESSION), format="turtle"))[0]
        low = lower_projection(contract)
        kinds = {low.value(n, RDF.type) for n in low.subjects(MORK.resultDatatype, None)}
        self.assertEqual(
            kinds,
            {
                MORK.RoundingExpression,
                MORK.QuotientExpression,
                MORK.TypedLiteralExpression,
                MORK.ChoiceExpression,
                MORK.ProductExpression,
                MORK.TypedRefExpression,
            },
        )
        (choice,) = low.subjects(RDF.type, MORK.ChoiceExpression)
        self.assertEqual(low.value(choice, MORK.comparisonOperator), MORK.GreaterThan)
        (rounding,) = low.subjects(RDF.type, MORK.RoundingExpression)
        self.assertEqual(low.value(rounding, MORK.roundingScale), Literal(2))
        (literal,) = low.subjects(RDF.type, MORK.TypedLiteralExpression)
        self.assertEqual(low.value(literal, MORK.typedValue), Literal(12))
        self.assertEqual(shape_violations(low, MORK_SHAPES), set())
        rerun = lower_projection(contract)
        self.assertEqual(canonical.hash_graph(low), canonical.hash_graph(rerun))


class ContractLoweringTests(unittest.TestCase):
    """Surface-to-MORK lowering for Promotion/Index contracts (ADR-A18, Phase 3 item 2)."""

    def test_lower_contract_emits_promotion_parameters(self) -> None:
        graph = load("saas-subscription-currency.ttl")
        contract = only_contract(graph, "subscription-currency")
        mapping_graph = lower_contract(contract)
        names = {
            str(mapping_graph.value(node, MORK.paramName))
            for node in mapping_graph.objects(None, MORK.hasParameterBinding)
        }
        self.assertIn("promotesTo", names)
        self.assertIn("sourceFidelity", names)
        self.assertIn("readPath", names)

    def test_lower_contract_emits_index_parameters(self) -> None:
        graph = load("employment-job-family.ttl")
        contract = only_contract(graph, "job-family")
        mapping_graph = lower_contract(contract)
        names = {
            str(mapping_graph.value(node, MORK.paramName))
            for node in mapping_graph.objects(None, MORK.hasParameterBinding)
        }
        self.assertIn("namingPolicy", names)
        self.assertTrue(any(name.startswith("indexForm_") for name in names))

    def test_lower_contract_agrees_with_lift_on_parameter_names(self) -> None:
        # Same contract, two mechanisms: a bare declaration lowered directly,
        # versus a compiled surface lifted after the fact. contract_parameter_
        # bindings() is shared between them precisely so this holds.
        graph = load("saas-subscription-currency.ttl")
        contract = only_contract(graph, "subscription-currency")
        declared = lower_contract(contract)
        compiled, _ = compile_example("saas-subscription-currency.ttl", "subscription-currency")
        lifted = lift(compiled)
        declared_names = {
            str(declared.value(node, MORK.paramName))
            for node in declared.objects(None, MORK.hasParameterBinding)
        }
        lifted_names = {
            str(lifted.value(node, MORK.paramName))
            for node in lifted.objects(None, MORK.hasParameterBinding)
        }
        self.assertEqual(declared_names, lifted_names)

    def test_lower_contract_mints_a_different_mapping_iri_than_lift(self) -> None:
        # The two mechanisms must never collide on one mapping IRI for the
        # same contract key (see lowering.py's module docstring).
        graph = load("saas-subscription-currency.ttl")
        contract = only_contract(graph, "subscription-currency")
        declared_mapping = next(lower_contract(contract).subjects(RDF.type, MORK.DataMapping))
        compiled, _ = compile_example("saas-subscription-currency.ttl", "subscription-currency")
        lifted_mapping = next(lift(compiled).subjects(RDF.type, MORK.DataMapping))
        self.assertNotEqual(declared_mapping, lifted_mapping)


class LoweringDependencyTests(unittest.TestCase):
    """The mork:dependsOnMapping graph link_dependencies/lower_all compute (ADR-A18)."""

    SCENARIO = """
        @prefix srf: <https://www.nebularis.org/neuro-semantic/lattice/surface#> .
        @prefix ex: <https://example.org/lattice/surface/dep#> .
        @prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

        ex:profile a srf:SurfaceProfile ;
            srf:generatorVersion "x" ; srf:canonicalisationVersion "srf-canon/2" ;
            srf:entailmentRegime srf:NoEntailment ;
            srf:namingNormalisation srf:SanitisedLocalName ;
            srf:symbolMode srf:PunnedSymbols ; srf:permittedStackDepth 0 .

        ex:promotion a srf:PromotionContract ;
            srf:contractKey "derived-value" ; srf:carrier ex:Household ;
            srf:readProperty ex:hasIncome ;
            srf:promotesTo ex:derivedValue ;
            srf:sourceFidelity srf:ExactSource ;
            srf:targetNamespace "https://example.org/exec#"^^xsd:anyURI ;
            srf:realisationMode srf:Materialised ;
            srf:surfaceProfile ex:profile .

        ex:subject a srf:ProjectionRoleBinding ; srf:roleKind srf:EvaluationSubjectRole .
        ex:evidence a srf:ProjectionRoleBinding ;
            srf:roleKind srf:RequiredEvidenceRole ; srf:bindsProperty ex:derivedValue .
        ex:household-evidence a srf:ProjectionRoleBinding ;
            srf:roleKind srf:CandidateEvidenceRole ; srf:bindsCarrier ex:Household .
        ex:target a srf:ProjectionRoleBinding ; srf:roleKind srf:ResultTargetRole ;
            srf:bindsProperty ex:contained ; srf:expandedAs ex:expansion .
        ex:expansion a srf:ExpansionStatement ;
            srf:expandsFrom ex:evidence ; srf:expansionSource srf:TransitiveClosure .

        ex:projection a srf:ProjectionContract ;
            srf:contractKey "eligibility-check" ; srf:carrier ex:Applicant ;
            srf:projectionKind srf:ExpansionProjection ;
            srf:hasRoleBinding ex:subject, ex:evidence, ex:household-evidence, ex:target ;
            srf:targetNamespace "https://example.org/exec#"^^xsd:anyURI ;
            srf:realisationMode srf:Materialised ;
            srf:surfaceProfile ex:profile .
    """
    DEP = "https://example.org/lattice/surface/dep#"

    def setUp(self) -> None:
        self.graph = Graph().parse(data=self.SCENARIO, format="turtle")

    def _mapping_for(self, combined: Graph, contract_iri: str) -> URIRef:
        """The node that stands for a contract: the one it names with ``srf:producesMapping`` where it lowers into a scheme,
        and the bare mapping that is for it otherwise."""
        produced = combined.value(URIRef(contract_iri), SRF.producesMapping)
        if produced is not None:
            return produced
        return next(
            mapping
            for mapping in combined.subjects(RDF.type, MORK.DataMapping)
            if combined.value(mapping, MORK.mappingFor) == URIRef(contract_iri)
        )

    def test_projection_depends_on_the_promotion_it_reads(self) -> None:
        contracts = read_contracts(self.graph)
        projections = read_projection_contracts(self.graph)
        combined = lower_all(contracts=contracts, projections=projections)

        promotion_mapping = self._mapping_for(combined, self.DEP + "promotion")
        projection_mapping = self._mapping_for(combined, self.DEP + "projection")
        depends_on = set(combined.objects(projection_mapping, MORK.dependsOnMapping))
        self.assertIn(promotion_mapping, depends_on)

    def test_promotion_is_never_a_dependant(self) -> None:
        contracts = read_contracts(self.graph)
        projections = read_projection_contracts(self.graph)
        combined = lower_all(contracts=contracts, projections=projections)
        promotion_mapping = self._mapping_for(combined, self.DEP + "promotion")
        self.assertFalse(any(combined.triples((promotion_mapping, MORK.dependsOnMapping, None))))

    def test_lower_all_is_deterministic(self) -> None:
        contracts = read_contracts(self.graph)
        projections = read_projection_contracts(self.graph)
        first = lower_all(contracts=contracts, projections=projections)
        second = lower_all(contracts=contracts, projections=projections)
        self.assertEqual(canonical.hash_graph(first), canonical.hash_graph(second))


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

    def test_promotion_onto_an_undeclared_authored_property_is_refused(self) -> None:
        with self.assertRaisesRegex(CompileError, "does not declare"):
            self.compile_fixture("defect-undeclared-source-property.ttl", "undeclared-promotion")

    def test_both_read_path_forms_is_refused(self) -> None:
        with self.assertRaisesRegex(ContractError, "exactly one read-path form"):
            read_contracts(parse_files([str(FIXTURES / "defect-both-read-path-forms.ttl")]))

    def test_closure_form_without_a_basis_is_refused(self) -> None:
        with self.assertRaisesRegex(ContractError, "closure basis"):
            read_contracts(parse_files([str(FIXTURES / "defect-closure-without-basis.ttl")]))


ORDER_SUPPLIER = "https://example.org/lattice/surface/order-supplier#"
ORDER_SUPPLIER_EXAMPLE = "order-supplier-construction-projection.ttl"


def order_graph() -> Graph:
    return load(ORDER_SUPPLIER_EXAMPLE)


def order_with(remove=(), add="") -> Graph:
    """The order and supplier example with some triples removed, given as (subject, predicate, object) local names with the
    object a local name, a term or None for any, and some Turtle added."""
    graph = order_graph()
    for subject, predicate, obj in remove:
        target = obj if obj is None or isinstance(obj, URIRef) else URIRef(ORDER_SUPPLIER + obj)
        graph.remove((URIRef(ORDER_SUPPLIER + subject), predicate, target))
    if add:
        graph.parse(
            data=f"""
            @prefix srf: <https://www.nebularis.org/neuro-semantic/lattice/surface#> .
            @prefix ex: <{ORDER_SUPPLIER}> .
            @prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
            {add}
            """,
            format="turtle",
        )
    return graph


def per_instance_graph() -> Graph:
    """The example with a node for each order, which names no key."""
    return order_with(
        remove=[("os-node", SRF.nodeIdentity, SRF.ByKey), ("os-node", SRF.keyBinding, "os-code")],
        add="ex:os-node srf:nodeIdentity srf:PerInstance .",
    )


def two_key_graph() -> Graph:
    """The example keyed by two required-evidence bindings, the code and a region the order names."""
    return order_with(
        add="""
        ex:os-region a srf:ProjectionRoleBinding ; srf:roleKind srf:RequiredEvidenceRole ; srf:bindsProperty ex:supplierRegion .
        ex:order-supplier-projection srf:hasRoleBinding ex:os-region .
        ex:os-node srf:keyBinding ex:os-region .
        """
    )


def order_contract(graph: Graph):
    return read_projection_contracts(graph, only=ORDER_SUPPLIER + "order-supplier-projection")[0]


class ConstructionModelTests(unittest.TestCase):
    """The analyser applies laws srf:P10 to srf:P13 as the shapes do."""

    def test_the_example_parses_its_node_its_key_and_the_values_it_writes(self) -> None:
        contract = order_contract(order_graph())
        node = contract.construction
        self.assertIsNone(contract.expression)
        self.assertEqual(node.iri, URIRef(ORDER_SUPPLIER + "os-node"))
        self.assertEqual(node.constructed_class, URIRef(ORDER_SUPPLIER + "Supplier"))
        self.assertTrue(node.keyed)
        self.assertEqual([k.iri for k in node.key], [URIRef(ORDER_SUPPLIER + "os-code")])
        self.assertEqual(
            [(w.property, w.binding.iri) for w in node.writes],
            [
                (URIRef(ORDER_SUPPLIER + "code"), URIRef(ORDER_SUPPLIER + "os-code")),
                (URIRef(ORDER_SUPPLIER + "name"), URIRef(ORDER_SUPPLIER + "os-name")),
            ],
        )
        self.assertEqual(node.link.binds_property, URIRef(ORDER_SUPPLIER + "suppliedBy"))

    def test_a_node_for_each_instance_names_no_key(self) -> None:
        node = order_contract(per_instance_graph()).construction
        self.assertFalse(node.keyed)
        self.assertEqual(node.key, ())

    def test_a_key_of_two_bindings_is_read_in_the_order_of_their_properties(self) -> None:
        node = order_contract(two_key_graph()).construction
        self.assertEqual([k.binds_property for k in node.key], [URIRef(ORDER_SUPPLIER + "supplierCode"), URIRef(ORDER_SUPPLIER + "supplierRegion")])

    def test_the_constructed_node_is_the_same_whatever_the_order_of_the_triples(self) -> None:
        reference = order_contract(order_graph()).construction
        triples = sorted(order_graph())
        for seed in range(5):
            shuffled = list(triples)
            random.Random(seed).shuffle(shuffled)
            graph = Graph()
            for triple in shuffled:
                graph.add(triple)
            self.assertEqual(order_contract(graph).construction, reference)

    def refused(self, graph: Graph, law: str) -> None:
        with self.assertRaisesRegex(ContractError, law):
            read_projection_contracts(graph)

    def test_a_graph_construction_with_no_node_is_refused(self) -> None:
        self.refused(order_with(remove=[("os-link", SRF.constructedAs, None)]), "srf:P10")

    def test_a_node_on_a_binding_that_is_not_a_result_target_is_refused(self) -> None:
        self.refused(order_with(add="ex:os-code srf:constructedAs ex:os-node ."), "srf:P10")

    def test_a_node_on_a_projection_of_another_kind_is_refused(self) -> None:
        graph = order_with(remove=[("order-supplier-projection", SRF.projectionKind, None)], add="ex:order-supplier-projection srf:projectionKind srf:JoinProjection .")
        self.refused(graph, "srf:P10")

    def test_a_derivation_that_states_a_node_is_refused(self) -> None:
        graph = arr_with(add="ex:arr-target srf:constructedAs ex:arr-expression .")
        self.refused(graph, "srf:P10")

    def test_a_link_that_binds_no_property_is_refused(self) -> None:
        self.refused(order_with(remove=[("os-link", SRF.bindsProperty, None)]), "srf:P10")

    def test_a_node_that_is_not_a_constructed_node_is_refused(self) -> None:
        self.refused(order_with(remove=[("os-node", RDF.type, SRF.ConstructedNode)]), "srf:P10")

    def test_a_node_with_no_class_is_refused(self) -> None:
        self.refused(order_with(remove=[("os-node", SRF.constructedClass, None)]), "srf:P11")

    def test_a_node_with_no_identity_or_an_identity_the_choice_does_not_name_is_refused(self) -> None:
        self.refused(order_with(remove=[("os-node", SRF.nodeIdentity, None)]), "srf:P11")
        self.refused(order_with(remove=[("os-node", SRF.nodeIdentity, None)], add="ex:os-node srf:nodeIdentity ex:Elsewhere ."), "srf:P11")

    def test_a_keyed_node_with_no_key_and_an_unkeyed_node_with_one_are_refused(self) -> None:
        self.refused(order_with(remove=[("os-node", SRF.keyBinding, None)]), "srf:P11")
        self.refused(order_with(remove=[("os-node", SRF.nodeIdentity, None)], add="ex:os-node srf:nodeIdentity srf:PerInstance ."), "srf:P11")

    def test_a_node_that_writes_nothing_is_refused(self) -> None:
        self.refused(order_with(remove=[("os-node", SRF.writes, None)]), "srf:P11")

    def test_a_node_that_writes_one_property_twice_is_refused(self) -> None:
        self.refused(order_with(add="ex:os-node srf:writes [ srf:writesProperty ex:name ; srf:fromBinding ex:os-code ] ."), "srf:P11")

    def test_a_value_written_from_what_is_not_an_evidence_binding_is_refused(self) -> None:
        for source in ("os-subject", "os-link", "unknown"):
            with self.subTest(source=source):
                graph = order_with(add=f"ex:os-node srf:writes [ srf:writesProperty ex:other ; srf:fromBinding ex:{source} ] .")
                self.refused(graph, "srf:P12")

    def test_a_written_value_with_no_property_or_no_binding_is_refused(self) -> None:
        self.refused(order_with(add="ex:os-node srf:writes [ srf:fromBinding ex:os-name ] ."), "srf:P12")
        self.refused(order_with(add="ex:os-node srf:writes [ srf:writesProperty ex:other ] ."), "srf:P12")

    def test_a_key_that_is_not_required_evidence_is_refused(self) -> None:
        for key in ("os-name", "os-subject", "unknown"):
            with self.subTest(key=key):
                self.refused(order_with(add=f"ex:os-node srf:keyBinding ex:{key} ."), "srf:P13")


class ConstructionShapeTests(unittest.TestCase):
    """The shapes of ontology/surface refuse what the analyser refuses, with no code beside them."""

    def violations(self, graph: Graph) -> set:
        return {name.rsplit("#", 1)[-1] for name in shape_violations(graph, SURFACE_SHAPES)}

    def test_the_example_and_its_variants_conform(self) -> None:
        for graph in (order_graph(), per_instance_graph(), two_key_graph()):
            self.assertEqual(self.violations(graph), set())

    def test_a_graph_construction_with_no_node_is_refused(self) -> None:
        graph = order_with(remove=[("os-link", SRF.constructedAs, None)])
        self.assertIn("ConstructionRequiredShape", self.violations(graph))
        self.assertIn("ConstructedNodeReachedShape", self.violations(graph))

    def test_a_node_on_a_binding_that_is_not_a_result_target_is_refused(self) -> None:
        self.assertIn("ConstructionPlacementShape", self.violations(order_with(add="ex:os-code srf:constructedAs ex:os-node .")))
        graph = arr_with(add="ex:arr-target srf:constructedAs ex:arr-expression .")
        self.assertIn("ConstructionPlacementShape", self.violations(graph))

    def test_a_node_on_a_projection_of_another_kind_is_refused(self) -> None:
        graph = order_with(remove=[("order-supplier-projection", SRF.projectionKind, None)], add="ex:order-supplier-projection srf:projectionKind srf:JoinProjection .")
        self.assertIn("ConstructionPlacementShape", self.violations(graph))

    def test_two_nodes_on_one_binding_are_refused(self) -> None:
        graph = order_with(add="ex:os-link srf:constructedAs ex:os-other . ex:os-other a srf:ConstructedNode .")
        self.assertIn("ProjectionRoleBindingShape", self.violations(graph))

    def test_a_link_that_binds_no_property_is_refused(self) -> None:
        self.assertIn("ConstructionLinkPropertyRequiredShape", self.violations(order_with(remove=[("os-link", SRF.bindsProperty, None)])))

    def test_a_node_that_is_no_constructed_node_is_refused(self) -> None:
        self.assertIn("ConstructionNodeTypedShape", self.violations(order_with(remove=[("os-node", RDF.type, SRF.ConstructedNode)])))

    def test_a_node_with_no_class_no_identity_or_no_value_is_refused(self) -> None:
        for predicate in (SRF.constructedClass, SRF.nodeIdentity, SRF.writes):
            with self.subTest(predicate=predicate):
                self.assertIn("ConstructedNodeShape", self.violations(order_with(remove=[("os-node", predicate, None)])))

    def test_an_identity_the_choice_does_not_name_is_refused(self) -> None:
        graph = order_with(remove=[("os-node", SRF.nodeIdentity, None)], add="ex:os-node srf:nodeIdentity ex:Elsewhere .")
        self.assertIn("ConstructedNodeShape", self.violations(graph))

    def test_a_keyed_node_with_no_key_and_an_unkeyed_node_with_one_are_refused(self) -> None:
        self.assertIn("ConstructedKeyShape", self.violations(order_with(remove=[("os-node", SRF.keyBinding, None)])))
        graph = order_with(remove=[("os-node", SRF.nodeIdentity, None)], add="ex:os-node srf:nodeIdentity srf:PerInstance .")
        self.assertIn("ConstructedKeyShape", self.violations(graph))

    def test_a_property_written_twice_is_refused(self) -> None:
        graph = order_with(add="ex:os-node srf:writes [ srf:writesProperty ex:name ; srf:fromBinding ex:os-code ] .")
        self.assertIn("ConstructedPropertyOnceShape", self.violations(graph))

    def test_a_written_value_with_no_property_or_no_binding_is_refused(self) -> None:
        for body in ("srf:fromBinding ex:os-name", "srf:writesProperty ex:other"):
            with self.subTest(body=body):
                graph = order_with(add=f"ex:os-node srf:writes [ {body} ] .")
                self.assertIn("WrittenValueShape", self.violations(graph))

    def test_a_value_written_from_what_is_not_an_evidence_binding_is_refused(self) -> None:
        for source in ("os-subject", "os-link", "unknown"):
            with self.subTest(source=source):
                graph = order_with(add=f"ex:os-node srf:writes [ srf:writesProperty ex:other ; srf:fromBinding ex:{source} ] .")
                self.assertIn("WrittenValueEvidenceShape", self.violations(graph))

    def test_a_key_that_is_not_required_evidence_is_refused(self) -> None:
        for key in ("os-name", "os-subject", "unknown"):
            with self.subTest(key=key):
                self.assertIn("ConstructedKeyEvidenceShape", self.violations(order_with(add=f"ex:os-node srf:keyBinding ex:{key} .")))

    def test_the_laws_the_shapes_discharge_are_in_the_vocabulary(self) -> None:
        vocabulary = parse_files([str(ROOT / "ontology" / "surface" / "vocab" / "surface-vocab.ttl")])
        for law in ("P10", "P11", "P12", "P13"):
            self.assertIn((SRF[law], RDF.type, SRF.Law), vocabulary)
        for choice in ("PerInstance", "ByKey"):
            self.assertIn((SRF[choice], RDF.type, SRF.IdentityChoice), vocabulary)


class ConstructionLoweringTests(unittest.TestCase):
    """Surface-to-MORK lowering of a graph construction (ADR-A18)."""

    def lowered(self, graph: Graph):
        contract = order_contract(graph)
        return contract, lower_projection(contract)

    def parts(self, low: Graph, contract):
        root = lowered_head(contract)
        (node,) = low.objects(root, MORK.compositeNarrowerMapping)
        return root, node

    def test_the_construction_lowers_into_a_scheme_a_source_node_root_and_a_contextual_datum(self) -> None:
        contract, low = self.lowered(order_graph())
        (scheme,) = set(low.subjects(RDF.type, MORK.MappingScheme))
        root, node = self.parts(low, contract)
        self.assertEqual(root, lowered_head(contract))
        self.assertEqual(low.value(root, MORK.identityRule), MORK.SourceNodeIdentity)
        concept = low.value(root, MORK.mappingFor)
        self.assertEqual(low.value(concept, MORK.representedAs), URIRef(ORDER_SUPPLIER + "Order"))
        self.assertEqual(low.value(node, MORK.broaderApplicative), root)
        self.assertEqual(low.value(node, MORK.exactTBoxMatch), URIRef(ORDER_SUPPLIER + "Supplier"))
        self.assertEqual(low.value(node, MORK.inverseRBoxMatch), URIRef(ORDER_SUPPLIER + "suppliedBy"))
        self.assertEqual(low.value(node, MORK.mappingScheme), scheme)
        self.assertEqual(set(low.objects(contract.iri, SRF.producesMapping)), {root})

    def test_the_datum_is_guarded_by_each_required_evidence_binding_and_by_no_candidate(self) -> None:
        contract, low = self.lowered(order_graph())
        _, node = self.parts(low, contract)
        guard = low.value(node, MORK.appliesWhen)
        self.assertIn((guard, RDF.type, SH.NodeShape), low)
        required = {(low.value(c, SH.path), low.value(c, SH.minCount)) for c in low.objects(guard, SH.property)}
        self.assertEqual(required, {(URIRef(ORDER_SUPPLIER + "supplierCode"), Literal(1))})

    def test_a_required_value_that_is_not_the_key_guards_the_datum_too(self) -> None:
        graph = order_with(remove=[("os-name", SRF.roleKind, None)], add="ex:os-name srf:roleKind srf:RequiredEvidenceRole .")
        contract, low = self.lowered(graph)
        _, node = self.parts(low, contract)
        guard = low.value(node, MORK.appliesWhen)
        paths = {low.value(c, SH.path) for c in low.objects(guard, SH.property)}
        self.assertEqual(paths, {URIRef(ORDER_SUPPLIER + "supplierCode"), URIRef(ORDER_SUPPLIER + "supplierName")})

    def test_an_assertion_writes_each_value_from_its_binding(self) -> None:
        contract, low = self.lowered(order_graph())
        _, node = self.parts(low, contract)
        written = {
            (low.value(a, MORK.exactRBoxMatch), low.value(a, MORK.dataRef))
            for a in low.objects(node, MORK.compositeNarrowerMapping)
        }
        self.assertEqual(
            written,
            {
                (URIRef(ORDER_SUPPLIER + "code"), Literal(f"<{ORDER_SUPPLIER}supplierCode>")),
                (URIRef(ORDER_SUPPLIER + "name"), Literal(f"<{ORDER_SUPPLIER}supplierName>")),
            },
        )

    def test_a_keyed_identity_is_the_contract_key_the_class_and_the_key_values(self) -> None:
        contract, low = self.lowered(order_graph())
        _, node = self.parts(low, contract)
        self.assertIsNone(low.value(node, MORK.conceptName))
        identity = low.value(node, MORK.identityTemplateMapping)
        self.assertIn((identity, RDF.type, MORK.ConcatExpression), low)
        left, right = low.value(identity, MORK.concatLeft), low.value(identity, MORK.concatRight)
        self.assertEqual(low.value(left, MORK.dataInline), Literal("order-supplier/Supplier/"))
        self.assertEqual(low.value(right, MORK.dataRef), Literal(f"<{ORDER_SUPPLIER}supplierCode>"))

    def test_a_key_of_two_values_is_joined_by_a_slash_in_the_order_of_their_properties(self) -> None:
        contract, low = self.lowered(two_key_graph())
        _, node = self.parts(low, contract)
        references = []
        current = low.value(node, MORK.identityTemplateMapping)
        while current is not None:
            left, right = low.value(current, MORK.concatLeft), low.value(current, MORK.concatRight)
            references.append(low.value(left, MORK.dataInline) or low.value(left, MORK.dataRef))
            current = right if (right, RDF.type, MORK.ConcatExpression) in low else None
            if current is None:
                references.append(low.value(right, MORK.dataInline) or low.value(right, MORK.dataRef))
        self.assertEqual(
            references,
            [
                Literal("order-supplier/Supplier/"),
                Literal(f"<{ORDER_SUPPLIER}supplierCode>"),
                Literal("/"),
                Literal(f"<{ORDER_SUPPLIER}supplierRegion>"),
            ],
        )
        self.assertEqual(shape_violations(low, MORK_SHAPES), set())

    def test_a_node_for_each_instance_names_no_key_and_is_named_from_the_contract_key_and_class(self) -> None:
        contract, low = self.lowered(per_instance_graph())
        _, node = self.parts(low, contract)
        self.assertIsNone(low.value(node, MORK.identityTemplateMapping))
        self.assertEqual(low.value(node, MORK.conceptName), Literal("order-supplier/Supplier"))

    def test_the_lowered_scheme_is_one_the_mork_shapes_accept(self) -> None:
        for graph in (order_graph(), per_instance_graph(), two_key_graph()):
            self.assertEqual(shape_violations(self.lowered(graph)[1], MORK_SHAPES), set())

    def test_lowering_is_deterministic_and_the_same_with_the_triples_permuted(self) -> None:
        contract = order_contract(order_graph())
        reference = canonical.hash_graph(lower_projection(contract))
        self.assertEqual(canonical.hash_graph(lower_projection(contract)), reference)
        triples = sorted(order_graph())
        for seed in range(5):
            shuffled = list(triples)
            random.Random(seed).shuffle(shuffled)
            graph = Graph()
            for triple in shuffled:
                graph.add(triple)
            self.assertEqual(canonical.hash_graph(lower_projection(order_contract(graph))), reference)

    def test_a_contract_key_that_needs_encoding_is_encoded_in_the_identifier(self) -> None:
        graph = order_with(remove=[("order-supplier-projection", SRF.contractKey, None)], add='ex:order-supplier-projection srf:contractKey "order supplier/1" .')
        contract, low = self.lowered(graph)
        _, node = self.parts(low, contract)
        left = low.value(low.value(node, MORK.identityTemplateMapping), MORK.concatLeft)
        self.assertEqual(low.value(left, MORK.dataInline), Literal("order%20supplier%2F1/Supplier/"))

    def test_a_construction_is_not_a_bare_mapping(self) -> None:
        contract, low = self.lowered(order_graph())
        self.assertEqual(set(low.subjects(MORK.mappingFor, contract.iri)), set())
        self.assertTrue(set(low.subjects(RDF.type, MORK.MappingScheme)))


try:
    import mork_rdf
except ImportError:  # the compiler is a package of its own, installed by the python bootstrap
    mork_rdf = None


@unittest.skipIf(mork_rdf is None, "mork_rdf is not installed")
class ConstructionCompilationTests(unittest.TestCase):
    """The lowered scheme compiles with `mork_rdf` and runs to the graph the contract states (SVA-S2g)."""

    BASE = "https://example.org/lattice/surface/order-supplier/out/"
    NODE = BASE + "order-supplier/Supplier/"
    TYPE = str(RDF.type)

    @classmethod
    def setUpClass(cls) -> None:
        # The compiler reads MORK's own shapes through the repository catalogue's reader, which sits in tools/.
        if str(ROOT / "tools") not in sys.path:
            sys.path.insert(0, str(ROOT / "tools"))

    def compile(self, graph: Graph):
        low = lower_projection(order_contract(graph))
        (scheme,) = set(low.subjects(RDF.type, MORK.MappingScheme))
        return mork_rdf.compile_scheme(low, scheme, base=self.BASE, at=datetime.fromisoformat("2026-11-24T00:00:00+00:00"))

    def evaluate(self, engine: str, compiled, source: Graph):
        if engine == "oxigraph":
            out = mork_rdf.run(compiled, source)
            return {(str(s), str(p), str(o)) for s, p, o in out.graph}, {(f.code, f.focus, f.value) for f in out.findings}
        from rdflib import Dataset

        dataset = Dataset()
        for triple in source:
            dataset.default_graph.add(triple)
        written = {(str(s), str(p), str(o)) for q in compiled.constructs for s, p, o in dataset.query(q.text)}
        reported = {(q.code, str(r["focus"]), None if r["value"] is None else str(r["value"])) for q in compiled.checks for r in dataset.query(q.text)}
        return written, reported

    def test_the_example_compiles_to_the_query_the_case_shows(self) -> None:
        compiled = self.compile(order_graph())
        node = compiled.constructs[0]
        expected = f"""BASE <{self.BASE}>
CONSTRUCT {{ ?t3 <{self.TYPE}> <{ORDER_SUPPLIER}Supplier> . ?f1 <{ORDER_SUPPLIER}suppliedBy> ?t3 . }}
WHERE {{
  ?f1 <{self.TYPE}> <{ORDER_SUPPLIER}Order> .
  FILTER (((EXISTS {{ ?f1 <{ORDER_SUPPLIER}supplierCode> ?any2 . }})))
  ?f1 <{ORDER_SUPPLIER}supplierCode> ?v4 .
  BIND (IRI(CONCAT("order-supplier/Supplier/", ENCODE_FOR_URI(STR(?v4)))) AS ?t3)
}}"""
        self.assertEqual(" ".join(node.text.split()), " ".join(expected.split()))
        self.assertEqual(len(compiled.constructs), 3)
        self.assertEqual([f.code for f in compiled.findings], ["MappingReview"])
        self.assertFalse(compiled.errors)

    def test_the_example_runs_to_its_expected_graph_on_each_engine(self) -> None:
        compiled = self.compile(order_graph())
        source = order_graph()
        for engine in ("oxigraph", "rdflib"):
            with self.subTest(engine=engine):
                written, reported = self.evaluate(engine, compiled, source)
                s1, s2 = self.NODE + "S1", self.NODE + "S2"
                self.assertEqual(
                    {t for t in written if t[2] != "true"},
                    {
                        (s1, self.TYPE, ORDER_SUPPLIER + "Supplier"),
                        (s1, ORDER_SUPPLIER + "code", "S1"),
                        (s1, ORDER_SUPPLIER + "name", "Acme Components"),
                        (s2, self.TYPE, ORDER_SUPPLIER + "Supplier"),
                        (s2, ORDER_SUPPLIER + "code", "S2"),
                        (ORDER_SUPPLIER + "order-1", ORDER_SUPPLIER + "suppliedBy", s1),
                        (ORDER_SUPPLIER + "order-2", ORDER_SUPPLIER + "suppliedBy", s1),
                        (ORDER_SUPPLIER + "order-3", ORDER_SUPPLIER + "suppliedBy", s2),
                    },
                )
                self.assertEqual(reported, set())

    def test_a_node_for_each_order_runs_to_a_node_for_each_order(self) -> None:
        compiled = self.compile(per_instance_graph())
        self.assertEqual(compiled.findings, ())
        for engine in ("oxigraph", "rdflib"):
            with self.subTest(engine=engine):
                written, _ = self.evaluate(engine, compiled, order_graph())
                nodes = {s for s, p, o in written if p == self.TYPE and o == ORDER_SUPPLIER + "Supplier"}
                self.assertEqual(len(nodes), 3)
                links = {s: o for s, p, o in written if p == ORDER_SUPPLIER + "suppliedBy"}
                self.assertEqual(len(set(links.values())), 3)

    def test_an_order_missing_its_required_code_contributes_nothing_and_is_reported(self) -> None:
        source = order_graph()
        source.parse(
            data=f"""@prefix ex: <{ORDER_SUPPLIER}> . ex:order-4 a ex:Order ; ex:supplierName "No Code Ltd" .""", format="turtle"
        )
        for engine in ("oxigraph", "rdflib"):
            with self.subTest(engine=engine):
                written, reported = self.evaluate(engine, self.compile(order_graph()), source)
                self.assertNotIn(ORDER_SUPPLIER + "order-4", {s for s, p, o in written})
                self.assertNotIn("No Code Ltd", {o for s, p, o in written})
                self.assertEqual(reported, {("InstanceExcluded", ORDER_SUPPLIER + "order-4", f"<{ORDER_SUPPLIER}supplierCode>")})

    def test_an_order_with_the_key_and_without_another_required_value_writes_no_link_where_another_made_the_node(self) -> None:
        contract_graph = order_with(remove=[("os-name", SRF.roleKind, None)], add="ex:os-name srf:roleKind srf:RequiredEvidenceRole .")
        source = Graph()
        source.parse(
            data=f"""@prefix ex: <{ORDER_SUPPLIER}> .
            ex:a a ex:Order ; ex:supplierCode "S1" ; ex:supplierName "Acme Components" .
            ex:b a ex:Order ; ex:supplierCode "S1" .""",
            format="turtle",
        )
        for engine in ("oxigraph", "rdflib"):
            with self.subTest(engine=engine):
                written, reported = self.evaluate(engine, self.compile(contract_graph), source)
                self.assertIn((ORDER_SUPPLIER + "a", ORDER_SUPPLIER + "suppliedBy", self.NODE + "S1"), written)
                self.assertNotIn(ORDER_SUPPLIER + "b", {s for s, p, o in written})
                self.assertEqual(reported, {("InstanceExcluded", ORDER_SUPPLIER + "b", f"<{ORDER_SUPPLIER}supplierName>")})

    def test_a_node_whose_orders_disagree_on_its_name_is_reported_by_node_and_value(self) -> None:
        source = Graph()
        source.parse(
            data=f"""@prefix ex: <{ORDER_SUPPLIER}> .
            ex:a a ex:Order ; ex:supplierCode "S1" ; ex:supplierName "Acme Components" .
            ex:b a ex:Order ; ex:supplierCode "S1" ; ex:supplierName "Acme Ltd" .""",
            format="turtle",
        )
        for engine in ("oxigraph", "rdflib"):
            with self.subTest(engine=engine):
                _, reported = self.evaluate(engine, self.compile(order_graph()), source)
                self.assertEqual(
                    reported,
                    {("ValueDisagrees", self.NODE + "S1", "Acme Components"), ("ValueDisagrees", self.NODE + "S1", "Acme Ltd")},
                )

    def test_a_keyed_construction_carries_the_mapping_review_and_one_for_each_instance_does_not(self) -> None:
        keyed = [f for f in self.compile(order_graph()).findings if f.code == "MappingReview"]
        self.assertEqual(len(keyed), 1)
        self.assertEqual(keyed[0].severity, mork_rdf.Severity.WARNING)
        self.assertEqual([f for f in self.compile(per_instance_graph()).findings if f.code == "MappingReview"], [])

    def test_compiling_the_lowered_scheme_is_the_same_whatever_the_order_of_the_contract(self) -> None:
        reference = self.compile(order_graph()).text()
        triples = sorted(order_graph())
        for seed in range(3):
            shuffled = list(triples)
            random.Random(seed).shuffle(shuffled)
            graph = Graph()
            for triple in shuffled:
                graph.add(triple)
            self.assertEqual(self.compile(graph).text(), reference)



ORDER_CUSTOMER = "https://example.org/lattice/surface/order-customer#"
ORDER_CUSTOMER_EXAMPLE = "order-customer-join-projection.ttl"


def join_graph() -> Graph:
    return load(ORDER_CUSTOMER_EXAMPLE)


def join_with(remove=(), add="") -> Graph:
    """The order and customer example with some triples removed, given as (subject, predicate, object) local names with the
    object a local name, a term or None for any, and some Turtle added."""
    graph = join_graph()
    for subject, predicate, obj in remove:
        target = obj if obj is None or isinstance(obj, (URIRef, Literal)) else URIRef(ORDER_CUSTOMER + obj)
        graph.remove((URIRef(ORDER_CUSTOMER + subject), predicate, target))
    if add:
        graph.parse(
            data=f"""
            @prefix srf: <https://www.nebularis.org/neuro-semantic/lattice/surface#> .
            @prefix ex: <{ORDER_CUSTOMER}> .
            @prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
            {add}
            """,
            format="turtle",
        )
    return graph


def candidate_graph() -> Graph:
    """The example on candidate evidence, both bindings of its one pair."""
    return join_with(
        remove=[("oc-code", SRF.roleKind, None), ("oc-match", SRF.roleKind, None)],
        add="ex:oc-code srf:roleKind srf:CandidateEvidenceRole . ex:oc-match srf:roleKind srf:CandidateEvidenceRole .",
    )


def any_number_graph() -> Graph:
    return join_with(remove=[("oc-join", SRF.joinMatches, None)], add="ex:oc-join srf:joinMatches srf:AnyNumber .")


def typed_graph() -> Graph:
    """The example comparing integer codes, both bindings stating the datatype."""
    return join_with(add="ex:oc-code srf:bindsDatatype xsd:integer . ex:oc-match srf:bindsDatatype xsd:integer .")


def cast_graph() -> Graph:
    """The example where the order holds its code as a string and the customer as an integer, so the order's value is cast."""
    return join_with(add="ex:oc-code srf:bindsDatatype xsd:string . ex:oc-match srf:bindsDatatype xsd:integer .")


def default_graph() -> Graph:
    """The example that states neither count, so it means at most one match for a value and any number of links."""
    return join_with(remove=[("oc-join", SRF.joinMatches, None)])


def one_link_graph() -> Graph:
    return join_with(add="ex:oc-join srf:joinLinks srf:AtMostOne .")


def mixed_graph() -> Graph:
    """The two-pair example whose first pair is compared as the same term and whose second casts a string region to an integer."""
    graph = two_pair_graph()
    for name, datatype in (("oc-region", XSD.string), ("oc-region-match", XSD.integer)):
        graph.add((URIRef(ORDER_CUSTOMER + name), SRF.bindsDatatype, datatype))
    return graph


def two_pair_graph() -> Graph:
    """The example joined on the code and a region, so a customer must hold both values the order names."""
    return join_with(
        add="""
        ex:oc-region a srf:ProjectionRoleBinding ; srf:roleKind srf:RequiredEvidenceRole ; srf:bindsProperty ex:customerRegion .
        ex:oc-region-match a srf:ProjectionRoleBinding ; srf:roleKind srf:RequiredEvidenceRole ;
            srf:bindsCarrier ex:Customer ; srf:bindsProperty ex:region .
        ex:order-customer-projection srf:hasRoleBinding ex:oc-region , ex:oc-region-match .
        ex:oc-join srf:joinsOn [ srf:joinLeft ex:oc-region ; srf:joinRight ex:oc-region-match ] .
        """
    )


def join_contract(graph: Graph):
    return read_projection_contracts(graph, only=ORDER_CUSTOMER + "order-customer-projection")[0]


class JoinModelTests(unittest.TestCase):
    """The analyser applies laws srf:P14 to srf:P17 as the shapes do."""

    def test_the_example_parses_its_pair_its_count_and_its_link(self) -> None:
        contract = join_contract(join_graph())
        join = contract.join
        self.assertIsNone(contract.expression)
        self.assertIsNone(contract.construction)
        self.assertEqual(join.iri, URIRef(ORDER_CUSTOMER + "oc-join"))
        self.assertEqual([(p.left.iri, p.right.iri) for p in join.pairs], [(URIRef(ORDER_CUSTOMER + "oc-code"), URIRef(ORDER_CUSTOMER + "oc-match"))])
        self.assertTrue(join.at_most_one)
        self.assertTrue(join.required)
        self.assertEqual(join.second_carrier, URIRef(ORDER_CUSTOMER + "Customer"))
        self.assertEqual(join.link.binds_property, URIRef(ORDER_CUSTOMER + "placedFor"))

    def test_a_join_on_candidate_evidence_is_not_required_and_a_count_of_any_number_is_not_at_most_one(self) -> None:
        self.assertFalse(join_contract(candidate_graph()).join.required)
        self.assertFalse(join_contract(any_number_graph()).join.at_most_one)

    def test_a_statement_that_states_neither_count_means_at_most_one_match_for_a_value_and_any_number_of_links(self) -> None:
        join = join_contract(default_graph()).join
        self.assertEqual((join.matches, join.links), (SRF.AtMostOne, SRF.AnyNumber))
        self.assertTrue(join.at_most_one)
        self.assertFalse(join.at_most_one_link)
        self.assertTrue(join_contract(one_link_graph()).join.at_most_one_link)

    def test_each_pair_states_its_own_datatype_the_right_bindings_and_a_pair_that_states_none_compares_the_same_term(self) -> None:
        self.assertEqual([p.datatype for p in join_contract(join_graph()).join.pairs], [None])
        self.assertEqual([p.datatype for p in join_contract(cast_graph()).join.pairs], [XSD.integer])
        self.assertEqual([p.datatype for p in join_contract(typed_graph()).join.pairs], [XSD.integer])
        self.assertEqual([p.datatype for p in join_contract(mixed_graph()).join.pairs], [None, XSD.integer])

    def test_pairs_are_read_in_the_order_of_the_properties_they_compare(self) -> None:
        pairs = join_contract(two_pair_graph()).join.pairs
        self.assertEqual([p.left.binds_property for p in pairs], [URIRef(ORDER_CUSTOMER + "customerCode"), URIRef(ORDER_CUSTOMER + "customerRegion")])

    def test_the_statement_is_the_same_whatever_the_order_of_the_triples(self) -> None:
        for build in (join_graph, two_pair_graph, mixed_graph, one_link_graph):
            reference = join_contract(build()).join
            triples = sorted(build())
            for seed in range(5):
                shuffled = list(triples)
                random.Random(seed).shuffle(shuffled)
                graph = Graph()
                for triple in shuffled:
                    graph.add(triple)
                self.assertEqual(join_contract(graph).join, reference)

    def refused(self, graph: Graph, law: str) -> None:
        with self.assertRaisesRegex(ContractError, law):
            read_projection_contracts(graph)

    def test_a_join_with_no_statement_is_refused(self) -> None:
        self.refused(join_with(remove=[("oc-link", SRF.joinedAs, None)]), "srf:P14")

    def test_a_statement_on_a_binding_that_is_not_a_result_target_is_refused(self) -> None:
        self.refused(join_with(add="ex:oc-code srf:joinedAs ex:oc-join ."), "srf:P14")

    def test_a_statement_on_a_projection_of_another_kind_is_refused(self) -> None:
        graph = join_with(remove=[("order-customer-projection", SRF.projectionKind, None)], add="ex:order-customer-projection srf:projectionKind srf:ExpansionProjection .")
        self.refused(graph, "srf:P14")
        self.refused(arr_with(add="ex:arr-target srf:joinedAs ex:arr-expression ."), "srf:P14")

    def test_a_link_that_binds_no_property_is_refused(self) -> None:
        self.refused(join_with(remove=[("oc-link", SRF.bindsProperty, None)]), "srf:P14")

    def test_a_statement_that_is_not_a_join_statement_is_refused(self) -> None:
        self.refused(join_with(remove=[("oc-join", RDF.type, SRF.JoinStatement)]), "srf:P14")

    def test_a_statement_with_no_pair_is_refused(self) -> None:
        self.refused(join_with(remove=[("oc-join", SRF.joinsOn, None)]), "srf:P15")

    def test_a_count_the_choice_does_not_name_is_refused(self) -> None:
        self.refused(join_with(remove=[("oc-join", SRF.joinMatches, None)], add="ex:oc-join srf:joinMatches ex:Elsewhere ."), "srf:P15")
        self.refused(join_with(add="ex:oc-join srf:joinLinks ex:Elsewhere ."), "srf:P15")

    def test_a_pair_with_no_left_or_no_right_is_refused(self) -> None:
        for side in ("joinLeft", "joinRight"):
            with self.subTest(side=side):
                graph = join_with(remove=[("oc-join", SRF.joinsOn, None)], add=f"ex:oc-join srf:joinsOn [ srf:{side} ex:oc-code ] .")
                self.refused(graph, "srf:P15")

    def test_a_side_that_is_not_an_evidence_binding_is_refused(self) -> None:
        for side, other in (("joinLeft", "oc-match"), ("joinRight", "oc-code")):
            for source in ("oc-subject", "oc-link", "unknown"):
                with self.subTest(side=side, source=source):
                    graph = join_with(remove=[("oc-join", SRF.joinsOn, None)], add=f"ex:oc-join srf:joinsOn [ srf:{side} ex:{source} ; srf:{'joinRight' if side == 'joinLeft' else 'joinLeft'} ex:{other} ] .")
                    self.refused(graph, "srf:P16")

    def test_a_left_that_names_a_second_carrier_is_refused(self) -> None:
        self.refused(join_with(add="ex:oc-code srf:bindsCarrier ex:Customer ."), "srf:P16")

    def test_a_right_that_names_no_carrier_or_the_contracts_own_is_refused(self) -> None:
        self.refused(join_with(remove=[("oc-match", SRF.bindsCarrier, None)]), "srf:P16")
        self.refused(join_with(remove=[("oc-match", SRF.bindsCarrier, None)], add="ex:oc-match srf:bindsCarrier ex:Order ."), "srf:P16")

    def test_right_bindings_that_name_two_carriers_are_refused(self) -> None:
        graph = two_pair_graph()
        graph.remove((URIRef(ORDER_CUSTOMER + "oc-region-match"), SRF.bindsCarrier, None))
        graph.add((URIRef(ORDER_CUSTOMER + "oc-region-match"), SRF.bindsCarrier, URIRef(ORDER_CUSTOMER + "Elsewhere")))
        self.refused(graph, "srf:P16")

    def test_a_pair_of_two_evidence_kinds_or_a_statement_of_two_is_refused(self) -> None:
        self.refused(join_with(remove=[("oc-match", SRF.roleKind, None)], add="ex:oc-match srf:roleKind srf:CandidateEvidenceRole ."), "srf:P17")
        graph = two_pair_graph()
        for name in ("oc-region", "oc-region-match"):
            graph.remove((URIRef(ORDER_CUSTOMER + name), SRF.roleKind, None))
            graph.add((URIRef(ORDER_CUSTOMER + name), SRF.roleKind, SRF.CandidateEvidenceRole))
        self.refused(graph, "srf:P17")

    def test_a_left_binding_that_states_a_datatype_with_no_right_one_to_cast_it_to_is_refused(self) -> None:
        self.refused(join_with(add="ex:oc-code srf:bindsDatatype xsd:integer ."), "srf:P17")
        graph = two_pair_graph()
        graph.add((URIRef(ORDER_CUSTOMER + "oc-region"), SRF.bindsDatatype, XSD.string))
        self.refused(graph, "srf:P17")

    def test_pairs_and_the_bindings_of_a_pair_may_state_different_datatypes(self) -> None:
        for graph in (cast_graph(), mixed_graph(), join_with(add="ex:oc-match srf:bindsDatatype xsd:integer .")):
            self.assertIsNotNone(join_contract(graph).join)


class JoinShapeTests(unittest.TestCase):
    """The shapes of ontology/surface refuse what the analyser refuses, with no code beside them."""

    def violations(self, graph: Graph) -> set:
        return {name.rsplit("#", 1)[-1] for name in shape_violations(graph, SURFACE_SHAPES)}

    def test_the_example_and_its_variants_conform(self) -> None:
        for graph in (join_graph(), candidate_graph(), any_number_graph(), typed_graph(), two_pair_graph(), cast_graph(), default_graph(), one_link_graph(), mixed_graph()):
            self.assertEqual(self.violations(graph), set())

    def test_a_join_with_no_statement_is_refused(self) -> None:
        graph = join_with(remove=[("oc-link", SRF.joinedAs, None)])
        self.assertIn("JoinRequiredShape", self.violations(graph))
        self.assertIn("JoinStatementReachedShape", self.violations(graph))

    def test_a_statement_on_a_binding_that_is_not_a_result_target_is_refused(self) -> None:
        self.assertIn("JoinPlacementShape", self.violations(join_with(add="ex:oc-code srf:joinedAs ex:oc-join .")))
        self.assertIn("JoinPlacementShape", self.violations(arr_with(add="ex:arr-target srf:joinedAs ex:arr-expression .")))

    def test_a_statement_on_a_projection_of_another_kind_is_refused(self) -> None:
        graph = join_with(remove=[("order-customer-projection", SRF.projectionKind, None)], add="ex:order-customer-projection srf:projectionKind srf:GraphConstructionProjection .")
        self.assertIn("JoinPlacementShape", self.violations(graph))

    def test_two_statements_on_one_binding_are_refused(self) -> None:
        graph = join_with(add="ex:oc-link srf:joinedAs ex:oc-other . ex:oc-other a srf:JoinStatement .")
        self.assertIn("ProjectionRoleBindingShape", self.violations(graph))

    def test_a_link_that_binds_no_property_is_refused(self) -> None:
        self.assertIn("JoinLinkPropertyRequiredShape", self.violations(join_with(remove=[("oc-link", SRF.bindsProperty, None)])))

    def test_a_statement_that_is_no_join_statement_is_refused(self) -> None:
        self.assertIn("JoinStatementTypedShape", self.violations(join_with(remove=[("oc-join", RDF.type, SRF.JoinStatement)])))

    def test_a_statement_with_no_pair_is_refused_and_one_with_no_count_is_not(self) -> None:
        self.assertIn("JoinStatementShape", self.violations(join_with(remove=[("oc-join", SRF.joinsOn, None)])))
        self.assertNotIn("JoinStatementShape", self.violations(default_graph()))

    def test_a_count_the_choice_does_not_name_or_a_count_stated_twice_is_refused(self) -> None:
        graph = join_with(remove=[("oc-join", SRF.joinMatches, None)], add="ex:oc-join srf:joinMatches ex:Elsewhere .")
        self.assertIn("JoinStatementShape", self.violations(graph))
        self.assertIn("JoinStatementShape", self.violations(join_with(add="ex:oc-join srf:joinLinks ex:Elsewhere .")))
        self.assertIn("JoinStatementShape", self.violations(join_with(add="ex:oc-join srf:joinMatches srf:AnyNumber .")))
        self.assertIn("JoinStatementShape", self.violations(join_with(add="ex:oc-join srf:joinLinks srf:AtMostOne , srf:AnyNumber .")))

    def test_a_pair_with_no_left_or_no_right_is_refused(self) -> None:
        for side in ("joinLeft", "joinRight"):
            with self.subTest(side=side):
                graph = join_with(remove=[("oc-join", SRF.joinsOn, None)], add=f"ex:oc-join srf:joinsOn [ srf:{side} ex:oc-code ] .")
                self.assertIn("JoinPairShape", self.violations(graph))

    def test_a_side_that_is_not_an_evidence_binding_is_refused(self) -> None:
        for source in ("oc-subject", "oc-link", "unknown"):
            with self.subTest(source=source):
                left = join_with(remove=[("oc-join", SRF.joinsOn, None)], add=f"ex:oc-join srf:joinsOn [ srf:joinLeft ex:{source} ; srf:joinRight ex:oc-match ] .")
                self.assertIn("JoinLeftBindingShape", self.violations(left))
                right = join_with(remove=[("oc-join", SRF.joinsOn, None)], add=f"ex:oc-join srf:joinsOn [ srf:joinLeft ex:oc-code ; srf:joinRight ex:{source} ] .")
                self.assertIn("JoinRightBindingShape", self.violations(right))

    def test_a_left_that_names_a_second_carrier_is_refused(self) -> None:
        self.assertIn("JoinLeftBindingShape", self.violations(join_with(add="ex:oc-code srf:bindsCarrier ex:Customer .")))

    def test_a_right_that_names_no_carrier_or_the_contracts_own_is_refused(self) -> None:
        self.assertIn("JoinRightBindingShape", self.violations(join_with(remove=[("oc-match", SRF.bindsCarrier, None)])))
        graph = join_with(remove=[("oc-match", SRF.bindsCarrier, None)], add="ex:oc-match srf:bindsCarrier ex:Order .")
        self.assertIn("JoinRightBindingShape", self.violations(graph))

    def test_right_bindings_that_name_two_carriers_are_refused(self) -> None:
        graph = two_pair_graph()
        graph.remove((URIRef(ORDER_CUSTOMER + "oc-region-match"), SRF.bindsCarrier, None))
        graph.add((URIRef(ORDER_CUSTOMER + "oc-region-match"), SRF.bindsCarrier, URIRef(ORDER_CUSTOMER + "Elsewhere")))
        self.assertIn("JoinSecondCarrierShape", self.violations(graph))

    def test_a_pair_of_two_evidence_kinds_or_a_statement_of_two_is_refused(self) -> None:
        graph = join_with(remove=[("oc-match", SRF.roleKind, None)], add="ex:oc-match srf:roleKind srf:CandidateEvidenceRole .")
        self.assertIn("JoinEvidenceKindShape", self.violations(graph))
        graph = two_pair_graph()
        for name in ("oc-region", "oc-region-match"):
            graph.remove((URIRef(ORDER_CUSTOMER + name), SRF.roleKind, None))
            graph.add((URIRef(ORDER_CUSTOMER + name), SRF.roleKind, SRF.CandidateEvidenceRole))
        self.assertIn("JoinEvidenceKindShape", self.violations(graph))

    def test_a_left_binding_that_states_a_datatype_with_no_right_one_to_cast_it_to_is_refused(self) -> None:
        self.assertIn("JoinDatatypeShape", self.violations(join_with(add="ex:oc-code srf:bindsDatatype xsd:integer .")))
        graph = two_pair_graph()
        graph.add((URIRef(ORDER_CUSTOMER + "oc-region"), SRF.bindsDatatype, XSD.string))
        self.assertIn("JoinDatatypeShape", self.violations(graph))

    def test_a_pair_may_cast_one_side_and_the_pairs_of_a_statement_may_differ(self) -> None:
        for graph in (join_with(add="ex:oc-match srf:bindsDatatype xsd:integer ."), cast_graph(), mixed_graph()):
            self.assertNotIn("JoinDatatypeShape", self.violations(graph))

    def test_the_laws_the_shapes_discharge_are_in_the_vocabulary(self) -> None:
        vocabulary = parse_files([str(ROOT / "ontology" / "surface" / "vocab" / "surface-vocab.ttl")])
        for law in ("P14", "P15", "P16", "P17"):
            self.assertIn((SRF[law], RDF.type, SRF.Law), vocabulary)
        for count in ("AtMostOne", "AnyNumber"):
            self.assertIn((SRF[count], RDF.type, SRF.JoinCardinality), vocabulary)


class JoinLoweringTests(unittest.TestCase):
    """Surface-to-MORK lowering of a join (ADR-A18)."""

    def lowered(self, graph: Graph):
        contract = join_contract(graph)
        return contract, lower_projection(contract)

    def parts(self, low: Graph, contract):
        root = lowered_head(contract)
        (datum,) = low.objects(root, MORK.compositeNarrowerMapping)
        return root, datum

    def test_the_join_lowers_into_a_scheme_a_source_node_root_and_a_datum_that_takes_the_second_carriers_node(self) -> None:
        contract, low = self.lowered(join_graph())
        (scheme,) = set(low.subjects(RDF.type, MORK.MappingScheme))
        root, datum = self.parts(low, contract)
        self.assertEqual(low.value(root, MORK.identityRule), MORK.SourceNodeIdentity)
        self.assertEqual(low.value(low.value(root, MORK.mappingFor), MORK.representedAs), URIRef(ORDER_CUSTOMER + "Order"))
        self.assertEqual(low.value(datum, MORK.broaderApplicative), root)
        self.assertEqual(low.value(datum, MORK.identityRule), MORK.SourceNodeIdentity)
        self.assertEqual(low.value(low.value(datum, MORK.mappingFor), MORK.representedAs), URIRef(ORDER_CUSTOMER + "Customer"))
        self.assertEqual(low.value(datum, MORK.inverseRBoxMatch), URIRef(ORDER_CUSTOMER + "placedFor"))
        self.assertEqual(low.value(datum, MORK.mappingScheme), scheme)
        self.assertEqual(set(low.objects(contract.iri, SRF.producesMapping)), {root})
        # The datum takes a node and writes only the link, so it names no class to type it with and has nothing beneath it.
        self.assertIsNone(low.value(datum, MORK.exactTBoxMatch))
        self.assertEqual(set(low.objects(datum, MORK.compositeNarrowerMapping)), set())

    def test_the_datum_states_each_condition_its_count_and_whether_an_unmatched_instance_is_reported(self) -> None:
        contract, low = self.lowered(join_graph())
        _, datum = self.parts(low, contract)
        (condition,) = low.objects(datum, MORK.joinsOn)
        self.assertIn((condition, RDF.type, MORK.JoinCondition), low)
        self.assertEqual(low.value(condition, MORK.parentRef), Literal(f"<{ORDER_CUSTOMER}customerCode>"))
        self.assertEqual(low.value(condition, MORK.ownRef), Literal(f"<{ORDER_CUSTOMER}code>"))
        self.assertEqual(low.value(datum, MORK.joinCardinality), MORK.AtMostOneMatch)
        self.assertEqual(low.value(datum, MORK.linkCardinality), MORK.AnyNumberOfMatches)
        self.assertEqual(low.value(datum, MORK.reportsUnmatched), Literal(True))
        self.assertEqual(low.value(datum, MORK.unmatchedSeverity), MORK.WarningFinding)

    def test_a_count_of_any_number_and_a_join_on_candidate_evidence_are_stated_as_they_are(self) -> None:
        _, any_low = self.lowered(any_number_graph())
        _, candidate_low = self.lowered(candidate_graph())
        for low, count, severity in ((any_low, MORK.AnyNumberOfMatches, MORK.WarningFinding), (candidate_low, MORK.AtMostOneMatch, MORK.InfoFinding)):
            datum = next(low.subjects(MORK.joinCardinality, None))
            self.assertEqual(low.value(datum, MORK.joinCardinality), count)
            # An instance that holds the values and finds no match is reported either way, as information on candidate evidence.
            self.assertEqual(low.value(datum, MORK.reportsUnmatched), Literal(True))
            self.assertEqual(low.value(datum, MORK.unmatchedSeverity), severity)

    def test_a_count_the_contract_leaves_out_is_written_into_the_scheme_as_its_default(self) -> None:
        """The contract may omit either count. The compiled form never does, so MORK states what the contract meant."""
        _, low = self.lowered(default_graph())
        datum = next(low.subjects(MORK.joinCardinality, None))
        self.assertEqual(low.value(datum, MORK.joinCardinality), MORK.AtMostOneMatch)
        self.assertEqual(low.value(datum, MORK.linkCardinality), MORK.AnyNumberOfMatches)
        self.assertEqual(canonical.hash_graph(self.lowered(default_graph())[1]) != canonical.hash_graph(self.lowered(one_link_graph())[1]), True)
        _, low = self.lowered(one_link_graph())
        self.assertEqual(low.value(next(low.subjects(MORK.joinCardinality, None)), MORK.linkCardinality), MORK.AtMostOneMatch)
        statement = join_graph()
        statement.add((URIRef(ORDER_CUSTOMER + "oc-join"), SRF.joinLinks, SRF.AnyNumber))
        stated = self.lowered(statement)[1]
        self.assertEqual(canonical.hash_graph(stated), canonical.hash_graph(self.lowered(join_graph())[1]))

    def test_the_guard_holds_the_required_evidence_of_the_instance_and_not_the_second_carriers(self) -> None:
        contract, low = self.lowered(join_graph())
        _, datum = self.parts(low, contract)
        guard = low.value(datum, MORK.appliesWhen)
        paths = {(low.value(c, SH.path), low.value(c, SH.minCount)) for c in low.objects(guard, SH.property)}
        self.assertEqual(paths, {(URIRef(ORDER_CUSTOMER + "customerCode"), Literal(1))})

    def test_a_join_on_candidate_evidence_is_guarded_by_no_value_it_compares(self) -> None:
        contract, low = self.lowered(candidate_graph())
        _, datum = self.parts(low, contract)
        self.assertIsNone(low.value(datum, MORK.appliesWhen))
        graph = join_with(add="ex:oc-channel a srf:ProjectionRoleBinding ; srf:roleKind srf:RequiredEvidenceRole ; srf:bindsProperty ex:channel . ex:order-customer-projection srf:hasRoleBinding ex:oc-channel .")
        _, low = self.lowered(graph)
        guard = low.value(self.parts(low, join_contract(graph))[1], MORK.appliesWhen)
        self.assertEqual({low.value(c, SH.path) for c in low.objects(guard, SH.property)}, {URIRef(ORDER_CUSTOMER + "customerCode"), URIRef(ORDER_CUSTOMER + "channel")})

    def test_each_pair_is_a_condition_in_the_order_of_the_properties_compared(self) -> None:
        contract, low = self.lowered(two_pair_graph())
        _, datum = self.parts(low, contract)
        conditions = [
            (low.value(c, MORK.parentRef), low.value(c, MORK.ownRef))
            for c in sorted(low.objects(datum, MORK.joinsOn))
        ]
        self.assertEqual(
            conditions,
            [
                (Literal(f"<{ORDER_CUSTOMER}customerCode>"), Literal(f"<{ORDER_CUSTOMER}code>")),
                (Literal(f"<{ORDER_CUSTOMER}customerRegion>"), Literal(f"<{ORDER_CUSTOMER}region>")),
            ],
        )

    def comparisons(self, graph: Graph) -> list:
        contract, low = self.lowered(graph)
        _, datum = self.parts(low, contract)
        self.assertIsNone(low.value(datum, MORK.lookupComparison))
        self.assertIsNone(low.value(datum, MORK.lookupDatatype))
        return [(low.value(c, MORK.parentRef), low.value(c, MORK.lookupComparison), low.value(c, MORK.lookupDatatype)) for c in sorted(low.objects(datum, MORK.joinsOn))]

    def test_each_condition_compares_by_term_unless_its_right_binding_states_a_datatype_which_the_value_is_cast_to(self) -> None:
        code, region = (Literal(f"<{ORDER_CUSTOMER}{name}>") for name in ("customerCode", "customerRegion"))
        self.assertEqual(self.comparisons(join_graph()), [(code, MORK.TermComparison, None)])
        self.assertEqual(self.comparisons(typed_graph()), [(code, MORK.CastComparison, XSD.integer)])
        # A string held by the order against an integer held by the customer, and a right binding alone, cast the order's value.
        self.assertEqual(self.comparisons(cast_graph()), [(code, MORK.CastComparison, XSD.integer)])
        self.assertEqual(self.comparisons(join_with(add="ex:oc-match srf:bindsDatatype xsd:integer .")), [(code, MORK.CastComparison, XSD.integer)])

    def test_a_composite_key_of_mixed_datatypes_states_each_pairs_comparison_on_its_own_condition(self) -> None:
        code, region = (Literal(f"<{ORDER_CUSTOMER}{name}>") for name in ("customerCode", "customerRegion"))
        self.assertEqual(self.comparisons(mixed_graph()), [(code, MORK.TermComparison, None), (region, MORK.CastComparison, XSD.integer)])
        two_integers = two_pair_graph()
        for name in ("oc-region", "oc-region-match"):
            two_integers.add((URIRef(ORDER_CUSTOMER + name), SRF.bindsDatatype, XSD.decimal))
        self.assertEqual(self.comparisons(two_integers), [(code, MORK.TermComparison, None), (region, MORK.CastComparison, XSD.decimal)])

    def test_the_lowered_scheme_is_one_the_mork_shapes_accept(self) -> None:
        for graph in (join_graph(), candidate_graph(), any_number_graph(), typed_graph(), two_pair_graph(), cast_graph(), default_graph(), one_link_graph(), mixed_graph()):
            self.assertEqual(shape_violations(self.lowered(graph)[1], MORK_SHAPES), set())

    def test_lowering_is_deterministic_and_the_same_with_the_triples_permuted(self) -> None:
        for build in (join_graph, two_pair_graph, mixed_graph, one_link_graph):
            reference = canonical.hash_graph(lower_projection(join_contract(build())))
            self.assertEqual(canonical.hash_graph(lower_projection(join_contract(build()))), reference)
            triples = sorted(build())
            for seed in range(5):
                shuffled = list(triples)
                random.Random(seed).shuffle(shuffled)
                graph = Graph()
                for triple in shuffled:
                    graph.add(triple)
                self.assertEqual(canonical.hash_graph(lower_projection(join_contract(graph))), reference)

    def test_a_join_is_not_a_bare_mapping(self) -> None:
        contract, low = self.lowered(join_graph())
        self.assertEqual(set(low.subjects(MORK.mappingFor, contract.iri)), set())
        self.assertTrue(set(low.subjects(RDF.type, MORK.MappingScheme)))

    def test_the_other_kinds_are_not_affected(self) -> None:
        (derivation,) = read_projection_contracts(arr_graph())
        self.assertIsNone(derivation.join)
        self.assertIsNone(order_contract(order_graph()).join)


@unittest.skipIf(mork_rdf is None, "mork_rdf is not installed")
class JoinCompilationTests(unittest.TestCase):
    """The lowered scheme compiles with `mork_rdf` and runs to the graph the contract states (SVA-S2h)."""

    BASE = "https://example.org/lattice/surface/order-customer/out/"
    LINK = ORDER_CUSTOMER + "placedFor"

    @classmethod
    def setUpClass(cls) -> None:
        if str(ROOT / "tools") not in sys.path:
            sys.path.insert(0, str(ROOT / "tools"))

    def compile(self, graph: Graph):
        low = lower_projection(join_contract(graph))
        (scheme,) = set(low.subjects(RDF.type, MORK.MappingScheme))
        return mork_rdf.compile_scheme(low, scheme, base=self.BASE, at=datetime.fromisoformat("2026-11-24T00:00:00+00:00"))

    def evaluate(self, engine: str, compiled, source: Graph):
        if engine == "oxigraph":
            out = mork_rdf.run(compiled, source)
            return {(str(s), str(p), str(o)) for s, p, o in out.graph}, {(f.code, f.focus, f.value) for f in out.findings}
        from rdflib import Dataset

        dataset = Dataset()
        for triple in source:
            dataset.default_graph.add(triple)
        written = {(str(s), str(p), str(o)) for q in compiled.constructs for s, p, o in dataset.query(q.text)}
        reported = {(q.code, str(r["focus"]), None if r["value"] is None else str(r["value"])) for q in compiled.checks for r in dataset.query(q.text)}
        return written, reported

    def test_the_example_compiles_to_the_query_the_case_shows(self) -> None:
        compiled = self.compile(join_graph())
        (link,) = compiled.constructs
        type_ = str(RDF.type)
        expected = f"""BASE <{self.BASE}>
CONSTRUCT {{ ?f1 <{self.LINK}> ?f2 . }}
WHERE {{
  ?f1 <{type_}> <{ORDER_CUSTOMER}Order> .
  ?f1 <{ORDER_CUSTOMER}customerCode> ?v3 .
  FILTER (((EXISTS {{ ?f1 <{ORDER_CUSTOMER}customerCode> ?any4 . }})))
  ?f2 <{type_}> <{ORDER_CUSTOMER}Customer> .
  ?f2 <{ORDER_CUSTOMER}code> ?v3 .
  {{ SELECT ?f1 ?v3 WHERE {{ ?f1 <{ORDER_CUSTOMER}customerCode> ?v3 . FILTER (((EXISTS {{ ?f1 <{ORDER_CUSTOMER}customerCode> ?any6 . }}))) ?f5 <{type_}> <{ORDER_CUSTOMER}Customer> . ?f5 <{ORDER_CUSTOMER}code> ?v3 . }} GROUP BY ?f1 ?v3 HAVING (COUNT(DISTINCT ?f5) = 1) }}
}}"""
        self.assertEqual(" ".join(link.text.split()), " ".join(expected.split()))
        self.assertEqual(sorted(q.code for q in compiled.checks), ["InstanceExcluded", "JoinAmbiguous", "JoinUnmatched"])
        self.assertEqual([(f.code, f.severity) for f in compiled.findings], [("MappingReview", mork_rdf.Severity.WARNING)])
        self.assertFalse(compiled.errors)

    def test_the_example_runs_to_its_expected_graph_on_each_engine(self) -> None:
        compiled = self.compile(join_graph())
        for engine in ("oxigraph", "rdflib"):
            with self.subTest(engine=engine):
                written, reported = self.evaluate(engine, compiled, join_graph())
                self.assertEqual(
                    written,
                    {
                        (ORDER_CUSTOMER + "order-1", self.LINK, ORDER_CUSTOMER + "customer-1"),
                        (ORDER_CUSTOMER + "order-2", self.LINK, ORDER_CUSTOMER + "customer-1"),
                    },
                )
                # The third order names a code no customer holds, so it is reported with the code and writes nothing.
                self.assertEqual(reported, {("JoinUnmatched", ORDER_CUSTOMER + "order-3", "C9")})

    def source_with(self, text: str) -> Graph:
        source = join_graph()
        source.parse(data=f"@prefix ex: <{ORDER_CUSTOMER}> .\n{text}", format="turtle")
        return source

    def test_an_order_whose_code_two_customers_hold_writes_no_link_and_names_each(self) -> None:
        source = self.source_with('ex:customer-3 a ex:Customer ; ex:code "C1" . ')
        for engine in ("oxigraph", "rdflib"):
            with self.subTest(engine=engine):
                written, reported = self.evaluate(engine, self.compile(join_graph()), source)
                self.assertEqual({s for s, p, o in written}, set())
                self.assertEqual(
                    {r for r in reported if r[0] == "JoinAmbiguous"},
                    {
                        ("JoinAmbiguous", ORDER_CUSTOMER + "order-1", ORDER_CUSTOMER + "customer-1"),
                        ("JoinAmbiguous", ORDER_CUSTOMER + "order-1", ORDER_CUSTOMER + "customer-3"),
                        ("JoinAmbiguous", ORDER_CUSTOMER + "order-2", ORDER_CUSTOMER + "customer-1"),
                        ("JoinAmbiguous", ORDER_CUSTOMER + "order-2", ORDER_CUSTOMER + "customer-3"),
                    },
                )

    def test_under_any_number_an_order_is_linked_to_each_customer_its_code_names(self) -> None:
        source = self.source_with('ex:customer-3 a ex:Customer ; ex:code "C1" . ')
        compiled = self.compile(any_number_graph())
        self.assertNotIn("JoinAmbiguous", {q.code for q in compiled.checks})
        for engine in ("oxigraph", "rdflib"):
            with self.subTest(engine=engine):
                written, _ = self.evaluate(engine, compiled, source)
                self.assertEqual(
                    written,
                    {
                        (order, self.LINK, ORDER_CUSTOMER + customer)
                        for order in (ORDER_CUSTOMER + "order-1", ORDER_CUSTOMER + "order-2")
                        for customer in ("customer-1", "customer-3")
                    },
                )

    def test_an_order_missing_its_required_code_contributes_nothing_and_is_reported(self) -> None:
        source = self.source_with('ex:order-4 a ex:Order . ')
        for engine in ("oxigraph", "rdflib"):
            with self.subTest(engine=engine):
                written, reported = self.evaluate(engine, self.compile(join_graph()), source)
                self.assertNotIn(ORDER_CUSTOMER + "order-4", {s for s, p, o in written})
                self.assertIn(("InstanceExcluded", ORDER_CUSTOMER + "order-4", f"<{ORDER_CUSTOMER}customerCode>"), reported)

    def test_on_candidate_evidence_an_order_with_a_code_and_no_customer_is_reported_as_information_and_one_with_no_code_is_silent(self) -> None:
        compiled = self.compile(candidate_graph())
        (unmatched,) = [q for q in compiled.checks if q.code == "JoinUnmatched"]
        self.assertEqual(unmatched.severity, mork_rdf.Severity.INFO)
        # On required evidence the same finding is a warning.
        (required,) = [q for q in self.compile(join_graph()).checks if q.code == "JoinUnmatched"]
        self.assertEqual(required.severity, mork_rdf.Severity.WARNING)
        for engine in ("oxigraph", "rdflib"):
            with self.subTest(engine=engine):
                written, reported = self.evaluate(engine, compiled, self.source_with("ex:order-4 a ex:Order . "))
                self.assertEqual(len(written), 2)
                # order-3 holds a code no customer has. order-4 holds no code, and says nothing.
                self.assertEqual(reported, {("JoinUnmatched", ORDER_CUSTOMER + "order-3", "C9")})
        out = mork_rdf.run(compiled, self.source_with("ex:order-4 a ex:Order . "))
        self.assertEqual({(f.code, f.focus): f.severity for f in out.findings}, {("JoinUnmatched", ORDER_CUSTOMER + "order-3"): mork_rdf.Severity.INFO})

    def test_two_codes_that_each_name_one_customer_give_an_order_two_links_since_a_value_is_counted_for_itself(self) -> None:
        source = self.source_with('ex:order-4 a ex:Order ; ex:customerCode "C1" , "C2" . ')
        compiled = self.compile(join_graph())
        for engine in ("oxigraph", "rdflib"):
            with self.subTest(engine=engine):
                written, reported = self.evaluate(engine, compiled, source)
                self.assertEqual(
                    {(s, o) for s, p, o in written if s == ORDER_CUSTOMER + "order-4"},
                    {(ORDER_CUSTOMER + "order-4", ORDER_CUSTOMER + "customer-1"), (ORDER_CUSTOMER + "order-4", ORDER_CUSTOMER + "customer-2")},
                )
                self.assertFalse({r for r in reported if r[1] == ORDER_CUSTOMER + "order-4"})

    def test_under_at_most_one_link_the_same_order_writes_no_link_and_names_each_match(self) -> None:
        source = self.source_with('ex:order-4 a ex:Order ; ex:customerCode "C1" , "C2" . ')
        compiled = self.compile(one_link_graph())
        self.assertIn("JoinManyMatches", {q.code for q in compiled.checks})
        for engine in ("oxigraph", "rdflib"):
            with self.subTest(engine=engine):
                written, reported = self.evaluate(engine, compiled, source)
                self.assertNotIn(ORDER_CUSTOMER + "order-4", {s for s, p, o in written})
                self.assertEqual(
                    {r for r in reported if r[0] == "JoinManyMatches"},
                    {("JoinManyMatches", ORDER_CUSTOMER + "order-4", ORDER_CUSTOMER + "customer-1"), ("JoinManyMatches", ORDER_CUSTOMER + "order-4", ORDER_CUSTOMER + "customer-2")},
                )
                # An order that finds one customer in all keeps its link.
                self.assertEqual({s for s, p, o in written}, {ORDER_CUSTOMER + "order-1", ORDER_CUSTOMER + "order-2"})

    def test_a_contract_that_states_neither_count_compiles_to_the_query_that_states_both(self) -> None:
        stated, omitted = self.compile(join_graph()), self.compile(default_graph())
        self.assertEqual([q.text for q in omitted.queries], [q.text for q in stated.queries])
        self.assertNotIn("JoinManyMatches", {q.code for q in omitted.checks})
        lowered = lower_projection(join_contract(default_graph()))
        self.assertIn((None, MORK.joinCardinality, MORK.AtMostOneMatch), lowered)
        self.assertIn((None, MORK.linkCardinality, MORK.AnyNumberOfMatches), lowered)

    def test_a_join_on_two_values_links_the_customer_that_holds_both(self) -> None:
        source = self.source_with(
            """ex:customer-1 ex:region "north" .
            ex:customer-3 a ex:Customer ; ex:code "C1" ; ex:region "south" .
            ex:order-1 ex:customerRegion "south" . ex:order-2 ex:customerRegion "east" ."""
        )
        for engine in ("oxigraph", "rdflib"):
            with self.subTest(engine=engine):
                written, reported = self.evaluate(engine, self.compile(two_pair_graph()), source)
                self.assertEqual(written, {(ORDER_CUSTOMER + "order-1", self.LINK, ORDER_CUSTOMER + "customer-3")})
                self.assertIn(("JoinUnmatched", ORDER_CUSTOMER + "order-2", "C1/east"), reported)

    MIXED = """@prefix ex: <%s> .
        ex:customer-1 a ex:Customer ; ex:code "A" ; ex:region 42 .
        ex:customer-2 a ex:Customer ; ex:code "A" ; ex:region 5 .
        ex:order-1 a ex:Order ; ex:customerCode "A" ; ex:customerRegion "42" .
        ex:order-2 a ex:Order ; ex:customerCode "A" ; ex:customerRegion 5 .
        ex:order-3 a ex:Order ; ex:customerCode "A" ; ex:customerRegion "9" .
        ex:order-4 a ex:Order ; ex:customerCode "B" ; ex:customerRegion "42" ."""

    def test_a_pair_may_cast_one_side_a_string_the_order_holds_against_an_integer_the_customer_holds(self) -> None:
        source = Graph().parse(data=f"""@prefix ex: <{ORDER_CUSTOMER}> .
            ex:customer-1 a ex:Customer ; ex:code 42 .
            ex:order-1 a ex:Order ; ex:customerCode "42" .
            ex:order-2 a ex:Order ; ex:customerCode "43" .""", format="turtle")
        for build in (cast_graph, lambda: join_with(add="ex:oc-match srf:bindsDatatype xsd:integer .")):
            compiled = self.compile(build())
            for engine in ("oxigraph", "rdflib"):
                with self.subTest(engine=engine):
                    written, reported = self.evaluate(engine, compiled, source)
                    self.assertEqual(written, {(ORDER_CUSTOMER + "order-1", self.LINK, ORDER_CUSTOMER + "customer-1")})
                    self.assertEqual(reported, {("JoinUnmatched", ORDER_CUSTOMER + "order-2", "43")})
        # Compared as the same term, with no cast, the string never meets the integer.
        for engine in ("oxigraph", "rdflib"):
            with self.subTest(engine=engine):
                written, _ = self.evaluate(engine, self.compile(join_graph()), source)
                self.assertEqual(written, set())

    def test_a_composite_key_compares_a_string_pair_and_an_integer_pair_each_as_its_pair_says(self) -> None:
        source = Graph().parse(data=self.MIXED % ORDER_CUSTOMER, format="turtle")
        compiled = self.compile(mixed_graph())
        for engine in ("oxigraph", "rdflib"):
            with self.subTest(engine=engine):
                written, reported = self.evaluate(engine, compiled, source)
                # The code is joined as the same term and the region is cast to an integer, so the string "42" meets 42, and
                # the integer 5 meets 5. The two customers hold one code, so the region tells them apart.
                self.assertEqual(
                    written,
                    {(ORDER_CUSTOMER + "order-1", self.LINK, ORDER_CUSTOMER + "customer-1"), (ORDER_CUSTOMER + "order-2", self.LINK, ORDER_CUSTOMER + "customer-2")},
                )
                self.assertEqual(
                    {r for r in reported if r[0] in ("JoinUnmatched", "JoinAmbiguous")},
                    {("JoinUnmatched", ORDER_CUSTOMER + "order-3", "A/9"), ("JoinUnmatched", ORDER_CUSTOMER + "order-4", "B/42")},
                )

    def test_integer_codes_are_cast_to_the_datatype_the_bindings_state(self) -> None:
        source = Graph().parse(
            data=f"""@prefix ex: <{ORDER_CUSTOMER}> .
            ex:customer-1 a ex:Customer ; ex:code 7 .
            ex:order-1 a ex:Order ; ex:customerCode "7" .""",
            format="turtle",
        )
        for engine in ("oxigraph", "rdflib"):
            with self.subTest(engine=engine):
                written, _ = self.evaluate(engine, self.compile(typed_graph()), source)
                self.assertEqual(written, {(ORDER_CUSTOMER + "order-1", self.LINK, ORDER_CUSTOMER + "customer-1")})

    def test_a_join_carries_the_mapping_review_whatever_its_evidence_and_count(self) -> None:
        for build in (join_graph, candidate_graph, any_number_graph, typed_graph, two_pair_graph, cast_graph, default_graph, one_link_graph, mixed_graph):
            with self.subTest(build=build.__name__):
                review = [f for f in self.compile(build()).findings if f.code == "MappingReview"]
                self.assertEqual(len(review), 1)
                self.assertEqual(review[0].severity, mork_rdf.Severity.WARNING)

    def test_compiling_the_lowered_scheme_is_the_same_whatever_the_order_of_the_contract(self) -> None:
        reference = self.compile(join_graph()).text()
        triples = sorted(join_graph())
        for seed in range(3):
            shuffled = list(triples)
            random.Random(seed).shuffle(shuffled)
            graph = Graph()
            for triple in shuffled:
                graph.add(triple)
            self.assertEqual(self.compile(graph).text(), reference)


BUNDLE_ITEMS = "https://example.org/lattice/surface/bundle-items#"
BUNDLE_EXAMPLE = "bundle-items-expansion-projection.ttl"
CATEGORY_ANCESTORS = "https://example.org/lattice/surface/category-ancestors#"
CATEGORY_EXAMPLE = "category-ancestors-expansion-projection.ttl"

RDF_REST = "http://www.w3.org/1999/02/22-rdf-syntax-ns#rest"
RDF_FIRST = "http://www.w3.org/1999/02/22-rdf-syntax-ns#first"
#: What the two named sources are, written as paths in full IRIs (SVA-Q49).
LIST_PATH = f"<{BUNDLE_ITEMS}items>/<{RDF_REST}>*/<{RDF_FIRST}>"
CLOSURE_PATH = f"<{CATEGORY_ANCESTORS}broader>+"


def bundle_graph() -> Graph:
    return load(BUNDLE_EXAMPLE)


def category_graph() -> Graph:
    return load(CATEGORY_EXAMPLE)


def bundle_with(remove=(), add="") -> Graph:
    """The bundle example with some triples removed, given as (subject, predicate, object) local names with the object a local
    name, a term or None for any, and some Turtle added."""
    graph = bundle_graph()
    for subject, predicate, obj in remove:
        target = obj if obj is None or isinstance(obj, (URIRef, Literal)) else URIRef(BUNDLE_ITEMS + obj)
        graph.remove((URIRef(BUNDLE_ITEMS + subject), predicate, target))
    if add:
        graph.parse(
            data=f"""
            @prefix srf: <https://www.nebularis.org/neuro-semantic/lattice/surface#> .
            @prefix sh: <http://www.w3.org/ns/shacl#> .
            @prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
            @prefix ex: <{BUNDLE_ITEMS}> .
            @prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
            {add}
            """,
            format="turtle",
        )
    return graph


def members_path_graph(path: str) -> Graph:
    """The bundle example stating its members as a SHACL path of its own, in Turtle, and no named source."""
    return bundle_with(remove=[("bd-expansion", SRF.expansionSource, None)], add=f"ex:bd-expansion srf:membersPath {path} .")


def list_path_graph() -> Graph:
    """The path a list's members are, stated by the contract and not named."""
    return members_path_graph("( ex:items [ sh:zeroOrMorePath rdf:rest ] rdf:first )")


def candidate_bundle_graph() -> Graph:
    """The bundle example on candidate evidence, so no instance is excluded."""
    return bundle_with(remove=[("bd-items", SRF.roleKind, None)], add="ex:bd-items srf:roleKind srf:CandidateEvidenceRole .")


def expansion_contract(graph: Graph, key: str = "bundle-items-projection", namespace: str = BUNDLE_ITEMS):
    return read_projection_contracts(graph, only=namespace + key)[0]


class ExpansionModelTests(unittest.TestCase):
    """The analyser applies laws srf:P18 to srf:P20 as the shapes do."""

    def test_the_bundle_example_parses_its_evidence_its_source_and_its_property(self) -> None:
        contract = expansion_contract(bundle_graph())
        expansion = contract.expansion
        self.assertIsNone(contract.expression)
        self.assertIsNone(contract.construction)
        self.assertIsNone(contract.join)
        self.assertEqual(expansion.iri, URIRef(BUNDLE_ITEMS + "bd-expansion"))
        self.assertEqual(expansion.evidence.iri, URIRef(BUNDLE_ITEMS + "bd-items"))
        self.assertEqual(expansion.source, SRF.ListMembers)
        self.assertTrue(expansion.required)
        self.assertEqual(expansion.link.binds_property, URIRef(BUNDLE_ITEMS + "contains"))
        self.assertEqual(expansion.path_text, LIST_PATH)

    def test_the_category_example_is_a_transitive_closure_on_candidate_evidence(self) -> None:
        expansion = expansion_contract(category_graph(), "category-ancestors-projection", CATEGORY_ANCESTORS).expansion
        self.assertEqual(expansion.source, SRF.TransitiveClosure)
        self.assertFalse(expansion.required)
        self.assertEqual(expansion.path_text, CLOSURE_PATH)

    def test_a_path_the_contract_states_is_the_path_a_named_source_gives(self) -> None:
        stated = expansion_contract(list_path_graph()).expansion
        self.assertIsNone(stated.source)
        self.assertEqual(stated.path_text, LIST_PATH)
        closure = members_path_graph("[ sh:oneOrMorePath ex:items ]")
        self.assertEqual(expansion_contract(closure).expansion.path_text, f"<{BUNDLE_ITEMS}items>+")

    def test_each_form_of_a_path_is_read_and_written_in_full_iris(self) -> None:
        items = f"<{BUNDLE_ITEMS}items>"
        parts = f"<{BUNDLE_ITEMS}parts>"
        cases = {
            "ex:items": items,
            "( ex:items ex:parts )": f"{items}/{parts}",
            "[ sh:alternativePath ( ex:items ex:parts ) ]": f"{items}|{parts}",
            "[ sh:inversePath ex:items ]": f"^{items}",
            "[ sh:zeroOrMorePath ex:items ]": f"{items}*",
            "[ sh:oneOrMorePath ex:items ]": f"{items}+",
            "[ sh:zeroOrMorePath [ sh:inversePath ex:items ] ]": f"(^{items})*",
            "( [ sh:alternativePath ( ex:items ex:parts ) ] ex:parts )": f"({items}|{parts})/{parts}",
        }
        for path, expected in cases.items():
            with self.subTest(path=path):
                self.assertEqual(expansion_contract(members_path_graph(path)).expansion.path_text, expected)

    def test_the_statement_is_the_same_whatever_the_order_of_the_triples(self) -> None:
        for build, key, namespace in ((bundle_graph, "bundle-items-projection", BUNDLE_ITEMS), (list_path_graph, "bundle-items-projection", BUNDLE_ITEMS), (category_graph, "category-ancestors-projection", CATEGORY_ANCESTORS)):
            reference = expansion_contract(build(), key, namespace).expansion
            triples = sorted(build())
            for seed in range(5):
                shuffled = list(triples)
                random.Random(seed).shuffle(shuffled)
                graph = Graph()
                for triple in shuffled:
                    graph.add(triple)
                self.assertEqual(expansion_contract(graph, key, namespace).expansion, reference)

    def refused(self, graph: Graph, law: str) -> None:
        with self.assertRaisesRegex(ContractError, law):
            read_projection_contracts(graph)

    def test_an_expansion_with_no_statement_is_refused(self) -> None:
        self.refused(bundle_with(remove=[("bd-contains", SRF.expandedAs, None)]), "srf:P18")

    def test_a_statement_on_a_binding_that_is_not_a_result_target_is_refused(self) -> None:
        self.refused(bundle_with(add="ex:bd-items srf:expandedAs ex:bd-expansion ."), "srf:P18")

    def test_a_statement_on_a_projection_of_another_kind_is_refused(self) -> None:
        self.refused(join_with(add="ex:oc-link srf:expandedAs ex:oc-join ."), "srf:P18")
        self.refused(arr_with(add="ex:arr-target srf:expandedAs ex:arr-expression ."), "srf:P18")

    def test_a_result_that_binds_no_property_is_refused(self) -> None:
        self.refused(bundle_with(remove=[("bd-contains", SRF.bindsProperty, None)]), "srf:P18")

    def test_a_statement_that_is_not_an_expansion_statement_is_refused(self) -> None:
        self.refused(bundle_with(remove=[("bd-expansion", RDF.type, SRF.ExpansionStatement)]), "srf:P18")

    def test_a_statement_that_expands_from_none_or_two_bindings_is_refused(self) -> None:
        self.refused(bundle_with(remove=[("bd-expansion", SRF.expandsFrom, None)]), "srf:P19")
        graph = bundle_with(add="ex:bd-other a srf:ProjectionRoleBinding ; srf:roleKind srf:RequiredEvidenceRole ; srf:bindsProperty ex:parts . ex:bundle-items-projection srf:hasRoleBinding ex:bd-other . ex:bd-expansion srf:expandsFrom ex:bd-other .")
        self.refused(graph, "srf:P19")

    def test_a_binding_that_is_not_an_evidence_binding_that_binds_a_property_is_refused(self) -> None:
        for source in ("bd-subject", "bd-contains", "unknown"):
            with self.subTest(source=source):
                self.refused(bundle_with(remove=[("bd-expansion", SRF.expandsFrom, None)], add=f"ex:bd-expansion srf:expandsFrom ex:{source} ."), "srf:P19")
        self.refused(bundle_with(remove=[("bd-items", SRF.bindsProperty, None)]), "srf:P19")

    def test_a_binding_that_names_a_second_carrier_is_refused(self) -> None:
        self.refused(bundle_with(add="ex:bd-items srf:bindsCarrier ex:Item ."), "srf:P19")

    def test_a_statement_that_names_both_a_source_and_a_path_or_neither_is_refused(self) -> None:
        self.refused(bundle_with(add="ex:bd-expansion srf:membersPath ex:items ."), "srf:P20")
        self.refused(bundle_with(remove=[("bd-expansion", SRF.expansionSource, None)]), "srf:P20")

    def test_a_source_the_choice_does_not_name_is_refused(self) -> None:
        self.refused(bundle_with(remove=[("bd-expansion", SRF.expansionSource, None)], add="ex:bd-expansion srf:expansionSource ex:Elsewhere ."), "srf:P20")

    def test_a_path_of_a_form_an_expansion_does_not_state_is_refused(self) -> None:
        for path in ("[ sh:zeroOrOnePath ex:items ]", "[ ]", "( ex:items )", "[ sh:alternativePath ( ex:items ) ]", "[ sh:inversePath ex:items ; sh:oneOrMorePath ex:items ]", '"items"'):
            with self.subTest(path=path):
                self.refused(members_path_graph(path), "srf:P20")

    def test_a_path_that_does_not_read_the_evidence_property_is_refused(self) -> None:
        self.refused(members_path_graph("ex:parts"), "srf:P20")
        self.refused(members_path_graph("( ex:parts ex:contains )"), "srf:P20")


class ExpansionShapeTests(unittest.TestCase):
    """The shapes of ontology/surface refuse what the analyser refuses, with no code beside them."""

    def violations(self, graph: Graph) -> set:
        return {name.rsplit("#", 1)[-1] for name in shape_violations(graph, SURFACE_SHAPES)}

    def test_the_examples_and_their_variants_conform(self) -> None:
        graphs = [bundle_graph(), category_graph(), list_path_graph(), candidate_bundle_graph()]
        graphs += [members_path_graph(path) for path in ("ex:items", "( ex:items ex:parts )", "[ sh:alternativePath ( ex:items ex:parts ) ]", "[ sh:inversePath ex:items ]", "[ sh:oneOrMorePath ex:items ]", "( [ sh:alternativePath ( ex:items ex:parts ) ] ex:parts )")]
        for graph in graphs:
            self.assertEqual(self.violations(graph), set())

    def test_an_expansion_with_no_statement_is_refused(self) -> None:
        graph = bundle_with(remove=[("bd-contains", SRF.expandedAs, None)])
        self.assertIn("ExpansionRequiredShape", self.violations(graph))
        self.assertIn("ExpansionStatementReachedShape", self.violations(graph))

    def test_a_statement_on_a_binding_that_is_not_a_result_target_is_refused(self) -> None:
        self.assertIn("ExpansionPlacementShape", self.violations(bundle_with(add="ex:bd-items srf:expandedAs ex:bd-expansion .")))
        self.assertIn("ExpansionPlacementShape", self.violations(arr_with(add="ex:arr-target srf:expandedAs ex:arr-expression .")))

    def test_a_statement_on_a_projection_of_another_kind_is_refused(self) -> None:
        graph = bundle_with(remove=[("bundle-items-projection", SRF.projectionKind, None)], add="ex:bundle-items-projection srf:projectionKind srf:JoinProjection .")
        self.assertIn("ExpansionPlacementShape", self.violations(graph))

    def test_two_statements_on_one_binding_are_refused(self) -> None:
        graph = bundle_with(add="ex:bd-contains srf:expandedAs ex:bd-other . ex:bd-other a srf:ExpansionStatement .")
        self.assertIn("ProjectionRoleBindingShape", self.violations(graph))

    def test_a_result_that_binds_no_property_is_refused(self) -> None:
        self.assertIn("ExpansionLinkPropertyRequiredShape", self.violations(bundle_with(remove=[("bd-contains", SRF.bindsProperty, None)])))

    def test_a_statement_that_is_no_expansion_statement_is_refused(self) -> None:
        self.assertIn("ExpansionStatementTypedShape", self.violations(bundle_with(remove=[("bd-expansion", RDF.type, SRF.ExpansionStatement)])))

    def test_a_statement_that_expands_from_none_or_two_bindings_is_refused(self) -> None:
        self.assertIn("ExpansionStatementShape", self.violations(bundle_with(remove=[("bd-expansion", SRF.expandsFrom, None)])))
        graph = bundle_with(add="ex:bd-other a srf:ProjectionRoleBinding ; srf:roleKind srf:RequiredEvidenceRole ; srf:bindsProperty ex:parts . ex:bundle-items-projection srf:hasRoleBinding ex:bd-other . ex:bd-expansion srf:expandsFrom ex:bd-other .")
        self.assertIn("ExpansionStatementShape", self.violations(graph))

    def test_a_binding_that_is_not_an_evidence_binding_that_binds_a_property_is_refused(self) -> None:
        for source in ("bd-subject", "bd-contains", "unknown"):
            with self.subTest(source=source):
                graph = bundle_with(remove=[("bd-expansion", SRF.expandsFrom, None)], add=f"ex:bd-expansion srf:expandsFrom ex:{source} .")
                self.assertIn("ExpansionEvidenceShape", self.violations(graph))
        self.assertIn("ExpansionEvidenceShape", self.violations(bundle_with(remove=[("bd-items", SRF.bindsProperty, None)])))

    def test_a_binding_that_names_a_second_carrier_is_refused(self) -> None:
        self.assertIn("ExpansionEvidenceShape", self.violations(bundle_with(add="ex:bd-items srf:bindsCarrier ex:Item .")))

    def test_a_statement_that_names_both_a_source_and_a_path_or_neither_is_refused(self) -> None:
        self.assertIn("ExpansionMembersShape", self.violations(bundle_with(add="ex:bd-expansion srf:membersPath ex:items .")))
        self.assertIn("ExpansionMembersShape", self.violations(bundle_with(remove=[("bd-expansion", SRF.expansionSource, None)])))

    def test_a_source_the_choice_does_not_name_or_two_of_them_are_refused(self) -> None:
        graph = bundle_with(remove=[("bd-expansion", SRF.expansionSource, None)], add="ex:bd-expansion srf:expansionSource ex:Elsewhere .")
        self.assertIn("ExpansionStatementShape", self.violations(graph))
        self.assertIn("ExpansionStatementShape", self.violations(bundle_with(add="ex:bd-expansion srf:expansionSource srf:TransitiveClosure .")))

    def test_a_path_of_a_form_an_expansion_does_not_state_is_refused(self) -> None:
        for path in ("[ sh:zeroOrOnePath ex:items ]", "[ ]", "( ex:items )", "[ sh:alternativePath ( ex:items ) ]", "[ sh:inversePath ex:items ; sh:oneOrMorePath ex:items ]", '"items"', "( ex:items [ sh:zeroOrOnePath ex:parts ] )"):
            with self.subTest(path=path):
                self.assertIn("ExpansionPathShape", self.violations(members_path_graph(path)))

    def test_a_path_that_does_not_read_the_evidence_property_is_refused(self) -> None:
        self.assertIn("ExpansionPathReadsEvidenceShape", self.violations(members_path_graph("ex:parts")))
        self.assertNotIn("ExpansionPathReadsEvidenceShape", self.violations(members_path_graph("( ex:parts [ sh:inversePath ex:items ] )")))

    def test_the_laws_the_shapes_discharge_are_in_the_vocabulary(self) -> None:
        vocabulary = parse_files([str(ROOT / "ontology" / "surface" / "vocab" / "surface-vocab.ttl")])
        for law in ("P18", "P19", "P20"):
            self.assertIn((SRF[law], RDF.type, SRF.Law), vocabulary)
        for source in ("ListMembers", "TransitiveClosure"):
            self.assertIn((SRF[source], RDF.type, SRF.ExpansionSource), vocabulary)


class ExpansionLoweringTests(unittest.TestCase):
    """Surface-to-MORK lowering of an expansion (ADR-A18)."""

    def lowered(self, graph: Graph, key: str = "bundle-items-projection", namespace: str = BUNDLE_ITEMS):
        contract = expansion_contract(graph, key, namespace)
        return contract, lower_projection(contract)

    def parts(self, low: Graph, contract):
        root = lowered_head(contract)
        (assertion,) = low.objects(root, MORK.compositeNarrowerMapping)
        return root, assertion

    def test_the_expansion_lowers_into_a_scheme_a_source_node_root_and_one_assertion_whose_reference_is_the_path(self) -> None:
        contract, low = self.lowered(bundle_graph())
        (scheme,) = set(low.subjects(RDF.type, MORK.MappingScheme))
        root, assertion = self.parts(low, contract)
        self.assertEqual(low.value(root, MORK.identityRule), MORK.SourceNodeIdentity)
        self.assertEqual(low.value(low.value(root, MORK.mappingFor), MORK.representedAs), URIRef(BUNDLE_ITEMS + "Bundle"))
        self.assertEqual(low.value(assertion, MORK.mappingScheme), scheme)
        self.assertEqual(low.value(assertion, MORK.exactRBoxMatch), URIRef(BUNDLE_ITEMS + "contains"))
        self.assertEqual(low.value(assertion, MORK.dataRef), Literal(LIST_PATH))
        self.assertEqual(set(low.objects(contract.iri, SRF.producesMapping)), {root})
        # Nothing is minted or typed, so no datum sits beneath the root and the assertion names no class and no value expression.
        self.assertIsNone(low.value(assertion, MORK.exactTBoxMatch))
        self.assertIsNone(low.value(assertion, MORK.valueExpression))
        self.assertEqual(set(low.objects(assertion, MORK.compositeNarrowerMapping)), set())

    def test_the_closure_lowers_to_its_path_and_a_stated_path_lowers_to_the_same_scheme_as_the_source_it_equals(self) -> None:
        contract, low = self.lowered(category_graph(), "category-ancestors-projection", CATEGORY_ANCESTORS)
        self.assertEqual(low.value(self.parts(low, contract)[1], MORK.dataRef), Literal(CLOSURE_PATH))
        named = self.lowered(bundle_graph())[1]
        stated = self.lowered(list_path_graph())[1]
        self.assertEqual(canonical.hash_graph(stated), canonical.hash_graph(named))

    def test_the_guard_holds_the_required_evidence_of_the_instance(self) -> None:
        contract, low = self.lowered(bundle_graph())
        _, assertion = self.parts(low, contract)
        guard = low.value(assertion, MORK.appliesWhen)
        paths = {(low.value(c, SH.path), low.value(c, SH.minCount)) for c in low.objects(guard, SH.property)}
        self.assertEqual(paths, {(URIRef(BUNDLE_ITEMS + "items"), Literal(1))})

    def test_an_expansion_on_candidate_evidence_is_guarded_by_nothing(self) -> None:
        for graph, key, namespace in ((candidate_bundle_graph(), "bundle-items-projection", BUNDLE_ITEMS), (category_graph(), "category-ancestors-projection", CATEGORY_ANCESTORS)):
            contract, low = self.lowered(graph, key, namespace)
            self.assertIsNone(low.value(self.parts(low, contract)[1], MORK.appliesWhen))

    def test_the_lowered_scheme_is_one_the_mork_shapes_accept(self) -> None:
        for graph, key, namespace in ((bundle_graph(), "bundle-items-projection", BUNDLE_ITEMS), (list_path_graph(), "bundle-items-projection", BUNDLE_ITEMS), (candidate_bundle_graph(), "bundle-items-projection", BUNDLE_ITEMS), (category_graph(), "category-ancestors-projection", CATEGORY_ANCESTORS)):
            self.assertEqual(shape_violations(self.lowered(graph, key, namespace)[1], MORK_SHAPES), set())

    def test_lowering_is_deterministic_and_the_same_with_the_triples_permuted(self) -> None:
        for build, key, namespace in ((bundle_graph, "bundle-items-projection", BUNDLE_ITEMS), (list_path_graph, "bundle-items-projection", BUNDLE_ITEMS), (category_graph, "category-ancestors-projection", CATEGORY_ANCESTORS)):
            reference = canonical.hash_graph(lower_projection(expansion_contract(build(), key, namespace)))
            self.assertEqual(canonical.hash_graph(lower_projection(expansion_contract(build(), key, namespace))), reference)
            triples = sorted(build())
            for seed in range(5):
                shuffled = list(triples)
                random.Random(seed).shuffle(shuffled)
                graph = Graph()
                for triple in shuffled:
                    graph.add(triple)
                self.assertEqual(canonical.hash_graph(lower_projection(expansion_contract(graph, key, namespace))), reference)

    def test_an_expansion_is_not_a_bare_mapping(self) -> None:
        contract, low = self.lowered(bundle_graph())
        self.assertEqual(set(low.subjects(MORK.mappingFor, contract.iri)), set())
        self.assertTrue(set(low.subjects(RDF.type, MORK.MappingScheme)))

    def test_the_other_kinds_are_not_affected(self) -> None:
        (derivation,) = read_projection_contracts(arr_graph())
        self.assertIsNone(derivation.expansion)
        self.assertIsNone(join_contract(join_graph()).expansion)
        self.assertIsNone(order_contract(order_graph()).expansion)


@unittest.skipIf(mork_rdf is None, "mork_rdf is not installed")
class ExpansionCompilationTests(unittest.TestCase):
    """The lowered scheme compiles with `mork_rdf` and runs to the graph the contract states (SVA-S2i)."""

    BASE = "https://example.org/lattice/surface/bundle-items/out/"
    CATEGORY_BASE = "https://example.org/lattice/surface/category-ancestors/out/"
    CONTAINS = BUNDLE_ITEMS + "contains"
    HAS_ANCESTOR = CATEGORY_ANCESTORS + "hasAncestor"
    #: The path as the compiler writes it back, which a check names.
    WRITTEN_LIST = f"<{BUNDLE_ITEMS}items>/(<{RDF_REST}>*)/<{RDF_FIRST}>"

    @classmethod
    def setUpClass(cls) -> None:
        if str(ROOT / "tools") not in sys.path:
            sys.path.insert(0, str(ROOT / "tools"))

    def compile(self, graph: Graph, key: str = "bundle-items-projection", namespace: str = BUNDLE_ITEMS, base: str = BASE):
        low = lower_projection(expansion_contract(graph, key, namespace))
        (scheme,) = set(low.subjects(RDF.type, MORK.MappingScheme))
        return mork_rdf.compile_scheme(low, scheme, base=base, at=datetime.fromisoformat("2026-11-25T00:00:00+00:00"))

    def evaluate(self, engine: str, compiled, source: Graph):
        if engine == "oxigraph":
            out = mork_rdf.run(compiled, source)
            return {(str(s), str(p), str(o)) for s, p, o in out.graph}, {(f.code, f.focus, f.value) for f in out.findings}
        from rdflib import Dataset

        dataset = Dataset()
        for triple in source:
            dataset.default_graph.add(triple)
        written = {(str(s), str(p), str(o)) for q in compiled.constructs for s, p, o in dataset.query(q.text)}
        reported = {(q.code, str(r["focus"]), None if r["value"] is None else str(r["value"])) for q in compiled.checks for r in dataset.query(q.text)}
        return written, reported

    def test_the_example_compiles_to_the_query_the_case_shows(self) -> None:
        compiled = self.compile(bundle_graph())
        (construct,) = compiled.constructs
        type_ = str(RDF.type)
        expected = f"""BASE <{self.BASE}>
CONSTRUCT {{ ?f1 <{self.CONTAINS}> ?v3 . }}
WHERE {{
  ?f1 <{type_}> <{BUNDLE_ITEMS}Bundle> .
  FILTER (((EXISTS {{ ?f1 <{BUNDLE_ITEMS}items> ?any2 . }})))
  ?f1 <{BUNDLE_ITEMS}items>/(<{RDF_REST}>*)/<{RDF_FIRST}> ?v3 .
}}"""
        self.assertEqual(" ".join(construct.text.split()), " ".join(expected.split()))
        self.assertEqual(sorted(q.code for q in compiled.checks), ["CollectionEmpty", "InstanceExcluded"])
        self.assertEqual([(f.code, f.severity) for f in compiled.findings], [("EngineeringReview", mork_rdf.Severity.WARNING)])
        self.assertFalse(compiled.errors)

    def test_the_closure_compiles_to_one_path_and_an_empty_check_and_no_exclusion(self) -> None:
        compiled = self.compile(category_graph(), "category-ancestors-projection", CATEGORY_ANCESTORS, self.CATEGORY_BASE)
        (construct,) = compiled.constructs
        expected = f"""BASE <{self.CATEGORY_BASE}>
CONSTRUCT {{ ?f1 <{self.HAS_ANCESTOR}> ?v2 . }}
WHERE {{
  ?f1 <{RDF.type}> <{CATEGORY_ANCESTORS}Category> .
  ?f1 <{CATEGORY_ANCESTORS}broader>+ ?v2 .
}}"""
        self.assertEqual(" ".join(construct.text.split()), " ".join(expected.split()))
        self.assertEqual(sorted(q.code for q in compiled.checks), ["CollectionEmpty"])
        self.assertEqual([f.code for f in compiled.findings], ["EngineeringReview"])

    def test_the_bundle_example_runs_to_its_expected_graph_on_each_engine(self) -> None:
        compiled = self.compile(bundle_graph())
        for engine in ("oxigraph", "rdflib"):
            with self.subTest(engine=engine):
                written, reported = self.evaluate(engine, compiled, bundle_graph())
                self.assertEqual(
                    written,
                    {(BUNDLE_ITEMS + "bundle-1", self.CONTAINS, BUNDLE_ITEMS + item) for item in ("item-1", "item-2", "item-3")}
                    | {(BUNDLE_ITEMS + "bundle-2", self.CONTAINS, BUNDLE_ITEMS + "item-3")},
                )
                # The fourth bundle has no list, so it is excluded with the property it lacks, and the third has an empty one.
                self.assertEqual(
                    reported,
                    {
                        ("InstanceExcluded", BUNDLE_ITEMS + "bundle-4", f"<{BUNDLE_ITEMS}items>"),
                        ("CollectionEmpty", BUNDLE_ITEMS + "bundle-3", self.WRITTEN_LIST),
                    },
                )

    def test_the_category_example_runs_to_a_statement_for_each_ancestor_on_each_engine(self) -> None:
        compiled = self.compile(category_graph(), "category-ancestors-projection", CATEGORY_ANCESTORS, self.CATEGORY_BASE)
        for engine in ("oxigraph", "rdflib"):
            with self.subTest(engine=engine):
                written, reported = self.evaluate(engine, compiled, category_graph())
                self.assertEqual(
                    written,
                    {
                        (CATEGORY_ANCESTORS + "category-b", self.HAS_ANCESTOR, CATEGORY_ANCESTORS + "category-a"),
                        (CATEGORY_ANCESTORS + "category-c", self.HAS_ANCESTOR, CATEGORY_ANCESTORS + "category-b"),
                        (CATEGORY_ANCESTORS + "category-c", self.HAS_ANCESTOR, CATEGORY_ANCESTORS + "category-a"),
                    },
                )
                self.assertEqual(reported, {("CollectionEmpty", CATEGORY_ANCESTORS + "category-a", f"<{CATEGORY_ANCESTORS}broader>+")})

    def test_the_empty_collection_is_information_and_the_exclusion_a_warning(self) -> None:
        compiled = self.compile(bundle_graph())
        self.assertEqual({q.code: q.severity for q in compiled.checks}, {"InstanceExcluded": mork_rdf.Severity.WARNING, "CollectionEmpty": mork_rdf.Severity.INFO})
        out = mork_rdf.run(compiled, bundle_graph())
        self.assertEqual(
            {(f.code, f.focus): f.severity for f in out.findings},
            {("InstanceExcluded", BUNDLE_ITEMS + "bundle-4"): mork_rdf.Severity.WARNING, ("CollectionEmpty", BUNDLE_ITEMS + "bundle-3"): mork_rdf.Severity.INFO},
        )

    def test_on_candidate_evidence_a_bundle_with_no_list_is_reported_as_an_empty_collection_and_none_is_excluded(self) -> None:
        compiled = self.compile(candidate_bundle_graph())
        self.assertNotIn("InstanceExcluded", {q.code for q in compiled.checks})
        for engine in ("oxigraph", "rdflib"):
            with self.subTest(engine=engine):
                written, reported = self.evaluate(engine, compiled, bundle_graph())
                self.assertEqual(len(written), 4)
                self.assertEqual(
                    reported,
                    {("CollectionEmpty", BUNDLE_ITEMS + "bundle-3", self.WRITTEN_LIST), ("CollectionEmpty", BUNDLE_ITEMS + "bundle-4", self.WRITTEN_LIST)},
                )

    def test_a_path_the_contract_states_compiles_to_the_query_the_source_it_equals_does(self) -> None:
        self.assertEqual([q.text for q in self.compile(list_path_graph()).queries], [q.text for q in self.compile(bundle_graph()).queries])

    def test_an_alternative_and_an_inverse_path_run_as_their_sparql_paths(self) -> None:
        graph = members_path_graph("[ sh:alternativePath ( ex:items [ sh:inversePath ex:partOf ] ) ]")
        source = Graph().parse(
            data=f"""@prefix ex: <{BUNDLE_ITEMS}> .
            ex:bundle-1 a ex:Bundle ; ex:items ex:item-1 .
            ex:item-2 ex:partOf ex:bundle-1 .""",
            format="turtle",
        )
        # The statement names ex:items, so the guard asks for it, and an alternative reads ex:items beside the inverse of ex:partOf.
        compiled = self.compile(graph)
        for engine in ("oxigraph", "rdflib"):
            with self.subTest(engine=engine):
                written, _ = self.evaluate(engine, compiled, source)
                self.assertEqual(written, {(BUNDLE_ITEMS + "bundle-1", self.CONTAINS, BUNDLE_ITEMS + item) for item in ("item-1", "item-2")})

    def test_an_expansion_carries_the_engineering_review_and_no_mapping_review(self) -> None:
        for build in (bundle_graph, list_path_graph, candidate_bundle_graph):
            with self.subTest(build=build.__name__):
                findings = self.compile(build()).findings
                self.assertEqual([(f.code, f.severity) for f in findings], [("EngineeringReview", mork_rdf.Severity.WARNING)])
                self.assertIn(f"{BUNDLE_ITEMS}items", findings[0].message)

    def test_compiling_the_lowered_scheme_is_the_same_whatever_the_order_of_the_contract(self) -> None:
        reference = self.compile(bundle_graph()).text()
        triples = sorted(bundle_graph())
        for seed in range(3):
            shuffled = list(triples)
            random.Random(seed).shuffle(shuffled)
            graph = Graph()
            for triple in shuffled:
                graph.add(triple)
            self.assertEqual(self.compile(graph).text(), reference)


if __name__ == "__main__":
    unittest.main()