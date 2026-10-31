<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Performance, integration and load testing for the studio - Status

**Unit ID:** `studio-quality`
**Status:** 🟡 planned 2026-10-31, waiting for `studio-publication`'s PB17
**Last updated:** 2026-10-31
**Plan:** [studio-quality.md](../plans/studio-quality.md)
**Sketch:** [studio-quality-kit.md](../sketches/studio-quality-kit.md)
**ADR:** [A-150](../../architecture/decisions/ADR-A150-performance-integration-and-load-testing.md), Proposed
**Branch:** `claude/config-authoring-studio`

## Current position

The maintainer asked on 2026-10-31 for a check of phase D's performance, a kit measuring each component with reports kept in git, and integration and load testing of the studio's topology with model-based checks, in Python or on the JVM and not F#, the tools left to the unit. The unit chose Hypothesis, its own linearisability checker, Locust and JMH (SQ-D1 to SQ-D8), and drafted ADR-A150. The maintainer asked for the publication unit's work to finish first.

**Next action:** build SQ1 and SQ2 once PB17 is in, then SQ3 to SQ6. For the maintainer, review ADR-A150 and SQ-D1 to SQ-D8.

## Log

- 2026-10-31: raised by the maintainer, sketched and planned, ADR-A150 drafted.
