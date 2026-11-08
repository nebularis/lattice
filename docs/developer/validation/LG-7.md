<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: Ledger LG-7, the ledger laws mechanised

**Unit:** `ledger` ([plan](../plans/ledger.md), [status](../status/ledger.md)).
**Machine and branch:** as the maintainer assigns. Commits are the maintainer's.
**Plan and brief:** [Ledger plan](../plans/ledger.md), LG-7 in detail.
**Decisions:** ADR-A131 decisions 3, 4 and 6, its addendum on positions, ADR-A-FM1 (Isabelle), ADR-A-FM2 (the proof gate), LG-Q2, LG-Q3, LG-Q6. Findings L1 to L8 of the [waterfall proofs sketch](../sketches/waterfall-proofs-and-the-generality-gap.md) §5.1.
**Track:** E, pulled ahead of B4a with the reason in the plan. This pack engages the mechanised-theory artefact, `tools/proofs/ledger/`, and the freshness check that ties its kernel to the layer's README.

## Invariant

Every law ADR-A131 states about accounts, draws, merge rules and allocation is proved once, in one Isabelle session over HOL alone, from definitions stated once in the ledger README's `isabelle-spec` block, so that LG-2's tests, LG-4's shapes and track C's C5 model cite a theorem rather than restate the law. The session proves nothing about the composition of evaluations, which is ADR-A130's and E4b's, and carries no term of any domain.

## Test cases

Each claim is a theorem with `(* GATE:BEGIN <id> *)` and `(* GATE:END *)` markers and a claim record under `claims/`. Level L2 throughout, the method Proof, the scope every instance unless a row says otherwise. Positive unless marked negative.

| ID | Given / When / Then | Protects |
|---|---|---|
| LA1 | an amount, a finite key set and weights / the pro rata rule splits it / the four axioms hold: the parts sum to the amount, no part exceeds its own bound, every part is non-negative, splitting the whole returns the whole | ADR-A131 d6, L2 |
| LA2 | the same / the priority rule splits it, filling keys in their order / the four axioms hold | ADR-A131 d6, L2 |
| LA3 | any rule satisfying the four axioms / the amount is zero / every part is zero. Derived, never assumed | L2 |
| LA4 | one arrangement / both lawful rules split it / they post different amounts to one key. Negative, an instance | LG-Q3, L3. A rule is declared data with an identity, never a default |
| LC1 | any lawful rule, any account tree, any sequence of draws / settled / for every key, the postings plus the residual equal the amount drawn | TD-95, L1, pointwise |
| LC2 | the same / summed / the totals agree | L1 |
| LC3 | the same / any account / nothing is posted to it beyond its availability, and the residual is non-negative | L1, L6 |
| LC4 | a share matrix with non-negative entries whose rows sum to one / attribution is applied to settled postings / the attributed amounts sum to the postings, party by party. A second law with its own statement | L8, ES-5's K4 |
| LD1 | an account tree as a parent function with no cycle, a draw on an account / applied / it debits the account and every ancestor as one operation that succeeds whole or changes nothing | ADR-A131 d3 |
| LD2 | the same tree / availability is read / it is the least of the account's remaining balance and its ancestors' | ADR-A131 d3 |
| LD3 | a credit along the same path / applied / no balance rises above its stated amount | ADR-A131 d3 |
| LD4 | a draw naming a purpose, an account outside its path counting that purpose / applied / that account is debited by the same draw and the draw still succeeds or fails whole | LG-Q2 |
| LO1 | several draws proposed at one position / merged by a lawful rule, then each settled / the postings are the same in every order of proposal | ADR-A131 d6, two phases. Generalises the spike's `order_independent` from a flat map to the tree |
| LR1 | an integer total and integer weights / split by floor division with a residual / the parts plus the residual equal the total and the residual is below the number of parts | TD-96, from the spike's `split_conserves` and `residual_bounds` |
| LR2 | the same / the residual allocated by a stated deterministic rule / the parts sum exactly to the total and the allocation is a function of its inputs alone | TD-96, ADR-A131 d6 exactness |
| LN1 | a threshold term below which nothing is posted and above which the whole is / the drawn amount rises by one / the residual falls. Negative, an instance | L5. Nothing above the ledger may assume a balance is monotone in its input |
| LG1 | the session / `check:proofs ledger` / builds with `quick_and_dirty = false`, and the gate finds no `sorry`, `oops`, `admit`, `oracle` or `axiomatization` and every claim digest matching | ADR-A-FM2 |
| LG2 | the README's `isabelle-spec` block and `Kernel.thy` / `check:formal-freshness` / they agree | epic principle E1 |

## One command

Run from the repository root.

```bash
mise run check:proofs -- ledger
```

then

```bash
mise run check:formal-freshness
```

A pass is `Finished Ledger` with exit code 0 and no `***` line, one law-report row per claim with outcome passed, and the freshness check silent.

## Artefacts to inspect

`ontology/ledger/README.md`, its new Laws section and `isabelle-spec` block. `tools/proofs/ledger/ROOT`, `Kernel.thy` (extracted, never edited), `Allocation.thy`, `Draws.thy`, `Rounding.thy`, `claims/*.json`, and the session's `README.md` with its provenance section.

## Deliberate non-coverage

The composition law, uniqueness of a solution and the least fixpoint over the information order, which are ADR-A130 decision 5's and belong to E4b after that decision is accepted. The runtime terms, postings as records and their keys, which LG-2 writes against these theorems. Conversion between value spaces (LG-Q8), carried as a hypothesis on the amount and not modelled. The derivation of one account per key value (LG-Q7). Any reinsurance or insurance structure, which is applied content and has no home in the substrate's proofs (WPG-Q4).

## Handoff

Built on machine S, 2026-11-08, on the branch the maintainer created from `main` after the squash of `docs/placement-vehicles-structure`, committed locally and not pushed.

**What was built.** Section 10 of `ontology/ledger/README.md` now states the laws' definitions in an `isabelle-spec` block, extracted to `tools/proofs/ledger/Kernel.thy`. The session `Ledger`, `session Ledger = HOL +` with `document = false` and `quick_and_dirty = false`, holds `Allocation.thy`, `Draws.thy` and `Rounding.thy`, sixteen claim records under `claims/`, and a session README with what is proved, what is assumed, what is not covered and the provenance. The kernel imports `Complex_Main`, which is part of the HOL session and is where the rationals are, and nothing from `HOL-Library`.

**Isabelle.** Isabelle2025-2, native, on Windows 11 through its bundled Cygwin. A clean build of the session gives `Finished Ledger (0:00:04 elapsed time)`, 1.9 s of theory time on 8 threads, and no `***` line.

**What was run, in full.**

- `mise run check:proofs -- ledger`: exit 0. The law report lists LA1 to LA4, LC1 to LC4, LD1 to LD4, LN1, LO1, LR1 and LR2, each `Proof passed`, then `Assumption audit: clean, no sorry/oops/admit/oracle/by-eval found` and `GATE: pass`.
- `mise run check:formal-freshness`: exit 0, `3 formal-methods artefact(s) consistent with their literate READMEs`.
- `mise run check:ontology-versioning -- --base-ref main`: exit 0, `50 in-scope ontology document(s) checked against main: no unbumped changes`. The README change adds no term and moves no extracted document, so nothing is bumped. The same run asks for the tag `persistence-store-v0.19.0`, which this slice did not cause.
- `mise run check:proofs -- eligibility`, before any edit: exit 0, `GATE: pass`, so the shared gate was working on this machine.

**Adversarial probes.** Two, each restored afterwards. Removing the ceiling from `credit` in the README's block and rebuilding fails LD3's first conclusion at `Draws.thy` line 103. Weakening LN1's `<` to `\<le>` without its claim record gives `[STATEMENT DIGEST MISMATCH, unreviewed restatement]` and `GATE: fail`.

**Deviations from the brief, with reasons.**

- **LG1 and LG2 have no claim record.** They are the two commands above rather than theorems, so they are checked by running them.
- **LO1 and LR2's order independence is over two lists without repeats that hold the same proposals**, rather than over multisets, since multisets are in `HOL-Library`. A second order of the same proposals is exactly such a pair.
- **LR2 proves `ldg:ToFirstInOrder` only.** `ldg:LargestRemainder` is not proved, and the reference evaluator sketch's RE-Q4 leans to it as the default, so it is the next rounding theorem to write.
- **The refinement between `rat` and `int`** is one lemma, `Rounding.floor_part_refines`, putting a floor part within one unit below the exact share. Nothing more of the refinement was cheap.
- **LC3 bounds the first posting by its account's availability** and proves no balance in the tree goes below zero over the whole sequence, which is the same law stated for every step.
- **Positions.** The kernel's `before` is proved a strict total order and is used by no claim, since every claim here is about one position.
- **The examples come first** in `Allocation.thy` and `Rounding.thy` as `value` checks, and each positive one is also a lemma proved by `simp`, since a `value` prints and checks nothing.

**WPG-Q1, answered (a).** With the body a parameter carrying only the congruence, the uniqueness, existence and exactly-one proofs went through, in a scratch session outside the repository on 2026-11-08. The scratch session and its build log were deleted.

**What to check first.** The four axioms in the README's block against ADR-A131 decision 6 and the sketch's L2, and the hypotheses of LC1 to LC3, which are what LG-2's laws as tests and LG-4's conservation shape will cite.

## Results

Filled at verification.
