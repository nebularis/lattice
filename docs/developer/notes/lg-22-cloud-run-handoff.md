<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# LG-22 cloud run, handoff, 2026-11-16

The build and run of LG-22 under the [brief](cloud-brief-lg-22-2026-11-15.md). The changes are small and the tests pass. What the maintainer reads is section 6, what the run found, and section 10.

## 1. The branch

The branch is `ledger/lg-22-cloud-run`, cut from `d5e9a31e`, the commit of `docs/placement-vehicles-structure` that holds the brief. Nothing was pushed to `docs/placement-vehicles-structure` or `main`, and no pull request, tag or version bump was made. Its commits, oldest first, are the mark (`d57135b8`), the corpus labels, the resumable stream and the probes (`86e74de3`), the request lists that continue the preload (`6518a54b`), the refused sample read among the writes (`7ef44d61`), and the commit that adds the records and this note, which is the last.

## 2. The environment

A cloud machine with 4 cores and 15 GiB of memory, Linux x86_64. Python 3.14.10, Java 25.0.5.0.3, Maven 3.9.11, rdflib 7.6.0, pyoxigraph 0.5.13 and Apache Jena 5.1.0, as the reports name them. `~/.lattice-setup-deferred` did not exist, and the Jena test kit was built with `mise run bootstrap:sparql-testkit` before any test. `mise run work:here` listed no other session building here. The machine was slower on this day than on the day of LG-19's run, by about 15 to 19% in the median on a root read of the same corpus (section 6.1).

## 3. The changes

In `check.py`, `generate` is now a method of `Stream`, which keeps its random draws and balances between calls. `take(count)` is what `generate` was, and the first `count` postings are the same as before posting for posting. `continued(seed)` is a stream that starts from the balances this one reached and draws with another seed. I chose to continue the balances and not the random state, since the lists of several threads must differ and each must be valid from the preload's balances alone. `corpus_facts` gives what a corpus holds (the share of credits, the passes, the periods, the period graphs, the postings a period), `credit_label` names it by the share drawn and the share held, and `corpus_section` is the table and the note once that a figure per period is not comparable with a run before LG-19. `using_period` puts a period length in place for the probe and puts the module's back, so `EVERY_POSITIONS` is not changed. Every table of a report names its credits through `credits(row)`, and every report has the corpus section.

In `writes.py`, `requests(preload, count, share, seed)` takes the preload and returns the next `count` postings of the preload's stream under `seed`. The plan the native module gets carries one list for each preload size, the stress lists drawn for the preload of 5,000, and a list of requests to refuse. `refusing_requests(count)` is `count` debits larger than the stated amount of the root, on the contracts in turn, so every store refuses them. `refuse_one` reads the path of one and raises if the writer does not refuse it. `run_writes` reads the sample among the writes, one request in step with every `writes // REFUSALS` writes, and adds a row `refused debit` to the classes. I chose to read them among the writes and not after, since the writer writes no checkpoint and its reads fold a tail that grows with every write, so a sample read at the end cost 1.4 to 1.5 times a written debit's reads (section 7). `audit` counts the debits and credits written, and the stress, queue and single-writer tables show them. The native `LedgerWrites.single` does the same, with the list of refusals read from the plan.

In `single_writer.py` the producers' lists take the preload. `late_readings.py` has the corpus section. `probes.py` holds the two probes and the reference generator of before LG-19, which the test of `check.py` imports. `mise.toml` has the task `check:ledger-credit-kinds-probes`.

## 4. The tests

Added, 29 tests with their parameters. `test_ck60` to `test_ck64` in `test_check.py` (the balances of a stream are the replay of its postings, a continued stream is valid from its balances and a fresh one is not, the period graphs are the quads' graphs, the labels, the period context). `test_wr20` to `test_wr26` in `test_writes.py` (one writer refuses none on each store, which fails on the old lists at 20,000 postings, each stress list is valid alone, the several-writer run counts its refusals, a refused request's row, a sample that is not refused fails the run, the report). `test_sw7` and `test_sw8` in `test_single_writer.py`, and `test_pr1` to `test_pr5` in the new `test_probes.py`. The names were checked free before they were added, and no name occurs twice in a file.

The collected count of `benchmark/ledger-credit-kinds` and `benchmark/ledger-credit-kinds-jvm` was 173 before (151 and 22) and is 202 after (180 and 22), which is 173 and 29.

Corrected: no assertion changed. `requests` took no preload before, so the six callers in the tests changed their call (`test_wr3`, `test_sw2`, `test_sw4`, `exported` of the native module's `test_jvm_writes.py`, which the three of `test_jw1` to `test_jw3` use), and `test_wr1` now accepts the class `refused debit` beside the written classes.

Two of my own mistakes, since caught. The test of `corpus_facts` failed on six cases because I had passed the one-level flag the wrong way round, so each corpus reported the other's graphs, and it is fixed. A native test failed because it still called `requests` by the old signature.

## 5. The commands

| Command | Result |
|---|---|
| `check:ledger-credit-kinds-writes`, twice, before the change | exit 0 in 775 and 745 s, 20 tests |
| `check:ledger-credit-kinds-jvm-writes`, twice, before | exit 0 in 636 and 647 s, 6 tests |
| `check:ledger-credit-kinds-single-writer`, twice, before | exit 0 in 804 and 769 s, 14 tests |
| the six tasks after the change, in the order of the brief | exit 0 in 7,300, 846, 259, 622, 767 and 71 s, with 180, 29, 16, 6, 19 and 6 tests |
| `check:ledger-credit-kinds-probes` | exit 0 in 1,036 s, 5 tests |
| `check:ledger-credit-kinds-writes` and `check:ledger-credit-kinds-jvm-writes` again, after the sample was moved among the writes | exit 0 in 836 and 621 s |
| `pytest benchmark/ledger-credit-kinds` | 180 passed in 359.72 s |
| `pytest benchmark/ledger-credit-kinds-jvm` | 22 passed in 124.01 s |

Every log has `report written to` and no WRONG RESULT. The writes and native writes figures in the README and in this note are from the second run after the change, which has the sample among the writes. The first run after the change had it at the end and is described in section 7. The reports are in the scratchpad of the session and not in the repository, as they are git-ignored.

## 6. What the run found

**1. The variation.** From the two baseline runs of each of the three tasks, the larger of two runs over the smaller by kind of figure, median, 90th percentile and greatest. The cost of a write in Python 1.03, 1.08, 1.20 and native 1.07, 1.17, 1.26. The commits a second of the stress in Python 1.02, 1.04, 1.04 and native 1.04, 1.10, 1.14. The lost races 1.07, 1.07, 1.27 in Python and 1.11, 1.17, 1.29 native. One writer's commits a second 1.07, 1.22, 1.40 in Python and 1.08, 1.19, 1.44 native, and the wait of a closed run 1.09, 1.21, 1.34. The reads were not run in a pair, since the first task takes two hours. Their variation is taken from LG-19's run and this run on the same corpora, which are two days apart, and it is wider. The root reads over 20 ms ran 1.19, 1.15 and 1.12 times as long in the median on rdflib, Jena and Oxigraph, with a least of 0.85 to 0.94 and a greatest of 1.49 to 1.77.

**2. The request lists.** At 20,000 postings the single writer refuses 0 of 500, where it refused 138 (Oxigraph in memory and on disk, Jena through Python, native Jena in memory) and 0 of 100 on TDB2, where it refused 16. It writes 297 debits and 203 credits of the 500, where it wrote 218 and 144 with 138 refused, and 60 and 40 on TDB2. The stress and the single writer refuse none at one thread or one producer, where they refused 24 of 1,000, and they write 685 debits and 315 credits. At 2 to 8 threads they still refuse, and the lists sent one after another refuse 10, 63 and 66 at 2, 4 and 8 threads and round robin 16, 52 and 61, so what they refuse is the joint draw of lists that are each valid alone on accounts they share, not the order of interleaving. That is a real refusal, the runs count it beside the lost races, and no audit was loosened. The cost of a refused request, each row the average of 100 requests, is 6.53, 16.48 and 75.72 ms on the Python stores and 17.97 and 15.36 ms on native Jena in memory and on TDB2 at 20,000 postings, against a written debit's reads and settling of 6.75, 16.97, 79.13, 17.95 and 16.17 ms. A refusal costs the path reads and saves the update and confirmation, under 1 ms in memory and 13 ms on TDB2.

**3. The writers' figures that moved beyond the variation.** A guarded debit at 20,000 postings costs 7.0, 17.5 and 81.4 ms on the Python stores and 18.6 and 29.8 ms native, which is the cost before LG-19 (7.4, 17.6, 69.4, 17.3 and 31.8 ms) and not the 5.4, 12.2, 63.4, 15.7 and 25.7 of LG-19. LG-19's sample wrote 362 of its 500 and so folded a shorter tail, and its reason, that a period holds fewer postings, is not borne out. The cost on Oxigraph on disk is 1.22 times the two baseline runs (greatest 1.20), the stress on Oxigraph in memory at 8 threads 1.10 times (greatest 1.04) with fewer requests refused, the stress on TDB2 1.16 to 1.22 times, a durable commit varying with the disk, and the keeper in memory with no guard in a backlog 1.56 times (greatest 1.44), a run of 0.3 s. Everything else did not move.

**4. The two probes.** The period probe on the one-level corpus at 20,000 postings and 5% credits drawn, the rows fixed at 20,000. rdflib's plain root read takes 59.0, 32.1, 20.7 and 12.2 s at 969, 486, 306 and 156 named graphs (periods of 100, 200, 320 and 640 passes), 61, 66, 68 and 78 ms a graph, and Oxigraph 343, 229, 214 and 245 ms. The hypothesis of LG-19 stands for rdflib, the time follows the graphs with the rows fixed, and not for Oxigraph. 486 graphs against 306 is 1.59 times and the reads took 1.55 times as long. The cut probe on Jena through the kit, 30 reads after 5 warm-up reads: the sum less the cuts costs 1.05 times the kind-filtered read over the 27 ancestor reads from the start (1.05 at the root) and 1.23 from a checkpoint (1.28 at the root). LG-19's 1.85 did not hold, and both ratios are inside the earlier 1.01 to 1.14 and 1.12 to 1.35. The two-level corpus at 5% credits holds 2,062 cuts in 5,220 credits now and held none in 987 credits before LG-19.

**5. Reading B's smallest case.** The account is `urn:acct:sec0`, the reading as known at recording 5,547 for the day 5,000 over 9,615 postings, where B is minus 2,061. The first posting that takes sec0 below zero in effective order is the debit 5,902 of 345 on `con1-1`, recorded and effective at position 2,924. In recorded order, the writer's own, sec0 stood at 2,084 before it and its whole path held at least 345, so it was accepted. In effective order sec0 stands at 90 before it and falls to minus 255. The postings that are recorded after it and effective before it are 12 under sec0, 6 of them debits that sum to 1,391, recorded at positions 2,951 to 3,493 and effective at 2,351 to 2,893, and the recorded balance exceeds the effective one by 1,994 before it, 603 of which I did not trace. The hypothesis stands. A debit the writer accepted in recorded order overdraws when the postings are settled again in effective order, because debits recorded later and effective earlier take their room first. The debit that overdraws is not late itself. The case cannot be cut below the history that drained sec0, since sec0 starts at 300,000, and the reading is impossible at sec0 only, 4 times with 5% late and 3 times with 20%. Nothing in `late_readings.py` changed.

**6. The three tests.** The corpora they build are the pre-LG-19 corpora posting for posting at each size they use, so none passes for a reason the change made. `test_ck3` raises "the cap's plain and kind-filtered balances are equal" on a stream of debits only, `test_ck21` "no ancestor's ceiling binds in the two-level corpus", `test_ck32b` "no ancestor stands above its stated amount", `test_wr16` "the effective sum reads 997,217 through the engine, the model gives 1,001,221", and `test_lr5` "reading B is 994,754 through the engine, the model gives 993,179". Each raises for the reason its name gives. `test_ck21` is named for a two-level corpus and builds the one-level stream, which is what it needs, since credits at contracts cannot be cut. No test can no longer fail.

**7. What no longer holds.** The statements are quoted in the benchmark README with the new figure. LG-19's "The cost of a write at 20,000 postings fell" and its reason are not borne out, the cost is the cost before LG-19. Its "They are not none, because the preload of 20,000 postings still leaves accounts low" is 0, its "rdflib's scan cost grows faster than the rows, which we have not tested" is tested and holds, and its Jena 1.85 is 1.05. In the Status cell of LG-Q23, the note of 2026-11-13 that "A guarded write at 20,000 postings costs 0.7 to 0.9 of what it cost" is 0.9 to 1.2. The cell of LG-Q26 quotes figures that did not move. Both questions are decided and I did not reopen either. LG-Q23 has a dated "Measured again" note, figures only.

## 7. Findings apart from the above

1. A refused request read after the 500 writes cost 1.4 to 1.5 times a written debit's reads, 8.6 against 5.7 ms on Oxigraph in memory at 1,000 postings, with the same queries. The writer writes no checkpoint, so the reads fold a tail that grows with every write, and a sample read last sees the longest. I read it among the writes, and ran the two tasks again. The first run, which is in no figure, had the sample at the end.
2. The reads of a write grow with the postings written since the last checkpoint, and the means of the write tables carry that. A table of the cost of a write is a mean over a tail that depends on how many writes were made, so a sample with fewer writes costs less. This is what LG-19 mistook for a cheaper period.
3. `Live.balance` caches a checkpoint's balance for each account the first time it reads it, so the first reads of a run are dearer, and a refused sample over all 24 contracts pays it once. I did not measure it apart.
4. rdflib's cost for each graph, 61 to 78 ms a graph on a read that folds 20,000 rows, means that the period length matters on rdflib more than the rows do. It is the maintainer's to weigh.
5. The 5% corpus held no cut before LG-19, so the sum less the cuts was timed on postings alone there. Any figure of the sum less the cuts at 5% credits before LG-19 read an empty set of cuts.

## 8. What did not run or was not finished

The Windows check of the quick tasks was not run, since this is a Linux machine. A pair of runs of the read tasks was not made, since the first takes about two hours, so the variation of the reads comes from two days. The 603 of reading B's difference was not traced. A corpus wide enough to hold a low credit share at 20,000 postings was not built, and the space a refusal's own record takes is not modelled, as the brief says. A corpus like the first would need a tree whose sublimits hold more than a hundred thousand, or a debit smaller than 250 on average, and both change what the benchmark measures. The second would need a record of a refusal in the ledger, which is a design decision.

## 9. What the index answered weakly

`mise run graph:ask -- misses --near` recorded no misses and no near answers, and said the knowledge index was older than the files it reads, so it built it. I asked the index little and read the brief, the code and the reports directly.

## 10. For the maintainer to decide or check

1. How long a period should be on rdflib, given 61 to 78 ms for each named graph (section 6.4). I changed no period length.
2. Whether the 5% rows are still the rows to measure, now that they are labelled. The corpus holds 26% credits and its cut count went from 0 to 2,062, so the figures at 5% are of another corpus than LG-17's.
3. LG-19's statements that no longer hold (section 6.7), which are for you to resolve in the READMEs or leave as history, and the note in LG-Q23.
4. Whether the several-writer refusals, which are the joint draw of lists on shared accounts, should be reduced by lists that draw on fewer accounts, or left as the joint capacity they are.
