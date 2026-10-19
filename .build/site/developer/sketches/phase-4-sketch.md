<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Phase 4 — Maturity (Sketch)

**Unit type:** Phase (of Epic `lattice-platform-development`)
**Unit ID:** `phase-4`
**Promotes to:** [phase-4-plan.md](../plans/phase-4-plan.md)
**Status record:** [phase-4-status.md](../status/phase-4-status.md)
**Depends on:** [phase-3](phase-3-sketch.md) exit gate

## Why this chunk is deliberately the lightest

The epic itself states Phase 4 is "deliberately lighter: each item is a sub-programme sized after Phase 3 measurement" (Part 8). There is no rolling-wave promise to expand this one at a numbered close-out slice the way Phase 2 and 3 have — Phase 4's own items (P4.1–P4.7) are sub-programmes, not slices, and several (P4.3 second store adapter, P4.5 SPC integration) are explicitly conditional ("if adopted"). Decomposing this further than the epic already has would mean inventing sizing the epic explicitly says depends on data that does not exist yet (P3.6.3's capacity/cost model, P3.6.1's benchmark run).

This chunk exists only to satisfy the Epic Decomposition Model's requirement that every phase in the DAG has a plan/status pair, and to carry forward the one non-negotiable item in this phase: **P4.7, multi-region, is explicitly a non-goal, not a deferred feature** — stated with its reason, reviewed annually. That framing should survive into whatever eventually expands this phase, not get silently reinterpreted as "not done yet."

## Risks specific to this phase

- P4.6 (commercial packaging) has its own falsifiable test embedded in the epic text: "does a commercial extension require zero patches to OSS classes? Prove with a sample adapter in a separate repo." That test should not get diluted into a documentation-only claim when this phase is eventually staffed.
