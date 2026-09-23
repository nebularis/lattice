<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# ADR-A57: Change Feed via Write-Side Emission and Reconciliation

**Status:** Proposed
**Date:** 2026-09-23
**Related:** Architecture Review §4.8, §5.3, G-06, G-03, ADR-A65, ADR-A74
**Drafted by:** Agent, autonomous session (P0.1.11). Pending human ratification — see [phase-0-status.md](../../developer/status/phase-0-status.md).

## Context

Downstream consumers (projections, subscriptions, reconciliation) need a reliable feed of graph changes. Three mechanisms exist: write-side emission, store transaction-log tailing, and snapshot diffing.

## Decision

| Option | Fidelity | Coupling |
|---|---|---|
| **Write-side emission (primary)** | Complete, provided no out-of-band writes exist | Requires banning direct store access |
| Store transaction-log tailing | Complete, including admin writes | Store-specific; adapter work per store |
| Snapshot diffing | Lossy, expensive | Portable |

Adopt write-side emission as the primary mechanism, backed by store-level audit reconciliation that periodically compares an expected-state digest against the store to detect out-of-band writes.

**Change event shape:**

```
ChangeEvent {
  tenantId, environmentId, txnId, seq, committedAt,
  graph, added: [quad], removed: [quad],
  cause: { kind: ingest|behaviour|projection|writeback|activation|admin,
           batchId?, stimulusId?, principal },
  packDigest, generationProfileId
}
```

**New rule for `data-architecture.md` §5 (rule 8):** no component writes to the RDF store except through `ScopedDataset`. Credentials for direct access exist only for audited break-glass procedures, which emit an `admin` change event.

## Consequences

- G1 (enforced by ArchUnit + Python import lint) is the mechanism that makes write-side emission trustworthy — if direct store access were possible, the feed would silently miss writes.
- The `cause` shape here is the same shape ADR-A65 records in provenance; one vocabulary, two consumers (change-feed subscribers and provenance queries).
- ADR-A75's `Capabilities` object carries a `CHANGE_FEED` Extended-tier flag with write-side emission as its Core fallback — an adapter without native change-feed support still supports this mechanism.
- Reconciliation jobs are scheduled and alarmed per ADR-A48's "every saga has a named reaper" rule, even though this is a feed rather than a saga.
