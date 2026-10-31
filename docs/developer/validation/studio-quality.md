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

