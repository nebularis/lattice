<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# ADR A-05: Compatibility operation vocabulary

## Status

Accepted

## Context

Eligibility conditions need a small, stable operation vocabulary to express how multiple requirements combine. Free-text or ad hoc operation naming prevents conformance checks from being portable.

## Decision

Eligibility declares a closed-by-default mechanism vocabulary for compatibility operations with three named operations:

- `elg:AllRequired`
- `elg:AnySufficient`
- `elg:DimensionConsistent`

These are individuals of `elg:CompatibilityOperation` and are used by `elg:compatibilityOperation`.

## Consequences

- Every condition states combination semantics in a machine-checkable way.
- Implementations can support profile-level checks without relying on implementation-specific labels.
- Downstream extensions may add operations, but baseline conformance depends on these three names.

## Addendum, 2026-10-19: composition operations, on profiles only

Agreed by the maintainer. The vocabulary says how an admission profile combines its conditions' outcomes, so
it is renamed `elg:CompositionOperation`, used by `elg:compositionOperation`, and only an admission profile
declares one. On a condition that is not a profile it had no effect, and a shape now reports it there.
`elg:DimensionConsistent` is removed, with the operational profile `elg:E6` that tested it. It was meant to
check that conditions on different dimensions are compatible before they are combined, which is a
precondition rather than a way of composing outcomes, and no compiler could evaluate it. The baseline is
`elg:AllRequired` and `elg:AnySufficient`. A downstream ontology may still add an operation, and the compilers
refuse one they cannot evaluate.

