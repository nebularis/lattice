# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""Capability requirement, spec, and self-check (sketch §3.6). The core
claim under test: a missing dal:CapabilitySpec never changes what is
resolved -- only whether a self-check exists to review it against."""

from __future__ import annotations

from rdflib import URIRef

from persistence import capability, resolver
from persistence.model import DIMENSIONS
from persistence.scopes import discover_targets

LENDING = "https://example.org/lending#"


def test_requirement_is_computed_without_any_spec(example):
    g = example("baseline-single-class.ttl")
    target = discover_targets(g, classes={URIRef(LENDING + "LoanApplication")})[0]
    dims = {d: resolver.resolve_dimension(g, target, d, None) for d in DIMENSIONS}
    uniq = resolver.resolve_uniqueness(g, target)
    req = capability.compute_requirement(dims, uniq)
    assert req.requires_cas == "LINEARIZABLE"
    assert req.requires_uniqueness_level == "Transactional"


def test_absence_of_spec_never_changes_resolution(example):
    """The load-bearing claim of §3.6: resolving with no spec and
    resolving with a spec that grants everything must agree exactly."""
    g = example("baseline-single-class.ttl")
    target = discover_targets(g, classes={URIRef(LENDING + "LoanApplication")})[0]

    without_spec = {d: resolver.resolve_dimension(g, target, d, None).value for d in DIMENSIONS}

    generous_spec = capability.CapabilitySpec(
        iri=None, provides_cas="LINEARIZABLE", provides_reasoning=True, provides_commit_validation="SHACL_CORE"
    )
    with_generous_spec = {d: resolver.resolve_dimension(g, target, d, generous_spec).value for d in DIMENSIONS}

    assert without_spec == with_generous_spec


def test_check_passes_when_spec_meets_requirement():
    req = capability.CapabilityRequirement(requires_cas="LINEARIZABLE")
    spec = capability.CapabilitySpec(iri="urn:x:env", provides_cas="LINEARIZABLE")
    result = capability.check_requirement(req, spec)
    assert result.verdict == "PASS"


def test_check_fails_when_spec_is_insufficient():
    req = capability.CapabilityRequirement(requires_cas="LINEARIZABLE")
    spec = capability.CapabilitySpec(iri="urn:x:env", provides_cas="BEST_EFFORT")
    result = capability.check_requirement(req, spec)
    assert result.verdict == "FAIL"
    assert "LINEARIZABLE" in result.failures[0]


def test_check_fails_on_missing_reasoning():
    req = capability.CapabilityRequirement(requires_reasoning_for=["urn:x:scope"])
    spec = capability.CapabilitySpec(iri="urn:x:env", provides_reasoning=False)
    result = capability.check_requirement(req, spec)
    assert result.verdict == "FAIL"


def test_check_fails_on_missing_strong_uniqueness_support():
    req = capability.CapabilityRequirement(requires_uniqueness_level="Strong")
    spec = capability.CapabilitySpec(iri="urn:x:env", provides_commit_validation="NONE")
    result = capability.check_requirement(req, spec)
    assert result.verdict == "FAIL"
