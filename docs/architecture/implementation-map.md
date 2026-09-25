<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Implemented Platform Map

This guide maps the implementation introduced by Phases 0 through 3. It is an orientation document for maintainers and coding agents. It does not replace normative ontology documentation in layer READMEs or decision rationale in ADRs.

Read [solution-design-specification.md](solution-design-specification.md) first for the platform's process, component, data, infrastructure, and robustness design. This map is a source-file index into that design, not a substitute for it.

| Area | Primary implementation | Contracts and guides | Current state |
|---|---|---|---|
| Repository orchestration | `mise.toml`, `.devcontainer/`, `deployment/compose/` | [toolchain](../developer/toolchain.md), [ADR-A29](decisions/ADR-A29-repository-toolchain-and-environment-boundary.md) | Authoring complete, runtime validation pending |
| Semantic platform | `platform/semantic-dataset-*`, `semantic-policy`, `platform-outbox`, `workers/graph_validation.py` | `contracts/events/graph-validation-*.schema.json`, [semantic platform](semantic-platform.md), [ADR-A30](decisions/ADR-A30-shared-semantic-platform-cross-runtime-boundary.md) | Authoring complete, persistence and integration validation pending |
| Surface workflow | `platform/surface-workflow`, `workers/surface_jobs.py` | `contracts/surface/`, `contracts/events/surface-job-*.schema.json`, [Surface workflow](surface-workflow.md), [ADR-A32](decisions/ADR-A32-surface-revision-lifecycle-and-release-candidates.md) | In progress |
| Surface authoring UI | `apps/surface-contract-studio` | [Surface Contract Studio](surface-contract-studio.md), `contracts/openapi/surface-workflow.openapi.json`, [ADR-A38](decisions/ADR-A38-surface-output-publication-and-studio-authoring-boundary.md) | Fixture-backed, awaiting HTTP adapter validation |
| Design-time reasoning checks | `platform/reasoning-testkit` (test-only), `tools/mork_compilers` OWL backend | [ADR-A83](decisions/ADR-A83-test-only-reasoning-engine-isolation.md), [ADR-A90](decisions/ADR-A90-eligibility-design-time-owl-class-backend.md) | Implemented, awaiting human validation |
| Release integration | `platform/release-integration` | `contracts/release/`, [release integration](release-stack-integration.md), [ADR-A31](decisions/ADR-A31-release-stack-neutral-integration-contract.md) | In progress |

## Dependency Direction

```text
Surface compiler and ontology assets
        ^
trusted graph resolver and worker adapter
        ^
Surface workflow control contract --> Release integration contract --> external release stack
        ^                                      ^
semantic dataset SPI, policy, outbox, and event schemas
```

The compiler and ontology assets retain semantic ownership. The new Java modules coordinate immutable references and operational lifecycle. Workers receive references, resolve them through trusted infrastructure, and call existing semantic code. External release stacks receive release intent and return receipts. None of these layers may use a browser or broker payload to establish graph authority.

## Reading Order

1. Read [ADR-A29](decisions/ADR-A29-repository-toolchain-and-environment-boundary.md) for environment and task ownership.
2. Read [semantic platform](semantic-platform.md) and [ADR-A30](decisions/ADR-A30-shared-semantic-platform-cross-runtime-boundary.md) for graph and transport boundaries.
3. Read [Surface workflow](surface-workflow.md) and [ADR-A32](decisions/ADR-A32-surface-revision-lifecycle-and-release-candidates.md) before changing Surface lifecycle code or worker messages.
4. Read [release integration](release-stack-integration.md) and [ADR-A31](decisions/ADR-A31-release-stack-neutral-integration-contract.md) before implementing registry, GitOps, CI, or signing adapters.

## Validation State

The repository's current authoring environment lacks Java 21, Maven, and a usable Python interpreter. JSON parsing, static diagnostics, and whitespace checks have run where available. Read each phase handoff before treating a component as validated.
