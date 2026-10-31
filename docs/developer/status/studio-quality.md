<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Performance, integration and load testing for the studio - Status

**Unit ID:** `studio-quality`
**Status:** 🔴 SQ1 and SQ2 built 2026-10-31, phase D's cost recovered but for publish, which waits on `projection-maintenance`
**Last updated:** 2026-10-31
**Plan:** [studio-quality.md](../plans/studio-quality.md)
**Sketch:** [studio-quality-kit.md](../sketches/studio-quality-kit.md)
**ADR:** [A-150](../../architecture/decisions/ADR-A150-performance-integration-and-load-testing.md), Proposed
**Branch:** `claude/config-authoring-studio`

## Current position

The maintainer asked on 2026-10-31 for a check of phase D's performance, a kit measuring each component with reports kept in git, and integration and load testing of the studio's topology with model-based checks, in Python or on the JVM and not F#, the tools left to the unit. The unit chose Hypothesis, its own linearisability checker, Locust and JMH (SQ-D1 to SQ-D8), and drafted ADR-A150. The maintainer asked for the publication unit's work to finish first.

The maintainer added on 2026-10-31 that most deployments span machines, so the harness also runs a topology in Docker Compose, each component its own container. The maintainer accepted Clojure on 2026-10-31, so the concurrent and distributed checks are a Jepsen test with Knossos and Elle (SQ-D2, ADR-A150 decision 4).

SQ1 was built on 2026-10-31. `tools/testing/studio_harness` starts a declared topology on its own ports, data, names and run folder, as processes or in Docker Compose, with a client of the studio's actions and a smoke scenario. Under compose, a sidecar forwards the published port to the service, since `local` authentication binds loopback only. `mise run studio:integration` runs `single` and `pair`, passing both ways, while the maintainer's studio ran on from the same checkout. Written by a Sonnet subagent and reviewed. Checks run 2026-10-31, all passing: the harness's 16 tests, and both integration runs.

SQ2 was built on 2026-10-31. Reports are kept in `benchmark/reports/`, `mise run benchmark:compare` tables two of them, and `mise run benchmark:studio-api` drives the studio's API through the harness, on this checkout or another. Run on the commit before phase D and on the head, three pairs, it found phase D slower: saves 65% to 95%, reads 30% to 100%, publishing about 7.5 times, while the registry listing is a third faster and the workspace listing unchanged. The figures and their run are in the Validation Pack's SQ2 section. Written by a Sonnet subagent and reviewed.

The maintainer asked on 2026-10-31 for the slowdown to be fixed. Traced the same day, the causes were commits, about 55 ms each on TDB2, four of them for every refresh that each save and publish queued, the writer parsing every payload it had written out as text, and a scan of the version rows on every read. The fixes are in the Validation Pack's last section: saves are now 31% to 53% slower than before phase D where they were 72% to 95%, a publish job is back to its old time, and a publish is 3.5 times slower where it was 7.4. What is left is commits, a save clearing and writing its whole part (SQ-Q1) and a publish waiting for its refresh (SQ-Q2).

The maintainer answered SQ-Q1 and SQ-Q2 on 2026-10-31. A save now writes its delta and a read runs its queries side by side, so every measure is at or under its time before phase D but a publish, about 3.3 times, which waits for its refresh until projections are maintained in the write. Two units were sketched, `persistence-delta-replace` and `projection-maintenance`.

**Next action:** for the maintainer, answer DR-Q1 to DR-Q4 and PM-Q1 to PM-Q4, and review ADR-A150, ADR-A149's addendum on the cost of a refresh, and SQ-D1 to SQ-D8. Then PM1 and PM2, which bring a publish back, and SQ3 to SQ6.

## Log

- 2026-10-31: raised by the maintainer, sketched and planned, ADR-A150 drafted.
- 2026-10-31: Docker Compose added to the harness's design. SQ1 built.
- 2026-10-31: SQ2 built. Phase D measured against the commit before it.
- 2026-10-31: Clojure accepted, SQ-D2 answered with Jepsen, Knossos and Elle.
- 2026-10-31: phase D's causes traced and four fixed. SQ-Q1 and SQ-Q2 raised.
- 2026-10-31: SQ-Q1 and SQ-Q2 answered. Saves write their delta, reads run side by side. `persistence-delta-replace` and `projection-maintenance` sketched.
