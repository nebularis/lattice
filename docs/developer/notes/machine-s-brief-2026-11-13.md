<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Machine S brief, 2026-11-13: the ledger proofs' second and third widening

**Draft, a first version. Not yet handed over.** The maintainer amends it once the remaining posting scenarios are ruled, and hands it over then. Until that day nothing here is started.

**For:** the agent on machine S, Windows 11, Isabelle2025-2 through its bundled Cygwin, where LG-7, LG-2, FME-0 and LG-8 were built. **Written on** `docs/placement-vehicles-structure` at the maintainer's request, after the ledger's open questions were decided on 2026-11-12 and 2026-11-13. It replaces the [brief of 2026-11-09](machine-s-brief-2026-11-09.md), whose slice LG-9 was planned and never started. It carries LG-9 as that brief stated it, with the two parts that waited on a question now decided, and adds LG-20.

## Why now, and why these

Machine S runs Isabelle and no benchmark. Everything below needs no measurement: each part states in the kernel something the maintainer has decided, and proves it or refutes it. What still waits on a ruling is named at the end and is not started.

## The branch

One branch, `fm/ledger-proofs-third-widening`, cut from `main` after this brief has been merged into it, and pushed. Both slices are built on it, LG-9 first, one commit for each mark and one per part at least, each with the trailers [GENAI_CONTRIBUTION.md](../../../GENAI_CONTRIBUTION.md) requires and a `Placement: T0, substrate proofs` trailer where the guard asks for one. Commit locally and push only when the maintainer says so. The maintainer merges. The branch `fm/ledger-proofs-second-widening` holds nothing beyond an older `main` and is not used.

## What machine S does and does not do

Isabelle work and the checks that go with it. Never a benchmark, none of the `check:ledger-credit-kinds` tasks, `check:ledger-posting-cost`, `check:ledger-late-posting`, `check:ledger-cross-family`, `check:ledger-graph-partition`, `check:sparql-constraint-query-cost` or `check:mork-rdf-run-cost`. Never the `HOL-Library` heap. Never a version bump, a tag, a merge or a push without the maintainer's word. No row moved to `verified`, which is the maintainer's. Take no decision the plan leaves open.

**A statement that will not prove is a result.** Every part below is a hypothesis until it is proved. Where one is false as written, keep the counterexample as a negative instance, record the question in the [ledger plan](../plans/ledger.md) with the next free `LG-Q` number, and say so in the handoff. Never weaken a statement, add a hypothesis or change a definition to make it pass without saying that you did and why, since a law that needed a hypothesis is a different law and the design must hear of it.

## Before the first edit

`mise run bootstrap`, since `main` moves its pins. `mise run work:here -- --role build --model <model>`. Then mark before you touch, the LG-9 row in the [ledger status record](../status/ledger.md) to `building <day>` with a history line, `mise run build:work`, and that commit alone. Mark LG-20 the same way on the day LG-9 is built. One Isabelle build at a time.

What was learned on FME-0 and LG-8 holds. A session's timeout lives in its `ROOT`, and no `-o` is passed on a command line, since it reaches the parent and rebuilds it. Every build runs from `tools/proofs/`, as `mise run check:proofs -- ledger` does, and the prelude is built with `-b` so its heap is saved. A proof by `auto`, `fastforce` or `blast` under a congruence rule can loop to the session's bound, so write the steps out where one does not return at once. The gate's digest covers every definition in the layer, so a new definition redigests every claim record, and only a changed statement is a reviewed restatement.

## What has been decided since the last brief

Read these before the plan's parts, since they are the reasons for them.

| Decision | Date | What it says | Where |
|---|---|---|---|
| LG-Q23, (b) with (d) | 2026-11-13 | a posting keeps the amount offered and the amount applied, and the writer records a cut at each accepting ancestor that had less room, so every ancestor's balance is a sum less its cuts | [balances sketch](../sketches/ledger-balances-under-post-once.md) §4.8, MEC-106, STD-330 |
| LG-Q26 | 2026-11-13 | a reading of a balance by effective day is a derivation a report declares, by the recorded amounts, by settling again in effective order, or as flows, and none is the ledger's | the same sketch §4.9, MEC-107, STD-328, STD-329 |
| STD-278 narrowed, STD-331 | 2026-11-13 | a read of the recorded amounts or the flows for a day may start from the checkpoint before the day, and a checkpoint carries the two flow totals | the standards register |
| LG-Q12, atomicity (a) | 2026-11-13 | an allocation across several accounts commits whole | STD-332, scenario D3 |
| LG-Q13, (a) | 2026-11-13 | an allocated amount honours its purpose, so allocation takes `reach` | STD-333, scenario D2 |
| LG-Q17, (a) | 2026-11-13 | a rule may leave an explicit residual | MEC-109, scenario A1 |
| LG-Q18, (c) | 2026-11-13 | the account declares an order's criterion and each request carries the rank derived from it | MEC-108 |
| LG-Q22, (a) | 2026-11-13 | a definition version pins its scheme edition. Nothing to prove | STD-334 |

The measurements behind LG-Q23 and LG-Q26 are in the packs of [LG-16](../validation/LG-16.md), [LG-17](../validation/LG-17.md) and [LG-18](../validation/LG-18.md). They show the laws holding on generated histories and are no substitute for the proofs.

## The slices

**LG-9, the proofs' second widening.** Home unit `ledger`, row LG-9, brief in the [ledger plan](../plans/ledger.md) under that name, which states each part. Build its seven parts that wait on nothing in the plan's order, then LG-Q16's part, then the two that waited on a question, which the plan now marks decided: LG-Q13, `spread` and `spread_int` debit `reach`, and LG-Q12, an allocation across accounts commits whole or changes nothing.

**LG-20, the proofs' third widening.** Row LG-20, brief in the plan under that name, after LG-9. Its four parts in the plan's order: LU, the cut record, which needs LB1 from LG-9. LE, the two positions and the readings by effective day. LV, a rule lawful with a residual, beside LS's two predicates. LK2, an order derived from ranks, on LK.

Read first, for both: LG-8's [pack](../validation/LG-8.md) with its Results, the [sketch on the residual to the first in order](../sketches/ledger-residual-to-first-in-order.md), the [sketch on balances under post-once](../sketches/ledger-balances-under-post-once.md) §3, §4.8, §4.9 and §5, and the session's README.

Every definition goes in the ledger README's `isabelle-spec` block and reaches `Kernel.thy` by `mise exec -- python tools/literate_extract.py ontology/ledger/README.md --layer ledger --root . --proofs-root tools/proofs`, never by hand. The kernel keeps `imports Complex_Main`. A library theory is imported by the theorem theories alone, and only one the prelude already holds. If a part needs a library theory the prelude lacks, stop and say so, since adding one is a reviewed change to `tools/proofs/base/Prelude.thy`. Examples come first in each theory, as `value` checks that are also lemmas. Each claim is a theorem between `(* GATE:BEGIN <id> *)` and `(* GATE:END *)` with a claim record under `claims/`.

The README changes with both slices, which moves an extracted document, so `mise run check:ontology-versioning -- --base-ref main` will report it unbumped. That report is expected and is not acted on, since versions move at the merge into `main`. Where a part needs a vocabulary term the README does not have, propose it in the README for review and name it in the handoff, as LS does for the two kinds of split.

## What is held back

Not in either slice, because a posting scenario that bears on it has no ruling yet: a tie the criterion does not break (F1), two positions that are the same moment (F2), scaling every request by one ratio (G1 to G3), and whatever E1 and E3 add. Where one has been ruled by the day a part is reached, read its ruling in the [posting scenarios note](../notes/ledger-posting-scenarios.md), say in the handoff what it would add, and do not build it.

## The packs

`docs/developer/validation/LG-9.md` and `docs/developer/validation/LG-20.md`, in the lifecycle skill's form, a row per claim, the parts left out named with what each waits on, and a handoff with every command's output read in full.

## Checks

`mise run check:proofs -- ledger`, `mise run check:proofs` once for every session, `mise run check:formal-freshness`, `mise exec -- python -m pytest tools/test_ledger.py` since the README changes, and `mise run check:ontology-versioning -- --base-ref main`. Two adversarial probes for each slice, a weakened statement the digest catches and a broken definition a theorem catches, each restored and the restore checked.

## At each handoff

The pack's handoff, the status record's history and the row at `built <day>`, `mise run build:roadmap -- --fetch` with the hand-written sections read against the records the work changed, and `mise run graph:ask -- misses --near` reported. End with what the slice left out and why, with each statement that was changed to make it prove and the reason, and with 🔴 RELEASE TAGS REQUIRED if the versioning check lists tags.
