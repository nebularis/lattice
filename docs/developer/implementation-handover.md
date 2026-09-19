<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Implementation Handover

This is the consolidated handover for Phases 0 through 6 of the MORK and Surface delivery plan. It is the starting point for a coding agent, maintainer, or network-enabled validation environment. The canonical phase plan remains [plan-morkSurfaceImplementation.prompt.md](../../.github/prompts/plan-morkSurfaceImplementation.prompt.md).

## Status

Phases 0 through 6 are **authoring complete**. Their source, contracts, tests, CI wiring, ADRs, architecture documentation, and phase handoffs exist. None is validated complete. This authoring host could run JSON parsing, editor diagnostics, Markdown-link checks, and `git diff --check`, but did not have Java 21, Maven, a usable Python interpreter, Docker on `PATH`, resolved Yarn dependencies, Playwright browsers, or network access.

Phase 7 is not started. Do not begin it until a network-enabled environment returns a bounded validation result for the current phases or explicitly accepts the documented residual risks.

## Reading Order

1. Read the [canonical plan](../../.github/prompts/plan-morkSurfaceImplementation.prompt.md) for scope, completion criteria, and phase order.
2. Read the [toolchain guide](toolchain.md), [Windows and WSL guidance](windows-wsl.md), and [offline handoff procedure](offline-phase-handoff.md).
3. Read the [architecture map](../architecture/implementation-map.md), then the phase architecture guides listed below.
4. Read the relevant ADRs before changing a boundary. The complete catalogue is [ADR README](../adr/README.md).
5. Run one phase handoff at a time in a network-enabled environment. Do not regenerate lockfiles, images, or generated assets without reporting the resulting changes.

## Core Boundaries

```text
Ontology and compiler sources
  -> immutable graph references
  -> policy, revision, and review control planes
  -> RabbitMQ worker boundaries
  -> immutable outputs and MORK staging graphs
  -> semantic release intent
  -> external release stack
```

RDF remains the semantic source of truth. PostgreSQL holds operational state. RabbitMQ carries graph-reference jobs and results, never RDF payloads, credentials, browser tokens, or executable commands. The control plane authorizes tenant and project scope before resolving a graph. The worker materializes canonical graph bytes and verifies the referenced hash before invoking a compiler.

## Phase 0 and 1

**Purpose:** repository foundation and shared semantic platform.

| Surface | Source and contracts | Documentation and decisions |
|---|---|---|
| Toolchains and tasks | [mise.toml](../../mise.toml), [root package manifest](../../package.json), [platform reactor](../../platform/pom.xml) | [repository delivery foundation](../architecture/repository-delivery-foundation.md), [ADR-A29](../adr/ADR-A29-repository-toolchain-and-environment-boundary.md) |
| Reference environment | [Dev Container](../../.devcontainer/devcontainer.json), [Compose services](../../deployment/compose/docker-compose.yml) | [Windows and WSL](windows-wsl.md) |
| Semantic dataset and policy | [dataset SPI](../../platform/semantic-dataset-spi), [Fuseki adapter](../../platform/semantic-dataset-fuseki), [graph policy](../../platform/semantic-policy) | [semantic platform](../architecture/semantic-platform.md), [ADR-A30](../adr/ADR-A30-shared-semantic-platform-cross-runtime-boundary.md) |
| Outbox and worker boundary | [outbox module](../../platform/platform-outbox), [worker package](../../workers), [graph validation request](../../contracts/events/graph-validation-request.schema.json) | [Phase 0 and 1 handoff](phase-0-1-handoff.md) |

The Phase 1 deployment gaps are PostgreSQL-backed outbox validation, Testcontainers, and an end-to-end Java to RabbitMQ to Python worker retry test.

## Phase 2

**Purpose:** Surface Promotion and Index lifecycle, graph-family ownership, worker execution, and authoring UI.

| Surface | Source and contracts | Documentation and decisions |
|---|---|---|
| Revision lifecycle and ledger | [Surface workflow module](../../platform/surface-workflow), [revision schema](../../contracts/surface/surface-revision.schema.json), [transition schema](../../contracts/surface/surface-revision-transition.schema.json) | [Surface workflow](../architecture/surface-workflow.md), [ADR-A32](../adr/ADR-A32-surface-revision-lifecycle-and-release-candidates.md), [ADR-A33](../adr/ADR-A33-surface-revision-ledger-and-optimistic-concurrency.md) |
| Immutable graph families | [registry implementation](../../platform/surface-workflow/src/main/java/org/nebularis/lattice/surface/SurfaceGraphFamilyRegistry.java), [registry migration](../../platform/surface-workflow/src/main/resources/db/migration/V2__surface_graph_artifact_registry.sql) | [ADR-A34](../adr/ADR-A34-surface-graph-family-registry-and-immutable-identity.md) |
| Surface workers | [job dispatcher](../../workers/src/lattice_workers/surface_jobs.py), [compiler executor](../../workers/src/lattice_workers/surface_executor.py), [consumer](../../workers/src/lattice_workers/surface_consumer.py), [RabbitMQ adapter](../../workers/src/lattice_workers/rabbitmq_surface_worker.py) | [ADR-A35](../adr/ADR-A35-trusted-surface-worker-execution-boundary.md), [ADR-A36](../adr/ADR-A36-surface-worker-idempotent-delivery-boundary.md), [ADR-A37](../adr/ADR-A37-surface-worker-durable-processing-and-rabbitmq-acknowledgement.md) |
| Worker contracts and persistence | [Surface job request](../../contracts/events/surface-job-request.schema.json), [result](../../contracts/events/surface-job-result.schema.json), [processed-job migration](../../workers/sql/V1__processed_surface_jobs.sql) | [Phase 2 handoff](phase-2-handoff.md) |
| Surface Contract Studio | [Studio source](../../apps/surface-contract-studio/src/studio.tsx), [Studio E2E](../../apps/surface-contract-studio/e2e/studio.spec.ts) | [Surface Contract Studio](../architecture/surface-contract-studio.md), [ADR-A38](../adr/ADR-A38-surface-output-publication-and-studio-authoring-boundary.md) |

Normative Surface semantics remain in [surface/README.md](../../surface/README.md). Existing Promotion, Index, parity, invalidation, and lowering algorithms remain in [tools/surface](../../tools/surface). The control plane must not reimplement them.

## Phase 3

**Purpose:** release-stack-neutral semantic release integration and OCI reference implementation.

| Surface | Source and contracts | Documentation and decisions |
|---|---|---|
| Semantic release requirements | [release integration module](../../platform/release-integration), [release intent](../../contracts/release/release-intent.schema.json), [release receipt](../../contracts/release/release-receipt.schema.json) | [release integration](../architecture/release-stack-integration.md), [ADR-A31](../adr/ADR-A31-release-stack-neutral-integration-contract.md), [ADR-A39](../adr/ADR-A39-semantic-release-assembly-and-provenance-ledger.md) |
| OCI reference, signing, and transport | [OCI adapter](../../platform/release-integration/src/main/java/org/nebularis/lattice/release/OciLayoutReleaseAdapter.java), [bundle service](../../platform/release-integration/src/main/java/org/nebularis/lattice/release/OciLayoutBundleService.java), [Cosign adapter](../../platform/release-integration/src/main/java/org/nebularis/lattice/release/CosignReleaseSigner.java), [ORAS adapter](../../platform/release-integration/src/main/java/org/nebularis/lattice/release/OrasOciRegistryTransport.java) | [OCI operator reference](../operator/release-stack-reference.md), [release security](../security/release-integration.md), [ADR-A40](../adr/ADR-A40-oci-reference-export-restore-and-command-adapters.md) |
| Ledger and provenance | [release ledger migration](../../platform/release-integration/src/main/resources/db/migration/V1__release_ledger.sql), [provenance projector](../../platform/release-integration/src/main/java/org/nebularis/lattice/release/ReleaseProvenanceProjector.java) | [Phase 3 handoff](phase-3-handoff.md) |
| Operation contracts | [environment binding](../../contracts/release/environment-binding.schema.json), [export](../../contracts/release/export-descriptor.schema.json), [restore](../../contracts/release/restore-request.schema.json), [retention](../../contracts/release/retention-decision.schema.json) | [release integration architecture](../architecture/release-stack-integration.md) |

LATTICE creates and verifies semantic intent. The release stack packages, signs, stores, promotes, restores, and retains artifacts. A valid signature does not prove semantic validity, and passed semantic gates do not prove release-stack provenance.

## Phase 4

**Purpose:** deterministic Surface Projection lowering to immutable MORK staging.

| Surface | Source and contracts | Documentation and decisions |
|---|---|---|
| Projection DTO and policy | [Projection contract](../../contracts/surface/projection-contract.schema.json), [handoff policy](../../contracts/surface/mork-handoff-policy.schema.json), [projection validator](../../workers/src/lattice_workers/projection_contract.py) | [Surface Projection to MORK](../architecture/surface-projection-mork.md), [ADR-A41](../adr/ADR-A41-surface-projection-mork-staging-boundary.md) |
| Lowering worker | [lower request](../../contracts/events/projection-lower-request.schema.json), [lower result](../../contracts/events/projection-lower-result.schema.json), [worker dispatcher](../../workers/src/lattice_workers/projection_lowering.py) | [Phase 4 handoff](phase-4-handoff.md) |
| Fixture and inspection | [ARR Projection fixture](../../surface/examples/saas-subscription-arr-projection.ttl), [Technical Inspector schema](../../contracts/surface/technical-inspector.schema.json), [Studio](../../apps/surface-contract-studio/src/studio.tsx) | [Surface lowering](../../tools/surface/lowering.py) |

All Projection policies are deterministic-only and prohibit LLM completion. Lowering accepts only graph references and a staging namespace. It rejects active mapping targets. MORK governance, not Surface, owns activation.

## Phase 5

**Purpose:** immutable MORK review snapshots, six decision semantics, role-safe evidence, and the Review Bench.

| Surface | Source and contracts | Documentation and decisions |
|---|---|---|
| Snapshot and decision model | [snapshot schema](../../contracts/mork/review-snapshot.schema.json), [decision schema](../../contracts/mork/review-decision.schema.json), [review semantics](../../workers/src/lattice_workers/mork_review.py), [lifecycle](../../workers/src/lattice_workers/mork_review_lifecycle.py) | [MORK Review Workbench](../architecture/mork-review-workbench.md), [ADR-A42](../adr/ADR-A42-mork-review-snapshot-and-decision-learning-boundary.md) |
| Role-restricted analysis | [evidence projection](../../workers/src/lattice_workers/mork_evidence_projection.py), [analysis worker](../../workers/src/lattice_workers/mork_analysis_worker.py), [review ledger migration](../../workers/sql/V2__mork_review_ledger.sql) | [Phase 5 handoff](phase-5-handoff.md) |
| Review Bench | [Workbench source](../../apps/mork-review-workbench/src/main.tsx), [Bench E2E](../../apps/mork-review-workbench/e2e/bench.spec.ts) | [MORK community package](../../mork/src/python/mork_communities) |

Domain Stewards can receive only review-safe evidence projections. They must not receive MCN, lint diagnostics, pack internals, MORK syntax, or cross-tenant content. `RESHAPE` produces structural feedback and must never change projection statistics.

## Phase 6

**Purpose:** replayable review queue, calibration-gated bulk action, governance ledger, and safe Atlas, Boundary, Ledger, and Pack fixtures.

| Surface | Source and contracts | Documentation and decisions |
|---|---|---|
| Queue and calibration | [queue schema](../../contracts/mork/review-queue.schema.json), [calibration schema](../../contracts/mork/calibration-gate.schema.json), [governance rules](../../workers/src/lattice_workers/mork_governance.py) | [MORK Queue, Calibration, and Governance](../architecture/mork-queue-calibration-governance.md), [ADR-A43](../adr/ADR-A43-mork-replayable-queue-and-calibrated-governance.md) |
| Governance commands | [minting request](../../contracts/mork/ontology-minting-request.schema.json), [retrospective challenge](../../contracts/mork/retrospective-challenge.schema.json), [template exception](../../contracts/mork/template-exception.schema.json) | [Phase 6 handoff](phase-6-handoff.md) |
| Governance ledger | [ledger schema](../../contracts/mork/governance-ledger-entry.schema.json), [ledger model](../../workers/src/lattice_workers/mork_governance_ledger.py), [Workbench fixture](../../apps/mork-review-workbench/src/main.tsx) | [Review Bench E2E](../../apps/mork-review-workbench/e2e/bench.spec.ts) |

Queue ordering is replayable. Bulk confirmation requires a passing calibration gate for the exact pack, profile, and model. Named ontology axioms reopen affected approvals without deleting prior history. Template exceptions require engineering review. Pack Studio and Domain Steward projections must not expose source syntax or technical internals.

## Validation Sequence

Run the phase handoffs in order. The current codebase has a generated or placeholder [Yarn lockfile](../../yarn.lock) that must be regenerated and reviewed with the committed package manifests before frontend validation. Do not claim a lockfile is valid until that occurs.

```text
mise install
mise run bootstrap
mise run check
mise run test

mvn -f platform/pom.xml verify
python -m pytest workers/tests
python -m unittest tools.surface.test_surface tools.mork_compilers.test_mork_compilers -v
python -m tools.phase8_conformance

yarn install
yarn check
yarn build
yarn playwright install --with-deps chromium
yarn test
```

Apply these migrations to the reference PostgreSQL database before integration tests:

```text
platform/surface-workflow/src/main/resources/db/migration/V1__surface_revision_ledger.sql
platform/surface-workflow/src/main/resources/db/migration/V2__surface_graph_artifact_registry.sql
platform/release-integration/src/main/resources/db/migration/V1__release_ledger.sql
workers/sql/V1__processed_surface_jobs.sql
workers/sql/V2__mork_review_ledger.sql
```

Start reference services using `mise run services:up`. Exercise Fuseki graph materialization, RabbitMQ acknowledgement, retry and dead-letter behavior, PostgreSQL persistence, OCI registry packaging and restore, and role-restricted review projections. Stop services with `mise run services:down` and use the phase handoffs for fixture and cleanup specifics.

## Validation Evidence and Gaps

Validation evidence belongs in CI or release records, not this document. The expected offsite acceptance conditions are:

- Existing Surface parity and Phase 8 conformance pass through the worker path.
- Stale Surface revisions and MORK review snapshots conflict safely.
- Surface output, MORK staging, and release artifacts are immutable and digest-addressed.
- The OCI reference signs, publishes, verifies, exports, restores, and records a receipt by digest.
- Projection lowering cannot write active MORK mappings.
- Domain Steward, Pack Studio, and review APIs do not leak restricted technical content.
- Queue order is replayable, and bulk confirmation remains blocked without matching calibration.

## Do Not Break

- Do not move or rewrite normative ontology directories. Layer READMEs remain normative.
- Do not replace native package managers with `mise`.
- Do not place RDF, credentials, browser tokens, file paths, shell commands, or mutable tags in worker or release contracts.
- Do not write an active MORK mapping from Surface or expose mapping activation in Surface-facing UI.
- Do not let `RESHAPE` alter projection statistics.
- Do not allow evidence projections for Domain Stewards to return MCN, syntax, lint diagnostics, pack internals, or cross-tenant data.
- Do not state that builds, tests, container pulls, registry operations, signing, or CI passed until evidence exists in the network-enabled environment.

## Next Phase

Phase 7 begins only after validation feedback is triaged. Its scope is compiler breadth and SPC readiness: adapter conformance, MORK-to-SPC bridge contracts with isolated RabbitMQ exchanges, and independently deployable SPC behavior. Read the Phase 7 section of the [canonical plan](../../.github/prompts/plan-morkSurfaceImplementation.prompt.md) before changing its boundary.