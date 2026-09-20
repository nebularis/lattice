<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# ADR-A27: Invalidation and minimal-scope regeneration policy

**Status:** Accepted
**Date:** 2026-09-18
**Supersedes:** none
**Related:** ADR-A16 (surface projection mechanism, profile-change regeneration), ADR-A21 (signature-scope composition), ADR-A19 (staged compiler architecture)
**Source plan:** [surface-mork-unified-projection-delivery-plan.md](../../../ontology/surface/docs/surface-mork-unified-projection-delivery-plan.md)

## Context

`ontology/surface/docs/OUTSTANDING-ITEMS 2.md` §2.2 already identifies invalidation cost as the reason stacking beyond depth 1 is capped, and notes the impact-scoping table has no row for a stacked-regeneration cost that has never been measured. Projection and MORK lowering (ADR-A18) add further regeneration triggers: a Projection contract change, a profile change, a mapping-version change under ADR-A22's new supersession model.

## Decision

**Regeneration is dependency-scoped and profile-aware, computed from the read set, never broad by default.** Where stacking exceeds depth 1 in future, the read set is treated as a DAG and freshness as a transitive property, per the mechanism `OUTSTANDING-ITEMS 2.md` §2.2 already describes but has not yet needed. A profile change remains the one case that legitimately triggers estate-wide regeneration, consistent with ADR-A16's stated consequence for profile changes.

## Consequences

- A regeneration planner computes the minimal impacted rebuild set from the read set and profile identity, rather than regenerating a whole layer or estate on any change.
- This ADR states the invalidation rule; it does not itself lift the stack-depth-1 ceiling, which remains gated on the composition laws in ADR-A21 and the cycle-detection work `OUTSTANDING-ITEMS 2.md` §2.2 describes.
- Fixture tests are required to demonstrate minimal-scope regeneration before this policy is considered discharged, not merely stated.
