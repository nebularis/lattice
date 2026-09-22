<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Phase 0 — Decisions and Non-Retrofittable Foundations (Sketch)

**Unit type:** Phase (of Epic `lattice-platform-development`)
**Unit ID:** `phase-0`
**Promotes to:** [phase-0-plan.md](../plans/phase-0-plan.md)
**Status record:** [phase-0-status.md](../status/phase-0-status.md)

## Why the boundary is here

Phase 0 is everything that cannot be safely retrofitted once a triple is durably written: identity policy, dataset topology, provenance conventions, bi-temporal design, PII/erasure, canonicalisation, and the store SPI's Core write surface. The epic's own framing (Part 4) states the exit gate as hard: nothing in Phase 1+ starts until every Phase 0 ADR is ratified and M0/M1 pass. That framing is sound and this decomposition does not revisit it — Phase 0's boundary is the epic author's boundary, not a new one drawn here.

What decomposition adds is not a new boundary, but the machinery a phase needs to be independently executable: its own plan and status file, an explicit inventory of the `docs/architecture` and README obligations buried across ~90 slices, and a delta plan for `solution-design-specification.md`, which Phase 0 will contradict or extend more than any other phase (it is the phase that replaces the SDS's current single-writer-per-store, no-role-split, no-store-SPI picture with the graph-primary, role-profiled, three-tier-SPI one).

## What stays exactly as the epic wrote it

The full slice tables (P0.1 through P0.10) are not duplicated here. [phase-0-plan.md](../plans/phase-0-plan.md) points back to [Part 4 of the epic](../plans/lattice-platform-agentic-development-v0.2.md#part-4--phase-0-decisions-and-non-retrofittable-foundations) as the authoritative slice-level scope, test taxonomy, and hard-ordering source. Duplicating ~90 rows into a second document would create two places that can drift; the plan cross-references instead, per the repository's own "say it once" guidance.

## What this decomposition pass found and does not resolve

Three mechanical corrections were made directly in the epic document because they are not architectural decisions, they are typos against already-established convention:

1. `deploy/` → `deployment/` (the root already exists under that name; copilot-instructions bans introducing a second top-level root without an ADR).
2. `make`/`just` task runner → `mise` tasks (copilot-instructions: "`mise` is the only task-orchestration entry point unless ADR-A29 is superseded"; ADR-A29 is not superseded).
3. `docs/adr/` → `docs/architecture/decisions/` (copilot-instructions explicitly forbids `docs/adr/` references).

Two things were found that are **not** mechanical and are **not** resolved here, because resolving them would be exactly the kind of unilateral design decision the Agentic Development Contract reserves for the human:

- **`platform/graph-spi` vs `platform/semantic-dataset-spi`.** Part 1's target topology names a new `graph-spi`/`graph-adapter-tdb2`/`graph-adapter-fuseki` family for the A75 three-tier SPI. `platform/semantic-dataset-spi` and `platform/semantic-dataset-fuseki` already exist and are the SPI the current `solution-design-specification.md` §4.1 describes. Nothing in the epic states whether P0.5 renames these in place, replaces them outright, or the two coexist during a migration window. P0.5.1 cannot start cleanly until this is answered — flagged as a pre-P0.5 decision point in [phase-0-plan.md](../plans/phase-0-plan.md).
- **`apps/surface-studio`/`apps/mork-bench` vs `apps/surface-contract-studio`/`apps/mork-review-workbench`.** Part 1's target topology uses shorter names than the apps that already exist and that P0.7.5's walking skeleton explicitly reuses ("Studio calls it"). Whether this is a rename, a fresh pair of apps, or Part 1 simply using informal short names is not stated. Lower urgency than the SPI question (Phase 1's P1.10 is the first slice that actually touches app naming), flagged the same way.

## Risks specific to starting this phase

- P0.1 alone is 15 decision slices, several explicitly flagged by the epic as "expect to reject and re-run" (P0.1.1, P0.1.3). A phase-0 plan that assumes single-pass ADR ratification under-forecasts review cost.
- P0.4 (canonicalisation) is named by the epic itself as "the single most load-bearing library in the system" and appears on the critical path summary (Part 14) alongside P0.5.8 and P2.1. Phase 0's own internal sequencing should protect P0.4's review bandwidth accordingly.
- The coordination-realm reconstruction proof (P0.6.4 — drop the coordination store, restart, prove convergence) is the executable test of A74's central claim. If it fails, it is not a phase-0 bug, it is evidence A74 needs revisiting, and that would ripple through the whole epic. Flagged, not resolved, here.
