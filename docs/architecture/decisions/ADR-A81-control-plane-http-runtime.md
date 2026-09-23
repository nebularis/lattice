<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# ADR-A81: Control Plane HTTP Runtime

**Status:** Proposed
**Date:** 2026-09-23
**Related:** Architecture Review §2.1 (G-22), ADR-A50, `solution-design-specification.md` §4.2
**Note on numbering:** The epic plan (`lattice-platform-agentic-development-v0.2.md`, P0.1.10) refers to this decision as "ADR-A44 amended." The existing [ADR-A44](ADR-A44-mork-teaching-pack-generated-content-boundary.md) is an accepted, unrelated decision (MORK Teaching Pack generated-content boundary). To avoid corrupting that decision, this content is recorded as a new ADR at the next free number (A81; A77–A80 already exist) rather than as an amendment to A44. This renumbering is itself a decision made without human confirmation in this autonomous session — flag for review.
**Drafted by:** Agent, autonomous session (P0.1.10). Pending human ratification — see [phase-0-status.md](../../developer/status/phase-0-status.md).

## Context

`solution-design-specification.md` §4.2 describes "a minimal HTTP runtime (a single well-chosen library)" without deciding the concurrency model, deadline propagation, or codec. G-22 names this as underdetermined.

## Decision

1. **Virtual threads, not reactive.** Java virtual-thread-per-request (final since Java 21; the repository runs Java 25) on a minimal HTTP server (Helidon SE / Javalin / Undertow class — a library, not a framework). Domain logic is blocking and synchronous by design; reactive style is explicitly rejected.
2. **Mandatory deadline propagation.** Every request carries a `Deadline`, propagated into every downstream call through the call context. A request with an expired deadline is refused before execution, not executed and then abandoned.
3. **JSON codec.** Jackson at the edge only. Wire types are generated from `contracts/**/*.schema.json` (G3); JSON Schema validation runs at the edge before domain code sees a payload.
4. **Control plane and data plane are the same process**, separated by role profile (ADR-A50), not by separate services.

## Consequences

- `platform/runtime-host` (P0.7.3) implements this skeleton: minimal HTTP server, virtual-thread-per-request, `LATTICE_ROLE` router mounting, Jackson at the edge only, JSON Schema validation from `contracts/`, `Deadline` propagated to every downstream call, `/healthz` and `/readyz`.
- A test asserts a request with an expired deadline is refused downstream, not executed.
- No domain component constructs its own HTTP client or server outside this shared runtime.
