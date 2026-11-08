<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Formal Methods: Status

**Unit ID:** `formal-methods` (epic)
**Status:** built 2026-11-02. ✅ Track D complete on `fm/phase-0-prover-spike` (D0-D4, plus the FM-PF1/PF4 fixes from the
macOS reproduction). **FM-D1 decided 2026-10-06: Isabelle.** FM-D10 decided:
Haskell and Scala both adopted as code-generation targets. The maintainer has also decided to
continue track E's work on this same branch rather than cutting a fresh one, deferring the merge
to `main` until track E work is ready (a deviation from plan §7.1's "brief, report and status
record reach `main` regardless", recorded here, not yet actioned). Gate D is not yet fully
closed: two criteria remain open, see §Gate D below
**Last updated:** 2026-10-10
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
decided too (ADR-A-FM2: `tools/proofs/`), and FME-1.0/E1.1 are done: `tools/proofs/eligibility/`
compiles and gates clean, natively, matching track D's spike evidence exactly. FME-1.2 was attempted
and found blocked on a missing normative source (its own status record), not merely unstarted.
Track C has its own plan, sketch and status record now too
([formal-methods-track-c.md](formal-methods-track-c.md)): C1 (an Alloy skeleton) and C2 (binding
resolution with scheme composition, ahead of CCS's HQ-4 and insurml-alignment's IMA-D4a, both read
directly from `main` and confirmed genuinely unresolved) are both **done**. C2's checked model
found that "union of membership, union of hierarchy" does not by itself prevent two composed
schemes disagreeing about a shared concept's `broader` parent — a counterexample, read and
recorded in full, not a reinvented worry. That finding is now answered: `ADR-A116` (Vocabulary
scheme composition), drafted 2026-10-07 at our request, cites C2's evidence directly,
decides the overlap rule (forbidden, by a new static shape) and the composition construct
(`voc:BindingAspect`/`voc:forAspect`), and is shared with CCS's HQ-4 and insurml-alignment's
IMA-D4a as one ADR, per IMA-D4a's own recommendation. Filed as plain `A116`, not the epic's own
`A-FM` block, since it is a shared Vocabulary-layer decision. Track B now has its own plan, sketch and status record
too ([formal-methods-track-b.md](formal-methods-track-b.md)): B1, B2 and B3 are all **done**
(`tools/reference/eligibility/`, `ADR-A-FM3` **Accepted**), the logic kernel and Eligibility's
denotation (L9-L16) ported from and verified against `tools/proofs/eligibility/`'s Isabelle
statements, differentially tested against `tools/mork_compilers`' SPARQL and SHACL (63 tests,
finding and fixing two real defects in the reference itself), and Surface's ADR-A27
regeneration-as-naturality property test (72 tests, no regression). B1's own scoping work
resolved FME-1.2 (below): the rounding/residual
theorem belongs to B4/E3-E4, not Quantification; track E's plan and status are corrected.

**FM-EP, the Eligibility pass, before CCS-9b.3 (decided 2026-10-09). Done, 2026-10-09.** On
machine S, branch `fm/eligibility-pass`: FM-D17 decided (A+B hybrid) and built, FME-1.4 built,
FMB-2.2 and FMB-2.1 built, B5 attempted and blocked (mirror gap, deferred). Full detail in track E's
and track B's own status records. Merged to `main` on 2026-10-09 (`2a438b15`). Its one hand-off to CCS, law L9's amendment in the Eligibility README, is released by CCS slice C9b0. Cost: 1969.4 AI credits for the whole work unit (see Estimates and actuals).

**Next action, for the maintainer:** review and accept (or revise) `ADR-A116`. FM-EP is merged (2026-10-09). Track B's B1-B3 are complete; B4 waits on CCS's C12. The two remaining Gate D
gaps (below) are deliberately deferred, not blocking. Also decide when and where the spike
branch, `fm/phase-0-prover-spike`, is created, and approve the image builds and any native
installs.

**2026-10-08, a second review.** An implementation-level review of the programme's actual
evidence (not just its sketches), disposed in
[formal-methods-more-feedback-response.md](../notes/formal-methods-more-feedback-response.md),
found two real defects beyond wording: `tools/proofs/eligibility/gate.py`'s statement digest does
not cover the definitions a gated statement depends on, and the Alloy model's first
`NoOverlapDisagreement` counterexample relied on a degenerate self-loop. The second was fixed and
re-checked the same session — the finding survives under well-formedness facts, with a new,
non-degenerate witness (`tools/models/vocabulary-scheme-composition/`). The first, and several
smaller hardening items, are queued as new slices (track E's FME-1.4, track B's FMB-2.1/B2.2/B5, track
C's FMC-2.2/C2.3), none blocking. A new open decision, FM-D17, asks whether to generate the kernel's
truth-table equations (not just its closed datatype) from one README source into both Isabelle and
Python, closing the "one hand-written table, two consumers" risk the review raised. **A new
track, H (Persistence), is also added this session** (§Track board), drafted from
`docs/developer/notes/rdf-engine/persistence-fml.md` and connected to, but independently
runnable from, tracks A, B, C and E — see `formal-methods-track-h.md`'s own plan, sketch and
status record.

## Track board

| Track | State | Blocked on |
|---|---|---|
| D Prover spike | done. FM-D1 decided: Isabelle | the two open Gate D criteria above |
| A Ledger and harness | not started | gate D's remaining criteria, then its ADR (A1). A5 runs with track C |
| B Reference semantics and oracle | B1, B2, B3, FMB-2.1, FMB-2.2 done. B5 attempted, blocked (mirror gap). [Its own plan, sketch and status](formal-methods-track-b.md) | B4 waits on CCS's C11a (done) and C12 (not done) |
| C Design-time models | C1 and C2 done 2026-10-06. [Its own plan, sketch and status](formal-methods-track-c.md) | C3 (slot exclusivity, SMT) not started, waits on nothing but is next in this track's own numbering |
| E Prover programme | FME-1.0/E1.1/E1.4 done. FM-D17 built. FME-1.2 retired (its real home is B4/E3-E4, not Quantification) | FME-1.3 waits on track C2's overlap-rule ADR, not on C2 itself (done) |
| F Native tooling | not started | its ADR, then a Python baseline per family |
| G Instrument assurance | not started | B4, C3 |
| H Persistence | in progress. H1 and the aggregate-ownership slices FMH-HO0 to FMH-HO9 merged and signed off 2026-10-10, ADR-A-FM4 and ADR-A122 accepted. H2, the typed IR, briefed 2026-10-10, ADR-A123 accepted, FMH-2.0 to FMH-2.3 merged and signed off (2026-10-12), H2.4 built and reviewed, FMH-2.5 and FMH-2.6 built, FMH-2.6 approved with three design questions open (2026-10-13), FMH-2.6b event half built, approved and complete (2026-10-14). [Its own plan, sketch and status](formal-methods-track-h.md) | nothing from tracks A-G, it reuses their methods but needs none of them to start |

## Track D

| Slice | Deliverable | State | Blocked on |
|---|---|---|---|
| FM-D0 | environments | built 2026-10-06, (commit `efa2469`): image and native routes, driver, network probe, smoke suite |  |
| FM-D1 | brief | built 2026-10-06, (commit `bb86f17`): written semantics, seeded defects S1-S5, MINOR change spec, measures |  |
| FM-D2 | Rocq track | built 2026-10-06, (commits `f4a6db4`, `17f05d9`, `57fea56`, `ca6fbc0`): Kernel.v (TA1, TA2), Eligibility.v (TL1-TL3), Adequacy.v (13 fixture-matching theorems, all via `reflexivity`), defects S1-S5 (each a compiled, positive detection, not a narrative), Reading.v (the MINOR change, M3 measured at +21/-7 lines for adding `MostValueR`), Interface.v (M6's `MonotoneReading` record, rejects non-monotone candidates at construction), Extraction.v (M4, extracted OCaml kernel checked against all 15 reference fixtures outside Rocq), 12 claim records, `gate.py rocq` passes clean |  |
| FM-D3 | Isabelle track | built 2026-10-06, (commits `c7b399a`, `2a115b1`, `5dd63ad`): Kernel.thy (TA1, TA2), Eligibility.thy (TL1-TL3), Adequacy.thy (15 lemmas via `eval`), defects S1-S5 (S4 needs `quick_and_dirty`, since Isabelle refuses bare `sorry`), Reading.thy (the MINOR change, M3 measured at +18/-6 lines for `MostValueR`), Interface.thy (M6's `monotone_reading` locale), Export.thy (M4/M5: OCaml and Haskell, both checked against all 15 reference fixtures, Haskell compiled with GHC), 13 claim records, `gate.py isabelle` passes clean |  |
| FM-D4 | report | built 2026-10-10, [formal-prover-experiment.md](../notes/formal-prover-experiment.md), M0-M8 scored for both provers after our corrections (Rocq 62.0, Isabelle 68.0 of 100, M9 removed, M5 reweighted 5→10 and rescored for Scala/Rust/Python, M6 corrected after a tested `can`/`Goal.prove` equivalent of Rocq's `Fail` was found and folded into `Interface.thy`). FM-D1 and FM-D10 decided |  |
| FM-PF1 | fixes | built 2026-10-07, (commit `c4075a6`), found by the macOS reproduction (`formal-prover-macos-portability.md`): `gate.py`'s `extract_statements` now excludes `defects/`, matching `scan_for_banned`, so the gate's digest check no longer depends on filesystem sort order (it previously passed only because Windows' case-insensitive sort happened to read the real statement last). `.gitignore` covers a stray staged CA file |  |
| FM-0 | track D, the prover spike, the pack that covers FM-D0 to FM-D4 | built 2026-10-06 |  |
| FM-CG1 | code generation from the layer models, `spikes/isabelle-layers`: thirteen proved layer theories, two code-generation theories, Haskell, SML and Scala exports, Eligibility's decision table executing | merged 2026-11-02, built 2026-11-01 |  |
| FM-CG2 | the generated Haskell as a differential oracle beside the Python reference, under the four conditions the spike's README states | planned | PDD-19 |

## Decisions

| # | State |
|---|---|
| FM-D1 | **decided 2026-10-06: Isabelle.** The report's first draft scored a 1.0-point Rocq tiebreak, carried by M9 (the engine notes' prior choice for an RDF/Datalog engine that was never built). We removed M9 and reweighted M5 to match M6; a follow-up question also corrected M6 (Isabelle has a tested `can`/`Goal.prove` equivalent of Rocq's `Fail`). The corrected total favours Isabelle by 6.0 points outright, and we confirmed it: both provers were fully capable, and Isabelle showed real, measured advantages, not just a narrow tiebreak. See [formal-prover-experiment.md](../notes/formal-prover-experiment.md) §1, §3, §5 and [ADR-A-FM1](../../architecture/decisions/ADR-A-FM1-formal-methods-prover-choice.md) |
| FM-D10 | **decided 2026-10-06: Haskell and Scala both adopted.** Isabelle's `export_code` demonstrated working Haskell (GHC-compiled, all fixtures matched); Scala is in the same code-generator family (documented, not yet exercised -- a near-term follow-up, not a blocker). Scala specifically opens a route to running generated algorithms directly in a JVM-based service layer |
| FM-D5, FM-D7, FM-D9 | revised 2026-10-06 after review |
| FM-D11, FM-D12, FM-D13 | decided 2026-10-06, as recommended |
| FM-D15 | decided 2026-10-06: stale on a tool change, suspect on a known soundness fix, invalid on a semantic change. Needs an ADR-A27 addendum |
| FM-D14 | open |
| FM-D16 | decided 2026-10-06: the image route everywhere for recorded work, native installs for authoring only. The spike remains blocked on Isabelle's image route for Gate D's smoke-suite criterion until that path is built |
| the rest | open |

## Log

- 2026-11-08: FM-D18 decided, a prelude session over the `HOL-Library` theories the layer proofs reach for, which every layer session parents on, as (d) of the ledger plan's LG-Q14. Track E's FME-0 builds it after an ADR-A-FM2 addendum.

- 2026-10-06: epic, sketches and the prover experiment drafted.
- 2026-10-06: reviewed. Five headline findings accepted. The epic re-sequenced into tracks A to G with
  metrics and abandonment conditions. The spike narrowed to the kernel and L15 and L16 carried end to
  end. Six points rebutted or refined in the review response, four of them for the maintainer's decision.
- 2026-10-06: FM-D11 (stratified Datalog), FM-D12 (generation from the README) and FM-D13 (L15 and L16 in the spike) decided as recommended. FM-D15's addendum belongs to ADR-A27, the invalidation rule, with the read-set kinds in ADR-A92's terms
- 2026-10-06: FM-D15 decided: a semantic input change invalidates, a tool identity change marks claims stale and schedules re-verification, and a known soundness fix marks them suspect, failing the gate until re-verified
- 2026-10-06: tracks staggered: C1, C2, B1 and B2 alongside the spike, A1 to A4 after gate D (A5 with C), B4 with C11a and C12, C3 with C13a
- 2026-10-06: a toolchain spike on a Windows host without administrator rights, behind a TLS-re-signing proxy, ran both stacks natively and in Linux containers: proofs, code generation, compilation, AST reading and cross-compilation all passed. The plans now run on macOS, Windows and Linux: an image route for every recorded check and job, slim, multi-arch, pinned and capped, native installs for authoring only (epic E9, §4 Environments, FM-D16), and slice FM-D0 for environments in track D
- 2026-10-06: FM-D16 decided as recommended: the image route everywhere for recorded work, native installs for authoring only.
- 2026-10-06: track D (D0-D4) completed on `fm/phase-0-prover-spike`. A brief defect found during FM-D2 (TA2 mis-stated as order-reversing, it is monotone) corrected before FM-D3 began. FM-D4's first draft scored a 1.0-point Rocq tiebreak. The maintainer then corrected the scoring: M9 (prior-choice consistency, evidenced by an RDF/Datalog engine that was sketched but never built) removed as worthless-than-nothing, M5 (other code-generation targets) reweighted from 5 to 10 to match M6 and rescored for production-toolchain relevance (Scala, Rust, Python). The corrected total (100 points) favours Isabelle by 5.0, an outright win under the plan's tie rule, not a tiebreak. FM-D1 and FM-D10 reopened rather than re-decided unilaterally, see [formal-prover-experiment.md](../notes/formal-prover-experiment.md).
- 2026-11-07: C4 gained three checks and a note, on `docs/placement-vehicles-structure`, from the [waterfall proofs sketch](../sketches/waterfall-proofs-and-the-generality-gap.md). C4-A10 checks that positions totalise the steps that draw one account, C4-A11 shows two outcomes once that totality is relaxed, and C4-A12 shows a run that omits a planned step still satisfying amount conservation. C4-A2's "only sequences determined steps" is marked load-bearing, since it is the premise those two checks isolate. E4c's row carries a note that its monotonicity is in the information order and that the external waterfall development contributes nothing to it, so E4c starts from nothing already proved. No track or slice changed state. TD-155 records that the code generated from the layer theories is partial on a cofinite set, with Haskell failing silently, found by a code-generation spike on `fml/isabelle-layers` that made Eligibility execute and agree across `value`, Haskell and Scala.
- 2026-10-06: Machine R reproduced the branch on macOS (Apple silicon), native installs only, unmodified: everything passed except `gate.py`, found to depend on filesystem sort order (FM-PF1). Fixed here: `extract_statements` now excludes `defects/`, matching `scan_for_banned` (commit `c4075a6`). A follow-up question on the M6 finding confirmed Isabelle's `can`/`Goal.prove` is a tested, working equivalent of Rocq's `Fail`, not a gap, the correction raised Isabelle's total to a 6.0-point win. The maintainer then decided FM-D1 (Isabelle) and FM-D10 (Haskell and Scala both adopted) on that evidence, and decided to continue track E's work on this branch rather than cutting a new one, deferring `main` until that work is ready. Gate D itself is not yet fully closed: the epic's abandonment thresholds are not yet revised with the measurements, and Isabelle has no image route in this spike to satisfy the smoke-suite criterion with (both open, see Gate D above).

## Estimates and actuals

| Track | Estimate (tokens) | Actual |
|---|---|---|
| D | 0.3M to 0.6M | |
| sketches, plans and the review response (2026-10-06) | not estimated | not recorded |
| FM-EP, the Eligibility pass (2026-10-09, machine S, `fm/eligibility-pass`) | not estimated | 1969.4 AI credits |
- 2026-10-09: an Eligibility pass scheduled before CCS-9b.3, which extends Eligibility with set comparisons and aggregate bindings: FM-D17, FME-1.4, FMB-2.2 and FMB-2.1 on this epic's own branch, merged to `main` first
- 2026-10-09: FM-EP merged to `main` (`2a438b15`). L9's README amendment handed to CCS slice CCS-9b.0 for release
- 2026-11-04: FM-CG1 and FM-CG2 added on `fml/isabelle-layers` (plan work-board, WB-7). The code-generation spike that branch had called H3.1 is this epic's FM-D10 at work and feeds PDD-19, not track H's H3, which the track H plan defines as the specification registry. FM-CG1 is on `main` as df0ddd1a. The row the adopt step took from track C's C4 pack is gone from this board, since that pack is track C's, now named by its slice FMC-4. FM-0 stays as the track D pack's row.
- 2026-11-07: FM-D17 widened on `docs/placement-vehicles-structure`, for the ledger unit's LG-7. `tools/literate_extract.py` renders an `isabelle-spec` block's `fun` clauses as Python only where the block's first line is `(* @reference-table *)`, which Eligibility's block now carries, so a kernel block without it holds any Isabelle definition and is written verbatim. Three tests added, Eligibility's `Kernel.thy` and `_kernel_defs.py` unchanged. The spike's `gate.py` and `claim-schema.json` copies are removed, since `check:proofs` runs `tools/proofs/gate.py` and the second copy misled a reader, recorded in ADR-A-FM2's addendum of the same day. The spike's `env/` scripts stay, since `check:proofs` and the native bootstrap tasks run them.
