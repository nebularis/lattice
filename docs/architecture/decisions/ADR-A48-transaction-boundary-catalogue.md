<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# ADR-A48: Transaction Boundary Catalogue (Replaces CAP Framing)

**Status:** Proposed
**Date:** 2026-09-23
**Related:** Architecture Review §5.2, §7.1, G-06, G-26, ADR-A74
**Supersedes:** `solution-design-specification.md` §7.1's CAP framing ("single-writer, single-broker, partition tolerance explicitly deferred")
**Drafted by:** Agent, autonomous session (P0.1.9). Pending human ratification — see [phase-0-status.md](../../developer/status/phase-0-status.md).

## Context

`solution-design-specification.md` §7.1 frames robustness as a CAP-theorem choice ("C or A"). The review argues this is the wrong question for a system with one relational store and one graph store: the real question is which writes span two stores, and what happens when the second write fails. §2.4's provenance write is an acknowledged unprotected dual write (G-06), and no catalogue exists naming every other multi-store operation's chosen mechanism.

## Decision

Replace the CAP framing with a transaction boundary catalogue. Every multi-store operation must be one of: a single-store transaction, an outbox, or a named saga with an explicit compensation and detector. There is no fourth category — "we alert on it" is not a mechanism.

| # | Operation | Stores touched | Mechanism | Residual risk | Detection |
|---|---|---|---|---|---|
| T1 | Surface lifecycle transition | Coordination | Single transaction + optimistic concurrency | None | — |
| T2 | Lifecycle transition + job enqueue | Coordination + broker | Outbox (row committed with state change; relay publishes) | Duplicate publish | Idempotent consumer by `jobId` |
| T3 | Job result recording | Coordination | Single transaction, idempotent by `(jobId, requestDigest)` | None | — |
| T4 | Generated output publication | Graph + artifact | Saga: write immutable graph (idempotent by revision IRI), write bytes (idempotent by digest), then record. Any prefix is safe — every step is content-addressed | Orphaned graph/bytes | Reaper by unreferenced digest |
| T5 | Release receipt + provenance graph | Graph only (ADR-A74) | Single store transaction — no longer a dual write | — | — |
| T6 | Ingestion commit | Graph (staging→ABox) + coordination (batch) + stream | Store transaction for graph moves; batch row via outbox-on-commit-marker; commit marker inside the store transaction | Batch row lag | Reaper resolves by commit marker presence |
| T7 | Behaviour effect application | Graph (versions + rtstate + emitted stimuli) | Single store transaction, mandatory. Aggregate lease ensures single writer | Requires multi-graph ACID; else per-aggregate saga with stimulus log as recovery point | Position/state-hash mismatch on next load |
| T8 | Write-back `same-transaction` | Graph (projection + source) | Single store transaction | Requires multi-graph ACID; refuse the mode if the capability report (ADR-A75) says no | Activation-time capability gate |
| T9 | Write-back `journalled` | Graph then graph | Saga with journal + compensation | Divergence window (advertised) | `listDivergent`, lag alarm |
| T10 | Pack activation | Coordination + graph + artifact + route tables | Saga with explicit phases and rollback | Partial promotion | Route-version quorum |
| T11 | Projection maintenance | Graph | Single transaction per key batch + watermark | Lag | Watermark + reconciliation |
| T12 | Tenant deprovision | Everything | Saga: export → verify → drop → retain ledgers | Partial drop | Reconciliation job listing orphaned datasets |

**Three rules, stated once (`solution-design-specification.md` §7.2):**

1. No unprotected dual write. Every multi-store operation is a single store transaction, an outbox, or a named saga with a compensation and a detector.
2. Content addressing is what makes sagas safe. T4, T6, and T10 are recoverable precisely because their intermediate products are idempotent by digest. Any future multi-store operation that is not content-addressed must justify itself.
3. Every saga has a named reaper. A saga without a reconciliation job that finds and resolves interrupted instances is an unbounded leak; reapers are listed as scheduled jobs with their own alarms.

Store column names above already reflect ADR-A74 (graph-primary): rows that were PG-only under the prior relational model are now coordination-only or graph-only, and T5's dual write is removed entirely.

## Consequences

- `solution-design-specification.md` §7 is rewritten to drop the CAP framing and state this catalogue plus its three rules.
- Every saga named above requires a registered reaper before Phase 1 exit; the reaper registry is tested (tracked as a P1.x test in the epic).
- Any new multi-store operation proposed after Phase 0 must be added to this table with a named mechanism before it is implemented — an operation not in this table is not approved.
