<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# ADR-A35: Trusted Surface worker execution boundary

**Status:** Accepted
**Date:** 2026-09-19
**Supersedes:** none
**Related:** Phase 2, ADR-A30, ADR-A27, ADR-A28, [Surface workflow architecture](../architecture/surface-workflow.md)

## Context

Surface generation, parity, and invalidation run existing compiler code over graph content. Letting an AMQP request choose file paths, command strings, Turtle payloads, or which process to execute would create arbitrary execution and data-exfiltration risks. Invalidation also has two different input roles: generated manifest evidence and source graphs.

## Decision

Accept only scoped graph references in Surface jobs. A trusted `GraphMaterializer` resolves authorized immutable references to canonical local bytes. `SurfaceCompilerExecutor` requires the returned path to remain inside its private work directory, requires a regular file, and computes SHA-256 over those canonical bytes before compiler invocation. The calculated digest must equal the graph reference revision hash. `SurfaceCompilerExecutor` constructs one fixed compiler argument vector for each closed job type and returns output digests and safe diagnostics. The request cannot select executable commands or filesystem paths.

Require `manifestGraph` as a separate graph reference for invalidation jobs. It cannot be represented by source-graph ordering. The executor passes it only to the compiler's `--manifest` argument and passes source graphs only to `--sources`.

## Consequences

- Generation always enables determinism and parity checks in the reference executor.
- A materialization path escape, missing file, or digest mismatch stops execution before the compiler receives any input.
- Output RDF remains local to the trusted adapter. Job results expose digests and diagnostics, not generated content.
- AMQP consumers must authenticate the caller upstream, authorize graph scope, and use a materializer that serializes the graph in the same canonical byte form used to derive its revision hash.
- The current executor is a testable adapter boundary. A deployed worker still needs broker consumer lifecycle, graph storage integration, output publication, retry behavior, and end-to-end tests.
