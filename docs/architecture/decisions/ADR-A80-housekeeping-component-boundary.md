<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# ADR-A80: Housekeeping component boundary

**Status:** Proposed
**Date:** 2026-09-22
**Supersedes:** none
**Related:** ADR-A78, ADR-A79, [rdf-sparql-patterns-guide.md](../rdf-sparql-patterns-guide.md) Chapters 21, 24, 25, 27

## Context

[rdf-sparql-patterns-guide.md](../rdf-sparql-patterns-guide.md) requires several jobs to run continuously regardless of which profile an adopter chooses: the uniqueness reconciler (P7), the gap and completeness scan (S3), the fork-detection query (F5), txn-claim and log-bucket retention, tombstone and snapshot pruning, and the graph-proliferation budget check (O-12). None of these has an owner. They are described as "always installed" but nothing in the platform installs them.

These jobs need to know *what* to check per target (its receipt model, retention window, meta topology, uniqueness constraints), which is exactly what a compiled `dal:DataAccessProfile` already states. They do not need a live store connection to have their queries generated, only to run them, and running them requires the store SPI, which does not yet exist and is out of scope for this phase (ADR-A79). A component that can only be finished once the SPI lands still needs its configuration model, job taxonomy, and contracts settled now, so that the SPI and the housekeeping execution engine are designed against a fixed job shape rather than invented together under time pressure later.

## Decision

1. **`platform/housekeeping` is a new Maven module** under the existing `lattice-platform` parent, `org.nebularis.lattice.housekeeping`, delivered in two parts with an explicit boundary between them.

2. **In scope now:** the job contract (`HousekeepingJob`, `JobResult`, `JobContext` as Java interfaces, with no store-calling implementation), the configuration model split into two kinds that are never conflated — *what to check*, read from a `dal:CompiledProfile` (retention, receipt model, uniqueness constraints, meta topology), and *how aggressively*, a deployment-local operational configuration (cadence, batch size, dry-run vs enforce, alert sink) that is not ontological and does not belong in RDF, consistent with the [data-architecture.md](../data-architecture.md) realm split — and the SPARQL queries each job type would run, produced by running the `tools/persistence` compiler's `instantiate` stage (ADR-A79) as a second, concrete caller of it.

3. **Out of scope now, and recorded as an open design question** in [lattice-platform-agentic-development-v0.2.md](../../developer/plans/lattice-platform-agentic-development-v0.2.md), Part 13: the execution engine that actually runs a generated query against a live store on a schedule. That depends on the store SPI (proposed A75) and the Query Execution component (ADR-A79's exclusion), neither of which exists yet.

4. **The component assumes no transport of its own.** Consistent with the "do not assume an interface" principle already stated for the deferred Request Query Mapping library, `platform/housekeeping` exposes a library contract, not an HTTP endpoint or a queue consumer. A future execution engine, or an adopter's own scheduler, decides how jobs are triggered and how results are surfaced.

5. **A four-stage roadmap is recorded, not built.** v0, this ADR's scope, is contracts, configuration model, and generated queries, with no execution. v1 adds an execution engine wired to the Fuseki/TDB2 reference SPI once it exists, with single-node scheduling. v2 adds distributed-safe scheduling and alert-sink integrations. v3 adds adaptive throttling using the guide's per-aggregate conflict-rate metrics ([§25.5](../rdf-sparql-patterns-guide.md#255-composition-decorators-and-retry-rules)).

## Consequences

- `platform/pom.xml` gains a `housekeeping` module entry. Its own `README.md` documents the configuration split and the roadmap in full, and a matching `docs/architecture/platform-housekeeping.md` records the same architecture at the level this ADR summarises.
- A future SPI-focused ADR that defines the execution engine must treat this ADR's job contract as a given, not a proposal, unless it explicitly supersedes this one.
- Because the job queries are produced by the same `instantiate` stage as any other target's operational SPARQL, a housekeeping job's queries are versioned, reviewed, and change exactly when the template library or the target's compiled profile changes, never by hand-editing a query embedded in Java.
