<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Ledger credit kinds

A benchmark under [ADR-A124](../../docs/architecture/decisions/ADR-A124-benchmark-root.md). It measures what a credit's kind and a stepwise credit ceiling add to the read of an ancestor's balance, on every engine the repository runs SPARQL on, before the ledger builds them. A cost measured on one engine is a hypothesis for another ([STD-176](../../docs/developer/standards.md)), so each read runs on rdflib in memory, Oxigraph on disk and Jena ARQ in memory.

Under the ledger's agreed design a draw or credit is posted once, at the account it names, and an ancestor's balance is a fold over its subtree's postings in the current period's named graph. The decision on LG-Q10 adds a kind to a credit posting, a concept IRI from a scheme, and each account declares which kinds restore it, all kinds by default. A ceiling is already part of the design, since a credit never lifts an account above its stated amount (law LD3), and where it can bind at an ancestor the fold has to be a running balance applied posting by posting.

## What it does

The tree has depth 4: a root, 2 sections, 3 sublimits to a section and 4 contracts to a sublimit, so 33 accounts. The first section is a cap and accepts recoveries only, and every other account accepts all kinds. Each account's ceiling is its stated amount. Postings come in passes of one to three (a pass position, then a micro-position in the pass) on random contracts, and each goes into a named graph keyed by its sublimit and its period of 200 passes. A credit is a recovery, a reinstatement or a write-back, in equal shares, under `https://example.org/`, except that a quarter of the credits on a path where no account restricts kinds (everything under the second section) carry no kind. Credits are larger than debits, so at 30% credits a ceiling binds often and at 5% it seldom does.

A credit is clamped at the contract it is posted to, which it never lifts above its stated amount (law LD3), and the amount applied there is stored on the credit (`l:applied`). What an ancestor folds is the credit as applied at its drawn contract, clamped again at the ancestor's own ceiling. A posting is 8 triples, and a credit has one more for what was applied and, if it has a kind, one for the kind.

At each period close a checkpoint is written as data, in the graph `urn:graph:checkpoint:<period>`. It holds, for each of the 33 accounts, the balance by each of the three folds (5 triples per account), so the filter and the clamp are already reflected in the balances of the second and third. A checkpointed read starts from the last checkpoint at or before the point and folds only the period graphs after it.

Every ancestor (6 sublimits, 2 sections, the root) is read at three pass positions, none on a period end, by each of four reads, from the start of history and from the checkpoint.

* **plain** is the stated amount plus the signed sum of every posting's offered amount in the subtree up to the point. It is today's design and the baseline.
* **kind-filtered** counts a credit only if the ancestor accepts its kind, by a join to the credit's kind, in one SPARQL aggregate.
* **stepwise** is an ordered SELECT of the accepted postings (`ORDER BY ?pos ?mp`, with the applied amount) folded by the caller, each credit clamped at the ceiling. Its time is split into the ordered query with the transfer of its rows, and the loop. The Java caller also splits the query from the transfer.
* **shortcut** is the kind-filtered aggregate from the stepwise checkpoint, then a check, and the stepwise fold only where the check fails. The check is that the balance is within the ceiling and that every contract under the ancestor was offered, over the folded range and in credits of any kind, no more than it had outstanding at the range's start (its stated amount less its stepwise checkpoint balance, and nothing outstanding from the start of history). A credit is clamped at its drawn contract only where it exceeds what is outstanding there, and debits only add to the outstanding amount, so the condition rules out a clamp at any contract in the range. The applied amounts are then the offered ones the aggregate summed, and the ancestor cannot be lifted above its ceiling because its outstanding draw is at least its contracts' together. The condition is sufficient and not necessary, so a failed check does not mean a clamp happened. It costs a second, grouped aggregate over the same range.

The join to the credit's kind has two forms. `optional` is an `OPTIONAL { ?p l:kind ?k }` in the graph block. `union` is `{ ?p l:direction l:Debit } UNION { ?p l:kind ?k } UNION { ?p l:direction l:Credit . FILTER NOT EXISTS { ?p l:kind ?z } }`, and its third branch keeps a credit that has no kind, which would otherwise match neither of the first two and drop out of the fold. The first version of this benchmark had only two branches and every credit had a kind, so it did not see that. Their cost differs by engine (below), so each backend reads the form that is cheaper on it, rdflib and Jena `optional` and Oxigraph `union`, and `LEDGER_KINDS_FORM=optional|union` forces one on all three. The report's `kind join` column says which was read.

## What it tests

| Claim | Test |
|---|---|
| An ancestor's kind-filtered fold counts a credit only if the account accepts its kind, keeps a credit with no kind where every account accepts all kinds, and equals the plain fold where the account accepts every kind | every ancestor at every point, against the model, on each backend and each form of the join |
| The stepwise fold folds the credit as applied at its drawn contract, which a plain sum cannot | the same, at 30% credits, where the model has a clamp bind at 24 of 24 contracts |
| A checkpoint holds the balance by each fold, including the filter and the clamp | every checkpointed read against the model's balance and posting count |
| The shortcut gives the stepwise balance, and falls back where its check fails | every shortcut read against the model's stepwise balance, and the rate of falling back |
| The filter, the clamp and the checkpoints are not the cost of a different design from the plain fold | time per read and postings folded per read, each read against the plain fold, on each backend and size |
| The cost is not one engine's or one caller's | the same corpus and the same balances on three engines through Python, and on Jena in memory and on TDB2 called from Java ([benchmark/ledger-credit-kinds-jvm](../ledger-credit-kinds-jvm/README.md)) |

## Pass criterion

Every read on every backend, from the start of history and from the checkpoint, equals the model's balance for that fold, ancestor and read point and counts the postings the model counts, and every shortcut read equals the model's stepwise balance. The folds therefore differ from each other exactly where the model says, and the report records where it expects it (`model_expects` in `report.json`: the contracts where a clamp binds, the ancestors where the stepwise and the plain or filtered balances differ, the credits with no kind). The stored triples, checkpoints included, have the count the arithmetic gives. The model must itself tell the folds apart, or the corpus is refused: the cap's plain and kind-filtered balances differ, a credit with no kind exists, and at 30% credits a clamp binds at a contract and reaches an ancestor. **A wrong balance, posting count or stored count fails the run. Time never does.** `test_check.py` shows the check fails on a balance off by one, on a filter that ignores the kind, on a join that drops a credit with no kind, on a missing clamp at the drawn contract, on a wrong checkpoint, on a shortcut that skips a needed fallback and on a stored count, that it does not fail on time, that the run leaves no store open, that each form of the join gives the model's balances, and that the emitted corpus matches the model ([PRI-63](../../docs/developer/principles.md)).

## Run it

```bash
mise run check:ledger-credit-kinds
```

```bash
LEDGER_KINDS_QUICK=1 mise run check:ledger-credit-kinds
```

The sizes are 1,000, 5,000 and 20,000 postings at 5% and 30% credits. `LEDGER_KINDS_MAX` caps the postings and `LEDGER_KINDS_QUICK=1` runs the smallest size. `LEDGER_KINDS_REPORT_DIR` writes the report elsewhere. The full run took about 14.5 minutes on the laptop below, most of it rdflib at 20,000 postings, where each of the four reads from the start of history takes 2 to 2.5 minutes a run. Jena needs the test kit jar, built on first use by `mise run bootstrap:sparql-testkit` ([ADR-A125](../../docs/architecture/decisions/ADR-A125-test-support-tooling.md)). Where there is no `java` or no jar, the Jena runs are left out and the report's environment says so. `report.md` and `report.json` are generated, git-ignored and written here, with the native Jena caller's timings merged in by `mise run check:ledger-credit-kinds-jvm`. The Oxigraph store is a temporary directory, removed when the run ends, including on failure.

## Measured results

Run of 2026-11-11 on an Apple-silicon laptop with 8 GB, Python 3.14.7, rdflib 7.6.0, pyoxigraph 0.5.13 and Jena ARQ 5.1.0, read at runtime from the jar the test kit's JVM runs and from the jar the native caller's JVM loads (Java 25, heap capped at 2 GB). "Rows" is the postings the read counted or, for stepwise, transferred. Times are the mean of 3 read points, at the root. The 5% rows are in `report.md`.

Time per root read (ms) from the start of history, 30% credits. The root accepts every kind, so all three folds count about the same rows. Native Jena is called from Java, the test kit is called from Python through a JSON pipe, both with the `optional` form.

| Backend | Postings | plain | kind-filtered | stepwise | of which query and transfer | of which loop |
|---|---|---|---|---|---|---|
| rdflib | 1,000 / 5,000 / 20,000 | 64 / 377 / 4,611 | 117 / 624 / 5,611 | 124 / 661 / 5,808 | 123 / 660 / 5,805 | 0.05 / 0.25 / 1.05 |
| Oxigraph (union) | 1,000 / 5,000 / 20,000 | 4.6 / 22.4 / 89.7 | 9.3 / 46.8 / 189 | 8.9 / 44.5 / 187 | 8.8 / 44.1 / 185 | 0.05 / 0.23 / 0.94 |
| Jena through the kit | 1,000 / 5,000 / 20,000 | 7.4 / 34.4 / 144 | 9.9 / 48.4 / 192 | 37.9 / 193 / 791 | 37.7 / 192 / 789 | 0.05 / 0.23 / 0.96 |
| Jena in memory, native | 1,000 / 5,000 / 20,000 | 2.3 / 7.4 / 37.0 | 4.9 / 10.6 / 49.4 | 5.9 / 22.3 / 96.5 | 5.8 / 22.2 / 96.3 | 0.00 / 0.01 / 0.02 |
| Jena TDB2, native | 1,000 / 5,000 / 20,000 | 4.6 / 22.2 / 89.9 | 4.6 / 21.1 / 89.7 | 6.2 / 31.5 / 150 | 6.1 / 31.3 / 150 | 0.00 / 0.01 / 0.02 |

Time of all 27 ancestor reads from the start of history against the plain fold, at 30% credits (5% in `report.md`).

| Backend | Postings | kind-filtered | stepwise |
|---|---|---|---|
| rdflib | 1,000 / 5,000 / 20,000 | 1.8 / 1.7 / 1.2 times | 1.8 / 1.8 / 1.3 times |
| Oxigraph | 1,000 / 5,000 / 20,000 | 2.0 / 2.1 / 2.1 times | 4.7 / 5.1 / 5.2 times |
| Jena through the kit | 1,000 / 5,000 / 20,000 | 1.3 / 1.4 / 1.4 times | 4.4 / 5.3 / 5.3 times |
| Jena in memory, native | 1,000 / 5,000 / 20,000 | 1.5 / 1.3 / 1.4 times | 1.9 / 2.4 / 2.6 times |
| Jena TDB2, native | 1,000 / 5,000 / 20,000 | 1.3 / 1.3 / 1.4 times | 1.7 / 1.8 / 2.0 times |

Checkpointed reads. The time of all 27 reads from the last checkpoint against the same reads from the start of history, at 20,000 postings and 30% credits, with the root's mean rows folded.

| Backend | plain | kind-filtered | stepwise | root rows, full / checkpointed |
|---|---|---|---|---|
| rdflib | 0.04 | 0.04 | 0.04 | 11,358 / 244 |
| Oxigraph | 0.03 | 0.03 | 0.92 | 11,358 / 244 |
| Jena through the kit | 0.05 | 0.03 | 0.02 | 11,358 / 244 |
| Jena in memory, native | 0.05 | 0.04 | 0.03 | 11,358 / 244 |
| Jena TDB2, native | 0.04 | 0.03 | 0.03 | 11,358 / 244 |

The shortcut. Fallbacks in the 27 reads of a run, read from the start of history and from the checkpoint, and the total time of the shortcut against the stepwise fold read the same way. At 1,000 postings 9 of the 27 checkpointed reads are at a point before the first close, so they cannot use a checkpoint.

| Credits | Postings | From the start | From the checkpoint |
|---|---|---|---|
| 5% | 1,000 / 5,000 / 20,000 | 27 / 27 / 27 of 27 | 9 / 0 / 0 of 27 |
| 30% | 1,000 / 5,000 / 20,000 | 27 / 27 / 27 of 27 | 26 / 25 / 18 of 27 |

| Backend (checkpointed, 20,000 postings) | shortcut s, 5% | stepwise s, 5% | shortcut s, 30% | stepwise s, 30% |
|---|---|---|---|---|
| rdflib | 3.41 | 1.71 | 5.26 | 1.98 |
| Oxigraph | 0.03 | 3.43 | 3.24 | 3.80 |
| Jena through the kit | 0.08 | 0.05 | 1.33 | 0.16 |
| Jena in memory, native | 0.02 | 0.01 | 0.05 | 0.02 |
| Jena TDB2, native | 0.03 | 0.01 | 0.07 | 0.03 |

The stored triples are 8,531 / 42,533 / 170,205 at 5% credits and 9,004 / 44,882 / 179,471 at 30%, the same on all three Python engines and in the native Jena store. Of these, 5 x 33 per close are the checkpoints (330 at 1,000 postings and 8,250 at 20,000).

What the run shows.

1. **The kind filter costs a factor of 1.2 to 2.1 on every engine and caller, and the factor does not grow with the history.** It is a per-posting join, so it scales with the postings folded as the plain fold does. The balances equal the model's, including for the credits with no kind, so the filter does not trade correctness for this.
2. **The stepwise fold's cost is the ordered query and the transfer, never the loop.** The clamping loop is 1 ms or less at 11,358 rows on every caller. Through the kit's JSON pipe the stepwise fold costs 4.4 to 5.3 times the plain fold on Jena. Called natively from Java it costs 1.9 to 2.6 times on Jena in memory and 1.7 to 2.0 times on TDB2, and the transfer of the rows into Java arrays is 2 to 3 ms of 96 to 150 ms, the rest being the engine's ordered query. LG-14 reported 3.4 to 4.9 times through the kit at 30% credits. Its folds read the offered amount, and this run's stepwise read also joins the applied amount, so the kit's figure measured now is 4.4 to 5.3 times, and the pipe accounts for about half of it. On rdflib and Oxigraph the rows are Python objects in-process or a native iterator, and the stepwise fold costs about the kind-filtered fold plus the applied join, 1.3 to 1.8 times plain on rdflib and 4.7 to 5.2 on Oxigraph. On Oxigraph the applied join, an `OPTIONAL` in the graph block, reads like the `optional` form of the kind join, a scan of every such triple in the store, so the stepwise fold does not get cheaper from a checkpoint there (0.92) while the aggregates do (0.03). We did not check the plan, and a `union` form of the applied join is the thing to try.
3. **A checkpoint at each period close bounds every read, and the cost no longer grows with the history.** At 20,000 postings a root read folds 244 rows instead of 11,358 (52 at 5% credits) and costs 2 to 6 percent of the full read on every engine and caller, except the stepwise read on Oxigraph, which pays for its applied join as above. Native Jena at 20,000 postings reads the root in 0.7 to 4.3 ms. The checkpoint is read with one lookup by account in a graph named by the period, and its cost is inside these figures.
4. **Once a credit is clamped at the account it is drawn on and the ancestor folds the applied amount, the ancestor's own ceiling never binds.** An ancestor's outstanding draw is at least the sum of its contracts', each of which is not negative, and a filter that rejects a credit only enlarges it. The model counts the credits an ancestor's ceiling reduced and finds none at either share (`ancestor_clamps_binding` is 0, and `test_ck6b` holds it), so the stepwise balance equals the filtered sum of the applied amounts. The clamp that matters is the drawn contract's. The plain and the stepwise balances differ at 24 of 24 contracts at 30% credits (2 of 24 at 5%), and the stepwise balance differs from the filtered one at 9 of 9 ancestors at 30% (4 of 9 at 5%). Reading the offered amounts, as plain and kind-filtered do, is therefore wrong wherever a contract was clamped, and that is the divergence the model expects and the check asserts. The ancestor's clamp in the loop is kept as the law and costs nothing, but a design that stores the applied amount on the credit does not need the loop's ceiling, and could fold the applied amounts in one aggregate. The ledger has to decide whether it stores `applied` or recomputes it.
5. **The shortcut pays only where its fallback is rare and the stepwise fold is dear.** Its check holds for every read from a checkpoint at 5% credits at 5,000 and 20,000 postings and for none from the start of history, where nothing is outstanding. At 30% credits contracts are fully restored most of the time, so it falls back in 18 to 26 of 27 reads from a checkpoint. When it does not fall back it is the fastest read there is, 0.03 s against 3.43 s for the stepwise fold on Oxigraph over a run. Where the stepwise fold is cheap (native Jena, rdflib) the shortcut costs 1.4 to 2.7 times it, for the second grouped aggregate, and where it falls back it costs the stepwise fold plus two aggregates. A sound condition that is cheap enough to pay for itself needs the per-contract outstanding amounts, which only a checkpoint holds, so it is a shortcut for the first read after a close at a low credit share, not for a high one.
6. **The form of the kind join is engine-specific, and the correction did not change which is cheaper.** The union form now has a third branch for a credit with no kind. Time of all ancestor reads against the plain fold at 5,000 postings and 30% credits, with each form forced on every engine:

   | Backend | optional | union |
   |---|---|---|
   | rdflib | 1.7 times | 6.6 times |
   | Oxigraph | 4.1 times | 2.1 times |
   | Jena through the kit | 1.4 times | 2.1 times |
   | Jena in memory, native | 1.3 times | 2.1 times |
   | Jena TDB2, native | 1.3 times | 2.5 times |

   The two-branch union gave 1.7 on Oxigraph and 1.6 on Jena (LG-14, at 20,000), so the third branch costs about 0.2 to 0.4 of the plain fold's time and does not change the ranking. On Oxigraph the `OPTIONAL` form behaves like a scan of every kind triple in the store, and on rdflib the `union` form scans every graph. We did not check either plan. A generated query for the kind filter should be chosen per engine and tested, as [ADR-A128](../../docs/architecture/decisions/ADR-A128-efficient-queries-and-shapes.md) asks of any generated query.

## What this does not measure

A ceiling that moves in time. Reads of a contract, which the account's own postings answer. A checkpoint written by the fold rather than by the model's arithmetic, and the cost of writing one, since the checkpoints are loaded with the history. Concurrent writers and late postings. A `union` form of the applied join on Oxigraph. A native caller on a store other than Jena. The event stream is seeded and the engines see the same one, so a figure compares folds on one engine and caller, and an engine against another only in its shape. The Java caller runs the reads of a corpus once each, in one JVM after a warm-up on the smallest corpus, so its smallest sizes include some JIT warm-up.

## Files

| File | What it is |
|---|---|
| `check.py` | the tree, the stream, the model, the checkpoints, the four reads on three backends, the pass criterion, the report, and `--emit` and `--merge` for the native Jena caller |
| `test_check.py` | the check's own tests |
| `conftest.py` | makes a temporary folder refuse removal while a store in it is open |
| `report.md`, `report.json` | the last run's results, generated and git-ignored |
