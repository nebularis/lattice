<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Surface workflow

The application lifecycle around Surface contracts. It does not reimplement Surface semantics, which stay in the ontology assets and `tools/surface`. See [Surface workflow control plane](../../docs/architecture/surface-workflow.md), [ADR-A32](../../docs/architecture/decisions/ADR-A32-surface-revision-lifecycle-and-release-candidates.md), [ADR-A33](../../docs/architecture/decisions/ADR-A33-surface-revision-ledger-and-optimistic-concurrency.md) and [ADR-A34](../../docs/architecture/decisions/ADR-A34-surface-graph-family-registry-and-immutable-identity.md).

## What it provides

| Type | Role |
|---|---|
| `SurfaceRevision`, `SurfaceRevisionState` | A revision references a contract graph, a profile graph and, once generated, a generated graph, all in one tenant and project. States are `DRAFT`, `REVIEW_REQUESTED`, `APPROVED`, `GENERATED`, `RELEASED` and `SUPERSEDED`. The record refuses a generated or released revision without a generated graph, and an approved one without approval evidence. |
| `SurfaceRevisionAction`, `SurfaceRevisionTransition` | The typed commands `REQUEST_REVIEW`, `APPROVE`, `RECORD_GENERATION`, `RELEASE` and `SUPERSEDE`, each with the evidence it requires, and the version the caller expects. |
| `SurfaceRevisionService` | Applies a transition through optimistic concurrency. A caller whose expected version is out of date gets `StaleSurfaceRevisionException`. |
| `SurfaceRevisionRepository`, `InMemorySurfaceRevisionRepository`, `JdbcSurfaceRevisionRepository` | The revision ledger. The JDBC implementation targets PostgreSQL. |
| `SurfaceGraphFamily`, `SurfaceGraphArtifact`, `SurfaceGraphFamilyRegistry` and its in-memory and JDBC implementations | A registry of graph artifacts by family, which are `CONTRACT`, `PROFILE`, `PREVIEW`, `GENERATED_OUTPUT`, `LOWERING_RECORD` and `INVALIDATION_PLAN`. A graph IRI registers once, and a different artifact for the same IRI raises `ImmutableGraphConflictException`. The graph content stays in the semantic dataset. |
| `SurfaceReleaseCandidate` | A generated revision with its outputs and gate evidence. `toReleaseIntent` converts it to a `ReleaseIntent` for `release-integration`. |
| `SurfaceRevisionApi` | A framework-neutral mapping of create, get and transition to responses that carry an HTTP-style status. |

The database schema is in `src/main/resources/db/migration`, as `V1__surface_revision_ledger.sql` and `V2__surface_graph_artifact_registry.sql`.

## Build and test

```bash
mise run check:java
mise exec -- mvn -f platform/pom.xml -pl surface-workflow -am verify
```

The first command builds and tests every platform module. The second builds this module and the modules it depends on. The tests cover the revision state rules, the API mapping and the in-memory repository and registry, and need no database. A pass is a Maven `BUILD SUCCESS`.

## Depends on

`semantic-dataset-spi` and `release-integration`.
