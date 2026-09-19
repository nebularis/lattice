<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# ADR-A40: OCI reference export, restore, and command adapters

**Status:** Accepted
**Date:** 2026-09-19
**Supersedes:** none
**Related:** Phase 3, ADR-A31, [release integration architecture](../architecture/release-stack-integration.md)

## Context

The OCI reference adapter can package an Image Layout offline, but Phase 3 also requires portable export and restore evidence plus an integration route to established registry and signing tools. LATTICE must not embed ORAS or Cosign as semantic runtime dependencies.

## Decision

Provide `OciLayoutBundleService` to copy an OCI layout as a portable bundle and verify its `index.json` digest before and after restore. Provide narrow `CommandRunner`-backed adapters for Cosign signing and ORAS registry transport. These adapters are invoked only by deployment configuration and can be replaced with other implementations of the same ports.

## Consequences

- Offline fixture tests can prove export and restore integrity without a live registry.
- ORAS and Cosign commands, identity, keyless policy, registry namespace, and network behavior remain validation-environment concerns.
- A release stack remains responsible for promotion, rollback, retention enforcement, and deployment. LATTICE owns only semantic intent and evidence.
