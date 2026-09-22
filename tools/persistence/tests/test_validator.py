# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""Cross-axis consistency checks (sketch §3.5) and boundary conflicts
(sketch §4.6). Every negative fixture in ontology/persistence/examples/
has a matching test here asserting the *named* exception kind, per
ADR-A79's "never a silent downgrade" rule -- a CI gate can assert on the
type, not grep a message string."""

from __future__ import annotations

import pytest
from rdflib import URIRef

from persistence import capability, resolver, validator
from persistence.model import CrossAxisViolation, DIMENSIONS
from persistence.scopes import discover_targets

LENDING = "https://example.org/lending#"


def _resolve_all(g, target, spec=None):
    dims = {d: resolver.resolve_dimension(g, target, d, spec) for d in DIMENSIONS}
    uniq = resolver.resolve_uniqueness(g, target)
    return dims, uniq


def _target_for(g, cls_local: str):
    cls = URIRef(LENDING + cls_local)
    return discover_targets(g, classes={cls})[0]


@pytest.mark.parametrize(
    "fixture,cls_local,expected_kind",
    [
        ("invalid-noboundary-cas.ttl", "Fact", "NoBoundaryConcurrencyConflict"),
        ("invalid-compositeboundary-receiptonly.ttl", "Widget", "CompositeBoundaryReceiptConflict"),
        ("invalid-metashards-changed-no-ack.ttl", "Widget", "UnacknowledgedShardMigration"),
        ("invalid-commitgrain-opseq.ttl", "Widget", "CommitGrainOpSeqConflict"),
        ("invalid-uniqueness-outside-boundary.ttl", "Widget", "UniquenessOutsideBoundary"),
    ],
)
def test_cross_axis_negative_fixture_raises_named_violation(example, fixture, cls_local, expected_kind):
    g = example(fixture)
    target = _target_for(g, cls_local)
    dims, uniq = _resolve_all(g, target)
    with pytest.raises(CrossAxisViolation) as excinfo:
        validator.check_cross_axis(g, target, dims, uniq)
    assert excinfo.value.kind == expected_kind


@pytest.mark.parametrize(
    "fixture,cls_local",
    [
        ("baseline-single-class.ttl", "LoanApplication"),
        ("value-based-cas.ttl", "Order"),
        ("composite-property-boundary-shacl.ttl", "Order"),
    ],
)
def test_positive_fixture_raises_nothing(example, fixture, cls_local):
    g = example(fixture)
    target = _target_for(g, cls_local)
    dims, uniq = _resolve_all(g, target)
    validator.check_cross_axis(g, target, dims, uniq)  # must not raise


def test_mixed_receipt_model_is_a_warning_not_an_error(example):
    g = example("warning-mixed-receipt-model.ttl")
    widget = URIRef(LENDING + "Widget")
    gadget = URIRef(LENDING + "Gadget")
    targets = discover_targets(g, classes={widget, gadget})
    resolved_by_target = {}
    for t in targets:
        spec = capability.load_capability_spec(g, t)
        resolved_by_target[t] = {d: resolver.resolve_dimension(g, t, d, spec) for d in DIMENSIONS}

    diagnostics = validator.check_mixed_receipt_model(g, resolved_by_target)
    assert len(diagnostics) == 1
    assert diagnostics[0].kind == "MixedReceiptModel"
    assert diagnostics[0].severity == "WARNING"


def test_mixed_receipt_model_does_not_false_positive_on_uniform_family(example):
    g = example("baseline-single-class.ttl")
    target = _target_for(g, "LoanApplication")
    dims, _ = _resolve_all(g, target)
    diagnostics = validator.check_mixed_receipt_model(g, {target: dims})
    assert diagnostics == []


@pytest.mark.parametrize(
    "fixture",
    [
        "baseline-single-class.ttl",
        "composite-property-boundary-shacl.ttl",
        "lending-credit-shared-class.ttl",
        "namespace-wide.ttl",
    ],
)
def test_boundary_conflicts_do_not_false_positive_on_valid_fixtures(example, fixture):
    g = example(fixture)
    validator.check_boundary_conflicts(g)  # must not raise
