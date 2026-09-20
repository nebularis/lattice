<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Release Stack Integration

LATTICE supplies semantic release intent. A release stack packages, signs, stores, promotes, deploys, retains, exports, restores, and observes that intent using its native capabilities.

This boundary prevents LATTICE from becoming a release engine. It also lets deployments use Docker plus CI, Kubernetes GitOps, or a durable workflow engine without changing semantic release identity or gate evidence.

## Contract

`ReleaseIntent` is created by LATTICE after semantic gates pass. It identifies immutable graph revisions and generated outputs by digest, carries the tenant and project scope, and records the requested environment and retention requirements. It excludes RDF payloads, credentials, tokens, mutable tags, endpoint configuration, and deployment commands.

`ReleaseReceipt` is produced by a release-stack adapter. It records immutable artifact location and digest, signing or provenance references, environment binding, lifecycle state, and safe diagnostic references. It cannot claim that LATTICE semantic gates passed.

The contract schemas live in `contracts/release/`. The Java port lives in `platform/release-integration/`. Adapters negotiate capabilities before performing an operation. The port has methods for planning, publishing, promoting, rolling back, exporting, restoring, and retiring a release. An adapter explicitly rejects operations it does not own.

## Responsibility Split

LATTICE owns graph lineage, semantic validation, parity, determinism, invalidation, approval evidence, semantic impact evidence, and release provenance.

The release stack owns registry and object storage, signing keys, credential management, artifact lifecycle, deployment mechanics, generic retention enforcement, rollouts, infrastructure backup, workflow scheduling, and telemetry storage.

## OCI Reference

The reference adapter writes a standard OCI Image Layout. Its OCI manifest references canonical release-intent and release-inventory layers. The returned receipt is addressed by the immutable OCI manifest digest. It can be tested offline from the generated layout and connected to an OCI registry by a transport adapter outside the semantic model.

The reference does not make ORAS, Cosign, Docker, a specific registry, or any CI product a LATTICE runtime requirement. An ORAS-compatible transport can publish the layout, and a Cosign-compatible signer can implement `ReleaseSigner` in deployment code.

## Deployment Models

For Docker plus CI, CI calls the semantic gates and adapter, publishes the resulting OCI layout, then deploys services with immutable digests.

For Kubernetes GitOps, CI or a workflow invokes the same adapter and updates an environment binding in Git. Argo CD or Flux reconciles that binding. The receipt should record Git revision, reconciliation outcome, deployment revision, and digest.

For a durable workflow engine, the workflow invokes the same operations and persists operation IDs. It can wait for approval, retry safely, and compensate failed external steps without replacing LATTICE semantic evidence.

## Contract Lifecycle

```text
immutable Surface and graph evidence
	-> LATTICE assembles ReleaseIntent
	-> adapter capability check and plan
	-> adapter packages and publishes immutable artifact
	-> adapter returns ReleaseReceipt
	-> external stack promotes or restores by digest
	-> LATTICE records semantic lineage and receipt correlation
```

`ReleaseIntent` is a request to a release stack, not a deployment manifest. It names the semantic inputs, output digests, environment requirements, gate evidence, and retention posture. `ReleaseReceipt` is evidence from an adapter, not semantic approval. A receipt must name the immutable digest that was actually packaged or promoted.

The schemas are located in `contracts/release/`. They use separate fields for LATTICE evidence and adapter evidence so a caller cannot substitute a successful registry upload for parity or approval, and a semantic gate cannot substitute for provenance verification.

## Semantic Assembly and Ledger

`ReleaseRequirements` makes the semantic release prerequisites explicit: profile ID and immutable profile revision hash, canonicalisation version, approval evidence digest, and impact evidence digest. `SemanticReleaseAssemblyService` applies the required-gate policy before an adapter can package a release. The default Surface policy requires approval, determinism, impact, and parity. It also requires generated outputs and rejects duplicate immutable graph references.

`ReleaseLedger` records the semantic intent before it accepts a receipt, then retains correlated lifecycle events such as promotion request, rollback request, export, restore, retention request, and failure. It records LATTICE evidence and references only. `JdbcReleaseLedger` persists canonical intent and receipt JSON plus ordered events through `platform/release-integration/src/main/resources/db/migration/V1__release_ledger.sql`. The receipt table has a foreign key to recorded intent, so a durable receipt cannot precede semantic intent. `ReleaseProvenanceProjector` turns intent, receipt, and ordered events into deterministic N-Triples for a later RDF provenance graph. The release stack remains the authority for registry lifecycle, deployment state, and workflow implementation. RDF dataset publication and PostgreSQL integration validation remain Phase 3 work.

`SemanticReleaseCoordinator` is the application entry point for `plan` and `publish`. It assembles the intent, records it, invokes the chosen adapter, then records the returned receipt. Application code must use this boundary rather than call an adapter directly. Environment binding, export, restore, and retention payloads are versioned under `contracts/release/`; the configured release stack implements those operations according to its declared capabilities.

## Adapter Capability Model

The `ReleaseStackAdapter` port exposes `plan`, `publish`, `promote`, `rollback`, `export`, `restore`, and `retire`. Capabilities declare which operations an adapter actually supports. Default operations explicitly fail when the chosen adapter does not own that behavior. This keeps a local OCI layout adapter from accidentally claiming GitOps promotion or storage retention capabilities.

Adapters may be synchronous internally but must retain opaque release and correlation IDs. A durable workflow engine may poll, receive callbacks, or resume from persisted operation state. These transport choices are not part of release identity.

## OCI Layout Reference

`OciLayoutReleaseAdapter` writes an OCI Image Layout to a caller-selected directory:

```text
oci-layout
index.json
blobs/sha256/<config>
blobs/sha256/<release-intent layer>
blobs/sha256/<release-inventory layer>
blobs/sha256/<manifest>
```

The manifest digest is the receipt's artifact identity. The adapter uses `ReleaseSigner` as a narrow extension point. A deterministic test double can return a reference without a key. A production Cosign-compatible signer and an ORAS-compatible registry transport belong outside the domain model. The optional Compose registry profile exists only for integration validation and has no production security posture.

`OciLayoutBundleService` exports a local OCI layout as a portable directory bundle and verifies the `index.json` SHA-256 digest before and after restore. `CosignReleaseSigner` and `OrasOciRegistryTransport` are `CommandRunner` adapters. They deliberately know only command construction, not key custody, authentication, promotion policy, or release semantics. Production configuration supplies those external concerns.

## Promotion, Recovery, and Retention

Promotion binds a previously verified digest to an environment. It must not rebuild an artifact from source or a mutable tag. Rollback promotes an earlier verified receipt and retains the new audit event. Export and restore use content-addressed bundles and must verify every graph and generated-output digest in an isolated target before the release stack activates it.

Legal hold and retention classes originate in the intent. The system enforcing physical deletion is the artifact store or release stack, which returns acknowledgement evidence in its receipt. LATTICE records semantic lineage and the retention request, but never operates a storage lifecycle engine.

## Operational Evidence

The adapter should emit OpenTelemetry-compatible trace links and preserve the correlation ID. The stack stores traces, logs, metrics, dashboards, and alerts. LATTICE requires enough receipt data to correlate a semantic release to those signals, while avoiding a dependency on a specific telemetry backend.

See [ADR-A31](../adr/ADR-A31-release-stack-neutral-integration-contract.md), [the operator reference](../operator/release-stack-reference.md), and [the Phase 3 handoff](../developer/phase-3-handoff.md) for implementation and validation boundaries.
