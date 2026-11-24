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

    def test_a_bare_mapping_names_its_contract_by_producesMapping_too(self) -> None:
        graph = Graph().parse(data=LoweringDependencyTests.SCENARIO, format="turtle")
        (contract,) = read_projection_contracts(graph)
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
        graph = Graph().parse(data=LoweringDependencyTests.SCENARIO, format="turtle")
        (contract,) = read_projection_contracts(graph)
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
        ex:target a srf:ProjectionRoleBinding ; srf:roleKind srf:ResultTargetRole .

        ex:projection a srf:ProjectionContract ;
            srf:contractKey "eligibility-check" ; srf:carrier ex:Applicant ;
            srf:projectionKind srf:JoinProjection ;
            srf:hasRoleBinding ex:subject, ex:evidence, ex:household-evidence, ex:target ;
            srf:targetNamespace "https://example.org/exec#"^^xsd:anyURI ;
            srf:realisationMode srf:Materialised ;
            srf:surfaceProfile ex:profile .
    """
    DEP = "https://example.org/lattice/surface/dep#"

    def setUp(self) -> None:
        self.graph = Graph().parse(data=self.SCENARIO, format="turtle")

    def _mapping_for(self, combined: Graph, contract_iri: str) -> URIRef:
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



if __name__ == "__main__":
    unittest.main()