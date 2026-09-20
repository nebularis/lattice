<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# ADR-A34: Surface graph-family registry and immutable identity

**Status:** Accepted
**Date:** 2026-09-19
**Supersedes:** none
**Related:** Phase 2, ADR-A13, ADR-A26, ADR-A27, ADR-A32, [Surface workflow architecture](../architecture/surface-workflow.md)

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
