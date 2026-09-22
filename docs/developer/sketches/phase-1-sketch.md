<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Phase 1 — Graph-Primary Core and the Deployment Plane (Sketch)

**Unit type:** Phase (of Epic `lattice-platform-development`)
**Unit ID:** `phase-1`
**Promotes to:** [phase-1-plan.md](../plans/phase-1-plan.md)
**Status record:** [phase-1-status.md](../status/phase-1-status.md)
**Depends on:** [phase-0](phase-0-sketch.md) exit gate (hard — no slice here starts before Phase 0's ADRs are ratified and M0/M1 pass)

## Why the boundary is here

Phase 1 is "move everything that currently lives in a relational ledger into the graph, then stand up the machinery to package and activate that graph for a tenant." The epic groups these because they share one property: every one of them is a `T-GPM` (graph-primary migration) of an *existing, already-implemented* relational entity (Surface lifecycle, release ledger, MORK review snapshots, governance ledger), plus the *new* deployment-plane capability (tenancy, packs, activation) that only makes sense once the graph is authoritative. That is a coherent phase boundary and this decomposition does not redraw it.

The epic itself (Part 5, §0.5 rolling-wave note) already says Phase 0 and Phase 1 are "specified at slice granularity below and are ready to execute." Unlike Phase 2–4, Phase 1 does not need a rolling-wave placeholder — it can be decomposed to the same depth as Phase 0.

## What stays exactly as the epic wrote it

[phase-1-plan.md](../plans/phase-1-plan.md) points back to [Part 5 of the epic](../plans/lattice-platform-agentic-development-v0.2.md#part-5--phase-1-graph-primary-core-and-the-deployment-plane) for the full P1.1–P1.11 slice tables, rather than duplicating roughly 50 rows a second time.

## What decomposition adds

Phase 1 is the one phase where the epic itself already names the exact `solution-design-specification.md` sections to update (P1.11.1: §1, §2.2, §4.1, §4.5, §4.6, §7.2) — that close-out slice is kept as written. What was missing, and what [phase-1-plan.md](../plans/phase-1-plan.md) adds, is:

- The README obligations for the phase's new `platform/*` modules (`mork-review`, `governance-ledger`, `tenancy`, `pack-builder`, `activation-controller`, `change-feed`) and new frontend packages (`@lattice/ui-kit`, `@lattice/client-ts`), none of which the epic's slice tables call out as README-producing even though each is a new subproject per copilot-instructions' documentation rule.
- A named home for the SPI inventory document P1.11.2 produces (A71's OSS/commercial boundary doc) — the epic says "SPI inventory table, TCK coverage per SPI, OSS/commercial boundary doc" but does not say where it lives. This plan places it under `docs/architecture/` as a normative platform document, consistent with every other cross-cutting design record, and flags that placement for confirmation rather than asserting it as settled.

## Risks specific to starting this phase

- P1.2.2 deletes the old conflict-rejection path and asserts the new behaviour on the old scenarios "with the test asserting the new behaviour" — this is exactly the kind of change the non-weakening rule exists to catch if done carelessly. The phase-1 plan should require the diff against Phase 0's test inventory to be explicit at this slice, not just at phase close.
- P1.9 (activation controller) is the first slice group with a real portability headline test (P1.9.3: a pack requiring `MULTI_GRAPH_ATOMIC_WRITE` is refused on Fuseki and accepted on TDB2). If Phase 0's capability report (P0.5.13) is thin, this test cannot be written honestly — a dependency worth checking explicitly at the P0/P1 boundary, not assumed.
- Two Phase 0 decomposition findings carry forward here unresolved: the `apps/surface-studio`/`apps/mork-bench` naming question (first actually touched by P1.10) and confirmation of whichever `graph-spi` decision Phase 0 made (P1.1–P1.6's `conditionalWrite`-based migrations depend on it directly).
