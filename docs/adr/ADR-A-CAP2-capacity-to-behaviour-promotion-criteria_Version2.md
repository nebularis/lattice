<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# ADR-A-CAP2: Promotion criteria from `applied/capacity` to `behaviour`

**Status:** Proposed  
**Date:** 2026-09-18

## Context

`applied/capacity` is intended as a thin, generic domain ontology over substrate Behaviour.  
Some constructs may eventually prove generic enough to belong in `behaviour`. Others must remain applied or deployment-specific.

Without explicit criteria, promotion risks either:

- polluting substrate with domain semantics, or
- duplicating generic mechanism indefinitely in applied layers.

## Decision

A construct from `applied/capacity` may be promoted to `behaviour` only if all criteria below are satisfied.

## Promotion criteria

### P1. Genericity criterion

The construct can be defined without naming any domain category such as:

- insurance,
- lending,
- credit covenant,
- policy,
- claim,
- premium,
- deductible,
- facility,
- borrower,
- SaaS plan,
- inventory class.

### P2. Multi-domain evidence criterion

At least two materially different non-derived applied examples must exercise the construct, with passing tests.

Minimum acceptable pairings include:

- lending + SaaS,
- lending + inventory,
- SaaS + public-sector quota,
- inventory + entitlement management.

Insurance-only evidence is insufficient for promotion.

### P3. Formal-law criterion

Construct must ship with:

- formal definition,
- explicit preconditions,
- at least one invariant or conservation law,
- deliberate-defect fixture proving violation detection.

### P4. Validation criterion

Construct must be enforceable by SHACL in a way that is implementation-neutral.

At minimum:

- structural shape coverage,
- constraint shape coverage,
- deterministic behavior constraints where relevant.

### P5. Runtime-neutrality criterion

Promotion must not encode storage-engine assumptions, indexing tricks, or compiler-specific implementation details.

Execution optimisation remains in projection profiles, not substrate semantics.

### P6. Dependency criterion

Promoted construct must not require imports from applied layers.

It must depend only on substrate layers or existing substrate-compatible primitives.

### P7. Compatibility criterion

Promotion must include migration guidance for existing applied instances and a non-breaking transition plan where feasible.

### P8. Governance criterion

Promotion requires an ADR containing:

- rationale,
- evidence corpus references,
- law statement,
- shape references,
- migration and compatibility notes.

## Non-promotable classes of content

The following are explicitly non-promotable into `behaviour`:

- domain vocabularies and taxonomies,
- product-specific statuses,
- market-specific role semantics,
- deployment-specific arithmetic partitions,
- proprietary theorem instantiations and benchmark-specific tuning constants.

## Consequences

- `behaviour` remains generic and durable.
- `applied/capacity` remains the proving ground for candidate abstractions.
- promotion decisions become auditable and repeatable.