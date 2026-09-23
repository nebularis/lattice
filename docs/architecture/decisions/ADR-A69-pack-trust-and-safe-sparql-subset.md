<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# ADR-A69: Pack Trust Model and Safe SPARQL Subset

**Status:** Proposed
**Date:** 2026-09-23
**Related:** Architecture Review §5.7 (S-5), G-12, ADR-A75
**Drafted by:** Agent, autonomous session (P0.1.13). Pending human ratification — see [phase-0-status.md](../../developer/status/phase-0-status.md).

## Context

A pack is untrusted content until verified: it can carry SPARQL that, if unrestricted, becomes an exfiltration or write-scope-escape channel (`SERVICE` calls to attacker-controlled endpoints, `LOAD` of network content, writes outside declared target graphs).

## Decision

### Pack trust model

| Component | Control |
|---|---|
| Signature verification | Tenant-configured trust root; every pack verified before any activation |
| Closure pinning | No network-resolvable imports; all dependencies inlined by digest |
| Safe SPARQL subset | No `SERVICE`, no `LOAD`, no arbitrary `INSERT`/`DELETE` outside declared target graphs |
| SHADOW phase | New graphs run in parallel with the current graph before promotion; outputs compared on a live sample |

### Safe SPARQL subset (normative for all pack content)

- No `SERVICE` calls — federated SPARQL is an egress channel, disallowed by default; allow-listed endpoints only, per environment, as an explicit exception.
- No `LOAD` — no network retrieval from within a query or update.
- No writes (`INSERT`/`DELETE`) outside declared target graphs.

This is the inverse of what an ad-hoc reasoning/query service may permit — packs are restricted precisely because they run with elevated, activation-scoped trust, unlike ad-hoc user queries which run under the requesting principal's own visibility.

## Consequences

- The safe subset must be statically checkable (a pack lint, P1.8.4) rather than enforced only at execution time; each forbidden construct has a dedicated rejection test (L8).
- ADR-A75's Native tier is exactly the tier a pack must never reach — pack SPARQL executes only through the Core/Extended surface, never through a Native escape hatch.
- G5 (no string concatenation into SPARQL; `PreparedQuery` + `Params` only) is a precondition for this ADR's static checkability — a pack lint cannot reason about concatenated query strings.
- The SHADOW phase requires the activation component (`C-02`) to support running two graph generations concurrently before promotion; this is a dependency on ADR-A54's generation/alias graph convention.
