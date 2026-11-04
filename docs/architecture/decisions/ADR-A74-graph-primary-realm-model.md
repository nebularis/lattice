<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# ADR-A74: One Declared Authority Per Kind Of State

**Status:** Proposed
**Date:** 2026-09-23. Rewritten 2026-10-27, see Provenance.
**Related:** Architecture Review Addendum 1 (§A1.1–A1.6, G-28, G-35, G-34), ADR-A75, ADR-A48, ADR-A13, `data-architecture.md`, `ontology-architecture.md`
**Unit:** [`phase-0`](../../developer/plans/phase-0-plan.md)
**Drafted in:** P0.1.1. Pending ratification — see [phase-0-status.md](../../developer/status/phase-0-status.md).

## Context

`data-architecture.md` names three authoritative realms: semantic graph, operational state in PostgreSQL, and artifact bytes. PostgreSQL holds the lifecycle ledgers, the graph-family registry, MORK review snapshots and decisions, the governance ledger, and release provenance as authoritative relational rows, with the RDF store treated as a secondary projection target. That produces the unprotected dual writes catalogued in ADR-A48 (G-06), and a graph-family conflict rule (`data-architecture.md` §5.2) that exists only to compensate for identity not being structural (ADR-A51).

The defect is the dual write, and the dual write comes from two stores each believing they own the same fact. Nothing about it is specific to which store wins.

This ADR was first drafted to answer it by inverting the framing, making the RDF store authoritative for anything meaning-bearing and PostgreSQL a coordination store only. That answer was right about the defect and too strong about the remedy. LATTICE is a framework and imposes no design decision its users do not need (PRI-01), and a deployment may reasonably hold the same model in a relational store, across several stores, or in a store LATTICE has never seen. Treating one storage technology as primary at the substrate contradicts that, and would make a relational backend for the whole system a violation rather than a configuration.

## Decision

**Every kind of durable state has exactly one declared authority. Everything else that persists it is annotated as derived and is reconstructible from that authority.**

That is the whole rule. It forbids the dual write without naming a winner, and it is the rule PRI-52 enforces.

**What a declaration says.** For each kind of state: which store is authoritative, what is derived from it, and how a derived copy is rebuilt. A deployment that declares nothing has one authority by default, since a single store cannot disagree with itself.

**The "where does a fact belong" test**, applied in order, to every fact the system produces. It resolves to a *kind of place*, and which store realises each kind is the deployment's to declare.

1. Is it meaning-bearing — would a domain expert or reasoner want to query it with the ontology? → the **semantic authority**.
2. Is it governance, approval, decision, or provenance about that content? → the **semantic authority** (Foundation already models this with `fnd:Version`, `fnd:Evidence`, `fnd:GovernanceState` and `fnd:TemporalScope`).
3. Is it ephemeral coordination — a lease, lock, idempotency key with a TTL, queue position, or hot counter? → **coordination**, never authoritative.
4. Is it high-rate, low-value, aggregate-only measurement (metering, latency, counts)? → **coordination or time-series**, never authoritative.
5. Are the bytes opaque (PDF, OCI layer, export bundle)? → the **artifact** realm.
6. Is it an ordered, high-throughput event log needing replay and retention? → the **stream** realm.
7. Does an algorithm need an access pattern the semantic authority genuinely cannot serve (ordered interval sweep, window functions, columnar aggregation, vector ANN)? → an **algorithmic projection sink**, derived, reconstructible, declared as a Surface projection target.

Rows 3, 4 and 7 are never authoritative whatever store realises them, which is the part of the test that does the work.

**The graph is the default semantic authority, not the required one.** Where a deployment states no preference, rows 1 and 2 resolve to the RDF store, because Foundation already models governance, versions, evidence and temporal scope, and because a graph-native authority needs no mapping layer to serve rows 1 and 2. A deployment that declares otherwise is configuring LATTICE, not breaking it, and the boundaries available to it are set out in the [multi-store runtime sketch](../../developer/sketches/multi-store-runtime.md) §3 and §4.

**A relational realisation is legitimate.** A SQL backend for the whole model satisfies this ADR as long as it is the declared authority and anything else holding the same state is derived and reconstructible. Nothing here requires an RDF store to exist.

**The existing relational tables.** Each is currently authoritative in PostgreSQL and each holds state rows 1 or 2 assign to the semantic authority, so each moves there. Under the default that is the graph, in the forms below.

| Current PostgreSQL table | Form under the semantic authority |
|---|---|
| `surface_revision_ledger` | `surface:Revision` node per state, chained by `fnd:supersededBy`, using `fnd:hasGovernanceState` |
| `mork_review_snapshot` | Immutable content-addressed snapshot graph, provenance refs co-resident |
| `mork_review_decision` | Decision nodes co-resident with the MORK mappings they decide against |
| `governance_ledger_entry` | Append-only governance graph, hash-chained segments |
| `release_ledger_intent` / `_receipt` / `_event` | Release provenance graph, which removes ADR-A48's T5 dual write entirely |
| `calibration_gate` | Gate node per `(pack, profile, model)` stratum, running counts in coordination, promoted at recalculation |

Every component other than the store SPI (ADR-A75) reaches the authority through that SPI and treats no other store as authoritative for anything this test assigns to it.

## Consequences

- A single-node LATTICE deployment needs no PostgreSQL: a semantic store, an embedded coordination store (ADR-A59, `coordination-h2`), a filesystem artifact store and a broker are sufficient.
- ADR-A48's transaction-boundary catalogue is re-expressed in these terms. Several rows (T4, T5, T6, T9, T10) simplify because a content-addressed write to one authority replaces a two-store saga with a single transaction plus reconciliation.
- `data-architecture.md` §1–§3 and §5–§7 are rewritten to reflect this model (tracked in [phase-0-plan.md](../../developer/plans/phase-0-plan.md) §3), stating the default rather than a fixed realm set.
- ADR-A51 (IRI policy) and ADR-A75 (store SPI) remain load-bearing: identity must be structural, and the SPI must expose the Core-tier primitives any authority depends on, before a durable write occurs.
- **What is irreversible is the declaration, not this ADR.** Once production data exists under a declared authority, moving it is a migration. Choosing the authority stays a deployment decision, so the earlier framing of this ADR as the single largest gating decision no longer holds: a deployment that defers the choice gets the graph by default and can be read without reordering the plan.
- A deployment that declares a non-default authority owes the mapping from the ontology to it. LATTICE does not provide one, and the absence is a cost of that choice rather than a gap here.

## Provenance

**Rewritten 2026-10-27, by the maintainer's decision, from "Graph-Primary Realm Model".** The original adopted the Architecture Review's inverse framing wholesale and made the RDF store authoritative for most durable state. It was drafted when splitting state between a graph store and PostgreSQL was the assumed design, and its purpose was to stop state going to PostgreSQL that had no reason to be there. That purpose is served by the single-authority rule alone.

Two things prompted the rewrite. The [multi-store runtime sketch](../../developer/sketches/multi-store-runtime.md) does not treat the graph as the central store of any architecture, and names the partition rather than the engine as what decides the runtime. And a relational backend for the whole system is a plausible direction, which the original would have contradicted outright rather than configured.

The decision test, the table of relational tables and the consequences survive, because they were always about which *kind* of place a fact belongs in. Only the premise that one technology holds that place has gone. This ADR was never accepted, so it is revised in place rather than superseded, and PRI-52 is restated with it.
