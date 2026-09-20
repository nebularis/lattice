<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Current Implementation Continuation

Date: 2026-09-20  
Working revision: `b19e1e7192dbb04fca1894f01908e9a11d976a2f`  
Status: paused after the first Surface control-plane implementation slice.

## Purpose

This is the restart point for the next session. It is not a plan document. Design lives in [solution-design-specification.md](../../architecture/solution-design-specification.md), [data-architecture.md](../../architecture/data-architecture.md), and [ux-design.md](../../architecture/ux-design.md). What remains is verification of already-authored work, and that verification's gaps are already documented. This file references them rather than re-deriving them:

- [Implementation handover](../implementation-handover.md), phase-by-phase authoring status, outstanding validation, and the "Do Not Break" invariants.
- [Offline phase handoff procedure](../offline-phase-handoff.md), the rule that authoring complete does not imply validated complete.
- Each phase handoff, [0-1](../phase-0-1-handoff.md), [2](../phase-2-handoff.md), [3](../phase-3-handoff.md), [4](../phase-4-handoff.md), [5](../phase-5-handoff.md), [6](../phase-6-handoff.md), with its own unverified-assumptions statement.

## Working Arrangement

Validation of implemented code follows the [Agentic Development Contract](../../../.github/copilot-instructions.md). Work is validated by the human running the listed commands and reporting the result, not by the agent re-running build and test suites on its own initiative.

## Evidence Recorded This Session

The following checks completed in this network-enabled environment, before the working arrangement above took effect:

| Area | Evidence | Result |
|---|---|---|
| Toolchain | `mise`-managed Java 21, Maven 3.9, Node 22, Python 3.11, Erlang 27, and Elixir 1.17 | Passed |
| Root Python | `python -m unittest tools.surface.test_surface tools.mork_compilers.test_mork_compilers -v` | 76 tests passed |
| Workers | `python -m pytest workers/tests -q` | 38 tests passed |
| Java reactor | `mvn -f platform/pom.xml verify` | Passed |
| Frontend | `yarn check` | Passed |
| Compose | PostgreSQL, RabbitMQ, Fuseki, and workspace services started | Passed |
| PostgreSQL | All five documented migrations applied. Host connection and expected tables verified | Passed |
| RabbitMQ | Host publish and consume smoke message | Passed |
| Fuseki | Base endpoint served. `/$/server` returned `401`, consistent with its protected administration API | Passed |
| Current API slice | `mise exec -- mvn -f platform/pom.xml -pl surface-workflow -am test` | Passed. 9 Surface workflow tests passed |

The service smoke checks prove reachability. They do not prove the intended Java to RabbitMQ to Python worker flow, graph materialization, lifecycle persistence, release flow, or role authorization.

## Worktree Boundary

Do not revert or remove changes outside a slice you are actively working on.

- Present from earlier validation work: `apps/mork-review-workbench/package.json`, `apps/surface-contract-studio/package.json`, `yarn.lock`, `deployment/compose/docker-compose.yml` (publishes PostgreSQL as `5432:5432` for host-driven validation), and the `SemanticReleaseAssemblyServiceTest.java` fix.
- A root [.gitignore](../../../.gitignore) now excludes Node, Yarn, Maven, Python, and Mix build and dependency output repository-wide. 63 previously tracked generated files were removed from the index, not deleted locally.
- Current Surface control-plane slice: [Surface OpenAPI contract](../../../contracts/openapi/surface-workflow.openapi.json), [SurfaceRevisionApi](../../../platform/surface-workflow/src/main/java/org/nebularis/lattice/surface/SurfaceRevisionApi.java), and its test. Framework-neutral, no HTTP listener, no persistence wiring, no identity.
- New architecture documentation: [solution-design-specification.md](../../architecture/solution-design-specification.md), [data-architecture.md](../../architecture/data-architecture.md), [ux-design.md](../../architecture/ux-design.md), and an updated [implementation-map.md](../../architecture/implementation-map.md).

## Verification Gaps

Sourced from the documents in [Purpose](#purpose). This is a pointer table, the documents linked are authoritative, not this summary.

| Phase | Handoff | Remains unverified |
|---|---|---|
| 0-1 | [phase-0-1-handoff.md](../phase-0-1-handoff.md) | Testcontainers integration, PostgreSQL-backed outbox persistence, end-to-end Java-to-RabbitMQ-to-Python retry test |
| 2 | [phase-2-handoff.md](../phase-2-handoff.md) | HTTP endpoint, ledger and graph-family migrations against a live PostgreSQL, Playwright browsers, Studio E2E, Fuseki materialization, RabbitMQ retry/dead-letter/duplicate-delivery behavior |
| 3 | [phase-3-handoff.md](../phase-3-handoff.md) | Maven/Java 21/Docker/ORAS/Cosign execution, registry push, signature verification, PostgreSQL ledger integration, RDF provenance publication, restore against a live registry |
| 4 | [phase-4-handoff.md](../phase-4-handoff.md) | Python/Yarn/Playwright/RabbitMQ/Fuseki/compiler tests, `yarn.lock` regeneration and review |
| 5 | [phase-5-handoff.md](../phase-5-handoff.md) | Python/Yarn/Playwright/RabbitMQ/graph-store integration commands |
| 6 | [phase-6-handoff.md](../phase-6-handoff.md) | Python/Yarn/Playwright/PostgreSQL/RabbitMQ/graph-store integration commands |

The current `SurfaceRevisionApi` slice postdates these handoffs and has only the regression gate below, no HTTP, persistence, or identity validation.

## Commands to Run

Per the Agentic Development Contract, run these yourself and report the result back.

```text
cd /Users/t4/work/lattice
mise exec -- mvn -f platform/pom.xml -pl surface-workflow -am test
```

Pass looks like: `Tests run: 9, Failures: 0, Errors: 0`, including `SurfaceRevisionApiTest`. This is a regression gate for the current slice only, it is not evidence against any row in the table above.

## Reference Material

- [Canonical Phase 0-7 plan](../../../.github/prompts/plan-morkSurfaceImplementation.prompt.md)
- [Implementation handover](../implementation-handover.md), including its "Do Not Break" invariants
- [Validation pause handover](../validation-pause-handover.md)
- [Validation status](../validation-status.md)
- [Platform solution design specification](../../architecture/solution-design-specification.md), [data architecture](../../architecture/data-architecture.md), [UX design](../../architecture/ux-design.md)
- Session plan memory: `/memories/session/plan.md` (session-scoped, not durable)

