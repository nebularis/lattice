# SPDX-License-Identifier: MPL-2.0
"""Consumer/provenance boundary check (plan §5; validation-pack VTB-14).

Both real consumers now honour scoped bindings: the Surface compiler resolves
a contract-bound population's scheme via `vocabulary.resolve` before
enumerating members (`tools/surface/src/surface/compile.py`), and
`ontology/eligibility/shapes/rules.ttl`'s `elg:HierarchyWellFoundednessShape`
checks every scheme a contract could resolve to (`boundScheme` or any
`SchemeBinding`), not only the unscoped fallback. This test keeps proving the
underlying divergence a naive `boundScheme`-only read would still produce, as
the reference the fix above is measured against.
"""

from __future__ import annotations

from datetime import datetime, timezone

from rdflib import URIRef

from vocabulary import resolve
from vocabulary.namespaces import VOC

EX = "https://example.org/lattice/vocabulary/examples#"
CONTRACT = URIRef(EX + "consumer-contract")
NORTH = URIRef(EX + "consumer-region-north")


def _naive_bound_scheme_read(graph, contract):
    """A boundScheme-only read, ignoring any voc:SchemeBinding."""
    return graph.value(contract, VOC.boundScheme)


def test_unscoped_context_agrees_with_the_naive_bound_scheme_read(example):
    """Existing boundScheme-only consumer behaviour remains valid when the
    caller's context has no applicable scoped binding."""
    g = example("consumer-boundary.ttl")
    at = datetime(2026, 3, 1, tzinfo=timezone.utc)

    naive = _naive_bound_scheme_read(g, CONTRACT)
    resolved = resolve(g, CONTRACT, context=[], at=at)

    assert resolved.used_fallback
    assert resolved.scheme == naive


def test_scoped_context_diverges_from_the_naive_bound_scheme_read(example):
    """A caller in the north region must resolve the applicable binding
    before reading a scheme: the naive boundScheme-only read would silently
    return the wrong (fallback) scheme."""
    g = example("consumer-boundary.ttl")
    at = datetime(2026, 3, 1, tzinfo=timezone.utc)

    naive = _naive_bound_scheme_read(g, CONTRACT)
    resolved = resolve(g, CONTRACT, context=[NORTH], at=at)

    assert not resolved.used_fallback
    assert resolved.scheme != naive
    assert resolved.scheme == URIRef(EX + "consumer-scheme-north-v1")


def test_resolved_under_is_retained_after_the_binding_it_named_lapses(example):
    """A record's voc:resolvedUnder assertion is data, not a cached resolve()
    result: it is unaffected by resolving the same contract again at a later
    time, even though the scheme currently in force has since changed."""
    g = example("consumer-boundary.ttl")
    record = URIRef(EX + "consumer-record-42")
    historical_binding = URIRef(EX + "consumer-binding-north-v1")

    current = resolve(
        g,
        CONTRACT,
        context=[NORTH],
        at=datetime(2026, 9, 1, tzinfo=timezone.utc),
    )
    assert current.winning_binding == URIRef(EX + "consumer-binding-north-v2")

    assert g.value(record, VOC.resolvedUnder) == historical_binding
