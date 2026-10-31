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
