<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# OCI Release Reference

The OCI reference is an interoperability example. It packages LATTICE semantic release metadata as a local OCI Image Layout. It is not a production release pipeline.

## Local Reference Registry

Start the optional OCI-compatible registry with:

```text
docker compose -f deployment/compose/docker-compose.yml --profile oci-reference up -d oci-registry
```

The registry listens on port `5000`. It is development-only and has no authentication, TLS, retention rules, or persistent backup configuration. Do not expose it outside a trusted local environment.

## Required Production Controls

A production release stack must:

- publish and promote immutable artifact digests, not tags;
- authenticate registry operations using workload identity or another managed credential mechanism;
- sign artifacts and verify signatures before promotion;
- retain a portable export and verify digest integrity during restore;
- record the environment binding, deployment revision, and rollback target in the release receipt;
- enforce retention and legal holds in the stack that owns physical storage;
- preserve correlation IDs in CI logs, workflow state, telemetry, and adapter receipts.

## Recovery

To recover a semantic release, select a previously verified receipt by immutable digest, export its OCI bundle, restore it into an isolated target, verify graph and generated-output digests, then request promotion through the release stack. LATTICE supplies the semantic lineage and gate evidence. The release stack performs artifact restoration and deployment.
