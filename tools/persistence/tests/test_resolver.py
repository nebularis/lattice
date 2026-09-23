# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""The precedence and resolution algorithm (sketch §3.4)."""

from __future__ import annotations

from rdflib import URIRef

from persistence import capability, resolver
from persistence.model import ProfileAmbiguityError
from persistence.scopes import Target, discover_targets

LENDING = "https://example.org/lending#"


def _target(cls_local: str, deployment: str | None = None) -> Target:
    cls = URIRef(LENDING + cls_local)
    dep = URIRef(LENDING + deployment) if deployment else None
    return Target(cls=cls, deployment=dep)


class TestBaselineDefaults:
    def test_class_with_no_matching_scope_gets_platform_baseline(self, example):
        g = example("baseline-single-class.ttl")
        target = _target("SomeUnconfiguredClass")
        rd = resolver.resolve_dimension(g, target, "concurrencyProfile", None)
        assert rd.value == "ProvidedConcurrency"
        assert rd.won_by is None
        assert rd.candidate_count == 0


class TestEpochGuardScope:
    """persistence-compiler-iri-sync Slice 1 (2026-09-23): dal:EpochProfile's
    dal:epochGuardScope, added to ontology/persistence by commit c276afb."""

    def test_baseline_default_is_row_level_guard_only(self, example):
        g = example("baseline-single-class.ttl")
        target = _target("LoanApplication")
        rd = resolver.resolve_dimension(g, target, "epochGuardScope", None)
        assert rd.value == "RowLevelGuardOnly"
        assert rd.won_by is None
        assert rd.candidate_count == 0

    def test_explicit_dataset_level_guard_resolves_with_authority_extra(self, example):
        g = example("epoch-dataset-level-guard.ttl")
        target = _target("LoanApplication")
        rd = resolver.resolve_dimension(g, target, "epochGuardScope", None)
        assert str(rd.value).rsplit("#", 1)[-1] == "DatasetLevelGuard"
        assert rd.won_by == LENDING + "LoanApplicationEpoch"
        assert str(rd.extra["epochAuthority"]).rsplit("#", 1)[-1] == "ExternalHighWaterMark"

    def test_explicit_row_level_guard_only_resolves(self, example):
        g = example("warning-epoch-unsafe-restore.ttl")
        target = _target("CreditLine")
        rd = resolver.resolve_dimension(g, target, "epochGuardScope", None)
        assert str(rd.value).rsplit("#", 1)[-1] == "RowLevelGuardOnly"
        assert str(rd.extra["epochAuthority"]).rsplit("#", 1)[-1] == "StoreLocalEpoch"


class TestSingleClassResolution:
    def test_resolves_every_dimension(self, example):
        g = example("baseline-single-class.ttl")
        target = _target("LoanApplication")
        for dim, expected_local in [
            ("aggregateBoundary", "NamedGraphBoundary"),
            ("concurrencyProfile", "Optimistic"),
            ("orderingGrain", "EventGrain"),
            ("receiptModel", "PatchLog"),
            ("metaTopology", "SharedSharded"),
        ]:
            rd = resolver.resolve_dimension(g, target, dim, None)
            assert str(rd.value).rsplit("#", 1)[-1] == expected_local, dim
            assert rd.won_by == LENDING + "LoanApplicationStrongProfile"

    def test_uniqueness_is_many_valued(self, example):
        g = example("baseline-single-class.ttl")
        target = _target("LoanApplication")
        constraints = resolver.resolve_uniqueness(g, target)
        assert len(constraints) == 1
        assert constraints[0]["constraintId"] == "loan-application-number-per-branch"


class TestSharedClassDeployments:
    """sketch §3.4.3's worked conflict: lending and credit each deploy
    beh:Behaviour into their own graph family."""

    BEH = "https://www.nebularis.org/neuro-semantic/lattice/behaviour#Behaviour"

    def test_discovers_one_target_per_deployment_plus_fallback(self, example):
        g = example("lending-credit-shared-class.ttl")
        targets = discover_targets(g, classes={URIRef(self.BEH)})
        assert len(targets) == 3
        deployments = {t.deployment for t in targets}
        assert None in deployments
        assert URIRef(LENDING + "LendingBehaviourGraphs") in deployments
        assert URIRef(LENDING + "CreditBehaviourGraphs") in deployments

    def test_lending_deployment_gets_optimistic_credit_gets_provided(self, example):
        g = example("lending-credit-shared-class.ttl")
        lending = Target(cls=URIRef(self.BEH), deployment=URIRef(LENDING + "LendingBehaviourGraphs"))
        credit = Target(cls=URIRef(self.BEH), deployment=URIRef(LENDING + "CreditBehaviourGraphs"))
        fallback = Target(cls=URIRef(self.BEH), deployment=None)

        assert resolver.resolve_dimension(g, lending, "concurrencyProfile", None).value.endswith("Optimistic")
        assert resolver.resolve_dimension(g, credit, "concurrencyProfile", None).value.endswith("ProvidedConcurrency")
        assert resolver.resolve_dimension(g, fallback, "concurrencyProfile", None).value.endswith("ProvidedConcurrency")

    def test_reasoning_dependent_scope_wins_receipt_model_without_a_spec(self, example):
        g = example("lending-credit-shared-class.ttl")
        lending = Target(cls=URIRef(self.BEH), deployment=URIRef(LENDING + "LendingBehaviourGraphs"))
        rd = resolver.resolve_dimension(g, lending, "receiptModel", None)
        assert rd.value.endswith("SnapshotPerRevision")
        assert rd.won_by_requires_reasoning is True

    def test_capability_spec_without_reasoning_drops_the_equivalent_class_candidate(self, example):
        from rdflib import RDF, Literal as RdfLiteral
        from persistence.namespaces import DAL

        g = example("lending-credit-shared-class.ttl")
        env = URIRef(LENDING + "NoReasoningEnv")
        g.add((env, RDF.type, DAL.CapabilitySpec))
        g.add((env, DAL.providesReasoning, RdfLiteral(False)))

        lending = Target(cls=URIRef(self.BEH), deployment=URIRef(LENDING + "LendingBehaviourGraphs"))
        spec = capability.load_capability_spec(g, lending)
        rd = resolver.resolve_dimension(g, lending, "receiptModel", spec)
        assert rd.value.endswith("PatchLog")  # falls back to lending's own priority-10 candidate
        assert str(LENDING + "HighValueBehaviourEquivalence") in rd.dropped_for_reasoning


class TestAmbiguity:
    def test_two_equal_priority_non_reasoning_candidates_raise(self, spec_graph):
        from rdflib import Namespace, RDF, Literal as RdfLiteral
        from persistence.namespaces import DAL

        g = spec_graph + spec_graph  # copy, mutated below
        ex = Namespace(LENDING)
        cls = ex.Thing

        g.add((ex.ScopeA, RDF.type, DAL.ClassScope))
        g.add((ex.ScopeA, DAL.targetClass, cls))
        g.add((ex.ScopeA, DAL.priority, RdfLiteral(5)))
        g.add((ex.ProfileA, RDF.type, DAL.ConcurrencyProfile))
        g.add((ex.ProfileA, DAL.appliesTo, ex.ScopeA))
        g.add((ex.ProfileA, DAL.concurrencyProfile, DAL.Optimistic))

        g.add((ex.ScopeB, RDF.type, DAL.ClassScope))
        g.add((ex.ScopeB, DAL.targetClass, cls))
        g.add((ex.ScopeB, DAL.priority, RdfLiteral(5)))
        g.add((ex.ProfileB, RDF.type, DAL.ConcurrencyProfile))
        g.add((ex.ProfileB, DAL.appliesTo, ex.ScopeB))
        g.add((ex.ProfileB, DAL.concurrencyProfile, DAL.ProvidedConcurrency))

        target = Target(cls=cls, deployment=None)
        try:
            resolver.resolve_dimension(g, target, "concurrencyProfile", None)
            assert False, "expected ProfileAmbiguityError"
        except ProfileAmbiguityError as e:
            assert e.dimension == "concurrencyProfile"
