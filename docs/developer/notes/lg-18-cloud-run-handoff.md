<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# LG-18 cloud run, handoff, 2026-11-12

The run of LG-18 under the [brief](cloud-brief-lg-18-2026-11-12.md). It needed no fix to the benchmark, and every step passed.

## 1. The branch

The branch is `docs/placement-vehicles-structure-h0e5v9`, cut from `eded752` of `docs/placement-vehicles-structure`, the commit that holds the brief. The session's branch name was set by the environment, so it is not the `ledger/lg-18-cloud-run` the brief suggests. Nothing was pushed to `docs/placement-vehicles-structure` or `main`. Its last commit is the one that adds this note.

## 2. The environment

A cloud machine with 4 cores, 15 GiB of memory and Linux x86_64 (kernel 6.18). Python 3.14.10, Java 25.0.5.0.3 (Ubuntu build), Maven 3.9.11, pyoxigraph 0.5.13, rdflib 7.6.0 and Apache Jena 5.1.0, as the reports name them. `~/.lattice-setup-deferred` did not exist. `mise run bootstrap` finished, and the Jena test kit was not built by it, so `mise run bootstrap:sparql-testkit` was run once (19 s). `mise run work:here` listed no other session building here. The index was older than the files and was rebuilt by bootstrap.

## 3. The commands

| Step | Command | Result |
|---|---|---|
| 1 | `test_writes.py` and `test_check.py` | first 81 passed and 2 skipped in 276.73 s, exit 0. The two skips are the Jena variants of `test_ck15` and `test_ck27b`, which skip without the test kit. After the kit was built, 102 passed in 300.89 s |
| 2 | `test_single_writer.py` | 14 passed in 4.99 s |
| 3 | `test_late_readings.py` | 6 passed in 2.77 s |
| 4 | `benchmark/ledger-credit-kinds-jvm` | 22 passed in 140.39 s. The Java compiled at the first attempt |
| 5 | quick `check:ledger-credit-kinds-single-writer` | exit 0 in 114 s |
| 6 | quick `check:ledger-credit-kinds-late-readings` | 6 tests passed, `readings 5000 late 0%`, `5%` and `20%`, exit 0 in 20 s |
| 7 | quick `check:ledger-credit-kinds-jvm-writes` | all 26 `queue-` exports audited, exit 0 in 182 s |
| 8 | the three tasks, full | single-writer exit 0 in 765 s, late-readings exit 0 in 69 s, jvm-writes exit 0 in 645 s |

The brief's 102 for step 1 matches only when the Jena kit is built. LG-17's pack gives 102 for the whole directory then, which now holds 122 tests with the two LG-18 files.

## 4. Changes to the benchmark

None. No file under `benchmark/` or `tools/` was edited. None of the likely failures of the brief occurred, including `test_sw4`, `test_lr5`, the reading A from the close against the start, the early store against the whole store, and the test kit's Jena called from the writer's thread.

## 5. The figures

The tables are in the [benchmark README](../../../benchmark/ledger-credit-kinds/README.md) and the [native README](../../../benchmark/ledger-credit-kinds-jvm/README.md), under "Measured results". Part one shows that one writer that reads its path matches the best guarded writer on each store and does not fall as producers are added. One that keeps its balances is 29 to 55 times the guarded rate, and with batches of 100, 107 to 159 times in the Python run. Part two shows that B, the postings settled again in effective order, differs from the ledger's balance at 22 to 25 of 27 heads once postings are late. A read from the close costs 1.6 and 2.1 ms, against 8 and 32 ms from the start, and B about twice A from the start.

## 6. Findings

1. On Oxigraph on disk the guarded writers write duplicate positions (18, 30 and 38 at 2, 4 and 8 threads), which agrees with TSD-73. A single writer on the same store equals the replay in every run, closed, backlog and batched. It bears on TD-162 and decides nothing there.
2. The commit on TDB2 costs less here than on the laptop. The native keeper measured 74 to 80 commits a second where about 10 was expected, and the writer that reads 35 to 38.
3. The late corpus at 20,000 postings has 6 readings below zero with no late posting. They are one account, `sec0`, at the recordings 4,991 and 9,977, with balances down to -711,618 against a ceiling of 300,000. The generated stream overdraws it, and the writers' guard would refuse those debits. A, B and the recorded balance agree there, so it is a property of the corpus and not of the readings.
4. At 5,000 postings A is impossible at 2 and 3 readings with late postings and B at none. At 20,000 A is impossible at 9 and 13 readings and B at 6, the same as with none late.
5. Python's Jena, the test kit, ran in the queue runs without trouble from the writer's thread.

No store surprised me beyond the above, so there is no smallest case to record for the store findings.

## 7. What did not run

The Windows check of the three quick tasks was not run, since this is a Linux machine. The 2,048 MiB heap and the sizes were the plan's. No second writer behind a keeper and no restart that reloads its balances is measured, as the README says.

## 8. What the index answered weakly

`mise run graph:ask -- misses --near` recorded no misses and no near answers. I read the brief, the pack and the code directly and asked the index few questions, so that says little about its coverage.

## 9. For the maintainer to decide or check

1. Whether to accept the figures as the slice's Results, which stay "Filled at verification".
2. Whether the late corpus should refuse debits beyond availability, as the writers do, so that the impossible readings of the corpus are not mixed with those of a late posting (finding 3). I left the corpus as written.
3. LG-Q23, LG-Q26, where single-writer is provided for Oxigraph on disk (TD-162) and which reading of a late posting a report shows. Their Status cells carry the figures only.
4. The count in the brief and the pack for step 1, which holds with the test kit built.
