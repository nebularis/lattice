<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Applied Insurance Reference - Status

**Unit ID:** `applied-insurance-reference` (epic)
**Plan:** [applied-insurance-reference.md](../plans/applied-insurance-reference.md)
**Machines, branches and merges:** [applied-insurance-reference-lanes.md](../plans/applied-insurance-reference-lanes.md)
**How to use this record:** lanes §5. In short: each machine edits only its own section. Machine R
also writes the round, the merge log and the phase table. Slice handoff notes go in the slice's
Validation Pack, never here.

---

## Round

**Current round:** 1 (machine R advances it when a round's merges are done)
**Branches ready to work on:** `air/3.1-flat-hierarchy` (R), `air/1.1-layout` (S), `air/2.1-peril-spec` (S).
Created and pushed by the human. Their detailed briefs (phase plans and Validation Pack
skeletons) were written on `main` and are merged into each branch before work starts.
**Briefs ready on `main`:** AIR-1.1, AIR-2.1, AIR-3.1.
**Briefs to draft before their branches (lanes §1):** AIR-1.2 and AIR-3.2, the next branches
after round 1. Every later slice is still an outline.

## Machine R

**Position:** round 1. AIR-1.1, AIR-2.1 and AIR-3.1 detailed to implementation level on `main`.
AIR-3.1 starts when the human switches R to autonomous mode on `air/3.1-flat-hierarchy`.
**Last updated:** 2026-09-26
**Blockers:** none

| Seq | Slice | Branch | State | Note |
|---|---|---|---|---|
| 2 | AIR-3.1 | `air/3.1-flat-hierarchy` | waiting for branch | brief: Phase 3 plan, AIR-3.1 in detail |
| 8 | AIR-3.2 | `air/3.2-set-readings` | waiting | |
| 13 | AIR-3.3 | `air/3.3-readings-swrl-owl` | waiting | |
| 21 | AIR-3.5 | `air/3.5-m2-check` | waiting | |
| 23+ | substrate ADRs, S1, S2, S4, S5, S7 | `air/s<n>-<slug>` | waiting | ADRs drafted in round 4 |

Verifying queue (S branches handed over and not yet merged): none.

## Machine S

**Position:** round 0. Waiting for the human to create the round 0 branches, then building AIR-1.1
and AIR-2.1.
**Last updated:** 2026-09-26
**Blockers:** none

| Seq | Slice | Branch | State | Note |
|---|---|---|---|---|
| 3 | AIR-1.1 | `air/1.1-layout` | waiting for branch | |
| 4 | AIR-1.2 | `air/1.2-shared-contracts` | waiting | |
| 5 | AIR-2.1 | `air/2.1-peril-spec` | waiting for branch | |
| 6 | AIR-2.2 | `air/2.2-characteristics` | waiting | |
| 7 | AIR-4.1 | `air/4.1-exposure-core` | waiting | |
| 9 | AIR-2.3 | `air/2.3-causes-n-t-e` | waiting | |
| 10 | AIR-2.4 | `air/2.4-causes-h-p-c-f-l` | waiting | |
| 11 | AIR-4.2 | `air/4.2-zones-attributes` | waiting | |
| 12 | AIR-4.4 | `air/4.4-loss-history` | waiting | |
| 14 | AIR-2.6 | `air/2.6-intensity` | waiting | |
| 15 | AIR-2.7 | `air/2.7-pools-editions` | waiting | |
| 16 | AIR-4.3 | `air/4.3-exposure-units` | waiting | |
| 17 | AIR-4.5 | `air/4.5-liability` | waiting | |
| 18 | AIR-2.5 | `air/2.5-collections` | waiting | |
| 19 | AIR-3.4 | `air/3.4-crosswalk` | waiting | |
| 20 | AIR-4.6 | `air/4.6-market-profiles` | waiting | |
| 22 | AIR-6.1 | `air/6.1-submission` | waiting | |
| 23+ | S6 | `air/s6-spatial-guidance` | waiting | |

## Merge log (machine R only)

| Seq | Slice | Round | Merged | `LOG.md` |
|---|---|---|---|---|
| 1 | AIR-0.1 | — | `3377a71` | signed off |

## Phases (machine R only)

| Phase | Plan | State |
|---|---|---|
| 0 Decisions | [plan](../plans/applied-insurance-reference-phase-0.md) | ✅ complete |
| 1 Module split | [plan](../plans/applied-insurance-reference-phase-1.md) | ⏳ |
| 2 Peril vocabulary | [plan](../plans/applied-insurance-reference-phase-2.md) | ⏳ |
| 3 Readings and crosswalks | [plan](../plans/applied-insurance-reference-phase-3.md) | ⏳ |
| 4 Exposure | [plan](../plans/applied-insurance-reference-phase-4.md) | ⏳ |
| 5 Contract module | [plan](../plans/applied-insurance-reference-phase-5.md) | 🅿️ deferred until Open CBAA integration of 1 to 4 (D2) |
| 6 Submission, claims | [plan](../plans/applied-insurance-reference-phase-6.md) | ⏳ |
| S Substrate track | [plan](../plans/applied-insurance-reference-substrate.md) | ⏳ |

## History

- 2026-09-26: sketches moved into `docs/developer/sketches/`, epic and phase plans written,
  `prl:canTrigger` corrected to a sub-property of `skos:semanticRelation`.
- 2026-09-26: scope decisions D1 to D4 and layout decisions D5 to D9 (epic §5). D10 reversed by
  D11, D12 added after the Eligibility walkthrough.
- 2026-09-26: ADRs A-98 (with addendum), A-99, A-100, A-102 and A-103 Accepted. A-101 reserved for
  Phase 5.
- 2026-09-26: AIR-0.1 signed off and merged (`3377a71`). Plan rewritten for two machines (R:
  Claude Code, Copilot Pro+. S: Copilot Business, no runtime, pull only). Status record
  restructured into per-machine sections, one epic record replacing per-phase records.
