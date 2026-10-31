<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Plan: performance, integration and load testing for the studio

**Unit ID:** `studio-quality` (SQ)
**Unit type:** multi-slice unit, validation gate per slice
**Status:** planned 2026-10-31, SQ-D1 to SQ-D8 taken alone for ratification, ADR-A150 Proposed
**Sketch:** [studio-quality-kit.md](../sketches/studio-quality-kit.md)
**Status record:** [studio-quality.md](../status/studio-quality.md)
**ADR:** [A-150](../../architecture/decisions/ADR-A150-performance-integration-and-load-testing.md), Proposed
**Depends on:** the `studio-publication` unit's phase D

## 1. Goal and acceptance

Phase D's cost is measured against the commit before it, each studio component can be measured alone and compared across runs, and each declared topology is checked against a model of the studio, sequentially, concurrently and, on demand, under load, with throughput and timings reported. Accepted when every slice's Validation Pack passes and the phase D comparison is in the status record.

## 2. Decisions

The sketch's §5, SQ-D1 to SQ-D8.

## 3. Slices

| Slice | What | Done when | Estimate |
|---|---|---|---|
| SQ1 | the harness: a topology from a declared configuration, isolated, with a client whose methods are the API's actions | a topology of one writer and one worker and one of two of each start, run a smoke scenario and stop, leaving no process and no data | 200k tokens |
| SQ2 | reports in git, the compare task, the Python timer, and the `studio-api` scenario run on the commit before phase D and on the head | both reports are in `benchmark/reports/studio-api/`, and their comparison is in the status record | 150k tokens |
| SQ3 | component benchmarks, JMH for the writer, the operations, skolemisation and the routes, the timer for the worker's jobs | each writes a report, and a second run compares with the first | 200k tokens |
| SQ4 | the model and the Hypothesis state machine, run against each declared topology | it passes on both topologies, and a deliberately broken guard in a test build is found and shrunk | 250k tokens |
| SQ5 | concurrent histories and the per-aggregate linearisability checker | concurrent runs pass on two writers, and a history with a lost update is reported | 200k tokens |
| SQ6 | Locust load runs with reports, their histories checkable | a load run of a declared length reports throughput and percentiles per action, and its history checks | 150k tokens |

## 4. Demonstration

The phase D comparison, then a load run on two writers whose history checks.
