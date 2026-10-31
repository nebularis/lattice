<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: studio-quality SQ1 to SQ6

**Plan:** [studio-quality](../plans/studio-quality.md)
**Status record:** [studio-quality](../status/studio-quality.md)

One pack for the unit, each slice a section.

## Invariant

A topology under test never touches a developer's studio: its ports, data, names and run folder are its own, and stopping it leaves nothing (ADR-A150 decision 3). A benchmark fails on a wrong result and never on time (STD-290).

## Commands

```bash
mise run check:config-studio
mise run studio:integration
mise run studio:integration -- --runner compose
```

The first runs the harness's own tests, which start nothing. The others start each declared topology, as processes or in Docker Compose, run the smoke scenario and stop it. A pass is exit status 0.

## SQ1: the harness

| ID | Given / When / Then | Level | +/− | Result |
|---|---|---|---|---|
| SQ1-01 | a topology file with a missing or wrong field, `oidc`, or no writer / parsed / refused with its reason | L1 | − | pass |
| SQ1-02 | the shipped `single` and `pair` topologies / a compose file generated / one service per component on one network, the service's port alone published on loopback | L1 | + | pass |
| SQ1-03 | `single` and `pair` as processes / started, the smoke scenario run, stopped / every step's status as expected, then no process alive, the port closed and the run folder gone | L5 | + | pass, 2026-10-31, 2 in 27 s |
| SQ1-04 | the same in Docker Compose / started, run, stopped / the same, and no container or image of the run left | L5 | + | pass, 2026-10-31, 2 in 97 s with a cold image build |
| SQ1-05 | a developer's studio running from the same checkout / both runs / its service still answering and its jars untouched | L8 | + | pass |

`tools/testing/studio_harness/tests` and `test/studio-integration/test_smoke.py`. Runs on macOS on Apple silicon, Java 25, Python 3.14.

**Changed in review.** The smoke scenario polled the terms route for up to 60 s and never read the registry listing. Publishing waits for its refresh, so it now reads the listing and the terms once each, and both must show the scheme.

**Not covered.** `oidc` topologies, the memory store under compose, and the transforms worker, which no scenario uses. A run interrupted part way leaves its run folder and processes. `writers` counts writer processes, which share the contract's eight partitions.

## SQ2: reports, comparison and phase D's cost

| ID | Given / When / Then | Level | +/− | Result |
|---|---|---|---|---|
| SQ2-01 | a report / validated / its fields, units and machine kind present, no host or user name | L1 | ± | pass |
| SQ2-02 | two reports / compared / medians, change in percent, a mark only when each median lies outside the other run's interquartile range, a warning when the machine kinds differ, exit 0 | L1 | + | pass |
| SQ2-03 | the `studio-api` scenario / run on `4029bd0f` and on `bd2a144d`, three pairs / every reply's status as expected, six reports written | L5 | + | pass, 2026-10-31 |

`tools/testing/studio_harness/tests` (36) and `benchmark/studio-api` (5), 41 in all.

**Phase D's cost**, the first pair, medians, on macOS 27.0.1, arm64, Apple M2 with 8 cores and 8 GiB, Java 25.0.2, Python 3.14.7, low power mode off, load average about 2.7 at each start:

| Measure | `4029bd0f` | `bd2a144d` | Change |
|---|---|---|---|
| save a part, 100 triples | 89.7 ms | 159.6 ms | +78% |
| save a part, 1,000 triples | 128.1 ms | 220.0 ms | +72% |
| save a part, 3,000 triples | 178.1 ms | 346.8 ms | +95% |
| read a part, 100 triples | 8.8 ms | 14.9 ms | +69% |
| read a part, 1,000 triples | 10.6 ms | 17.2 ms | +62% |
| read a part, 3,000 triples | 15.1 ms | 19.4 ms | +29% |
| list workspaces | 2.9 ms | 3.0 ms | +3%, within noise |
| a publish job, submitted to done | 151.6 ms | 290.3 ms | +92% |
| publish | 90.4 ms | 666.3 ms | +637% |
| list the registry | 3.7 ms | 2.5 ms | −32% |

The other two pairs agree: saves 65% to 95% slower, reads 30% to 100% slower, publishing about 7.5 times slower, the registry listing about a third faster, the workspace listing unchanged.

**What is not yet known.** These are measures of the whole studio, so they say how much slower and not why. Hypotheses, none measured: a read now loads the workspace from its description and two scans of version rows, where it read one description. A save adds a read of the part for its delta, skolemisation, a digest and a claim, and queues a refresh that reads the whole store while the next request runs. Publishing now waits for that refresh. SQ3's component benchmarks are to separate them.

## Phase D's causes and their fixes

**What the time went on**, traced from Fuseki's log of each request (`--verbose`) and Java Flight Recorder on the service and the writer, on the harness's `single` topology, with TDB2 and with Fuseki's in-memory dataset:
- **Commits.** Every update request on TDB2 cost 52 ms to 104 ms whatever its size, and 1 ms to 9 ms in memory (TSD-44). Each refresh was four of them (the job submitted, marked running, finished with its projections, deleted), so each save was followed by four more commits, and the next save queued behind them in the writers' queue. A publish waited for its refresh, five commits in all where it had one.
- **The writer's CPU.** About 40% of the writer's samples were the SPARQL parser reading the payload, which the writer had written out as text into the generated operation and then parsed back.
- **Reads.** A workspace's load scanned each family's meta graph for every row under the workspace's prefix, two queries whose cost grows with every part in the store.

**What changed**:
- the writer fills each payload slot with a marker triple, parses the small request, and replaces the marker's quads with the payload's quads in the syntax tree, so a payload is never parsed (`StudioOperations.build`)
- a workspace's version rows are read by their roots, the parts' and the documents' its description lists, in one query with an inline `VALUES`, one index lookup a root (`StudioStore.versionRows`)
- a refresh is two commits: the worker no longer marks a refresh job running, and the update that succeeds it deletes the job and its receipts (ADR-A149 addendum, the cost of a refresh)
- a refresh that no reply waits for starts half a second after the first write that asked for it, so a burst of writes shares one (`Refresher`)
- the platform's jar plugin always creates the jar, since without `clean` a shaded module's jar kept stale copies of a changed dependency's classes, which made the first measurement of these fixes measure the old code.

| ID | Given / When / Then | Level | +/− | Result |
|---|---|---|---|---|
| SQD-01 | twenty refresh requests within the delay / the delay passes / one refresh ran, and a wait that follows starts one at once | L1 | + | pass |
| SQD-02 | a refresh job / its update succeeds / the projections are written and the job and its receipts are gone, and a second update of it is not found | L4 | + | pass |
| SQD-03 | a refresh job / the worker runs it / one update reaches the writer, never a running one | L1 | + | pass |
| SQD-04 | every existing writer, service and operation test / the payload spliced and the rows read by root / all pass unchanged | L1 to L4 | ± | pass |
| SQD-05 | the `studio-api` scenario / run on the fixes / every reply as expected | L5 | + | pass, 2026-10-31 |

Commands run 2026-10-31, all passing: `mvn -q -f platform/pom.xml -pl config-studio-authoring,config-studio-service,config-studio-writer,config-studio-transforms -am verify` through `mise exec`, the worker's two studio test modules (68), and `mise run benchmark:studio-api`.

**The result**, medians, same machine, load average about 2.3 to 2.7 at each start:

| Measure | before phase D, `4029bd0f` | phase D, `bd2a144d` | the fixes, `c83dd347` | against before phase D |
|---|---|---|---|---|
| save a part, 100 triples | 89.7 ms | 159.6 ms | 136.8 ms | +53% |
| save a part, 1,000 triples | 128.1 ms | 220.0 ms | 182.8 ms | +43% |
| save a part, 3,000 triples | 178.1 ms | 346.8 ms | 232.7 ms | +31% |
| read a part, 100 triples | 8.8 ms | 14.9 ms | 12.0 ms | +36% |
| read a part, 3,000 triples | 15.1 ms | 19.4 ms | 17.3 ms | +15% |
| list workspaces | 2.9 ms | 3.0 ms | 2.2 ms | −25% |
| a publish job, submitted to done | 151.6 ms | 290.3 ms | 152.0 ms | 0%, within noise |
| publish | 90.4 ms | 666.3 ms | 320.7 ms | about 3.5 times |
| list the registry | 3.7 ms | 2.5 ms | 2.8 ms | −25% |

On Fuseki's in-memory dataset a save of 1,000 triples now takes 84 ms, against 225 ms before the fixes, so what is left on TDB2 is commits. **Not yet fixed**, each a question in the sketch's §6: a save still clears its part and writes it whole, 121 ms of TDB2's time for 1,000 triples where its delta is two (SQ-Q1), and a publish still waits for a refresh of two commits and a worker's turn (SQ-Q2). The read costs one more round trip than before phase D, for the version rows, which was left as it is.

**Not covered.** Whether SQ2's reports of `bd2a144d` ran on jars with stale classes is not known. The writer's jar in this checkout held core classes compiled at 15:05 when the fault was found, and those reports ran at 16:34, so they may have measured part of an earlier commit. A run of `bd2a144d` from a clean build would settle it. The fixes were not measured on Linux, where a commit costs less, nor under concurrent load, which SQ6 covers.

## Phase D, the delta save and the reads side by side

After SQ-Q1 and SQ-Q2 were answered on 2026-10-31:
- a part's or a document's save writes its delta, `StudioOperations.replaceDelta`, the generated replace with its sweep taken out, the retracted triples deleted and the asserted inserted, in one operation. It leaves exactly the quads the generated replace leaves, digest included, since it digests the whole next state as the generated one does
- a workspace's description and its parts' version rows are read at once, then its documents' rows when it lists any, and a part's read fetches the part's graph beside the workspace, so a read costs two round trips one after the other, as before phase D.

| ID | Given / When / Then | Level | +/− | Result |
|---|---|---|---|---|
| SQD-06 | a part and a document, 150 of 300 triples changed / a delta replace / one operation, carrying no unchanged triple, leaving the quads the generated replace leaves | L4 | + | pass |
| SQD-07 | a delta replace at a stale or a replayed sequence / applied / nothing changes | L4 | − | pass |
| SQD-08 | every service and writer test / reads side by side / all pass unchanged | L1 to L4 | ± | pass |

Commands run 2026-10-31, all passing: the studio's Java modules with `verify`, and `mise run benchmark:studio-api`. The run on the committed code is the report of this section's commit, and its figures are below.

