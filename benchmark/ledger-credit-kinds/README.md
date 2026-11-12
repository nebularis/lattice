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

## Credits at two levels of a path, and the cut

LG-15 posted every credit on a contract, and there no ancestor's ceiling bound. A credit posted at an ancestor restores that ancestor and not the accounts below it, so a later credit below can push the ancestor past its ceiling (section 4.8 of the sketch on balances under post-once). The second corpus, `two-level`, has the same passes, debits, contracts, amounts and kinds as the first (`stream_two_level`), but `UPPER_SHARE`, one half, of the credits are posted at a sublimit or a section on the drawn contract's path instead of at the contract, chosen at random among the accounts there that accept the credit's kind. A credit posted at an internal account X is clamped at X, changes no account below X, and folds upward from X.

Where a credit lives. A credit at a sublimit goes in that sublimit's own period graph, shared with the postings of its contracts. A credit at a section goes in a period graph keyed by the section. An account reads the graphs keyed by every sublimit and section in its subtree, itself included, so a section's credit is read by that section and the root and by no sublimit, and a sublimit's credit by the sublimit, its section and the root. No account reads a graph outside its own subtree.

The writer holds the stepwise balance of every account. It applies a credit at its posting account up to that account's room, then each accepting ancestor takes the lesser of the applied amount and its own room, stepwise, and where it takes less the difference is a **cut** at that ancestor. A cut is stored with the credit in the credit's own graph as 3 triples, a cut node naming its posting (`l:cutOf`), the ancestor it is at (`l:cutAt`) and its value (`l:cutValue`). A cut has no position of its own, so a read joins it to its posting for the position bound, in the same graph. We chose 3 triples over 4 with a copy of the position, which would save that join and cost a triple per cut, and we did not measure the 4-triple form. A cut is recorded only at an ancestor that accepts the credit, so the read of cuts needs no kind filter.

**sum-with-cuts** is an ancestor's balance as the stated amount (or the checkpoint's balance), plus the debits in its subtree, plus the credits it accepts at the amount applied, less the cuts recorded at it. It is two aggregates, one over the postings and one over the cuts, whose times are reported apart. The postings aggregate is a `UNION` of three branches inside the graph block, a debit, a credit with a kind and a credit with no kind, with no `OPTIONAL` there, since an `OPTIONAL` inside `GRAPH ?g` reads every graph on Oxigraph 0.5.13 (TSD-71) and the applied amount is absent on a debit. The account's kind filter is outside the graph block, where its declarations are in the default graph. One form is used on all three engines. The postings aggregate alone is the kind-filtered sum of applied amounts with no cuts, which the check reads as well and compares with the model's.

## Like-for-like read forms, a cut that copies its position, and a ceiling above a stated amount

LG-16 compared the sum with cuts, which reads postings with a three-branch `UNION`, against the kind-filtered fold, which joins the kind by `OPTIONAL` or by its own `UNION`. Its ratios mixed the cost of the cuts with the cost of the query form. LG-17 closes three things it left open, and tests the sketch's own tree in an engine.

**Like-for-like reads.** The two-level corpus is also read by the three folds the one-level corpus has, each against the model at every ancestor, point and mode. `plain` and `shortcut` are the one-level reads. On this corpus a credit posted at an internal account restores it and every accepting account above it, so the shortcut's check counts the credits posted anywhere in an account's subtree against what each account on the path has outstanding, where the one-level check counts credits at contracts. The one-level check is unchanged. `kind-filtered-union` is the kind-filtered sum of offered amounts written in the three-branch `UNION` form of the postings part of `sum-with-cuts`, so the ratio of `sum-with-cuts` to it is what the applied amount and the cuts add. It does not match the micro-position the kind-filtered fold also matches, so its ratio to the kind-filtered fold bundles the query form with that pattern.

Why the forms differ in cost, one line per engine. None of the three can explain a query here, so each reason is a hypothesis and none was read from a plan.

* **Oxigraph 0.5.13** cannot explain. `Store.query` has no explain option and `QuerySolutions` offers only `serialize` and `variables`. TSD-71's reading of the source, an `OPTIONAL` inside `GRAPH ?g` under a `VALUES ?g` that falls back to a hash join over every graph, is the reason the `optional` form is dear. It says nothing of the gap between the two `UNION` forms, which is not explained.
* **Jena ARQ 5.1.0 through the kit** cannot explain. The kit passes the query text to ARQ and returns the solutions, with no explain call, and we did not build one.
* **rdflib 7.6.0** cannot explain a plan. It prints the parsed algebra (`rdflib.plugins.sparql.algebra.pprintAlgebra`), which names no join order and no cost, and we did not read it. Why its `UNION` form is dear stays open (TSD-Q37).

**A cut that copies its position.** The default cut, `joined`, is the 3 triples of LG-16, and a read joins it to its posting for the position bound. The `copied` cut also carries its posting's position (`l:cutPosition`), 4 triples, and the cuts read needs no join. The choice is the named `cut_form` (`CUT_FORMS`, default `joined`) on `quads`, `expected_stored`, `cuts_scan`, `read_with_cuts` and `run_backend_cut_forms`. Each form is loaded into a store of its own, read by the sum with cuts from the start and from the checkpoint, and checked against the model, with the time of the cuts aggregate kept apart. It runs at 30% credits, since at 5% there is no cut.

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
| When credits land at two levels of one path, an ancestor's kind-filtered sum of applied amounts is wrong where a cut was recorded, and the sum with cuts equals the stepwise balance | the two-level corpus, every ancestor at every point, in both modes, on each backend: the sum with cuts and the stepwise fold against the model's stepwise balance, and the postings alone against the model's sum of applied amounts, which differs from it at 8 of 9 ancestors at 30% credits |
| The writer's cuts are the stepwise law's | the cuts the writer recorded against the cuts the model's replay gives, and the stored triples, cuts included, against the arithmetic |
| The cuts do not hide behind a different query form | the plain fold, the shortcut and a kind-filtered read in the sum with cuts' own `UNION` form on the two-level corpus, each against the model, and the ratio of the sum with cuts to that read |
| A cut that copies its position reads as the joined cut does | the same corpus stored both ways, the sum with cuts against the model from the start and the checkpoint on each backend, with stored triples and the time of the cuts aggregate for each |
| A ceiling above a stated amount lets a credit lift an account past what was drawn, and the sum with cuts is still the stepwise balance | the ceiling variant, every ancestor at every point, mode and backend against the model, which clamps at the ceiling, and the count of cuts and of balances above their stated amount |
| The sketch's tree and history read the sketch's figures through an engine | the aggregate reads 9 as the sum of applied amounts, 7 stepwise and 7 as the sum with cuts, with one cut of 2, and the annual cap reads 9 under every fold, on each backend |
| The cost is not one engine's or one caller's | the same corpus and the same balances on three engines through Python, and on Jena in memory and on TDB2 called from Java ([benchmark/ledger-credit-kinds-jvm](../ledger-credit-kinds-jvm/README.md)) |

## Pass criterion

Every read on every backend, from the start of history and from the checkpoint, equals the model's balance for that fold, ancestor and read point and counts the postings the model counts, and every shortcut read equals the model's stepwise balance. The folds therefore differ from each other exactly where the model says, and the report records where it expects it (`model_expects` in `report.json`: the contracts where a clamp binds, the ancestors where the stepwise and the plain or filtered balances differ, the credits with no kind). The stored triples, checkpoints included, have the count the arithmetic gives. The model must itself tell the folds apart, or the corpus is refused: the cap's plain and kind-filtered balances differ, a credit with no kind exists, and at 30% credits a clamp binds at a contract and reaches an ancestor. **A wrong balance, posting count or stored count fails the run. Time never does.** `test_check.py` shows the check fails on a balance off by one, on a filter that ignores the kind, on a join that drops a credit with no kind, on a missing clamp at the drawn contract, on a wrong checkpoint, on a shortcut that skips a needed fallback and on a stored count, that it does not fail on time, that the run leaves no store open, that each form of the join gives the model's balances, and that the emitted corpus matches the model ([PRI-63](../../docs/developer/principles.md)).

The two-level pass criterion is part of the same check. Every kind-filtered, stepwise and sum-with-cuts read, from the start and from the checkpoint, equals the model, the cuts the writer recorded are the model's, the stored count includes 3 triples a cut, and at 30% credits an ancestor's ceiling binds (a cut exists) and the sum of applied amounts with no cuts differs from the stepwise balance at an ancestor, on the model and on each engine. A corpus where that could not be told is refused. `test_check.py` also shows the check fails when a cut is dropped from the stored data (with the stored count agreeing, so only the balance can tell), when the writer records no cut, and that the four-step history of the sketch gives 9 for the sum of applied amounts, 7 for the stepwise balance and the sum with cuts, with one cut of 2 at the aggregate, and 9 at the annual cap under every fold.

The LG-17 additions are part of the same check. Every `plain`, `shortcut` and `kind-filtered-union` read on the two-level corpus equals the model. Both cut forms give the model's balance and their stored count equals the arithmetic with 3 or 4 triples a cut. In the ceiling variant every read equals the model, which clamps at the ceiling, the corpus is refused unless some ancestor stands above its stated amount at a read point, and the stored count includes a triple for each ceiling. The sketch's figures are asserted on each engine. `test_check.py` shows the check fails on a `kind-filtered-union` read that is off by one, on a shortcut that skips a fallback on the two-level corpus, on a copied cut with a wrong position, on a read that clamps at the stated amount in the ceiling variant, on a ceiling variant in which nothing stands above its stated amount, and on a writer that records no cut when the sketch is read through an engine.

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

The sizes are 1,000, 5,000 and 20,000 postings at 5% and 30% credits. `LEDGER_KINDS_MAX` caps the postings and `LEDGER_KINDS_QUICK=1` runs the smallest size. `LEDGER_KINDS_NEW_ONLY=1` skips the one-level corpus and runs only the two-level corpus with its like-for-like reads, the cut forms and the ceiling variant, which is the part LG-17 added. `LEDGER_KINDS_REPORT_DIR` writes the report elsewhere. The full run took 2,325 s (about 39 minutes) on the laptop below, with the 82 tests at 161 s of it, most of it rdflib at 20,000 postings, where each read from the start of history takes minutes a run. Jena needs the test kit jar, built on first use by `mise run bootstrap:sparql-testkit` ([ADR-A125](../../docs/architecture/decisions/ADR-A125-test-support-tooling.md)). Where there is no `java` or no jar, the Jena runs are left out and the report's environment says so. `report.md` and `report.json` are generated, git-ignored and written here, with the native Jena caller's timings merged in by `mise run check:ledger-credit-kinds-jvm`. The Oxigraph store is a temporary directory, removed when the run ends, including on failure.

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

### The two-level corpus and the cut

Run of 2026-11-12 on the same laptop and engine versions, 52 tests passed and the whole task finished in 1,408 s, the two-level corpus included. Credits are posted at a contract, a sublimit or a section, half of them above a contract. "Rows" are as above, with a cut counted as a row. Times are the mean of 3 read points, at the root, at 20,000 postings. The 1,000 and 5,000 rows and the 5% rows are in `report.md`.

Stored cuts. At 30% credits there are 55 / 514 / 2,160 cuts at 1,000 / 5,000 / 20,000 postings, on 44 / 401 / 1,708 credits, which is 14.2% / 26.7% / 28.4% of the credits carrying a cut. They cost 165 / 1,542 / 6,480 triples, 3.5% of the 185,951 stored at 20,000. At 5% credits no ancestor's ceiling binds at any size, so there is no cut and the stored count equals the one-level corpus's. Every stored count equals the arithmetic, on all three engines.

Where the sums are wrong. At 30% credits the kind-filtered sum of applied amounts with no cuts, which is the postings part of the sum with cuts, differs from the stepwise balance at 8 of 9 ancestors at every size, on the model and on each engine. The kind-filtered sum of offered amounts (LG-14's fold) differs at 9 of 9. The sum with cuts and the stepwise fold equal the model at all 9 in both modes.

Time per root read (ms), 30% credits, from the start of history, then from the last checkpoint. The ratios are the time of all 27 ancestor reads of the sum with cuts against the other fold.

| Backend | read | kind-filtered | stepwise | sum-with-cuts | of which postings / cuts | to kind-filtered | to stepwise |
|---|---|---|---|---|---|---|---|
| rdflib | full | 7,494 | 7,642 | 5,123 | 4,983 / 138 | 0.71 | 0.69 |
| rdflib | checkpointed | 262 | 258 | 194 | 179 / 12 | 0.85 | 0.89 |
| Oxigraph | full | 197 | 194 | 117 | 109 / 7.0 | 0.57 | 0.22 |
| Oxigraph | checkpointed | 4.46 | 147 | 3.50 | 3.04 / 0.29 | 0.86 | 0.01 |
| Jena through the kit | full | 219 | 848 | 257 | 241 / 16 | 1.18 | 0.31 |
| Jena through the kit | checkpointed | 6.40 | 17.5 | 8.60 | 5.79 / 0.70 | 1.32 | 0.56 |

At 5% credits, full, the ratios to kind-filtered / stepwise are 0.54 / 0.53 on rdflib, 0.42 / 0.17 on Oxigraph and 1.04 / 0.27 on Jena, and checkpointed 0.73 / 0.74, 1.49 / 0.01 and 1.57 / 1.14.

What the run shows.

1. **The sum with cuts costs about what the kind-filtered sum costs, and far less than the ordered read.** From the start of history it is 0.57 to 1.18 times the kind-filtered fold at 30% credits (0.42 to 1.04 at 5%) and 0.22 to 0.69 times the stepwise fold. It has no ordered read and no loop, so it does not pay the transfer of rows to the caller. On rdflib and Oxigraph it is cheaper than the kind-filtered fold, whose kind join is an `OPTIONAL` or a two-branch `UNION`. Its three-branch `UNION` reads each of the three kinds of posting once. On Jena it is 1.2 times dearer. We did not read a plan to say why, and the comparison is of one query form against another on each engine, not of one design against the other.
2. **The cuts are cheap to read.** The cuts aggregate is 3 to 6 percent of the read at the root (138 of 5,123 ms on rdflib, 7.0 of 117 on Oxigraph, 16 of 257 on Jena at 30%), and 0.4 to 3 percent at 5% credits, where it matches nothing. It folds 710 more rows than the postings alone at the root (12,068 against 11,358), one per cut recorded there.
3. **A checkpoint bounds the read as before.** The sum with cuts from the last checkpoint is 0.02 to 0.04 of the full read on rdflib, Oxigraph and Jena at 20,000 postings and 30% credits (194 of 5,123, 3.5 of 117, 8.6 of 257 ms), folding 255 rows instead of 12,068. The checkpoint holds the account's balance, which is the same under the stepwise law and under the sum with cuts, so the sum with cuts starts from the checkpoint's stepwise balance.
4. **The postings aggregate uses no `OPTIONAL` inside a graph block and does not meet TSD-71's Oxigraph case.** The checkpointed read on Oxigraph is 3.5 ms against 147 ms for the stepwise fold, which still joins the applied amount by `OPTIONAL`.
5. **Where a 5% corpus has no cut the fold is not wrong.** At 5% credits no ceiling binds, so the sum of applied amounts with no cuts equals the stepwise balance and the kind-filtered sum of offered amounts is right, which is LG-15's finding. The defect of section 4.8 needs credits at two levels and enough of them to fill an ancestor.

### Like-for-like reads, the copied cut and the ceiling variant

Run of 2026-11-12 on the same laptop and engine versions, 82 tests passed and the whole task finished in 2,325 s. Times are the mean of 3 read points at the root, and the ratios are the time of all 27 ancestor reads, at 20,000 postings. The 1,000 and 5,000 rows and the 5% rows are in `report.md`. Single points on small times move a good deal between runs, for example Jena's checkpointed 5,000-posting read at 5% credits shows a ratio of 2.9 on 4 ms, and the tables below are at 20,000.

The sum with cuts against the like-for-like read, `kind-filtered-union`, at 30% credits (5% credits in brackets). It is the cost the applied amount and the cuts add to the same query form.

| Backend | read | kind-filtered ms | kind-filtered-union ms | sum-with-cuts ms | sum-with-cuts / kind-filtered-union | sum-with-cuts / plain | kind-filtered-union / kind-filtered |
|---|---|---|---|---|---|---|---|
| rdflib | full | 6,460 | 4,003 | 4,277 | 1.03 (1.01) | 0.84 | 0.66 |
| rdflib | checkpointed | 215 | 150 | 158 | 1.12 (1.12) | 1.04 | 0.80 |
| Oxigraph | full | 190 | 107 | 116 | 1.07 (1.03) | 1.26 | 0.53 |
| Oxigraph | checkpointed | 4.41 | 2.87 | 3.28 | 1.18 (1.35) | 1.66 | 0.67 |
| Jena through the kit | full | 194 | 210 | 259 | 1.12 (1.07) | 1.75 | 1.09 |
| Jena through the kit | checkpointed | 5.65 | 5.54 | 6.35 | 1.18 (1.25) | 1.79 | 1.01 |

The shortcut and the plain fold on the two-level corpus. Fallbacks in the 27 reads of a run, and the total time of the shortcut against the stepwise fold, at 20,000 postings read from the checkpoint (from the start of history it falls back in 27 of 27 reads at both shares on every backend).

| Backend | fallbacks, 5% / 30% | shortcut s against stepwise s, 5% | shortcut s against stepwise s, 30% |
|---|---|---|---|
| rdflib | 0 / 13 of 27 | 3.88 against 1.91 | 5.36 against 2.11 |
| Oxigraph | 0 / 13 of 27 | 0.02 against 3.32 | 2.23 against 3.68 |
| Jena through the kit | 0 / 13 of 27 | 0.07 against 0.05 | 0.24 against 0.15 |

A cut that copies its position, at 30% credits. The cuts aggregate is the second of the two aggregates of the sum with cuts. Ratios are copied against joined over all 27 ancestor reads.

| Backend | stored triples, joined / copied | cuts aggregate ms at the root, joined / copied, full | joined / copied, checkpointed | cuts aggregate, copied / joined, full / checkpointed | whole sum with cuts, copied / joined, full |
|---|---|---|---|---|---|
| rdflib | 185,951 / 188,111 | 132 / 127 | 10.2 / 10.2 | 0.95 / 0.97 | 1.00 |
| Oxigraph | 185,951 / 188,111 | 6.69 / 4.96 | 0.23 / 0.18 | 0.75 / 0.82 | 0.98 |
| Jena through the kit | 185,951 / 188,111 | 13.5 / 11.0 | 0.59 / 0.60 | 0.84 / 0.99 | 1.01 |

The ceiling variant, at 30% credits. Eleven of the 30 contracts and sublimits have a ceiling of 1.5 times their stated amount. Counts are the model's, and the three engines read the same ones.

| Postings | cuts | credits with a cut | stored triples | accounts above stated at some read point | ancestor reads above stated | ancestors where the uncut sum is wrong | offered sum wrong |
|---|---|---|---|---|---|---|---|
| 1,000 | 85 | 66 of 309 | 9,270 | 7 of 33 | 6 of 27 | 5 of 9 | 9 of 9 |
| 5,000 | 550 | 431 of 1,501 | 46,543 | 3 of 33 | 5 of 27 | 5 of 9 | 9 of 9 |
| 20,000 | 2,190 | 1,739 of 6,013 | 186,052 | 2 of 33 | 4 of 27 | 6 of 9 | 9 of 9 |

Time per root read (ms), 20,000 postings, ceiling variant against the two-level corpus (in brackets), full then checkpointed.

| Backend | kind-filtered | stepwise | sum-with-cuts | to kind-filtered | to stepwise |
|---|---|---|---|---|---|
| rdflib | 6,817 (6,460) / 252 (215) | 6,929 (6,431) / 245 (216) | 5,254 (4,277) / 183 (158) | 0.73 (0.68) / 0.87 (0.90) | 0.72 (0.67) / 0.89 (0.91) |
| Oxigraph | 187 (190) / 4.36 (4.41) | 180 (177) / 139 (137) | 116 (116) / 3.24 (3.28) | 0.57 (0.57) / 0.81 (0.78) | 0.24 (0.24) / 0.01 (0.01) |
| Jena through the kit | 201 (194) / 5.17 (5.65) | 807 (785) / 16.5 (16.2) | 235 (259) / 6.69 (6.35) | 1.17 (1.23) / 1.28 (1.19) | 0.31 (0.33) / 0.50 (0.51) |

The sketch's tree, loaded into each engine as the benchmark's own quads and read by every fold: the aggregate reads 9 as the sum of applied amounts, 7 stepwise and 7 as the sum with cuts, with one cut of 2 at the aggregate, and the annual cap reads 9 by the kind-filtered, `kind-filtered-union`, stepwise and sum-with-cuts folds, on rdflib, Oxigraph and Jena (the plain fold reads the cap at 19, since it counts the reinstatement the cap does not accept).

What the run shows.

1. **The cuts add 3 to 12 percent from the start of history and 12 to 18 percent from a checkpoint, once the query form is held.** At 20,000 postings and 30% credits the sum with cuts is 1.03 times (rdflib), 1.07 (Oxigraph) and 1.12 (Jena) the like-for-like read from the start, and 1.12, 1.18 and 1.18 from the checkpoint. LG-16's finding that the sum with cuts was cheaper than the kind-filtered fold on rdflib and Oxigraph (0.57 to 0.71) was therefore the query form, not the cuts. The like-for-like read is itself 0.66, 0.53 and 1.09 of the kind-filtered fold, because it is a different form that also leaves out the micro-position pattern. We cannot separate the two, since no engine here explains a query.
2. **The shortcut behaves on the two-level corpus as it does on the one-level one.** It falls back in every read from the start of history, and from a checkpoint in none at 5% credits and 13 of 27 at 30%, against 18 of 27 on the one-level corpus. Its balance equals the model's in every read, so the subtree-wide check of credits held on this corpus. It costs a second aggregate, so it is the dearer read on rdflib and Jena (1.4 to 2.5 times the stepwise fold from a checkpoint) and the cheaper one on Oxigraph from a checkpoint, 0.02 s against 3.32 s at 5% credits and 2.23 against 3.68 at 30%.
3. **Copying the position into the cut saves 0 to 25 percent of the cuts aggregate, which is 3 to 6 percent of the read, and costs a triple a cut.** The whole sum with cuts is within 2 percent of the joined form on every backend, and the copy adds 2,160 triples to 185,951, 1.2 percent. On these figures the copy does not pay, and the 3-triple form stays the default. The saving is largest on Oxigraph and Jena at 20,000 postings from the start of history. From a checkpoint the cuts read is 0.2 to 10 ms and the copy changes nothing that can be told from noise.
4. **A ceiling above a stated amount costs a read nothing that can be told apart.** The sum with cuts equals the stepwise balance at every ancestor in both modes on all three engines, and its times against the two-level corpus agree to within run-to-run variation (the ratios to the kind-filtered and stepwise folds differ by 0 to 0.09, and Jena at 5,000 postings read the sum with cuts in 97 ms against 63 and was not repeated). The model finds 2 accounts of 33 above their stated amount at some read point at 20,000 postings, 4 of the 27 ancestor reads, and 7 and 3 at the smaller sizes. A read that clamps at the stated amount fails the check. The variant has 30 more cuts than the two-level corpus at 20,000 postings (2,190 against 2,160), and its sum with no cuts is wrong at 6 of 9 ancestors where the two-level corpus's is wrong at 8.
5. **The sketch's figures hold through an engine as well as in the model.** The cut the writer records is the cut the cuts aggregate reads back, and a writer that records none gives 9 where the model gives 7, which the check catches.

## What this does not measure

Concurrent writers, which the cut needs, since the writer reads the path balances and records the cut in one step. The cost of writing, since the cuts and the ceilings are loaded with the history and the writer's reads of the path balances are not run. Late postings. The Java caller, which reads the one-level corpus only (`benchmark/ledger-credit-kinds-jvm`). Each of these is for a later part of LG-17. Not in LG-17 at all, a query plan for any engine, since none here can explain a query, a ceiling that moves in time, reads of a contract, which the account's own postings answer, a checkpoint written by the fold rather than by the model's arithmetic, a `union` form of the applied join on Oxigraph, and a native caller on a store other than Jena. The ceiling variant is read at 30% credits only and without the plain fold or the shortcut. The event stream is seeded and the engines see the same one, so a figure compares folds on one engine and caller, and an engine against another only in its shape. The Java caller runs the reads of a corpus once each, in one JVM after a warm-up on the smallest corpus, so its smallest sizes include some JIT warm-up.

## Files

| File | What it is |
|---|---|
| `check.py` | the tree, the streams, the model, the checkpoints, the four reads and the sum with cuts on three backends, the like-for-like reads, the cut forms, the ceiling variant, the sketch's tree, the pass criterion, the report, and `--emit` and `--merge` for the native Jena caller (the one-level corpus only) |
| `test_check.py` | the check's own tests |
| `conftest.py` | makes a temporary folder refuse removal while a store in it is open |
| `report.md`, `report.json` | the last run's results, generated and git-ignored |
