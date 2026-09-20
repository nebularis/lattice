<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Phase 3 Validation Handoff

**Status:** Accepted
**Governing ADRs:** [ADR-A31](../../architecture/decisions/ADR-A31-release-stack-neutral-integration-contract.md), [ADR-A39](../../architecture/decisions/ADR-A39-semantic-release-assembly-and-provenance-ledger.md), [ADR-A40](../../architecture/decisions/ADR-A40-oci-reference-export-restore-and-command-adapters.md)

## Scope

Phase 3 adds a release-stack-neutral contract and an OCI Image Layout reference adapter. It does not add a LATTICE-owned release pipeline, registry, deployment controller, signing service, workflow engine, or artifact-retention system.

## Commands

Run these commands from a clean network-enabled clone:

```text
mise install
mise run bootstrap
mvn -f platform/pom.xml -pl release-integration test
apply platform/release-integration/src/main/resources/db/migration/V1__release_ledger.sql to PostgreSQL
docker compose -f deployment/compose/docker-compose.yml --profile oci-reference up -d oci-registry
oras cp --from-oci-layout <layout-directory> localhost:5000/lattice/release:<tag>
cosign sign --yes localhost:5000/lattice/release@<manifest-digest>
docker compose -f deployment/compose/docker-compose.yml --profile oci-reference down -v
```

The Maven test verifies semantic release assembly, intent requirements, in-memory ledger ordering, deterministic RDF provenance projection, and offline OCI layout packaging with deterministic fixture data. A registry transport and a Cosign-backed signer are intentionally external adapters and require their own configured identity, registry namespace, and validation command matrix.

## Expected Artifacts

The reference adapter emits `oci-layout`, `index.json`, and digest-addressed blobs under a caller-selected directory. The receipt uses an immutable `sha256:` manifest digest. The release contract fixtures demonstrate a valid intent and one rejected by missing semantic gate evidence. A valid intent also supplies immutable profile, canonicalisation, approval, and impact evidence requirements.

The release schemas include adapter capabilities, intent, receipt, environment binding, export descriptor, restore request, and retention decision. The application coordinator records validated semantic intent before it invokes a release-stack adapter and records the resulting receipt after the adapter returns.

## Unverified Assumptions

The restricted authoring environment did not run Maven, Java 21, Docker, ORAS, Cosign, registry, signing, or CI commands. It has no Maven or Java 21 on `PATH`. Registry push, signature verification, PostgreSQL ledger integration, RDF provenance publication, restore against a live registry, and Compose profile execution require validation in a network-enabled environment.
