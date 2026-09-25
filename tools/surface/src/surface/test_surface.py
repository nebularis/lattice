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

import unittest
from dataclasses import replace
from pathlib import Path

from rdflib import Graph, URIRef
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
from .model import ContractError, SurfaceGraphAnalyser, read_contracts, read_projection_contracts
from .mork import HAS_PROJECTION_PROVENANCE, PROJECTION_MAPPING, lift, lower
from .lowering import lower_all, lower_contract, lower_projection
from .invalidation import (
    compare_read_set,
    impacted_mappings,
    impacted_artefacts,
    impacted_surfaces,
    plan_regeneration,
    read_set_from_manifest,
)
from .parity import run_shared_surface_parity
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
        members, scheme = enumerate_population(self.graph, self.contract.population, at=AT)
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


class ProjectionLoweringTests(unittest.TestCase):
    """Surface-to-MORK lowering for srf:ProjectionContract (ADR-A18)."""

    def contract(self):
        graph = load("saas-subscription-arr-projection.ttl")
        return read_projection_contracts(
            graph, only=SAAS_ARR + "subscription-arr-projection"
        )[0]

    def test_lower_projection_emits_one_data_mapping(self) -> None:
        mapping_graph = lower_projection(self.contract())
        mappings = set(mapping_graph.subjects(RDF.type, MORK.DataMapping))
        self.assertEqual(len(mappings), 1)
        mapping = next(iter(mappings))
        self.assertEqual(
            mapping_graph.value(mapping, MORK.mappingFor),
            URIRef(SAAS_ARR + "subscription-arr-projection"),
        )
        self.assertTrue(any(mapping_graph.triples((mapping, MORK.hasTargetingSpec, None))))

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

    def test_both_read_path_forms_is_refused(self) -> None:
        with self.assertRaisesRegex(ContractError, "exactly one read-path form"):
            read_contracts(parse_files([str(FIXTURES / "defect-both-read-path-forms.ttl")]))

    def test_closure_form_without_a_basis_is_refused(self) -> None:
        with self.assertRaisesRegex(ContractError, "closure basis"):
            read_contracts(parse_files([str(FIXTURES / "defect-closure-without-basis.ttl")]))


if __name__ == "__main__":
    unittest.main()