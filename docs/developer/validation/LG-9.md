<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: Ledger LG-9, the target kernel in the README and the 19 claims proved again on it

**Unit:** `ledger` ([plan](../plans/ledger.md), LG-9, [status](../status/ledger.md)).
**Machine:** S. **Branch:** `fm/ledger-proofs-on-the-target-kernel`, per the [machine S brief of 2026-11-15](../notes/machine-s-brief-2026-11-15.md). Commits are local, and pushing is the maintainer's.
**Brief:** the ledger plan's "LG-9, the target kernel in the README, and the 19 claims proved again on it", restated 2026-11-15 under LG-Q27 (b).
**Decisions:** LG-Q27 (b), LG-Q28 K1 to K6, LG-Q16 (c) by default, TD-161, LG-Q14 (d).
**Depends on:** LG-8 ([its pack](LG-8.md)) and LG-21, the [target kernel](../sketches/ledger-target-kernel.md) and its [spike](../../../spikes/ledger-target-kernel/README.md).

## Invariant

`Kernel.thy` is extracted from the ledger README and holds the definitions of the target kernel unchanged, in the spike theory's order, so the 600 generated cases give the same results on it as on the spike. Every claim of LG-7 and LG-8 is a theorem on those definitions between gate markers, keeping its identifier, with a claim record whose digest matches, and the path is given as a list so that what reads a path evaluates.

## Test cases

Each claim is a theorem with `(* GATE:BEGIN <id> *)` and `(* GATE:END *)` markers and a claim record under `tools/proofs/ledger/claims/`. Level L2, the method Proof.

| ID | Given / When / Then | Protects | +/- |
|---|---|---|---|
| LG9-R0a | the README's `isabelle-spec` blocks / extracted by `literate_extract.py` / `Kernel.thy` holds every definition of `Target.thy`, byte for byte after whitespace, in its order, with `shares_ok` and `attributed` restated beside them | epic principle E1 | + |
| LG9-R0b | the 600 cases of `cases.py` / evaluated on the extracted kernel, `Ledger_Target_Kernel` / each agrees with the model, as on `Target.thy` | the move changes no result | + |
| LG9-R0c | an account rounding half-even beside largest remainder, stating no treatment of the difference / validated / refused by `ldg:NearestRoundingStatesTheDifferenceShape`, and `authority-aggregate.ttl`, now toward zero, conforms | LG-Q16 (c) | - |
| LX1 | a tree and an account in it / the walk up by at most as many steps as there are accounts / lists the path exactly, with no repeat | R1, the path as a list | + |
| LA1 | any finite key set / the proportional rule over an ordered field / lawful | ADR-A131 d6 | + |
| LA2 | a rank injective on the keys and any rule for a tie / by rank / lawful, and it is the priority formula | `ldg:InPriorityOrder`, TD-161 | + |
| LA3, LA4 | as LG-7's, LA4 with by rank in place of the priority rule | ADR-A131 d6 | +, - |
| LC1, LC2 | any rule and any sequence of accounts charged / `spread` / every key's parts plus what is left equal what was asked, and every account falls by the parts granted at the accounts that charge it | L1, conservation | + |
| LC3 | a rule that rations and accounts charged that are finite and non-empty / any step / no balance below zero and every part within the least balance left on what it charges | L1, L6 | + |
| LC4 | a rule that apportions, a basis for each part of positive total, parts of non-negative total / attributed / exactly, and no party negative | TD-95 | + |
| LD1 to LD4 | as LG-7's, LD3 on the new credit, which returns the applied amount, the cuts and the balances | ADR-A131 d3, d4 | + |
| LO1 | two proposal lists with the same multiset / settled by any policy and rank / the same outcome and balances | two phases | + |
| LN1 | as LG-7's | the residual | - |
| LR1 | as LG-8's, with `short` for what floor division leaves | TD-96 | + |
| LR2 | an order injective on the keys, requests non-negative, an amount from zero to what was asked / `ration (to_first order)` / sums exactly, and is the same for every proposal list with the same multiset | `ldg:ToFirstInOrder`, TD-161 | + |
| LR3 | the same / `ration (largest_remainder (first_in order))` / sums exactly, a key reached has a remainder at least that of any key not reached, and the same for every multiset | `ldg:LargestRemainder`, TD-161 | + |
| LR4 | an order injective on the keys / both rules under rationing / lawful over whole units on every non-negative request | ADR-A131 d6 | + |
| LR5 | a part, and an amount allocated across accounts / rounded by largest remainder and exactly by any lawful rule / within one unit of the exact share, strictly so under largest remainder, every account charged the same, every key conserved | TD-96, L1 | + |
| LG9-g | the session / `mise run check:proofs -- ledger` / builds with `quick_and_dirty = false`, the gate finds no banned marker and every digest matches | ADR-A-FM2 | + |
| LG9-f | the README's blocks and `Kernel.thy` / `mise run check:formal-freshness` / they agree | epic principle E1 | + |
| LG9-p1 | a weakened LR4 statement without its claim record / the gate / `STATEMENT DIGEST MISMATCH` on LR4 and `GATE: fail` | the gate | - |
| LG9-p2 | a broken `unmet` in the extracted kernel / the build / a theorem fails | the theorems | - |

## One command

```bash
mise run check:proofs -- ledger
mise run check:formal-freshness
```

## Artefacts to inspect

`ontology/ledger/README.md` section 10, its blocks and prose, the vocabulary definitions of `ldg:InPriorityOrder`, `ldg:ToFirstInOrder` and `ldg:LargestRemainder`, the new constraint in section 7.2, and the terms proposed in section 13. `ontology/ledger/examples/authority-aggregate.ttl` and `refusal-nearest-beside-residual.ttl`. `tools/proofs/ledger/Kernel.thy` (extracted), `Allocation.thy`, `Draws.thy`, `Rounding.thy`, `claims/*.json` and the session's `README.md`. `tools/proofs/gate.py`. `spikes/ledger-target-kernel/cases.py`, `kernel/ROOT` and `kernel/Kernel_Cases.thy`.

## Deliberate non-coverage

Every law the target kernel gains, which is LG-20's. The shapes and the runtime document, LG-2's rework, beyond the one constraint LG-Q16 asks for. Code export, and the composition law, which is E4b's. Any benchmark. Positions, which the target kernel does not define, so LG-7's supporting lemma that positions are a strict total order goes with `before`.

## Handoff

Built on machine S, 2026-11-16, Isabelle2025-2 through its bundled Cygwin, committed locally and not pushed.

**What was built.**

- **R0, the kernel moves.** Section 10 of the ledger README holds the definitions of `Target.thy` in its order, in blocks of their own, each group with the prose it needs, and `Kernel.thy` was extracted from it and never edited. No definition of `Target.thy` changed, and the spike is untouched but for its cases. `shares_ok` and `attributed` are restated as an apportionment. Each part's total is apportioned among the parties by a basis for that part and a rule that apportions, and `shares_ok` says each basis is non-negative with a positive total. The old share matrix is the proportional rule with its rows as the bases. The six examples of `Target.thy` are `value` checks and lemmas by `code_simp` at the head of `Allocation.thy`. `cases.py` also writes `kernel/Kernel_Cases.thy`, the same 60 lemmas importing `Ledger.Kernel`, built by a session of its own in `kernel/ROOT` that loads the kernel from source, so the spike's own `ROOT` still builds alone. The vocabulary's three definitions say the order is the account's declaration, never the identifiers'. The constraint LG-Q16 asks for is `ldg:NearestRoundingStatesTheDifferenceShape`, with a refusal example and its row in `tools/test_ledger.py`, and `authority-aggregate.ttl` rounds toward zero.
- **R1, the path as a list.** LX1, `Draws.chain_is_the_path`, and `available_by_chain` from it. The code equation is `Draws.path_step`, the path unfolded one step, which needs no hypothesis to state and whose evaluation is the walk LX1 bounds. With it and the code equation for `inj_on`, `value` and `code_simp` evaluate `settle`, `spread`, `pots` and `credit` on four examples. No `export_code`.
- **R2, the 19 claims.** Each restated on the target and proved, keeping its identifier, with its record redigested and its `statedAs` and scope moved where the theorem's name or reach changed.

**Statements changed, and the hypotheses they gained or lost.**

- LA2 is by rank with a rank injective on the keys, as planned, and holds for any rule for a tie.
- LC1 and LC2 hold of any rule. LG-7 asked a lawful rule and a finite key set, and neither is needed, since `spread` subtracts what it grants and charges the total of what it grants.
- LC3 asks a rule that rations, weaker than lawful, and accounts charged that are finite, non-empty and within the set whose balances start non-negative, in place of a tree. A path in a tree is such a set (`Draws.path_charged`).
- **LC4 gained a hypothesis.** The parts attributed have non-negative totals, since an apportionment shares a non-negative amount. The old share matrix multiplied any total.
- LD3's second part, that a credit undoes a draw, is stated with every account accepting the credit, since the new `credit` takes only where an account accepts its kind.
- LO1 holds for any policy and rank.
- **LR2 and LR3 gained hypotheses.** Under rationing the amount is from zero to what was asked and the requests are non-negative, and the order is injective on the keys. LG-8's statements held for any total by positive weights, since they gave a unit to any key. Rationing gives one only to a request not yet met, and with 3 units by weights 1 and 1, both floor parts are 1, both requests are met, and the unit short has nowhere to go. That case is outside rationing, so it is not a counterexample to a law, and no LG-Q is raised.
- **LR4 lost one.** To the first in order is lawful on every non-negative request, where LG-8 needed positive weights, since under rationing a request of no weight is met and takes no unit. LG-8's first finding is answered for rationing by the definition (`Rounding.example_a_key_of_no_weight` shows both sides).
- LR5's spread asks accounts charged that are finite and non-empty in place of a tree, and an order injective on the keys for largest remainder.
- K1 held throughout. Every definition that only adds, subtracts and compares is used at any ordered ring, the proportional rule at any ordered field, and the rules over whole units at `int`. No claim needed proving twice at `rat` and `int`.

**Findings.**

1. **The gate read `admit` in an Isabelle theory as Coq's marker.** The target kernel defines a function `admit`, so the assumption audit failed on `Kernel.thy`. `gate.py` now scans a `.thy` file for Isabelle's markers alone, `sorry`, `oracle`, `axiomatization` and `by eval`, and a `.v` file as before.
2. **The gate's digest did not cover records.** `policy` and `book` are records, and `DEF_HEADER` matched no `record`, so changing a field would have moved no digest. It now matches `record`.
3. **No definition was found wanting.** Every statement proved as planned or with the hypotheses above, and no counterexample was found, so the model's examples are unchanged.
4. **`tie` is a field of `policy`**, so a rule for a tie in a statement is named `tr`.

**Terms proposed in the README for review** (section 13), not declared. `ldg:SplitKinds` with `ldg:Rationing` and `ldg:Apportionment`. `ldg:leavesResidual`. `ldg:declaredOrder`, `ldg:distinctRanks`, `ldg:tieRule` and `ldg:refusesMixedPurposes`. `ldg:RefusalReasons` with `ldg:Exceeds`, `ldg:Unranked`, `ldg:Tied`, `ldg:Undecided`, `ldg:Mixed` and `ldg:Crossing`. `ldg:roundingDifference` with `ldg:RoundingDifferences`, `ldg:ShownOnly` and `ldg:SettledToNearest`, which the new constraint reads, so until it is declared the constraint refuses every account rounding to the nearest beside a residual rule.

**What was run, each output read in full.**

- Every build during the work was `driver.py --route native --workdir tools/proofs isabelle build -d base -d ledger Ledger`, one at a time. Two proof attempts timed out at the session's 90 s bound, each a `blast` over general lemmas, rewritten with explicit steps. The session builds in about 14 s.
- `Ledger_Target_Kernel`, the 600 cases on the extracted kernel, from clean: `Finished Ledger_Target_Kernel (0:00:36 elapsed time)`. The spike's own `Ledger_Target`: `Finished Ledger_Target (0:00:37 elapsed time)`. `cases.py` rewrote `Cases.thy` unchanged.
- `mise run check:proofs`, every session: `LatticeBase` `GATE: nothing to gate`, Eligibility `GATE: pass`, ledger twenty rows, LA1 to LA4, LC1 to LC4, LD1 to LD4, LN1, LO1, LR1 to LR5 and LX1, each `Proof passed`, `Assumption audit: clean`, `GATE: pass`.
- `mise run check:formal-freshness`: `3 formal-methods artefact(s) consistent with their literate READMEs`.
- `mise exec -- python -m pytest tools/test_ledger.py`: `37 passed`, with the new refusal among them.
- `mise run check:ontology-versioning -- --base-ref main`: UNBUMPED, three release member files changed since main at release 0.21.2, as the brief expected, and not acted on.
- `mise exec -- python spikes/ledger-target-kernel/model.py 20`: ran to the end with exit 0, so no law broke on any case drawn.

**Adversarial probes**, each restored and the restore checked.

- **A weakened statement.** LR4's first conclusion as `rations` in place of `lawful`, with its record unchanged: `gate.py` printed LR4 with `[STATEMENT DIGEST MISMATCH, unreviewed restatement]` and `GATE: fail`, exit 1, and no other claim. Restored, `GATE: pass`.
- **A broken definition.** `unmet` with `\<le>` in place of `<` in the extracted `Kernel.thy`, so a request met in full may take a unit: the build failed at `Rounding.thy` line 52, the example of a key of no weight, and line 472, the bound `floor_units_bounds` on which LR4 rests. Restored by extraction, the kernel's hash matched the one before the probe, and `check:proofs -- ledger` gave `GATE: pass`.

| Row | Result |
|---|---|
| LG9-R0a | pass |
| LG9-R0b | pass |
| LG9-R0c | pass |
| LX1 | pass |
| LA1 to LA4 | pass |
| LC1 to LC4 | pass |
| LD1 to LD4 | pass |
| LO1, LN1 | pass |
| LR1 to LR5 | pass |
| LG9-g | pass |
| LG9-f | pass |
| LG9-p1 | pass |
| LG9-p2 | pass |

## Results

**The maintainer's verdict** is written here when given. The row on the board moves to `verified` with it.

**A third probe, picked by the agent at the maintainer's word on 2026-11-16, on machine R after the merge.** `available` in the extracted `Kernel.thy` edited by hand to `bal a`, the account's own balance and not the least along its path, with the README unchanged. `mise run check:formal-freshness` failed, exit 1, with `DRIFT` on `Kernel.thy` against the README's blocks, which is R0's claim that the kernel is extracted and never edited. `mise run check:proofs -- ledger` failed, exit 1, at `Draws.example_pots`, `Merge.no_purpose_is_settle` and `Pots.the_unit_left_is_withheld_along_the_path`. Restored from a copy, `git diff` empty, then 3 artefacts consistent, 72 rows `Proof passed`, `Assumption audit: clean` and `GATE: pass`.
