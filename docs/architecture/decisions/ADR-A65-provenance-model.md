<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# ADR-A65: Provenance Model

**Status:** Proposed
**Date:** 2026-09-23
**Related:** Architecture Review §4.19, §5.6, G-03, G-06, ADR-A54, ADR-A57, ADR-A67
**Drafted by:** Agent, autonomous session (P0.1.5). Pending human ratification — see [phase-0-status.md](../../developer/status/phase-0-status.md).

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
