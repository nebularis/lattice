<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Cloud session brief, 2026-11-15: build and run LG-22

**For:** the agent in a cloud session that takes slice LG-22 of the `ledger` unit, the one that ran LG-18 and LG-19 or another. **Written on** `docs/placement-vehicles-structure` at the maintainer's request, after LG-19's branch was read and merged. LG-22 is yours whole: you write the changes, add the tests, run what they touch and record what you find. You decide nothing about the ledger's design.

Read [AGENTS.md](../../../AGENTS.md) first. It governs this work. Where this brief is silent, it holds. The [brief for LG-19](cloud-brief-lg-19-2026-11-13.md) and its [handoff note](lg-19-cloud-run-handoff.md) say how the last run went. This slice answers the four things that note asked the maintainer and the two results it left unexplained.

## What the maintainer decided on LG-19's questions

| LG-19 asked | Decided, 2026-11-15 | Your part |
|---|---|---|
| whether 5% credits at 5,000 and 20,000 postings is still the stream to measure, since the realised share is 14% and 26% | the rows are kept and labelled by what they hold. A corpus wide enough to hold a low share at size is a slice of its own if it is wanted, and is not this one | part one |
| whether the request lists of the writes should be drawn against the state of the store | yes. A list continues the preload's own stream, so one writer refuses none, and a refused request is measured on its own | part two |
| whether a pass in which every draw was refused is drawn again or skipped | drawn again, as you chose. It is the generator's draw and nothing the ledger does | nothing to change |
| what becomes of the statements in the READMEs that no longer hold | the dated results stay as history, and a short table of current figures goes at the top | part four |

## The branch, and what you hand back

- **Work on one branch of your own**, `ledger/lg-22-cloud-run`, cut from `docs/placement-vehicles-structure` at the commit that holds this brief. If your session has already made a branch from that commit, use it and say its name.
- **Never push to `docs/placement-vehicles-structure` or to `main`, and never merge into either.** No pull request, no tag, no version bump.
- **You have the maintainer's go-ahead to commit and to push to your own branch**, with the hooks on. One commit a piece. Each carries the trailers [GENAI_CONTRIBUTION.md](../../../GENAI_CONTRIBUTION.md) requires, `Generated-by`, `AI-Content` and `Co-Authored-By`, and a `Placement: T0, substrate tooling` trailer.
- **Your final commit adds a handoff note**, `docs/developer/notes/lg-22-cloud-run-handoff.md`, described at the end, and its message says in a few lines what changed and what you found.
- **Your last message names the branch**, its address on GitHub (`https://github.com/nebularis/lattice/tree/<branch>`), and the hash of its last commit. Then stop.

## Mode

Autonomous mode, by the maintainer's word for this slice: run the checks yourself and report their real results. Never say a check passed unless it ran and passed, and read all of what a command printed. Every figure you write comes from a report file or from output you read in full.

## Before the first edit

1. Where `~/.lattice-setup-deferred` exists, wait for it to go. In a thread that runs no hook, start setup with `bash tools/claude-cloud-setup.sh --session`.
2. `mise run bootstrap`, then `mise run bootstrap:sparql-testkit`. Then `mise run work:here -- --role build --model <model>`.
3. **Mark before you touch.** Set the LG-22 row in the [ledger status record](../status/ledger.md) to `building <day>` with a history line, run `mise run build:work`, and commit that alone.
4. Check that Java 25 and Maven 3.9 answer through mise. If a fetch is refused, load the skill `lattice-constrained-environments` and do not work around it.

Run one benchmark at a time, never two benchmarks or two JVMs at once. Copy each generated report to a folder outside the repository as it is written, since they are git-ignored.

## Step one: the baseline, and the variation measured directly

LG-19 took its run-to-run variation from cells whose inputs did not change, which left the bounds wide. Measure it this time. Before any change, run the three tasks that use request lists twice each, and keep both reports of each.

```bash
mise run check:ledger-credit-kinds-writes
mise run check:ledger-credit-kinds-jvm-writes
mise run check:ledger-credit-kinds-single-writer
```

On the last cloud machine they took about 11, 9 and 12 minutes. The spread between the two runs of each figure is the variation you compare against in step four. A pass is exit 0 with `report written to` and no `WRONG RESULT`.

## Part one: a row says what it holds

Every table and report line that names a credit share today names the share drawn. Where debits are refused the stream holds more credits than were drawn, so the label misleads.

- In every report the benchmark writes, and every table added to a README from now on, a corpus is named by the share drawn and the share realised, for example "drawn 5%, holds 26.3%". Where the two agree to a tenth of a percent, the one figure is enough.
- Beside it, give what else changed with the refusals: the passes, the period graphs and the postings a period, since a period is counted in passes and a period of the 5% corpus at 20,000 postings holds 247 postings where it held 392. Any figure taken per period or per checkpoint is not comparable with a run before LG-19, and the report says so once.
- Change no seed, share, size, tree or period length.

## Part two: request lists that know the store

**What is wrong.** `writes.requests(count, share, seed)` draws a fresh stream from a full tree and discards its settlement. The lists are then sent to a store that holds a preload of up to 20,000 postings, whose accounts are low, so the live writers refuse 138 of 500 at 20,000 postings for lack of availability. A refused request costs its reads and writes nothing, so the written sample is smaller than it looks and the concurrent runs have fewer commits competing.

**The rule.** A request list for a store preloaded with `n` postings continues the preload's own stream: sent one after another by one writer, in list order, no request in it is refused. Read every caller before you choose how, in `writes.py`, `single_writer.py`, their tests, and the plan `store_plan` hands the native module, which carries the lists to `LedgerWrites.java`. The smallest change that gives every caller the rule is the one wanted. Lists must still differ by seed where a caller needs several, for example one a thread.

**What follows from it.**

1. *One writer.* A test, on each store the tests use, that a single writer sent a list in order against its preload refuses none. It must fail on today's `requests` at 20,000 postings.
2. *Several writers.* Each thread's list was valid in one order, and threads interleave, so a writer may still refuse a debit that another's commit left no room for. That is a real refusal and is counted and reported, by threads, beside the lost races. Do not suppress it.
3. *A refusal measured on its own.* Add one row to the write tables: the cost of a request the writer refuses, its path reads with no write, on a small list built to be refused, for example debits larger than the least account on their path holds. Say how many requests the row averages.
4. *The audits.* Every audit that compares a run with its replay stays as strict as it is.

Report the written debits and credits of each run before and after, so the sample sizes are known.

## Part three: the two results LG-19 left unexplained

Each is a probe. Neither changes a default, and each is run on demand from the benchmark's own module, with a test that it runs at a small size.

**rdflib's root read at 5% credits, 1.5 times slower.** Counted from the two generators on 2026-11-15 with nothing timed, the 5% corpus at 20,000 postings has 486 period graphs where it had 306, which is 1.59 times, and the 30% corpus 360 where it had 300, where no slowdown showed beyond the variation. The hypothesis is that rdflib's read grows with the number of named graphs it visits and not only with the rows it folds. Test it:

- On the one-level corpus at 20,000 postings and 5% drawn, time the plain root read from the start of history on rdflib with the period length at 100, 200, 320 and 640 passes, the postings identical in every case, each read repeated at least 5 times, the median and the spread reported.
- Report, for each length, the period graphs, the rows folded and the time. Run the same on Oxigraph as a control.
- Say what the figures show. If the time follows the graphs with the rows fixed, the hypothesis stands, and it bears on how long a period should be on rdflib. If it does not, say so and leave the cause open. A period length is passed to the probe and the module's `EVERY_POSITIONS` is not changed.

**Jena through the kit, the sum less the cuts at 1.85 times the kind-filtered read.** It was a few single reads of milliseconds, read once. Repeat each of the two reads 30 times after 5 warm-up reads, at 20,000 postings and 5% drawn, from the start of history and from a checkpoint, and report the median, the least and the greatest of each and the ratio of the medians. If the ratio holds above the 1.01 to 1.14 measured before LG-19, offer the likeliest cause as a hypothesis, for example more cuts a posting, and give the count of cuts in both corpora.

## Part four: the READMEs, and three things to read

1. **Current figures.** At the top of the benchmark's README, under its introduction, add a short section "Current figures", one table of the headline figures as they stand after this run, each with the dated section it comes from. The dated results below stay as they are. Do the same in the native module's README. Add a dated passage for this run in each, in the form of LG-19's.
2. **Reading B's impossible readings.** LG-19 found reading B, the postings settled again in effective order, impossible at 4 and 3 of 81 readings with 5% and 20% of postings late, where the earlier run found none of its own. Find the smallest case: one account, one reading, the postings that produce it in recorded order and in effective order. Report it in the handoff note. The hypothesis to confirm or refute is that a debit the writer accepted in recorded order overdraws when the same postings are settled in effective order. Change nothing in `late_readings.py` to remove it.
3. **The tests LG-19 did not read.** Its handoff says the tests that depend on what the corpus holds were read only by their passing: the discrimination checks, the write benchmark's late postings, and `test_lr5`. Read each, and say for each whether it still tests what its name claims on the new corpus, or passes for another reason. A test that can no longer fail is a finding, and is repaired only where the repair is to the test and not to what it claims.
4. **Test names.** LG-19's first new tests took the names of six that exist, and Python dropped the six without a word. Before you add a test, check its name is free, and after you add them check the collected count is the old count plus the new.

## Step four: the runs, and what to report

Run the six tasks once on the changed code, one at a time.

```bash
mise run check:ledger-credit-kinds
mise run check:ledger-credit-kinds-writes
mise run check:ledger-credit-kinds-jvm
mise run check:ledger-credit-kinds-jvm-writes
mise run check:ledger-credit-kinds-single-writer
mise run check:ledger-credit-kinds-late-readings
```

The first took about 106 minutes on the last cloud machine. Then report, in this order.

1. **The variation**, from step one's two runs, for each kind of figure.
2. **The request lists.** For each run, the refusals before and after, the written debits and credits, and the cost of a refused request.
3. **The writers' figures that moved** beyond the variation, before and after, with the ratio: a write's cost by kind, the guarded writers' commits a second and retries by threads, the one writer's rates, and the batches. Offer the likeliest reason for each as a hypothesis.
4. **The two probes**, with their tables and what each shows.
5. **Reading B's smallest case.**
6. **The three tests read.**
7. **Any conclusion that no longer holds.** If a statement in a README, a pack, or the Status cell of LG-Q23 or LG-Q26 in the [ledger plan](../plans/ledger.md) is contradicted, quote it, give the new figure and stop there. Both questions are decided, and reopening one is the maintainer's.

## Step five: the records

1. **The two READMEs**, as part four says.
2. **A [Validation Pack](../validation/) for LG-22**, `docs/developer/validation/LG-22.md`, in the layout of [LG-19's](../validation/LG-19.md). Leave Results as "Filled at verification".
3. **The [status record](../status/ledger.md).** A history line, and the LG-22 row to `built <day>, building <day>` once every step has passed. Then `mise run work:normalise -- --apply` and `mise run build:work`.
4. **The roadmap.** `mise run build:roadmap -- --fetch`, and read item 12 of its next steps against what you found.
5. **The plan.** A dated "Measured again" note in the Status cells of LG-Q23 and LG-Q26 only where a figure they quote moved, figures only.

## What you do not decide, and what is not in this slice

Whether a ledger has one writer or guarded writers, where single-writer is provided for Oxigraph on disk (TD-162), how long a period is, the benchmark's tree, seed, sizes and shares, and anything in the ledger's design. A corpus wide enough to hold a low credit share at 20,000 postings is not built here. Nor is the space a refusal's own record takes, which the corpus does not model, since a refused debit leaves no trace in it. Say in the handoff what each would need if you see it.

## The handoff note, in your final commit

`docs/developer/notes/lg-22-cloud-run-handoff.md`, with an SPDX header, holding:

1. **The branch**, the commit it was cut from, and its last commit.
2. **The environment**, the kind of machine and the versions the runs reported, and anything setup skipped.
3. **The changes**, by function, with each choice you made and its reason.
4. **The tests**, added and corrected, with the collected counts before and after and each number that changed.
5. **Every command**, with its real result: the counts, the exit code and the elapsed time.
6. **What you found**, in the order of step four.
7. **Findings apart from the above**, anything a store or the benchmark did that was not expected.
8. **What did not run or was not finished**, and why.
9. **What the index answered weakly**, from `mise run graph:ask -- misses --near`, or that it recorded none.
10. **What the maintainer is asked to decide or check.**

Write it as the team writes: no semicolons, one line a paragraph, a colon only before a list, a table or a quotation.
