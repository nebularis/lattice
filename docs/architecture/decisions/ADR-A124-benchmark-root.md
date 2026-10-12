<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# ADR-A124: A benchmark root for checks that measure, run on demand

**Status:** Accepted, 2026-10-12
**Date:** 2026-10-12
**Supersedes:** none
**Amends:** [ADR-A77](ADR-A77-repository-topology-and-documentation-governance.md), its list of repository roots
**Related:** [ADR-A29](ADR-A29-repository-toolchain-and-environment-boundary.md),
[ADR-A125](ADR-A125-test-support-tooling.md),
[Track H plan §4.2](../../developer/plans/formal-methods-track-h.md#42-h24-the-composite-family-and-what-each-store-does-planned-2026-10-12)
(H2.4-Q3, which raised it)

## Context

Some questions about LATTICE are answered by measuring, not by a test that passes or fails on every change. The first is
TD-42: a composite replace builds its payload once per stored triple of the aggregate, which was measured as quadratic on
rdflib by a scratch script, and is unmeasured on Oxigraph. The later tranches of the formal-methods epic will model each
store's behaviour and need such measurements repeated, for each engine and each version of it.

None of the existing roots fits.

- `test/` holds end-to-end suites, which gate a change.
- `spikes/` holds experiments, which are not maintained and which no `mise` task runs.
- `tools/` holds reference implementations and developer toolchains, which a measurement uses but is not.

A measurement that runs inside a gating suite slows every run. Under rdflib the composite replace at 10,000 stored triples is
expected to take minutes, and a measurement that fails on time makes a check depend on the machine. A measurement kept as a
scratch script is not repeatable, and its numbers cannot be checked later.

## Decision

1. **`benchmark/` is a repository root** for benchmarks: checks that measure, run on demand. One subdirectory per benchmark,
   named for its area and topic, for example `benchmark/persistence-composite-cost/`.
2. **A benchmark is a check.** It has a pass criterion on correctness, which it asserts at every size and on every engine it
   runs on, and it fails on a wrong result. It never fails on time. Its measurements go to a generated, git-ignored report in
   its own directory.
3. **A benchmark runs on demand.** Its `mise` task is named `check:<area>-<topic>`, for example
   `check:persistence-composite-cost`. It is never a dependency of `check` or of a default CI job. A scheduled job may run it
   later, decided separately.
4. **A benchmark depends on what it measures, and nothing depends on it.** It may import from `tools/`, including test-support
   packages under `tools/testing/` (ADR-A125). No other code imports from `benchmark/`.
5. **A measurement quoted elsewhere states its run.** A Validation Pack or a technical-debt row that cites a figure gives the
   date, the engine and its version, the Python version and the kind of machine, never the machine or person it ran on.

## Consequences

- AGENTS.md's table of roots, the root README and the copy of AGENTS.md for Copilot (`mise run build:agent-guidance`) gain
  `benchmark/` when this ADR is accepted.
- The first benchmark is `benchmark/persistence-composite-cost`, built in slice H2.4b of formal-methods Track H.
- A benchmark's numbers are evidence for a decision, such as which form of an update a store should get, and not a gate. A
  budget, if one is wanted, is a later decision with its own ADR or addendum.
- A benchmark that grows into a correctness suite moves to `test/` or to a tool's own tests.
