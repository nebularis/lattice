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
