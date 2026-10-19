<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Phase 2 — Ingestion and Query Planes (Status)

**Unit type:** Phase
**Unit ID:** `phase-2`
**Status:** ⏳ Rolling-wave placeholder — not started, full expansion awaits P1.11.3
**Last updated:** 2026-09-23
**Plan:** [phase-2-plan.md](../plans/phase-2-plan.md)
**Sketch:** [phase-2-sketch.md](../sketches/phase-2-sketch.md)

---

## Current state

Decomposed from the epic on 2026-09-22 as a rolling-wave placeholder, per the epic's own methodology (Part 0.5). The persistence-compiler integration across P2.1/P2.3/P2.4 is already fully designed (see [epic Part 6](../plans/lattice-platform-agentic-development-v0.2.md#part-6--phase-2-ingestion-and-query-planes)); the rest awaits Phase 1's store-SPI learnings.

## Blockers

| Blocker | Detail |
|---|---|
| Phase 1 exit gate | Hard dependency |
| Full VP-level slice expansion | Scheduled at P1.11.3, not yet done |
| ~~Identity-profile resolution in `tools/persistence`~~ | Resolved 2026-09-23: [`persistence-compiler-iri-sync`](persistence-compiler-iri-sync.md) Slice 3 resolves `dal:IdentityProfile` per resource role, which P2.1.5 reads. Minting stays in P2.1.5 |

## Milestone tracker

| Milestone | Demonstrable outcome | Status |
|---|---|---|
| M4 | Ingestion (deterministic mapping plan compiled, bad payload quarantines, replay-by-digest fixes it) | Not demonstrated |
| M5 | Query + lineage | Not demonstrated |
| M6 | Content pipeline | Not demonstrated |

## Changes to already-specified slices (2026-09-23)

The persistence caller contract that P2.1.4a, P2.3.1 and P2.3.6 rely on changed after the guide's post-3866b21 remediation and `persistence-compiler-iri-sync` Slice 2: payload and log-bucket lists are Mustache request-time slots, every write binds a request digest and is confirmed on the primary, and some targets need `bootstrap-version-row` at id allocation. The epic's Part 6 rows were updated to match, and the contract is documented in `tools/persistence/README.md`, "Using the generated SPARQL directly". P2.1.5 was corrected to follow ADR-A82's identity profiles.

## Next steps

1. Wait for Phase 1 exit gate.
2. At P1.11.3, expand this phase to full VP-level detail and update this plan/status accordingly.
