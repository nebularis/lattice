<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Formal prover experiment: D4 report

**Unit:** [formal-methods](../status/formal-methods.md), track D
**Plan:** [formal-methods-phase-0.md](../plans/formal-methods-phase-0.md)
**Brief:** [formal-methods-0.md](../validation/formal-methods-0.md)
**Branch:** `fm/phase-0-prover-spike`, head commit `5dd63ad` at the time of writing
**Decides:** FM-D1 (the proof assistant, or none) and FM-D10 (the Haskell question)

Both D2 (Rocq 9.3.0) and D3 (Isabelle2025-2/HOL) completed the chain this brief specifies (TA1,
TA2, TL1 to TL3, the adequacy table, all five seeded defects, the scripted MINOR change, OCaml
extraction, a second code-generation target, the M6 interface comparison, claim records, and a
clean `gate.py` run), within the plan's 0.25M-token-per-track budget (plan §8). Per §5's decision
rule, this is the "both complete it" row: the higher weighted total wins, a margin under 5 points
is a tie broken by M0, then M3.

**Revision, after human review of the first draft's scoring:** the plan's own M9 ("consistency
with prior choices") and its M5 weight are both overridden here, on the human's explicit
instruction, as a correction to the plan rather than a reinterpretation of its evidence. The
plan's weight table (`formal-methods-phase-0.md` §4) is unchanged by this report; the deviation
is recorded here and should be reconciled with the plan separately. Two changes:

- **M9 is removed outright**, not scored. The "prior choice" it measured is the engine notes'
  recommendation for the physical planner, a sketch for an RDF/Datalog engine that was not built
  and is not a commitment this spike owes continuity to. Counting it was worse than neutral: it
  rewarded Rocq for a decision this programme never actually made, not for anything track D
  measured.
- **M5 ("other targets") is reweighted from 5 to 10, equal to M6**, since a target this spike's
  generated code could go straight into a production toolchain (Scala for service-layer
  algorithms, in particular) matters as much as the interface-rejection architecture fit M6
  scores. M5's raw scores are also revised below to weigh Scala, Rust and Python specifically,
  per that same instruction.

This changes the weighted total from 105 to 100 and reverses the tiebreak outcome (§3, §5).

## 1. Tool identification (§6)

| Tool | Version | Image/archive | Route actually used |
|---|---|---|---|
| Rocq | 9.3.0 | native opam switch `fm`; `rocq/rocq-prover@sha256:9a1e969649a3cc3c6f310d5be5a842e2187384560337c6c0807aba9f8565efba` built but not exercised for D2's proofs | native, throughout D2 |
| Isabelle | Isabelle2025-2 | native install at `C:\fmx\Isabelle2025-2`; no image route exists in this spike (epic §4, confirmed by `driver.py` refusing `--route image` for `isabelle`) | native, the only route available |

**Fairness rule 1 deviation, disclosed plainly:** the brief requires both tracks "on the image
route" (brief §7). Neither track actually ran that way. D2's proofs were all run via native
`rocq compile`, not through the driver's `image_rocq` path, for iteration speed; D3 has no image
route to run at all. The image route remains validated by D0's smoke suite, but the measures
below (M0 to M6 especially) reflect native-route costs for both tools, which is a fair
comparison between them, just not the one the brief specified. This is noted once here rather
than qualifying every measure below with it.

## 2. Evidence summary

- **Rocq** (`spikes/formal-prover/rocq/`): `Kernel.v`, `Eligibility.v`, `Adequacy.v` (13
  fixture theorems plus the 2 negation rows, 15 total under one `AQ` claim),
  `CheckKernel.v`/`CheckEligibility.v` (assumption audits, all "Closed under the global
  context"), `Reading.v` (MINOR change, two commits), `Interface.v` (the `MonotoneReading`
  dependent record), `Extraction.v` + `extracted_kernel.ml` + `extraction_driver.ml` (OCaml,
  all 15 fixtures matched), `defects/S1`-`S5` (each a compiling, positive demonstration), 13
  claim records, `gate.py rocq` passes.
- **Isabelle** (`spikes/formal-prover/isabelle/`): `Kernel.thy`, `Eligibility.thy`,
  `Adequacy.thy` (15 lemmas via `eval`), `Reading.thy` (MINOR change, two commits),
  `Interface.thy` (the `monotone_reading` locale, two interpretations), `Export.thy` +
  `formal_methods_kernel.ml`/`export_driver.ml` (OCaml, all 15 fixtures matched) +
  `Formal_Methods_Kernel.hs`/`ExportDriver.hs` (Haskell, all 15 fixtures matched, compiled with
  GHC 9.10.3), `defects/S1`-`S5` (S4 needed `quick_and_dirty` to compile at all, see §4), 13
  claim records, `gate.py isabelle` passes.
- A defect in the brief itself was found and fixed during D2 (commit `8f81d9d`): TA2 was stated
  as order-reversing; it is monotone. The Rocq proof of the stated (wrong) direction produced an
  unprovable goal, caught before it was mistaken for a tooling failure. D3 formalised the
  corrected statement from the start, per the no-unreviewed-restatement rule applied reflexively
  (brief §10).

## 3. Scores

Each measure scored 0 to 10, from the evidence above and the working notes kept during D2/D3.
Weighted score = raw score × (weight ÷ 10).

| # | Measure | Weight | Rocq | Isabelle | Rocq weighted | Isabelle weighted |
|---|---|---|---|---|---|---|
| M0 | cost to carry the law end to end | 20 | 7 | 6 | 14.0 | 12.0 |
| M1 | counterexample finding (S1-S3) | 15 | 5 | 6 | 7.5 | 9.0 |
| M2 | proof effort and agent success (TA1-TL3) | 15 | 7 | 6 | 10.5 | 9.0 |
| M3 | proof-repair cost, scripted MINOR change | 15 | 7 | 8 | 10.5 | 12.0 |
| M4 | generated OCaml | 5 | 7 | 8 | 3.5 | 4.0 |
| M5 | other targets (Scala, Rust, Python, N-version) | 10 | 2 | 8 | 2.0 | 8.0 |
| M6 | architecture fit (interface rejection) | 10 | 8 | 6 | 8.0 | 6.0 |
| M7 | toolchain and CI | 5 | 6 | 7 | 3.0 | 3.5 |
| M8 | library fit | 5 | 6 | 7 | 3.0 | 3.5 |
| **Total** | | **100** | | | **62.0** | **67.0** |

M9 removed; see the revision note above §1. M5's weight raised from 5 to 10 and its raw scores
revised, same note.

Margin: 5.0 points, not under the 5-point tie threshold (plan §5: "a margin under 5 points is a
tie"). **This is a decisive win for Isabelle, not a tie**, so no tiebreak applies. This reverses
the first draft's conclusion (a 1.0-point Rocq tiebreak win under the plan's original M9/M5
weights). See §5 for what this means for FM-D1.

### Notes per measure

- **M0.** Both tool builds are fast once set up (Rocq's five-file chain and Isabelle's
  five-theory session each compile in one to five seconds). The gap is agent iteration cost
  within this session: Rocq's TL1/TL2 proofs succeeded with fewer false starts once the
  `Forall_inv`/`in_dec` pattern was found; Isabelle's TL2 (`some_value_monotone`/
  `every_value_monotone`) needed several failed inductions (`list_all2_induct` with `arbitrary`
  variables misnaming goals, an "Ill-formed destruction rule" from `dest:` attributes, and a
  `simp` gap on the impossible-length `Nil` case) before landing on a working combination. This
  is one session's experience with one agent configuration, not a general claim about either
  tool's learning curve.
- **M1.** Neither track exercised an automatic counterexample finder: no QuickChick is
  installed for Rocq in this spike, and Isabelle's bundled `nitpick`/`quickcheck` were not
  invoked (all refutations in both tracks are hand-constructed witnesses, e.g. `[Permitted;
  Denied]`). Isabelle scores slightly higher only because that tooling ships with the
  distribution and needs no separate install, an unexercised but readily available difference.
- **M2.** Both chains completed without abandoning a theorem. Rocq's kernel-level proofs needed
  explicit case bullets (`split; [|split;[|split]]`) and care around `destruct ... eqn:` rewriting
  pre-existing hypotheses; Isabelle's kernel-level proofs were markedly terser (one-line
  `by (cases a; cases a'; cases b; simp add: decision_leq_def)` closes a 3×3×3 case split) but
  the list-level monotonicity proofs cost more iteration (see M0).
- **M3.** Measured directly from `git diff --numstat` after adding `MostValueR` to an otherwise
  working chain: Rocq +21/-7 lines (`Reading.v`, commits `17f05d9` then `57fea56`); Isabelle
  +18/-6 lines (`Reading.thy`, commits `c7b399a` then `2a115b1`). Comparable, Isabelle slightly
  cheaper.
- **M4.** Rocq's extraction represents lists as a bespoke `Nil`/`Cons` type (its own stdlib
  `list`, not OCaml's native list), so the driver needs a small `mk` adapter
  (`extraction_driver.ml`). Isabelle's `export_code` maps HOL's `list` directly to OCaml's
  native `[]`/`::`, no adapter needed; it does, by default, hide the `decision` type's
  constructors behind an abstract signature, needing an explicit `export_code Permitted Denied
  Undetermined ...` to expose them (once known, a one-line fix).
- **M5, rescored for production-toolchain relevance (Scala, Rust, Python).** Isabelle's code
  generator officially targets SML, OCaml, Haskell **and Scala**; the Haskell path was exercised
  this spike (`ExportDriver.hs`, GHC 9.10.3, all 15 fixtures matched), and Scala sits in the same
  code-generator family, so the same pattern (list and constructor mapping, see M4) is very
  likely to carry over with the same low adaptation cost, though it was not itself run this
  session. Rocq's `Extraction` library targets only OCaml, Haskell and Scheme: **there is no
  Scala backend at all**, a structural gap rather than an unexercised one. Neither tool's code
  generator targets Rust or Python directly: Rocq's adjacent Rust tooling (`hax`, `coq-of-rust`,
  cited in the engine notes) verifies existing Rust code written against a Rocq spec, which
  verifies in the opposite direction from generating Rust out of a proof, so it does not help
  here. This is a wash between the two for Rust and Python, and is reflected by neither prover
  scoring near the top of the range; Isabelle's score is carried by Scala plus the demonstrated
  Haskell/OCaml pair, Rocq's by OCaml alone.
- **M6.** Rocq's `MonotoneReading` dependent record rejects a non-monotone candidate as a type
  error at the point of construction, and the rejection itself is demonstrated inside the
  successfully-building file via `Fail Definition` (`Interface.v`), a self-contained,
  machine-checked assertion that the bad candidate fails. Isabelle's `monotone_reading` locale
  rejects the same shape of candidate at `interpretation`/`unfold_locales`, a proof obligation
  failure rather than a type error, which is at least as legible to a non-type-theorist (it reads
  as an ordinary unproved goal) but could not be demonstrated as a failing-yet-contained command
  in this spike: Isar has no batch-mode equivalent of Rocq's `Fail`, so `Interface.thy` instead
  documents the rejection in a comment rather than asserting it. That weakens Isabelle's score
  here on demonstrability, not on the soundness of the rejection itself.
- **M7.** Both have working `mise` bootstrap tasks, confirmed idempotent in D0. Rocq has a built
  image (unused for D2's actual proof work); Isabelle has none at all in this spike, a real gap
  against the epic's eventual containerised-worker story (epic §4). Isabelle's native install is
  one self-contained directory bundling its own Poly/ML and Cygwin, with no PATH-ordering
  fragility; Rocq's opam-based install needs `Enable-FmxRocq`'s PATH reordering (documented as a
  "known fragility point" since D0).
- **M8.** Neither track drew on either library's order/lattice typeclass hierarchy in practice
  (both hand-roll `decision_leq`). The engine notes' own comparison (`compiled-persistence-
  profiles.md`) describes both ecosystems as "very large"; Isabelle/HOL plus the Archive of
  Formal Proofs is marginally broader for published order/lattice developments specifically,
  hence the small edge, unconfirmed by anything this spike actually used.
- **M9, removed.** The plan's M9 scored "consistency with prior choices," evidenced by the engine
  notes' recommendation of "OCaml with Rocq" for an RDF/Datalog engine's physical planner. That
  engine was sketched, not built, and this spike owes no continuity to a decision the programme
  never actually acted on. Scoring it rewarded Rocq for a choice made in a different, abandoned
  context, not for anything D2 or D3 measured, so it is removed rather than scored.

## 4. Seeded-defect detection, by tool

| Defect | Rocq | Isabelle |
|---|---|---|
| S1 (weak empty case) | caught: two positive refutation theorems compile (`defects/S1_weak_empty_case.v`) | caught: two positive refutation lemmas compile (`defects/S1_weak_empty_case.thy`) |
| S2 (broken negation) | caught: two refutation theorems compile | caught: two refutation lemmas compile |
| S3 (vacuous interface) | caught: `Fail Definition` demonstrates the rejected instantiation inside the build | caught in substance (`real_definitions_cannot_satisfy_ri_agree`), but the failing `interpretation` itself is only a comment, not an executed, contained failure (see M6) |
| S4 (`Admitted`/`sorry`) | Rocq accepts `Admitted` silently; `check_s4.py` confirms `gate.py`'s source scan catches it outside `defects/` | Isabelle's own build **refuses** `sorry` by default ("Cheating requires quick_and_dirty mode!"), a stronger, build-time rejection; `quick_and_dirty` had to be enabled for the whole defects session just to let this one file compile, so `check_s4.py` could then show what the gate's source scan additionally catches |
| S5 (weakened restatement, same name) | caught: `check_s5.py` recomputes both digests and shows they differ | caught: `check_s5.py` recomputes both digests and shows they differ |

Isabelle's default refusal of `sorry` is a genuinely stronger assurance property than Rocq's
silent acceptance of `Admitted`, not reflected in the M0-M8 table above (closest fit is M6/M7);
noted here because it is a real, observed difference in favour of Isabelle's tooling.

## 5. Decisions

### FM-D1: the proof assistant, or none

**Reopened, pending the human's confirmation.** With M9 removed and M5 reweighted and rescored
(§1, §3), the total flips to a 5.0-point Isabelle win, at or past the plan's tie threshold, so
§5's decision rule gives the higher total outright with no tiebreak: **Isabelle, not Rocq.** This
reverses the first draft's conclusion, which depended entirely on M9 (a measure now removed) and
a 1.0-point M0 tiebreak that the new total no longer needs.

This report does not treat that reversal as settling FM-D1 by itself. Adopting Isabelle for
track E is a design decision the Agentic Development Contract reserves for the human, and the
evidence behind the swing is still thin in places the caveats (§6) already name: M5's Scala score
rests on an unexercised but documented capability, not a run; M0 and M2's small gaps are one
session's experience, not a controlled study. What this report changes is the recommendation it
would make absent further guidance: **Isabelle**, on the corrected weights, rather than Rocq's
previous narrow tiebreak. The human may re-confirm Rocq (for reasons this report's measures do
not capture, such as the MetaRocq/Rust-bridge ecosystem M9 used to count), confirm Isabelle, or
ask for specific gaps (Scala, specifically) to be exercised before deciding.

### FM-D10: the Haskell question

Isabelle answers it directly: `export_code ... in Haskell` produced working, GHC-compiled
Haskell matching every reference fixture with no manual adaptation. Rocq's extraction can target
Haskell in principle (its `Extraction` library supports it) but this was not exercised in D2.
With FM-D1 reopened rather than settled for Rocq, this question is reopened with it: if Isabelle
is adopted, Haskell (and Scala, per M5) are both already-working targets at effectively no
further cost; if Rocq is retained, Haskell remains available but unverified in this spike, and
Scala is not available from Rocq's extraction mechanism at all (§3, M5).

## 6. Caveats on this report

- Both tracks ran on one host (Windows), one agent configuration, in one session each, which is
  the fairness rule the brief sets (§7 rule 1) for agent and host, but not for route (§1 above).
- D2 was built before D3 (brief §7 rule 3), and the agent carried patterns from D2 into D3 (for
  example, the GATE-marker convention, the defects/ directory shape, and the claim schema were
  already fixed by D1 and not re-derived). This is intended by the brief (both read the same
  brief, not each other's sources) and did not, on inspection, give D3 an unfair proof-tactic
  head start: the actual Isabelle tactics are unrelated to Rocq's, and the Isar failures recorded
  under M0/M2 are genuine first-encounters with Isabelle's induction principles, not harder
  because D2 came first.
- The M0-M2 debugging-iteration counts are this session's lived experience with one model and
  are not a controlled timing study. A different session could plausibly reverse M0 and M2's
  small gaps; at the current 5.0-point margin, reversing both would roughly halve the gap but not
  close it (M0's swing alone is 2 points either way), so the outright-win outcome is not fragile
  to that particular uncertainty the way the first draft's 1.0-point tiebreak was.
- M5's Scala score for Isabelle (8/10, §3) rests on that target being part of the same
  `export_code` mechanism already twice demonstrated working (OCaml, Haskell), not on Scala
  itself having been run. Before treating M5 as settled, D3 should actually exercise
  `export_code ... in Scala` the way D3 already did for OCaml and Haskell, so this score becomes
  demonstrated rather than inferred.
