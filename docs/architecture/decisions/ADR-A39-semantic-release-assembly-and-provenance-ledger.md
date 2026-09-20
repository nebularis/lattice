<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# ADR-A39: Semantic release assembly and provenance ledger

**Status:** Accepted
**Date:** 2026-09-19
**Supersedes:** none
**Related:** Phase 3, ADR-A26, ADR-A27, ADR-A28, ADR-A31, [release integration architecture](../release-stack-integration.md)

## Context

An OCI artifact can be syntactically valid while lacking required semantic approval, impact, profile, or canonicalisation evidence. Release-stack receipts also need an auditable LATTICE record without duplicating registry, workflow, deployment, or storage implementation details.

## Decision

Require `ReleaseRequirements` on every release intent, carrying profile identity and revision hash, canonicalisation version, approval evidence digest, and impact evidence digest. `SemanticReleaseAssemblyService` verifies generated outputs, unique immutable graph references, and the policy-required semantic gates before a release stack adapter is invoked.

Record semantic intents, adapter receipts, and correlated lifecycle events through `ReleaseLedger`. Receipt recording requires a prior semantic intent. Project these records through `ReleaseProvenanceProjector` to deterministic N-Triples for later storage in an RDF provenance graph. The ledger and projection store release-facing evidence and correlation references only, not RDF payloads or generic release-stack state.

## Consequences

- A release stack cannot package an intent until LATTICE has evidence for approval, determinism, impact, and parity under the default Surface policy.
- Surface lifecycle callers must supply requirements explicitly. They cannot infer approval or impact evidence from UI state or a receipt.
- In-memory ledger behavior and deterministic RDF provenance projection are testable now. `JdbcReleaseLedger` persists canonical intent and receipt evidence plus ordered event records in PostgreSQL. Integration with an RDF dataset and PostgreSQL integration tests remain required before Phase 3 is authoring complete.
