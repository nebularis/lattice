<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# ADR-A-CAP1: Capacity runtime projection profile (`capx`) and substrate-promotion boundary

**Status:** Proposed  
**Date:** 2026-09-18

## Context

LATTICE substrate layers (`behaviour`, `quantification`) are intentionally generic and semantically rich.  
Directly evaluating high-throughput financial transactions against the generic source graph requires deep traversal and repeated joins that are avoidable in runtime-critical flows.

The applied `capacity` layer introduces generic finite-resource semantics.  
Runtime execution requires a compact, normalised projection profile that preserves semantics while reducing hop depth and join complexity.

Recent MERIDIAN FBO material confirms several valid runtime lessons:

- finite-resource state, deterministic precedence, and phase-restricted dependency handling are essential,
- static versus state-gated admission must remain explicit,
- pre-application limiting and post-application depletion are semantically distinct,
- runtime-critical evaluation should not depend on live traversal of external vocabulary hierarchies.

Some outputs are intentionally outside graph scope, for example materialised sweep-line interval structures for gap analysis. This ADR covers only graph-resident execution A-Box shape.

## Decision

1. Introduce a **runtime projection profile** under applied capacity:
   - namespace: `capx:`
   - purpose: compact execution view for transaction-time processing
   - source of truth remains substrate and applied source graphs.

2. Keep source semantics rich and generic.  
   Use deterministic projection to materialise runtime-normalised A-Box nodes and scalar values.

3. Runtime profile is constrained to graph-resident execution semantics:
   - executable resources
   - executable balances
   - executable demands
   - executable draws
   - executable dependencies
   - executable guard snapshots.

4. Enforce runtime invariants with embedded SHACL:
   - non-negativity
   - bounded allocation
   - demand conservation
   - deterministic precedence uniqueness per target and phase
   - phase-specific dependency acyclicity (where graph closure is materialised)
   - execution-space consistency.

5. Explicitly separate runtime graph from out-of-graph analytical artefacts.
   - CoverSpan/sweep-line materialisations and similar algorithmic indices are out of scope for this profile.
   - This profile only guarantees A-Box efficiency and determinism for allocation processing.

6. Promotion of `capacity` constructs into `behaviour` is governed by ADR-A-CAP2.
   - no construct is promoted solely because it appears in a private or insurance-focused model,
   - promotion requires multi-domain generic evidence and formal law coverage.

## Consequences

### Positive

- predictable runtime query patterns with low hop count
- deterministic transaction processing semantics preserved in graph form
- clean separation of source semantics and execution representation
- reusable runtime profile across insurance, lending, subscription, inventory, and related domains
- avoids premature substrate contamination by domain-specific constructs.

### Trade-offs

- requires projection compiler and invalidation policy
- duplicates selected scalar facts from source graph into runtime view
- introduces profile-governance burden (shape evolution and compatibility).

### Non-goals

- replacing source ontologies
- expressing all analytics in-graph
- embedding domain-specific financial instruments in substrate layers.

## Implementation notes

- Runtime joins should prefer stable short keys (`resourceKey`, `demandKey`) over long IRI joins in hot paths.
- Quantities must be canonicalised into one execution space per arrangement partition before runtime.
- Eligibility complexity is evaluated upstream and represented as executable guard state snapshots.
- Dependency phases (`pre-draw`, `activation`, `post-draw`) must be explicit, not inferred.

## Related

- `capacity-domain-analysis-and-design.md`
- `capacity-model-performance-addendum.md`
- `ADR-A-C1` applied-layer restatement boundary
- `docs/architecture/deferred-scope-and-boundaries.md`