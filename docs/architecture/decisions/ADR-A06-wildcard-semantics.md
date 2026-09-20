<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# ADR A-06: Wildcard semantics and limits

## Status

Accepted

## Context

Wildcard matching is useful for generic condition patterns but can silently collapse constraints if semantics are not explicitly bounded.

## Decision

Eligibility requires explicit wildcard policy via `elg:wildcardSemantics`, using one of:

- `elg:NoWildcard`
- `elg:SingleDimensionWildcard`
- `elg:MultiDimensionWildcard`

Wildcard use is legal only when the condition declares a wildcard-enabled strategy (`elg:Wildcard`).

## Consequences

- Wildcard behavior is transparent and profile-auditable.
- Conditions that do not opt into wildcard strategy stay strict by construction.
- Over-broad matching becomes detectable by static validation.
