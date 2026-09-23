# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""persistence-compiler-iri-sync Slice 2: the extension properties on
dal:AggregateBoundaryProfile, dal:ConcurrencyProfile, dal:OrderingProfile,
dal:ReceiptProfile and dal:MetaTopologyProfile. Each is its own resolved
dimension (plan decision 1), with explicit baseline defaults (decision 2),
and declared shard counts warn rather than vanish (decision 3)."""

from __future__ import annotations

from pathlib import Path

import pytest
from rdflib import Graph, Literal as RdfLiteral, URIRef

from persistence import resolver
from persistence.compiler import CompileError, compile_to_graph
from persistence.model import BASELINE_DEFAULTS, DIMENSIONS, CrossAxisViolation
from persistence.namespaces import DAL
from persistence.scopes import Target
from persistence.validator import check_cross_axis

REPO_ROOT = Path(__file__).resolve().parents[3]
SPEC_TTL = REPO_ROOT / "ontology" / "persistence" / "spec" / "persistence.ttl"
EXAMPLES_DIR = REPO_ROOT / "ontology" / "persistence" / "examples"

PREFIXES = """
@prefix dal: <https://www.nebularis.org/neuro-semantic/lattice/persistence#> .
@prefix ex:  <https://example.org/lending#> .
"""
CLS = URIRef("https://example.org/lending#Thing")

BASE = PREFIXES + """
ex:ThingScope a dal:ClassScope ; dal:priority 10 ; dal:targetClass ex:Thing .
ex:ThingProfile a dal:DataAccessProfile ;
    dal:appliesTo ex:ThingScope ;
    dal:strategy dal:NamedGraphBoundary ;
    dal:graphIriTemplate "urn:g:thing/{id}" ;
    dal:concurrencyProfile dal:Optimistic ;
    dal:orderingGrain dal:EventGrain ;
    dal:receiptModel dal:PatchLog ;
    dal:metaTopology dal:SharedSharded .
"""


def _graph(extra: str = "", base: str = BASE) -> Graph:
    g = Graph()
    g.parse(SPEC_TTL, format="turtle")
    g.parse(data=base + extra, format="turtle")
    return g


def _dims(g: Graph) -> dict:
    target = Target(CLS)
    return {d: resolver.resolve_dimension(g, target, d, None) for d in DIMENSIONS}


def _local(v) -> str | None:
    return None if v is None else str(v).rsplit("#", 1)[-1]


def _kinds(extra: str = "", base: str = BASE) -> set[str]:
    g = _graph(extra, base)
    return {d.kind for d in check_cross_axis(g, Target(CLS), _dims(g), [])}


# ---- Decision 1: per-property resolution -----------------------------------------------------


def test_property_on_its_own_profile_node_is_resolved():
    g = _graph("ex:Etag a dal:DataAccessProfile ; dal:appliesTo ex:ThingScope ; dal:etagForm dal:WeakEtag .")
    rd = _dims(g)["etagForm"]
    assert _local(rd.value) == "WeakEtag"
    assert rd.won_by == "https://example.org/lending#Etag"


def test_property_on_a_lower_priority_node_is_still_resolved():
    extra = """
ex:Wide a dal:NamespaceScope ; dal:priority 1 ; dal:iriPrefix "https://example.org/lending#" .
ex:WideConcurrency a dal:DataAccessProfile ; dal:appliesTo ex:Wide ; dal:deadlockPolicy dal:PartitionedWriter .
"""
    assert _local(_dims(_graph(extra))["deadlockPolicy"].value) == "PartitionedWriter"


def test_higher_priority_node_wins_per_property():
    extra = """
ex:Wide a dal:NamespaceScope ; dal:priority 1 ; dal:iriPrefix "https://example.org/lending#" .
ex:WideOrdering a dal:DataAccessProfile ; dal:appliesTo ex:Wide ; dal:contiguityCheckMode dal:AdvisoryContiguityCheck .
ex:NarrowOrdering a dal:DataAccessProfile ; dal:appliesTo ex:ThingScope ; dal:contiguityCheckMode dal:BlockingContiguityCheck .
"""
    assert _local(_dims(_graph(extra))["contiguityCheckMode"].value) == "BlockingContiguityCheck"


def test_two_equal_priority_declarations_are_ambiguous():
    extra = """
ex:A a dal:DataAccessProfile ; dal:appliesTo ex:ThingScope ; dal:retentionMode dal:PrefixOnlyRetention .
ex:B a dal:DataAccessProfile ; dal:appliesTo ex:ThingScope ; dal:retentionMode dal:BucketAnyRetention .
"""
    with pytest.raises(CompileError):
        compile_to_graph(_graph(extra), classes={CLS})


def test_literal_dimensions_are_emitted_with_resolved_literal():
    g = Graph()
    g.parse(SPEC_TTL, format="turtle")
    g.parse(EXAMPLES_DIR / "extension-properties.ttl", format="turtle")
    out, _ = compile_to_graph(g, classes={URIRef("https://example.org/lending#Facility")})
    by_dim = {str(out.value(n, DAL.dimension)): n for n in out.subjects(DAL.dimension, None)}
    assert out.value(by_dim["lagWindowMillis"], DAL.resolvedLiteral).toPython() == 30000
    assert str(out.value(by_dim["registryGraph"], DAL.resolvedLiteral)) == "urn:g:registry/facility"
    assert out.value(by_dim["lagWindowMillis"], DAL.resolvedValue) is None
    assert _local(out.value(by_dim["firstWrite"], DAL.resolvedValue)) == "PreCreatedRow"


# ---- Decision 2: baseline defaults -----------------------------------------------------------


@pytest.mark.parametrize(
    "dimension,expected",
    [
        ("firstWrite", "AbsentRow"),
        ("etagForm", "StrongEtag"),
        ("etagRepresentation", "SingleRepresentation"),
        ("deadlockPolicy", "EngineDetectAndRetry"),
        ("contiguityCheckMode", "BlockingContiguityCheck"),
        ("retentionMode", "PrefixOnlyRetention"),
    ],
)
def test_baseline_default(dimension, expected):
    rd = _dims(_graph())[dimension]
    assert rd.value == expected == BASELINE_DEFAULTS[dimension]
    assert rd.candidate_count == 0


@pytest.mark.parametrize(
    "dimension",
    ["globalReadStrategy", "lagWindowMillis", "asOfFloorSource", "txnShards", "logShards", "keyShards", "registryGraph"],
)
def test_no_default_where_absence_is_meaningful(dimension):
    assert _dims(_graph())[dimension].value is None


# ---- Checks: one positive and one negative per check ------------------------------------------


def test_weak_etag_with_optimistic_warns_even_across_nodes():
    assert "WeakEtagCas" in _kinds("ex:E a dal:DataAccessProfile ; dal:appliesTo ex:ThingScope ; dal:etagForm dal:WeakEtag .")
    assert "WeakEtagCas" not in _kinds()


def test_no_global_read_warns():
    assert "NoGlobalRead" in _kinds("ex:O a dal:DataAccessProfile ; dal:appliesTo ex:ThingScope ; dal:globalReadStrategy dal:NoGlobalRead .")
    assert "NoGlobalRead" not in _kinds()


def test_dataset_tier_without_global_read_warns():
    base_with_tier = BASE.replace("dal:orderingGrain dal:EventGrain ;", "dal:orderingGrain dal:EventGrain ; dal:datasetTierModel dal:HybridLogicalClock ;")
    assert "DatasetTierWithoutGlobalRead" in _kinds(base=base_with_tier)
    assert "DatasetTierWithoutGlobalRead" not in _kinds(
        "ex:O a dal:DataAccessProfile ; dal:appliesTo ex:ThingScope ; dal:globalReadStrategy dal:DenseFeedRead .",
        base=base_with_tier,
    )
    assert "DatasetTierWithoutGlobalRead" not in _kinds()


def test_advisory_contiguity_warns():
    assert "AdvisoryContiguity" in _kinds("ex:O a dal:DataAccessProfile ; dal:appliesTo ex:ThingScope ; dal:contiguityCheckMode dal:AdvisoryContiguityCheck .")
    assert "AdvisoryContiguity" not in _kinds()


def test_sorted_acquisition_with_single_request_cas_warns():
    extra = "ex:C a dal:DataAccessProfile ; dal:appliesTo ex:ThingScope ; dal:deadlockPolicy dal:SortedAcquisition ."
    assert "SortedAcquisitionIneffective" in _kinds(extra)
    locking = BASE.replace("dal:concurrencyProfile dal:Optimistic", "dal:concurrencyProfile dal:LockingConcurrency")
    assert "SortedAcquisitionIneffective" not in _kinds(extra, base=locking)


@pytest.mark.parametrize("prop", ["txnShards", "logShards", "keyShards"])
def test_declared_shard_count_warns_not_honoured(prop):
    assert "ShardingNotHonoured" in _kinds(f"ex:M a dal:DataAccessProfile ; dal:appliesTo ex:ThingScope ; dal:{prop} 16 .")
    assert "ShardingNotHonoured" not in _kinds(f"ex:M a dal:DataAccessProfile ; dal:appliesTo ex:ThingScope ; dal:{prop} 1 .")


def test_bucket_any_retention_with_as_of_floor_is_refused():
    bad = 'ex:R a dal:DataAccessProfile ; dal:appliesTo ex:ThingScope ; dal:retentionMode dal:BucketAnyRetention ; dal:asOfFloorSource "job" .'
    g = _graph(bad)
    with pytest.raises(CrossAxisViolation) as e:
        check_cross_axis(g, Target(CLS), _dims(g), [])
    assert e.value.kind == "AsOfFloorRetentionConflict"
    # the two properties on different nodes: still refused, on resolved values
    split = """
ex:R1 a dal:DataAccessProfile ; dal:appliesTo ex:ThingScope ; dal:retentionMode dal:BucketAnyRetention .
ex:R2 a dal:DataAccessProfile ; dal:appliesTo ex:ThingScope ; dal:asOfFloorSource "job" .
"""
    g = _graph(split)
    with pytest.raises(CrossAxisViolation):
        check_cross_axis(g, Target(CLS), _dims(g), [])
    ok = 'ex:R a dal:DataAccessProfile ; dal:appliesTo ex:ThingScope ; dal:retentionMode dal:BucketAnyRetention .'
    _kinds(ok)  # no as-of floor: allowed


@pytest.mark.parametrize("window", [None, "0"])
def test_lag_window_read_requires_positive_window(window):
    decl = "ex:O a dal:DataAccessProfile ; dal:appliesTo ex:ThingScope ; dal:globalReadStrategy dal:LagWindowRead"
    decl += f" ; dal:lagWindowMillis {window} ." if window else " ."
    g = _graph(decl)
    with pytest.raises(CrossAxisViolation) as e:
        check_cross_axis(g, Target(CLS), _dims(g), [])
    assert e.value.kind == "LagWindowMissing"


def test_lag_window_read_with_window_passes():
    _kinds("ex:O a dal:DataAccessProfile ; dal:appliesTo ex:ThingScope ; dal:globalReadStrategy dal:LagWindowRead ; dal:lagWindowMillis 30000 .")


# ---- Behaviour: firstWrite and registryGraph --------------------------------------------------


def _ops(extra: str = "", base: str = BASE) -> dict[str, object]:
    _, compiled = compile_to_graph(_graph(extra, base), classes={CLS})
    return {o.operation: o for o in compiled[0].operations}


def test_absent_row_keeps_create_if_absent():
    ops = _ops()
    assert "create-if-absent" in ops and "bootstrap-version-row" not in ops


def test_pre_created_row_gets_bootstrap_instead_of_create():
    ops = _ops("ex:B a dal:DataAccessProfile ; dal:appliesTo ex:ThingScope ; dal:firstWrite dal:PreCreatedRow .")
    assert "create-if-absent" not in ops
    assert ops["bootstrap-version-row"].template_id == "bootstrap-version-row.mustache"
    assert "cas-replace" in ops


def test_pre_created_row_under_dataset_guard_uses_guarded_bootstrap():
    extra = """
ex:B a dal:DataAccessProfile ; dal:appliesTo ex:ThingScope ; dal:firstWrite dal:PreCreatedRow .
ex:E a dal:EpochProfile ; dal:appliesTo ex:ThingScope ; dal:epochGuardScope dal:DatasetLevelGuard .
"""
    assert _ops(extra)["bootstrap-version-row"].template_id == "bootstrap-version-row-dataset-guard.mustache"


def test_registry_graph_is_bound_on_every_audit():
    ops = _ops('ex:M a dal:DataAccessProfile ; dal:appliesTo ex:ThingScope ; dal:registryGraph "urn:g:registry/thing" .')
    for name in ["gap-scan-audit", "fork-detection-audit", "revision-multi-txn-audit", "txn-multi-revision-audit"]:
        bindings = {b.name: b.value for b in ops[name].bindings}
        assert bindings["registryGraph"] == "<urn:g:registry/thing>"
    assert "registryGraph" not in {b.name for b in ops["cas-replace"].bindings}


def test_registry_graph_absent_means_no_binding():
    assert "registryGraph" not in {b.name for b in _ops()["gap-scan-audit"].bindings}


def test_unsafe_registry_graph_iri_fails_compile():
    with pytest.raises(CompileError):
        compile_to_graph(
            _graph('ex:M a dal:DataAccessProfile ; dal:appliesTo ex:ThingScope ; dal:registryGraph "urn:x> } ; DROP ALL ; #" .'),
            classes={CLS},
        )


def test_resolved_literal_is_rdf_literal():
    rd = _dims(_graph("ex:M a dal:DataAccessProfile ; dal:appliesTo ex:ThingScope ; dal:txnShards 8 ."))["txnShards"]
    assert isinstance(rd.value, RdfLiteral) and int(rd.value) == 8


def test_lag_window_negative_fixture_fails_for_the_right_reason():
    """Guards the fixture itself: it must fail on the missing window, not
    on an unrelated ambiguity."""
    g = Graph()
    g.parse(SPEC_TTL, format="turtle")
    g.parse(EXAMPLES_DIR / "invalid-lagwindow-missing.ttl", format="turtle")
    with pytest.raises(CompileError) as e:
        compile_to_graph(g)
    assert isinstance(e.value.__cause__, CrossAxisViolation)
    assert e.value.__cause__.kind == "LagWindowMissing"
