<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Ledger posting cost

A benchmark under [ADR-A124](../../docs/architecture/decisions/ADR-A124-benchmark-root.md). It measures what it costs to record the draws on an account tree, and what it costs to read a balance back, under the choices the ledger history sketch weighs. Until now those costs were judgements. The account model is in the [Ledger README](../../ontology/ledger/README.md), where accounts form a tree by `ldg:partOf` and a draw affects the drawn account and every ancestor.

The tree has depth 3, mirroring a placement: a contract account, the layer it sits on, and the programme the layer belongs to. There are 2 programmes, 5 layers to a programme and 10 contracts to a layer, so 112 accounts. The stream is N events on random contract accounts, four in five a debit and one in five a credit, from a fixed seed. A posting is 8 triples (type, account, owner, key, position, micro-position, direction, amount). The same history is held five ways, on Oxigraph persisted to a temporary directory.

| Strategy | What each event writes | How a balance is read |
|---|---|---|
| every-level | a posting at the contract and at each ancestor | the stated amount, less the account's own debits, plus its own credits |
| post-once | one posting, at the contract | the same fold, over the postings of every account in the subtree, reached by `partOf*` |
| post-once-checkpointed | as post-once, and every 500 events a checkpoint (4 triples) for each of the 112 accounts | the checkpoint at the latest close at or before the point, then the fold over the postings after it |
| post-once-balance-after | as post-once, with `balanceAfter` on each posting (a 9th triple) | a contract from its latest posting at or before the point, an ancestor by the post-once fold |
| post-once-period-graphs | as post-once-checkpointed, with each posting in a named graph keyed by its layer and its period | the same checkpoint, then the fold over exactly the graphs of the periods after it, so earlier postings are never visited |

A closing recurrence fixes the positions at which checkpoints exist, so every strategy that reads one computes the latest close at or before the point and derives the checkpoint's IRI from the account and that position. It never searches for the checkpoint by its properties, which costs an order more and grows with the number of closes ([TSD-36](../../docs/architecture/triple-store-discovery.md#tsd-36-a-bound-object-does-not-give-the-seek-a-bound-subject-gives)).

## What it tests

| Claim | Test |
|---|---|
| Recording at every level costs *d* times recording at the drawn account | the stored triples of every-level against post-once |
| A subtree fold gives the balance an ancestor's own postings give | every account at every read point, in all five strategies, against a plain model |
| A checkpoint bounds the fold | postings folded per read, checkpointed against post-once |
| A running balance makes a contract read one lookup | postings folded and time per contract read, balance-after against post-once |
| Naming the periods' graphs bounds the read in time, not only in postings folded | time per read, period-graphs against checkpointed, across the sizes |

## Pass criterion

For every account and every read point, each strategy reports the model's balance, so all five report the same balance. The read points are before any event, the first event, a third and a half of the way through, on a checkpoint, just after one, and the last two events. The stored triples have the count each strategy's arithmetic gives (`expected_stored`). A checkpointed or period-graph read never folds more postings than the same read without checkpoints. **A wrong balance or count fails the check. Time never does.** Timings, triples and postings folded go to `report.md` and `report.json` here, which are generated and git-ignored. A figure quoted elsewhere states its run (ADR-A124 decision 5), as the report's first line does.

## Run it

```bash
mise run check:ledger-posting-cost
```

```bash
LEDGER_COST_QUICK=1 mise run check:ledger-posting-cost
```

```bash
LEDGER_COST_PROBE=100000 mise run check:ledger-posting-cost
```

The default sizes are 1,000, 5,000 and 20,000 events, and the full run takes about 30 seconds. `LEDGER_COST_MAX` caps the sizes and `LEDGER_COST_QUICK` runs the smallest alone. `LEDGER_COST_PROBE` runs one size of its own instead of the defaults, which is how the 100,000-event figures below were produced, in about 90 seconds. It is never a dependency of `check`. The store is created in a temporary directory that is removed when the run ends, including on failure, and nothing is written into the repository except the two report files.

We used `pyoxigraph` directly. The [Oxigraph test-support package](../../tools/testing/oxigraph/README.md) is in memory only, and a persistent store keeps the process small enough to raise the size. rdflib is in memory and slower to load, so it was not used.

## Measured results

Run of 2026-10-24 on a laptop, Python 3.14, pyoxigraph 0.5.13, at 20,000 events. Each read figure is the mean over the accounts of that level and the 8 read points. "Folded" is the number of postings a read summed.

| Strategy | Stored triples | Per event | Write s | Contract ms (folded) | Layer ms (folded) | Programme ms (folded) |
|---|---|---|---|---|---|---|
| every-level | 480,334 | 24.0 | 2.53 | 0.96 (72.1) | 8.68 (720.8) | 42.39 (3604.2) |
| post-once | 160,334 | 8.0 | 0.83 | 0.95 (72.1) | 8.65 (720.8) | 43.14 (3604.2) |
| post-once-checkpointed | 178,254 | 8.9 | 0.86 | 0.74 (0.8) | 6.57 (8.3) | 32.84 (41.7) |
| post-once-balance-after | 180,334 | 9.0 | 0.93 | 0.75 (0.7) | 8.86 (720.8) | 43.70 (3604.2) |
| post-once-period-graphs | 178,254 | 8.9 | 0.77 | **0.09** (0.8) | **0.12** (8.3) | **0.34** (41.7) |

The programme read, by size, with the 100,000-event column from a `LEDGER_COST_PROBE` run of the same date.

| Strategy | 1,000 | 5,000 | 20,000 | 100,000 |
|---|---|---|---|---|
| post-once | 2.66 ms | 11.12 ms | 43.14 ms | 261.13 ms |
| post-once-checkpointed | 2.19 ms | 8.81 ms | 32.84 ms | 217.53 ms |
| post-once-period-graphs | 0.40 ms | 0.34 ms | 0.34 ms | 0.54 ms |

What the run shows.

1. **Recording at every level costs *d* times the postings.** The stored triples of every-level are 2.996 times those of post-once at 20,000 events, and exactly 3 times once the 334 triples of the tree itself are set aside. This holds the arithmetic and does not depend on the engine.
2. **The balances agree.** All five strategies read the model's balance for all 112 accounts at all 8 read points, at every size. A divergence fails the run.
3. **Post-once reads an ancestor at the cost of the subtree.** The fold grows with the history, from 238 postings at 1,000 events to 3,604 at 20,000 for a programme, and the time grows with it, from 2.7 ms to 43 ms. Post-once contract reads cost the same as every-level reads, since a contract's postings are the same in both.
4. **Checkpoints cut the postings folded by a factor of 86 at a programme, and barely cut the time.** A fold of 3,604 postings becomes 42 and no longer grows with the history, while the time falls only from 43.1 ms to 32.8 ms. The position bound in the fold is a `FILTER`, so the engine visits every posting of the subtree before the filter applies. **A checkpoint alone bounds the arithmetic and not the scan.**
5. **A running balance makes a contract read one posting.** The contract fold falls from 72.1 postings to 0.7. The time saving is small because a contract has few postings, and it does nothing for an ancestor, which has no postings of its own under post-once.
6. **Checkpoints and balance-after cost storage.** Checkpoints add 0.9 triples per event at 112 accounts and a close every 500 events, which is a cost of accounts times closes and not of events. Balance-after adds 1 triple per event.
7. **Naming the periods' graphs removes the scan floor, and the read goes flat.** The programme read is 0.40, 0.34, 0.34 and 0.54 ms at 1,000, 5,000, 20,000 and 100,000 events, so it does not grow with the history over a hundredfold range. The same read checkpointed grows from 2.19 ms to 217.53 ms, so the saving grows from 5 times to 403 times. **The postings folded are identical to the checkpointed strategy's at every account and read point, and so are the stored triples**, at 178,254 at 20,000 events and 889,934 at 100,000, since a posting's 8 quads count the same in a named graph. The write time is the same within the noise. The whole gain is in postings the engine no longer visits. Layer reads fall from 6.57 ms to 0.12 ms and contract reads from 0.74 ms to 0.09 ms.
8. **The position filter that remains is at the boundary of the read.** A graph is taken whole unless the read point falls inside its period. Checkpoints close on period ends, so the lower bound never cuts a period, and the filter is needed only for the period holding the read point, and not at all when the point is itself a period end. Whole periods between the two carry no filter. A contract read still names its own account, since a graph holds the ten contracts of a layer. We tried `VALUES ?g` with `GRAPH ?g` and a union of `GRAPH <name>` blocks, and they were within about 10% of each other, so we kept `VALUES` because it is shorter.
9. **Deriving the checkpoint's IRI removes the one term that still grew.** Searching for the latest checkpoint with a filter and a sort cost 0.04 ms at 2 closes an account and 1.06 ms at 200, growing with the closes and so with time, which made it the next floor once finding 7 had flattened the fold. Computing the close position from the interval and naming the checkpoint directly is flat, at 0.020 to 0.023 ms over the same range. Binding the position as an object rather than naming the subject gives only half the saving and still grows. The measurement and the mechanism are [TSD-36](../../docs/architecture/triple-store-discovery.md#tsd-36-a-bound-object-does-not-give-the-seek-a-bound-subject-gives). All the figures above use the derived form, so findings 4 and 5 are reported with it too.

## Extrapolation

This section extrapolates from the measurements above and was not run.

**On the scenario.** The ledger history sketch set the scenario as depth 3 and 10 million events a year, and the figures below take that as one tree and so as a **worst case rather than an expected layout**. In an operational system the partition is likely to be the programme, since a claim is calculated against one placement and no correctness query crosses two. An enterprise rate of 10 million events a year spread over some thousands of active programmes gives each one a few thousand postings a year, which the first row below reads in about 9 ms with no mechanism beyond post-once. The mechanisms measured here are what a layout that cannot be partitioned that cleanly would need. [multi-store-runtime.md](../../docs/developer/sketches/multi-store-runtime.md) argues the partition question.

| Quantity | Extrapolated | Basis |
|---|---|---|
| One programme's own year, 2,000 postings, read by post-once | about 9 ms | 4.3 µs per subtree posting visited, measured at 10,000 postings |
| Postings stored, every-level | 240 million triples a year | 24.0 triples per event, linear in events |
| Postings stored, post-once | 80 million triples a year | 8.0 triples per event |
| Checkpoint overhead | accounts × closes × 4 triples | independent of event count, 0.9 triples per event here |
| Programme fold, post-once, one tree | 5 million postings at the end of a year if two programmes share the stream | linear in the history, as the 1,000 to 100,000 series is |
| Programme read time, post-once, one tree | of the order of 20 seconds at that size | the 4.3 µs constant times the subtree |
| Programme read time, checkpointed, one tree | of the same order, since the filter does not seek | finding 4, and the 217 ms at 100,000 events |
| Programme read time, period graphs | set by the closing interval rather than by the history, since the fold visits only the periods since the close | finding 7's flatness, and about 2 µs per posting in the interval |
| Graphs held | layers × periods | 400 at 20,000 events here. A year of daily closes over many layers reaches a far larger number, which we did not measure |

The 240 million is the postings alone and sits below the sketch's 450 million, which also counts a balance record of about 7 triples per account touched. We did not write balance records, so the benchmark confirms the factor of *d* and not the 450 million.

**What we did not measure.** The cost of a very large number of graphs, which is the open risk in finding 7. A posting arriving late into a period already closed, since the stream is append-only. Any archive or restore path. The behaviour of a second engine, so every finding here is Oxigraph's.

## Files

| File | Role |
|---|---|
| `check.py` | the tree, the stream, the five strategies, the model, the pass criterion and the report |
| `test_check.py` | the check's own tests, including that a wrong balance, a wrong count and an over-wide fold fail it, that time does not, and that the temporary store is removed |
