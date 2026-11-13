<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Cloud session brief, 2026-11-13: build and run LG-19

**For:** the agent in a cloud session that takes slice LG-19 of the `ledger` unit, the one that ran LG-18 or another. **Written on** `docs/placement-vehicles-structure` at the maintainer's request. LG-18 was written elsewhere and only run in the cloud. LG-19 is yours whole: you write the change, correct the tests, run every benchmark it touches and record what moved. You decide nothing about the ledger's design.

Read [AGENTS.md](../../../AGENTS.md) first. It governs this work. Where this brief is silent, it holds. The [brief for LG-18](cloud-brief-lg-18-2026-11-12.md) and its [handoff note](lg-18-cloud-run-handoff.md) say how the last run went and what the environment needed.

## The decision you are carrying out

The benchmark's generated streams let a debit through whatever the accounts on its path hold. A contract is stated at a thousand million and never binds, and a sublimit at 100,000, a section at 300,000 and the root at a million do, so by 20,000 postings one section stands at minus 711,618. The ledger's own writers refuse such a debit. The maintainer ruled on 2026-11-13 that correctness comes first and a corpus refuses a debit that would leave an account below zero, as the writers do. Every figure of LG-14 to LG-18 at 20,000 postings was measured on a corpus that overdraws, and LG-18 counted 6 readings below zero with nothing late for that reason alone.

## The branch, and what you hand back

- **Work on one branch of your own**, `ledger/lg-19-cloud-run`, cut from `docs/placement-vehicles-structure` at the commit that holds this brief. If your session has already made a branch from that commit, use it and say its name.
- **Never push to `docs/placement-vehicles-structure` or to `main`, and never merge into either.** No pull request, no tag, no version bump.
- **You have the maintainer's go-ahead to commit and to push to your own branch**, with the hooks on. One commit a piece. Each carries the trailers [GENAI_CONTRIBUTION.md](../../../GENAI_CONTRIBUTION.md) requires, `Generated-by`, `AI-Content` and `Co-Authored-By`, and a `Placement: T0, substrate tooling` trailer.
- **Your final commit adds a handoff note**, `docs/developer/notes/lg-19-cloud-run-handoff.md`, described at the end, and its message says in a few lines what changed and what moved.
- **Your last message names the branch**, its address on GitHub (`https://github.com/nebularis/lattice/tree/<branch>`), and the hash of its last commit. Then stop.

## Mode

Autonomous mode, by the maintainer's word for this slice: run the checks yourself and report their real results. Never say a check passed unless it ran and passed, and read all of what a command printed. Every figure you write comes from a report file or from output you read in full.

## Before the first edit

1. Where `~/.lattice-setup-deferred` exists, wait for it to go. In a thread that runs no hook, start setup with `bash tools/claude-cloud-setup.sh --session`.
2. `mise run bootstrap`, then `mise run bootstrap:sparql-testkit`, which the last run found bootstrap does not build and without which two Jena tests skip. Then `mise run work:here -- --role build --model <model>`.
3. **Mark before you touch.** Set the LG-19 row in the [ledger status record](../status/ledger.md) to `building <day>` with a history line, run `mise run build:work`, and commit that alone.
4. Check that Java 25 and Maven 3.9 answer through mise. If a fetch is refused, load the skill `lattice-constrained-environments` and do not work around it.

## Step one: the baseline, before any change

Run the six tasks on the code as it stands and keep their reports, so every comparison is made on one machine. The generated reports are git-ignored, so copy each to a folder outside the repository as it is written.

```bash
mise run check:ledger-credit-kinds
mise run check:ledger-credit-kinds-writes
mise run check:ledger-credit-kinds-jvm
mise run check:ledger-credit-kinds-jvm-writes
mise run check:ledger-credit-kinds-single-writer
mise run check:ledger-credit-kinds-late-readings
```

Run one at a time, never two benchmarks or two JVMs at once. On the last cloud machine the three of LG-18 took 13, 1 and 11 minutes. The first four were not timed there. A pass is exit 0 with `report written to` and no `WRONG RESULT`.

Also record, for each of the two streams and each size and credit share the benchmark uses, how many debits would be refused under the rule below, which you can count without changing the stream. That table says where the corpus overdraws today, and it is the first thing the handoff note reports.

## Step two: the change

All of it is in `benchmark/ledger-credit-kinds/check.py`, in `stream` and `stream_two_level`. Read both, the model (`run_model`), `settle_debit` and `settle_credit`, and how `writes.Live.prepare` refuses, before you edit.

**The rule.** A debit is refused when its amount is more than the stepwise balance of any account on its path, the contract included, at the moment it is drawn. That is the writers' own test, `any(step[i] < amount for i in chain(at))`. A refused debit is not a posting. It is not in the stream, the store, the model or any count of postings.

**What to keep as it is.**

1. *The random draws.* Draw every value for a refused debit exactly as today and then drop it, so the generator's sequence does not shift. A size and share at which nothing is refused then gives a stream that is the same, posting for posting, as today's. Show this with a test that compares the stream before and after for a size where your step-one table counts no refusal. If no such size exists, say so and say why.
2. *The count.* A stream of `count` postings still has `count` postings, so the generator draws on until it has them. The share of credits among the postings then rises above the share drawn where debits are refused. Report the realised share beside the drawn one, for every size.
3. *Positions.* A pass in which every draw was refused has no posting. Decide whether its position is skipped or the pass is redrawn, keep whichever leaves the period graphs and the closes meaningful, and say which you chose and why. Nothing in the benchmark requires positions without a gap, except the writers' own live revisions, which are not the corpus's.
4. *`stream`.* It tracks only each contract's balance today. It needs the stepwise balance of every account on a path to apply the rule, as `stream_two_level` already has. Use `settle_debit` and `settle_credit` for it and check that the credits' applied amounts are unchanged where nothing is refused.

**What must still hold.** The benchmark refuses a corpus that could not fail its own checks (`check_discriminates`, `check_discriminates_cuts`). With debits refused, balances sit higher and ceilings bind more, so these should still pass, and a corpus on which they do not is a result to report and never a check to loosen. The sketch's four-step tree and the fixed interleavings do not use the streams and should not change.

**A choice to report and not to make silently.** If refusing debits leaves a size with so few debits that the corpus no longer exercises what a benchmark measures, for example no cut at 30% credits, stop that part and say so. Do not change the tree's stated amounts, the seed, the debit and credit sizes or the shares to repair it. Those are the maintainer's to change.

## Step three: tests

- A test that no account's stepwise balance is below zero at any posting of either stream, at each size the tests use and at 20,000 postings once. It must fail on today's generator at 20,000.
- A test that a refused debit leaves no trace: the stream's length, the model's rows and the stored count agree.
- The test of step two's point 1.
- Every existing test, corrected only where it asserted a number that the corpus legitimately changed. Say which numbers changed and from what to what. A test that now passes for a different reason than before is to be read, not assumed.

The counts to expect before your change, with the Jena test kit built: 102 in `test_check.py` and `test_writes.py`, 14 in `test_single_writer.py`, 6 in `test_late_readings.py` and 22 in `benchmark/ledger-credit-kinds-jvm`.

## Step four: the runs, and what moved

Run the six tasks again on the changed corpus, one at a time, and keep the reports beside the baseline's.

Then compare. The question the maintainer wants answered is which published figures moved and whether any conclusion changes. Report it in this order.

1. **Where the corpus changed.** For each stream, size and share: the debits refused, the realised credit share, the stored triples before and after, and whether the stream is identical to the baseline's.
2. **Correctness.** That every benchmark still passes its own criterion on the new corpus, and the impossible readings of `late_readings.py` with nothing late, which should now be none.
3. **The writers.** The debits the live writers refuse at 20,000 postings, which were 187 of 500 in LG-17 because the corpus had already overdrawn the cap, and what they are now.
4. **Each headline figure of LG-14 to LG-18**, before and after on this machine, with the ratio. A ratio within the run-to-run variation you observed is "did not move". For the rest, say what moved and offer the likeliest reason as a hypothesis. The headline figures are the ones each README section and each pack's Handoff states in its "What the figures show" or equivalent passage.
5. **Any conclusion that no longer holds.** If a statement in a README, a pack, or the Status cell of LG-Q23 or LG-Q26 in the [ledger plan](../plans/ledger.md) is contradicted by the new figures, quote it, give the new figure, and stop there. Both questions are decided, and reopening one is the maintainer's.

## Step five: the records

1. **The benchmark's README and the native module's README.** Add a dated passage, "Measured again on corpora that refuse an overdrawing debit (LG-19)", with the tables of step four. Leave the earlier dated results as they are, and add one sentence to each that was measured at 20,000 postings saying it was measured on a corpus that overdraws and where the newer figure is. Results are history and are never rewritten.
2. **A [Validation Pack](../validation/) for LG-19**, `docs/developer/validation/LG-19.md`, in the layout of [LG-18's](../validation/LG-18.md): the invariant, the test cases with a level and whether each is a positive or a negative case, the one command, the artefacts, the deliberate non-coverage, and the Handoff with every command and its real result. Leave Results as "Filled at verification".
3. **The [status record](../status/ledger.md).** A history line, and the LG-19 row to `built <day>, building <day>` once every step has passed. Then `mise run work:normalise -- --apply` and `mise run build:work`.
4. **The roadmap.** `mise run build:roadmap -- --fetch`, and read item 12 of its next steps against what you found.
5. **The plan.** A dated "Measured again" note in the Status cells of LG-Q23 and LG-Q26, figures only.

## What you do not decide

Whether a ledger has one writer or guarded writers, where single-writer is provided for Oxigraph on disk (TD-162), the benchmark's tree, seed, sizes and shares, and anything in the ledger's design. LG-Q23 and LG-Q26 are decided. Your figures either leave them standing or you say exactly what contradicts them.

## The handoff note, in your final commit

`docs/developer/notes/lg-19-cloud-run-handoff.md`, with an SPDX header, holding:

1. **The branch**, the commit it was cut from, and its last commit.
2. **The environment**, the kind of machine and the versions the runs reported, and anything setup skipped.
3. **Where the corpus overdrew before**, the table of step one.
4. **The change**, by function, with the choices of step two's points 2 and 3 and their reasons.
5. **The tests**, added and corrected, with each number that changed.
6. **Every command**, with its real result: the counts, the exit code and the elapsed time, for the baseline and for the changed corpus.
7. **What moved**, in the order of step four.
8. **Findings**, apart from the above: anything a store or the benchmark did that was not expected.
9. **What did not run or was not finished**, and why.
10. **What the index answered weakly**, from `mise run graph:ask -- misses --near`, or that it recorded none.
11. **What the maintainer is asked to decide or check.**

Write it as the team writes: no semicolons, one line a paragraph, a colon only before a list, a table or a quotation.
