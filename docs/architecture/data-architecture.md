<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Platform Data Architecture

Companion to [Platform Solution Design Specification](solution-design-specification.md). This document covers data that is not ontology content: lifecycle ledgers, registries, job state, and generated artifacts. Ontology and RDF modelling stays normative in the layer READMEs (`foundation/`, `surface/`, `applied/*`) and in [ontology-architecture.md](ontology-architecture.md). This document exists because the platform now needs a second data model, alongside the ontology, for its own operation.

## 1. Three Data Realms

The platform has three realms with different authorities. No realm may hold another realm's authoritative content.

| Realm | Storage | Authoritative for | Never holds |
|---|---|---|---|
| Semantic graph data | Fuseki (RDF dataset) | Contract, profile, generated output, MORK staging, and MORK active-mapping graph content, addressed by immutable IRI and revision hash | Lifecycle state, job status, approval records, credentials |
| Operational state | PostgreSQL | Lifecycle ledgers, graph-family registry, processed-job idempotency, review and governance ledgers, release ledger | RDF triples, generated Turtle, compiled artifacts |
| Artifact bytes | Filesystem reference store today, OCI-compatible registry for release bundles | Generated output bytes, OCI image layouts, exported release bundles, addressed by SHA-256 digest | Lifecycle state, approval state |

A `GraphReference` (`tenantId`, `projectId`, `graphIri`, `revisionHash`) is the only pointer that crosses realms. Every table in PostgreSQL that needs to refer to graph content stores a `GraphReference`, never a copy of the content. See [semantic-platform.md](semantic-platform.md) for the cross-runtime contract this pointer serves.

## 2. Conceptual Data Model

### 2.1 Operational entities (PostgreSQL realm)

| Entity | Owning component | Identity | Immutability rule |
|---|---|---|---|
| `SurfaceRevision` (ledger row) | Surface Workflow | `revisionId` | Mutable row, versioned by `revision_version`. Prior states are not retained as separate rows in the current design (see §7 gap). |
| `SurfaceGraphArtifact` | Surface Workflow (graph-family registry) | (`tenantId`, `projectId`, `graphIri`) | Append-only. Same key with different hash, family, or owner revision is rejected. |
| `ProcessedSurfaceJob` | Surface worker tier | `jobId` | Append-only. Same `jobId` with a different request digest is rejected. |
| `ReleaseLedgerIntent` | Release Integration | `releaseId` | Append-only. Re-recording an equal intent is idempotent, a different intent for the same ID is rejected. |
| `ReleaseLedgerReceipt` | Release Integration | `releaseId` | Requires a prior intent row (foreign key). Latest receipt overwrites the receipt projection, full history is in the event table. |
| `ReleaseLedgerEvent` | Release Integration | (`releaseId`, `eventId`) | Append-only, ordered by `recordedAt`, `eventId`. |
| `MorkReviewSnapshot` | MORK Review | `snapshotId` | New registration requires a strictly greater `snapshot_version`. Prior snapshot rows are retained, not deleted. |
| `MorkReviewDecision` | MORK Review | (`snapshotId`, `decidedAt`) | Append-only, tied to the exact `snapshotHash` it was decided against. |
| `GovernanceLedgerEntry` | MORK Governance | (`entryId`) | Append-only, replay ordered by occurrence time then entry ID. |
| `CalibrationGate` | MORK Governance | (`packId`, `profileId`, `modelId`) | Replaces on recalculation. Historical calibration runs are retained as ledger entries, not as the gate's own row history (see §7 gap). |
| `ReviewQueueEntry` | MORK Governance | `entryId` | Derived, replayable from snapshot population. Not yet backed by a durable table (see §7 gap). |

### 2.2 Artifact entities (artifact realm)

| Entity | Produced by | Addressed by | Retention |
|---|---|---|---|
| Generated Surface output (Turtle/N-Quads) | `SurfaceCompilerExecutor` via `SurfaceOutputPublisher` | SHA-256 digest | Immutable, kept while any revision references it |
| OCI image layout / bundle | `OciLayoutReleaseAdapter`, `OciLayoutBundleService` | OCI manifest digest | Immutable, retention policy owned by the release stack, not LATTICE (ADR-A31) |
| Export bundle | `OciLayoutBundleService.export` | Manifest digest, re-verified on restore | Immutable, portable |

### 2.3 Semantic graph families (Fuseki realm)

Restated from [surface-workflow.md](surface-workflow.md) and [surface-projection-mork.md](surface-projection-mork.md) because the platform's operational tables reference these families by name:

| Family | Written by | Mutability |
|---|---|---|
| `CONTRACT` | Surface authoring | Immutable per revision hash |
| `PROFILE` | Surface authoring | Immutable per revision hash |
| `PREVIEW` | Surface worker (preview generation) | Immutable per revision hash |
| `GENERATED_OUTPUT` | Surface worker (compiler executor) | Immutable per revision hash |
| `LOWERING_RECORD` | Projection lowering worker | Immutable per revision hash |
| `INVALIDATION_PLAN` | Surface worker (invalidation job) | Immutable per revision hash |
| MORK staging graph | Projection lowering worker | Immutable, content-addressed by mapping digest |
| MORK active-mapping graph | MORK governance activation (not yet implemented, explicitly out of Surface's reach) | Governed by MORK, not Surface |

## 3. System of Record Matrix

This is the direct answer to "which component is the system of record for which data." Every other component holding a copy of this data holds a cache or a reference, not authority.

| Data class | System of record | Readers | Notes |
|---|---|---|---|
| Contract/profile/generated/staging RDF content | Fuseki | Surface Contract Studio (via Control Plane), MORK Review Workbench (via Control Plane), workers | Never read or written directly by a browser |
| Surface revision lifecycle state and version | PostgreSQL `surface_revision_ledger` | Surface Contract Studio, release assembly, invalidation planning | Single writer: `SurfaceRevisionService` behind the Control Plane |
| Immutable graph-family ownership | PostgreSQL `surface_graph_artifact` | Release assembly, invalidation planning, Technical Inspector | Prevents IRI reuse across revisions |
| Surface job idempotency and cached result | PostgreSQL `processed_surface_job` (worker-owned schema) | Worker tier only | Control plane does not query this table directly, it receives result events |
| Release intent, receipt, and event history | PostgreSQL `release_ledger_*` | Release Operator view, CI/CD systems reading receipts | Facts about LATTICE's semantic evidence, not registry state |
| Release provenance (RDF form) | Fuseki, dedicated provenance named graph (see [solution-design-specification.md §4.4](solution-design-specification.md#44-release-integration-exposure-the-answer-to-who-calls-this)) | Auditors via SPARQL, Release Ledger view | Derived deterministically from the PostgreSQL release ledger, not independently authored |
| MORK review snapshot and decision | PostgreSQL `mork_review_snapshot`, `mork_review_decision` | MORK Review Workbench | Snapshot content is a projection of the MORK mapping graph, not the graph itself |
| MORK governance ledger | PostgreSQL `governance_ledger_entry` (table name proposed, see §7) | MORK Review Workbench (Ledger view), Pack Studio | Replay-ordered, append-only |
| Generated output and OCI bytes | Filesystem reference store / OCI registry | Release Operator, external release stack | Digest is the join key back to PostgreSQL and Fuseki records |
| Identity and role claims | External OIDC provider (Keycloak in the reference environment) | Control Plane authentication middleware only | Never cached as a writable copy, tokens are verified per request |

## 4. Data Flows

```mermaid
flowchart LR
  subgraph Browser
    Studio[Surface Contract Studio]
    Bench[MORK Review Workbench]
  end
  subgraph ControlPlane[Control Plane HTTP API]
    SurfaceAPI[Surface Workflow API]
    ReleaseAPI[Release API]
    MorkAPI[MORK Review and Governance API]
  end
  subgraph Postgres[(PostgreSQL)]
    Ledger[(surface_revision_ledger)]
    Registry[(surface_graph_artifact)]
    ReleaseLedger[(release_ledger_*)]
    ReviewLedger[(mork_review_*)]
    GovLedger[(governance_ledger_entry)]
  end
  subgraph Broker[RabbitMQ]
    SurfaceQ[[surface job queues]]
    ProjQ[[projection lowering queues]]
    MorkQ[[mork analysis queues]]
  end
  subgraph Workers[Python Worker Tier]
    SurfaceWorker[Surface job worker]
    ProjWorker[Projection lowering worker]
    MorkWorker[MORK analysis worker]
  end
  Fuseki[(Fuseki RDF dataset)]
  Artifacts[(Artifact store / OCI registry)]

  Studio -->|HTTPS JSON| SurfaceAPI
  Studio -->|HTTPS JSON| ReleaseAPI
  Bench -->|HTTPS JSON| MorkAPI
  SurfaceAPI --> Ledger
  SurfaceAPI --> Registry
  SurfaceAPI -->|outbox row, same transaction| SurfaceQ
  ReleaseAPI --> ReleaseLedger
  MorkAPI --> ReviewLedger
  MorkAPI --> GovLedger
  SurfaceQ --> SurfaceWorker
  ProjQ --> ProjWorker
  MorkQ --> MorkWorker
  SurfaceWorker <-->|authorized read/write by GraphReference| Fuseki
  ProjWorker <-->|authorized read/write by GraphReference| Fuseki
  MorkWorker -->|read only, role-projected| Fuseki
  SurfaceWorker -->|generated output bytes| Artifacts
  ReleaseAPI -->|packages digests referenced by the ledger| Artifacts
  SurfaceWorker -->|result event| SurfaceAPI
  ProjWorker -->|result event| SurfaceAPI
  MorkWorker -->|result event| MorkAPI
```

Each arrow from a worker back to the Control Plane is a result event consumed on a dedicated result queue, not a direct database write from Python into PostgreSQL. The Control Plane is the only writer of operational state. See [solution-design-specification.md §2](solution-design-specification.md#2-process-design) for the full process maps this diagram summarizes.

## 5. Data Sharing and Concurrent Access Rules

1. **Optimistic concurrency on lifecycle state.** Every `SurfaceRevision` read returns a `version`. Every transition command carries `expectedVersion`. A mismatch is a `409`, never a silent overwrite. This is the only concurrency control on lifecycle rows, there is no row locking held across a user think-time.
2. **Immutable graph-family conflict rule.** `(tenantId, projectId, graphIri)` may be registered once. Registering the same key with a different hash, family, or owner revision is rejected outright, it is not resolved by "last write wins."
3. **Idempotent job replay.** `(jobId, requestDigest)` is the deduplication key for Surface jobs. A retried delivery with an identical request replays the cached result without recompiling. A reused `jobId` with different content is rejected.
4. **Snapshot staleness rule.** A MORK review decision must supply the exact `snapshotHash` of the snapshot it decides against. A newer registered snapshot makes the older hash stale, and a decision against a stale hash is rejected rather than merged.
5. **Tenant and project scoping.** Every graph reference, job, snapshot, and ledger row carries `tenantId` and `projectId`. Cross-scope reads are rejected at the policy layer (`GraphAccessPolicy`) before they reach a data store, not filtered out afterward in application code.
6. **No cross-realm foreign keys.** PostgreSQL never stores a foreign key into Fuseki, and Fuseki never stores a foreign key into PostgreSQL. The `GraphReference` is the only join, resolved at read time, so the two stores can be backed up, restored, or migrated independently.
7. **Single writer per data class.** Exactly one component writes each table in §3. Readers other than that writer access the data only through the Control Plane's read APIs, never through a direct database connection from a browser or from another component's worker process.

## 6. Retention, Immutability, and Lifecycle

- Graph content, generated output, and OCI artifacts are retained by content digest and are never mutated in place. Deletion is a retention-policy operation, not a routine one, and remains explicitly out of LATTICE's scope for the release stack (ADR-A31).
- Ledger tables (`release_ledger_event`, `mork_review_decision`, `governance_ledger_entry`) are append-only audit trails. They are the mechanism by which "who inspected this evidence and what did they do with it" stays answerable, per the Robustness and Component Design sections of the master specification.
- `surface_revision_ledger` and `mork_review_snapshot` currently overwrite the row's current-state columns rather than retaining a full state-transition history table. This is flagged as a gap in §7, because it limits point-in-time reconstruction of "what did the revision look like when approval X was granted" to what the ledger event trail (once implemented per §7) can reconstruct.

## 7. Open Gaps

These are implementation gaps, not design ambiguity. Each has a resolution direction so the next implementation slice has a concrete target.

| Gap | Impact | Resolution direction |
|---|---|---|
| Transactional outbox is in-memory only (`InMemoryTransactionalOutbox`) | An operational state change and its event are not yet durably atomic | Add a PostgreSQL-backed outbox table written in the same transaction as the lifecycle change, per [solution-design-specification.md §4](solution-design-specification.md#4-component-design) |
| No `job_status` or progress table | Studio cannot show worker progress without polling the worker tier directly | Add a Control Plane-owned `surface_job_status` table populated on enqueue and on result-event consumption |
| No durable review queue or calibration-gate history table | Atlas queue and calibration curve are computed from fixtures, not from persisted state | Add `review_queue_entry` and `calibration_run` tables, populated by the MORK governance service |
| No provenance graph publisher | `ReleaseProvenanceProjector` produces N-Triples that are not yet written to Fuseki | Add a `ProvenanceGraphPublisher` adapter invoked after receipt recording |
| No full state-history table for revisions or snapshots | Point-in-time reconstruction relies on ledger event replay, which does not yet exist for Surface revisions | Add a `surface_revision_event` table mirroring the pattern already used for release and governance ledgers |
