<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# ADR-A37: Surface worker durable processing and RabbitMQ acknowledgement

**Status:** Accepted
**Date:** 2026-09-19
**Supersedes:** none
**Related:** Phase 1, Phase 2, ADR-A30, ADR-A36, [Surface workflow architecture](../surface-workflow.md)

## Context

The in-memory processed-job store proves idempotency rules but loses state on worker restart. A worker also needs clear acknowledgement behavior to avoid acknowledging failed work or endlessly retrying malformed messages.

## Decision

Use PostgreSQL `processed_surface_job` records for durable idempotency state. Store opaque job ID, canonical request digest, JSON result, and processing timestamp. Use a RabbitMQ adapter that acknowledges a delivery only after consumer execution, result publication, and durable recording complete. Malformed JSON is negatively acknowledged without requeue. Other failures are negatively acknowledged with requeue so configured retry and dead-letter topology can handle them.

## Consequences

- The publisher must confirm result publication before the consumer records a job.
- A message that cannot be parsed is a permanent input failure. A materialization, compiler, database, or broker failure is retryable until deployment policy exhausts attempts.
- A production RabbitMQ connection setup must configure durable queues, dead-letter exchange, retry delay, consumer prefetch, and TLS or workload identity outside the domain worker code.
- PostgreSQL migration execution and live broker tests remain validation-environment work.
