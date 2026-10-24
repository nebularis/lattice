<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Ledger posting cost

A benchmark under [ADR-A124](../../docs/architecture/decisions/ADR-A124-benchmark-root.md). It measures what it costs to record the draws on an account tree, and what it costs to read a balance back, under the choices the ledger history sketch weighs. Until now those costs were judgements. The account model is in the [Ledger README](../../ontology/ledger/README.md), where accounts form a tree by `ldg:partOf` and a draw affects the drawn account and every ancestor.

The tree has depth 3, a leaf, a programme aggregate and an authority aggregate, with 2 authorities, 10 programmes and 100 leaves. The stream is N events on random leaves, four in five a debit and one in five a credit, from a fixed seed. A posting is 8 triples (type, account, owner, key, position, micro-position, direction, amount). The same history is held in five ways, on Oxigraph persisted to a temporary directory.

| Strategy | What each event writes | How a balance is read |
|---|---|---|
| every-level | a posting at the leaf and at each ancestor | the stated amount, less the account's own debits, plus its own credits |
| post-once | one posting, at the leaf | the same fold, over the postings of every account in the subtree, reached by `partOf*` |
| post-once-checkpointed | as post-once, and every 500 events a checkpoint (4 triples) for each of the 112 accounts | the latest checkpoint at or before the point, then the fold over the postings after it |
| post-once-balance-after | as post-once, with `balanceAfter` on each posting (a 9th triple) | a leaf from its latest posting at or before the point, an ancestor by the post-once fold |
| post-once-period-graphs | as post-once-checkpointed, with each posting's 8 triples in a named graph keyed by the leaf's programme and the period `(event - 1) // 500` | the latest checkpoint, then a fold over exactly the graphs of the programmes in the subtree and the periods after it, with no join to the account tree |

## What it tests

| Claim | Test |
|---|---|
| Recording at every level costs *d* times recording at the drawn account | the stored triples of every-level against post-once |
| A subtree fold gives the balance an ancestor's own postings give | every account at every read point, in all five strategies, against a plain model |
| A checkpoint bounds the fold | postings folded per read, checkpointed against post-once |
| A running balance makes a leaf read one lookup | postings folded and time per leaf read, balance-after against post-once |
| Naming the graphs of the periods since the last checkpoint removes the scan floor, so an ancestor read is bounded in time as well as in work | time per authority read, period-graphs against checkpointed, at 1,000, 5,000 and 20,000 events |
| Moving a posting into a named graph does not change what is stored | stored triples, period-graphs against checkpointed |

## Pass criterion

For every account and every read point, each strategy reports the model's balance, so all five report the same balance. The read points are before any event, the first event, a third and a half of the way through, on a checkpoint, just after one, and the last two events. The stored triples have the count each strategy's arithmetic gives (`expected_stored`). A checkpointed read never folds more postings than the same read without checkpoints, and a period-graph read never folds more than the checkpointed read. **A wrong balance or count fails the check. Time never does.** Timings, triples and postings folded go to `report.md` and `report.json` here, which are generated and git-ignored. A figure quoted elsewhere states its run (ADR-A124 decision 5), as the report's first line does.

## Run it

```bash
mise run check:ledger-posting-cost
LEDGER_COST_MAX=5000 mise run check:ledger-posting-cost    # caps the events
LEDGER_COST_QUICK=1 mise run check:ledger-posting-cost     # the smallest size only
```

The sizes are 1,000, 5,000 and 20,000 events, and the full run takes about 30 seconds, of which about 5 are the check's own tests. It is never a dependency of `check`. The store is created in a temporary directory that is removed when the run ends, including on failure, and nothing is written into the repository except the two report files.

We used `pyoxigraph` directly. The [Oxigraph test-support package](../../tools/testing/oxigraph/README.md) is in memory only, and a persistent store keeps the process small enough to raise the size. rdflib is in memory and slower to load, so it was not used.

## Measured results

Run of 2026-10-24 on a laptop, Python 3.14, pyoxigraph 0.5.13, at 20,000 events, the full run of `mise run check:ledger-posting-cost` that wrote the current `report.md`. Every figure in this README comes from that run unless it says otherwise. Each read figure is the mean over the accounts of that level and the 8 read points. "Folded" is the number of postings a read summed.

| Strategy | Stored triples | Per event | Write s | Leaf read ms (folded) | Programme read ms (folded) | Authority read ms (folded) |
|---|---|---|---|---|---|---|
| every-level | 480,334 | 24.0 | 2.63 | 0.99 (72.1) | 8.97 (720.8) | 44.08 (3604.2) |
| post-once | 160,334 | 8.0 | 0.80 | 1.00 (72.1) | 9.39 (720.8) | 45.72 (3604.2) |
| post-once-checkpointed | 178,254 | 8.9 | 0.88 | 1.67 (0.8) | 7.01 (8.3) | 34.44 (41.7) |
| post-once-balance-after | 180,334 | 9.0 | 0.96 | 0.77 (0.7) | 9.17 (720.8) | 45.24 (3604.2) |
| post-once-period-graphs | 178,254 | 8.9 | 0.83 | 0.25 (0.8) | 0.28 (8.3) | 0.53 (41.7) |

The authority read across the three sizes, in milliseconds with the postings folded in brackets, from the same run.

| Strategy | 1,000 events | 5,000 events | 20,000 events |
|---|---|---|---|
| post-once | 2.76 (238.1) | 11.75 (947.9) | 45.72 (3604.2) |
| post-once-checkpointed | 2.25 (59.6) | 8.82 (41.7) | 34.44 (41.7) |
| post-once-period-graphs | 0.45 (59.6) | 0.38 (41.7) | 0.53 (41.7) |

What the run shows.

1. **Recording at every level costs *d* times the postings.** The stored triples of every-level are 2.996 times those of post-once at 20,000 events, and exactly 3 times once the 334 triples of the tree itself are set aside. This holds the arithmetic and does not depend on the engine.
2. **The balances agree.** All five strategies read the model's balance for all 112 accounts at all 8 read points, at every size. A divergence fails the run.
3. **Post-once reads an ancestor at the cost of the subtree.** The fold grows with the history, from 238 postings at 1,000 events to 3,604 at 20,000 for an authority, and the time grows with it, from 2.8 ms to 46 ms. Post-once leaf reads cost the same as every-level reads, since a leaf's postings are the same in both.
4. **Checkpoints cut the postings folded by a factor of 86 at an authority.** A fold of 3,604 postings becomes 42, and it no longer grows with the history. The time falls by much less, from 46 ms to 34 ms. In our query the position bound is a filter, so the engine still visits every posting of the subtree before the filter applies. A leaf read is slower with checkpoints (1.67 ms against 1.00 ms) because it adds a checkpoint lookup to a fold that was already small. The sketch's claim that a checkpoint bounds the read holds for the work folded, and holds for time only if the detail before the checkpoint is out of the hot store or the store can seek by position. Finding 7 measures a way of keeping the older detail from being visited.
5. **A running balance makes a leaf read one posting.** The leaf fold falls from 72.1 postings to 0.7, and the time from 1.00 ms to 0.77 ms. The saving in time is small here because a leaf has few postings. It does not help an ancestor, since an ancestor has no postings of its own under post-once.
6. **Checkpoints and balance-after cost storage.** Checkpoints add 0.9 triples per event at 112 accounts and a close every 500 events, which is a cost of accounts times closes and not of events. Balance-after adds 1 triple per event.
7. **Naming the graphs of the periods since the last checkpoint removes the scan floor.** The authority read takes 0.45 ms at 1,000 events, 0.38 ms at 5,000 and 0.53 ms at 20,000, folding 59.6, 41.7 and 41.7 postings. The same read in the checkpointed strategy takes 2.25, 8.82 and 34.44 ms, so the saving grows from 5 times to 65 times as the history grows from 1,000 to 20,000 events. The postings folded are the same as the checkpointed strategy's at every account and read point, so the saving is all in the postings the engine no longer visits. Programme reads fall from 7.01 ms to 0.28 ms and leaf reads from 1.67 ms to 0.25 ms. The fold is not flat to the digit and the residual growth is not in the fold. In a by-hand probe, outside the default sizes and not part of the check, the authority read at 100,000 events was 1.5 ms and 1.8 ms in two runs, against 213 ms for the checkpointed strategy (one run, 890,000 triples in both, the probe took about 25 seconds). Timing the two steps apart at an authority gave a graph fold of 0.37 ms at 1,000 events, 0.28 ms at 20,000 and 0.33 ms at 100,000, flat within the noise, and a checkpoint lookup of 0.05, 0.18 and 0.74 ms. The lookup finds the latest checkpoint of an account by filtering and sorting all of that account's checkpoints, so it grows with the number of closes. It is the next scan floor, and we did not try to remove it. The stored triples are 178,254 for both strategies at 20,000 events, as the arithmetic predicts, since a posting's 8 quads count the same in a named graph. The write time is the same within the noise (0.83 s against 0.88 s).
8. **The position filter that remains is at the boundary of the read.** A graph is taken whole unless the read point falls inside its period. Checkpoints close on period ends, so the lower bound never cuts a period and the filter is needed only for the period holding the read point, and not at all when the point is itself a period end. Whole periods between the two carry no filter. A leaf read still needs the leaf's account in the pattern, since a graph holds the ten leaves of a programme. We tried `VALUES ?g` with `GRAPH ?g` and a union of `GRAPH <name>` blocks, and they were within about 10% of each other. The authority reads were 0.37 and 0.40 ms for `VALUES` against 0.42 ms for the union at 5,000 events, and 0.51 ms against 0.54 and 0.55 ms at 20,000, with leaf and programme reads equal. We used `VALUES` because it is shorter and was not slower.

## Extrapolation

This section extrapolates from the measurements above and was not run. The sketch's scenario is depth 3 and 10 million events a year.

| Quantity | Extrapolated | Basis |
|---|---|---|
| Postings stored, every-level | 240 million triples a year | 24.0 triples per event, linear in events |
| Postings stored, post-once | 80 million triples a year | 8.0 triples per event |
| Checkpoint overhead | accounts × closes × 4 triples | independent of event count, 0.9 triples per event here |
| Authority fold, post-once | grows with the subtree, 5 million postings at the end of a year if two authorities share the stream | linear in the history, as the 1,000 to 20,000 series is |
| Authority read time, post-once | of the order of 20 seconds at that size | 4.6 microseconds per subtree posting, measured at 10,000 postings |
| Authority fold, checkpointed | bounded by the closing interval, about the interval's events divided by the authorities | measured as 42 postings for a 500-event close at two authorities |
| Authority read time, checkpointed on this engine | still of the order of the same 20 seconds | the position filter does not seek, so the scan floor remains |
| Authority fold, period graphs | the same as checkpointed | the same postings, measured equal at every account and read point |
| Authority read time, period graphs | the fold is flat, the checkpoint lookup grows with the closes | 0.3 ms of fold at every size measured, and a lookup of 0.74 ms at 200 closes per account. At a year's volume the lookup would be the cost, linear in closes if nothing changes, which we did not run |

The 240 million is the postings alone and sits below the sketch's 450 million, which also counts a balance record of about 7 triples per account touched. We did not write balance records, so the benchmark confirms the factor of *d* and not the 450 million. The shape of the tree at scale also differs from ours, and the real subtree width of an authority sets the fold. If the engine cannot seek by position, the sketch's test for a projected rollup may be met on this engine at a year's volume, until the hot store holds only the detail since the last close. Finding 7 shows that, on this engine, partitioning the detail into a graph per programme and closing period gets the same effect without a separate hot store, at the cost of a graph per programme per period (400 at 20,000 events). We did not measure the cost of a very large number of graphs, or a posting that arrives late into a period already closed, since the stream is append-only.

## Files

| File | Role |
|---|---|
| `check.py` | the tree, the stream, the five strategies, the model, the pass criterion and the report |
| `test_check.py` | the check's own tests, including that a wrong balance, a wrong count and an over-wide checkpointed or period-graph fold fail it, that the period-graph filter is left only where a bound cuts a period, that time does not, and that the temporary store is removed |
