<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Ledger credit kinds on native Jena

A benchmark under [ADR-A124](../../docs/architecture/decisions/ADR-A124-benchmark-root.md). It repeats [benchmark/ledger-credit-kinds](../ledger-credit-kinds/README.md) on Jena called from Java, so the stepwise fold's ordered query is folded in Java and its rows do not cross the test kit's JSON pipe, which made the stepwise fold look 3.4 to 4.9 times the plain fold. It runs on Jena in memory (an ARQ query over a transactional in-memory dataset) and on Jena TDB2 on disk in a temporary directory that is removed afterwards, with the same corpora, the same four reads (plain, kind-filtered, stepwise, shortcut), from the start of history and from the last checkpoint, and each form of the kind join. It adds no dependency to [benchmark/ledger-store-comparison](../ledger-store-comparison/README.md), whose Jena 5.1.0 and TDB2 it uses.

## How it runs

The Python benchmark writes each corpus as N-Quads and, for every read, the balance and posting count the model gives, as `expected.json` (`check.py --emit`). Both go to `target/corpus/`, which is git-ignored. This module loads a corpus, builds the same query text as `check.py` does, runs every read, checks every balance and posting count against the expected values, and writes its timings to `report.json` in the shape of the Python report. `check.py --merge` then adds them to the Python benchmark's `report.md`. The stepwise fold's time is split into the ordered query, the transfer of its rows into Java arrays, and the clamping loop. The Jena version is read at runtime from the jar the JVM loads.

## Pass criterion

Every read equals the model's balance and posting count, every shortcut read equals the model's stepwise balance, and the store holds the stored count the arithmetic gives. **A wrong balance or count prints `WRONG RESULT`, exits non-zero and writes no report, so the task fails. Time never does.** `test_jvm.py` shows the run passes on the emitted corpus and fails on a wrong balance, a wrong posting count and a wrong shortcut balance.

## Run it

```bash
mise run check:ledger-credit-kinds-jvm
```

```bash
LEDGER_KINDS_QUICK=1 mise run check:ledger-credit-kinds-jvm
```

The task runs the tests, writes the corpora, runs the JVM with a 2 GB heap cap and merges the timings. It takes about a minute and a half at the full sizes (1,000, 5,000 and 20,000 postings at 5% and 30% credits). `LEDGER_KINDS_MAX` and `LEDGER_KINDS_QUICK` shorten it as they do the Python benchmark, and `-Dkinds.forms=optional` or `union` on the `mvn` command runs one form. Maven fetches Jena on first use. It is never a dependency of `check`. The results are in the Python benchmark's README.

| File | Role |
|---|---|
| `pom.xml` | Jena 5.1.0 (TDB2) and a no-op logger, as the sibling benchmarks |
| `src/main/java/org/nebularis/lattice/benchmark/creditkinds/CreditKinds.java` | the stores, the reads, the checks and the report |
| `test_jvm.py` | the caller's own tests |
