<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Machine S brief, 2026-11-15: the ledger proofs on the target kernel

**Handed over by the maintainer on 2026-11-16**, after reviewing the target kernel's definitions, on the branch `fm/ledger-proofs-on-the-target-kernel`, cut from `main` once this brief was on it.

**For:** the agent on machine S, Windows 11, Isabelle2025-2 through its bundled Cygwin, where LG-7, LG-2, FME-0 and LG-8 were built. **Written on** `docs/placement-vehicles-structure` at the maintainer's request, as the end of slice LG-21. It replaces the [brief of 2026-11-13](machine-s-brief-2026-11-13.md), which was never handed over. It is one bundle of work, two slices on one branch, to be returned whole.

## Why the plan changed

LG-9 and LG-20 were planned as two widenings of the kernel, 17 parts in the order the questions were decided, which would have changed or doubled 12 of its 38 definitions. The maintainer decided on 2026-11-15 (LG-Q27) that the kernel is written once in its decided form first, and that you prove on that. It has been written, type-checked and tried on generated cases, and its questions are decided (LG-Q28). Read the [sketch](../sketches/ledger-target-kernel.md) before anything else. It says why each definition is as it is, which law each must keep and which it gains, and what writing them down found.

Machine S runs Isabelle and no benchmark. Nothing below needs a measurement.

## What you are given

| | Where | What it is |
|---|---|---|
| the definitions | [`spikes/ledger-target-kernel/Target.thy`](../../../spikes/ledger-target-kernel/Target.thy) | 78 definitions and six evaluated examples, type-checked on the HOL heap, with no law proved. They are decided. You move them and prove on them, and you do not redesign them |
| the two tied together | [`spikes/ledger-target-kernel/Cases.thy`](../../../spikes/ledger-target-kernel/Cases.thy), written by `cases.py` | 600 inputs on which Isabelle evaluates the definitions and compares with the model, all agreeing. After R0, point it at the extracted kernel and it must still build |
| a search of the laws | [`spikes/ledger-target-kernel/model.py`](../../../spikes/ledger-target-kernel/model.py) | the definitions transliterated, with each law of LG-20 asserted on generated cases. It found no counterexample and proves nothing. It runs with the standard library alone |
| the two slices | the [ledger plan](../plans/ledger.md), under "LG-9" and "LG-20" | every part and every law, by name |

## The branch

One branch, `fm/ledger-proofs-on-the-target-kernel`, cut from `main` after this brief has been merged into it, and pushed. Both slices are built on it, LG-9 first, one commit for each mark and one a part or a group at least, each with the trailers [GENAI_CONTRIBUTION.md](../../../GENAI_CONTRIBUTION.md) requires and a `Placement: T0, substrate proofs` trailer where the guard asks for one. Commit locally and push only when the maintainer says so. The maintainer merges.

## What machine S does and does not do

Isabelle work and the checks that go with it. Never a benchmark, none of the `check:ledger-credit-kinds` tasks, `check:ledger-posting-cost`, `check:ledger-late-posting`, `check:ledger-cross-family`, `check:ledger-graph-partition`, `check:sparql-constraint-query-cost` or `check:mork-rdf-run-cost`. Never the `HOL-Library` heap. Never a version bump, a tag, a merge or a push without the maintainer's word. No row moved to `verified`, which is the maintainer's. Take no decision the plan leaves open, and change no definition.

**A statement that will not prove is a result.** Every law is a hypothesis until it is proved. Where one is false as written, keep the counterexample as a negative instance, record the question in the [ledger plan](../plans/ledger.md) with the next free `LG-Q` number, and say so in the handoff. Never weaken a statement, add a hypothesis or change a definition to make it pass without saying that you did and why, since a law that needed a hypothesis is a different law and the design must hear of it.

**A definition that is wrong is a result too.** If a definition of `Target.thy` cannot carry a law it is meant to, or does not say what the sketch says it does, stop that part, show the smallest case, and say so. The search found three such faults before you, and they are in the sketch's section 4. Do not repair a definition on your own.

**Where the search and a proof disagree.** The model asserts each law of LG-20 on small cases. Where a proof fails on a law the search holds, say what kind of case the search could not have drawn. Where you find a counterexample, add it to the model's examples in the same commit, so the search would now catch it.

## Before the first edit

`mise run bootstrap`, since `main` moves its pins. `mise run work:here -- --role build --model <model>`. Then mark before you touch, the LG-9 row in the [ledger status record](../status/ledger.md) to `building <day>` with a history line, `mise run build:work`, and that commit alone. Mark LG-20 the same way on the day LG-9 is built. One Isabelle build at a time.

What was learned on FME-0 and LG-8 holds. A session's timeout lives in its `ROOT`, and no `-o` is passed on a command line, since it reaches the parent and rebuilds it. Every build runs from `tools/proofs/`, as `mise run check:proofs -- ledger` does, and the prelude is built with `-b` so its heap is saved. A proof by `auto`, `fastforce` or `blast` under a congruence rule can loop to the session's bound, so write the steps out where one does not return at once. The gate's digest covers every definition in the layer, so the new kernel redigests every claim record, and each restated claim is a reviewed restatement.

## The slices

**LG-9, the target kernel in the README, and the 19 claims proved again on it.** Row LG-9, brief in the plan under that name. Three parts in order. R0 moves the definitions into the README's `isabelle-spec` block, and leaves the README naming a decision only in its section 5.1 and no working-document identifier anywhere (STD-337), from which `Kernel.thy` is extracted by `mise exec -- python tools/literate_extract.py ontology/ledger/README.md --layer ledger --root . --proofs-root tools/proofs`, never by hand. R1 gives the path as a list, so the examples evaluate. R2 restates each of the 19 claims of LG-7 and LG-8 on the new definitions and proves it, keeping its identifier. Between R0 and the end of R2 the session does not build whole. That is expected, and no commit in that stretch is pushed as a passing state.

**LG-20, the laws the target kernel gains.** Row LG-20, brief in the plan under that name, after LG-9. Seven groups by definition, in the plan's order: the predicates, ranks, whole units, the merge and settlement with purposes, allocation and pots, credits and the sum, and the readings. Each group names its laws and the negative instances to keep.

Read first, for both: the target kernel's [sketch](../sketches/ledger-target-kernel.md) whole, LG-8's [pack](../validation/LG-8.md) with its Results, the [sketch on balances under post-once](../sketches/ledger-balances-under-post-once.md) §3, §4.8, §4.9 and §5, the [posting scenarios note](ledger-posting-scenarios.md) for the rulings each law rests on, and the session's README.

The kernel keeps `imports Complex_Main`. A library theory is imported by the theorem theories alone, and only one the prelude already holds. If a part needs a library theory the prelude lacks, stop and say so, since adding one is a reviewed change to `tools/proofs/base/Prelude.thy`. Examples come first in each theory, as `value` checks that are also lemmas. Each claim is a theorem between `(* GATE:BEGIN <id> *)` and `(* GATE:END *)` with a claim record under `claims/`.

**The number type.** The definitions that only add, subtract and compare are stated once over an ordered ring (LG-Q28, K1). How much of the existing proofs that moves is not known. Where a claim that held over the rationals will not prove over an ordered ring within a day's work, prove it at `rat` and at `int`, say so in the handoff, and leave the definition as it is.

The README changes with both slices, which moves an extracted document, so `mise run check:ontology-versioning -- --base-ref main` will report it unbumped. That report is expected and is not acted on, since versions move at the merge into `main`. Where a part needs a vocabulary term the README does not have, propose it in the README for review and name it in the handoff.

## What is decided, and where

| Decision | What it says | Where |
|---|---|---|
| LG-Q27 (b) | the kernel is written once in its decided form before more is proved on it | the plan |
| LG-Q28, K1 to K6 | one statement for whole units and exact amounts, reading B by the account's own policy, purposes at one position, a refusal at one pot, a residual declared, a unit short under rounding to the nearest | the sketch's sections 6 and 7 |
| LG-Q23, LG-Q26, LG-Q12, LG-Q13, LG-Q17, LG-Q18 | the cut record, the readings, an allocation whole, a purpose honoured, a residual, an order by rank | the plan's question table, MEC-106 to MEC-109, STD-328 to STD-333 |
| scenarios F1, G1 to G3, C1 | a tie, ranks as tiers and pots, a ballot, a floor, a unit left unpaid | the [posting scenarios note](ledger-posting-scenarios.md), MEC-110 to MEC-112 |

Nothing is held back for want of a ruling.

## The packs

`docs/developer/validation/LG-9.md` and `docs/developer/validation/LG-20.md`, in the lifecycle skill's form, a row per claim, what was left out named with what it waits on, and a handoff with every command's output read in full.

## Checks

`mise run check:proofs -- ledger`, `mise run check:proofs` once for every session, `mise run check:formal-freshness`, `mise exec -- python -m pytest tools/test_ledger.py` since the README changes, `mise run check:ontology-versioning -- --base-ref main`, and `mise exec -- python spikes/ledger-target-kernel/model.py 20`, which must still pass after any example you add to it. Two adversarial probes for each slice, a weakened statement the digest catches and a broken definition a theorem catches, each restored and the restore checked.

## What you return

The branch, with LG-9 and LG-20 both built or with a plain account of where each stopped. At each slice's handoff: the pack's handoff, the status record's history and the row at `built <day>`, `mise run build:roadmap -- --fetch` with the hand-written sections read against the records the work changed, and `mise run graph:ask -- misses --near` reported. End with what each slice left out and why, with each statement that was changed to make it prove and the reason, with each definition you found wanting, and with 🔴 RELEASE TAGS REQUIRED if the versioning check lists tags.
