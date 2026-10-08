<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# ADR-A-FM1: Proof assistant and code-generation targets for the formal-methods prover programme

**Status:** Accepted
**Date:** 2026-10-06
**Related:** the formal-methods epic plan, [formal-methods-phase-0.md](../../developer/plans/formal-methods-phase-0.md) (track D, the spike), [formal-prover-experiment.md](../../developer/notes/formal-prover-experiment.md) (the D4 report), [formal-prover-macos-portability.md](../../developer/notes/formal-prover-macos-portability.md)
**Unit:** [`formal-methods`](../../developer/plans/formal-methods.md) (epic), gate D, decisions FM-D1 and FM-D10

## Context

Track D's spike (`fm/phase-0-prover-spike`) carried the logic kernel (TA1, TA2) and Eligibility's
set readings and negation (TL1 to TL3, ADR-A103) end to end in both Rocq 9.3.0 and Isabelle2025-2/
HOL: written semantics to formal statement, proof, assumption audit, adequacy against the Python
reference fixtures (`tools/mork_compilers/src/mork_compilers/test_set_readings.py`), five seeded
defects (S1 to S5), a scripted MINOR change (a fourth value reading, `MostValueR`), OCaml
extraction, a claim record per theorem, and a passing `gate.py` run. Both tracks completed within
budget; per the phase-0 plan's own decision rule, this is the "both complete it" row.

The plan's weighted measures (M0 to M9, §4) scored Rocq and Isabelle at 66.5 and 65.5 of 105, a
1.0-point margin under the plan's 5-point tie threshold, broken by M0 in Rocq's favour. On review,
the human found two faults in that scoring, not in the tracks' evidence:

1. **M9 ("consistency with prior choices") rewarded continuity with a decision the programme
   never made.** Its evidence was the engine notes' recommendation of "OCaml with Rocq" for an
   RDF/Datalog engine's physical planner (`docs/developer/notes/rdf-engine/compiled-persistence-
   profiles.md`), a sketch that was never built. Scoring it counted a choice this codebase does
   not act on, worth less than nothing: removed outright, not down-weighted.
2. **M5 ("other code-generation targets") was underweighted against what a production toolchain
   could use directly.** Scala, reachable from Isabelle's `export_code` in the same family as the
   OCaml and Haskell targets both tracks exercised, opens running generated algorithms in a
   JVM-based service layer, a capability Rocq's `Extraction` library (OCaml, Haskell, Scheme) does
   not have at all. Reweighted from 5 to 10, equal to M6 (architecture fit), and rescored for
   Scala, Rust and Python specifically (Rocq: 2/10, no Scala backend, no Rust or Python from
   either tool's own code generator; Isabelle: 8/10, Scala documented in the same proven family as
   the already-demonstrated Haskell and OCaml targets, Rust and Python unavailable from either).

A follow-up question narrowed a further fault: M6 had scored Isabelle down for being unable to
demonstrate a non-monotone interface candidate's rejection the way Rocq's `Fail Definition` does,
inside a build that otherwise succeeds. Tested directly: Isabelle's `can` (a standard ML
combinator) wrapping `Goal.prove`, inside an `ML_command`, gives exactly that shape of evidence,
confirmed against the spike's own `inverted_reading` counterexample and folded into
`spikes/formal-prover/isabelle/Interface.thy`, replacing a comment-only placeholder. M6 revised
from 6 to 7 for Isabelle.

With M9 removed and M5 and M6 corrected, the weighted total (out of 100) is Rocq 62.0, Isabelle
68.0, a 6.0-point margin, past the plan's tie threshold: an outright win under the plan's own
decision rule, not a tiebreak. A macOS reproduction (Apple silicon, native installs, Machine R)
independently confirmed both tracks' proofs, defects, extraction and exports reproduce unmodified,
and found one real defect in the gate script itself (`gate.py`'s statement-digest check depended
on filesystem sort order, fixed in `c4075a6`), not in either track's mathematics.

## Decision

1. **Isabelle/HOL (Isabelle2025-2 at the time of the spike) is the proof assistant for the
   formal-methods prover programme (FM-D1).** Track E proceeds against it. The decision follows
   the corrected scoring's outright win, not an overrule of the plan's decision rule: the human
   confirmed the result rather than imposing a different one, on the strength of concrete,
   measured advantages this spike could observe directly (a cheaper MINOR-change repair, a
   native OCaml list mapping needing no adapter, a demonstrated second code-generation target, a
   simpler native install), not a narrow margin alone.
2. **Haskell and Scala are both adopted as code-generation targets (FM-D10).** Haskell is
   demonstrated: `export_code ... in Haskell`, compiled with GHC, matches every reference fixture.
   Scala is not yet exercised in this spike but is documented in the same `export_code` mechanism
   already proven twice; exercising it is near-term follow-up work for track E, not a precondition
   of this decision. Scala's value is specifically running generated algorithms directly in a
   JVM-based service layer, which Rocq's extraction mechanism cannot reach at all.
3. **Rocq's spike work is kept, not discarded.** `spikes/formal-prover/rocq/` remains a complete,
   working, independently-reproduced record on this branch. Nothing in this decision closes the
   door on Rocq: if a future measure shifts materially (a Haskell or Scala need Isabelle cannot
   serve, a verified-extraction requirement MetaRocq's ecosystem serves better, Isabelle's
   `interpretation`-level rejection proving too indirect in practice), the spike's own evidence is
   the place to start re-opening it, not a fresh spike.
4. **What this decision does not yet settle.** Gate D (phase-0 plan §9) is not fully closed:
   Isabelle has no image route in this spike (only Rocq's does), so the smoke-suite criterion is
   unmet for the chosen prover, deferred deliberately (human instruction, 2026-10-06, to conserve
   tokens; retro-fittable on another host). The epic's abandonment thresholds (`formal-methods.md`
   §6) are annotated with this spike's measurements but not recalibrated, since they were measured
   against a toy few-dozen-line theory, not a production-scale layer. FM-D2 (where track E's real
   theories live, replacing `spikes/`) is deferred to track E's own plan.

## Consequences

- Track E's plan, sketch and status record are filed as their own documents
  (`formal-methods-track-e.md` under `plans/`, `sketches/` and `status/`), per the Epic
  Decomposition Model's phase-level documentation rule, rather than as a section of the epic's own
  plan.
- `docs/developer/plans/formal-methods.md` and `docs/developer/status/formal-methods.md` record
  FM-D1 and FM-D10 as decided, cross-referencing this ADR and the D4 report as their evidence.
- No ontology, `tools/`, `workers/` or `platform/` content changes as a consequence of this ADR by
  itself: it governs the formal-methods epic's own tooling choice, not any layer's semantics.
- This ADR is numbered outside the main `A-`series' sequential pool (`A-FM`, after the existing
  `A-C` and `A-CAP` precedent for thematically distinct, non-sequential blocks), because this
  branch and the `computable-contract-substrate` and `insurml-alignment` epics are drafting ADRs
  concurrently on separate machines; a plain next-sequential number allocated independently on
  each would collide on merge, as has already happened once in this catalogue's history (A-44,
  A-81, A-83; see this directory's `README.md`). Track E's later ADRs continue this `A-FM2`,
  `A-FM3`, … series.

## Addendum, 2026-10-08

An implementation-level review of the programme's evidence (disposed in full in
[formal-methods-more-feedback-response.md](../../developer/notes/formal-methods-more-feedback-response.md)
§2, §4) raised two points about this decision's own evidence, neither of which reopens it:

1. **M6's corrected evidence is weaker than the Context section states.** Isabelle's `can`
   wrapping `Goal.prove` demonstrates that *a given tactic fails* on a goal, inside a successful
   build. It does not demonstrate that the goal is false or unprovable, the way Rocq's
   `Fail Definition` demonstrates a definition is rejected by the termination or type checker.
   These are different strengths of evidence, and the Context section's "exactly that shape of
   evidence" overstates the match. Where this programme needs the stronger shape (a candidate
   definition proved impossible, not merely a chosen proof attempt failing), the pattern to reach
   for is the one `Eligibility.thy` already uses for TL3b (proving the negation of a false
   candidate statement directly), not the `can`/`Goal.prove` wrapper M6 credits.
2. **M5's Scala credit has not been exercised, and was not held to the same scrutiny M9's removal
   established.** M9 was removed for rewarding a decision the codebase never acted on. M5's Scala
   component rewards a capability (`export_code ... in Scala`) that is, as of this addendum,
   equally unexercised. Exercising it is already named above as "near-term follow-up work for
   track E, not a precondition of this decision" — this addendum raises its priority, given the
   review's point, but does not change the decision: removing Scala's credit from M5 and
   recomputing the total is recorded as an open, low-cost check (run `export_code ... in Scala`
   from the existing kernel theory, compile with `scalac`, and recompute M5 both with and without
   the resulting evidence) rather than taken as already discharged.

Neither point changes FM-D1 or FM-D10: both were corroborated by concrete, measured advantages
beyond the M5/M6/M9 scoring alone (the Context section's own list: MINOR-change repair cost,
native list mapping, a second demonstrated code-generation target, a simpler native install). The
open check in point 2 is tracked, not scheduled, since nothing downstream currently depends on
its outcome.
