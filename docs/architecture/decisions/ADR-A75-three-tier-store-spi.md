<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# ADR-A75: Three-Tier Store SPI

**Status:** Proposed
**Date:** 2026-09-23
**Related:** Architecture Review Addendum 2 (§A2.1–A2.7, G-16, G-10), ADR-A74, `platform/graph-spi`
**Drafted by:** Agent, autonomous session (P0.1.2). Pending human ratification — see [phase-0-status.md](../../developer/status/phase-0-status.md).

## Context

ADR-A74 makes the RDF store authoritative for most durable state. Store adapters (TDB2 in-process, Fuseki remote, and future adapters) differ substantially in what they support beyond SPARQL 1.1 core: multi-request transactions, change feeds, bulk load, native SHACL or reasoning, text/vector indexes, CAS primitives. Domain code must not silently depend on a capability one adapter has and another lacks.

## Decision

Define three SPI tiers in `platform/graph-spi`:

| Tier | Contract | Portability | Who may depend on it |
|---|---|---|---|
| **Core** | Expressible in SPARQL 1.1 + Graph Store Protocol alone. Every adapter implements it in full. All platform semantics are defined at this tier. | Universal | Any domain component |
| **Extended** | Capability-gated: multi-request transactions, change feed, bulk load, native SHACL, native reasoning, text/vector index, CAS primitives, binary result formats, in-process binding. | Declared per adapter via a published `Capabilities` object | Only components that either declare a Core fallback or are gated at activation time |
| **Native** | Adapter-specific escape hatch, explicitly non-portable, reachable only through a named, audited interface. | None | Adapter internals only. Domain logic must never reference this tier (enforced, ArchUnit). |

**Rule:** a pack requiring an Extended capability (for example `MULTI_GRAPH_ATOMIC_WRITE`) cannot be activated onto a dataset whose adapter's `Capabilities` report does not declare it, unless a Core fallback exists and is used instead.

**Capabilities object:** a machine-readable, versioned, TCK-verified capability report per adapter, consumed by the activation component (`C-02`) at pack-activation time. Minimum fields: `ATOMIC_SINGLE_REQUEST_UPDATE` (Core, mandatory), `MULTI_REQUEST_TXN`, `CHANGE_FEED`, `MULTI_GRAPH_ATOMIC_WRITE` (each Extended, each with a stated fallback), reasoning profile support (RDFS/RL/QL/EL), text/vector index presence, snapshot/PITR support.

**Central design constraint:** every write unit must be expressible as a single SPARQL Update request (multiple `DELETE`/`INSERT`/`WHERE` operations separated by `;`), which essentially every conforming store executes atomically. This is what makes Core-tier atomicity portable without a Native-tier transaction API.

## Consequences

- `platform/graph-spi` (Core + Extended interfaces, `Capabilities`, `CommitMetadata`), `platform/graph-spi-tck` (conformance + benchmark kit), `platform/graph-adapter-tdb2`, and `platform/graph-adapter-fuseki` are required new modules (P0.5).
- Every Extended-tier capability used anywhere in the domain layer must carry a documented Core fallback or an activation-time gate; the TCK enforces this (P0.5.8 hostile scoping suite, P0.5.9 injection suite).
- ArchUnit rule (G1) bans domain-layer imports of Native-tier types.
- The relationship between `platform/graph-spi` and the existing `platform/semantic-dataset-spi` / `platform/semantic-dataset-fuseki` modules is a separate, not-yet-resolved decision (tracked in [phase-0-plan.md](../../developer/plans/phase-0-plan.md) §2) — this ADR defines the tier model; it does not resolve module naming or migration path.
