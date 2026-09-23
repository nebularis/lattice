<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# ADR-A67: Bi-Temporal Model

**Status:** Proposed
**Date:** 2026-09-23
**Related:** Architecture Review §5.5, G-07, ADR-A65, `ontology-architecture.md`
**Drafted by:** Agent, autonomous session (P0.1.6). Pending human ratification — see [phase-0-status.md](../../developer/status/phase-0-status.md).

## Context

The platform needs two independent time axes and currently models neither explicitly at the runtime layer. Valid time answers "what was true in the world at date X" (Foundation already provides `fnd:TemporalScope`, unused by the platform). Transaction time answers "what did the system believe at date X, before a later correction arrived."

## Decision

1. Every runtime A-Box assertion graph carries `lattice:transactionTime` (the commit instant, monotone per dataset). Where the asserted facts are themselves temporally scoped, subject nodes also carry `fnd:TemporalScope` (`validFrom`/`validTo`).
2. **No in-place correction.** A correction is a new version with a new transaction time, superseding the prior version (`fnd:supersededBy`), with `fnd:Evidence` naming the correction cause. The prior version remains queryable.
3. The query component (`C-12`) accepts `asOfValidTime` and `asOfTransactionTime` parameters independently. Omitting both means "current beliefs about now."
4. Behaviour guards receive `decisionTime` (valid time) as a stimulus field. The engine pins transaction time at commit. Replay supplies both, so determinism survives backdated claims.
5. Decision records store both time values, so "re-derive this decision exactly" is possible without requiring the graph to have stood still since.

### Query path split

Bi-temporal queries over named graphs require either a per-graph temporal index or a temporal-filter pattern on every query. Materialise *current* projections for the hot path (subject to the NFR/SLO catalogue, P0.1.15); answer as-of queries from authoritative layers via a separate analytic path with relaxed SLOs. This is a deliberate two-path design, stated here rather than discovered later.

## Consequences

- G6 (no `now()` inside guards, effects, or canonicalisation — time is an input) is the enforcement mechanism for rule 4; ArchUnit bans clock access in named packages.
- ADR-A65's provenance record and this ADR's `lattice:transactionTime` are the same field — one write path sets it once, not twice.
- The materialised-current / analytic-as-of split has SLO consequences that must be captured in `docs/architecture/nfr.md` (P0.1.15) before the query component's L7 benchmarks are meaningful.
- Every write path must be audited to confirm it never mutates a prior version in place; this is checked alongside ADR-A65's homogeneity audit (P2.5.1).
