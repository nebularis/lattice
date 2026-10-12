<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# ADR-A125: Test-support tooling under `tools/testing/`

**Status:** Proposed
**Date:** 2026-10-12
**Supersedes:** none
**Related:** [ADR-A77](ADR-A77-repository-topology-and-documentation-governance.md),
[ADR-A75](ADR-A75-three-tier-store-spi.md), [ADR-A84](ADR-A84-standalone-minting-libraries.md),
[ADR-A124](ADR-A124-benchmark-root.md),
[Track H plan §4.2](../../developer/plans/formal-methods-track-h.md#42-h24-the-composite-family-and-what-each-store-does-planned-2026-10-12)
(H2.4-Q2, which raised it)

## Context

The persistence compiler's generated SPARQL is run on rdflib by its own tests. Slice H2.4 of formal-methods Track H needs
a second, independent engine, Oxigraph, so that what a test shows does not rest on one implementation, and so that the
probes of what each store does (H5's capability record) can be run on both. Today Oxigraph is reached only through
`spikes/persistence-oxigraph`, which is not maintained and which no `mise` task runs.

What is needed is an adapter that loads data, runs an update or a query, binds `$name` parameters as a caller would, and
reads back quads. It is used by tests and by benchmarks, and by nothing else. None of the existing homes fits.

- It is **not a runtime backend or a store SPI.** ADR-A75 describes the SPI's tiers and none is defined. Putting the adapter
  in `platform/` or naming it as a backend would suggest an interface that does not exist.
- It is **not a library for adopters.** `packages/` holds libraries meant to be embedded (ADR-A84).
- It is **not a suite.** `test/` holds end-to-end suites, not support code shared between them.
- It is **not a spike.** It must be maintained and reused.

## Decision

1. **`tools/testing/` holds test-support packages**: engines, adapters and fixture builders used by tests, checks and
   benchmarks. One package per subdirectory, for example `tools/testing/oxigraph/`, with its own `pyproject.toml`, installed
   by a `mise` task `bootstrap:testing-<name>`.
2. **Only tests, checks and benchmarks use them.** No product code imports a test-support package: nothing under a tool's
   `src/`, `platform/`, `workers/`, `packages/` or `apps/`. A tool's tests may.
3. **A test-support package names no interface beyond what its tests need.** An adapter for an engine is not a store SPI,
   and its methods carry no promise to adopters.
4. **A suite that uses one skips those cases when it is absent**, unless the `mise` task that runs the suite installs it.
   The default `check` does not need any test-support package unless a later decision adds one.

## Consequences

- AGENTS.md's table of roots, which describes `tools/`, gains a line for `tools/testing/` when this ADR is accepted, and the
  copy for Copilot is rebuilt (`mise run build:agent-guidance`).
- The first package is `tools/testing/oxigraph`, depending on `pyoxigraph>=0.5.11,<0.6`, built in slice H2.4b. Its adapter
  is taken from `spikes/persistence-oxigraph`, which then points at it.
- Rule 2 is not yet enforced by a check. The existing import guard covers ontology layers only. A check that no product code
  imports from `tools/testing/` is a small addition, and until it exists the rule is kept by review.
- A dependency of a test-support package is a test dependency of the suites that use it, recorded in the lock file like any
  other.
