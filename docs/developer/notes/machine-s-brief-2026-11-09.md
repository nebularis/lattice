<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Machine S brief, 2026-11-09: the ledger proofs' second widening

**For:** the agent on machine S, Windows 11, Isabelle2025-2 through its bundled Cygwin, where LG-7, LG-2, FME-0 and LG-8 were built. **Written on** `docs/placement-vehicles-structure` at the maintainer's request, after FME-0 and LG-8 reached `main` and were reviewed. It replaces the [brief of 2026-11-08](machine-s-brief-2026-11-08.md), whose two slices are built.

## The branch

One branch, `fm/ledger-proofs-second-widening`, cut from `main` after this brief was merged into it, and pushed. The whole slice is built on it, one commit for the mark and one per part at least, each with the trailers [GENAI_CONTRIBUTION.md](../../../GENAI_CONTRIBUTION.md) requires and a `Placement: T0, substrate proofs` trailer where the guard asks for one. Commit locally and push only when the maintainer says so. The maintainer merges.

## What machine S does and does not do

Isabelle work and the checks that go with it. Never a benchmark, none of `check:ledger-posting-cost`, `check:ledger-late-posting`, `check:ledger-cross-family`, `check:ledger-graph-partition`, `check:sparql-constraint-query-cost` or `check:mork-rdf-run-cost`. Never the `HOL-Library` heap. Never a version bump, a tag, a merge or a push without the maintainer's word. No row moved to `verified`, which is the maintainer's. Take no decision the plan leaves open. Where a part of this slice waits on a question, read the question's row in the [ledger plan](../plans/ledger.md) on the day the part is reached, build what a decided row decided, leave an open one out, and say which in the handoff.

## Before the first edit

`mise run bootstrap`, since `main` moves its pins. `mise run work:here -- --role build --model <model>`. Then mark before you touch, the LG-9 row in the [ledger status record](../status/ledger.md) to `building <day>` with a history line, `mise run build:work`, and that commit alone. One Isabelle build at a time.

Three things learned on FME-0 and LG-8, which hold here. A session's timeout lives in its `ROOT`, and no `-o` is passed on a command line, since it reaches the parent and rebuilds it. Every build runs from `tools/proofs/`, as `mise run check:proofs -- ledger` does, and the prelude is built with `-b` so its heap is saved, which `tools/proofs/check.py` now does. A proof by `auto`, `fastforce` or `blast` under a congruence rule can loop to the session's 90 second bound, so write the steps out where one does not return at once. The gate's digest covers every definition in the layer, so a new definition in the kernel or a theory redigests every claim record, and only a changed statement is a reviewed restatement.

## The slice, LG-9

Home unit `ledger`, row LG-9, brief in the [ledger plan](../plans/ledger.md) under "LG-9, the proofs' second widening", which states each part. Read first: LG-8's [pack](../validation/LG-8.md) with its Results, the [sketch on the residual to the first in order](../sketches/ledger-residual-to-first-in-order.md), the [sketch on balances under post-once](../sketches/ledger-balances-under-post-once.md) §3 and §5, and the session's README.

Every definition goes in the ledger README's `isabelle-spec` block and reaches `Kernel.thy` by `mise exec -- python tools/literate_extract.py ontology/ledger/README.md --layer ledger --root . --proofs-root tools/proofs`, never by hand. The kernel keeps `imports Complex_Main`. A library theory is imported by the theorem theories alone, and only one the prelude already holds. If a part needs a library theory the prelude lacks, stop and say so, since adding one is a reviewed change to `tools/proofs/base/Prelude.thy`. Examples come first in each theory, as `value` checks that are also lemmas. Each claim is a theorem between `(* GATE:BEGIN <id> *)` and `(* GATE:END *)` with a claim record under `claims/`.

**The parts that wait on nothing, in this order.**

1. **LK, the order as a declared input.** First, since every later part uses it. No rule orders proposals by their keys (TD-161).
2. **LR2 over multisets**, restated over the declared order.
3. **LX1, an executable path.** After it, the examples of every later part can be evaluated.
4. **LB1, LB1n and LB2, the running balance.** The law LG-2's rework will cite, now that LG-Q9 is decided (a), a running balance on the posting at the drawn account.
5. **LM2, a merge at one position over whole units**, with `largest_remainder`.
6. **LM1, a merge that refuses**, as LG-Q11 decided on 2026-11-09: an explicit result, grants or a refusal with its reason, the refusal a guard by the declared `ldg:Refuse` policy before any rule, never zero grants. LM2's merge returns the same result, so build LM1 first or restate LM2 with it.

**The parts that wait on a question, in this order.** LG-Q15, then LG-Q16, then LG-Q13, then LG-Q12, each as the plan's brief states it. Under LG-Q15 (b) the vocabulary table's definition of `ldg:ToFirstInOrder` in the README's section 6 changes too, which moves an extracted document, so `mise run check:ontology-versioning -- --base-ref main` will report it unbumped. That report is expected and is not acted on, since versions move at the merge into `main`.

**The pack.** `docs/developer/validation/LG-9.md`, in the lifecycle skill's form, a row per claim, the parts left out named with the question each waits on, and a handoff with every command's output read in full.

**Checks.** `mise run check:proofs -- ledger`, `mise run check:proofs` once for every session, `mise run check:formal-freshness`, `mise exec -- python -m pytest tools/test_ledger.py` since the README changes, and `mise run check:ontology-versioning -- --base-ref main`. Two adversarial probes as before, a weakened statement the digest catches and a broken definition a theorem catches, each restored and the restore checked.

## At each handoff

The pack's handoff, the status record's history and the row at `built <day>`, `mise run build:roadmap -- --fetch` with the hand-written sections read against the records the work changed, and `mise run graph:ask -- misses --near` reported. End with what the slice left out and why, and with 🔴 RELEASE TAGS REQUIRED if the versioning check lists tags.
