<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Phase 3 — Operation Plane (Sketch)

**Unit type:** Phase (of Epic `lattice-platform-development`)
**Unit ID:** `phase-3`
**Promotes to:** [phase-3-plan.md](../plans/phase-3-plan.md)
**Status record:** [phase-3-status.md](../status/phase-3-status.md)
**Depends on:** [phase-2](phase-2-sketch.md) exit gate

## Why this chunk is deliberately light

Same rationale as [phase-2-sketch.md](phase-2-sketch.md): the epic's rolling-wave methodology expands Phase 3 to full VP-level detail at P2.11.4 (Phase 2's own close-out slice), not before. This chunk exists as a real, standalone plan/status pair — satisfying the Epic Decomposition Model — without inventing test tables the epic has explicitly deferred.

The epic states one hard gate for this phase that is worth restating rather than leaving buried in a table: **no C-09 (behaviour execution engine) slice starts until C-07 (projection maintenance) reconciliation has been green for a full week of nightly runs against synthetic load, including an injected-divergence scenario.** This is called out twice in the epic (Part 7's header and Part 10's "anti-pattern to avoid" note) because a behaviour engine over a silently-corrupt projection produces wrong decisions that look right. That gate is not something later expansion should be allowed to quietly soften.

## Risks specific to this phase, worth stating now

- R-03 (incremental projection divergence) is rated **High** likelihood in the epic's own risk register and is this phase's dominant risk (P3.1.7's reconciliation suite is its owning control).
- R-02 (mis-declared `lens` corrupts authored data) and the write-back loop cap (P3.3.9) are the two controls protecting the one thing this phase must never do: silently mutate an authored, human-approved value. Both are pack-build-time or hard-cap checks, not runtime judgment calls, and should stay that way through expansion.
