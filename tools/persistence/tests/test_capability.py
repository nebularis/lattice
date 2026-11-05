# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""Capability requirement, spec, and self-check (sketch §3.6). The core
claim under test: a missing dal:CapabilitySpec never changes what is
resolved -- only whether a self-check exists to review it against."""

from __future__ import annotations

from rdflib import URIRef

from persistence import capability, resolver
from persistence.namespaces import DAL
from persistence.model import DIMENSIONS
from persistence.scopes import discover_targets

from conftest import EXAMPLES_DIR

LENDING = "https://example.org/lending#"


def test_requirement_is_computed_without_any_spec(example):
    g = example("baseline-single-class.ttl")
    target = discover_targets(g, classes={URIRef(LENDING + "LoanApplication")})[0]
    dims = {d: resolver.resolve_dimension(g, target, d, None) for d in DIMENSIONS}
    uniq = resolver.resolve_uniqueness(g, target)
    req = capability.compute_requirement(dims, uniq)
    assert req.requires_cas == str(DAL.Linearizable)
    assert req.requires_uniqueness_level == "Transactional"


def test_absence_of_spec_never_changes_resolution(example):
    """The load-bearing claim of §3.6: resolving with no spec and
    resolving with a spec that grants everything must agree exactly."""
    g = example("baseline-single-class.ttl")
    target = discover_targets(g, classes={URIRef(LENDING + "LoanApplication")})[0]

    without_spec = {d: resolver.resolve_dimension(g, target, d, None).value for d in DIMENSIONS}

    generous_spec = capability.CapabilitySpec(
        iri=None, provides_cas=str(DAL.Linearizable), provides_reasoning=True, provides_commit_validation=str(DAL.ShaclCoreValidation)
    )
    with_generous_spec = {d: resolver.resolve_dimension(g, target, d, generous_spec).value for d in DIMENSIONS}

    assert without_spec == with_generous_spec


def test_check_passes_when_spec_meets_requirement():
    req = capability.CapabilityRequirement(requires_cas=str(DAL.Linearizable))
    spec = capability.CapabilitySpec(iri="urn:x:env", provides_cas=str(DAL.Linearizable))
    result = capability.check_requirement(req, spec)
    assert result.verdict == "PASS"


def test_check_fails_when_spec_is_insufficient():
    req = capability.CapabilityRequirement(requires_cas=str(DAL.Linearizable))
    spec = capability.CapabilitySpec(iri="urn:x:env", provides_cas=str(DAL.BestEffort))
    result = capability.check_requirement(req, spec)
    assert result.verdict == "FAIL"
    assert "Linearizable" in result.failures[0] and "BestEffort" in result.failures[0]


def test_check_fails_on_missing_reasoning():
    req = capability.CapabilityRequirement(requires_reasoning_for=["urn:x:scope"])
    spec = capability.CapabilitySpec(iri="urn:x:env", provides_reasoning=False)
    result = capability.check_requirement(req, spec)
    assert result.verdict == "FAIL"


def test_check_fails_on_missing_strong_uniqueness_support():
    req = capability.CapabilityRequirement(requires_uniqueness_level="Strong")
    spec = capability.CapabilitySpec(iri="urn:x:env", provides_commit_validation=str(DAL.NoCommitValidation))
    result = capability.check_requirement(req, spec)
    assert result.verdict == "FAIL"


def test_the_levels_rank_no_guarantee_below_best_effort_below_linearizable():
    rank = capability._CAS_RANK
    assert rank[str(DAL.NoConcurrencyGuarantee)] < rank[str(DAL.BestEffort)] < rank[str(DAL.Linearizable)]


def test_a_spec_that_names_no_level_provides_no_guarantee():
    req = capability.CapabilityRequirement(requires_cas=str(DAL.BestEffort))
    result = capability.check_requirement(req, capability.CapabilitySpec(iri="urn:x:env"))
    assert result.verdict == "FAIL" and "NoConcurrencyGuarantee" in result.failures[0]


def test_the_spec_loader_reads_the_level_as_an_iri(example):
    g = example("baseline-single-class.ttl")
    g.parse(EXAMPLES_DIR / "capability-spec-example.ttl", format="turtle")
    target = discover_targets(g, classes={URIRef(LENDING + "LoanApplication")})[0]
    spec = capability.load_capability_spec(g, target)
    assert spec.provides_cas == str(DAL.Linearizable)
