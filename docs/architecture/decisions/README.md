<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Architecture Decision Records

This directory holds the ADRs that govern LATTICE's substrate architecture. An ADR is the authoritative record of a decision, its context, and its consequences. Layer READMEs describe *what* a layer is; ADRs describe *why* the layers are shaped, ordered, and bounded the way they are.

## Convention

- Filename: `ADR-{id}-{slug}.md`, for example `ADR-A01-layer-dependency-order.md`.
- IDs are stable once assigned and are never reused, even if an ADR is superseded.
- Each ADR uses the same shape: Status, Context, Decision, Consequences.
- Status is one of `Proposed`, `Accepted`, `Superseded by ADR-{id}`.
- An ADR may be amended in place for clarifications that do not change the decision. A change to the decision itself is a new ADR that supersedes the old one.

## Index

| ADR | Title | Status |
|---|---|---|
| [A-01](ADR-A01-layer-dependency-order.md) | Layer dependency order and import direction | Accepted |
| [A-12](ADR-A12-identity-and-derivation-model.md) | Identity and derivation-authority model | Accepted |
| [A-13](ADR-A13-dataset-graph-role-model.md) | Dataset, graph-role, and provenance model | Accepted |
| [A-14](ADR-A14-conformance-levels.md) | Conformance-level framework | Accepted |
| [A-15](ADR-A15-realisation-strategy-neutrality.md) | Realisation-strategy neutrality | Accepted |
| [A-16](ADR-A16-surface-projection-mechanism.md) | Surface projection mechanism | Accepted |
| [A-17](ADR-A17-surface-unified-projection-authoring-model.md) | Surface unified projection authoring model | Accepted |
| [A-18](ADR-A18-surface-to-mork-lowering-boundary.md) | Surface-to-MORK lowering boundary | Accepted |
| [A-19](ADR-A19-staged-compiler-architecture-and-backend-fanout.md) | Staged compiler architecture and backend fan-out | Accepted |
| [A-20](ADR-A20-projection-subsystem-semantics-and-laws.md) | Projection subsystem semantics and law model | Accepted |
| [A-21](ADR-A21-signature-scope-composition-for-stacked-surfaces.md) | Signature-scope and conservativity composition in stacked surfaces | Accepted |
| [A-22](ADR-A22-mork-governance-and-versioning-foundation-alignment.md) | MORK governance and versioning with Foundation alignment | Accepted |
| [A-23](ADR-A23-mork-compiler-family-completion-policy.md) | MORK compiler family completion policy | Accepted |
| [A-24](ADR-A24-eligibility-executable-semantics-backend-strategy.md) | Eligibility executable semantics and backend strategy | Accepted |
| [A-25](ADR-A25-llm-participation-and-deterministic-production-gate.md) | LLM participation and deterministic production gate | Accepted |
| [A-26](ADR-A26-provenance-chain-completeness-across-surface-mork-artefacts.md) | Provenance chain completeness across Surface, MORK, and artefacts | Accepted |
| [A-27](ADR-A27-invalidation-and-minimal-scope-regeneration-policy.md) | Invalidation and minimal-scope regeneration policy | Accepted |
| [A-28](ADR-A28-parity-and-conformance-release-gate.md) | Parity and conformance gate for generated behaviours | Accepted |
| [A-29](ADR-A29-repository-toolchain-and-environment-boundary.md) | Repository toolchain and environment boundary | Accepted |
| [A-30](ADR-A30-shared-semantic-platform-cross-runtime-boundary.md) | Shared semantic platform and cross-runtime boundary | Accepted |
| [A-31](ADR-A31-release-stack-neutral-integration-contract.md) | Release-stack-neutral integration contract | Accepted |
| [A-32](ADR-A32-surface-revision-lifecycle-and-release-candidates.md) | Surface revision lifecycle and immutable release candidates | Accepted |
| [A-33](ADR-A33-surface-revision-ledger-and-optimistic-concurrency.md) | Surface revision ledger and optimistic concurrency | Accepted |
| [A-34](ADR-A34-surface-graph-family-registry-and-immutable-identity.md) | Surface graph-family registry and immutable identity | Accepted |
| [A-35](ADR-A35-trusted-surface-worker-execution-boundary.md) | Trusted Surface worker execution boundary | Accepted |
| [A-36](ADR-A36-surface-worker-idempotent-delivery-boundary.md) | Surface worker idempotent delivery boundary | Accepted |
| [A-37](ADR-A37-surface-worker-durable-processing-and-rabbitmq-acknowledgement.md) | Surface worker durable processing and RabbitMQ acknowledgement | Accepted |
| [A-38](ADR-A38-surface-output-publication-and-studio-authoring-boundary.md) | Surface output publication and Studio authoring boundary | Accepted |
| [A-39](ADR-A39-semantic-release-assembly-and-provenance-ledger.md) | Semantic release assembly and provenance ledger | Accepted |
| [A-40](ADR-A40-oci-reference-export-restore-and-command-adapters.md) | OCI reference export, restore, and command adapters | Accepted |
| [A-41](ADR-A41-surface-projection-mork-staging-boundary.md) | Surface Projection to MORK staging boundary | Accepted |
| [A-42](ADR-A42-mork-review-snapshot-and-decision-learning-boundary.md) | MORK review snapshot and decision-learning boundary | Accepted |
| [A-43](ADR-A43-mork-replayable-queue-and-calibrated-governance.md) | MORK replayable queue and calibrated governance | Accepted |
| [A-44](ADR-A44-mork-teaching-pack-generated-content-boundary.md) | MORK Teaching Pack generated-content boundary | Accepted |
| [A-03](ADR-A03-condition-taxonomy.md) | Eligibility condition taxonomy | Accepted |
| [A-04](ADR-A04-interval-overlap-law-split.md) | Interval containment and overlap law split | Accepted |
| [A-05](ADR-A05-compatibility-vocabulary.md) | Compatibility operation vocabulary | Accepted |
| [A-06](ADR-A06-wildcard-semantics.md) | Wildcard semantics and limits | Accepted |
| [A-07](ADR-A07-eligibility-authoring-direction.md) | Eligibility authoring direction and extraction contract | Accepted |
| [A-07b](ADR-A07b-minimal-instrument-shape.md) | Minimal Instrument shape and versioning contract | Accepted |
| [A-08](ADR-A08-behaviour-four-tier-model.md) | Behaviour four-tier model | Accepted |
| [A-09](ADR-A09-behaviour-selection-policy.md) | Behaviour selection policy | Accepted |
| [A-10](ADR-A10-behaviour-activation-policy.md) | Behaviour activation policy | Accepted |
| [A-11](ADR-A11-effect-and-target-binding.md) | Effect payload and target binding contract | Accepted |
| [A-C1](ADR-AC1-applied-layer-theorem-restatement.md) | Applied-layer theorem restatement policy | Accepted |
| [A-C2](ADR-AC2-clean-room-authoring-procedure.md) | Clean-room authoring procedure for substrate content | Accepted |
| [A-78](ADR-A78-persistence-profile-substrate-and-aggregate-boundaries.md) | Persistence profile substrate and configurable aggregate boundaries | Accepted |
| [A-79](ADR-A79-persistence-compiler-toolchain.md) | Persistence compiler toolchain and template-based SPARQL generation | Accepted |
| [A-80](ADR-A80-housekeeping-component-boundary.md) | Housekeeping component boundary | Accepted |
| [A-48](ADR-A48-transaction-boundary-catalogue.md) | Transaction boundary catalogue (replaces CAP framing) | Proposed |
| [A-50](ADR-A50-role-profiled-deployment.md) | Role-profiled deployment | Proposed |
| [A-51](ADR-A51-iri-and-identity-policy.md) | IRI and identity policy | Superseded by A-82 |
| [A-54](ADR-A54-dataset-topology.md) | Dataset topology and named-graph layout | Proposed |
| [A-57](ADR-A57-change-feed.md) | Change feed via write-side emission and reconciliation | Proposed |
| [A-59](ADR-A59-partitioned-work-queue-abstraction.md) | `PartitionedWorkQueue` abstraction | Proposed |
| [A-62](ADR-A62-spc-namespace-harmonisation.md) | SPC namespace harmonisation and integration deferral | Proposed |
| [A-63](ADR-A63-project-vs-environment-scoping.md) | Project vs environment scoping | Proposed |
| [A-65](ADR-A65-provenance-model.md) | Provenance model (named-graph-per-batch) | Proposed |
| [A-66](ADR-A66-principal-model.md) | Principal model extension | Proposed |
| [A-67](ADR-A67-bi-temporal-model.md) | Bi-temporal model | Proposed |
| [A-68](ADR-A68-pii-and-erasure.md) | PII and erasure | Proposed |
| [A-69](ADR-A69-pack-trust-and-safe-sparql-subset.md) | Pack trust model and safe SPARQL subset | Proposed |
| [A-71](ADR-A71-platform-licence-and-spi-seam.md) | Platform licence (MPL-2.0) and SPI seam | Proposed |
| [A-74](ADR-A74-graph-primary-realm-model.md) | Graph-primary realm model | Proposed |
| [A-75](ADR-A75-three-tier-store-spi.md) | Three-tier store SPI (Core/Extended/Native) | Proposed |
| [A-81](ADR-A81-control-plane-http-runtime.md) | Control Plane HTTP runtime | Proposed |
| [A-82](ADR-A82-framework-neutral-identity-pattern-selection.md) | Framework-neutral identity pattern selection | Proposed |

ADR numbering deliberately skips A-02. Eligibility (A-03–A-07 and A-07b) and Behaviour (A-08–A-11) are now assigned to the decisions authored in Gates 2 and 3. A-02 remains reserved for the document-hierarchy question folded into [../../GOVERNANCE.md](../../GOVERNANCE.md) instead of a standalone ADR. A-17–A-28 are the Surface-MORK unified projection wave, numbered continuously from A-16 per the [ADR bundle outline](../../../ontology/surface/docs/adr-bundle-outline-surface-mork-unified-projection.md); accepted following maintainer sign-off on the [delivery plan](../../../ontology/surface/docs/surface-mork-unified-projection-delivery-plan.md) Phase 0 architecture lock. A-45 through A-76 were reserved by forward reference from `solution-design-specification.md` and `Architecture Review.md`; A-48, A-50, A-51, A-54, A-57, A-59, A-62, A-63, A-65 through A-69, A-71, and A-74/A-75 are now filed as `Proposed`, drafted autonomously against that reserved block during Phase 0's P0.1 decision slices and pending human ratification (see [phase-0-status.md](../../developer/status/phase-0-status.md)). A-76 (Maven vs Gradle) remains reserved, deferred to build-skeleton slice P0.2.1. A-78 through A-80 are assigned outside that reserved block, to avoid pre-empting a number a referring document already names for a different topic. The epic's own forward reference to "ADR-A44 amended" collides with the existing, unrelated, accepted A-44 (MORK Teaching Pack); that content is filed instead as new ADR-A81, the next free number after A-80. This index is updated as each is added.
