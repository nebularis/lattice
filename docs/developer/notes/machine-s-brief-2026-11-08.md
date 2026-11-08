<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Machine S brief, 2026-11-08: the prelude session, then the widened ledger proofs

**For:** the agent on machine S, Windows 11, Isabelle2025-2 through its bundled Cygwin, where LG-7 and LG-2 were built. **Written on** `docs/placement-vehicles-structure` at the maintainer's request, after machine S's `vyvid-migration` work reached `main` at 05c6ac7b.

## The branch

One branch, `fm/prelude-and-ledger-proofs`, cut from `main` at 04eb11d1 on 2026-11-08, after `docs/placement-vehicles-structure` was squash-merged into it, and pushed, so the briefs this note points at, the survey and the ADR-A-FM2 addendum are on it. Both slices below are built on it, in order, one commit per mark and one per slice at least, each with the trailers [GENAI_CONTRIBUTION.md](../../../GENAI_CONTRIBUTION.md) requires and a `Placement: T0, substrate proofs` trailer where the guard asks for one. Commit locally as LG-7 and LG-2 were, and push only when the maintainer says so. The maintainer merges.

## What machine S does and does not do

Isabelle work, yes. The ledger session built there in four seconds, and nothing below needs more than the prelude's first build, a few minutes from source. Never build the `HOL-Library` heap. The prelude loads the theories it imports from source through its `sessions` clause, and the first `mise run check:proofs` builds its heap on its own (STD-324). Never run a benchmark, none of `check:ledger-posting-cost`, `check:ledger-late-posting`, `check:ledger-cross-family`, `check:ledger-graph-partition`, `check:sparql-constraint-query-cost` or `check:mork-rdf-run-cost`, which the maintainer has ruled out on that machine. Never bump a version, create a tag, merge or push without the maintainer's word. Take no decision the plans leave open, LG-Q9 to LG-Q13, the `HOLCF` question, or any reshaping of the sessions beyond ADR-A-FM2's addendum of 2026-11-08.

## Before the first edit

Run `mise run bootstrap`, since `main` now pins Вивід at v0.2.24 and the ledger's tests import a new test-support package, `tools/testing/ledger_corpus`. Where the hooks say `vyd trust` is needed, run it in the checkout. Run `mise run work:here -- --role build --model <model>`. Then mark before you touch (skill `lattice-lifecycle`), the slice's row to `building <day>` with a history line, `mise run build:work`, and that commit alone. LG-2's mark was committed after its first edits, and the pack recorded the lapse. Do not repeat it. One Isabelle build at a time.

## Slice 1, FME-0, the prelude session

Home unit `formal-methods-track-e`, row FME-0 in [its status record](../status/formal-methods-track-e.md), brief in [its plan](../plans/formal-methods-track-e.md) §3, decided by ADR-A-FM2's addendum of 2026-11-08 and FM-D18. Read the [HOL sessions survey](../sketches/hol-sessions-survey.md) §7 and §8 first, which name the nineteen theories and why each is there.

Deliverables. `tools/proofs/base/ROOT` declaring `session LatticeBase = HOL +` with `sessions "HOL-Library"`, `document = false` and `quick_and_dirty = false`, and one theory, `Prelude.thy`, importing the nineteen theories of the survey's §7 table and nothing else, with no law, no claim and no gate marker. A `README.md` in the session's directory saying what it is for and pointing at the survey for why each import is there. `tools/proofs/check.py` building `LatticeBase` before any layer's session and passing `-d tools/proofs/base` to every build, with the gate reporting a session that holds no claim as nothing to gate rather than failing it. The two existing sessions re-parented, `session Eligibility = LatticeBase +` and `session Ledger = LatticeBase +`, with every theorem they hold still proved and every claim still gated. No layer README changes, since the kernels keep `imports Main` or `imports Complex_Main`. A Validation Pack, `docs/developer/validation/FME-0.md`, in the lifecycle skill's form, whose handoff records the prelude's first build time on machine S, read in full from `isabelle build`'s output, and the second run skipping it.

Checks. `mise run check:proofs`, every session, exit 0 and `GATE: pass` for each gated session. `mise run check:formal-freshness`, silent. One adversarial probe, recorded in the pack and the status record: drop `-d tools/proofs/base` from one build and show the layer session fails to find its parent, then restore it.

## Slice 2, LG-8, the proofs widened on HOL-Library

Home unit `ledger`, row LG-8 in [its status record](../status/ledger.md), brief in [its plan](../plans/ledger.md) under "LG-8, the proofs widened on HOL-Library", sized claim by claim in the [sketch on balances under post-once](../sketches/ledger-balances-under-post-once.md) §6. Read LG-7's [Validation Pack](../validation/LG-7.md), whose deviations are what this slice closes, and the session README's what-is-assumed and what-is-not-covered sections, which move with the claims.

Deliverables, each a theorem between `(* GATE:BEGIN <id> *)` and `(* GATE:END *)` with a claim record under `claims/`. LO1 restated over `HOL-Library.Multiset` as `mset ps = mset ps'`, a reviewed restatement whose claim record moves with it. LR3, `ldg:LargestRemainder` sums exactly to the total and is a function of its inputs alone, the keys chosen by `take r` of `sort_key` over the remainders, ties by key order. LR4, the two integer rules lawful in the integer sense. LR5, the refinement beyond one part, every rounded part within one unit of the exact share and the rounded fold conserving exactly, which needs an integer `spread` stated in the ledger README's `isabelle-spec` block and extracted to `Kernel.thy` with `mise exec -- python tools/literate_extract.py ontology/ledger/README.md --layer ledger --root . --proofs-root tools/proofs`, never written into `Kernel.thy` by hand. LC3 for every step, replacing its second conclusion as a reviewed restatement. LM1 only if LG-Q11 is decided by then, otherwise left out and said so in the handoff. The kernel keeps `imports Complex_Main`, and a library theory is imported by `Allocation.thy`, `Draws.thy` and `Rounding.thy` alone. A Validation Pack, `docs/developer/validation/LG-8.md`, with a row per claim.

Checks. `mise run check:proofs -- ledger`, `mise run check:formal-freshness`, and `mise run check:ontology-versioning -- --base-ref main`, whose UNBUMPED report on the ledger README is expected and is not acted on, since versions move at the merge into `main` (BL-18). Two adversarial probes as LG-7 did, one a weakened statement caught by the digest, one a broken definition caught by a theorem.

## At each handoff

The pack's handoff with every command's output read in full, the status record's history and the slice's row at `built <day>`, `mise run build:roadmap -- --fetch` with the hand-written sections read against the records the work changed, and `mise run graph:ask -- misses --near` reported. End with 🔴 RELEASE TAGS REQUIRED if the versioning check lists tags, and with what machine R should pick up next.
