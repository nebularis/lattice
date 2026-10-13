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

**Current round:** 3 (machine R advances it when a trip's merges are done). Round 1 merged
AIR-3.1, AIR-1.1 and AIR-2.1. Round 2 merged AIR-3.2 and AIR-1.2.
**Branch:** one for all of S's slices, `air/applied-reference` (lanes §2 and §3, revised
2026-10-13). The per-slice branches of rounds 1 to 3 were all merged into `main` and are deleted.
**Trip 1 for machine S, in this order:** AIR-2.2, then AIR-4.1. Both briefs are on the branch and
use the versions of `main` at `69cb7675`. S stops after AIR-4.1 and hands over.
**Briefs ready on the branch:** AIR-1.1, AIR-2.1, AIR-3.1, AIR-1.2, AIR-3.2 (all merged), AIR-2.2,
AIR-4.1. AIR-3.3 has a brief that is blocked (phase 3 plan).
**Briefs to draft before trip 2 (lanes §1):** AIR-2.3, AIR-2.4, AIR-4.2 and AIR-4.4.
**Concurrent work:** from round 3, machine R also builds the normative-rule-substrate unit, and
from 2026-09-30 the computable-contract-substrate unit (CCS), which took over NRS N4, and on
2026-10-10 N1, N2 and N5 as well. R verifies S's bundles before continuing CCS or NRS slices, AIR-3.3
waits for CCS HQ-6a.2 to merge and for AIR-3.3-Q1 (phase 3 plan), and lands before CCS's N1 and
C13. NRS N9 waits for Phase 2, substrate S2 is authored with CCS C9b3, and CCS C9 merges before
Phase 5 (epic §3b). CCS bumps of Foundation, Vocabulary, Quantification and Party force a re-pin of
the applied modules at each sync (lanes §6 step 4), so trips stay short.

## Machine R

**Position:** round 3. Rounds 1 and 2 complete, Phase 1 complete. AIR-2.2, AIR-4.1 and AIR-3.3
briefs drafted, the first two refreshed on 2026-10-13. Next: draft the trip 2 briefs while S builds
trip 1. NRS N2 moved to CCS on 2026-10-10 (NRS NQ-2).
**Last updated:** 2026-10-13
**Blockers:** AIR-3.3 waits for CCS HQ-6a.2 to merge and for AIR-3.3-Q1.

| Seq | Slice | Branch | State | Note |
|---|---|---|---|---|
| 2 | AIR-3.1 | `air/3.1-flat-hierarchy` | merged | tags `eligibility-vocab-v0.7.0`, `executable-v0.6.0` |
| 8 | AIR-3.2 | `air/3.2-set-readings` | merged | eight tags (Validation Pack Results) |
| 13 | AIR-3.3 | `air/3.3-readings-swrl-owl`, created from `main` after HQ-6a.2 merges | waiting | brief blocked on AIR-3.3-Q1 |
| 21 | AIR-3.5 | `air/3.5-m2-check` | waiting | |
| 23+ | substrate ADRs, S1, S2, S4, S5, S7 | `air/s<n>-<slug>` | waiting | ADRs drafted in round 4 |

Verifying queue (S slices handed over and not yet merged): none.

## Machine S

**Position:** round 3, trip 1. AIR-1.1, AIR-2.1 and AIR-1.2 merged. Next: AIR-2.2, then AIR-4.1,
on `air/applied-reference`.
**Last updated:** 2026-10-13
**Blockers:** none. The branch is pushed before S starts.

| Seq | Slice | State | Note |
|---|---|---|---|
| 3 | AIR-1.1 | merged | set by R. No version bumps, no tags |
| 4 | AIR-1.2 | merged | set by R. Tags `applied-classification-v0.1.0`, `applied-classification-vocab-v0.1.0`, `insurance-common-v0.1.0`, `insurance-common-vocab-v0.1.0` |
| 5 | AIR-2.1 | merged | set by R: three shape defects fixed at verification. Tags `applied-insurance-peril-shapes-v0.1.0`, `insurance-peril-v0.1.0`, `insurance-peril-vocab-v0.1.0` |
| 6 | AIR-2.2 | ready | trip 1, first. Brief refreshed 2026-10-13 |
| 7 | AIR-4.1 | ready | trip 1, second. Brief refreshed 2026-10-13 |
| 9 | AIR-2.3 | waiting for brief | trip 2 |
| 10 | AIR-2.4 | waiting for brief | trip 2 |
| 11 | AIR-4.2 | waiting for brief | trip 2 |
| 12 | AIR-4.4 | waiting for brief | trip 2 |
| 14 | AIR-2.6 | waiting | |
| 15 | AIR-2.7 | waiting | |
| 16 | AIR-4.3 | waiting | |
| 17 | AIR-4.5 | waiting | |
| 18 | AIR-2.5 | waiting | |
| 19 | AIR-3.4 | waiting | |
| 20 | AIR-4.6 | waiting | |
| 22 | AIR-6.1 | waiting | |
| 23+ | S6 | waiting | |

## Merge log (machine R only)

| Seq | Slice | Round | Merged | Gate |
|---|---|---|---|---|
| 1 | AIR-0.1 | — | `3377a71` | signed off |
| 2 | AIR-3.1 | 1 | fast-forward to the head of `air/3.1-flat-hierarchy` | signed off |
| 3 | AIR-1.1 | 1 | fast-forward to `651fbfa` | signed off |
| 5 | AIR-2.1 | 1 | fast-forward to the head of `air/2.1-peril-spec` | signed off |
| 8 | AIR-3.2 | 2 | fast-forward to the head of `air/3.2-set-readings` | signed off |
| 4 | AIR-1.2 | 2 | fast-forward to the head of `air/1.2-shared-contracts` | signed off |

## Phases (machine R only)

| Phase | Plan | State |
|---|---|---|
| 0 Decisions | [plan](../plans/applied-insurance-reference-phase-0.md) | ✅ complete |
| 1 Module split | [plan](../plans/applied-insurance-reference-phase-1.md) | ✅ AIR-1.1 and AIR-1.2 merged |
| 2 Peril vocabulary | [plan](../plans/applied-insurance-reference-phase-2.md) | 🚧 AIR-2.1 merged |
| 3 Readings and crosswalks | [plan](../plans/applied-insurance-reference-phase-3.md) | 🚧 AIR-3.1 and AIR-3.2 merged |
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
- 2026-09-30: AIR-2.2, AIR-4.1 and AIR-3.3 briefs and Validation Pack skeletons written and
  merged into `main` (`b2afc8e`, `532aadd`). The round 3 branches held only those commits.
- 2026-10-13: epic reconvened after the pause for CCS and FML (note
  [air-epic-reconvene](../notes/air-epic-reconvene.md)). Every `air/*` branch was found to be an
  ancestor of `origin/main`, so all eight are deleted. S's slices now share one branch,
  `air/applied-reference` (lanes revised). AIR-2.2 and AIR-4.1 briefs re-pinned to the layer
  versions of `main` at `69cb7675`. AIR-3.3 is blocked on CCS HQ-6a.2 and AIR-3.3-Q1. Trip 1 for
  S is AIR-2.2 then AIR-4.1.
