<!-- SPDX-License-Identifier: MPL-2.0 -->

# Vocabulary Resolver

Reference implementation of the scoped and temporal binding resolution law
stated in `ontology/vocabulary/README.md` §4 and decided in
[ADR-A85](../../docs/architecture/decisions/ADR-A85-vocabulary-scoped-temporal-binding-resolution.md).
Given a `voc:SchemeContract`, a caller-supplied active context (a set of
`voc:BindingScope` IRIs), and a resolution time, `vocabulary.resolver.resolve`
returns the one `voc:ConceptScheme` that applies, or raises a named exception
naming why none can be selected.

This package answers one question only: which scheme applies. It does not
decide which scopes hold for a given value, does not resolve a fuzzy label to
a concept, and is not a live store or runtime scheduler — all deliberately out
of scope per the [design sketch](../../docs/developer/sketches/vocabulary-temporal-binding.md).

## Install

```bash
mise exec -- python -m pip install -e ./tools/vocabulary[test]
```

## Resolution law

For one contract, a `voc:SchemeBinding` is a candidate when every scope it
names is present in the caller's context (no scope means every context) and
the caller's resolution time falls within its `fnd:TemporalScope`. Among
candidates, a binding whose scope set is a strict superset of another
candidate's takes precedence over it. If, after that, more than one candidate
remains — either truly equal scope sets, or two incomparable sets neither of
which is a superset of the other — resolution refuses to choose and raises
`BindingConflictError`, naming every tied candidate. If no candidate exists at
all, the contract's `voc:boundScheme` is used as the unscoped fallback; if
that is also absent, resolution raises `NoApplicableBindingError`.

No step here selects silently. A conflict is always reported as a conflict,
never resolved by iteration order, insertion order, or any other incidental
property of the input graph — see `tests/test_determinism.py`.

## What this package deliberately does not check

Structural completeness (a binding missing `forContract` or `bindsScheme`),
temporal interval sanity, scopeless-binding/`boundScheme` agreement, and the
context-independent case of an equal-specificity conflict are all SHACL-level
checks in `ontology/vocabulary/shapes/constraints.ttl`, not this resolver's
job — see that file's header for why those four are checkable from the graph
alone while a context-dependent precedence decision is not. `tests/test_shacl_fixtures.py`
runs the fixtures under `ontology/vocabulary/examples/` against those shapes;
`tests/test_resolver.py` and `tests/test_determinism.py` exercise this
resolver against the same fixtures for the context-dependent cases SHACL
cannot decide.

The historical-provenance-time shape's `vvp:resolvedAt` term is a valid-time
"as-of" query point (the same axis as `fnd:validFrom`/`fnd:validTo` and
`resolve()`'s own `at` parameter), not a transaction-time "recorded when"
timestamp — see `constraints.ttl`'s header for why it is named `resolvedAt`
rather than `recordedAt`, and why it is a validation-profile placeholder
rather than a normative Vocabulary term.

## Modules

- [`vocabulary.namespaces`](src/vocabulary/namespaces.py) — the `VOC`, `FND`,
  and `VVP` (validation-profile-only) namespaces.
- [`vocabulary.model`](src/vocabulary/model.py) — `Binding`, `CandidateTrace`,
  `Resolution`, and the resolver's exception types.
- [`vocabulary.resolver`](src/vocabulary/resolver.py) — `resolve()`, the
  precedence algorithm itself.
