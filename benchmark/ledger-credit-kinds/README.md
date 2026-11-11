<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Ledger credit kinds

A benchmark under [ADR-A124](../../docs/architecture/decisions/ADR-A124-benchmark-root.md). It measures what a credit's kind and a stepwise credit ceiling add to the read of an ancestor's balance, on every engine the repository runs SPARQL on, before the ledger builds them. A cost measured on one engine is a hypothesis for another ([STD-176](../../docs/developer/standards.md)), so each read runs on rdflib in memory, Oxigraph on disk and Jena ARQ in memory.

Under the ledger's agreed design a draw or credit is posted once, at the account it names, and an ancestor's balance is a fold over its subtree's postings in the current period's named graph. The decision on LG-Q10 adds a kind to a credit posting, a concept IRI from a scheme, and each account declares which kinds restore it, all kinds by default. A ceiling is already part of the design, since a credit never lifts an account above its stated amount (law LD3), and where it can bind at an ancestor the fold has to be a running balance applied posting by posting.

## What it does

The tree has depth 4: a root, 2 sections, 3 sublimits to a section and 4 contracts to a sublimit, so 33 accounts. The first section is a cap and accepts recoveries only, and every other account accepts all kinds. Each account's ceiling is its stated amount. Postings come in passes of one to three (a pass position, then a micro-position in the pass) on random contracts, and each goes into a named graph keyed by its sublimit and its period of 200 passes. A credit is a recovery, a reinstatement or a write-back, in equal shares, under `https://example.org/`. Credits are larger than debits, so at 30% credits a ceiling binds often and at 5% it seldom does. A posting is 8 triples, and a credit has a ninth for its kind.

Every ancestor (6 sublimits, 2 sections, the root) is read at three pass positions, none on a period end, by each of three folds.

| Fold | Balance | Form on the engine |
|---|---|---|
| plain | the stated amount plus the signed sum of every posting in the subtree up to the point, every credit counted. Today's design, the baseline | one SPARQL aggregate over the subtree's graphs |
| kind-filtered | the same, counting a credit only if the ancestor declares no kinds or declares the credit's kind | one SPARQL aggregate, with a join to the credit's kind and a filter on the ancestor's `accepts` |
| stepwise | the ancestor's running balance applied posting by posting in recorded order, each accepted credit clamped at the ceiling | **an ordered SELECT folded in Python.** SPARQL cannot clamp a running sum. The engine filters by kind, sorts by `?pos ?mp` and returns every accepted posting as a row, and Python loops over the rows. The time includes the sort, the transfer of every row and the loop |

The join to the credit's kind has two forms. `optional` is an `OPTIONAL { ?p l:kind ?k }` in the graph block. `union` is `{ ?p l:direction l:Debit } UNION { ?p l:kind ?k }`. Their cost differs by engine (below), so each backend reads the form that is cheaper on it, rdflib and Jena `optional` and Oxigraph `union`, and `LEDGER_KINDS_FORM=optional|union` forces one on all three. The report's `kind join` column says which was read.

Reads fold from the start of history. There are no checkpoints, since the question is what the filter and the ceiling add per posting folded, and a checkpoint would bound the folded postings the same way for all three folds.

## What it tests

| Claim | Test |
|---|---|
| An ancestor's kind-filtered fold counts a credit only if the account accepts its kind, and equals the plain fold where the account accepts every kind | every ancestor at every point, against the model, on each backend |
| The stepwise fold clamps each accepted credit at the ceiling, which a plain sum cannot | the same, at 30% credits, where the model has a ceiling bind |
| The kind filter and the stepwise fold are not the cost of a different design from the plain fold | time per read and postings folded per read, each fold against the plain fold, on each backend and size |
| The stepwise fold's cost is a sort and a transfer, not only a fold | rows returned per read and time, stepwise against kind-filtered |
| The cost is not one engine's | the same corpus and the same balances on three engines |

## Pass criterion

Every read on every backend equals the model's balance for that fold, ancestor and read point, and counts the postings the model counts. The three folds therefore differ from each other exactly where the model says. The stored triples have the count the arithmetic gives. The model must itself tell the folds apart, or the corpus is refused: the cap's plain and kind-filtered balances differ, and at 30% credits a ceiling binds at some ancestor. **A wrong balance, posting count or stored count fails the run. Time never does.** `test_check.py` shows the check fails on a balance off by one, on a filter that ignores the kind, on a fold that ignores the ceiling and on a stored count, that it does not fail on time, that the run leaves no store open, and that each form of the kind join gives the model's balances ([PRI-63](../../docs/developer/principles.md)).

## Run it

```bash
mise run check:ledger-credit-kinds
```

```bash
LEDGER_KINDS_QUICK=1 mise run check:ledger-credit-kinds
```

The sizes are 1,000, 5,000 and 20,000 postings at 5% and 30% credits. `LEDGER_KINDS_MAX` caps the postings and `LEDGER_KINDS_QUICK=1` runs the smallest size. The full run took about 6.5 minutes on the laptop below, nearly all of it rdflib at 20,000. Jena needs the test kit jar, built on first use by `mise run bootstrap:sparql-testkit` ([ADR-A125](../../docs/architecture/decisions/ADR-A125-test-support-tooling.md)). Where there is no `java` or no jar, the Jena runs are left out and the report's environment says so. `report.md` and `report.json` are generated, git-ignored and written here. The Oxigraph store is a temporary directory, removed when the run ends, including on failure.

## Measured results

Run of 2026-11-11 on an Apple-silicon laptop, Python 3.14.7, rdflib 7.6.0, pyoxigraph 0.5.13 and Jena ARQ 5.1.0 through the test kit (a Java 25 process, not TDB2). The Jena version is read from the jar the JVM runs. "Rows" is the postings the read counted or, for stepwise, transferred. Times are the mean of 3 read points, at the root.

Time per root read (ms), 30% credits. The root accepts every kind, so all three folds count the same rows. The cap section counts 5,115 of 5,679 at 20,000 postings. The 5% rows are in `report.md`.

| Backend (kind join) | Postings | plain | kind-filtered | stepwise | root rows |
|---|---|---|---|---|---|
| rdflib (optional) | 1,000 | 66 | 117 | 106 | 569 |
| rdflib (optional) | 5,000 | 370 | 613 | 587 | 2,825 |
| rdflib (optional) | 20,000 | 4,498 | 5,463 | 5,412 | 11,358 |
| Oxigraph (union) | 1,000 | 4.4 | 7.6 | 8.8 | 569 |
| Oxigraph (union) | 5,000 | 22.0 | 38.1 | 44.3 | 2,825 |
| Oxigraph (union) | 20,000 | 90.7 | 154.6 | 179.3 | 11,358 |
| Jena (optional) | 1,000 | 10.3 | 10.1 | 33.3 | 569 |
| Jena (optional) | 5,000 | 34.2 | 47.2 | 175.4 | 2,825 |
| Jena (optional) | 20,000 | 138.0 | 190.3 | 753.8 | 11,358 |

Time of all 27 ancestor reads (9 ancestors at 3 read points) against the plain fold, from `report.json`, at 30% credits. At 5% credits rdflib and Oxigraph are within 0.15 of these, and Jena's stepwise factor is 2.9 / 4.6 / 4.8.

| Backend | Postings | kind-filtered | stepwise |
|---|---|---|---|
| rdflib | 1,000 / 5,000 / 20,000 | 1.8 / 1.7 / 1.2 times | 1.6 / 1.6 / 1.2 times |
| Oxigraph | 1,000 / 5,000 / 20,000 | 1.7 / 1.7 / 1.7 times | 1.9 / 2.0 / 2.0 times |
| Jena | 1,000 / 5,000 / 20,000 | 1.2 / 1.3 / 1.4 times | 3.4 / 4.5 / 4.9 times |

The stored triples are 8,154 / 40,338 / 161,086 at 5% credits and 8,408 / 41,600 / 166,112 at 30%, the same on all three engines. The kind adds one triple to each credit, 987 of 161,086 at 5% and 6,013 of 166,112 at 30% (3.6% of the store at 20,000), and the plain fold does not read them.

What the run shows.

1. **The kind filter costs a factor of 1.2 to 1.8 on every engine, and the factor does not grow with the history.** It is a per-posting join, so it scales with the postings folded as the plain fold does. The balances equal the model's, so the filter does not trade correctness for this.
2. **The stepwise fold costs about the kind-filtered fold on rdflib and Oxigraph (1.2 to 2.0 times the plain fold), and 2.9 to 4.9 times on Jena.** On Jena the factor grows with the history, from 3.4 to 4.9 at 30% credits. The extra over the kind-filtered fold is the sort and the transfer of every row, which on Jena crosses a JSON pipe from the JVM to Python (about 11,000 rows in 750 ms at the root). That transfer is a cost of the test kit, and a native Jena caller would not pay it. On rdflib and Oxigraph the rows are Python objects in-process or a native iterator, and the sort and the loop add under 20% to the kind-filtered fold.
3. **The absolute cost is the aggregate's, not the clamp's.** At 20,000 postings a root read is 90 to 180 ms on Oxigraph and up to 750 ms through the Jena kit. The ceiling's loop was not timed apart from the sort and the transfer. Where the balance is wanted often, a checkpoint holding the clamped running balance at each close bounds the rows for all three folds alike, and is not measured here.
4. **The form of the kind join is engine-specific, and the wrong form is a performance problem.** An earlier full run of the same corpus forced one form on every engine. Time of all ancestor reads against the plain fold at 20,000 postings and 30% credits:

   | Backend | optional | union |
   |---|---|---|
   | rdflib | 1.2 times | 6.0 times |
   | Oxigraph | 4.1 times | 1.7 times |
   | Jena | 1.4 times | 1.6 times |

   On Oxigraph the `OPTIONAL` read of a single sublimit cost about the same as the root's, 199 ms against 24 ms for the plain fold in an ad hoc probe, so it behaves like a scan of every kind triple in the store. The `union` form took 33 ms. On rdflib the `union` form took about 8.3 s even for a sublimit, so it scans every graph. We did not check either plan. A generated query for the kind filter should be chosen per engine and tested, as [ADR-A128](../../docs/architecture/decisions/ADR-A128-efficient-queries-and-shapes.md) asks of any generated query.

## What this does not measure

Checkpoints, so every read folds from the start and the cost grows with the history. A clamp at a contract, which a posting reaching an ancestor never passes through, and a ceiling that moves in time. Reads of a contract, which the account's own postings answer. Concurrent writers and late postings. A native Jena store such as TDB2 (the test kit is in memory, [benchmark/ledger-store-comparison](../ledger-store-comparison/README.md) covers TDB2 for the period-graph read) and a Jena caller that does not cross a pipe. The event stream is seeded and the three engines see the same one, so a figure compares folds on one engine, and an engine against another only in its shape.

## Files

| File | What it is |
|---|---|
| `check.py` | the tree, the stream, the model, the three folds on three backends, the pass criterion and the report |
| `test_check.py` | the check's own tests |
| `conftest.py` | makes a temporary folder refuse removal while a store in it is open |
| `report.md`, `report.json` | the last run's results, generated and git-ignored |
