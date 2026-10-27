<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Review: CAP-84 and CAP-85, the two new ledger benchmarks

**Raised:** 2026-10-27
**For:** ratification of two capability rows in the [capability register](../capabilities.md)
**Unit:** [`ledger`](../status/ledger.md)
**Status record:** the measurements are recorded in [benchmark/ledger-posting-cost](../../../benchmark/ledger-posting-cost/README.md) and [benchmark/ledger-store-comparison](../../../benchmark/ledger-store-comparison/README.md)
**Decisions they serve:** MS-Q9 (answered), the ADR-A67 addendum of 2026-10-27, [TSD-40](../../architecture/triple-store-discovery.md)

Both rows are marked unratified. This note is what each one claims, why it exists, what it is not, and the one thing about each worth disagreeing with.

## CAP-84, the partition sweep

**Claim.** Measure what a finer graph partition costs, by holding the events fixed and shortening the closing period so the named graphs multiply (ADR-A124).

**Entry point.** `mise run check:ledger-graph-partition`, which is `sweep.py` beside the existing `check.py` in the same module rather than a module of its own, since it reuses that benchmark's tree, stream and model wholesale.

**Why it exists.** The multi-store sketch's MS-Q9 asked whether a store degrades as the number of named graphs rises, which bounds how fine the period partition may be. The question was unanswered and the sketch's leaning depended on it.

**What it found.** No read ceiling in range. The graphs rise 327 times, from 40 to 13,082, and the read falls monotonically from 6.683 ms to 0.132 ms. The cost is storage and write time, rising 6.5 and 5.5 times, which is the `accounts × closes × 4` checkpoint arithmetic rather than anything to do with graphs. So the limit on partition fineness is storage.

**What it is not.** It is one engine. The SST-file and open-file parts of the finding are RocksDB's, and nothing in them transfers to a B+tree or an in-memory store, which is why CAP-85 exists. It does not sweep the tree's width, only the period.

**Worth disagreeing with.** The sweep holds the event count at 20,000 and shortens the period, so the finest partition also has the smallest fold, and the read time falls for two reasons at once. A cleaner experiment would hold the fold constant and vary only the graph count, which would need a different generator. The present shape answers the design question (how fine may we go) without isolating the mechanism (what does a graph cost). If the isolated number matters later, this benchmark does not give it.

## CAP-85, the store comparison

**Claim.** Measure whether the ledger's period-graph partition bounds an aggregate read on Jena TDB2 as it does on Oxigraph, so the result is a property of naming the graphs rather than of one engine (ADR-A124, STD-176).

**Entry point.** `mise run check:ledger-store-comparison`, a standalone Maven project under `benchmark/`, outside the platform reactor, depending on `jena-tdb2` at the version the reactor already manages.

**Why it exists.** Every figure behind the period-graph design was Oxigraph's. STD-176 makes a cost measured on one engine a hypothesis for another, and TSD-40 showed that a patch version of one engine moved a property path's cost by 2.4 times. A design resting on one engine's behaviour needed a second.

**What it found.** The shape replicates. On TDB2 the filtered subtree fold grows from 9.16 ms to 49.31 ms across a twentyfold history while the period-graph read stays between 1.38 ms and 2.73 ms, so the saving grows from 3.4 times to 36 times. The partition is doing the work, not the storage engine.

**What it is not.** Not a comparison of engines. The Java stream is not the Python one, so the two benchmarks see the same volume and structure but not the same draws, and no figure from one should be set against a figure from the other. Only the shape of each curve is comparable. It measures one aggregate at one depth, two strategies of the five, and no concurrency.

**Worth disagreeing with.** Two things. The first TDB2 reading of each run carries JIT warm-up, which is why 1,000 events reads slower than 20,000, and seven repetitions with a median is a thin defence against that. And **writing costs more with the partition on TDB2**, 1.32 s against 0.63 s at 20,000 events, where on Oxigraph the two were within noise. The checkpoints are most of the extra quads. That is the one measured result pointing against the design, it is unexplained, and anything write-heavy leaning on the partition should measure it first.

## What ratifying each one commits us to

| | Commits us to |
|---|---|
| CAP-84 | keeping a sweep that answers how fine a partition may be on Oxigraph, and re-running it when the closing recurrence or the checkpoint shape changes |
| CAP-85 | keeping a second engine in the benchmark set, so a Jena toolchain stays installable, and re-running both when a store-dependent figure is quoted in a design |

Neither is in `check`. Both fail on a wrong balance and never on time, as ADR-A124 requires, and both remove their temporary stores on failure.

## Open question for the reviewer

**LB-Q1.** Should the store comparison grow to the other three strategies, or stay at the two that carry the claim? Staying is cheaper to keep correct and answers the question asked. Growing would let a figure from either benchmark be read against the other, which needs the streams to agree, which needs the event stream to become a committed fixture rather than a seeded generator. That is a real change and it is not obviously worth it.
