<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# ADR-A38: Surface output publication and Studio authoring boundary

**Status:** Accepted
**Date:** 2026-09-19
**Supersedes:** none
**Related:** Phase 2, ADR-A32, ADR-A34, ADR-A35, [Surface Contract Studio architecture](../architecture/surface-contract-studio.md)

## Context

Generated Surface output is needed by release candidates, diff views, and recovery. Worker temporary directories are not durable artifact storage. Authors also need a typed authoring experience that does not require editing Turtle, while technical users need to inspect the generated declaration.

## Decision

Publish successful compiler output through a `SurfaceOutputPublisher` port. The reference filesystem implementation stores Turtle output by SHA-256 digest and returns a descriptor with media type, digest, and immutable URI. Failed compiler runs publish nothing.

Provide the Surface Contract Studio as a React workspace that authors the typed workflow contract, not raw RDF. It exposes Promotion and Index modes, path and closure controls, profile selection, law evidence, dependency impact, output diff, and technical Turtle inspection. The initial UI is fixture-backed and is designed to bind to the framework-neutral Surface Workflow OpenAPI contract when an HTTP adapter is deployed.

## Consequences

- Generated output survives worker cleanup and can be registered as an immutable graph-family artifact by a deployment publisher.
- A graph-store or object-store publisher can replace the filesystem reference without changing worker job semantics.
- Studio E2E tests exercise authoring affordances independently of a live backend. API integration tests remain required once the HTTP adapter exists.
- The Yarn lockfile must be regenerated in the network-enabled validation environment for the newly added React, Vite, Lucide, and Playwright dependencies.
