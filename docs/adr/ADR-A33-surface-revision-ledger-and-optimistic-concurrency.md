<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# ADR-A33: Surface revision ledger and optimistic concurrency

**Status:** Accepted
**Date:** 2026-09-19
**Supersedes:** none
**Related:** Phase 2, ADR-A13, ADR-A27, ADR-A32, [Surface workflow architecture](../architecture/surface-workflow.md)

## Context

Surface revision state changes are user and worker initiated. Two actors can read the same revision and attempt incompatible updates, such as an approval after a supersession. Storing workflow state inside RDF would conflate operational coordination with semantic source-of-truth graphs. Storing mutable graph documents in the operational database would duplicate semantic content and make revision hashes less meaningful.

## Decision

Maintain Surface workflow state in a PostgreSQL operational ledger. Store graph references and lifecycle evidence, not RDF content. Give each revision an increasing optimistic-concurrency version. A replacement must name the version that was read. The database updates state only when the stored version matches, and otherwise reports a stale-revision conflict.

## Consequences

- `SurfaceRevision` remains a pure lifecycle model and enforces allowed transitions independently of storage.
- `SurfaceRevisionRepository` is a storage port. The in-memory implementation supports deterministic unit tests and the JDBC implementation maps the same port to PostgreSQL.
- The `surface_revision_ledger` migration stores tenant, project, contract and profile references, generated graph reference, approval evidence, state, version, and recorded time. It does not store Turtle or generated graph content.
- API and AMQP handlers must return a conflict for stale replacements and must reload a revision before choosing a new transition.
- PostgreSQL integration tests, migration runner configuration, and failure-retry exercises remain required before the adapter is validated for deployment.
