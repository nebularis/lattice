<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# ADR-A68: PII and Erasure

**Status:** Proposed
**Date:** 2026-09-23
**Related:** Architecture Review §5.7 (S-9), §4.10, ADR-A54, ADR-A65, ADR-A82
**Drafted by:** Agent, autonomous session (P0.1.7). Pending human ratification — see [phase-0-status.md](../../developer/status/phase-0-status.md).

## Context

The review's threat model names PII-in-graph / GDPR erasure (S-9) as irreversible once production data exists — it must be decided before any data write, not discovered after. An append-only, content-addressed, provenance-tracked graph store is structurally hostile to "search and destroy" erasure unless personal data is isolated by construction.

## Decision

1. Personal data is modelled as separately-graphed, referenceable nodes. A `pty:Actor`'s identifying attributes live in a dedicated per-subject graph, not interleaved with non-personal facts in a shared batch graph.
2. **Erasure is a graph drop plus a tombstone** — dropping the per-subject graph and recording a tombstone node — rather than a search-and-destroy sweep across an append-only estate.
3. **Ledgers retain references (pseudonymous IDs), not personal data.** The governance ledger, provenance records, and any hash-chained audit trail refer to a subject by pseudonymous reference only.
4. Write-back never writes to a graph marked `lattice:authority = derived-*`. It writes to the authoritative source graph, creating a new version of the source node (`fnd:supersededBy`), with the projection write and the triggering stimulus or user action recorded as `fnd:Evidence`. The source layer's history therefore records why it changed, without duplicating personal data into derived layers.
5. LATTICE-minted identifiers follow the selected privacy-safe identity pattern. An unkeyed hash of a personal key is prohibited. Use a per-subject reference node, or an opaque surrogate with a restricted keyed claim where lookup or uniqueness is required.
6. **Erasure is durable only if it survives restore.** A deployment with any erasure obligation maintains an erasure register outside the dataset (alongside the durable epoch authority `ontology/persistence` now models as `dal:EpochProfile`) and replays it — dropping the listed graphs and re-asserting tombstones — before any restored, rebuilt, or cloned dataset admits readers or writers. A restore or clone that skips this replay is a personal-data exposure, not a neutral operational event.
7. **A receipt or history model that keeps a second, immutable copy of personal payload is incompatible with per-subject graph-drop erasure**, unless that copy is itself per-subject and enumerable, or the payload is crypto-shredded instead. A family carrying personal data selects `dal:PerSubjectGraphDrop` with per-subject-scoped receipts, or `dal:CryptoShred` with a specified key-custody and as-of-failure policy; it does not select an unscoped `dal:PatchLog` or `dal:SnapshotPerRevision` model. `ontology/persistence`'s `dal:PersonalDataReceiptCompatibilityShape` checks this at the configuration level.
8. **Claim-scheme rotation and ownership monotonicity.** Rotating a keyed claim's secret uses a declared dual-write phase so uniqueness holds across the rotation window (never "a new salt and a backfill" alone). Where an erasure policy permits physically deleting a claim, the ownership-monotonicity argument in the patterns guide's Chapter 6.2 no longer holds unconditionally; the family declares `dal:erasurePrecedence` (`dal:ErasureWins` or `dal:MonotonicityWins`) naming which wins and how reconciliation behaves.
9. **The residual exposure window is the backup retention period.** Erasure bounds exposure to that window, it does not eliminate it; the window is part of what the DPO/legal review in the Consequences below assesses.

## Consequences

- A deployment selecting per-subject PII graphs declares that graph-locator form through its topology and identity profiles. The profile compiler and validator (P0.3.7) validate that selected form alongside PII-specific shapes (P0.3.8).
- `ontology/governance/shapes/` gains a PII data-model shape: a ledger fixture containing personal data must fail validation (P0.3.8, L1).
- Erasure as a graph-drop operation must be reconciled with ADR-A65's provenance-homogeneity rule and ADR-A67's "no in-place correction" rule — dropping a graph is the one operation that is not a superseding version, and this ADR is the explicit exception, scoped to per-subject PII graphs only.
- A formal DPO/legal review gate on this decision is recommended before the Phase 0 exit gate, per the epic's own open question. This ADR does not substitute for that review; it records the technical mechanism the review would assess.
