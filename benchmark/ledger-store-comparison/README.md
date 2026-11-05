<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Ledger store comparison

A benchmark under [ADR-A124](../../docs/architecture/decisions/ADR-A124-benchmark-root.md). It asks whether the ledger's period-graph partition bounds an aggregate read on a store of a different architecture, or whether the result is a property of one engine.

[benchmark/ledger-posting-cost](../ledger-posting-cost/README.md) measured, on Oxigraph, that a programme's balance read behind a position filter grows with the history while the same read over named period graphs stays flat. Oxigraph keeps its data in RocksDB, a log-structured merge tree. Jena TDB2 keeps its in B+tree indexes with a node table, and runs on the JVM. If the result holds on both, it is a property of naming the graphs rather than of one engine's storage ([STD-176](../../docs/developer/standards.md), and [TSD-40](../../docs/architecture/triple-store-discovery.md#tsd-40-a-zero-or-more-property-paths-cost-changed-between-oxigraph-0511-and-0513), where a patch version alone moved a path's cost by 2.4 times).

## What it does

The account tree, the event mix and the two strategies mirror the posting-cost benchmark: 2 programmes, 5 layers to a programme, 10 contracts to a layer, four events in five a debit, and a read of a programme's balance at depth 3.

| Strategy | What each event writes | How the balance is read |
|---|---|---|
| post-once | one posting at the contract, in the default graph | a fold over the subtree, reached by `partOf*`, behind a position filter |
| post-once-period-graphs | one posting at the contract, in a named graph keyed by its layer and period, plus a checkpoint per account at each close | the checkpoint at the latest close, addressed by a derived IRI, then a fold over exactly the graphs of the periods after it |

The read is taken mid-period, so the fold covers a partial period's graphs rather than landing on a close where the checkpoint answers alone.

**The event streams of the two benchmarks differ.** Java's generator is not Python's, so the two engines see the same volume and structure but not the same draws. Only the shape of each engine's curve is comparable, never a figure against a figure. Each run checks itself against a model computed in the same process by plain arithmetic.

## Pass criterion

The programme's balance, by both strategies, equals the model's. **A wrong balance fails the run. Time never does.** A failure names the strategy, the event count, the balance read and the balance expected.

## Run it

```bash
mise run check:ledger-store-comparison
```

```bash
mise exec -- mvn -q -f benchmark/ledger-store-comparison/pom.xml exec:java -Dledger.store.max=5000
```

The sizes are 1,000, 5,000 and 20,000 events and the run takes about a minute including the build. `ledger.store.max` caps them. It is never a dependency of `check`. Each size builds a TDB2 store in a temporary directory, which is removed when the run ends, including on failure, and nothing is written into the repository.

## Measured results

Run of 2026-10-27, run R-I of the [discovery record](../../docs/architecture/triple-store-discovery.md), Jena 5.1.0 on Java 25. "Folded" is the number of postings the read summed.

| Strategy | Events | Quads | Write s | Read ms | Folded |
|---|---|---|---|---|---|
| post-once | 1,000 | 8,334 | 0.20 | 9.162 | 349 |
| post-once-period-graphs | 1,000 | 9,230 | 0.16 | 2.731 | 116 |
| post-once | 5,000 | 40,334 | 0.21 | 17.755 | 2,353 |
| post-once-period-graphs | 5,000 | 44,814 | 0.40 | 1.576 | 133 |
| post-once | 20,000 | 160,334 | 0.63 | 49.311 | 9,849 |
| post-once-period-graphs | 20,000 | 178,254 | 1.32 | 1.381 | 117 |

What the run shows.

1. **The result is not Oxigraph's alone.** On TDB2 the filtered subtree fold grows from 9.16 ms to 49.31 ms as the history grows twentyfold, and the period-graph read stays between 1.38 ms and 2.73 ms. The saving grows from 3.4 times to 36 times. The shape is the same as Oxigraph's, where the same two reads are 2.66 ms to 43.89 ms and 0.40 ms to 0.36 ms.
2. **The absolute cost is not the same, and should not be read as a comparison of engines.** TDB2's period-graph read is of the order of four times Oxigraph's, and its filtered fold is within about ten per cent. The streams differ, the languages differ, and the first TDB2 reading of each run carries JIT warm-up, which is why 1,000 events reads slower than 20,000.
3. **The postings folded are bounded on both.** The period-graph read folds about 120 postings at every size, where the filtered fold grows to 9,849. That is the arithmetic the partition fixes, and it is engine-independent by construction.
4. **Writing costs more with the partition on TDB2**, 1.32 s against 0.63 s at 20,000 events, where on Oxigraph the two were within noise. The checkpoints are most of the extra quads, and TDB2's write path pays more for them. Worth measuring again before a write-heavy design leans on it.

## What this does not measure

A third architecture, such as an in-memory reasoner. A partition fine enough to stress the number of graphs, which the Oxigraph sweep covers. Any archive, restore or materialisation path. Concurrent writers. The event stream is append-only, so a posting arriving late into a closed period is untested.

## Files

| File | Role |
|---|---|
| `pom.xml` | a standalone Maven project, outside the platform reactor, depending on `jena-tdb2` |
| `src/main/java/.../StoreComparison.java` | the tree, the stream, the model, the two strategies, the pass criterion and the report |
