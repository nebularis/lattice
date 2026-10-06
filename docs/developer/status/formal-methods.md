<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Formal Methods: Status

**Unit ID:** `formal-methods` (epic)
**Status:** ✅ Track D complete on `fm/phase-0-prover-spike` (D0-D4, plus the PF1/PF4 fixes from the
macOS reproduction). **FM-D1 decided 2026-10-06 by the human: Isabelle.** FM-D10 decided:
Haskell and Scala both adopted as code-generation targets. The human has also decided to
continue track E's work on this same branch rather than cutting a fresh one, deferring the merge
to `main` until track E work is ready (a deviation from plan §7.1's "brief, report and status
record reach `main` regardless", recorded here, not yet actioned). Gate D is not yet fully
closed: two criteria remain open, see §Gate D below
**Last updated:** 2026-10-06
**Plan:** [formal-methods.md](../plans/formal-methods.md), [the prover spike](../plans/formal-methods-phase-0.md)
**Review response:** [formal-methods-review-response.md](../notes/formal-methods-review-response.md)
**Sketches:** [formal-methods.md](../sketches/formal-methods.md),
[adequacy and architecture](../sketches/formal-adequacy-and-architecture.md),
[assurance records](../sketches/assurance-records.md),
[instrument assurance](../sketches/instrument-assurance.md),
[reference evaluator](../sketches/reference-evaluator.md),
[toolchain workers](../sketches/formal-toolchain-workers.md)

## Current position

Track D is complete. FM-D1 is decided: Isabelle/HOL is the prover for track E. The tracks remain
staggered as planned: C1, C2, B1 and B2 alongside the spike, A1 to A4 after gate D, B4 with C11a
and C12, C3 with C13a. CCS remains the active unit, with C7c branched. Track E has its own plan,
sketch and status record now ([formal-methods-track-e.md](formal-methods-track-e.md)). FM-D2 is
decided too (ADR-A-FM2: `tools/proofs/`), and E1.0/E1.1 are done: `tools/proofs/eligibility/`
compiles and gates clean, natively, matching track D's spike evidence exactly. E1.2 was attempted
and found blocked on a missing normative source (its own status record), not merely unstarted.
Track C has its own plan, sketch and status record now too
([formal-methods-track-c.md](formal-methods-track-c.md)): C1 (an Alloy skeleton) and C2 (binding
resolution with scheme composition, ahead of CCS's HQ-4 and insurml-alignment's IMA-D4a, both read
directly from `main` and confirmed genuinely unresolved) are starting.

**Next action, for the human:** none blocking track C. The two remaining Gate D gaps (below) are
deliberately deferred, not blocking.

## Gate D (phase-0 plan §9)

| Criterion | State |
|---|---|
| the report is complete, every measure scored and evidence linked | done |
| FM-D1 decided, or the prover abandoned, with reasons if the rule is overruled | done: Isabelle, via the corrected decision rule (not an overrule of it -- M9/M5/M6 were corrected first, the rule's outright-win outcome was then followed) |
| FM-D10's Haskell question answered | done: Haskell and Scala both adopted |
| the epic §6 abandonment thresholds revised with the measurements | **open**. The spike's actual M0/M3 figures (e.g. Isabelle's MINOR-change repair at +18/-6 lines) have not yet been fed back into the epic's standing thresholds |
| the smoke suite passes on macOS, Windows and Linux by the image route, for the chosen prover's stack | **open, and currently unmet**. Isabelle has no image route in this spike at all (epic §4 table; `driver.py` refuses `--route image` for `isabelle` by design). Only Rocq (not chosen) has a working image. Building one is new work, not yet started |
| no build output, binary, image, certificate or toolchain file tracked on the branch | holds (checked after every commit this track) |
| the report and the status record are on `main` | **open**. Per plan §7.1 these were meant to reach `main` regardless of the branch's own fate; the human's decision to keep working on this branch before merging anything has deferred this too. Needs an explicit choice: land these three documents on `main` now (a small, low-risk cherry-pick), or supersede §7.1's expectation deliberately and merge everything together later |

## Track board

| Track | State | Blocked on |
|---|---|---|
| D Prover spike | done. FM-D1 decided: Isabelle | the two open Gate D criteria above |
| A Ledger and harness | not started | gate D's remaining criteria, then its ADR (A1). A5 runs with track C |
| B Reference semantics and oracle | not started | its ADR. B1 and B2 alongside the spike, B4 with C11a and C12 |
| C Design-time models | started 2026-10-06. [Its own plan, sketch and status](formal-methods-track-c.md) | none. C1 (Alloy skeleton) and C2 (scheme composition, ahead of CCS C8's HQ-4 and insurml-alignment's IMA-D4a) both starting |
| E Prover programme | plan and sketch written, not started | FM-D2 (an ADR), then track C's C2 for E1.3 only |
| F Native tooling | not started | its ADR, then a Python baseline per family |
| G Instrument assurance | not started | B4, C3 |

## Track D

| Slice | State |
|---|---|
| D0 environments | done (commit `efa2469`): image and native routes, driver, network probe, smoke suite |
| D1 brief | done (commit `bb86f17`): written semantics, seeded defects S1-S5, MINOR change spec, measures |
| D2 Rocq track | done (commits `f4a6db4`, `17f05d9`, `57fea56`, `ca6fbc0`): Kernel.v (TA1, TA2), Eligibility.v (TL1-TL3), Adequacy.v (13 fixture-matching theorems, all via `reflexivity`), defects S1-S5 (each a compiled, positive detection, not a narrative), Reading.v (the MINOR change, M3 measured at +21/-7 lines for adding `MostValueR`), Interface.v (M6's `MonotoneReading` record, rejects non-monotone candidates at construction), Extraction.v (M4, extracted OCaml kernel checked against all 15 reference fixtures outside Rocq), 12 claim records, `gate.py rocq` passes clean |
| D3 Isabelle track | done (commits `c7b399a`, `2a115b1`, `5dd63ad`): Kernel.thy (TA1, TA2), Eligibility.thy (TL1-TL3), Adequacy.thy (15 lemmas via `eval`), defects S1-S5 (S4 needs `quick_and_dirty`, since Isabelle refuses bare `sorry`), Reading.thy (the MINOR change, M3 measured at +18/-6 lines for `MostValueR`), Interface.thy (M6's `monotone_reading` locale), Export.thy (M4/M5: OCaml and Haskell, both checked against all 15 reference fixtures, Haskell compiled with GHC), 13 claim records, `gate.py isabelle` passes clean |
| D4 report | done: [formal-prover-experiment.md](../notes/formal-prover-experiment.md), M0-M8 scored for both provers after the human's corrections (Rocq 62.0, Isabelle 68.0 of 100; M9 removed, M5 reweighted 5→10 and rescored for Scala/Rust/Python, M6 corrected after a tested `can`/`Goal.prove` equivalent of Rocq's `Fail` was found and folded into `Interface.thy`). **FM-D1 and FM-D10 decided** |
| PF1/PF4 fixes | done (commit `c4075a6`), found by the macOS reproduction (`formal-prover-macos-portability.md`): `gate.py`'s `extract_statements` now excludes `defects/`, matching `scan_for_banned`, so the gate's digest check no longer depends on filesystem sort order (it previously passed only because Windows' case-insensitive sort happened to read the real statement last). `.gitignore` covers a stray `corporate-ca.crt` |

## Decisions

| # | State |
|---|---|
| FM-D1 | **decided 2026-10-06 by the human: Isabelle.** The report's first draft scored a 1.0-point Rocq tiebreak, carried by M9 (the engine notes' prior choice for an RDF/Datalog engine that was never built). The human removed M9 and reweighted M5 to match M6; a follow-up question also corrected M6 (Isabelle has a tested `can`/`Goal.prove` equivalent of Rocq's `Fail`). The corrected total favours Isabelle by 6.0 points outright, and the human confirmed it: both provers were fully capable, and Isabelle showed real, measured advantages, not just a narrow tiebreak. See [formal-prover-experiment.md](../notes/formal-prover-experiment.md) §1, §3, §5 and [ADR-A-FM1](../../architecture/decisions/ADR-A-FM1-formal-methods-prover-choice.md) |
| FM-D10 | **decided 2026-10-06: Haskell and Scala both adopted.** Isabelle's `export_code` demonstrated working Haskell (GHC-compiled, all fixtures matched); Scala is in the same code-generator family (documented, not yet exercised -- a near-term follow-up, not a blocker). Scala specifically opens a route to running generated algorithms directly in a JVM-based service layer |
| FM-D5, FM-D7, FM-D9 | revised 2026-10-06 after review |
| FM-D11, FM-D12, FM-D13 | decided 2026-10-06, as recommended |
| FM-D15 | decided 2026-10-06: stale on a tool change, suspect on a known soundness fix, invalid on a semantic change. Needs an ADR-A27 addendum |
| FM-D14 | open |
| FM-D16 | open: the image route everywhere for recorded work, native installs for authoring only. Blocked, for Isabelle specifically, on building the image Gate D's smoke-suite criterion needs |
| the rest | open |

## Log

- 2026-10-06: epic, sketches and the prover experiment drafted.
- 2026-10-06: reviewed. Five headline findings accepted. The epic re-sequenced into tracks A to G with
  metrics and abandonment conditions. The spike narrowed to the kernel and L15 and L16 carried end to
  end. Six points rebutted or refined in the review response, four of them for the human's decision.
- 2026-10-06: FM-D11 (stratified Datalog), FM-D12 (generation from the README) and FM-D13 (L15 and L16 in the spike) decided as recommended. FM-D15's addendum belongs to ADR-A27, the invalidation rule, with the read-set kinds in ADR-A92's terms
- 2026-10-06: FM-D15 decided: a semantic input change invalidates, a tool identity change marks claims stale and schedules re-verification, and a known soundness fix marks them suspect, failing the gate until re-verified
- 2026-10-06: tracks staggered: C1, C2, B1 and B2 alongside the spike, A1 to A4 after gate D (A5 with C), B4 with C11a and C12, C3 with C13a
- 2026-10-06: a toolchain spike on a Windows host without administrator rights, behind a TLS-re-signing proxy, ran both stacks natively and in Linux containers: proofs, code generation, compilation, AST reading and cross-compilation all passed. The plans now run on macOS, Windows and Linux: an image route for every recorded check and job, slim, multi-arch, pinned and capped, native installs for authoring only (epic E9, §4 Environments, FM-D16), and slice D0 for environments in track D
- 2026-10-06: track D (D0-D4) completed on `fm/phase-0-prover-spike`. A brief defect found during
  D2 (TA2 mis-stated as order-reversing; it is monotone) corrected before D3 began. D4's first
  draft scored a 1.0-point Rocq tiebreak. The human then corrected the scoring: M9 (prior-choice
  consistency, evidenced by an RDF/Datalog engine that was sketched but never built) removed as
  worth-less-than-nothing, M5 (other code-generation targets) reweighted from 5 to 10 to match
  M6 and rescored for production-toolchain relevance (Scala, Rust, Python). The corrected total
  (100 points) favours Isabelle by 5.0, an outright win under the plan's tie rule, not a tiebreak.
  FM-D1 and FM-D10 reopened rather than re-decided unilaterally; see
  [formal-prover-experiment.md](../notes/formal-prover-experiment.md).
- 2026-10-06: Machine R reproduced the branch on macOS (Apple silicon), native installs only,
  unmodified: everything passed except `gate.py`, found to depend on filesystem sort order
  (PF1). Fixed here: `extract_statements` now excludes `defects/`, matching `scan_for_banned`
  (commit `c4075a6`). A follow-up question on the M6 finding confirmed Isabelle's `can`/
  `Goal.prove` is a tested, working equivalent of Rocq's `Fail`, not a gap; the correction raised
  Isabelle's total to a 6.0-point win. The human then decided FM-D1 (Isabelle) and FM-D10
  (Haskell and Scala both adopted) on that evidence, and decided to continue track E's work on
  this branch rather than cutting a new one, deferring `main` until that work is ready. Gate D
  itself is not yet fully closed: the epic's abandonment thresholds are not yet revised with the
  measurements, and Isabelle has no image route in this spike to satisfy the smoke-suite
  criterion with (both open, see Gate D above).

## Estimates and actuals

| Track | Estimate (tokens) | Actual |
|---|---|---|
| D | 0.3M to 0.6M | |
| sketches, plans and the review response (2026-10-06) | not estimated | not recorded |
