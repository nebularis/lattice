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

### The two-level corpus read natively, and Jena's plans

Run of 2026-11-12 on the same laptop by `mise run check:ledger-credit-kinds-jvm`, Jena 5.1.0 called from Java 25 with a 2 GB heap, each read run once in one JVM. The two-level corpus is read in the `optional` kind join form, in memory and on TDB2, at 1,000, 5,000 and 20,000 postings and 5% and 30% credits, by the plain, kind-filtered, `kind-filtered-union`, stepwise and sum-with-cuts folds, from the start of history and from the last checkpoint. Every balance and count equals the model's, and the postings alone of the sum with cuts equal the model's sum of applied amounts and differ from the stepwise balance at 8 of 9 ancestors at 30% credits, as the model says. The report holds every row, in the section "Native Jena (Java), two-level corpus".

Mean ms per read of the root from the start of history, 20,000 postings (the cuts column is the time of the cuts aggregate, part of the sum with cuts):

| Store | credits | plain | kind-filtered | kind-filtered-union | stepwise | sum-with-cuts | of which cuts |
|---|---|---|---|---|---|---|---|
| memory | 5% | 37.72 | 49.99 | 72.95 | 88.75 | 48.75 | 1.93 |
| memory | 30% | 40.12 | 53.58 | 63.16 | 106.71 | 58.24 | 4.03 |
| TDB2 | 5% | 88.17 | 72.32 | 63.39 | 125.26 | 63.83 | 1.14 |
| TDB2 | 30% | 113.65 | 109.86 | 109.69 | 203.95 | 117.77 | 7.49 |

The ratio of the time of all 27 ancestor reads, 20,000 postings, from the start of history and (in brackets) from the last checkpoint:

| Store | credits | sum-with-cuts / kind-filtered-union | sum-with-cuts / stepwise | sum-with-cuts / plain | kind-filtered-union / kind-filtered |
|---|---|---|---|---|---|
| memory | 5% | 0.91 (1.20) | 0.65 (1.59) | 1.45 (1.92) | 1.16 (1.38) |
| memory | 30% | 0.97 (0.82) | 0.66 (1.17) | 1.63 (1.93) | 1.14 (1.91) |
| TDB2 | 5% | 1.04 (1.17) | 0.57 (1.30) | 1.02 (1.86) | 0.85 (1.32) |
| TDB2 | 30% | 1.09 (1.13) | 0.69 (0.99) | 1.50 (1.83) | 1.01 (1.12) |

The sum with cuts costs what its like-for-like read costs, within 0.82 to 1.20 and mostly within 0.9 to 1.1 from the start, which is the shape the Python callers gave on Jena (1.07 and 1.12 from the start at 5% and 30%, and 1.25 and 1.18 from the checkpoint). The ratio is not a quantity this single run fixes to better than about 0.1. The checkpointed reads take 1 to 3 ms, so a single slow read moves a ratio, and the one checkpointed read of the root by `kind-filtered-union` in memory at 30% took 5.08 ms against 1 to 2 ms for the others, which is why that row's two ratios (0.82 and 1.91) are not to be read as a difference. The cuts aggregate is 2 to 7% of the sum with cuts, 4.03 of 58.24 ms in memory and 7.49 of 117.77 ms on TDB2 at 30%. The sum with cuts costs 0.57 to 0.69 of the stepwise fold from the start, and 1.0 to 1.6 of it from the checkpoint, where the stepwise fold has little to fold. On TDB2 the stepwise fold, which crosses no pipe here, costs 1.4 to 1.8 of the plain fold at the root at 20,000 postings (125.26 against 88.17 ms and 203.95 against 113.65 ms), and 1.5 on the one-level corpus at 30% (150.15 against 97.25 ms).

What the plans show. The run writes what Jena will run for three reads of the root at 20,000 postings and 30% credits to `benchmark/ledger-credit-kinds-jvm/target/plans.txt` (git-ignored), for each store, as compiled, as optimised by ARQ, and for TDB2 in quad form and in the order TDB2's reordering gives each pattern.

* **The `VALUES ?g` graphs are the bound that works.** In all three queries ARQ turns the join of the VALUES table with the `GRAPH ?g` block into a `sequence`, so the pattern is evaluated once per listed graph with `?g` bound, 400 graphs for the root at 20,000 postings from the start. TDB2 keeps the same shape in quad form with `?g` as the first term of each quad. No graph outside the list is touched. This agrees with the measurements, where a checkpointed read, which lists few graphs, costs 0.5 to 3 ms against 40 to 120 ms from the start.
* **The filter on position does not bound a scan.** In every query the optimiser keeps `?pos` as a variable of the first triple of the pattern, `?p l:position ?pos`, and applies `FILTER(?pos <= N)` to the rows of that triple, so each listed graph is read for all its position triples and the bound only drops rows after them. In the OPTIONAL form it places the filter after that triple and moves the rest of the pattern (`microPosition`, `direction`, `amount`) behind it, so those are probed only for rows that pass. Nothing in the plan turns the bound into a range of an index. Only the last listed graph holds postings above the bound, so the filter saves little in these reads, and what follows from the plan is that a read costs the number of position triples in the graphs listed.
* **OPTIONAL against UNION.** The OPTIONAL form becomes `conditional`, one probe of `l:kind` for each row that passes the filter. The UNION form is three branches, each repeating the position triple and its filter, so the position triples of the listed graphs are scanned three times, and the third branch tests `NOT EXISTS` for each credit. The plan therefore does more per graph for the UNION, and the measurements put the UNION at 1.14 to 1.16 of the OPTIONAL in memory at 20,000 postings and 0.85 to 1.01 on TDB2. That the plan has three scans does not by itself explain a ratio near 1, since the second and third branches are selective after the position scan, and the plan carries no cardinalities or costs, so it shows the work Jena is asked to do and not what it costs. The kind filter outside the graph block, `FILTER(?d = l:Debit || NOT EXISTS ... || EXISTS ...)`, is applied to every row of both forms and is not part of the difference.
* **The cuts aggregate is driven by the cuts.** Its first triple has a constant object, `?c l:cutAt <urn:acct:root>`, so both stores start from the cuts at the account and join to `cutOf` and the posting's position. Its work is the cuts recorded at the account (2,160 in the whole corpus) and not the postings, which fits it taking 2 to 7% of the sum with cuts. The position filter is again applied after the join.
* **TDB2's reordering changes nothing here.** The store's transformation, `ReorderFixed`, returned the patterns of all three queries in the order they were given. TDB2 has no statistics in this benchmark, so a reordering by selectivity was not possible.

What the output does not show. ARQ's execution log, which would show the plan as it ran and the order the in-memory engine chose, goes through SLF4J, which the module binds to a no-op logger, so it was not read, and the in-memory engine's plan is the optimised algebra alone, without whatever its executor does after it. The TDB2 order is what the store's reordering transformation returns for a pattern, asked directly, and not the order read from a log of a run. No plan carries a row count or a time. So the plans explain which graphs and triples are touched and how often, and they do not decide whether the UNION's repeated scan or the OPTIONAL's probe costs more, for which the measured ratios are the evidence. This closes the gap for Jena only. Oxigraph and rdflib offer nothing to read.

## Writes, concurrent writers and late postings

`writes.py`, run by `mise run check:ledger-credit-kinds-writes` (`LEDGER_WRITES_QUICK=1` runs the smallest sizes, `LEDGER_WRITES_REPORT_DIR` writes `writes-report.md` and `writes-report.json` elsewhere, both git-ignored). It reuses the tree, the writer's arithmetic, the vocabulary, the quads and the reads of `check.py`, and adds no behaviour to it.

**The live writer.** For one posting against a store that holds history, the writer reads the ledger's revision and the balance of every account on the posting account's path (a sum with cuts from the last checkpoint, whose balances it reads once), settles the posting in the application with `settle_debit` and `settle_credit`, refuses a debit larger than the balance of any account on its path, and writes the posting, its applied amount, its kind, its cuts and the new revision in one SPARQL update request. It writes no checkpoint, so its reads fold every period after the last one the history holds. A contract has its own read, since `check.py` reads ancestors only.

**The guard.** One triple in the default graph holds the revision of the owner's ledger. The write is `DELETE { revision N } INSERT { revision N+1, and the posting and its cuts in the period graph } WHERE { revision N }` (PAT-21, PAT-04), and the committed revision N+1 is the posting's recorded position. SPARQL update returns no count, so the writer asks afterwards whether its own posting exists. The posting's IRI is unique to the writer and the attempt. A stale writer wrote nothing, reads again and retries. The unguarded writer sends `DELETE DATA { revision N } ; INSERT DATA { revision N+1, and the posting }` and does not confirm. One revision covers the owner's whole ledger, so any commit makes every other writer in flight stale. The benchmark reports the figures that bear on whether that is too coarse and does not decide it.

**What concurrent means here.** Threads in one process against one `pyoxigraph.Store`. It is not a test over HTTP, nor from several processes. pyoxigraph releases the GIL in a query and in an update: a thread counting in pure Python beside a thread running queries back to back ran at 0.98 of its speed alone, beside updates at 1.04, and beside a thread of pure Python at 0.48, on 8 CPUs, so the threads overlap in the engine. The fixed interleavings step two writers by hand, with no threads, and are the tests. The stress gives each thread its own seeded requests from the two-level stream's distribution, 1,000 further postings in all on a store holding 5,000, each retried until it commits or is refused as unavailable. After each run the committed records are read back in revision order and compared with a replay through `settle_debit` and `settle_credit`: every stored applied amount, every stored cut and every account's sum with cuts. Revisions must be dense and unique. A guarded run on the in-memory store that differs raises `WrongResult`. The on-disk store is audited and reported but not asserted, for the reason below.

**Late postings.** A late posting is stored in the period graph of its recorded position, with its effective position as one more triple, on every posting. That is a choice of this benchmark and not a decision, since where a posting effective inside a sealed period goes is open (PDD-14). A seeded `LATE_SHARE` of 5% of the postings, and a second run at 20%, are effective one to three periods (200 passes each) before they are recorded, never after (STD-294). The writer settled each in recorded order, so its applied amount and cuts were computed against every posting recorded before it. At each ancestor and read point four numbers are compared. Recorded is the sum with cuts over postings recorded by the point, and must equal the stepwise replay, in the model and through Oxigraph. Effective is the same amounts and cuts over postings effective by the point, folded from the start over every period graph (STD-278, and no reach cap, since a posting recorded long after the point can be effective by it), and the engine must equal the model. Replay R is a fresh stepwise replay in recorded order of only the postings effective by the point, and replay E the same in effective order, ties by recorded order. Nothing says which is right.

Figures, from one run on one laptop (8 CPUs, 8 GB, Oxigraph 0.5.13, Jena 5.1.0 through the kit, Python 3.14.7). The report holds every row.

A write, mean ms, 500 further postings by one writer. The store is in memory unless stated. A debit reads 4 accounts and makes 8.1 requests, a credit with no cut 3.0 to 3.1 accounts and 6.7 to 6.9, a credit with a cut 3.5 to 3.7 and 7.4 to 7.7. A write adds 8.0, 9.8 to 9.9 and 13.2 to 13.9 triples, and the revision triple is replaced, not added. At 20,000 postings 187 of the 350 debits were refused, because the corpus does not refuse debits and the cap section is already overdrawn, so a debit under it has no availability.

| Backend, postings | debit total | credit total | credit with a cut total | path reads share | update, guarded / unguarded | confirm |
|---|---|---|---|---|---|---|
| Oxigraph memory, 1,000 | 2.49 | 2.29 | 2.33 | 98% | 0.03 / 0.02 | 0.02 |
| Oxigraph memory, 5,000 | 2.20 | 1.93 | 2.24 | 98% | 0.03 / 0.02 | 0.02 |
| Oxigraph memory, 20,000 | 2.82 | 2.51 | 2.58 | 98% | 0.03 / 0.03 | 0.02 |
| Oxigraph disk, 20,000 | 11.00 | 10.06 | 10.03 | 99% | 0.09 / 0.07 | 0.03 |
| Jena, 1,000 | 20.83 | 18.73 | 19.46 | 97% | 0.42 / 0.32 | 0.18 |
| Jena, 20,000 | 41.15 | 24.34 | 31.95 | 98% | 0.40 / 0.37 | 0.16 |

The settle is under 0.01 ms everywhere. The p95 is 1.2 to 1.5 times the mean on Oxigraph and up to 2 times on Jena. The guard adds the confirmation and a dearer update, 0.03 to 0.06 ms on Oxigraph in memory and on disk and about 0.25 ms on Jena, 1 to 2% of a write, and all of the cost of a write is the path reads.

The stress, in memory, 932 to 990 commits of 1,000 requests (the rest refused as unavailable):

| Threads | writer | lost races | retries per request, mean / max | wall s | commits per s | differs from the replay (applied, cuts, balances) | overdrawing debits | duplicate revisions |
|---|---|---|---|---|---|---|---|---|
| 1 | guarded | 0 | 0 / 0 | 3.27 | 298 | 0, 0, 0 | 0 | 0 |
| 2 | guarded | 492 | 0.49 / 492 | 3.72 | 266 | 0, 0, 0 | 0 | 0 |
| 4 | guarded | 1,869 | 1.87 / 539 | 5.07 | 187 | 0, 0, 0 | 0 | 0 |
| 8 | guarded | 5,346 | 5.35 / 117 | 9.04 | 104 | 0, 0, 0 | 0 | 0 |
| 1 | unguarded | 0 | 0 / 0 | 3.14 | 311 | 0, 0, 0 | 0 | 0 |
| 2 | unguarded | 0 | 0 / 0 | 2.36 | 417 | 16, 90, 1 | 0 | 485 |
| 4 | unguarded | 0 | 0 / 0 | 1.62 | 584 | 31, 138, 3 | 5 | 700 |
| 8 | unguarded | 0 | 0 / 0 | 1.47 | 635 | 28, 117, 7 | 5 | 788 |

The unguarded writer's differences are not asserted and may be zero by luck in another run. The fixed interleavings are the tests: two recoveries racing for the room at an aggregate (the stale writer's missing cut lands, and the aggregate's sum differs), two debits racing for the last availability of an aggregate (the second is refused on retry with the guard and overdraws it without), and a debit and a credit on different contracts under one aggregate (the guard made the second retry once, and the outcome equals the replay).

The guard on the on-disk store, three guarded runs a cell, 5,000 postings and 1,000 requests. In memory all nine runs were dense with no duplicate. On disk 8 of 9 had two commits at one revision, from 2 to 32 of them, and in 6 runs a stored cut or applied amount differed from the replay. So the one revision triple closes the race in memory and not on disk, and the benchmark reports the disk figures without asserting them. The cause is the store and not the writer: Oxigraph 0.5.13 makes a second update wait in memory and not on disk, where two updates that read the same revision both commit, and one lock around the update call restores the guard (TSD-73).

Late postings, 9 ancestors at 3 points, 27 reads a row. The recorded sum equalled the replay and the model, and the effective sum equalled the model, in every row. With no late posting all four agreed.

| Postings | late share | late postings | effective differs from R | from E | R from E | largest difference, eff/R, eff/E, R/E | effective sum impossible | effective read / recorded read |
|---|---|---|---|---|---|---|---|---|
| 5,000 | 5% | 257 | 7 | 26 | 26 | 3,780 / 4,938 / 2,935 | 4 | 1.29 |
| 5,000 | 20% | 974 | 9 | 26 | 26 | 3,630 / 6,892 / 6,892 | 2 | 1.29 |
| 20,000 | 5% | 1,013 | 7 | 26 | 26 | 4,093 / 4,033 / 2,178 | 4 | 1.39 |
| 20,000 | 20% | 3,997 | 10 | 27 | 27 | 7,264 / 6,312 / 2,467 | 7 | 1.38 |

The effective sum is impossible (below zero or above the ceiling) at 4 reads at 5% and 2 at 5,000 postings and 20% credits late, and also at 2 reads of the 20,000-posting corpus with no late posting, where the history is already overdrawn. Folding every period graph from the start costs 1.3 to 1.4 times the recorded fold from the start of history, whose cost grows with the point read.

What the write benchmark does not show. The writer writes no checkpoint, so a period close is not measured. The stress is threads in one process. The disk store is not asserted. The native Jena writer is below.

### The same writer on native Jena

Run of 2026-11-12 on the same laptop by `mise run check:ledger-credit-kinds-jvm-writes` (981 s with its 6 tests), Jena 5.1.0 called from Java 25 with a 2 GB heap, threads in one JVM against one dataset, Jena in memory and TDB2 in a temporary directory. The writer is `writes.py`'s ported (the module `benchmark/ledger-credit-kinds-jvm`), with the same preloads and the same seeded request lists, so a run is comparable to the Oxigraph one above. After each run the JVM exports the dataset and Python loads the export into an in-memory Oxigraph and runs `audit`, the replay of the commits in revision order, so the replay is the Python one. TDB2 makes every commit durable, at 84 to 98 ms an update here, so a TDB2 run takes smaller counts and is not the same size as the in-memory one. TDB2 ran the probe up to 100 markers and 50 increments a thread, the single writer for 100 writes, and the stress for 200 requests in all, each cell three times at 2, 4 and 8 threads. Jena in memory ran the sizes of the Python benchmark, 1,000 markers, 500 increments, 500 writes and 1,000 requests.

**C1, the probe of TSD-73 on Jena.** A counter triple. Each thread reads the counter N, sends `DELETE { N } INSERT { N+1 and its marker } WHERE { N }` as one update request in its own write transaction, and asks in a read transaction whether its marker exists, until the counter reaches the target. Then each thread increments in the store (`DELETE { ?n } INSERT { ?m } WHERE { ... BIND(?n + 1 AS ?m) }`). Three runs a cell at 2, 4 and 8 threads, one at 1.

| Store | Threads | markers confirmed, of the target, 3 runs | revisions with more than one marker | lost races, 3 runs | increment final, of threads times the count | counter triples left |
|---|---|---|---|---|---|---|
| memory, target 1,000 | 1 | 1,000 | 0 | 0 | 500 of 500 | 1 |
| memory | 2 | 1,000, 1,000, 1,000 | 0, 0, 0 | 997, 999, 998 | 1,000 of 1,000 in every run | 1 |
| memory | 4 | 1,000, 1,000, 1,000 | 0, 0, 0 | 2,904, 2,979, 2,958 | 2,000 of 2,000 | 1 |
| memory | 8 | 1,000, 1,000, 1,000 | 0, 0, 0 | 6,778, 6,574, 6,850 | 4,000 of 4,000 | 1 |
| TDB2, target 100 | 1 | 100 | 0 | 0 | 50 of 50 | 1 |
| TDB2 | 2 | 100, 100, 100 | 0, 0, 0 | 100, 100, 100 | 100 of 100 | 1 |
| TDB2 | 4 | 100, 100, 100 | 0, 0, 0 | 300, 300, 300 | 200 of 200 | 1 |
| TDB2 | 8 | 100, 100, 100 | 0, 0, 0 | 700, 700, 700 | 400 of 400 | 1 |

On both Jena stores, in all 20 guarded runs, every revision carries one marker, the confirmed markers are the target, and the in-store increment ends at threads times the count as one triple. A second update does wait for the first and runs its `WHERE` on the first's result. A lost race is a guarded update that found the counter already moved and wrote nothing, and its thread read again. At two threads a store loses about one race a revision on memory (997 to 999 of 1,000) and exactly one on TDB2 (100 of 100), and TDB2 loses exactly threads less one races a revision at 2, 4 and 8, as writers queued behind a lock would. A thread dump taken during an exploratory run, not part of the report, showed the TDB2 threads parked in `TransactionCoordinator.acquireWriterLock`, a fair semaphore, with one thread committing. This differs from Oxigraph on disk (TSD-73), where the same probe confirmed 1,300 to 1,600 markers of 1,000, and agrees with Oxigraph in memory. So the guard is safe on Jena in memory and on TDB2 called in process (TSD-74). The probe is reported and not asserted, and what it decides is only whether the guarded runs of the store are held to the replay. Both are.

**What a write costs.** Mean ms per write, one writer, 500 further postings on Jena in memory and 100 on TDB2, guarded. The path reads are made in one read transaction.

| Store, postings | debit total | credit total | credit with a cut total | path reads share | update, guarded / unguarded | confirm |
|---|---|---|---|---|---|---|
| Jena memory, 1,000 | 6.12 | 5.39 | 5.77 | 93 to 95% | 0.24 / 0.21 | 0.08 |
| Jena memory, 5,000 | 5.90 | 4.63 | 5.60 | 93 to 95% | 0.22 / 0.20 | 0.06 |
| Jena memory, 20,000 | 10.43 | 6.18 | 8.30 | 94 to 97% | 0.27 / 0.24 | 0.07 |
| Jena TDB2, 1,000 | 102.86 | 100.10 | 102.86 | 13 to 15% | 86.45 / 86.74 | 0.53 |
| Jena TDB2, 20,000 | 110.69 | 94.63 | 105.57 | 11 to 18% | 90.40 / 93.43 | 0.37 |

The writes are the same as the Python ones, 4 accounts and 8.1 requests for a debit in memory (8.4 on TDB2, which writes the first 100 of the requests), 3.0 to 3.1 accounts and 6.7 to 6.9 requests for a credit, and 8, 9.8 to 9.9 and 13.2 to 13.9 triples. The settle is under 0.01 ms. Natively on Jena in memory a write costs 4.6 to 10.4 ms against 17 to 41 ms through the test kit's pipe, and the path reads, which are 93 to 97% of it, are the cost, as in Oxigraph where a write is 2.2 to 2.8 ms. On TDB2 a write costs 95 to 113 ms, of which the update, that is the commit, is 84 to 98 ms and the path reads 10 to 20 ms. The guard adds the confirmation, 0.06 to 0.08 ms in memory and 0.3 to 0.9 ms on TDB2, and a dearer update, 0.02 to 0.04 ms in memory. At 20,000 postings 187 of the 500 writes were refused in memory (32 of 100 on TDB2), because the corpus overdraws its cap section. Every single-writer export, guarded and unguarded, equals the replay. A warm-up writer runs first, and each single-writer figure is one run.

**The stress.** Jena in memory, guarded, 1,000 requests on a store of 5,000, three runs a cell (the three values are shown where they differ):

| Threads | commits | lost races | retries per request, mean / max | wall s | commits per s | differs from the replay | duplicate revisions |
|---|---|---|---|---|---|---|---|
| 1 | 976 | 0 | 0 / 0 | 7.71 | 127 | none | 0 |
| 2 | 987, 991, 987 | 674, 895, 578 | 0.58 to 0.90 / 224 to 429 | 7.76, 8.75, 7.97 | 113 to 127 | none | 0 |
| 4 | 940, 931, 934 | 2,277, 2,252, 2,241 | 2.24 to 2.28 / 156 to 343 | 8.38, 8.91, 8.39 | 104 to 112 | none | 0 |
| 8 | 939, 937, 937 | 4,884, 4,850, 4,847 | 4.85 to 4.88 / 77 to 125 | 12.38, 12.41, 12.63 | 74 to 76 | none | 0 |

The rest of the 1,000 requests were refused as unavailable. Against Oxigraph in memory above, the lost races are the same order (492, 1,869 and 5,346 at 2, 4 and 8 threads there) and the throughput lower, 127 to 74 commits per s against 298 to 104. The same writer without the guard, once a cell, left 484, 683 and 776 duplicate revisions at 2, 4 and 8 threads (485, 700 and 788 on Oxigraph), 15 to 31 stored applied amounts, 99 to 147 stored cuts and 2 to 6 balances that differ from the replay, and 0 to 4 debits that overdrew an account. Those are reported and not asserted.

On TDB2, guarded, 200 requests in all on a store of 5,000, three runs a cell, every run committed all 200 requests with dense revisions and no difference from the replay. The lost races were 100, 300 and 700 at 2, 4 and 8 threads in every run, the retries per request 0.50, 1.50 and 3.50, the wall time 22 to 24 s, 30 to 31 s and 41 to 60 s (22.7 s at one thread, 113 ms a request with its reads), which is 8 to 9, 6 to 7 and 3 to 5 commits per s. Without the guard the wall time fell to 18, 17 and 15 s and the store held 100, 150 and 175 duplicate revisions of 200, with 2 to 8 stored applied amounts, 13 to 23 stored cuts and 1 to 4 balances that differ from the replay.

What the native writes do not show. They are threads in one JVM, not several processes or HTTP. TDB2 ran at a fifth to a tenth of the in-memory counts. The wall time of a guarded run on TDB2 grows far less than its lost races, so a lost race costs much less than a commit, and the cause was not examined. Each cell of the stress is three runs and the single writer one, on one laptop.

## What this does not measure

Not in LG-17 at all, a query plan from the Python callers, since none of them can explain a query (the Java caller's plans are above, for Jena only and without a run-time explanation), a ceiling that moves in time, a checkpoint written by the fold rather than by the model's arithmetic, a `union` form of the applied join on Oxigraph, and a native caller on a store other than Jena. The ceiling variant is read at 30% credits only and without the plain fold or the shortcut. The Java caller does not read the ceiling variant, the cut forms or the shortcut on the two-level corpus. The event stream is seeded and the engines see the same one, so a figure compares folds on one engine and caller, and an engine against another only in its shape. The Java caller runs the reads of a corpus once each, in one JVM after a warm-up on the smallest corpus, so its smallest sizes include some JIT warm-up. The write benchmark below does not measure writes over HTTP or from more than one process, a store other than Oxigraph and Jena under concurrent writers, a writer that writes the checkpoint at a period close, a guard narrower than the owner's whole ledger, a posting effective inside a sealed period as a decision, or any rule that consumes an amount in effective order. The native writes are threads in one JVM, on Jena TDB2 at smaller counts than the in-memory runs because every TDB2 commit is made durable.

## Files

| File | What it is |
|---|---|
| `check.py` | the tree, the streams, the model, the checkpoints, the four reads and the sum with cuts on three backends, the like-for-like reads, the cut forms, the ceiling variant, the sketch's tree, the pass criterion, the report, and `--emit` and `--merge` for the native Jena caller (both corpora) |
| `test_check.py` | the check's own tests |
| `writes.py` | the live writer, its guard, the fixed interleavings, the stress, the GIL probe, the late postings and their four numbers, and the report (`writes-report.md`, `writes-report.json`), and `--emit-jvm` and `--audit-jvm` for the native Jena writer |
| `test_writes.py` | the write benchmark's own tests |
| `conftest.py` | makes a temporary folder refuse removal while a store in it is open |
| `report.md`, `report.json`, `writes-report.md`, `writes-report.json` | the last runs' results, generated and git-ignored |
