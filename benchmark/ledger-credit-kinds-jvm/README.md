<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Ledger credit kinds on native Jena

A benchmark under [ADR-A124](../../docs/architecture/decisions/ADR-A124-benchmark-root.md). It repeats [benchmark/ledger-credit-kinds](../ledger-credit-kinds/README.md) on Jena called from Java, so the stepwise fold's ordered query is folded in Java and its rows do not cross the test kit's JSON pipe, which made the stepwise fold look 3.4 to 4.9 times the plain fold. It runs on Jena in memory (an ARQ query over a transactional in-memory dataset) and on Jena TDB2 on disk in a temporary directory that is removed afterwards. It adds no dependency to [benchmark/ledger-store-comparison](../ledger-store-comparison/README.md), whose Jena 5.1.0 and TDB2 it uses. It does three things, in two tasks.

| Task | What it runs |
|---|---|
| `check:ledger-credit-kinds-jvm` | the one-level corpus (plain, kind-filtered, stepwise and shortcut, from the start of history and from the last checkpoint, in each form of the kind join), the two-level corpus with the cuts the writer recorded (plain, kind-filtered, `kind-filtered-union`, stepwise and sum-with-cuts, from the start and from the last checkpoint), and the query plans Jena gives three of the root's reads |
| `check:ledger-credit-kinds-jvm-writes` | the ledger's live writer and a counter probe of the store's concurrency, each run exported and audited in Python |

## How the reads run

The Python benchmark writes each corpus as N-Quads and, for every read, the balance and posting count the model gives, as `expected.json` (`check.py --emit`). Both go to `target/corpus/`, which is git-ignored. This module loads a corpus, builds the same query text as `check.py` does, runs every read, checks every balance and posting count against the expected values, and writes its timings to `report.json` in the shape of the Python report. `check.py --merge` then adds them to the Python benchmark's `report.md`, as "Native Jena (Java)" for the one-level corpus and "Native Jena (Java), two-level corpus" for the other. The stepwise fold's time is split into the ordered query, the transfer of its rows into Java arrays, and the clamping loop. The sum with cuts is split into its postings aggregate and its cuts aggregate. The Jena version is read at runtime from the jar the JVM loads.

The two-level corpus is emitted at each size and at 5% and 30% credits, and read in one kind join form, `optional`, which is Jena's default in the Python benchmark (`-Dkinds.forms2=optional,union` reads both). The expected values include the model's sum of applied amounts, so each full read of the sum with cuts also shows that the postings alone are wrong where the model says they are, which is the defect the cut repairs. The shortcut is not read on the two-level corpus.

## The plans

For the root account's full read of the largest two-level corpus at 30% credits, the run writes `target/plans.txt` (git-ignored, `-Dkinds.plans` moves it) with what Jena will run for three queries, the kind-filtered fold in the OPTIONAL form, `kind-filtered-union` and the cuts aggregate of the sum with cuts. For each it prints the algebra as compiled, the algebra after ARQ's optimiser (`Algebra.optimize`), and for TDB2 also the quad form (`Algebra.toQuadForm`) and the triple order that TDB2's own reordering transformation gives each pattern. The rows of the `VALUES ?g` table are listed for the first two graphs and the last. ARQ's execution logging goes through SLF4J, which this module binds to a no-op logger, so the log of the reordering is not available and the store's reordering transformation is asked directly. The reading is in the [Python benchmark's README](../ledger-credit-kinds/README.md).

## The writes

`writes.py --emit-jvm` writes, to `target/writes/`, the account tree, a preload of the two-level corpus at 30% credits with the ledger's revision triple at each size (1,000, 5,000 and 20,000 postings), the request lists (the same seeds as the Python benchmark's single writer and stress, so the runs are comparable) and the plan of the runs. `LedgerWrites` then runs, on Jena in memory and on TDB2, with threads in one JVM against one dataset:

| Run | What it does |
|---|---|
| the probe (C1) | a counter triple. Each thread reads the counter N, sends `DELETE { N } INSERT { N+1 and its marker } WHERE { N }` as one update request in its own write transaction, and asks in a read transaction whether its marker exists, until the counter reaches 1,000. Then the increment in the store, 500 times a thread. 1, 2, 4 and 8 threads, three runs a cell |
| the single writer | 500 writes on stores of 1,000, 5,000 and 20,000 postings, guarded and unguarded, with the time of each write split into path reads, settle, update and confirm |
| the stress | 1, 2, 4 and 8 threads, 1,000 requests in all on a store of 5,000, guarded (three runs a cell at 2, 4 and 8) and once unguarded |
| one writer per ledger (LG-18, written 2026-11-12 and not yet run) | producers hand the stress's requests to one writer through a queue. Closed runs with 1, 2, 4 and 8 producers, by a writer that reads its path and by one that keeps the balances it has settled. Backlog runs by both, by the keeper with no guard, and by the keeper writing batches of 10 and of 100 in one update. Every export is held to the replay |

The writer is the port of `writes.py`'s. It reads the revision and the sum with cuts of every account on the posting's path from the last checkpoint, in one read transaction, settles with the benchmark's arithmetic, refuses a debit larger than the balance of any account on its path, and writes the posting, its applied amount, kind and cuts and the new revision in one guarded update, confirmed by asking for its own posting. After each run the dataset is exported as gzipped N-Quads, and `writes.py --audit-jvm` loads each export into an in-memory Oxigraph and runs `audit` on it, the replay of the commits in revision order through the benchmark's writer. The replay is Python's and none is written in Java. A guarded run on a store is asserted against the replay only if the probe showed that store kept the guard in every guarded run at two threads or more, and is otherwise audited and reported. An unguarded run is never asserted.

## Pass criterion

For the reads, every read equals the model's balance and posting count, every shortcut read equals the model's stepwise balance, the postings alone of the sum with cuts equal the model's sum of applied amounts and differ from the stepwise balance at as many ancestors as the model says, and the store holds the stored count the arithmetic gives. For the writes, every preload holds its stored count, a single writer never loses a race and the store grows by the triples the writes add, and the audit holds as above. **A wrong balance, count or audit prints `WRONG RESULT`, exits non-zero and writes no report, so the task fails. Time never does, and neither does anything the probe shows about the store.** `test_jvm.py` shows the read run passes on the emitted corpora and fails on a wrong balance, a wrong posting count, a wrong shortcut balance, a wrong expected value of any of the five two-level folds, and a wrong model sum of applied amounts. `test_jvm_writes.py` shows the audit fails on an export whose stored cut was changed and on one with a duplicate revision, that a store whose probe lost a guarded update is not held to the replay, that a small native run is audited and passes, and that a Java run fails on a preload that is not the corpus.

## Run it

```bash
mise run check:ledger-credit-kinds-jvm
mise run check:ledger-credit-kinds-jvm-writes
```

```bash
LEDGER_KINDS_QUICK=1 mise run check:ledger-credit-kinds-jvm
LEDGER_WRITES_QUICK=1 mise run check:ledger-credit-kinds-jvm-writes
```

Each task runs its tests, writes its inputs, runs the JVM with a 2 GB heap cap and finishes the report. Neither is ever a dependency of `check`, and each fails on a wrong result and never on time (ADR-A124). `LEDGER_KINDS_MAX` and `LEDGER_KINDS_QUICK` shorten the first as they do the Python benchmark, `-Dkinds.forms=optional` or `union` on the `mvn` command runs one form of the one-level corpus, and `LEDGER_WRITES_QUICK` and `LEDGER_WRITES_REPORT_DIR` act as they do for the Python writes benchmark. Maven fetches Jena on first use. The results are in the Python benchmark's README.

| File | Role |
|---|---|
| `pom.xml` | Jena 5.1.0 (TDB2) and a no-op logger, as the sibling benchmarks, and the arguments of the two main classes |
| `src/main/java/org/nebularis/lattice/benchmark/creditkinds/CreditKinds.java` | the stores, the reads, the checks and the report of the first task |
| `src/main/java/org/nebularis/lattice/benchmark/creditkinds/Plans.java` | the plans |
| `src/main/java/org/nebularis/lattice/benchmark/creditkinds/LedgerWrites.java` | the probe, the live writer, the stress and the exports |
| `test_jvm.py` | the read run's own tests |
| `test_jvm_writes.py` | the write run's and the audit's own tests |

The reports are generated and git-ignored. `report.json` and the merged `report.md` are the first task's, and `writes-report.md` and `writes-report.json` the second's, written here and not to the Python benchmark's folder. `target/` holds the corpora, the exports and the plans.
