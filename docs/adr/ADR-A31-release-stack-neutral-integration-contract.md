<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# ADR-A31: Release-stack-neutral integration contract

**Status:** Accepted
**Date:** 2026-09-19
**Supersedes:** none
**Related:** Phase 3, ADR-A26, ADR-A27, ADR-A28, [release integration architecture](../architecture/release-stack-integration.md)

## Context

LATTICE needs semantic release identity, immutable graph lineage, gate evidence, and recoverable output references. It does not need to own a generic artifact registry, signing service, deployment controller, GitOps reconciler, workflow engine, object store, or telemetry backend. Binding the domain model to one of these choices would prevent deployments from using Docker plus CI, Kubernetes GitOps, or durable workflows.

## Decision

Define `ReleaseIntent`, `ReleaseReceipt`, adapter capabilities, and immutable digest requirements as a versioned integration contract. LATTICE creates semantic release intent only after its gates pass. A release stack packages, signs, publishes, promotes, restores, retains, and reports receipts using its native mechanisms. Provide an OCI Image Layout reference adapter and optional signing port as an interoperability reference, not as a required production stack.

## Consequences

- Semantic gate evidence and release-stack signature or deployment evidence remain distinct and neither substitutes for the other.
- Published, promoted, restored, and rolled-back releases use immutable digests. Tags are discovery aids only.
- The OCI reference can run fixture tests offline. Registry transport, signing identity, and production promotion remain external adapters and require offsite validation.
- Future Kubernetes, CI, and workflow integrations map to the same contract without changing semantic release identity.
