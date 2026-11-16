<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Ledger credit kinds

A benchmark under [ADR-A124](../../docs/architecture/decisions/ADR-A124-benchmark-root.md). It measures what a credit's kind and a stepwise credit ceiling add to the read of an ancestor's balance, on every engine the repository runs SPARQL on, before the ledger builds them. A cost measured on one engine is a hypothesis for another ([STD-176](../../docs/developer/standards.md)), so each read runs on rdflib in memory, Oxigraph on disk and Jena ARQ in memory.

Under the ledger's agreed design a draw or credit is posted once, at the account it names, and an ancestor's balance is a fold over its subtree's postings in the current period's named graph. The decision on LG-Q10 adds a kind to a credit posting, a concept IRI from a scheme, and each account declares which kinds restore it, all kinds by default. A ceiling is already part of the design, since a credit never lifts an account above its stated amount (law LD3), and where it can bind at an ancestor the fold has to be a running balance applied posting by posting.

## Headline figures

At 20,000 postings unless said, on the cloud machine of the measured results below. A corpus is named by the share of credits drawn and the share it holds, since a corpus that refuses an overdrawing debit holds more credits than were drawn. A ratio is within one run on one engine.

| Figure | Value | Measured |
|---|---|---|
| credits of the corpus drawn at 5%, one-level and two-level | holds 26.3% and 26.1%, in 16,190 and 16,028 passes (the corpus drawn at 30% holds 41.9% and 36.7%) | 2026-11-13 |
| the kind-filtered fold against the plain, over all 27 ancestor reads at 30% credits | 1.15 on rdflib, 2.32 on Oxigraph, 1.21 on Jena through the kit, 1.49 on native Jena in memory and 1.51 on TDB2 | 2026-11-16 |
| the stepwise fold against the plain, the same reads | 1.20, 5.94, 5.72, 2.86 and 2.22 | 2026-11-16 |
| a checkpointed stepwise read against the full read | 3% on rdflib, Jena and native Jena, 0.89 on Oxigraph | 2026-11-16 |
| the shortcut's fallbacks in 27 checkpointed reads | 10 at 5% credits drawn and 27 at 30% | 2026-11-13 |
| the stored triples, one-level and two-level | 183,186 and 189,297 at 5% credits drawn, 185,551 and 193,581 at 30% | 2026-11-13 |
| the sum with cuts against the kind-filtered read in the same form, two-level at 30% credits, from the start and from a checkpoint | 1.01, 1.01 and 1.19, then 1.12, 1.35 and 1.32, on rdflib, Oxigraph and Jena through the kit. Repeated 30 times on Jena at 5% credits drawn, 1.05 and 1.23 | 2026-11-16 |
| the plain root read on rdflib at 5% credits drawn, with the rows fixed at 20,000, by named graphs | 12.2 s at 156, 20.7 s at 306, 32.1 s at 486 and 59.0 s at 969 graphs. Oxigraph does not follow, 214 to 343 ms | 2026-11-16 |
| the cuts of the two-level corpus at 5% credits drawn | 2,062 in 5,220 credits | 2026-11-16 |
| a cut that copies its position, in extra triples | 1.84% | 2026-11-13 |
| a guarded write of a debit, Python on Oxigraph in memory, Oxigraph on disk and Jena, then native Jena in memory and TDB2 | 7.0, 17.5, 81.4, 18.6 and 29.8 ms | 2026-11-16 |
| a refused request, the same stores | 6.5, 16.5, 75.7, 18.0 and 15.4 ms, which is a written debit's reads and settling, with no write | 2026-11-16 |
| debits one live writer refuses | 0 of 500 | 2026-11-16 |
| the writer that reads its path against the best guarded writer, commits a second | 124 against 127 on Oxigraph in memory, 43 against 47 on disk, 16 against 17 on Jena. The keeper is 55.9, 75.1 and 24.6 times, and with batches of 100 138.5, 170.0 and 122.7 times | 2026-11-16 |
| late readings | with nothing late, no reading below zero for A or B. With 5% and 20% late, A is below zero at 6 and 9 of 81 readings, B at 4 and 3, and B differs from the ledger at 20 and 22 of 27 heads | 2026-11-13 |

## What it does

The tree has depth 4: a root, 2 sections, 3 sublimits to a section and 4 contracts to a sublimit, so 33 accounts. The first section is a cap and accepts recoveries only, and every other account accepts all kinds. Each account's ceiling is its stated amount. Postings come in passes of one to three (a pass position, then a micro-position in the pass) on random contracts, and each goes into a named graph keyed by its sublimit and its period of 200 passes. A credit is a recovery, a reinstatement or a write-back, in equal shares, under `https://example.org/`, except that a quarter of the credits on a path where no account restricts kinds (everything under the second section) carry no kind. A debit that would leave an account on its path below zero is refused, as the writers refuse it, and is not in the stream, and the stream draws on until it has its count. Credits are larger than debits, so a ceiling binds often.

A credit is clamped at the contract it is posted to, which it never lifts above its stated amount (law LD3), and the amount applied there is stored on the credit (`l:applied`). What an ancestor folds is the credit as applied at its drawn contract, clamped again at the ancestor's own ceiling. A posting is 8 triples, and a credit has one more for what was applied and, if it has a kind, one for the kind.

At each period close a checkpoint is written as data, in the graph `urn:graph:checkpoint:<period>`. It holds, for each of the 33 accounts, the balance by each of the three folds (5 triples per account), so the filter and the clamp are already reflected in the balances of the second and third. A checkpointed read starts from the last checkpoint at or before the point and folds only the period graphs after it.

Every ancestor (6 sublimits, 2 sections, the root) is read at three pass positions, none on a period end, by each of four reads, from the start of history and from the checkpoint.

* **plain** is the stated amount plus the signed sum of every posting's offered amount in the subtree up to the point. It is today's design and the baseline.
* **kind-filtered** counts a credit only if the ancestor accepts its kind, by a join to the credit's kind, in one SPARQL aggregate.
* **stepwise** is an ordered SELECT of the accepted postings (`ORDER BY ?pos ?mp`, with the applied amount) folded by the caller, each credit clamped at the ceiling. Its time is split into the ordered query with the transfer of its rows, and the loop. The Java caller also splits the query from the transfer.
* **shortcut** is the kind-filtered aggregate from the stepwise checkpoint, then a check, and the stepwise fold only where the check fails. The check is that the balance is within the ceiling and that every contract under the ancestor was offered, over the folded range and in credits of any kind, no more than it had outstanding at the range's start (its stated amount less its stepwise checkpoint balance, and nothing outstanding from the start of history). A credit is clamped at its drawn contract only where it exceeds what is outstanding there, and debits only add to the outstanding amount, so the condition rules out a clamp at any contract in the range. The applied amounts are then the offered ones the aggregate summed, and the ancestor cannot be lifted above its ceiling because its outstanding draw is at least its contracts' together. The condition is sufficient and not necessary, so a failed check does not mean a clamp happened. It costs a second, grouped aggregate over the same range.

The join to the credit's kind has two forms. `optional` is an `OPTIONAL { ?p l:kind ?k }` in the graph block. `union` is `{ ?p l:direction l:Debit } UNION { ?p l:kind ?k } UNION { ?p l:direction l:Credit . FILTER NOT EXISTS { ?p l:kind ?z } }`, and its third branch keeps a credit that has no kind, which would otherwise match neither of the first two and drop out of the fold.  Their cost differs by engine (below), so each backend reads the form that is cheaper on it, rdflib and Jena `optional` and Oxigraph `union`, and `LEDGER_KINDS_FORM=optional|union` forces one on all three. The report's `kind join` column says which was read.

## Credits at two levels of a path, and the cut

Where every credit is posted on a contract, no ancestor's ceiling binds. A credit posted at an ancestor restores that ancestor and not the accounts below it, so a later credit below can push the ancestor past its ceiling (section 4.8 of the sketch on balances under post-once). The second corpus, `two-level`, has the same passes, debits, contracts, amounts and kinds as the first (`stream_two_level`), but `UPPER_SHARE`, one half, of the credits are posted at a sublimit or a section on the drawn contract's path instead of at the contract, chosen at random among the accounts there that accept the credit's kind. A credit posted at an internal account X is clamped at X, changes no account below X, and folds upward from X.

Where a credit lives. A credit at a sublimit goes in that sublimit's own period graph, shared with the postings of its contracts. A credit at a section goes in a period graph keyed by the section. An account reads the graphs keyed by every sublimit and section in its subtree, itself included, so a section's credit is read by that section and the root and by no sublimit, and a sublimit's credit by the sublimit, its section and the root. No account reads a graph outside its own subtree.

The writer holds the stepwise balance of every account. It applies a credit at its posting account up to that account's room, then each accepting ancestor takes the lesser of the applied amount and its own room, stepwise, and where it takes less the difference is a **cut** at that ancestor. A cut is stored with the credit in the credit's own graph as 3 triples, a cut node naming its posting (`l:cutOf`), the ancestor it is at (`l:cutAt`) and its value (`l:cutValue`). A cut has no position of its own, so a read joins it to its posting for the position bound, in the same graph. The 4-triple form, with a copy of the position, saves that join and costs a triple a cut, and is the second cut form below. A cut is recorded only at an ancestor that accepts the credit, so the read of cuts needs no kind filter.

**sum-with-cuts** is an ancestor's balance as the stated amount (or the checkpoint's balance), plus the debits in its subtree, plus the credits it accepts at the amount applied, less the cuts recorded at it. It is two aggregates, one over the postings and one over the cuts, whose times are reported apart. The postings aggregate is a `UNION` of three branches inside the graph block, a debit, a credit with a kind and a credit with no kind, with no `OPTIONAL` there, since an `OPTIONAL` inside `GRAPH ?g` reads every graph on Oxigraph 0.5.13 (TSD-71) and the applied amount is absent on a debit. The account's kind filter is outside the graph block, where its declarations are in the default graph. One form is used on all three engines. The postings aggregate alone is the kind-filtered sum of applied amounts with no cuts, which the check reads as well and compares with the model's.

## Like-for-like read forms, a cut that copies its position, and a ceiling above a stated amount

The sum with cuts reads postings with a three-branch `UNION`, and the kind-filtered fold joins the kind by `OPTIONAL` or by its own `UNION`, so a ratio between the two mixes the cost of the cuts with the cost of the query form. Three further things are read to separate them, and the sketch's own tree is tested in an engine.

**Like-for-like reads.** The two-level corpus is also read by the three folds the one-level corpus has, each against the model at every ancestor, point and mode. `plain` and `shortcut` are the one-level reads. On this corpus a credit posted at an internal account restores it and every accepting account above it, so the shortcut's check counts the credits posted anywhere in an account's subtree against what each account on the path has outstanding, where the one-level check counts credits at contracts. The one-level check is unchanged. `kind-filtered-union` is the kind-filtered sum of offered amounts written in the three-branch `UNION` form of the postings part of `sum-with-cuts`, so the ratio of `sum-with-cuts` to it is what the applied amount and the cuts add. It does not match the micro-position the kind-filtered fold also matches, so its ratio to the kind-filtered fold bundles the query form with that pattern.

Why the forms differ in cost, one line per engine. None of the three can explain a query here, so each reason is a hypothesis and none was read from a plan.

* **Oxigraph 0.5.13** cannot explain. `Store.query` has no explain option and `QuerySolutions` offers only `serialize` and `variables`. TSD-71's reading of the source, an `OPTIONAL` inside `GRAPH ?g` under a `VALUES ?g` that falls back to a hash join over every graph, is the reason the `optional` form is dear. It says nothing of the gap between the two `UNION` forms, which is not explained.
* **Jena ARQ 5.1.0 through the kit** cannot explain. The kit passes the query text to ARQ and returns the solutions, with no explain call, and we did not build one.
* **rdflib 7.6.0** cannot explain a plan. It prints the parsed algebra (`rdflib.plugins.sparql.algebra.pprintAlgebra`), which names no join order and no cost, and we did not read it. Why its `UNION` form is dear stays open (TSD-Q37).

**A cut that copies its position.** The default cut, `joined`, is 3 triples, and a read joins it to its posting for the position bound. The `copied` cut also carries its posting's position (`l:cutPosition`), 4 triples, and the cuts read needs no join. The choice is the named `cut_form` (`CUT_FORMS`, default `joined`) on `quads`, `expected_stored`, `cuts_scan`, `read_with_cuts` and `run_backend_cut_forms`. Each form is loaded into a store of its own, read by the sum with cuts from the start and from the checkpoint, and checked against the model, with the time of the cuts aggregate kept apart. It runs at 30% credits.

**A ceiling above a stated amount.** An account has a `ceiling_amount`, and its `ceiling` is that or, by default, its stated amount, so every default figure is unchanged. The writer, the model and the stepwise read clamp at the ceiling, never at the stated amount, and a read of the stepwise fold gets the ceiling from the store (`l:ceilingAmount`, one triple, only where an account has one of its own). The variant corpus (`build_ceiling_tree`) gives a ceiling of `CEILING_FACTOR` (1.5) times the stated amount to a share `CEILING_SHARE` (one half) of the contracts and sublimits, chosen by a seeded draw, 11 of 30. A credit can then lift an account above what was drawn from it. It is read by the same three folds as the two-level corpus, at 30% credits.

**The sketch's tree in an engine.** `run_sketch` loads the four-step history of section 4.8 of the balances sketch into each backend as the benchmark's own quads, written by the benchmark's writer (`using_tree` makes the benchmark's functions run on another tree), and reads the annual cap and the aggregate by every fold.

## What it tests

| Claim | Test |
|---|---|
| An ancestor's kind-filtered fold counts a credit only if the account accepts its kind, keeps a credit with no kind where every account accepts all kinds, and equals the plain fold where the account accepts every kind | every ancestor at every point, against the model, on each backend and each form of the join |
| The stepwise fold folds the credit as applied at its drawn contract, which a plain sum cannot | the same, at 30% credits, where the model has a clamp bind at 24 of 24 contracts |
| A checkpoint holds the balance by each fold, including the filter and the clamp | every checkpointed read against the model's balance and posting count |
| The shortcut gives the stepwise balance, and falls back where its check fails | every shortcut read against the model's stepwise balance, and the rate of falling back |
| The filter, the clamp and the checkpoints are not the cost of a different design from the plain fold | time per read and postings folded per read, each read against the plain fold, on each backend and size |
| When credits land at two levels of one path, an ancestor's kind-filtered sum of applied amounts is wrong where a cut was recorded, and the sum with cuts equals the stepwise balance | the two-level corpus, every ancestor at every point, in both modes, on each backend: the sum with cuts and the stepwise fold against the model's stepwise balance, and the postings alone against the model's sum of applied amounts, which differs from it wherever a cut was recorded |
| The writer's cuts are the stepwise law's | the cuts the writer recorded against the cuts the model's replay gives, and the stored triples, cuts included, against the arithmetic |
| The cuts do not hide behind a different query form | the plain fold, the shortcut and a kind-filtered read in the sum with cuts' own `UNION` form on the two-level corpus, each against the model, and the ratio of the sum with cuts to that read |
| A cut that copies its position reads as the joined cut does | the same corpus stored both ways, the sum with cuts against the model from the start and the checkpoint on each backend, with stored triples and the time of the cuts aggregate for each |
| A ceiling above a stated amount lets a credit lift an account past what was drawn, and the sum with cuts is still the stepwise balance | the ceiling variant, every ancestor at every point, mode and backend against the model, which clamps at the ceiling, and the count of cuts and of balances above their stated amount |
| The sketch's tree and history read the sketch's figures through an engine | the aggregate reads 9 as the sum of applied amounts, 7 stepwise and 7 as the sum with cuts, with one cut of 2, and the annual cap reads 9 under every fold, on each backend |
| The cost is not one engine's or one caller's | the same corpus and the same balances on three engines through Python, and on Jena in memory and on TDB2 called from Java ([benchmark/ledger-credit-kinds-jvm](../ledger-credit-kinds-jvm/README.md)) |

## Pass criterion

Every read on every backend, from the start of history and from the checkpoint, equals the model's balance for that fold, ancestor and read point and counts the postings the model counts, and every shortcut read equals the model's stepwise balance. The folds therefore differ from each other exactly where the model says, and the report records where it expects it (`model_expects` in `report.json`: the contracts where a clamp binds, the ancestors where the stepwise and the plain or filtered balances differ, the credits with no kind). The stored triples, checkpoints included, have the count the arithmetic gives. The model must itself tell the folds apart, or the corpus is refused: the cap's plain and kind-filtered balances differ, a credit with no kind exists, and at 30% credits a clamp binds at a contract and reaches an ancestor. **A wrong balance, posting count or stored count fails the run. Time never does.** `test_check.py` shows the check fails on a balance off by one, on a filter that ignores the kind, on a join that drops a credit with no kind, on a missing clamp at the drawn contract, on a wrong checkpoint, on a shortcut that skips a needed fallback and on a stored count, that it does not fail on time, that the run leaves no store open, that each form of the join gives the model's balances, and that the emitted corpus matches the model ([PRI-63](../../docs/developer/principles.md)).

The two-level pass criterion is part of the same check. Every kind-filtered, stepwise and sum-with-cuts read, from the start and from the checkpoint, equals the model, the cuts the writer recorded are the model's, the stored count includes 3 triples a cut, and at 30% credits an ancestor's ceiling binds (a cut exists) and the sum of applied amounts with no cuts differs from the stepwise balance at an ancestor, on the model and on each engine. A corpus where that could not be told is refused. `test_check.py` also shows the check fails when a cut is dropped from the stored data (with the stored count agreeing, so only the balance can tell), when the writer records no cut, and that the four-step history of the sketch gives 9 for the sum of applied amounts, 7 for the stepwise balance and the sum with cuts, with one cut of 2 at the aggregate, and 9 at the annual cap under every fold.

The like-for-like reads, the cut forms, the ceiling variant and the sketch's tree are part of the same check. Every `plain`, `shortcut` and `kind-filtered-union` read on the two-level corpus equals the model. Both cut forms give the model's balance and their stored count equals the arithmetic with 3 or 4 triples a cut. Every copied position is its posting's, which is checked on the stored cuts themselves, since a read sees a copied position only where a read point falls on it. In the ceiling variant every read equals the model, which clamps at the ceiling, the corpus is refused unless some ancestor stands above its stated amount at a read point, and the stored count includes a triple for each ceiling. The sketch's figures are asserted on each engine. `test_check.py` shows the check fails on a `kind-filtered-union` read that is off by one, on a shortcut that skips a fallback on the two-level corpus, on a copied cut with a wrong position, on a read that clamps at the stated amount in the ceiling variant, on a ceiling variant in which nothing stands above its stated amount, and on a writer that records no cut when the sketch is read through an engine.

## Run it

```bash
mise run check:ledger-credit-kinds
```

```bash
LEDGER_KINDS_QUICK=1 mise run check:ledger-credit-kinds
```

```bash
LEDGER_KINDS_NEW_ONLY=1 mise run check:ledger-credit-kinds
```

The sizes are 1,000, 5,000 and 20,000 postings at 5% and 30% credits. `LEDGER_KINDS_MAX` caps the postings and `LEDGER_KINDS_QUICK=1` runs the smallest size. `LEDGER_KINDS_NEW_ONLY=1` skips the one-level corpus and runs only the two-level corpus with its like-for-like reads, the cut forms and the ceiling variant, `LEDGER_KINDS_REPORT_DIR` writes the report elsewhere. The full run took 7,300 s (about two hours) on the cloud machine below, with its 180 tests, most of it rdflib at 20,000 postings, where each read from the start of history takes seconds to tens of seconds. Jena needs the test kit jar, built on first use by `mise run bootstrap:sparql-testkit` ([ADR-A125](../../docs/architecture/decisions/ADR-A125-test-support-tooling.md)). Where there is no `java` or no jar, the Jena runs are left out and the report's environment says so. `report.md` and `report.json` are generated, git-ignored and written here, with the native Jena caller's timings merged in by `mise run check:ledger-credit-kinds-jvm`. The Oxigraph store is a temporary directory, removed when the run ends, including on failure.

### The whole benchmark

Seven tasks make up this benchmark, with the native module's two among them. They share one corpus and one writer, so the code as it stands is exercised only by running all seven, and a change to the corpus or the writer moves the figures of every one. Run one at a time, never two together, since they disturb each other's timings. None is part of `mise run check`, which a test holds (ADR-A124).

| Task | What it runs | On the cloud machine below |
|---|---|---|
| `check:ledger-credit-kinds` | the reads of both corpora on three engines, with the benchmark's own tests | 7,300 s |
| `check:ledger-credit-kinds-writes` | the live writer, the guard, the stress and the late postings | 846 s |
| `check:ledger-credit-kinds-jvm` | the reads on Jena called from Java, and its plans | 259 s |
| `check:ledger-credit-kinds-jvm-writes` | the writer and the counter probe on Jena called from Java | 622 s |
| `check:ledger-credit-kinds-single-writer` | one writer per ledger against the guarded writers | 767 s |
| `check:ledger-credit-kinds-late-readings` | the readings of a balance by effective day | 71 s |
| `check:ledger-credit-kinds-probes` | the period length and the repeated read of the cuts | 1,036 s |

That is about three hours in all, on 4 cores. The benchmark's own tests alone, 183 here and 22 in the native module, run in about five minutes with `mise exec -- python -m pytest benchmark/ledger-credit-kinds benchmark/ledger-credit-kinds-jvm`, and show that the checks can fail, never what a store costs.

## Measured results

Run on a cloud machine with 4 cores, 15 GiB of memory and Linux x86_64, with Python 3.14.10, Java 25.0.5, Maven 3.9.11, rdflib 7.6.0, pyoxigraph 0.5.13 and Apache Jena 5.1.0. The reads were measured on 2026-11-13 and again on 2026-11-15 and 2026-11-16, and the writes and the probes on the later days. Every task exited 0 with no WRONG RESULT, and the tests pass, 180 here and 22 in the native module. A figure from another run names it. `report.md` holds every row.

### The corpora

A contract is stated at a thousand million and never binds. A sublimit at 100,000, a section at 300,000 and the root at a million do. Since a debit that an account on its path cannot cover is refused, and the stream draws on until it has its count, a corpus holds more credits than were drawn. Every report names a corpus by the share drawn and the share it holds.

| Corpus | Postings | Credits drawn | Debits refused | Credits | Credits held | Passes | Stored triples |
|---|---|---|---|---|---|---|---|
| one-level | 1,000 | 5% | 0 | 55 | 5.5% | 492 | 8,531 |
| one-level | 5,000 | 5% | 8,691 | 694 | 13.9% | 3,280 | 44,047 |
| one-level | 20,000 | 5% | 86,358 | 5,260 | 26.3% | 16,190 | 183,186 |
| one-level | 1,000 | 30% | 0 | 309 | 30.9% | 514 | 9,004 |
| one-level | 5,000 | 30% | 0 | 1,501 | 30.0% | 2,486 | 44,882 |
| one-level | 20,000 | 30% | 7,818 | 8,389 | 41.9% | 11,922 | 185,551 |
| two-level | 1,000 | 5% | 0 | 55 | 5.5% | 492 | 8,531 |
| two-level | 5,000 | 5% | 10,546 | 776 | 15.5% | 3,331 | 44,198 |
| two-level | 20,000 | 5% | 85,571 | 5,220 | 26.1% | 16,028 | 189,297 |
| two-level | 1,000 | 30% | 0 | 309 | 30.9% | 514 | 9,169 |
| two-level | 5,000 | 30% | 0 | 1,501 | 30.0% | 2,486 | 46,424 |
| two-level | 20,000 | 30% | 4,283 | 7,333 | 36.7% | 11,088 | 193,581 |

At 5% drawn the accounts drain by about posting 2,500, and from there most debits are refused, so the corpus drawn at 5% is one of 26% credits at 20,000 postings. It is measured as the corpus it is. A period is counted in passes, and a pass holds fewer postings where debits are refused, so the one-level corpus at 20,000 postings has 80 checkpoints at 5% drawn and 59 at 30%. A figure taken per period or per checkpoint depends on that.

### The variation

The three tasks that use request lists were run twice on the same code. The larger of the two runs over the smaller, by kind of figure, over every cell. A figure that moves by less than the greatest did not move.

| Figure | Median | 90th percentile | Greatest | Cells |
|---|---|---|---|---|
| cost of a write, Python | 1.03 | 1.08 | 1.20 | 54 |
| cost of a write, native | 1.07 | 1.17 | 1.26 | 36 |
| commits a second of the stress, Python | 1.02 | 1.04 | 1.04 | 8 |
| commits a second of the stress, native | 1.04 | 1.10 | 1.14 | 28 |
| lost races of the stress, Python and native | 1.07 and 1.11 | 1.07 and 1.17 | 1.27 and 1.29 | 3 and 18 |
| commits a second of one writer, Python and native | 1.07 and 1.08 | 1.22 and 1.19 | 1.40 and 1.44 | 39 and 26 |
| the guarded writers of the single-writer task, Python | 1.04 | 1.08 | 1.15 | 9 |
| the wait of a closed run, Python | 1.09 | 1.21 | 1.34 | 24 |

The reads were not repeated in a pair, since their task takes about two hours. Between the two days they were run, on the same corpora, the root reads over 20 ms ran 1.19 times as long on the later day in the median on rdflib (0.94 to 1.77), 1.15 on Jena through the kit (0.87 to 1.49) and 1.12 on Oxigraph (0.85 to 1.51). A read compared across days carries that. A ratio between two folds inside one run does not, and varies by up to 20%.

### The reads of the one-level corpus

Time per root read (ms) from the start of history, at 20,000 postings and 30% credits drawn, on 2026-11-13. The root accepts every kind, so all three folds count about the same rows. Native Jena is called from Java, and the test kit from Python through a JSON pipe, both with the `optional` form.

| Backend | plain | kind-filtered | stepwise |
|---|---|---|---|
| rdflib | 12,708 | 15,370 | 15,869 |
| Oxigraph (union) | 127 | 280 | 280 |
| Jena through the kit | 202 | 264 | 1,417 |
| Jena in memory, native | 50.5 | 77.9 | 150 |
| Jena TDB2, native | 112.9 | 140.8 | 228 |

Time of all 27 ancestor reads against the plain fold, the same corpus, on 2026-11-16.

| Backend | kind-filtered | stepwise |
|---|---|---|
| rdflib | 1.15 times | 1.20 times |
| Oxigraph | 2.32 | 5.94 |
| Jena through the kit | 1.21 | 5.72 |
| Jena in memory, native | 1.49 | 2.86 |
| Jena TDB2, native | 1.51 | 2.22 |

What the reads show.

1. **The kind filter costs a factor of 1.15 to 2.32 on every engine and caller.** It is a join for each posting, so it scales with the postings folded as the plain fold does. The balances equal the model's, including for the credits with no kind, so the filter does not trade correctness for this.
2. **The stepwise fold's cost is the ordered query and the transfer of its rows, never the loop.** The clamping loop takes about a millisecond for ten thousand rows on every caller. Through the kit's JSON pipe the stepwise fold costs 5.72 times the plain fold on Jena. Called natively from Java it costs 2.86 times in memory and 2.22 on TDB2, so the pipe is about half of the kit's figure. On Oxigraph the applied amount is joined by an `OPTIONAL` in the graph block, which reads like the `optional` form of the kind join, a scan of every such triple in the store (TSD-71), so the stepwise fold does not get cheaper from a checkpoint there. We did not check the plan, and a `union` form of the applied join is the thing to try.
3. **A checkpoint at each period close bounds every read, and its cost no longer grows with the history.** A checkpointed stepwise read costs 3% of the full read at 20,000 postings on rdflib, on Jena through the kit and on native Jena, and 0.89 on Oxigraph for the reason above. The checkpoint is read with one lookup by account in a graph named by the period, and its cost is inside these figures.
4. **Once a credit is clamped at the account it is drawn on and the ancestor folds the applied amount, the ancestor's own ceiling never binds.** An ancestor's outstanding draw is at least the sum of its contracts', each of which is not negative, and a filter that rejects a credit only enlarges it. The model counts the credits an ancestor's ceiling reduced and finds none on any corpus (`ancestor_clamps_binding` is 0, and `test_ck6b` holds it), so the stepwise balance equals the filtered sum of the applied amounts. The clamp that matters is the drawn contract's. At 20,000 postings the plain and the stepwise balances differ at 24 of 24 contracts at 30% drawn and at 15 of 24 at 5% drawn, and the stepwise balance differs from the filtered one at 9 of 9 ancestors and at 8 of 9. Reading the offered amounts, as plain and kind-filtered do, is therefore wrong wherever a contract was clamped, and that is the divergence the model expects and the check asserts. The ledger records the amount applied beside the amount offered (LG-Q23), so an ancestor folds the applied amounts in one aggregate.
5. **The shortcut pays only where its fallback is rare, and on these corpora it seldom is.** From the start of history nothing is outstanding and it falls back in every read. From a checkpoint it falls back in 3 of 27 reads at 5,000 postings and 10 of 27 at 20,000 at 5% drawn, and in 25 and 27 of 27 at 30%, since contracts are fully restored most of the time. Where it does not fall back it is one aggregate and a check. Where it does it costs the stepwise fold plus two aggregates. A sound condition that is cheap enough to pay for itself needs the outstanding amount of each contract, which only a checkpoint holds.
6. **The form of the kind join is specific to the engine.** Time of all ancestor reads against the plain fold with each form forced on every engine, at 5,000 postings and 30% credits, a corpus in which no debit is refused, on an Apple-silicon laptop on 2026-11-11:

   | Backend | optional | union |
   |---|---|---|
   | rdflib | 1.7 times | 6.6 times |
   | Oxigraph | 4.1 times | 2.1 times |
   | Jena through the kit | 1.4 times | 2.1 times |
   | Jena in memory, native | 1.3 times | 2.1 times |
   | Jena TDB2, native | 1.3 times | 2.5 times |

   On Oxigraph the `OPTIONAL` form behaves like a scan of every kind triple in the store, and on rdflib the `union` form scans every graph. We did not check either plan. A generated query for the kind filter should be chosen per engine and tested, as [ADR-A128](../../docs/architecture/decisions/ADR-A128-efficient-queries-and-shapes.md) asks of any generated query.

### The reads of the two-level corpus, and the cut

At 20,000 postings the two-level corpus holds 2,062 cuts in 5,220 credits at 5% drawn. The sum of applied amounts with no cuts, which is the postings part of the sum with cuts, differs from the stepwise balance wherever a cut was recorded, on the model and on each engine, and the sum with cuts and the stepwise fold equal the model at every ancestor in both modes.

The sum with cuts against the like-for-like read, `kind-filtered-union`, over all 27 ancestor reads at 20,000 postings and 30% credits drawn, on 2026-11-16. It is the cost the applied amount and the cuts add to the same query form.

| Backend | from the start of history | from the last checkpoint |
|---|---|---|
| rdflib | 1.01 | 1.12 |
| Oxigraph | 1.01 | 1.35 |
| Jena through the kit | 1.19 | 1.32 |

What the reads show.

1. **The cuts add 1 to 19 percent from the start of history and 12 to 35 percent from a checkpoint, once the query form is held.** A comparison of the sum with cuts against the kind-filtered fold in its own form would mix the cuts with the form, and no engine here explains a query, so the two cannot otherwise be told apart.
2. **The sum with cuts needs no ordered read and no loop**, so it does not pay the transfer of rows to the caller that the stepwise fold pays. Its postings aggregate uses no `OPTIONAL` inside a graph block and does not meet TSD-71's Oxigraph case.
3. **A cut that copies its position adds 1.84% to the store at 20,000 postings**, 197,141 triples against 193,581, and 1.1% at 5,000. It saves the join of a cut to its posting. The joined form is the default, and the copy's read has not been timed on these corpora.
4. **A ceiling above a stated amount changes no result.** In the ceiling variant the sum with cuts equals the stepwise balance at every ancestor in both modes on all three engines, the model finds accounts above their stated amount at a read point, and a read that clamps at the stated amount fails the check. Its counts and times are in the report.
5. **The sketch's figures hold through an engine as well as in the model.** Loaded into each engine as the benchmark's own quads, the aggregate reads 9 as the sum of applied amounts, 7 stepwise and 7 as the sum with cuts, with one cut of 2 at the aggregate, and the annual cap reads 9 by the kind-filtered, `kind-filtered-union`, stepwise and sum-with-cuts folds, on rdflib, Oxigraph and Jena. The plain fold reads the cap at 19, since it counts the reinstatement the cap does not accept. A writer that records no cut gives 9 where the model gives 7, which the check catches.

### What Jena's plans show

`mise run check:ledger-credit-kinds-jvm` writes what Jena will run for three reads of the root of the largest two-level corpus at 30% credits to `benchmark/ledger-credit-kinds-jvm/target/plans.txt` (git-ignored), for each store, as compiled, as optimised by ARQ, and for TDB2 in quad form and in the order TDB2's reordering gives each pattern.

* **The `VALUES ?g` graphs are the bound that works.** In all three queries ARQ turns the join of the VALUES table with the `GRAPH ?g` block into a `sequence`, so the pattern is evaluated once for each listed graph with `?g` bound. TDB2 keeps the same shape in quad form with `?g` as the first term of each quad. No graph outside the list is touched, which is why a checkpointed read, which lists few graphs, is cheap.
* **The filter on position does not bound a scan.** In every query the optimiser keeps `?pos` as a variable of the first triple of the pattern, `?p l:position ?pos`, and applies `FILTER(?pos <= N)` to the rows of that triple, so each listed graph is read for all its position triples and the bound only drops rows after them. In the OPTIONAL form it places the filter after that triple and moves the rest of the pattern behind it, so those are probed only for rows that pass. Nothing in the plan turns the bound into a range of an index. So a read costs the number of position triples in the graphs listed.
* **OPTIONAL against UNION.** The OPTIONAL form becomes `conditional`, one probe of `l:kind` for each row that passes the filter. The UNION form is three branches, each repeating the position triple and its filter, so the position triples of the listed graphs are scanned three times, and the third branch tests `NOT EXISTS` for each credit. The plan carries no cardinalities or costs, so it shows the work Jena is asked to do and not what it costs. The kind filter outside the graph block is applied to every row of both forms and is not part of the difference.
* **The cuts aggregate is driven by the cuts.** Its first triple has a constant object, `?c l:cutAt <urn:acct:root>`, so both stores start from the cuts at the account and join to `cutOf` and the posting's position. Its work is the cuts recorded at the account and not the postings. The position filter is again applied after the join.
* **TDB2's reordering changes nothing here.** The store's transformation, `ReorderFixed`, returned the patterns of all three queries in the order they were given. TDB2 has no statistics in this benchmark, so a reordering by selectivity was not possible.

What the output does not show. ARQ's execution log, which would show the plan as it ran and the order the in-memory engine chose, goes through SLF4J, which the module binds to a no-op logger, so it was not read, and the in-memory engine's plan is the optimised algebra alone. The TDB2 order is what the store's reordering transformation returns for a pattern, asked directly, and not the order read from a log of a run. No plan carries a row count or a time. Oxigraph and rdflib offer nothing to read.

### The probes

`mise run check:ledger-credit-kinds-probes`, 1,036 s, on 2026-11-16.

**The period length.** The plain root read from the start of history, on the one-level corpus at 20,000 postings and 5% credits drawn, with the period length at four values and the postings the same. Five reads after one warm-up, the median with the least and the greatest.

| Backend | Period passes | Period graphs | Rows folded | Median ms | Least | Greatest |
|---|---|---|---|---|---|---|
| rdflib | 100 | 969 | 20,000 | 59,000 | 56,163 | 65,822 |
| rdflib | 200 | 486 | 20,000 | 32,059 | 31,416 | 33,481 |
| rdflib | 320 | 306 | 20,000 | 20,708 | 20,346 | 20,959 |
| rdflib | 640 | 156 | 20,000 | 12,159 | 11,811 | 12,222 |
| Oxigraph | 100 | 969 | 20,000 | 343 | 302 | 346 |
| Oxigraph | 200 | 486 | 20,000 | 229 | 214 | 297 |
| Oxigraph | 320 | 306 | 20,000 | 214 | 211 | 221 |
| Oxigraph | 640 | 156 | 20,000 | 245 | 219 | 251 |

On rdflib the time follows the named graphs with the rows fixed, 61 ms a graph at 969, 66 at 486, 68 at 306 and 78 at 156, so most of a read is a cost for each graph it visits (TSD-75). Oxigraph stays within 214 to 343 ms and does not follow the graphs. rdflib is a test engine here, so the period length is not chosen for it.

**The cuts, repeated.** The sum with cuts against the kind-filtered read in the same form, on Jena through the kit, the two-level corpus at 20,000 postings and 5% credits drawn, each read 30 times after 5 warm-up reads, over the 27 ancestor reads and at the root.

| Read from | Of | kind-filtered median, least, greatest ms | sum with cuts median, least, greatest ms | Ratio of the medians |
|---|---|---|---|---|
| the start | 27 reads | 2,936, 2,671, 3,968 | 3,089, 2,896, 3,423 | 1.05 |
| the start | root | 326, 291, 369 | 341, 312, 403 | 1.05 |
| a checkpoint | 27 reads | 109.8, 86.5, 126.1 | 135.5, 112.3, 167.4 | 1.23 |
| a checkpoint | root | 5.45, 4.20, 7.15 | 6.98, 5.75, 10.11 | 1.28 |

A single read of a few milliseconds is not stable, and a ratio of two of them can read far from this.

## Writes, concurrent writers and late postings

`writes.py`, run by `mise run check:ledger-credit-kinds-writes` (`LEDGER_WRITES_QUICK=1` runs the smallest sizes, `LEDGER_WRITES_REPORT_DIR` writes `writes-report.md` and `writes-report.json` elsewhere, both git-ignored). It reuses the tree, the writer's arithmetic, the vocabulary, the quads and the reads of `check.py`, and adds no behaviour to it.

**The live writer.** For one posting against a store that holds history, the writer reads the ledger's revision and the balance of every account on the posting account's path (a sum with cuts from the last checkpoint, whose balances it reads once), settles the posting in the application with `settle_debit` and `settle_credit`, refuses a debit larger than the balance of any account on its path, and writes the posting, its applied amount, its kind, its cuts and the new revision in one SPARQL update request. It writes no checkpoint, so its reads fold every period after the last one the history holds, a tail that grows with every write. A contract has its own read, since `check.py` reads ancestors only.

**The request lists.** A list for a store preloaded with `n` postings continues the stream the preload came from (`writes.requests(preload, count, share, seed)`, drawn from `check.Stream.continued`), so one writer sent it in order refuses none. The lists of several threads differ by seed, each valid alone from the preload's balances.

**The guard.** One triple in the default graph holds the revision of the owner's ledger. The write is `DELETE { revision N } INSERT { revision N+1, and the posting and its cuts in the period graph } WHERE { revision N }` (PAT-21, PAT-04), and the committed revision N+1 is the posting's recorded position. SPARQL update returns no count, so the writer asks afterwards whether its own posting exists. The posting's IRI is unique to the writer and the attempt. A stale writer wrote nothing, reads again and retries. The unguarded writer sends `DELETE DATA { revision N } ; INSERT DATA { revision N+1, and the posting }` and does not confirm. One revision covers the owner's whole ledger, so any commit makes every other writer in flight stale. The benchmark reports the figures that bear on whether that is too coarse and does not decide it.

**What concurrent means here.** Threads in one process against one `pyoxigraph.Store`. It is not a test over HTTP, nor from several processes. pyoxigraph releases the GIL in a query and in an update: a thread counting in pure Python beside a thread running queries back to back ran at 0.98 of its speed alone, beside updates at 1.04, and beside a thread of pure Python at 0.48, on 8 CPUs, so the threads overlap in the engine. The fixed interleavings step two writers by hand, with no threads, and are the tests. The stress sends 1,000 further postings in all to a store holding 5,000, each retried until it commits or is refused as unavailable. After each run the committed records are read back in revision order and compared with a replay through `settle_debit` and `settle_credit`: every stored applied amount, every stored cut and every account's sum with cuts. Revisions must be dense and unique. A guarded run on the in-memory store that differs raises `WrongResult`. The on-disk store is audited and reported but not asserted, for the reason below.

**Late postings.** A late posting is stored in the period graph of its recorded position, with its effective position as one more triple, on every posting. A seeded `LATE_SHARE` of 5% of the postings, and a second run at 20%, are effective one to three periods (200 passes each) before they are recorded, never after (STD-294). The writer settled each in recorded order, so its applied amount and cuts were computed against every posting recorded before it. At each ancestor and read point four numbers are compared. Recorded is the sum with cuts over postings recorded by the point, and must equal the stepwise replay, in the model and through Oxigraph. Effective is the same amounts and cuts over postings effective by the point, folded from the start over every period graph (STD-278), and the engine must equal the model. Replay R is a fresh stepwise replay in recorded order of only the postings effective by the point, and replay E the same in effective order, ties by recorded order.

### What a write costs

One writer, 500 requests on a store of 20,000 postings, guarded, on 2026-11-16. It refuses none of the 500 and writes 297 debits and 203 credits. A debit reads 4 accounts in 8.1 queries. A refused request is a debit larger than the stated amount of the root, which every store refuses after reading its path, and each row averages 100 of them, read among the writes in step with them.

| Store, 20,000 postings | A written debit, total ms | Its reads and settle | A refused request, ms |
|---|---|---|---|
| Oxigraph in memory | 7.00 | 6.75 | 6.53 |
| Oxigraph on disk | 17.45 | 16.97 | 16.48 |
| Jena through the kit | 81.36 | 79.13 | 75.72 |
| native Jena in memory | 18.62 | 17.95 | 17.97 |
| native Jena on TDB2 | 29.81 | 16.17 | 15.36 |

Nearly all of a write's cost is its path reads. A refusal costs those reads and saves the update and its confirmation, which is under 1 ms in memory and 13 ms on TDB2, where a commit is made durable.

**The cost of a write is a mean over a tail.** The writer writes no checkpoint, so each write's reads fold every posting written since the last one, and a sample of fewer writes costs less a write. A refused request read after the 500 writes cost 1.4 to 1.5 times a written debit's reads, with the same queries. A writer that closes its periods would not carry that tail, and this benchmark does not measure one.

### Several writers

One thread of the stress refuses none of its 1,000 requests and writes 685 debits and 315 credits. At two threads or more a run still refuses, 13 to 18 of 1,000 at 2 threads, 54 to 65 at 4 and 57 to 86 at 8 on Oxigraph in memory. Each list is valid alone, and together they draw more than the accounts they share hold. The same lists sent one after another refuse 10, 63 and 66, and round robin 16, 52 and 61, so the refusals are the joint draw and not the order of interleaving. They are real, and a run reports them beside its lost races.

The best guarded writer commits 127 times a second on Oxigraph in memory, 47 on disk and 17 on Jena through the kit, and the guarded writers lose throughput as threads are added, to 41.6 a second at 8 threads on Oxigraph in memory. The unguarded writer's differences from the replay are not asserted and may be zero by luck in a run.

The fixed interleavings are the tests: two recoveries racing for the room at an aggregate (the stale writer's missing cut lands, and the aggregate's sum differs), two debits racing for the last availability of an aggregate (the second is refused on retry with the guard and overdraws it without), and a debit and a credit on different contracts under one aggregate (the guard made the second retry once, and the outcome equals the replay).

**The guard on the on-disk store.** In memory every guarded run is dense with no duplicate. On disk the guarded writers write duplicate positions, 24, 28 and 46 at 2, 4 and 8 threads. So the one revision triple closes the race in memory and not on disk, and the benchmark reports the disk figures without asserting them. The cause is the store and not the writer: Oxigraph 0.5.13 makes a second update wait in memory and not on disk, where two updates that read the same revision both commit, and one lock around the update call restores the guard (TSD-73).

### The four numbers of a late posting

9 ancestors at 3 points, 27 reads a row, at 5,000 postings, a size at which no debit is refused, on a laptop on 2026-11-12. The recorded sum equalled the replay and the model, and the effective sum equalled the model, in every row. With no late posting all four agreed.

| Late share | Late postings | Effective differs from R | From E | R from E | Largest difference, eff/R, eff/E, R/E | Effective sum below zero or above the ceiling | Effective read / recorded read |
|---|---|---|---|---|---|---|---|
| 5% | 257 | 7 | 26 | 26 | 3,780 / 4,938 / 2,935 | 4 | 1.29 |
| 20% | 974 | 9 | 26 | 26 | 3,630 / 6,892 / 6,892 | 2 | 1.29 |

Folding every period graph from the start costs 1.3 times the recorded fold from the start of history, whose cost grows with the point read.

What the write benchmark does not show. The writer writes no checkpoint, so a period close is not measured. The stress is threads in one process. The disk store is not asserted.

### The same writer on native Jena

`mise run check:ledger-credit-kinds-jvm-writes`, Jena 5.1.0 called from Java 25 with a 2 GB heap, threads in one JVM against one dataset, Jena in memory and TDB2 in a temporary directory. The writer is `writes.py`'s ported (the module `benchmark/ledger-credit-kinds-jvm`), with the same preloads and request lists. After each run the JVM exports the dataset and Python loads the export into an in-memory Oxigraph and runs `audit`, the replay of the commits in revision order, so the replay is the Python one. TDB2 makes every commit durable, so a TDB2 run takes smaller counts, 100 writes for the single writer and 200 requests for the stress.

**The probe of TSD-73 on Jena.** A counter triple. Each thread reads the counter N, sends `DELETE { N } INSERT { N+1 and its marker } WHERE { N }` as one update request in its own write transaction, and asks in a read transaction whether its marker exists, until the counter reaches the target. Then each thread increments in the store (`DELETE { ?n } INSERT { ?m } WHERE { ... BIND(?n + 1 AS ?m) }`). Three runs a cell at 2, 4 and 8 threads, one at 1. It reads no corpus. The table is of a laptop run on 2026-11-12.

| Store | Threads | Markers confirmed, of the target, 3 runs | Revisions with more than one marker | Lost races, 3 runs | Increment final, of threads times the count | Counter triples left |
|---|---|---|---|---|---|---|
| memory, target 1,000 | 1 | 1,000 | 0 | 0 | 500 of 500 | 1 |
| memory | 2 | 1,000, 1,000, 1,000 | 0, 0, 0 | 997, 999, 998 | 1,000 of 1,000 in every run | 1 |
| memory | 4 | 1,000, 1,000, 1,000 | 0, 0, 0 | 2,904, 2,979, 2,958 | 2,000 of 2,000 | 1 |
| memory | 8 | 1,000, 1,000, 1,000 | 0, 0, 0 | 6,778, 6,574, 6,850 | 4,000 of 4,000 | 1 |
| TDB2, target 100 | 1 | 100 | 0 | 0 | 50 of 50 | 1 |
| TDB2 | 2 | 100, 100, 100 | 0, 0, 0 | 100, 100, 100 | 100 of 100 | 1 |
| TDB2 | 4 | 100, 100, 100 | 0, 0, 0 | 300, 300, 300 | 200 of 200 | 1 |
| TDB2 | 8 | 100, 100, 100 | 0, 0, 0 | 700, 700, 700 | 400 of 400 | 1 |

On both Jena stores, in all 20 guarded runs, every revision carries one marker, the confirmed markers are the target, and the in-store increment ends at threads times the count as one triple. A second update does wait for the first and runs its `WHERE` on the first's result. A lost race is a guarded update that found the counter already moved and wrote nothing, and its thread read again. TDB2 loses exactly threads less one races a revision at 2, 4 and 8, as writers queued behind a lock would. A thread dump taken during an exploratory run, not part of the report, showed the TDB2 threads parked in `TransactionCoordinator.acquireWriterLock`, a fair semaphore, with one thread committing. This differs from Oxigraph on disk (TSD-73), where the same probe confirmed 1,300 to 1,600 markers of 1,000, and agrees with Oxigraph in memory. So the guard is safe on Jena in memory and on TDB2 called in process (TSD-74). The probe is reported and not asserted, and what it decides is only whether the guarded runs of the store are held to the replay. Both are.

**The native writes.** The cost of a write and of a refused request are in the table above. The single writer refuses none, of 500 in memory and of 100 on TDB2, where it writes 60 debits and 40 credits. The stress with one thread refuses none, and at 2, 4 and 8 threads a guarded run in memory refuses 15, 53 and 61, the joint draw again. Every single-writer export, guarded and unguarded, equals the replay, and no guarded run has a duplicate position.

What the native writes do not show. They are threads in one JVM, not several processes or HTTP. TDB2 ran at a fifth to a tenth of the in-memory counts.

## One writer per ledger, and the readings of a late posting

**`single_writer.py`**, run by `mise run check:ledger-credit-kinds-single-writer`. The guarded writers above each read their path, write under the guard and try again when they lose a race. Here producers hand their requests to one writer through a queue. It uses the stores, preloads and request lists of the stress, and runs the guarded writers again beside it so both are measured on one machine.

| Writer | What it does for a posting |
|---|---|
| reads | reads the revision and the balance of every account on the path, settles, writes one guarded update and confirms it, as `writes.Live` does |
| keeps | settles from balances it read once and has kept since, writes one update and confirms it. It is right only while it is the ledger's one writer |
| keeps, in batches | settles several postings from the balances kept and writes them in one update that moves the revision by their number |

A closed run has 1, 2, 4 and 8 producers that each wait for their answer, and gives the time a request waits. A backlog run queues every request before the writer starts, and gives the writer's rate, which the report also states as postings a second and a day at 70% of it. Every run is held to the replay of its commits on every store, the on-disk one included, since nothing races a single writer. The native Jena run, in memory and on TDB2, is part of `check:ledger-credit-kinds-jvm-writes`.

**`late_readings.py`**, run by `mise run check:ledger-credit-kinds-late-readings`, for LG-Q26. On the late corpus of `writes.py` it reads a balance for a day as known at a recording, three ways at every ancestor.

| Reading | What it is | Read |
|---|---|---|
| A | the recorded amounts of the postings effective by the day and recorded by the recording | a sum, from the start of history or from the checkpoint at the close before the day |
| B | the same postings settled again in effective order, each debit charged in full | an ordered read of the account's subtree folded by the caller, always from the start |
| C | no balance, the debits and the credits offered | two sums, from the start, or since the close before the day |

It checks that each engine read equals the model, that a store holding only what was recorded by then reads the same as the whole store, that A at a day's own recording is the ledger's balance, and that with no late posting A and B agree. It counts the readings that lie below zero or above the ceiling, the heads at which B differs from the ledger, and how far a figure as known at the recording has moved by the end of history. It times each read, and reading A by the age of the day. The checkpointed read of A rests on STD-294: nothing is effective after it is recorded, so everything recorded by a close is effective by any later day.

The ledger's own reading B settles a debit that no longer fits by its account's policy, refused where the account refuses and cut where it rations (STD-336). This benchmark's B charges it in full and does not yet do that, so a B reading below zero here is one the ledger's reading would not show.

### Measured results, one writer per ledger

On 2026-11-16, 1,000 requests, with every run equal to the replay of its commits on every store, the on-disk Oxigraph store included.

| Store | One writer that reads its path, commits a second | The best guarded writer | The writer that keeps its balances, against the best guarded | With batches of 100 |
|---|---|---|---|---|
| Oxigraph in memory | 124 | 127 | 55.9 times | 138.5 times |
| Oxigraph on disk | 43 | 47 | 75.1 times | 170.0 times |
| Jena through the kit | 16 | 17 | 24.6 times | 122.7 times |

On native Jena, one writer that reads its path with 8 producers commits 68 times a second in memory and 40 on TDB2, against 41 and 21 for 8 guarded threads. The keeper in a backlog commits 2,194 a second in memory and 83 on TDB2, and 5,008 and 1,745 with batches of 100.

What the figures show. A single writer that reads its path matches the best guarded writer on each store and does not lose throughput as producers are added, where the guarded writers do, and on disk lose writes (TSD-73). A writer that keeps its balances is 25 to 75 times the guarded rate, and batching raises it to 123 to 170 times. One writer fed by 8 producers refuses 61 of 1,000, the joint draw of their lists. The keeper is right only while it is the ledger's one writer. The run does not test a second writer behind it (that is `test_sw4`), and it does not measure a restart that reloads the balances.

### Measured results, the readings of a late posting

The late corpus at 5,000 and 20,000 postings, at 0%, 5% and 20% late, a day as known at a recording at each of the 9 ancestors. The 5,000 rows are of 2026-11-12, a size at which no debit is refused, and the 20,000 rows of 2026-11-13.

| Postings | Late share | Readings | A below zero or above the ceiling | B the same | Heads | B differs from the ledger at the head |
|---|---|---|---|---|---|---|
| 5,000 | 0% | 72 | 0 | 0 | 27 | 0 |
| 5,000 | 5% | 72 | 2 | 0 | 27 | 23 |
| 5,000 | 20% | 72 | 3 | 0 | 27 | 25 |
| 20,000 | 0% | 81 | 0 | 0 | 27 | 0 |
| 20,000 | 5% | 81 | 6 | 4 | 27 | 20 |
| 20,000 | 20% | 81 | 9 | 3 | 27 | 22 |

Mean milliseconds a read at 5,000 postings:

| Late share | Recorded | A from the start | A from the close | C from the start | C since the close | B |
|---|---|---|---|---|---|---|
| 5% | 1.54 | 8.10 | 1.56 | 7.43 | 1.21 | 14.20 |
| 20% | 1.50 | 8.29 | 1.61 | 7.52 | 1.22 | 14.43 |

At 20,000 postings reading A costs 1.7 ms from the close and 30 ms from the start, B 50 ms, and the flows since the close 1.2 ms.

How far a figure as known at the recording has moved by the end of history, at 5,000 postings and 20% late: A moved in 45 readings by up to 11,443 (mean 1,397), B in 41 by up to 11,713 (mean 1,269), the debits in 45 by up to 28,997 and the amounts offered in 42 by up to 42,221.

What the figures show. Every read equals the model, a store holding only what was recorded by the recording reads the same as the whole store, and with no late posting A and B agree and no reading lies outside its range. With late postings B differs from the ledger's balance at 20 to 25 of the 27 heads, so B is not the balance the ledger recorded. A at a head equals it by construction. A read from the checkpoint at the close costs about what the recorded balance costs, and its cost grows with the size of history only when read from the start. B costs about twice A from the start. C since the close, which a checkpoint carrying the two totals completes, costs 1.2 ms.

**Why B can fall below zero.** It does so at one account, `urn:acct:sec0`, 4 times of 81 with 5% late and 3 times with 20%. In the smallest such reading, as known at recording 5,547 for the day 5,000, the first posting that takes the account below zero in effective order is a debit of 345 recorded and effective at position 2,924, so it is not late itself. In recorded order, the writer's own, the account stood at 2,084 before it and the writer accepted it. In effective order the account stands at 90 before it and falls to minus 255, because 12 postings recorded after it are effective before it, 6 of them debits that sum to 1,391, and take their room first. Of the difference of 1,994, 603 was not traced, and the likeliest reason is credits that apply differently when settled again. So a debit the writer accepted can overdraw when the same postings are settled in effective order, with no late debit of its own.

## What this does not measure

Not measured: a query plan from the Python callers, since none of them can explain a query (the Java caller's plans are above, for Jena only and without a run-time explanation), a ceiling that moves in time, a checkpoint written by the fold rather than by the model's arithmetic, a `union` form of the applied join on Oxigraph, and a native caller on a store other than Jena. The ceiling variant is read at 30% credits only and without the plain fold or the shortcut. The Java caller does not read the ceiling variant, the cut forms or the shortcut on the two-level corpus. The event stream is seeded and the engines see the same one, so a figure compares folds on one engine and caller, and an engine against another only in its shape. The Java caller runs the reads of a corpus once each, in one JVM after a warm-up on the smallest corpus, so its smallest sizes include some JIT warm-up. The write benchmark does not measure writes over HTTP or from more than one process, a store other than Oxigraph and Jena under concurrent writers, a writer that writes the checkpoint at a period close, a guard narrower than the owner's whole ledger, a posting effective inside a sealed period as a decision, a reading B that settles a debit by its account's policy (STD-336), a corpus wide enough to hold a low share of credits at 20,000 postings, the space a refusal's own record takes, or any rule that consumes an amount in effective order. The native writes are threads in one JVM, on Jena TDB2 at smaller counts than the in-memory runs because every TDB2 commit is made durable.

## Files

| File | What it is |
|---|---|
| `check.py` | the tree, the streams, the model, the checkpoints, the four reads and the sum with cuts on three backends, the like-for-like reads, the cut forms, the ceiling variant, the sketch's tree, the pass criterion, the report, and `--emit` and `--merge` for the native Jena caller (both corpora) |
| `test_check.py` | the check's own tests |
| `writes.py` | the live writer, its guard, the fixed interleavings, the stress, the GIL probe, the late postings and their four numbers, and the report (`writes-report.md`, `writes-report.json`), and `--emit-jvm` and `--audit-jvm` for the native Jena writer |
| `test_writes.py` | the write benchmark's own tests |
| `single_writer.py`, `test_single_writer.py` | one writer per ledger fed through a queue, against the guarded writers, and its tests |
| `late_readings.py`, `test_late_readings.py` | the readings of a balance by effective day as known at a recording, and its tests |
| `probes.py`, `test_probes.py` | the period-length probe and the repeated read of the cuts, run by `mise run check:ledger-credit-kinds-probes`, and their tests |
| `conftest.py` | makes a temporary folder refuse removal while a store in it is open |
| `report.md`, `report.json`, `writes-report.md`, `writes-report.json`, `single-writer-report.*`, `late-readings-report.*` | the last runs' results, generated and git-ignored |
