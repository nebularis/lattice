<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# ADR-A65: Provenance Model

**Status:** Proposed
**Date:** 2026-09-23
**Related:** Architecture Review §4.19, §5.6, G-03, G-06, ADR-A54, ADR-A57, ADR-A67
**Unit:** [`phase-0`](../../developer/plans/phase-0-plan.md)
**Drafted in:** P0.1.5. Pending ratification — see [phase-0-status.md](../../developer/status/phase-0-status.md).

## Context

Every durable write must be attributable: what caused it, under what pack and profile, by which principal, at what transaction time. The review compares four mechanisms for recording this at the required granularity without pathological storage cost.

## Decision

### Mechanism: named-graph-per-batch

| Option | Granularity | Cost | Portability | Query ergonomics |
|---|---|---|---|---|
| **Named-graph-per-batch** | All triples from one ingestion batch, extraction run, stimulus application, or projection generation share a graph carrying the provenance record | Low — one record per batch | Universal | `GRAPH ?g { ... }` then look up `?g`'s record |
| RDF-star / per-triple | Per triple | High (2–5×) | Poor | Awkward |
| Singleton property | Per triple | Very high | Universal but pathological | Bad |
| Reified statements | Per triple | Highest | Universal | Bad |

**Provenance homogeneity rule:** one ingestion request, one document extraction run, one stimulus application, one projection generation each get their own graph. Never accumulate multiple causes into one graph for write efficiency — the storage saving is trivial and the audit loss is total. This is the same convention `ontology/persistence`'s `dal:MetaTopologyProfile`/`dal:ReceiptModel` dimensions assume; a future `dal:` value must not silently contradict it.

### Provenance record shape

Recorded in the `prov:{scope}` graph (ADR-A54) for that batch graph:

```
<batchGraph> a lattice:ProvenanceScope ;
  lattice:authority "authoritative" | "derived-cache" | "derived-operational" | ... ;
  prov:wasGeneratedBy <activity> ;
  lattice:packDigest ... ;
  lattice:generationProfileId ... ;
  lattice:cause [ kind: ingest|behaviour|projection|writeback|activation|admin ;
                  batchId | stimulusId | extractionRunId | journalId ] ;
  prov:wasAttributedTo <principal-or-agent> ;
  lattice:sourceArtifact <documentDigest|payloadDigest> ;
  lattice:derivedFrom ( <sourceGraph> ... ) ;
  fnd:recordedAt ... ;
  lattice:transactionTime ... .
```

## Consequences

- `ontology/governance/shapes/provenance.ttl` (P0.3.6) enforces exactly one `ProvenanceScope` with one `cause` per assertion graph; violations are rejected at L1.
- ADR-A57's change feed events carry the same `cause` shape, so change-feed consumers and provenance queries agree on vocabulary.
- Every write path introduced through Phase 4 is audited against this rule (P2.5.1: enumerate every graph, assert exactly one cause).
- `lattice:transactionTime` on the provenance record is the same field ADR-A67 requires on every assertion graph; these two ADRs share one field, not two.

## Addendum (2026-10-27): a graph may be a provenance unit or a partitioning unit

The homogeneity rule above says never to accumulate several causes into one graph for write efficiency, because the storage saving is trivial and the audit loss total. That reasoning holds wherever the graph is what carries the cause. It does not hold where each record carries its own.

The ledger's postings are the case that shows the difference. A pass has an identity and a recorded time, and it stamps every posting it writes, so a posting's cause is recoverable from the posting. Partitioning postings into a graph per account partition and closing period then accumulates many passes into one graph and loses nothing, because nothing was being read from the graph's identity. The partition is what makes an aggregate's balance readable in time independent of the history, measured in [benchmark/ledger-posting-cost](../../../benchmark/ledger-posting-cost/README.md) finding 7.

**The rule is therefore qualified rather than relaxed.** A graph is a provenance unit or a partitioning unit, declared, and whichever it is, every record's cause must be recoverable. Where the graph is the provenance unit, the homogeneity rule applies unchanged and one cause gets one graph. Where each record carries its cause, the graph is free to be a partitioning unit, and the audit requirement is discharged by the record rather than by the graph.

Two consequences follow.

- **The audit of ADR-A65 (P2.5.1) checks recoverability, not graph homogeneity alone.** A graph holding several causes passes where every record in it names its own cause, and fails where any record's cause can be reached only through the graph.
- **The transaction time of ADR-A67 follows the same carrier.** Where the graph is the provenance unit, `lattice:transactionTime` sits on the graph as both ADRs state. Where the record is, it sits on the record, and one write path still sets it once.

This addendum records a qualification found by measurement. It does not reopen the choice of named-graph-per-batch over per-triple provenance, which stands.
