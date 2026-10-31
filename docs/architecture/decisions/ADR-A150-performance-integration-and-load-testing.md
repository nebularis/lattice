<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# ADR-A150: Performance, integration and load testing, with reports kept in git

**Status:** Proposed
**Date:** 2026-10-31 (proposed)
**Amends:** ADR-A124, what a benchmark's report is
**Related:** ADR-A124 (the benchmark root), ADR-A125 (test-support tooling), ADR-A136 (the studio), ADR-A149 (publication), PRI-65, STD-290, STD-040
**Unit:** [`studio-quality`](../../developer/plans/studio-quality.md)

## Context

A change to a write path, such as the studio's move onto generated persistence operations (ADR-A149 decisions 12 and 13), can slow a system without failing a test. Benchmarks under `benchmark/` measure on demand, but each writes a generated report that git ignores, so a run cannot be compared with one from last month. Nothing starts a deployment's topology in more than one configuration and checks it for correctness, and nothing measures it under load.

## Decision

1. **A benchmark's reports are kept in git**, one file per run, `benchmark/reports/{benchmark}/{date}-{commit}.json`, each naming its commit, its date and the kind of machine, never the machine's name or its owner (ADR-A124 decision 5). A compare task tables a run against a base and never fails on time (STD-290).
2. **Components are measured alone**, in process, by benchmarks under `benchmark/`: JMH for the JVM, a timer of our own for Python.
3. **A topology is started from a declared configuration** by a test-support harness under `tools/testing/`, always on its own ports, dataset and run folder, never a developer's store.
4. **Integration suites under `test/` check each topology against a model**, sequentially with property-based state machines (Hypothesis), and concurrently by checking recorded histories for linearisability, each aggregate on its own. They run on demand, never inside `check`.
5. **Load runs under `benchmark/` drive a topology** with the same actions (Locust), only on demand, and report throughput and latency percentiles per action. A load run's histories may be checked as a correctness run's are.

## Consequences

- A slowdown is seen by comparing reports, and its cause by the component benchmarks.
- Reports add a file per run to git, small JSON, so the repository grows by kilobytes a run.
- Hypothesis and Locust become test dependencies of the Python toolchain, and JMH of a benchmark's own build.
- The model of the studio in the integration suite is a second description of its behaviour, kept honest by the suite failing when the two disagree.

## Provenance

Raised by the maintainer on 2026-10-31, after phase D of the publication unit, with the choice of tools left to the unit. The [sketch](../../developer/sketches/studio-quality-kit.md) holds the options weighed.
