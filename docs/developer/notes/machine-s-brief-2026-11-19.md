<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Machine S brief, 2026-11-19: the ledger's rework, LG-11, LG-25 to LG-28 and LG-12

**For:** the agent on machine S. **Written on** `docs/placement-vehicles-structure` at the maintainer's request. It is the ledger half of your next tranche. The multi-store half, the PostgreSQL fixture, MSA-I5a and what follows them, is briefed by the session that reviews the multi-store work. It adds to the briefs of [2026-11-17](machine-s-brief-2026-11-17.md) and [2026-11-18](machine-s-brief-2026-11-18.md), which still hold for asking the index, for committing locally and never pushing, and for keeping a local workaround out of every commit.

## 1. Your branch

The maintainer cuts a new branch for you from `spi/multi-store-architecture`, after this branch is merged into it, and names it. Work on it alone. Every text this brief names is then on your branch, so the brief of 2026-11-18's instruction to read them elsewhere no longer applies.

## 2. What happened to your last work

- **The ledger proofs are verified.** The maintainer verified LG-9 and LG-20 on 2026-11-19, with LG-23, and all three are on `main`.
- **The shared proof session is accepted.** [ADR-A-FM2](../../architecture/decisions/ADR-A-FM2-formal-methods-theory-home.md)'s addendum of 2026-11-18 was accepted that day, so MSA-I5a waits on nothing.
- **Your second bundle is back and not yet reviewed.** Your nine fixes, MSA-I2's rework and the part of MSA-I6 built so far stay off `main` until the maintainer has given a verdict on each.

## 3. What the maintainer decided since the brief of 2026-11-18

Each is recorded in the [ledger plan](../plans/ledger.md)'s questions, and the [sketch](../sketches/ledger-vocabulary-rework.md) says what each means for the vocabulary. No question holds a slice.

| Question | Decision | Built by |
|---|---|---|
| LG-Q38 | one `ldg:Request` node for every request on every merge, `ldg:Grant` retired, a refused merge keeps its requests | LG-26 |
| LG-Q39 | a cut names its posting, and a read by position joins the two | LG-25 |
| LG-Q40 | the account definition is versioned in this rework, which takes on TD-102 | LG-28 |
| LG-Q41 | the residual account is named on the merge policy | LG-26 |
| LG-Q42 | LG-11 first, then LG-25 to LG-28, released together | all five |
| LG-Q43 | a checkpoint is written at a close only for an account that moved | LG-27 |
| LG-Q45 | a pass moves a ledger's revision once | LG-27, unchanged by it |

**A position is a natural number.** LG-25 narrows the two position properties from `xsd:integer` to `xsd:nonNegativeInteger`.

**The checkpoint's addendum is accepted.** [ADR-A131](../../architecture/decisions/ADR-A131-ledger-layer.md)'s addendum of 2026-11-19 defines "moved" for LG-27. An account moved when a posting recorded since its last checkpoint changes its balance, or the debits or the accepted credits offered that the checkpoint holds. That is wider than the README's "whose balance moved", and LG-27 brings the README into line.

## 4. Once a pass, which answers C1 to C3 of your census

Your census found three conditions in `ordered-draws.ttl` that no text stated. C1 has the writer return a revision with each posting. LG-Q37 has each pass record the one revision it moved the ledger to, and the ledger README defines a pass as one evaluation's write of records. The maintainer decided for LG-Q37's reading on 2026-11-19, as LG-Q45.

**The rule.** A pass is evaluated from one revision of a ledger and written as one request, which moves the revision once. The request is refused when the ledger has moved from the revision the pass read, and the pass is then evaluated again.

**What becomes of each condition, inside one ledger.**

| Condition | Under once a pass |
|---|---|
| C1, a later guard names the revision an earlier posting produced | not needed. A later guard sees its pass's own earlier postings in the evaluation, and no other write falls between them |
| C2, the writer's refusal is the guard failing | the writer refuses the whole pass. No transition of it is recorded, and it is evaluated again from the newer revision |
| C3, a replay from receipts for each posting | one fact for each pass. The revision the pass records is its receipt, and a replay finds the pass's write and evaluates from the revision before it |

**The evidence.** An exhaustive model of the example's three transitions, against a credit or a second activation on the same accounts and one crash at any point, from twelve starting states. Once a pass with the refusal gave only outcomes that the passes run one after another give. Without the refusal it did not. With each posting a write of its own, it did not in 7 of 12 states in any variant tried, since a posting returns a revision that includes whatever landed before it. The model is [`tools/models/ledger-pass-revision/`](../../../tools/models/ledger-pass-revision/README.md), and MSA-I6 is asked to check it again in TLA+.

**Two gaps in C1 to C3 as you stated them,** which matter where a pass writes two ledgers and each ledger takes a write of its own.

- **After a refusal.** C2 does not say which revision a later guard reads. The refusal has to return the revision it was refused at.
- **A guard that fails leaves no receipt.** A replay then evaluates it on the latest revision, and can post after a later posting of its own pass. The revision the pass started from has to be recorded.

**What this means for the rework.** LG-27 builds what LG-Q37 decided, one triple for each pass, and adds no term for a posting. Where the rule itself is stated is not decided, and is PDD-22 of the [pending design decisions](../pending-design-decisions.md). Your candidate R6 is PDD-23. Build neither.

## 5. The slices, in one lane

Every slice edits the one ledger README, so the rework has one writer at a time. Run the multi-store half beside it with your second sub-agent.

| Order | Slice | Estimate |
|---|---|---|
| 1 | LG-11, conversion leaves the ledger | 30k |
| 2 | LG-25, postings as decided, the balance record removed | 200k |
| 3 | LG-26, merges as decided | 150k |
| 4 | LG-27, the ledger node, its profile and revision, the checkpoint's two totals | 150k |
| 5 | LG-28, the account definition as a versioned thing | 200k |
| 6 | LG-12, which draws an account accepts | 30k |

- **LG-27 comes before LG-28.** LG-27 moves the closing recurrence off the definition that LG-28 then versions.
- **LG-12 goes last** although it waits only on LG-11, since MSA-I7, MSA-I8 and MSA-I10 wait on the five and not on it.
- **What each slice holds and removes** is the table of the sketch's section 5, and its row in the plan.
- **Mark before you touch.** Set the slice's row on the [ledger's board](../status/ledger.md) to `building` and the day, run `mise run build:work`, and commit the mark alone.

## 6. Rules the rework has to keep

- **The README is the source.** Edit `ontology/ledger/README.md`, extract, and never edit a generated file.
- **No version moves on your branch.** Write each change under the README's `- **Unreleased**.` release note, each sub-bullet opening with its class. The five are released together at the merge into `main`, which is the maintainer's.
- **A README states what is.** It carries no account of an earlier or mistaken state, names a decision only in its Design decisions section and its release notes, and names no slice, question or debt.
- **A rule a slice writes into ADR-A131 is an addendum drafted as Proposed.** LG-26 owes one for the request. An addendum that narrows a numbered decision opens with a bold lead naming it.
- **A removed test names its decision.** The rework removes the balance record, the grant and the conversion terms, with their shapes and tests. For each test removed or loosened, the pack names the question or addendum that decided it.
- **The proofs follow the kernel.** A change to the README's formal blocks regenerates the ledger's kernel, so each slice runs `mise run check:proofs` and reads the build's own lines. Say in the pack what became of each claim that named a removed term.
- **MSA-I5a touches the ledger's proof session too,** for its agreement lemma. Land that lemma before LG-25 starts or after the slice in hand has its proofs green, never beside it.

## 7. What you do not do

- Behaviour's migration (LG-3) and allocation (LG-4), which follow the rework and are not briefed.
- A revision on a posting, a receipt for each posting, or any term for PDD-22 or PDD-23.
- Mark a decision record Accepted, or a row `verified`.

## 8. What you hand back

For each slice, its Validation Pack with the one command and its results, its board row at `built`, and the index report. One bundle when the rework closes, as the multi-store half's brief arranges for the rest.
