<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# ADR-A50: Role-Profiled Deployment

**Status:** Proposed
**Date:** 2026-09-23
**Related:** Architecture Review §2.1 (G-23), ADR-A81, `solution-design-specification.md` §4.2
**Drafted by:** Agent, autonomous session (P0.1.10). Pending human ratification — see [phase-0-status.md](../../developer/status/phase-0-status.md).

## Context

Runtime ingestion traffic (thousands of payloads/minute, latency-sensitive) and authoring/review traffic (dozens of requests/minute, latency-tolerant) currently share the same deployment unit, thread pool, and deploy cadence. This prevents independent scaling and puts authoring changes on the same blast radius as ingestion load.

## Decision

Single codebase, deployed as role-profiled processes selected by a `LATTICE_ROLE` environment setting:

- **`control`** — authoring, review, release, governance, deployment.
- **`edge`** — ingestion, query, subscriptions.
- **`projection`** and **`behaviour`** — reserved role profiles for the projection and behaviour planes, mounted independently once those planes exist (Phase 1+).

Each role profile mounts only its own routes (asserted per role at startup). Identity, policy, and outbox wiring (`solution-design-specification.md` §4.2) remain a single composition root shared by every role, so there is no duplicated wiring — only independent scaling, independent deploy cadence, and blast-radius separation.

## Consequences

- `platform/runtime-host` (P0.7.3) is the shared skeleton every role profile mounts onto.
- The Compose reference stack (`deployment/compose`) gains one service per role profile, sharing one image (P0.7.6).
- A test asserts that each role profile mounts only its own routes.
- This ADR names the roles; ADR-A81 defines the HTTP runtime mechanics (virtual threads, deadlines) shared by every role.
