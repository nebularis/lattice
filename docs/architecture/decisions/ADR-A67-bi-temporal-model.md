<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# ADR-A67: Bi-Temporal Model

**Status:** Proposed
**Date:** 2026-09-23
**Related:** Architecture Review §5.5, G-07, ADR-A65, `ontology-architecture.md`
**Unit:** [`phase-0`](../../developer/plans/phase-0-plan.md)
**Drafted in:** P0.1.6. Pending ratification — see [phase-0-status.md](../../developer/status/phase-0-status.md).

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

## Addendum (2026-10-27): the query-path split is not forced

The query path split above rests on a premise: that bi-temporal queries over named graphs need either a per-graph temporal index or a temporal filter on every query, so current projections are materialised for the hot path while as-of queries go to a separate analytic path with relaxed SLOs.

Measurement has found a third option the premise does not consider. **Naming the periods is itself the per-graph temporal index.** Where a record's postings are partitioned into a graph per account partition and closing period, "the records since the last close" is a graph selection rather than a filtered scan, and where a closing recurrence fixes the positions at which checkpoints exist, the checkpoint at or before a point is addressed by a derived IRI rather than searched for. Both were measured on the ledger's account tree in [benchmark/ledger-posting-cost](../../../benchmark/ledger-posting-cost/README.md), findings 7 and 9, with the supporting store behaviour in TSD-04, TSD-36 and TSD-40.

An as-of read on that shape costs 0.36 ms over 20,000 events and 0.54 ms over 100,000, against 32.8 ms and 217.5 ms for the same read behind a position filter. It does not grow with the history. So an as-of query does not need relaxed SLOs, a materialised current projection or a second path, for the pattern where that partition is available.

**What this changes.** The split stops being a design rule and becomes one option among three, chosen per aggregate rather than for the platform.

| Shape | As-of read |
|---|---|
| partitioned by period, checkpoints at declared closings | answered on the authoritative graphs, no projection, no relaxed SLO |
| not partitioned, a temporal filter on every query | the premise above holds, and the split is the right answer |
| current state wanted at OLTP rates | a materialised projection, which [ADR-A13](ADR-A13-dataset-graph-role-model.md) already places in the Materialisation graph role and which is never the evidence for a decision |

**What is unchanged.** Rules 1 to 5 stand. Two independent axes, no in-place correction, independent `asOfValidTime` and `asOfTransactionTime` parameters, `decisionTime` as a stimulus field, and both times on a decision record. The materialised projection remains available and remains forbidden as evidence.

**What this costs.** The partition is only available where the records are append-only and a closing recurrence is declared, so the first row is a pattern rather than a default. The storage cost of frequent closings is real and measured: shortening the closing period raises the stored quads with the product of accounts and closes, by 6.5 times across the range swept. Every figure here is Oxigraph's, and STD-176 makes it a hypothesis on another engine until measured, which TSD-40 shows is true even across patch versions of one engine.
