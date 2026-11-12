<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Cloud session brief, 2026-11-12: run and correct LG-18

**For:** the agent in a cloud session that picks up slice LG-18 of the `ledger` unit. **Written on** `docs/placement-vehicles-structure` at the maintainer's request. LG-18 was written on a laptop that was busy, so none of it has run. Only a syntax check of its Python passed, and its Java has never been compiled. Your job is to run it, correct what is wrong with the benchmark, record what it measures, and hand back a branch. You decide nothing about the design.

Read [AGENTS.md](../../../AGENTS.md) first. It governs this work. Where this brief is silent, it holds.

## The branch, and what you hand back

- **Work on one branch of your own**, `ledger/lg-18-cloud-run`, cut from `docs/placement-vehicles-structure` at the commit that holds this brief. If your session has already made a branch from that commit, use it and say its name.
- **Never push to `docs/placement-vehicles-structure` or to `main`, and never merge into either.** No pull request, no tag, no version bump.
- **You have the maintainer's go-ahead to commit and to push to your own branch**, with the hooks on. One commit a piece: a fix with the test that shows it, the results, the records. Each commit carries the trailers [GENAI_CONTRIBUTION.md](../../../GENAI_CONTRIBUTION.md) requires, `Generated-by`, `AI-Content` and `Co-Authored-By`, and a `Placement: T0, substrate tooling` trailer.
- **Your final commit adds a handoff note**, `docs/developer/notes/lg-18-cloud-run-handoff.md`, described at the end of this brief, and its message says in a few lines what ran and what did not.
- **Your last message names the branch**, its address on GitHub (`https://github.com/nebularis/lattice/tree/<branch>`), and the hash of its last commit. Then stop. The maintainer reads the branch and decides what reaches `docs/placement-vehicles-structure`.

## Mode

Autonomous mode, by the maintainer's word for this slice: run the checks yourself and report their real results. Everything else in the contract stands. Never say a check passed unless it ran and passed, and read all of what a command printed. Every figure you write comes from a report file or from output you read in full.

## Before the first edit

1. Where `~/.lattice-setup-deferred` exists, setup is still installing in the background. Wait for it to go before any test. In a thread that runs no hook, start it with `bash tools/claude-cloud-setup.sh --session`.
2. `mise run bootstrap`, then `mise run work:here -- --role build --model <model>`. Where it lists another live session building here, say so in your handoff and carry on only on your own branch.
3. The slice is already marked. The LG-18 row in the [ledger status record](../status/ledger.md) says `building 2026-11-12`. Leave it until the slice has run.
4. Check that Java 25 and Maven 3.9 answer through mise (`mise exec -- java -version`, `mise exec -- mvn -version`). The native run fetches Apache Jena 5.1.0 from Maven Central on first use. If a fetch is refused by the environment, load the skill `lattice-constrained-environments`, do not work around it, run everything that does not need Java, and say so in the handoff.
5. Where `vyd` is missing or says it did not run, each task says what it skipped. Report that and carry on.

## What LG-18 is

Read the [Validation Pack](../validation/LG-18.md) in full, then the benchmark's [README](../../../benchmark/ledger-credit-kinds/README.md) section "One writer per ledger, and the readings of a late posting", then the module docstrings. LG-17's [pack](../validation/LG-17.md) says what the modules it builds on do.

| Part | Files | What it measures |
|---|---|---|
| one, a single writer per ledger | `benchmark/ledger-credit-kinds/single_writer.py`, `test_single_writer.py`, and the keeper and the queue in `benchmark/ledger-credit-kinds-jvm/src/main/java/org/nebularis/lattice/benchmark/creditkinds/LedgerWrites.java` | producers hand requests to one writer through a queue. The writer reads its path for every posting, or keeps the balances it has settled, or also writes several postings in one update. Run beside LG-17's guarded writers on the same stores and request lists |
| two, the readings of a late posting | `benchmark/ledger-credit-kinds/late_readings.py`, `test_late_readings.py` | a balance for a day as known at a recording, by the recorded amounts (A), by settling again in effective order (B), and as flows with no balance (C), for LG-Q26 |
| changed for both | `benchmark/ledger-credit-kinds/writes.py` | `Live.text` is split into `lines` and `text`, `store_plan` gains the queue's sizes, and `audit_jvm` and `render_jvm` handle the queue runs |

A benchmark here fails on a wrong result and never on time, runs on demand, and is never part of `check` (ADR-A124).

## The work, in this order

Run one thing at a time. Never two benchmarks or two JVMs at once, since they disturb each other's timings.

| Step | Command, from the repository root | A pass |
|---|---|---|
| 1 | `mise exec -- python -m pytest benchmark/ledger-credit-kinds/test_writes.py benchmark/ledger-credit-kinds/test_check.py -q -p no:cacheprovider -W ignore` | 102 passed. This shows the change to `writes.py` broke nothing of LG-17's |
| 2 | `mise exec -- python -m pytest benchmark/ledger-credit-kinds/test_single_writer.py -q -p no:cacheprovider -W ignore` | 14 passed |
| 3 | `mise exec -- python -m pytest benchmark/ledger-credit-kinds/test_late_readings.py -q -p no:cacheprovider -W ignore` | 6 passed |
| 4 | `mise exec -- python -m pytest benchmark/ledger-credit-kinds-jvm -q -p no:cacheprovider -W ignore` | 22 passed. This compiles the Java for the first time, and `test_jw5` now runs the queue on both Jena stores |
| 5 | `LEDGER_WRITES_QUICK=1 mise run check:ledger-credit-kinds-single-writer` | the tests pass, a line for each run, `report written to`, exit 0 |
| 6 | `LEDGER_WRITES_QUICK=1 mise run check:ledger-credit-kinds-late-readings` | the tests pass, `readings 5000 late 0%`, `5%` and `20%`, `report written to`, exit 0 |
| 7 | `LEDGER_WRITES_QUICK=1 mise run check:ledger-credit-kinds-jvm-writes` | the tests pass, every `queue-` export is audited, `report written to`, exit 0 |
| 8 | steps 5, 6 and 7 again without `LEDGER_WRITES_QUICK` | the same. These three runs are the slice's figures |

On the laptop LG-17's native task took about 16 minutes before the queue was added, and its Python writes task about 7. Expect step 8 to take longer than that. Run a long command in the background and wait for it.

`WRONG RESULT` on standard error with a non-zero exit is the benchmark's own pass criterion failing. Its message names the store, the account and the read.

## Where a first run is most likely to fail, and what to do

| Likely failure | What it probably is | What to do |
|---|---|---|
| the Java does not compile | a mistake in code that was never compiled, in `Keeper`, `Ask`, `asked` or `queue`, or in the lines added to `main` | fix the Java. Do not change what a run measures to make it compile |
| `test_sw4` does not raise | the second seeded request is a debit that the keeper refuses, so nothing is written and no race is lost | pick requests that are written, for example by taking the first credit of a longer seeded list. Keep the test's claim, that a second writer is caught |
| `test_lr5` does not raise | at 1,000 postings no ancestor's reading B depends on the order of settling | raise the corpus or the late share until it does, and say which in the handoff. A test that cannot fail is not kept as it is |
| reading A from the close differs from reading A from the start | either a mistake in `late_readings.start` or `scan`, or a checkpoint whose balance is not the sum with cuts at its close | find which. The first is a bug to fix. The second is a finding about LG-16's checkpoints: stop that part, report it with the smallest case, and do not adjust the benchmark to hide it |
| the early store reads differently from the whole store | a read that forgets the recording, or a mistake in `late_readings.load` | the same rule. A bug in the benchmark is fixed, a real difference is reported |
| the test kit's Jena fails when called from the writer's thread | the kit may accept calls only from the thread that made it | make the kit's backend in the thread that uses it, or leave Jena out of the Python queue runs and say so. The native run covers Jena |
| a single writer's run on Oxigraph on disk does not equal its replay | this would contradict TSD-73's account, that the on-disk store loses writes only when updates overlap | do not loosen the audit. Report it with the run's numbers, since it bears on TD-162 |

**The rule for every fix.** A defect in the benchmark's own code or tests is yours to fix, with the smallest change, and each fix is named in the handoff note with its reason. A result that says something about the ledger's design or about a store is a finding. Never make a check pass by weakening its pass criterion, widening a tolerance, skipping a store or deleting a negative test. Where you cannot tell a bug from a finding, stop that part, say what you saw, and carry on with the parts that do not depend on it.

## What to record when it has run

1. **The benchmark's README.** In the section "One writer per ledger, and the readings of a late posting", replace "not yet run" with a "Measured results" passage for each part: the date, the kind of machine (cores, memory, operating system, never a host name), the engine versions the reports name, the tables that carry the result, and a short reading of them. Say plainly where a figure contradicts the expectation the README states. The cloud machine is not the laptop, so compare a writer only with the guarded writers of the same run.
2. **The native module's README**, the row for the one writer per ledger, the same way.
3. **The [Validation Pack](../validation/LG-18.md).** Under Handoff, add what was run: each command, its real result with the test counts and the elapsed time, each fix, and what was not run. Leave Results as "Filled at verification", which is the maintainer's.
4. **The [status record](../status/ledger.md).** A history line with the day, and the LG-18 row to `built <day>, building 2026-11-12` once every step has passed. If a step did not pass, leave the row at building and say why in the line. Then `mise run work:normalise -- --apply` and `mise run build:work`.
5. **The roadmap.** `mise run build:roadmap -- --fetch`, and read item 12 of its next steps against what you found.
6. **The plan's questions.** Add LG-18's figures to the Status cell of LG-Q26 in the [ledger plan](../plans/ledger.md) as a dated "Measured" note, and do the same for LG-Q23 where the single writer bears on it. Record figures only. Do not answer either question, and do not change a leaning.
7. **A store that surprised you.** The store findings live in a separate repository that this session does not write to. Put what you saw in the handoff note, with the smallest query or program that shows it and the versions it ran on.

The generated reports (`single-writer-report.*`, `late-readings-report.*`, `writes-report.*`) are git-ignored and stay so. Copy the tables you cite into the README.

## What you do not decide

LG-Q23 and LG-Q26, whether a ledger has one writer or guarded writers, where single-writer is provided for Oxigraph on disk (TD-162), and which reading of a late posting a report shows. The maintainer has said that a report by effective day needs a balance as well as the flows, and has not said which balance. Your figures inform these. If a result seems to settle one, say what it shows and stop there.

## The handoff note, in your final commit

`docs/developer/notes/lg-18-cloud-run-handoff.md`, with an SPDX header as this file has, holding:

1. **The branch**, the commit it was cut from, and its last commit.
2. **The environment**: the kind of machine, the versions of Python, Java, Maven, pyoxigraph and Jena the runs reported, and anything setup skipped.
3. **Every command of the table above**, with its real result: the counts, the exit code, the elapsed time. For a step that failed first, what failed, what you changed, and the result after.
4. **Each change to the benchmark**, by file, with its reason, and whether it changes what is measured.
5. **The figures**, as the README's tables, and in a sentence or two what each part shows.
6. **Findings**, each separated from the bugs: what a store or the design did that the benchmark did not expect.
7. **What did not run or was not finished**, and why.
8. **What the index answered weakly**, from `mise run graph:ask -- misses --near`, or that `vyd` was not available.
9. **What the maintainer is asked to decide or check.**

Write it as the team writes: no semicolons, one line a paragraph, a colon only before a list, a table or a quotation, and no working document cited from a user-facing one. The benchmark READMEs may cite decisions and findings by their identifiers, as they already do.
