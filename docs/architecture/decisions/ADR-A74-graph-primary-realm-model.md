<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# ADR-A74: Graph-Primary Realm Model

**Status:** Proposed
**Date:** 2026-09-23
**Related:** Architecture Review Addendum 1 (§A1.1–A1.6, G-28, G-35, G-34), ADR-A75, ADR-A48, `data-architecture.md`, `ontology-architecture.md`
**Drafted by:** Agent, autonomous session (P0.1.1). Pending human ratification — see [phase-0-status.md](../../developer/status/phase-0-status.md).

## Context

`data-architecture.md` currently names three authoritative realms: semantic graph (Fuseki), operational state (PostgreSQL), and artifact bytes. PostgreSQL holds the lifecycle ledgers, the graph-family registry, MORK review snapshots and decisions, the governance ledger, and release provenance as authoritative relational rows, with the RDF store treated as a secondary projection target. This produces the unprotected dual writes catalogued in ADR-A48 (G-06) and a graph-family conflict rule (`data-architecture.md` §5.2) that exists only to compensate for identity not being structural (see ADR-A51).

The Architecture Review's Addendum 1 proposes the inverse framing: everything that is meaning-bearing, or is governance/approval/decision/provenance about graph content, belongs in the RDF store, mapped onto Foundation's existing vocabulary (`fnd:Version`, `fnd:Evidence`, `fnd:GovernanceState`, `fnd:TemporalScope`). PostgreSQL is retained only as a coordination store for facts that are never authoritative by nature.

## Decision

Adopt the graph-primary realm model.

**The "where does a fact belong" test**, applied in order, to every fact the system produces:

1. Is it meaning-bearing — would a domain expert or reasoner want to query it with the ontology? → **Graph (authoritative).**
2. Is it governance, approval, decision, or provenance about graph content? → **Graph** (Foundation already models this).
3. Is it ephemeral coordination — a lease, lock, idempotency key with a TTL, queue position, or hot counter? → **Coordination realm**, never authoritative.
4. Is it high-rate, low-value, aggregate-only measurement (metering, latency, counts)? → **Coordination / time-series**, never authoritative.
5. Are the bytes opaque (PDF, OCI layer, export bundle)? → **Artifact realm.**
6. Is it an ordered, high-throughput event log needing replay and retention? → **Stream realm.**
7. Does an algorithm need an access pattern RDF genuinely cannot serve (ordered interval sweep, window functions, columnar aggregation, vector ANN)? → **Algorithmic projection sink**, derived, reconstructible, declared as a Surface projection target.

**Existing relational tables and their graph-primary destination:**

| Current PostgreSQL table | Graph-primary form |
|---|---|
| `surface_revision_ledger` | `surface:Revision` node per state, chained by `fnd:supersededBy`, using `fnd:hasGovernanceState` |
| `mork_review_snapshot` | Immutable content-addressed snapshot graph, provenance refs co-resident |
| `mork_review_decision` | Decision nodes co-resident with the MORK mappings they decide against |
| `governance_ledger_entry` | Append-only governance graph, hash-chained segments |
| `release_ledger_intent` / `_receipt` / `_event` | Release provenance graph; removes T5's dual write entirely (ADR-A48) |
| `calibration_gate` | Gate node per `(pack, profile, model)` stratum; running counts in coordination, promoted to graph at recalculation |

Every component other than the store SPI (ADR-A75) is forbidden from writing the RDF store directly (`ScopedDataset` only, G1) and forbidden from treating PostgreSQL, or its replacement coordination store, as authoritative for anything the test above assigns to the graph.

## Consequences

- A single-node LATTICE deployment requires no PostgreSQL at all: an RDF store, an embedded coordination store (ADR-A59, `coordination-h2`), a filesystem artifact store, and a broker are sufficient.
- ADR-A48's transaction-boundary catalogue must be re-expressed in graph-primary terms; several table rows (T4, T5, T6, T9, T10) simplify because content-addressed graph writes replace two-store sagas with single-store transactions plus reconciliation.
- `data-architecture.md` §1–§3 and §5–§7 must be rewritten to reflect this realm model (tracked in [phase-0-plan.md](../../developer/plans/phase-0-plan.md) §3).
- ADR-A51 (IRI policy) and ADR-A75 (store SPI) become load-bearing prerequisites: identity must be structural, and the store SPI must expose the Core-tier primitives this model depends on, before any durable write occurs.
- This decision is irreversible once production data exists (per the epic's own framing, Part 0). No slice in Phase 1+ writes durable data before this ADR and ADR-A75 are ratified.

## Open question for human ratification

The epic explicitly names this as the single largest gating decision ("if you do not accept A74, roughly 40% of the plan reorders"). Drafted here as accepted, consistent with the epic's stated default assumption, because no contrary instruction was given. Confirm or reject explicitly before Phase 1 begins.
