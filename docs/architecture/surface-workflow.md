<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Surface Workflow Control Plane

The Surface workflow control plane adds application lifecycle around existing Surface semantics. It does not translate Promotion, Index, Projection, parity, invalidation, canonicalisation, or lowering rules into Java. Those rules remain in the ontology assets and `tools/surface`.

## Revision Model

A `SurfaceRevision` references three graph families directly:

| Family | Purpose | Required point in lifecycle |
|---|---|---|
| Contract graph | Immutable Promotion or Index declaration revision | Draft onward |
| Profile graph | Immutable generation and canonicalisation profile revision | Draft onward |
| Generated graph | Immutable output and manifest graph produced from the approved revision | Generated onward |

All graph references carry tenant, project, graph IRI, and revision hash. The workflow rejects mixed tenant or project scope. It makes no graph-store calls itself.

## Graph-Family Registry

`SurfaceGraphFamilyRegistry` catalogs immutable graph artifact metadata. The family vocabulary is `CONTRACT`, `PROFILE`, `PREVIEW`, `GENERATED_OUTPUT`, `LOWERING_RECORD`, and `INVALIDATION_PLAN`. Each `SurfaceGraphArtifact` records the family, graph reference, owning revision ID, and registration time.

The registry key is tenant ID, project ID, and graph IRI. Re-registering the identical artifact is idempotent. Reusing that scoped IRI for a different hash, family, or owner revision raises an immutable-graph conflict. This prevents later release, invalidation, or operator tooling from treating a mutable name as immutable evidence.

The registry is operational metadata only. It does not store RDF and does not replace Fuseki or another semantic dataset. A future physical graph-store adapter must write and hash content, return a `GraphReference`, then register the resulting artifact. It must never change content under an already registered reference.

## State Transitions

```text
DRAFT -> REVIEW_REQUESTED -> APPROVED -> GENERATED -> RELEASED
  \-------------------------------------------------> SUPERSEDED
```

`APPROVED` stores approval evidence. `GENERATED` requires both approval evidence and an immutable generated-graph reference. `RELEASED` retains the same evidence. Supersession preserves the revision references and records that it is no longer the active candidate. The persistent revision ledger remains deferred, so the current model represents transition rules rather than durable concurrency control.

## Revision Ledger

The workflow now exposes `SurfaceRevisionRepository` as an operational-state port. `InMemorySurfaceRevisionRepository` supports deterministic unit tests. `JdbcSurfaceRevisionRepository` maps the port to PostgreSQL using the migration at `platform/surface-workflow/src/main/resources/db/migration/V1__surface_revision_ledger.sql`.

The ledger stores tenant and project scope, lifecycle state, immutable contract, profile, and generated graph references, approval evidence, a `recorded_at` timestamp, and a monotonically increasing `revision_version`. It deliberately does not store RDF, generated Turtle, or a copy of the semantic source of truth.

Callers read a `VersionedSurfaceRevision`, choose a valid domain transition, then replace it with the version they read. The database update includes `where revision_id = ? and revision_version = ?`. A missing update produces a stale-revision conflict and prevents an older client or worker from overwriting a newer state. This is an operational conflict, distinct from semantic validation failure.

## Typed Command Boundary

`SurfaceRevisionService` is the application boundary for state changes. It accepts `SurfaceRevisionTransition`, which contains an expected version and one closed action:

| Action | Required evidence | Resulting lifecycle transition |
|---|---|---|
| `REQUEST_REVIEW` | None | `DRAFT` to `REVIEW_REQUESTED` |
| `APPROVE` | Approval evidence ID | `REVIEW_REQUESTED` to `APPROVED` |
| `RECORD_GENERATION` | Immutable generated graph reference | `APPROVED` to `GENERATED` |
| `RELEASE` | None beyond revision evidence | `GENERATED` to `RELEASED` |
| `SUPERSEDE` | None | Any non-superseded state to `SUPERSEDED` |

The service reads the revision, compares the expected version before it evaluates the transition, then delegates replacement to the repository. A mismatch is always a stale-revision conflict. A matching version with an illegal state transition is a separate state error. This ordering prevents an old client from learning or acting on newer lifecycle state through a command intended for an earlier version.

`contracts/surface/surface-revision-transition.schema.json` defines the wire command. `contracts/openapi/surface-workflow.openapi.json` describes the framework-neutral HTTP shape for a later adapter. Its transition endpoint returns `409` for stale versions or invalid state. The OpenAPI document is a contract artifact only. This repository has not introduced an HTTP server or a framework dependency.

## Worker Boundary

`surface-job-request` selects `generation`, `parity`, or `invalidation`. It contains only contract, profile, and source graph references. Invalidation additionally requires a distinct `manifestGraph` reference. `workers/surface_jobs.py` validates the closed message shape, rejects RDF, credentials, browser tokens, shell commands, and cross-scope references, then delegates to a trusted execution adapter.

`SurfaceCompilerExecutor` is the reference execution adapter. It asks an injected `GraphMaterializer` to resolve authorized immutable graph references into canonical bytes in a private temporary directory. Before it invokes the compiler, it requires that every returned path remains within that directory, is a regular file, and hashes to its graph reference's SHA-256 revision hash. A materialization failure produces a safe diagnostic and prevents compiler execution. Generation always runs `compile` with `--verify-determinism` and `--parity`. Parity runs `parity`. Invalidation passes `manifestGraph` only to `check --manifest` and passes source graphs only to `--sources`.

The adapter returns generated-output SHA-256 digests and safe diagnostics. It does not return Turtle or N-Quads in a job result. Request data cannot choose a command or file path. A future deployment adapter must obtain graph content through an authorized dataset adapter, serialize it in the same canonical form used for the revision hash, register generated graph artifacts, publish output to a graph store, and connect the executor to AMQP acknowledgement and retry policy.

## Delivery and Retry Boundary

`SurfaceJobConsumer` is the worker-side delivery coordinator. It canonicalizes the complete request as sorted JSON and hashes it with SHA-256. `jobId` plus that digest identifies one request. Reusing a job ID for different content is rejected. An exact retry reads a cached result and republishes it without invoking the executor again.

The consumer publishes before it records the processed job. A normal retry after a confirmed publication only republishes the result. If a publish succeeds externally but the worker cannot observe acknowledgement, the job remains unrecorded and can execute again. This is intentionally at-least-once behavior. `SurfaceResultPublisher` and the receiving control plane must make result publication and result recording idempotent by `jobId`. Compiler determinism and content-addressed outputs limit a repeated execution to duplicate delivery of the same immutable result.

`InMemoryProcessedSurfaceJobStore` is suitable only for tests. A deployed worker needs durable processed-job state or broker-backed idempotency, integrated with broker acknowledgement and result-event persistence.

`PostgresProcessedSurfaceJobStore` is the durable reference adapter. Its migration lives at `workers/sql/V1__processed_surface_jobs.sql` and records job ID, canonical request digest, result JSON, and processing time. It records only after publication returns successfully. `RabbitMqSurfaceWorker` adapts delivery to the consumer: success acknowledges, malformed JSON negatively acknowledges without requeue, and other errors negatively acknowledge with requeue. Connection setup, retry delay, dead-letter queue binding, prefetch, and transport authentication remain deployment configuration.

## Output Publication

`SurfaceOutputPublisher` retains successful generated Turtle outside a worker temporary directory. The filesystem reference publisher stores each artifact under its SHA-256 digest and returns a descriptor with media type, digest, and URI. The executor publishes nothing when the compiler returns a failure status. A deployment publisher must verify output bytes, write to the semantic graph store or immutable artifact store, and register the corresponding `GENERATED_OUTPUT` graph-family artifact.

## Release Handoff

A `SurfaceReleaseCandidate` is constructed only from `GENERATED` revisions with generated-output digests and passed semantic gate evidence. It converts to the Phase 3 `ReleaseIntent` using the contract, profile, and generated graph references. The release stack receives no Turtle and cannot make a revision semantically valid by signing it.

## Current Limitations

The Studio UI, migration runner configuration, PostgreSQL integration tests, durable graph-family registry storage, physical graph-store adapter, HTTP adapter, RabbitMQ transport adapter, durable processed-job store, output-publication adapter, E2E fixture runs, and graph lineage projections are not implemented. The current tests verify lifecycle preconditions, stale-write handling through the in-memory adapter and command service, immutable graph-family registration, worker envelope validation, fixed compiler argument construction, and in-memory idempotent delivery behavior only. See the [Phase 2 handoff](../developer/phase-2-handoff.md) for required offsite validation.
