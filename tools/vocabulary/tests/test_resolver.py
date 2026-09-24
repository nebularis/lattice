# SPDX-License-Identifier: MPL-2.0
"""Resolver-level tests for the resolution law's context-dependent cases
(the ones ontology/vocabulary/shapes/constraints.ttl cannot check on its
own: strict-superset precedence and applicability need a caller-supplied
active context and resolution time). See tools/vocabulary/README.md.

Covers validation-pack cases VTB-05, 06, 07 (the context-dependent form:
incomparable applicable scope sets), 08, 10.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from rdflib import URIRef

from vocabulary import BindingConflictError, NoApplicableBindingError, resolve

EX = "https://example.org/lattice/vocabulary/examples#"


def _at(iso: str) -> datetime:
    return datetime.fromisoformat(iso).replace(tzinfo=timezone.utc)


def test_conjunctive_scope_requires_every_named_scope(example):
    """VTB-05: a context naming only one of a two-scope binding's scopes
    does not satisfy it; the single-scope binding for the same region wins
    instead."""
    g = example("conjunctive-scopes.ttl")
    contract = URIRef(EX + "cnj-contract")
    north = URIRef(EX + "cnj-region-north")

    result = resolve(g, contract, context=[north], at=_at("2026-03-01T00:00:00"))

    assert result.scheme == URIRef(EX + "cnj-scheme-region")
    assert not result.used_fallback


def test_strict_superset_precedence(example):
    """VTB-06: when both named scopes hold, the binding whose scope set is
    a strict superset of the other applicable binding's wins."""
    g = example("conjunctive-scopes.ttl")
    contract = URIRef(EX + "cnj-contract")
    north = URIRef(EX + "cnj-region-north")
    gold = URIRef(EX + "cnj-tier-gold")

    result = resolve(g, contract, context=[north, gold], at=_at("2026-03-01T00:00:00"))

    assert result.scheme == URIRef(EX + "cnj-scheme-region-tier")
    assert result.winning_binding == URIRef(EX + "cnj-binding-region-tier")


def test_fallback_used_when_no_binding_applies(example):
    """VTB-08: an empty context matches neither scoped binding, so the
    contract's voc:boundScheme fallback is used."""
    g = example("conjunctive-scopes.ttl")
    contract = URIRef(EX + "cnj-contract")

    result = resolve(g, contract, context=[], at=_at("2026-03-01T00:00:00"))

    assert result.used_fallback
    assert result.scheme == URIRef(EX + "cnj-scheme-fallback")
    assert result.winning_binding is None


def test_equal_specificity_conflict_raises(example):
    """VTB-07: two bindings applicable at once, neither a strict superset
    of the other, refuse to resolve rather than picking one."""
    g = example("equal-specificity-conflict.ttl")
    contract = URIRef(EX + "conflict-contract")
    region = URIRef(EX + "conflict-region")

    with pytest.raises(BindingConflictError) as excinfo:
        resolve(g, contract, context=[region], at=_at("2026-03-01T00:00:00"))

    assert {c.node for c in excinfo.value.candidates} == {
        URIRef(EX + "conflict-binding-x"),
        URIRef(EX + "conflict-binding-y"),
    }


def test_open_ended_binding_remains_eligible_after_start(example):
    """VTB-10: an open-ended binding (no validTo) stays applicable at any
    time at or after its validFrom."""
    g = example("unscoped-time-bounded.ttl")
    contract = URIRef(EX + "utb-contract")

    result = resolve(g, contract, context=[], at=_at("2030-01-01T00:00:00"))

    assert result.scheme == URIRef(EX + "utb-scheme")
    assert not result.used_fallback


def test_temporal_handover_selects_the_edition_in_force(example):
    g = example("temporal-handover.ttl")
    contract = URIRef(EX + "handover-contract")

    before = resolve(g, contract, context=[], at=_at("2026-03-01T00:00:00"))
    at_handover = resolve(g, contract, context=[], at=_at("2026-07-01T00:00:00"))
    after = resolve(g, contract, context=[], at=_at("2026-09-01T00:00:00"))

    assert before.scheme == URIRef(EX + "handover-scheme-v1")
    assert at_handover.scheme == URIRef(EX + "handover-scheme-v2")
    assert after.scheme == URIRef(EX + "handover-scheme-v2")


def test_no_applicable_binding_and_no_fallback_raises(example):
    g = example("missing-binds-scheme.ttl")
    contract = URIRef(EX + "missing-bs-contract")

    with pytest.raises(NoApplicableBindingError):
        resolve(g, contract, context=[], at=_at("2026-03-01T00:00:00"))
