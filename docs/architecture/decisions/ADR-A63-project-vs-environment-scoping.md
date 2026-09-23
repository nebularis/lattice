<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# ADR-A63: Project vs Environment Scoping

**Status:** Proposed
**Date:** 2026-09-23
**Related:** Architecture Review §4.17, G-23, ADR-A51, ADR-A54
**Drafted by:** Agent, autonomous session (P0.1.8). Pending human ratification — see [phase-0-status.md](../../developer/status/phase-0-status.md).

## Context

The existing single `GraphReference` type conflates two distinct scoping axes: the design-time grouping under which a pack is authored, and the runtime environment it is activated into. This blocks the vendor-ships-pack-to-customer case (a pack built in project P activated into environments E₁…Eₙ, possibly belonging to different tenants) and leaves `projectId`/`environmentId` doing both jobs implicitly.

## Decision

### Entity model

```
Organisation
  └── Tenant                 (isolation boundary; owns datasets, quotas, entitlements)
        ├── Project          (design-time grouping: contracts, mappings, packs)   [existing]
        └── Environment       (runtime: dev | test | staging | prod | per-tenant custom)
              ├── DatasetBinding    (store kind, URI, capability report)
              └── ActivationBinding (pack in force)   [C-02]
```

`projectId` scopes *authoring*. `environmentId` scopes *running*. These are stated as distinct from this ADR onward — no component may use one where the other is required.

### Two reference types replace `GraphReference`

```
AuthoredGraphReference(tenant, project, revisionIri, hash)
RuntimeGraphReference(tenant, environment, graphIri, generation)
```

`revisionHash` on `AuthoredGraphReference` is a verification field (ADR-A51), not an identity field. `GraphMaterializer`'s hash check verifies exactly what it claims once this split lands.

## Consequences

- P1.2.3 replaces the single `GraphReference` with these two types; a mismatched revision hash raises `GraphMaterializationError` before any compiler invocation; a runtime reference cannot be used where an authored one is required (enforced at the type level).
- P1.7.1 implements the entity model above; provisioning sagas (P1.7.2) create datasets per ADR-A54's topology, scoped to environments, not projects.
- Service-principal credential scoping (ADR-A66) is per-environment, not per-project, since ingestion and query traffic is runtime traffic.
