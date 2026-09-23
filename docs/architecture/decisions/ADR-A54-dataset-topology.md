<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# ADR-A54: Dataset Topology and Named-Graph Layout

**Status:** Proposed
**Date:** 2026-09-23
**Related:** Architecture Review §4.3, G-10, G-16, ADR-A51, ADR-A74
**Drafted by:** Agent, autonomous session (P0.1.4). Pending human ratification — see [phase-0-status.md](../../developer/status/phase-0-status.md).

## Context

ADR-A74 makes the RDF store authoritative for most durable state, across every tenant, environment, and content category (TBox, shapes, ABox, staging, projections, provenance, runtime state, write-back journals). Without a stated dataset-per-tenant policy and a named-graph grammar, isolation depends on application-layer discipline rather than store-level structure, and G-10/G-16 remain open.

## Decision

### Dataset boundary

| Option | Isolation | Cross-tenant query | Cost at scale | Verdict |
|---|---|---|---|---|
| One dataset, graph-per-tenant | Weak (app layer only) | Easy | Cheap | Rejected — violates "no client-side security" |
| **Dataset-per-tenant, shared store process** | Strong at query scope | Federation only | Moderate | **Default** |
| Store-per-tenant | Strongest | Federation | Expensive | Recommended only for dedicated/regulated tenants |

### Named-graph layout (inside a tenant dataset)

```
urn:lattice:{tenant}:{env}:tbox:{layer}:{revHash}          # pack-loaded, read-only at runtime
urn:lattice:{tenant}:{env}:shapes:{layer}:{revHash}
urn:lattice:{tenant}:{env}:abox:{appOntology}:current      # alias graph
urn:lattice:{tenant}:{env}:abox:ingest:{batchId}           # per-batch, provenance carrier
urn:lattice:{tenant}:{env}:stage:{batchId}                 # pre-admission, never queried
urn:lattice:{tenant}:{env}:proj:{projectionId}:{gen}       # projection generation
urn:lattice:{tenant}:{env}:proj:{projectionId}:current     # alias
urn:lattice:{tenant}:{env}:prov:{scope}
urn:lattice:{tenant}:{env}:rtstate:{aggregateType}:{gen}   # behaviour runtime state
urn:lattice:{tenant}:{env}:writeback:{journalId}
```

Alias graphs (`:current`) are the sole promotion and rollback mechanism. No consumer names a generation directly; activation repoints the alias atomically.

## Consequences

- A graph-name validator (P0.3.7) enforces this grammar, sharing its grammar with ADR-A51's lineage/revision IRI forms.
- `ontology/persistence`'s `dal:graphIriTemplate`/`dal:graphPrefix` values must validate against this same grammar.
- `data-architecture.md` §2 is rewritten to state this convention as the dataset topology (tracked in [phase-0-plan.md](../../developer/plans/phase-0-plan.md) §3).
- Large or regulated tenants may be provisioned on the store-per-tenant tier; the tenancy provisioning saga (P1.7.2) must support both tiers without changing the graph grammar.
