<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# LG-19 cloud run, handoff, 2026-11-13

The build and run of LG-19 under the [brief](cloud-brief-lg-19-2026-11-13.md). The change is small and the tests pass. What the maintainer reads is section 7, what moved, and section 9.

## 1. The branch

The branch is `ledger/lg-19-cloud-run`, cut from `c6b6ef09` of `docs/placement-vehicles-structure`, the commit that holds the brief. Nothing was pushed to `docs/placement-vehicles-structure` or `main`, and no pull request was opened. Its commits, oldest first, are the mark (`41607971`), the change with its tests (`c9164958`) and the commit that adds this note, which is the last.

## 2. The environment

A cloud machine with 4 cores and 15 GiB of memory, Linux x86_64. Python 3.14.10, Java 25.0.5.0.3, Maven 3.9.11, rdflib 7.6.0, pyoxigraph 0.5.13 and Apache Jena 5.1.0, as the reports name them. `~/.lattice-setup-deferred` did not exist. The Jena test kit was built with `mise run bootstrap:sparql-testkit` before any test. `mise run work:here` listed no other session building here.

## 3. Where the corpus overdrew before

The debits that the rule would refuse in today's stream, counted without changing it, so the stream carries on overdrawn after the first. The first refused posting is the first debit more than an account on its path held. By level is the debits that were more than the contract, sublimit, section and root held, and one debit can be more than several.

| stream | size | credits | debits | refused | first refused | by level | lowest balance |
|---|---|---|---|---|---|---|---|
| one-level | 1,000 | 5% | 945 | 0 | | 0, 0, 0, 0 | 0 |
| one-level | 5,000 | 5% | 4,761 | 2,242 | 2,585 | 0, 1,989, 2,193, 65 | -259,809 |
| one-level | 20,000 | 5% | 19,013 | 16,494 | 2,585 | 0, 16,241, 16,445, 14,317 | -3,048,969 |
| one-level | 1,000 | 30% | 691 | 0 | | 0, 0, 0, 0 | 0 |
| one-level | 5,000 | 30% | 3,499 | 0 | | 0, 0, 0, 0 | 0 |
| one-level | 20,000 | 30% | 13,987 | 5,206 | 5,135 | 0, 0, 5,206, 0 | -863,541 |
| two-level | 1,000 | 5% | 945 | 0 | | 0, 0, 0, 0 | 0 |
| two-level | 5,000 | 5% | 4,761 | 2,264 | 2,489 | 0, 2,057, 2,193, 63 | -259,809 |
| two-level | 20,000 | 5% | 19,013 | 16,516 | 2,489 | 0, 16,309, 16,445, 14,315 | -3,048,718 |
| two-level | 1,000 | 30% | 691 | 0 | | 0, 0, 0, 0 | 0 |
| two-level | 5,000 | 30% | 3,499 | 0 | | 0, 0, 0, 0 | 0 |
| two-level | 20,000 | 30% | 13,987 | 4,912 | 5,969 | 0, 0, 4,912, 0 | -712,127 |

So the corpus overdrew at 5% credits from posting 2,500 and at 30% from posting 5,000. The sizes with no refusal are 1,000 at both shares and 5,000 at 30%, and no contract ever stood short. The section at minus 711,618 that LG-18 found is this table's last row, the two-level stream at 20,000 postings and 30% credits, read at the recording 9,977 and not at the end of the stream, where it is lower.

## 4. The change

In `check.py`, `stream` and `stream_two_level` are one generator, `generate(count, credit_share, two_level)`, and the two keep their names and call it. The new `refuses_debit(step, at, amount)` is the writers' test, `any(step[i] < amount for i in chain(at))`, and `writes.Live.prepare` calls it in place of its own copy of the expression, which changes nothing it measures. `generate` holds the stepwise balance of every account, settles a debit with `settle_debit` and a credit with `settle_credit`, and drops a debit that `refuses_debit` refuses after every value of it is drawn. The one-level corpus now needs the balances of the ancestors as the two-level one did, and the credits' applied amounts equal the old ones wherever nothing is refused (the test of identity shows it, including the `applied` of the one-level debit, which is its amount, as before).

The choice of point 2 of the brief, the count. A stream of `count` postings has `count` postings, the generator drawing on until it has them, so the share of credits rises. The realised shares are in the table of section 7.

The choice of point 3, positions. A pass in which every draw was refused is drawn again at the same position, and its position is not skipped. I chose it because the period graphs and the closes are named by passes and a skipped pass would leave a period with fewer passes than it names, and at 5% credits most passes would be skipped. The cost is that the number of passes grows (16,190 passes for 20,000 postings at 5%, where it was 10,040) and a pass holds about 1.2 postings where it held 2. A stream that cannot reach its count, since every debit is refused and no credit is drawn, raises after 10,000 passes in a row with no posting (`IDLE_PASSES`), which is a guard and no benchmark parameter.

## 5. The tests

Added, as `test_ck50` to `test_ck57` in `test_check.py`, 29 tests with their parameters. No account is below zero at any posting of either stream at 400, 2,000, 5,000 and 20,000 postings (`ck50`). The same replay fails on a copy of the old generator kept in the test file at 20,000 postings, so the test can fail (`ck51`). The stream equals the old one where the table counts no refusal, at 1,000 postings at both shares and at 5,000 at 30%, for both streams (`ck52`), and differs at 5,000 and 5% where debits are refused (`ck53`). A refused debit leaves no trace in the length, the model's rows, the positions or the share of credits (`ck54`) or the stored count on Oxigraph (`ck55`). A stream that cannot reach its count raises (`ck56`), and `refuses_debit` is the writers' rule (`ck57`).

Corrected: none. No existing test asserted a number that the corpus changed, and the 122 tests that existed pass as they were, 151 with the new ones, and the 22 of the native module. I read the tests that depend on what the corpus holds (the discrimination checks, the write benchmark's late postings, the late readings' `test_lr5`) only by their passing, and did not read each one for a different reason than before.

One mistake of mine, since caught. The first names of the new tests, `ck30` to `ck35`, were the names of six tests that exist. Python took the later definitions and dropped the six silently, and the run showed it as 44 tests where 29 were new. They are `ck50` to `ck57` now, and the count is 151.

## 6. The commands

| Command | Before the change | After the change |
|---|---|---|
| `mise run check:ledger-credit-kinds` | exit 0 in 5,487 s, 122 tests | exit 0 in 6,368 s, 151 tests |
| `mise run check:ledger-credit-kinds-writes` | exit 0 in 678 s, 20 tests | exit 0 in 659 s, 20 tests |
| `mise run check:ledger-credit-kinds-jvm` | exit 0 in 238 s, 16 tests | exit 0 in 231 s, 16 tests |
| `mise run check:ledger-credit-kinds-jvm-writes` | exit 0 in 552 s, 6 tests | exit 0 in 547 s, 6 tests |
| `mise run check:ledger-credit-kinds-single-writer` | exit 0 in 698 s, 14 tests | exit 0 in 665 s, 14 tests |
| `mise run check:ledger-credit-kinds-late-readings` | exit 0 in 61 s, 6 tests | exit 0 in 60 s, 6 tests |
| `pytest benchmark/ledger-credit-kinds` | | 151 passed in 274.21 s |
| `pytest benchmark/ledger-credit-kinds-jvm` | | 22 passed in 117.91 s |

Each log has `report written to` and no WRONG RESULT. The brief expected 102, 14, 6 and 22 before the change. The 102 is `test_writes.py` and `test_check.py` together with the Jena kit built, and the first task ran the 122 of the whole directory. The reports are in `/tmp` of the session and not in the repository, as they are git-ignored.

## 7. What moved

**Where the corpus changed.** Refused is the debits drawn and dropped, which is more than the table of section 3 counts since the new stream does not carry on overdrawn. Identical is whether the stream equals the old one posting for posting.

| stream | size | drawn credit share | debits refused | postings | credits | realised credit share | last position | last position before | stored triples before | stored triples after | identical to before |
|---|---|---|---|---|---|---|---|---|---|---|---|
| one-level | 1,000 | 5% | 0 | 1000 | 55 | 5.5% | 492 | 492 | 8,531 | 8,531 | yes |
| one-level | 5,000 | 5% | 8691 | 5000 | 694 | 13.9% | 3280 | 2489 | 42,533 | 44,047 | no |
| one-level | 20,000 | 5% | 86358 | 20000 | 5260 | 26.3% | 16190 | 10040 | 170,205 | 183,186 | no |
| one-level | 1,000 | 30% | 0 | 1000 | 309 | 30.9% | 514 | 514 | 9,004 | 9,004 | yes |
| one-level | 5,000 | 30% | 0 | 5000 | 1501 | 30.0% | 2486 | 2486 | 44,882 | 44,882 | yes |
| one-level | 20,000 | 30% | 7818 | 20000 | 8389 | 41.9% | 11922 | 9977 | 179,471 | 185,551 | no |
| two-level | 1,000 | 5% | 0 | 1000 | 55 | 5.5% | 492 | 492 | 8,531 | 8,531 | yes |
| two-level | 5,000 | 5% | 10546 | 5000 | 776 | 15.5% | 3331 | 2489 | 42,533 | 44,198 | no |
| two-level | 20,000 | 5% | 85571 | 20000 | 5220 | 26.1% | 16028 | 10040 | 170,205 | 189,297 | no |
| two-level | 1,000 | 30% | 0 | 1000 | 309 | 30.9% | 514 | 514 | 9,169 | 9,169 | yes |
| two-level | 5,000 | 30% | 0 | 5000 | 1501 | 30.0% | 2486 | 2486 | 46,424 | 46,424 | yes |
| two-level | 20,000 | 30% | 4283 | 20000 | 7333 | 36.7% | 11088 | 9977 | 185,951 | 193,581 | no |

**Correctness.** Every benchmark passes its own criterion, and the discrimination checks pass at every size, so no check was loosened. The impossible readings of the late readings with nothing late are 0 for A and 0 for B at 20,000 postings, where they were 6 and 6.

**The writers.** The live writers' debits refused at 20,000 postings are 138 of 500 on the Python stores and on native Jena in memory, and 16 of 100 on TDB2, where they were 187 and 32. They are not none, because the request lists are drawn from the two-level stream and settled against a store that holds the preload of 20,000 postings, which still leaves accounts low.

**The headline figures.** The benchmark README's passage "Measured again on corpora that refuse an overdrawing debit (LG-19)" and the native module's have the tables. The run-to-run variation, from the cells whose inputs did not change, is 0.75 to 1.46 times for a Python root read and 0.66 to 2.06 on native Jena, 0.9 to 1.1 for a run of more than a few seconds, 0.7 to 1.3 for one of under a second, and up to 20% for a ratio between two folds. Inside that, nothing moved but the following.

| Figure | Before | After | Likeliest reason, as a hypothesis |
|---|---|---|---|
| rdflib root read at 20,000 postings and 5% credits, plain, one-level | 11,136 ms | 16,715 ms (1.50) | rows folded rose 4% and the store 7.6%, so rdflib's scan grows faster than the rows. Not tested |
| the shortcut's fallbacks from a checkpoint at 5% credits, 5,000 and 20,000 postings | 0 and 0 of 27 | 3 and 10 of 27 | at 5% the accounts drain and more contracts are fully restored when a read lands |
| the same at 30% credits and 20,000 postings | 18 of 27 | 27 of 27 | the same |
| contracts where plain and stepwise differ, 20,000 postings, 5% | 2 of 24 | 15 of 24 | more clamps bind once debits stop at zero |
| stored triples, one-level, 20,000 postings | 170,205 at 5%, 179,471 at 30% | 183,186 and 185,551 | more credits among the postings, and more checkpoints (50 to 80 at 5%) |
| a copied cut's extra triples at 20,000 postings | 1.16% | 1.84% | more cuts per posting |
| a guarded write at 20,000 postings | 7.4, 17.6 and 69.4 ms (Oxigraph memory, disk, Jena) | 5.4, 12.2 and 63.4 ms | a period holds 248 postings where it held 398, so the path reads fold fewer rows. Not tested |
| debits refused by the live writers at 20,000 postings | 187 and 32 | 138 and 16 | the preload leaves more room |
| impossible readings with nothing late, 20,000 postings | 6 and 6 | 0 and 0 | the overdraw is gone |

**Any conclusion that no longer holds.** The statements are quoted in the benchmark README with the new figure. None of them is a decision. The Status cell of LG-Q26 has figures that this run changes, the impossible readings (6 at 0% late, which the cell attributes to the generated stream, then 9 and 13, and B's 6) and the heads at which B differs (22 to 25 of 27), and its new note gives the new ones. LG-Q23's costs (the sum less the cuts at 1.01 to 1.14 of the kind-filtered read from the start) stand. The two questions are decided and I did not reopen either. Each has a dated "Measured again" note, figures only, and the old note is as it was.

## 8. Findings

1. The accounts drain at 5% credits. From about posting 2,500 most debits are refused, and a stream of 20,000 postings needs about 105,000 draws. The share of credits rises from 5% to 26% at 20,000 postings. The benchmark at 5% credits is no longer a stream of 5% credits, and the maintainer may want the drawn share raised or the sizes at 5% reconsidered. I changed neither.
2. A pass of the new stream holds about 1.2 postings at 5% credits where it held 2, so a period graph holds about 248 postings where it held 398, and the checkpoints are 80 where they were 50 at 20,000 postings. Anything that was read per pass or per period changes with it, which is the likeliest reason for the cheaper writes of section 7.
3. The rdflib result at 5% credits (1.4 to 1.6 times, section 7) is outside the variation and unexplained.
4. In the earlier run the checkpointed read of the sum less the cuts on Jena through the kit at 20,000 postings and 30% had one outlier of 978 ms, which gives a ratio of 0.07 in the before column. It is an outlier of the before run and is not a finding about the design.
5. Jena through the kit at 5% credits and 20,000 postings reads the sum less the cuts at 1.85 times the kind-filtered read from the start after the change, where it was 1.01. It is a few single reads of milliseconds and was not repeated. I did not find the cause.

## 9. What did not run or was not finished

The Windows check of the quick tasks was not run, since this is a Linux machine. I did not repeat the before run to measure the variation directly, and took it from the cells whose inputs did not change, which is why the bounds are wide. I did not read each existing test for a different reason than before (section 5).

## 10. What the index answered weakly

`mise run graph:ask -- misses --near` recorded no misses and no near answers, and said the knowledge index was older than the files it reads, so it built it. I asked the index few questions and read the brief, the code and the reports directly.

## 11. For the maintainer to decide or check

1. Finding 1: whether 5% credits at 5,000 and 20,000 postings is still the stream to measure, since the realised share is 14% and 26%.
2. Whether the late corpus and the request lists of the writes should draw their debits against the state of the store, so the live writers refuse none for lack of availability. I left them as they were.
3. The quotes in the benchmark README of what no longer holds, which are for you to resolve in the READMEs or leave as history.
4. Whether the positions choice (a refused pass is drawn again, no gap) is the one you want, since the other, skipping, keeps the number of passes and thins the periods.
