<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# ADR-A59: PartitionedWorkQueue Abstraction

**Status:** Proposed
**Date:** 2026-09-23
**Related:** Architecture Review §4.9 (C-09), §5.3, G-09, ADR-A50
**Drafted by:** Agent, autonomous session (P0.1.12). Pending human ratification — see [phase-0-status.md](../../developer/status/phase-0-status.md).

## Context

Job families in the system have different ordering requirements: design-time compilation jobs need none, ingestion batch chunks need per-key order, and behaviour stimuli need strict per-aggregate order enforced by a lease. Without a declared abstraction, ordering guarantees become an accident of whichever queue implementation is chosen first.

## Decision

Every job family declares an `orderingClass` at wiring time:

| Ordering class | Definition | Partition key | Example use |
|---|---|---|---|
| `none` | No ordering guarantee | — | Surface jobs, projection lowering, MORK analysis |
| `per-key` | Strict order within a key; parallel across keys | Named in the declaration | Ingestion batch chunks, document extraction stages, write-back applies |
| `per-key, strict` | Absolute ordering, one processor at a time | `aggregateKey` | Behaviour stimuli — the critical case; aggregate lease enforced |

A family declaring `per-key` without a named key fails at wiring time (L1 test).

**`platform/partitioned-queue-spi`** defines the `PartitionedWorkQueue` abstraction independent of implementation. Two implementations are planned behind the SPI:

| Implementation | Ordering | Operational cost | Phase |
|---|---|---|---|
| RabbitMQ consistent-hash exchange, one queue per partition | Per-key within partition | Low; plugin dependency | Phase 1 default |
| PostgreSQL / coordination-store `FOR UPDATE SKIP LOCKED` per key | Per-key, transactional | No new infra; couples throughput to the coordination store | Phase 1 alternative, config-only switch |

Kafka/Redpanda partitioned log is deferred to Phase 3+, when replay/retention needs justify new infrastructure.

## Consequences

- `partitioned-queue-spi`, `partitioned-queue-rabbit`, `partitioned-queue-pg` are required new modules (P0.8.1–P0.8.3).
- The same ordering suite runs against both implementations (L4), so the implementation choice stays a configuration change, not a code change.
- Poison-message policy and priority/pool separation for runtime vs. maintenance families (`solution-design-specification.md` §4.5) are extensions of this abstraction, addressed in P0.8.2/P0.8.4.
