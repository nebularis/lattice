<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# ADR-A36: Surface worker idempotent delivery boundary

**Status:** Accepted
**Date:** 2026-09-19
**Supersedes:** none
**Related:** Phase 1, Phase 2, ADR-A30, ADR-A35, [Surface workflow architecture](../architecture/surface-workflow.md)

## Context

RabbitMQ and comparable transports provide at-least-once delivery. A Surface worker can receive duplicate requests, a result publish can succeed but fail before acknowledgement is observed, and a message can be retried after the worker process restarts. Running a compiler repeatedly is acceptable only when output identity and result publication are controlled.

## Decision

Introduce a transport-neutral `SurfaceJobConsumer`. It computes a canonical SHA-256 digest of the complete request, uses the opaque `jobId` plus that digest as its idempotency identity, and rejects reuse of one job ID for different request content. It publishes a result before recording successful processing. On a duplicate exact request, it republishes the cached result without re-executing the compiler.

The publisher contract is idempotent by job ID. A failed or uncertain publish leaves the job unrecorded so it may execute again on retry. The receiving control plane must idempotently record result events using the same opaque job ID.

## Consequences

- Worker delivery is at least once, not exactly once in isolation.
- Duplicate jobs after confirmed publication avoid compiler work through the processed-job store.
- A crash or acknowledgement uncertainty after external publication can lead to a repeat execution. Deterministic compiler output, immutable output digests, idempotent result publishing, and idempotent result recording make that safe.
- The in-memory processed-job store is a unit-test adapter. A deployed worker needs durable storage or broker-backed idempotency coordinated with result publication and acknowledgement.
