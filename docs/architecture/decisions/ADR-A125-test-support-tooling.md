<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# ADR-A125: Test-support tooling under `tools/testing/`

**Status:** Accepted, 2026-10-12, with an addendum accepted 2026-10-21 and one proposed 2026-10-27
**Date:** 2026-10-12
**Supersedes:** none
**Related:** [ADR-A77](ADR-A77-repository-topology-and-documentation-governance.md),
[ADR-A75](ADR-A75-three-tier-store-spi.md), [ADR-A84](ADR-A84-standalone-minting-libraries.md),
[ADR-A124](ADR-A124-benchmark-root.md),
[Track H plan §4.2](../../developer/plans/formal-methods-track-h.md#42-h24-the-composite-family-and-what-each-store-does-planned-2026-10-12)
(H2.4-Q2, which raised it)
**Unit:** [`formal-methods`](../../developer/plans/formal-methods.md) (epic), track H

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

## Addendum, 2026-10-21: Oxigraph is the default engine, conformance runs before a merge, and mem_check (accepted 2026-10-21)

Decided and accepted by the maintainer on 2026-10-21, as the later decision that decision 4 allows.

1. **The persistence tests run their generated SPARQL on Oxigraph by default.** `check:persistence` needs
   `tools/testing/oxigraph` and runs each engine test once, on Oxigraph. rdflib stays the library the compiler and pySHACL are
   built on. Only the store that executes generated SPARQL in a behaviour test changes. Measured serially before the change, the
   engine tests took 8.8 s on Oxigraph and 39.8 s on rdflib, at peaks of 347 MB and 403 MB.
2. **Conformance is a run of its own.** A test whose subject is one engine's behaviour, not the generated SPARQL, is a conformance
   test, for example a sweep over sixteen hash seeds on rdflib or a probe of a recorded store behaviour. It is marked so the default
   run leaves it out. `check:persistence-conformance` runs the engine tests on every engine we have, with the conformance tests, on
   demand and before a merge into `main`. It is not part of `check`, as the benchmarks of ADR-A124 are not. Each engine added later,
   for example Jena, GraphDB or RDFox, joins this run and adds nothing to `check`.
3. **`tools/testing/mem_check` says how much memory is available and how many workers fit in it.** A suite that runs in parallel
   gives its own measured peak per worker. It runs as many workers as fit in what is available less a reserve, up to the count it
   would use anyway and never fewer than two. `PYTEST_XDIST_AUTO_NUM_WORKERS` overrides it. It uses only the standard library, on macOS,
   Linux and Windows, so it adds no dependency.

Decision 4's last sentence is amended: the default `check` needs `tools/testing/oxigraph` and `tools/testing/mem_check` for the
persistence tests. `mise run bootstrap` installs both, and a check task that finds one missing stops and names the task that installs
it, instead of installing it on every run or skipping its cases. Applying the same split to the other suites is a slice of its own, ordered by their expected memory use.

## Addendum, 2026-10-27: Jena joins the conformance runs (proposed, awaiting the maintainer)

Proposed by us, not yet accepted.

1. **A second engine kit.** Apache Jena ARQ, the third engine the 2026-10-21 addendum foresaw, runs as `platform/sparql-testkit`, a Maven module serving an in-memory dataset over standard input and output, as `platform/reasoning-testkit` serves its reasoners (ADR-A83). `tools/testing/jena` drives it from Python with the methods of `tools/testing/oxigraph`. It needs no JVM bridge, so ADR-A83's isolation holds, and `check:reasoning-isolation` refuses a dependency on any test kit outside `test` scope.
2. **Engine probes have a package of their own.** `tools/testing/sparql_probes` holds probes of how engines behave that are about no one tool, with the expected result per engine, run on rdflib, Oxigraph and Jena by `check:sparql-probes-conformance`.
3. **One command for every engine.** `check:conformance` runs every conformance task in turn before a merge into `main`. No `check` default changes, and Jena adds nothing to `check`, as decision 2 of the 2026-10-21 addendum says.
