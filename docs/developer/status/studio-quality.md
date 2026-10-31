<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Performance, integration and load testing for the studio - Status

**Unit ID:** `studio-quality`
**Status:** 🔴 SQ1 and SQ2 built 2026-10-31, phase D measured slower, causes not yet measured
**Last updated:** 2026-10-31
**Plan:** [studio-quality.md](../plans/studio-quality.md)
**Sketch:** [studio-quality-kit.md](../sketches/studio-quality-kit.md)
**ADR:** [A-150](../../architecture/decisions/ADR-A150-performance-integration-and-load-testing.md), Proposed
**Branch:** `claude/config-authoring-studio`

## Current position

The maintainer asked on 2026-10-31 for a check of phase D's performance, a kit measuring each component with reports kept in git, and integration and load testing of the studio's topology with model-based checks, in Python or on the JVM and not F#, the tools left to the unit. The unit chose Hypothesis, its own linearisability checker, Locust and JMH (SQ-D1 to SQ-D8), and drafted ADR-A150. The maintainer asked for the publication unit's work to finish first.

The maintainer added on 2026-10-31 that most deployments span machines, so the harness also runs a topology in Docker Compose, each component its own container. Whether the distributed checks use Jepsen, in Clojure, or stay in Python is open with the maintainer.

SQ1 was built on 2026-10-31. `tools/testing/studio_harness` starts a declared topology on its own ports, data, names and run folder, as processes or in Docker Compose, with a client of the studio's actions and a smoke scenario. Under compose, a sidecar forwards the published port to the service, since `local` authentication binds loopback only. `mise run studio:integration` runs `single` and `pair`, passing both ways, while the maintainer's studio ran on from the same checkout. Written by a Sonnet subagent and reviewed. Checks run 2026-10-31, all passing: the harness's 16 tests, and both integration runs.

SQ2 was built on 2026-10-31. Reports are kept in `benchmark/reports/`, `mise run benchmark:compare` tables two of them, and `mise run benchmark:studio-api` drives the studio's API through the harness, on this checkout or another. Run on the commit before phase D and on the head, three pairs, it found phase D slower: saves 65% to 95%, reads 30% to 100%, publishing about 7.5 times, while the registry listing is a third faster and the workspace listing unchanged. The figures and their run are in the Validation Pack's SQ2 section. Written by a Sonnet subagent and reviewed.

**Next action:** find the causes, with SQ3's component benchmarks and a profile of a save and a read, and fix them. For the maintainer, say whether Jepsen is wanted, and review ADR-A150 and SQ-D1 to SQ-D8.

## Log

- 2026-10-31: raised by the maintainer, sketched and planned, ADR-A150 drafted.
- 2026-10-31: Docker Compose added to the harness's design. SQ1 built.
- 2026-10-31: SQ2 built. Phase D measured against the commit before it.
