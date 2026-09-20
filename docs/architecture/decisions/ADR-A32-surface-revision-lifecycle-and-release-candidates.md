<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# ADR-A32: Surface revision lifecycle and immutable release candidates

**Status:** Accepted
**Date:** 2026-09-19
**Supersedes:** none
**Related:** Phase 2, ADR-A16, ADR-A21, ADR-A27, ADR-A28, ADR-A31, [Surface workflow architecture](../surface-workflow.md)

## Context

The existing Surface compiler deterministically implements Promotion, Index, parity, and invalidation semantics, but it has no application-level lifecycle for drafts, approval evidence, immutable graph families, or release handoff. Release operations must only observe outputs from a reviewed and immutable semantic revision.

## Decision

Model each Surface revision as an immutable reference set for contract and profile graphs. Permit the ordered lifecycle `DRAFT`, `REVIEW_REQUESTED`, `APPROVED`, `GENERATED`, `RELEASED`, or `SUPERSEDED`. Require approval evidence before generation and require immutable generated-graph evidence before release. Form a `SurfaceReleaseCandidate` only from a generated revision with output digests and passed semantic gates. Translate the candidate to a release intent without altering compiler semantics.

## Consequences

- A revision cannot bypass review to reach generation or release.
- Contract, profile, and generated graph references share one tenant and project scope.
- Surface worker jobs carry only these scoped references and select generation, parity, or invalidation through a closed job type.
- The current Java model is a control-plane contract. Persistent ledger, graph-store adapter, AMQP consumer, Studio UI, and end-to-end fixture execution remain Phase 2 work.
