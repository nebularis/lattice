<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# ADR-A42: MORK review snapshot and decision-learning boundary

**Status:** Accepted
**Date:** 2026-09-20
**Related:** Phase 5, ADR-A22, ADR-A25

## Context

MORK review decisions must be reproducible against immutable evidence and must not leak syntax, lint diagnostics, or unrelated tenant data to reviewers. The six review decisions have different mapping and learning semantics.

## Decision

Use immutable, tenant-and-project-scoped review snapshots. Model Confirm, Retarget, Reshape, Decline, Teach, and Defer as closed decisions with distinct effects. `RESHAPE` records structural feedback only and never changes projection statistics. Reviewers receive evidence projections, not MORK syntax or pack internals.

## Consequences

- A decision requires the snapshot hash it reviewed, enabling stale-snapshot conflict handling.
- Worker and UI projections must enforce tenant and project scope before returning evidence.
- Teaching and retargeting can contribute learning evidence. Reshape and defer do not alter projection statistics.
