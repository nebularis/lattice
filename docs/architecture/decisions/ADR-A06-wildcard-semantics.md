---
published: true
---
<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# ADR-A06: Wildcard semantics and limits

**Status:** Published, 2026-10-19. Accepted 2026-09-17.
**Described in:** [Eligibility README](../../../ontology/eligibility/README.md)

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

## Provenance

Accepted when Eligibility was first specified, 2026-09-17.
