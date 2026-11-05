<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Release integration

The Java port through which LATTICE hands a semantic release to a release stack, and the ledger that records the evidence. LATTICE supplies the release intent and a stack packages, signs, stores and promotes it. See [Release stack integration](../../docs/architecture/release-stack-integration.md), [ADR-A31](../../docs/architecture/decisions/ADR-A31-release-stack-neutral-integration-contract.md), [ADR-A39](../../docs/architecture/decisions/ADR-A39-semantic-release-assembly-and-provenance-ledger.md) and [ADR-A40](../../docs/architecture/decisions/ADR-A40-oci-reference-export-restore-and-command-adapters.md).

## What it provides

| Type | Role |
|---|---|
| `ReleaseIntent`, `ReleaseReceipt`, `ContentReference`, `SemanticGateEvidence`, `ReleaseRequirements` | The records of the contract. An intent names the immutable graph revisions, the generated outputs by SHA-256 digest, the gate evidence, the environment, the retention class and any rollback target. A receipt records the adapter, the lifecycle state, the artifact digest and URI, and optional signature and diagnostic references. |
| `ReleaseStackAdapter`, `ReleaseCapability` | The adapter port. `plan` and `publish` are required. `promote`, `rollback`, `export`, `restore` and `retire` throw by default, since the configured release stack owns them. An adapter declares the capabilities it has. |
| `SemanticReleasePolicy`, `SemanticReleaseAssemblyService` | The assembly check. A release needs generated outputs, no duplicate graph reference and evidence for every required gate. The default policy for Surface requires approval, determinism, impact and parity. |
| `SemanticReleaseCoordinator` | The one place that calls an adapter. It assembles the intent, records it in the ledger, calls the adapter and records the receipt. |
| `ReleaseLedger`, `InMemoryReleaseLedger`, `JdbcReleaseLedger` | The append ledger of intents, receipts and events. The JDBC implementation targets PostgreSQL, with its schema in `src/main/resources/db/migration/V1__release_ledger.sql`. |
| `ReleaseProvenanceProjector` | Projects an intent, a receipt and the ledger events to N-Triples for a provenance graph. |
| `OciLayoutReleaseAdapter`, `OciLayoutBundleService` | An adapter that writes an OCI Image Layout without a registry client, and an export and restore of such a bundle with a manifest digest check. |
| `CosignReleaseSigner`, `OrasOciRegistryTransport`, `CommandRunner` | Deployment adapters that run the configured `cosign` and `oras` commands through a `CommandRunner`. |

## Build and test

```bash
mise run check:java
mise exec -- mvn -f platform/pom.xml -pl release-integration -am verify
```

The first command builds and tests every platform module. The second builds this module and the SPI it depends on. The tests cover the in-memory ledger, the OCI layout adapter and bundle service, the provenance projection and the assembly service, and need no registry or database. A pass is a Maven `BUILD SUCCESS`.

## Depends on

`semantic-dataset-spi`, for `GraphReference`. The signer and the registry transport call the `cosign` and `oras` programs when they are used.
