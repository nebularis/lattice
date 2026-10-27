<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# ADR-A34: Surface graph-family registry and immutable identity

**Status:** Accepted
**Date:** 2026-09-19
**Supersedes:** none
**Related:** Phase 2, ADR-A13, ADR-A26, ADR-A27, ADR-A32, [Surface workflow architecture](../surface-workflow.md)

## Context

Surface lifecycle and release evidence reference more than contract, profile, and generated graphs. Previews, lowering records, and invalidation plans also need durable provenance. A physical graph store may differ by deployment, but using mutable names for different graph content would let a receipt, invalidation plan, or release candidate silently refer to changing semantic input.

## Decision

Define a closed Surface graph-family vocabulary and an operational registry of immutable graph artifact metadata. A registration includes family, tenant and project scoped graph reference, owning revision, and registration time. A graph IRI may be registered again only when family, owner revision, and revision hash are identical. A different hash, family, or owner for the same scoped IRI is rejected.

The registry stores metadata only. It does not persist RDF or serve graph content. A later graph-store adapter is responsible for writing and reading actual immutable graph content through the semantic dataset SPI.

## Consequences

- Contract, profile, preview, generated-output, lowering-record, and invalidation-plan references have a common typed identity boundary.
- The registry can support release inventory, impact analysis, and operator investigation without duplicating semantic data.
- A physical storage adapter must verify the content hash before registration and must not mutate content behind a registered graph IRI.
- The in-memory registry supports contract tests. Durable registry persistence and Fuseki storage integration remain Phase 2 work.

## Addendum (2026-10-27): a family declares where its graphs seal, and an unsealed graph is not registrable

The registry above accepts a graph IRI again only when family, owner revision and revision hash are identical, and requires a storage adapter to verify the content hash before registration and never to mutate content behind a registered IRI. Every Surface family it was written for produces a graph that is complete when it is written, so the moment of registration was never in question.

A graph that is appended to over a period and then closed does not fit that assumption. The ledger's period partition is the case: a book holds one account partition's postings for one closing period, it grows throughout the period, and it is complete only at the close ([ADR-A13](ADR-A13-dataset-graph-role-model.md)'s addendum of 2026-10-27, measured in [benchmark/ledger-posting-cost](../../../benchmark/ledger-posting-cost/README.md) finding 7). Registering such a graph while it is open would make the registry's central promise false, since the content behind the registered IRI is still changing and the verified hash is already stale.

**A family declares the point at which its graphs seal, and only a sealed graph may be registered.** For a Surface family that point is the write, which is the behaviour above, unchanged. For a family whose graphs accumulate, it is the act that closes them, and for the ledger's period books that act is the closing. Registration of an unsealed graph is refused rather than merely discouraged, so the promise has an enforcement point rather than resting on a caller's good behaviour.

The graph-family vocabulary was closed to Surface's families. It opens to a family that declares a sealing point, which is what lets a ledger period book be registered at all. Nothing else about the registry changes: it still stores metadata only, serves no graph content, and rejects a differing hash, family or owner for the same scoped IRI.

**This answers a question asked elsewhere, with no new mechanism.** The ledger needed a digest recorded at a close and checked on restore, so that an archived period can be shown to be the record that was written, and the [multi-store runtime sketch](../../developer/sketches/multi-store-runtime.md) §5.3 left it open along with MS-Q4. The hash verification this ADR already requires before registration is that digest. A sealed book registered at its close is a book whose content can be proved unchanged later, and the restore path checks the registry rather than carrying a digest scheme of its own.

Two consequences worth naming.

- **The close becomes a registration event**, so it does more than write a checkpoint. A close that fails to register has sealed a book without recording its identity, which is a reconciliation case rather than a lost one, since the hash can be recomputed from the sealed content.
- **A family with no declared sealing point keeps the old behaviour.** Nothing existing has to declare anything, and the absence means "sealed at the write", which is what every Surface family already does.
