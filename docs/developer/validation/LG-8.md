<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: Ledger LG-8, the proofs widened on HOL-Library

**Unit:** `ledger` ([plan](../plans/ledger.md), LG-8, [status](../status/ledger.md)).
**Machine:** S. **Branch:** `fm/prelude-and-ledger-proofs`, per the [machine S brief](../notes/machine-s-brief-2026-11-08.md). Commits are local, and pushing is the maintainer's.
**Brief:** the ledger plan's "LG-8, the proofs widened on HOL-Library", sized claim by claim in the [sketch on balances under post-once](../sketches/ledger-balances-under-post-once.md) §6.
**Decisions:** LG-Q14 decided (d), ADR-A-FM2's addendum of 2026-11-08, ADR-A131 decision 6, TD-96. LG-Q11 is open, so LM1 is out.
**Depends on:** track E's FME-0, the prelude `LatticeBase` ([its pack](FME-0.md)), and LG-7 ([its pack](LG-7.md)), whose deviations this slice closes.

## Invariant

The ledger session parents on the prelude and reaches `HOL-Library` through it alone. The laws LG-7 stated over two lists without repeats, the first step only, or the first-in-order rule only now hold in their natural form, and every claim stays a theorem between gate markers with a claim record whose digest matches.

## Test cases

Each claim is a theorem with `(* GATE:BEGIN <id> *)` and `(* GATE:END *)` markers and a claim record under `tools/proofs/ledger/claims/`. Level L2, the method Proof.

| ID | Given / When / Then | Protects | +/- |
|---|---|---|---|
| LO1 | two lists of proposals at one position with the same multiset / merged by any rule and settled / the same postings and balances. A reviewed restatement of LG-7's two lists without repeats | ADR-A131 d6, two phases | + |
| LR3 | an integer total and integer weights with a positive sum / the residual given to the largest remainders, ties in key order / the parts sum exactly to the total, a key reached has a remainder at least that of any key not reached, and the result depends on the weights alone in every order | `ldg:LargestRemainder`, TD-96, RE-Q4 | + |
| LR4 | a total from zero to the sum of the weights / either integer rule / the four axioms over whole units, for largest remainder on every non-negative weight and for to the first in order on positive weights | ADR-A131 d6 | + |
| LR4n | one unit in weights 0, 3 and 3 / to the first in order / key 0, of weight 0, gets the unit. Negative, an instance, the reason for LR4's positive-weight hypothesis | `ldg:ToFirstInOrder` | - |
| LR5 | any part, and any amount drawn across any sequence of accounts in a tree / rounded by largest remainder over whole units, and exactly by any lawful rule / each part is within one unit of its exact share, every account gives up exactly what the exact split takes, and every key conserves exactly | TD-96, L1 | + |
| LC3 | any lawful rule, tree and sequence / any step *i* / the posting at step *i* is within its account's availability in the balances the first *i* steps left. A reviewed restatement of LG-7's second conclusion, which bounded the first step only | L1, L6 | + |
| LG8-g | the session / `mise run check:proofs -- ledger` / builds with `quick_and_dirty = false`, the gate finds no banned marker and every digest matches | ADR-A-FM2 | + |
| LG8-f | the README's block and `Kernel.thy` / `mise run check:formal-freshness` / they agree | epic principle E1 | + |
| LG8-p1 | a weakened LR3 statement without its claim record / the gate / `STATEMENT DIGEST MISMATCH` on LR3 and `GATE: fail` | the gate | - |
| LG8-p2 | a broken `largest_remainder` in the README's block, extracted / the build / a theorem fails | the theorems | - |

## One command

```bash
mise run check:proofs -- ledger
mise run check:formal-freshness
```

## Artefacts to inspect

`ontology/ledger/README.md` section 10, its new prose and the `remainder`, `largest_remainder` and `spread_int` definitions. `tools/proofs/ledger/Kernel.thy` (extracted), `Draws.thy`, `Rounding.thy`, `claims/*.json`, and the session's `README.md`.

## Deliberate non-coverage

LM1, which waits on LG-Q11. Largest remainder inside `merge` at one position, since `merge` takes a rule over exact amounts. Code export of `spread_int` and `draw`, which the brief leaves out, and which `path`, a set defined by a transitive closure, would not support as it stands. LR2's own order independence stays over two lists without repeats, since the brief restates LO1 only. The fold shapes LG-Q9 changes, which are LG-2's, and the composition law, which is E4b's.

## Handoff

Built on machine S, 2026-11-09, Isabelle2025-2 through its bundled Cygwin, after FME-0 on the same branch, committed locally and not pushed.

**What was built.**

- **The kernel.** Section 10 of the ledger README gains `remainder`, `largest_remainder`, which takes `take` of the residual's units from `sort_key` by the negated remainder over `sorted_list_of_set K`, so ties stay in key order, and `spread_int`, the split of an amount across several accounts in turn over whole units with a rounding rule in place of an exact one. `Kernel.thy` was extracted with `literate_extract.py --proofs-root tools/proofs`, never edited, and keeps `imports Complex_Main`. No other extracted document changed.
- **`Draws.thy`** imports `Allocation "HOL-Library.Multiset"`. LO1 is restated over `mset ps = mset ps'`, through `requested_mset`. LC3's second conclusion is restated for every step, through `spread_step`, which shows the posting at step *i* is the rule applied to what the first *i* steps left, and `available_nonneg`.
- **`Rounding.thy`** imports `Draws "HOL-Library.Multiset"` and gains LR3, LR4 with the definition `int_lawful`, the four axioms over whole units, and LR5, with examples first: one arrangement where the two rules give 6, 3, 1 and 5, 3, 2, and the zero-weight instance.
- **Claim records.** LR3, LR4 and LR5 are new. LO1's and LC3's scopes move with their restatements, to `EveryProposalListWithTheSameMultiset` and `EveryLawfulRuleTreeSequenceAndStep`. Every one of the sixteen existing records was redigested, since the gate's digest covers every definition in the layer and the kernel and `Rounding.thy` gained definitions. Only LO1's and LC3's statements changed.
- **The session README** says how the session reaches the library, and its what-is-proved, what-is-assumed and what-is-not-covered sections move with the claims.

**Three findings.**

1. **To the first in order is lawful only on positive weights.** It gives a residual unit to the first key whatever its weight, so one unit in weights 0, 3 and 3 goes to the key of weight 0, past its bound (`Rounding.to_first_can_exceed_a_zero_weight`). Largest remainder never does, since a key it reaches has a positive remainder and so a positive weight. So LR4 states to the first in order under a positive-weight hypothesis, and `spread_int` is proved with largest remainder, since a request fully met part way through a sequence has weight zero. Whether `ldg:ToFirstInOrder` needs a shape refusing a zero-weight key, or is retired in favour of largest remainder, is the maintainer's.
2. **Rounding moves amounts between keys and never between accounts.** The sketch asked for each account's rounded balance within one unit per posting of the exact balance. It is equal, exactly, since at every step the amount taken from an account is the least of what is still requested and what the account affords, and both the rounded and the exact split leave the same total still requested. LR5 states the equality.
3. **Per key, the rounded and exact splits agree within one unit at a single part only.** After the first account the rounded and exact amounts still requested per key differ, so the parts at later accounts are not compared key by key. LR5's per-key statement is exact conservation over whole units instead.

**What was run, each output read in full.**

- Every build during the work was `driver.py --route native --workdir tools/proofs isabelle build -d base -d ledger Ledger`, one at a time. One proof attempt timed out at the session's 90 s bound, and bisecting found the loop among four helper lemmas proved by `auto`, `fastforce` and `blast` with a congruence rule. They were rewritten with explicit steps, and the build has stayed under ten seconds since.
- `mise run check:proofs`, every session: exit 0. `LatticeBase` current, `GATE: nothing to gate`. Eligibility current, 33 claims passed, `GATE: pass`. `Running Ledger ... Finished Ledger (0:00:09 elapsed time)`, 0:00:23 with Isabelle's start, and the law report lists LA1 to LA4, LC1 to LC4, LD1 to LD4, LN1, LO1 and LR1 to LR5, each `Proof passed` with no digest mismatch, `Assumption audit: clean, no sorry/oops/admit/oracle/by-eval found`, `GATE: pass`.
- `mise run check:formal-freshness`: `3 formal-methods artefact(s) consistent with their literate READMEs`.
- `mise run check:ontology-versioning -- --base-ref main`: exit 0, `55 in-scope ontology document(s) checked against main: no unbumped changes`, and no tag asked for. The README change adds no term and moves no extracted document, so the UNBUMPED report the brief expected did not come.

**Adversarial probes**, each restored and the restore checked by the full run above.

- **A weakened statement.** An added hypothesis `0 \<le> t` on `largest_remainder_sums_exactly`, with LR3's record unchanged: `gate.py` printed LR3 with `[STATEMENT DIGEST MISMATCH, unreviewed restatement]` and `GATE: fail`, exit 1, and no other claim.
- **A broken definition.** `take (nat (leftover t K w) + 1)` in the README's `largest_remainder`, extracted to `Kernel.thy`: the build failed, exit 1, at `Rounding.thy` lines 324 (`largest_remainder_sums_exactly`), 341 (`largest_remainder_takes_the_largest`), 434 and 446.

| Row | Result |
|---|---|
| LO1 | pass |
| LR3 | pass |
| LR4 | pass |
| LR4n | pass, `to_first_can_exceed_a_zero_weight` by `code_simp` |
| LR5 | pass |
| LC3 | pass |
| LG8-g | pass |
| LG8-f | pass |
| LG8-p1 | pass |
| LG8-p2 | pass |
| LM1 | not built, LG-Q11 open |

## Results

**Recorded 2026-11-09, verification not yet closed.**

**What was run.** On 2026-11-09 the maintainer ran `mise run check:proofs` on machine R, in a checkout of machine S's branch, and read its output. `Finished LatticeBase (0:01:12 elapsed time)`, `GATE: nothing to gate`. `Finished Eligibility (0:00:02 elapsed time)`, 33 claim rows each `Proof passed`, `GATE: pass`. `Finished Ledger (0:00:05 elapsed time)`, nineteen claim rows, LA1 to LA4, LC1 to LC4, LD1 to LD4, LN1, LO1 and LR1 to LR5, each `Proof passed`, `Assumption audit: clean, no sorry/oops/admit/oracle/by-eval found`, `GATE: pass`. The ledger's report names every theorem this slice gated: LO1 `settled_the_same_in_every_order_of_proposal`, LC3 `nothing_posted_beyond_availability`, LR3 with its three theorems, LR4 with `largest_remainder_lawful` and `to_first_lawful_on_positive_weights`, and LR5 with `rounded_part_within_one_unit` and `rounded_spread_takes_what_the_exact_takes`. That covers row LG8-g. `mise run check:formal-freshness`, run on the merged tree the same day in the session that wrote this section: `3 formal-methods artefact(s) consistent with their literate READMEs`. That covers row LG8-f. The two probes, LG8-p1 and LG8-p2, were machine S's and were not repeated.

**What review found.** The statements were read against the sketch that sized them. LO1, LC3 and LR3 are what was asked. LR5 is stronger than asked on one point and narrower on another, both rightly: an account's rounded balance equals its exact balance, where the sketch asked for within one unit, and the per-key bound of one unit holds at a single part only, so the per-key statement is exact conservation. The handoff's first finding is a decision, raised as LG-Q15 with LG-Q16 beside it in the [sketch on the residual to the first in order](../sketches/ledger-residual-to-first-in-order.md). What is left for LG-9: LR2's order independence over multisets, a merge at one position over whole units, and LM1 once LG-Q11 is answered.

**What the maintainer reads to close it.**

- the ledger README's section 10, the new prose and the definitions `remainder`, `largest_remainder` and `spread_int`
- the statements of LR3, LR4 and LR5 and the definition `int_lawful` in `tools/proofs/ledger/Rounding.thy`, and of LO1 and LC3 in `Draws.thy`, each between its gate markers
- the three findings of the handoff above
- the [sketch on the residual to the first in order](../sketches/ledger-residual-to-first-in-order.md), for LG-Q15 and LG-Q16

**The maintainer's verdict** is written here when given. The row on the board moves to `verified` with it.
