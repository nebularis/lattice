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

**Current round:** 3 (machine R advances it when a round's merges are done). Round 1 merged
AIR-3.1, AIR-1.1 and AIR-2.1. Round 2 merged AIR-3.2 and AIR-1.2.
**Branches ready to work on:** none yet. `air/2.2-characteristics` and `air/4.1-exposure-core`
wait for the maintainer to create them, as does `air/3.3-readings-swrl-owl`.
**Briefs ready on `main`:** AIR-1.1, AIR-2.1, AIR-3.1, AIR-1.2, AIR-3.2, AIR-2.2, AIR-4.1, AIR-3.3.
**Briefs to draft before their branches (lanes §1):** round 4's (AIR-2.3, AIR-2.4, AIR-4.2,
AIR-4.4).
**Concurrent work:** from round 3, machine R also builds the normative-rule-substrate unit, and
from 2026-09-30 the computable-contract-substrate unit (CCS), which took over NRS N4, and on
2026-10-10 N1, N2 and N5 as well. R verifies S's bundles first, AIR-3.3 lands before CCS's N1 and
C13, NRS N9 waits for Phase 2, substrate S2 is authored with CCS C9b3, and CCS C9 merges before
Phase 5 (epic §3b).

## Machine R

**Position:** round 3. Rounds 1 and 2 complete, Phase 1 complete. AIR-2.2, AIR-4.1 and AIR-3.3
briefs drafted. Next: AIR-3.3 once its branch exists. NRS N2 moved to CCS on 2026-10-10 (NRS NQ-2).
**Last updated:** 2026-09-30
**Blockers:** none

| Seq | Slice | Branch | State | Note |
|---|---|---|---|---|
| 2 | AIR-3.1 | `air/3.1-flat-hierarchy` | merged | tags `eligibility-vocab-v0.7.0`, `executable-v0.6.0` |
| 8 | AIR-3.2 | `air/3.2-set-readings` | merged | eight tags (Validation Pack Results) |
| 13 | AIR-3.3 | `air/3.3-readings-swrl-owl` | waiting for branch | brief on `main` |
| 21 | AIR-3.5 | `air/3.5-m2-check` | waiting | |
| 23+ | substrate ADRs, S1, S2, S4, S5, S7 | `air/s<n>-<slug>` | waiting | ADRs drafted in round 4 |

Verifying queue (S branches handed over and not yet merged): none.

## Machine S

**Position:** round 3. AIR-1.1, AIR-2.1 and AIR-1.2 merged. Next: AIR-2.2 and AIR-4.1, once R has
drafted their briefs and we have created their branches.
**Last updated:** 2026-09-26
**Blockers:** waiting for the `air/2.2-characteristics` and `air/4.1-exposure-core` branches.

| Seq | Slice | Branch | State | Note |
|---|---|---|---|---|
| 3 | AIR-1.1 | `air/1.1-layout` | merged | set by R. No version bumps, no tags |
| 4 | AIR-1.2 | `air/1.2-shared-contracts` | merged | set by R. Tags `applied-classification-v0.1.0`, `applied-classification-vocab-v0.1.0`, `insurance-common-v0.1.0`, `insurance-common-vocab-v0.1.0` |
| 5 | AIR-2.1 | `air/2.1-peril-spec` | merged | set by R: three shape defects fixed at verification. Tags `applied-insurance-peril-shapes-v0.1.0`, `insurance-peril-v0.1.0`, `insurance-peril-vocab-v0.1.0` |
| 6 | AIR-2.2 | `air/2.2-characteristics` | waiting for branch | brief on `main` |
| 7 | AIR-4.1 | `air/4.1-exposure-core` | waiting for branch | brief on `main` |
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
