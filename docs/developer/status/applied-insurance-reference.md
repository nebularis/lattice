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
**One trip for machine S (lanes §4, revised 2026-10-13):** AIR-2.0, 2.2, 4.1, 2.6, 2.3, 2.4, 4.2,
4.3, 4.4, 2.7, 4.5, 2.5, 3.4, 3.5, 4.6, 6.1, then S6. The branch is created only when every brief
is written, and comes to R once, when the trip is done.
**Briefs written:** every slice of the trip, the last on 2026-10-13. Every question of the trip is
decided (2026-10-14), so the branch can be created. AIR-3.3 has a brief that is blocked (phase 3
plan).
**Concurrent work:** from round 3, machine R also builds the normative-rule-substrate unit, and
from 2026-09-30 the computable-contract-substrate unit (CCS), which took over NRS N4, and on
2026-10-10 N1, N2 and N5 as well. AIR-3.3 waits for CCS HQ-6a.2 to merge and for AIR-3.3-Q1 (phase 3 plan),
and lands before CCS's N1 and C13. NRS N9 waits for Phase 2, substrate S2 is authored with CCS
C9b3, and CCS C9 merges before Phase 5 (epic §3b). The trip's imports stay pinned to `main` at the
branch point, and R re-pins once at the merge (lanes §6 step 4).

## Machine R

**Position:** round 3. Rounds 1 and 2 complete, Phase 1 complete. Every brief of the one trip
written and every question decided (2026-10-14). Next: the maintainer creates and pushes
`air/applied-reference` from `main`, and R verifies S's bundle when the trip is done. AIR-3.3 waits
on CCS HQ-6a.2. NRS N2 moved to CCS on 2026-10-10 (NRS NQ-2).
**Last updated:** 2026-10-14
**Blockers:** AIR-3.3 waits for CCS HQ-6a.2 to merge and for AIR-3.3-Q1.

| Seq | Slice | Branch | State | Note |
|---|---|---|---|---|
| 2 | AIR-3.1 | `air/3.1-flat-hierarchy` | merged | tags `eligibility-vocab-v0.7.0`, `executable-v0.6.0` |
| 8 | AIR-3.2 | `air/3.2-set-readings` | merged | eight tags (Validation Pack Results) |
| 13 | AIR-3.3 | `air/3.3-readings-swrl-owl`, created from `main` after HQ-6a.2 merges | waiting | brief blocked on AIR-3.3-Q1 |
| 23+ | substrate ADRs, S1, S2, S4, S5, S7 | `air/s<n>-<slug>` | waiting | ADRs drafted in round 4 |

Verifying queue (S slices handed over and not yet merged): none.

## Machine S

**Position:** round 3, the one trip. AIR-1.1, AIR-2.1, AIR-1.2, AIR-2.0 and AIR-2.2 built on
`air/applied-reference` (not yet handed to R). Next: AIR-4.1.
**Last updated:** 2026-10-14
**Blockers:** none.

| Seq | Slice | State | Note |
|---|---|---|---|
| 3 | AIR-1.1 | merged | set by R. No version bumps, no tags |
| 4 | AIR-1.2 | merged | set by R. Tags `applied-classification-v0.1.0`, `applied-classification-vocab-v0.1.0`, `insurance-common-v0.1.0`, `insurance-common-vocab-v0.1.0` |
| 5 | AIR-2.1 | merged | set by R: three shape defects fixed at verification. Tags `applied-insurance-peril-shapes-v0.1.0`, `insurance-peril-v0.1.0`, `insurance-peril-vocab-v0.1.0` |
| 5a | AIR-2.0 | built | `insurance/common` and `insurance/peril` converted to literate READMEs, the extractor extended (nested `--layer` paths, `@output-file` on `turtle-vocab`), `prl:DocumentationShape` added (shapes `0.1.0` → `0.2.0`). No spec/vocab version change. [Validation Pack](../validation/applied-insurance-reference-2.0.md) |
| 6 | AIR-2.2 | built | peril spec `0.4.0`→`0.5.0` (common import, four sub-property axioms), peril-vocab `0.4.0`→`0.5.0` (70 characteristic/companion concepts, four `voc:boundScheme` bindings). Lists amended beyond the first brief (Intentional/Economic agency, 13 more mechanisms, consequence widened to 19). [Validation Pack](../validation/applied-insurance-reference-2.2.md) |
| 7 | AIR-4.1 | in progress | brief refreshed 2026-10-13, literate |
| 9 | AIR-2.3 | ready | after AIR-2.6 |
| 10 | AIR-2.4 | ready | |
| 11 | AIR-4.2 | ready | brief written 2026-10-13 |
| 12 | AIR-4.4 | ready | brief written 2026-10-13. After AIR-4.3 |
| 14 | AIR-2.6 | ready | before AIR-2.3 |
| 15 | AIR-2.7 | ready | brief written 2026-10-13 |
| 16 | AIR-4.3 | ready | brief written 2026-10-13, before AIR-4.4 |
| 17 | AIR-4.5 | ready | brief written 2026-10-13 |
| 18 | AIR-2.5 | ready | brief written 2026-10-13 |
| 19 | AIR-3.4 | ready | brief written 2026-10-13, AIR-3.4-Q1 and Q2 decided 2026-10-14 |
| 20 | AIR-4.6 | ready | brief written 2026-10-13 |
| 21 | AIR-3.5 | ready | moved from R on 2026-10-13 (lanes §2). Brief written the same day |
| 22 | AIR-6.1 | ready | brief written 2026-10-13, AIR-6.1-Q1 decided 2026-10-14 |
| 23+ | S6 | ready | brief written 2026-10-13 (substrate plan) |

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
- 2026-10-13: re-planned as one trip for S (lanes §1, §4): versioning governs `main`, not a
  branch, and the applied modules have no importer on `main` outside AIR, so S builds every slice
  that does not wait on CCS or NRS before the branch comes to R once. AIR-3.5 moves to S. Every brief
  is written on R first. Decided the same day: agency values `Intentional` and `Economic`, thirteen
  mechanisms and four consequences added to AIR-2.2 (Q1, Q2, Q5), P wording-defined (Q3), latent
  onset for wrongful acts and professional error (Q4), the cause characteristics by inheritance with
  overrides, a sample of definitions reviewed on R before S drafts the rest (Q6), 10-minute winds for
  typhoon and severe tropical cyclone (Q7), heat and cold waves index-based (Q8), the hours-clause
  windows (Q9), units in `insurance/common` aligned to QUDT (Q10). Every AIR module is literate, and
  every concept documents the standards it follows in `skos:note` (AIR-2.0, a new first slice).
  AIR-2.6 now precedes AIR-2.3.
- 2026-10-13: earlier private designs for exposure, catastrophe modelling and reference data
  reviewed against the plan. Decided the same day (R1 to R10): a class of business contract in
  `insurance/common`, industry, domicile and legal form on the legal entity, a loss experience
  stating period, source and completeness, cover history events and summary terms, requirement
  strength and an attachment measure, attribute types for all eight profile families with shapes
  for two, eight consequences and the tropical depression concept (287 causes), catastrophe model
  results, multi-insured portfolios and licences out of scope (epic §7), a grouping property in
  AIR-4.3, and two programme roles. Also decided: AIR-4.2 (Q13) and AIR-4.4 (Q11, Q12) proposals,
  every active ISO 4217 currency in `insurance/common` with AIR-2.6 (Q14). AIR-4.3 now precedes
  AIR-4.4. AIR-4.2 and AIR-4.4 briefs written.
- 2026-10-13: the N.MET sample definitions accepted. Briefs written for AIR-4.3, 2.7, 2.5, 3.4, 3.5,
  4.5, 4.6, 6.1 and S6, with their Validation Packs, so every slice of the trip has a brief. Three
  questions remain open, and the briefs follow their leanings: AIR-3.4-Q1 (crosswalk OED's peril
  codes and an example house list, and not yet the CBAA cause-of-loss list), AIR-3.4-Q2 (a lifted
  value is a derived `aeo:liftedPeril` beside the recorded code), AIR-6.1-Q1 (requests, answers as
  assessments and derived gaps, not the rest of the earlier designs' question bridge). AIR-2.7
  adds the peril contract's missing fallback binding to the cause scheme.
- 2026-10-14: AIR-6.1-Q1 walked through and settled at its leaning. What AIR-6.1 does not build,
  with everything else the epic leaves to consumers, is collected in
  [air-leftovers.md](../plans/air-leftovers.md).
- 2026-10-14: AIR-3.4-Q1 and AIR-3.4-Q2 decided at their leanings. No question of the trip remains
  open, so `air/applied-reference` can be created.
