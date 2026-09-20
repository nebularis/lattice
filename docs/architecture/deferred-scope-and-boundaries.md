<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Deferred Scope and Integration Boundaries

This document records what remains intentionally out of scope after Gates 1–6, and what would have to be true before that scope is reopened.

## 1. Behaviour extent items still deferred

Gate 3 made the allowance extent profile usable for `bhv:Sequential` absorption and made `bhv:Proportional` visibly unavailable rather than silently absent. Gate 6 does not change that semantic surface.

The remaining deferred Behaviour items are:

- `bhv:Proportional` absorption
- reset-semantics edge cases for allowance restoration and carry-over

### 1.1 `bhv:Proportional`

`bhv:Proportional` remains declared in [ontology/behaviour/vocab/behaviour-vocab.ttl](../../ontology/behaviour/vocab/behaviour-vocab.ttl) and rejected by [ontology/behaviour/shapes/constraints.ttl](../../ontology/behaviour/shapes/constraints.ttl).

Before it is made usable, the repository should first carry:

1. two non-domain motivating examples
2. an explicit conservation law for the proportional allocator
3. at least one deliberate-defect fixture showing a broken proportional allocation
4. shared-corpus parity across at least two Behaviour profiles

Until those preconditions exist, the correct status is declared-and-unusable.

### 1.2 Reset-semantics edge cases

The following allowance-reset cases remain intentionally undescribed in the public substrate:

- increments above capacity
- capped restore
- reset-versus-pending-depletion ordering
- late or retrospective stimuli
- carry-over across reset boundaries

These are not blocked by Quantification or by the current Behaviour ontology shape. They remain deferred because they require precise law statements, example fixtures, and conflict-resolution policy, none of which should be implied by partial prose.

## 2. Applied-layer boundary

Per [ADR-A-C1](decisions/ADR-AC1-applied-layer-theorem-restatement.md) and [docs/GOVERNANCE.md](../GOVERNANCE.md), the public substrate stops at generic mechanism and generic law.

What belongs in an applied or deployment layer instead:

- concrete dimension sets and category inventories
- deployment-specific projections
- numeric or combinatorial theorems about one deployment's configuration
- policy choices that select one admissible substrate interpretation among several domain-specific ones

Such content may be authored in this repository where the user directs. It is simply not part of the public substrate contract.

## 3. SPC boundary

SPC is present in-repo as a substantial standalone ontology, but it is not part of the LATTICE dependency graph used by Gates 1–6.

SPC integration remains separate future work because at least three things are still missing:

1. namespace harmonisation away from the placeholder SPC namespace
2. explicit `projection/` contracts to the relevant LATTICE layers
3. a conformance story showing that process-level exchange remains aligned with the semantic states and obligations it drives

Until then, SPC should be treated as adjacent work, not as an implicit runtime dependency of Behaviour.

## 4. What Gate 6 closes

Gate 6 closes documentation scope, not ontology breadth. After this gate:

- the current usable Behaviour extent surface is `Sequential`
- the remaining extent features are explicitly deferred rather than ambiguous
- the applied-layer boundary is documented once, in one place
- SPC is documented as present but unintegrated, with concrete integration prerequisites
