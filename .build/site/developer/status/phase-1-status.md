<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Phase 1 — Graph-Primary Core and the Deployment Plane (Status)

**Unit type:** Phase
**Unit ID:** `phase-1`
**Status:** ⏳ Not started — blocked on Phase 0 exit gate
**Last updated:** 2026-09-22
**Plan:** [phase-1-plan.md](../plans/phase-1-plan.md)
**Sketch:** [phase-1-sketch.md](../sketches/phase-1-sketch.md)

---

## Current state

Decomposed from the epic on 2026-09-22. No slice has started. Cannot start until [phase-0-status.md](phase-0-status.md) records its exit gate as passed.

## Blockers

| Blocker | Detail |
|---|---|
| Phase 0 exit gate | Hard dependency, per the epic |
| SPI inventory doc placement | See [phase-1-plan.md §2](../plans/phase-1-plan.md#2-documentation-obligations--docsarchitecture) — confirm `docs/architecture/spi-inventory.md` before P1.11.2 |
| `apps/*` naming | Carried from Phase 0's decomposition findings — first actually touched by P1.10 |

## Milestone tracker

| Milestone | Demonstrable outcome | Status |
|---|---|---|
| M2 | Graph-primary lifecycle (Surface revision authored/reviewed/approved entirely in the graph, no relational ledger) | Not demonstrated |
| M3 | Pack + activation (signed pack, activated with diff/SHADOW/promote/rollback, Activation Console) | Not demonstrated |

## Next steps

1. Wait for Phase 0 exit gate.
2. Confirm SPI inventory doc placement and `apps/*` naming (low urgency, cheap to resolve now).
3. Begin P1.1 (Surface lifecycle → graph).
