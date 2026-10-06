<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Formal Methods: Status

**Unit ID:** `formal-methods` (epic)
**Status:** 📝 Proposed. Sketches, epic plan and Phase 0 plan drafted, awaiting human review
**Last updated:** 2026-10-06
**Plan:** [formal-methods.md](../plans/formal-methods.md), [phase 0](../plans/formal-methods-phase-0.md)
**Sketches:** [formal-methods.md](../sketches/formal-methods.md),
[adequacy and architecture](../sketches/formal-adequacy-and-architecture.md),
[assurance records](../sketches/assurance-records.md),
[instrument assurance](../sketches/instrument-assurance.md),
[reference evaluator](../sketches/reference-evaluator.md),
[toolchain workers](../sketches/formal-toolchain-workers.md)

## Current position

Nothing is built. Phase 0, the prover experiment, is the first step. CCS remains the active unit,
with C7c next.

**Next action, for the human:** review the plans, then approve the toolchain installs (Rocq through
opam, Isabelle) and the spike location for Phase 0.

## Phase board

| Phase | State | Blocked on |
|---|---|---|
| 0 Prover experiment | not started | human review, toolchain installs |
| 1 Decisions and ADRs | not started | gate 0 |
| 2 Cheap wins | not started | phase 1 |
| 3 Kernel, foundations, adequacy | not started | phase 1 |
| 4 Toolchain workers | not started | phase 3 |
| 5 Eligibility | not started | phases 3 and 4 |
| 6 Reference evaluator, conformance kit | not started | phases 3 and 4, CCS C11a |
| 7 Instrument assurance | not started | phases 5 and 6, CCS C8a |
| 8 Monitors, compilers, Surface, MORK, assembly | not started | phase 7, insurml-alignment phase 4 |

## Phase 0

| Slice | State |
|---|---|
| FM-0.1 brief | not started |
| FM-0.2 Rocq track | not started |
| FM-0.3 Isabelle track | not started |
| FM-0.4 worker smoke test and benchmark | not started |
| FM-0.5 report | not started |

## Decisions

| # | State |
|---|---|
| FM-D1 | open, settled by Phase 0 |
| FM-D2 to FM-D10 | open |

## Estimates and actuals

| Phase | Estimate (tokens) | Actual |
|---|---|---|
| 0 | 0.4M to 0.8M | |
| sketches and plans (2026-10-06) | not estimated | not recorded |
