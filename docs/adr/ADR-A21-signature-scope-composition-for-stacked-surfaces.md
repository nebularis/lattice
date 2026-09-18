<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# ADR-A21: Signature-scope and conservativity composition in stacked surfaces

**Status:** Accepted
**Date:** 2026-09-18
**Supersedes:** none
**Related:** ADR-A16 (X1 conservativity, X6 signature scope), ADR-A20 (Projection laws)
**Source plan:** [surface-mork-unified-projection-delivery-plan.md](../../surface/docs/surface-mork-unified-projection-delivery-plan.md)

## Context

ADR-A16's law X6 already distinguishes `srf:LocalSignature` from `srf:SourceSignature` for a single promotion. `surface/docs/OUTSTANDING-ITEMS 2.md` §2.2 states, informally and as unenforced work, the rule a stacked surface would need: signature scope composes, so a surface built over a source-signature promotion is not conservative over the original source either. This has never been enforced because stacking is capped at depth 1 by `srf:StackDepthReleaseCeilingShape`, and depth 1 has no predecessor to compose with. Projection introduces new stacking paths — a Projection over a Promotion, a Projection over another Projection — before that cap is necessarily lifted.

## Decision

**Signature-scope composition is stated as law now, ahead of any decision to lift the depth-1 ceiling.** `signatureScope` of a composed surface is `srf:SourceSignature` if any input surface's is, else `srf:LocalSignature`. Law X1 (conservativity) gains a composition clause reflecting this. Law R1 (determinism) gains a matching clause: every surface in a stack shares one profile identity, checked statically.

This ADR does not lift `srf:StackDepthReleaseCeilingShape`. It states the law that lifting it depends on, per `OUTSTANDING-ITEMS 2.md` §2.2's own account of what must be written down first.

## Consequences

- X1 and R1 are amended in place with composition clauses, not superseded — the underlying decision (conservativity, determinism) is unchanged, only its behaviour under stacking is now stated.
- Projection contracts stacked over Promotion or Index surfaces compute `signatureScope` by this rule at compile time, before any depth-1 cap is revisited.
- Lifting the depth-1 ceiling remains a separate, later decision, and still requires the read-set DAG, cycle detection, and freshness-propagation work `OUTSTANDING-ITEMS 2.md` §2.2 describes. This ADR removes only the "law not yet stated" blocker, not the remaining implementation.
