<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Governance Surfaces Integration Plan

**Unit:** `governance-surfaces-integration`
**Status:** Planning phase
**Relates to:** Phase 2 (Surface control plane), Phase 5 (MORK review)
**Sketches:** [governance-and-versioning-migration.md](../sketches/governance-and-versioning-migration.md)
**Architecture:** [Surface workflow](../../architecture/surface-workflow.md), [MORK review workbench](../../architecture/mork-review-workbench.md)

## Purpose

Transform fixture-backed UI shells ([Surface Contract Studio](../../../apps/surface-contract-studio), [MORK Review Workbench](../../../apps/mork-review-workbench)) into production governance surfaces connected to control-plane APIs, ledger persistence, and role-based permission enforcement.

## Current State

- **Surface Contract Studio:** renders 4 fixture contracts; no backend connection
- **MORK Review Workbench:** renders 1 fixture snapshot with static evidence; no decision persistence or permission model
- **Design:** [governance-and-versioning-migration.md](../sketches/governance-and-versioning-migration.md) specifies four roles with distinct perimeters and access rules
- **APIs:** [Surface revision API](../../../contracts/openapi/surface-workflow.openapi.json) and [MORK review contracts](../../../contracts/mork/) exist

## Scope: Three Slices

### S1. Surface Contract Studio Backend Integration (Phase 2)

**Goal:** Studio connects to Surface control plane and displays real contracts from ledger

- Fetch contract list via SurfaceRevisionApi `/contracts` endpoint
- Display contract state transitions per [ADR-A32](../../architecture/decisions/ADR-A32-surface-revision-lifecycle-and-release-candidates.md)
- Implement contract detail pane: fetch by ID, render diff against previous revision
- Wire save action to revision approval workflow
- Tests: contract list fetch, state machine validation, diff correctness

**Deliverables:**
- Modified [studio.tsx](../../../apps/surface-contract-studio/src/studio.tsx) with real API calls
- Updated [Studio E2E tests](../../../apps/surface-contract-studio/e2e/studio.spec.ts) with live API fixtures
- Documentation: [Surface Contract Studio](../../architecture/surface-contract-studio.md)

### S2. MORK Review Bench Permission Model (Phase 5)

**Goal:** Enforce role-based visibility and decision constraints

- Implement `DomainSteward`, `IntegrationEngineer`, `OntologyOwner`, `PackMaintainer` role checks
- Render content visibility per [governance-and-versioning-migration.md Part 2](../sketches/governance-and-versioning-migration.md#part-2-who-is-at-the-keyboard) permissions table
- Hide/disable decisions based on role (Steward can Confirm/Retarget/Decline/Teach/Defer; cannot Reshape)
- Tests: each role with positive and negative decision tests

**Deliverables:**
- Permission model in [workbench.tsx](../../../apps/mork-review-workbench/src/main.tsx)
- Updated E2E tests with role-scoped fixtures
- Documentation delta in [MORK Review Workbench](../../architecture/mork-review-workbench.md)

### S3. Evidence Projection and Snapshot State (Phase 5)

**Goal:** Display real evidence projections and persist decisions

- Fetch review snapshot by ID from ledger per [ADR-A42](../../architecture/decisions/ADR-A42-mork-review-snapshot-and-decision-learning-boundary.md)
- Project evidence per role: Steward receives only safe evidence (witness/coverage); Engineer sees MCN; Maintainer sees failure signatures
- Wire decision buttons to review-decision POST endpoint
- Implement optimistic concurrency: stale-snapshot detection and conflict handling
- Tests: snapshot fetch, evidence projection per role, decision recording, stale-snapshot rejection

**Deliverables:**
- Modified workbench component with live snapshot wiring
- Evidence projection module (new file)
- Updated E2E and contract tests
- Documentation: role-safe evidence projection rules

## Testing Strategy

| Level | Description | Ownership |
|---|---|---|
| **L1** | Unit: permission checks, evidence filter functions | both apps |
| **L3** | Contract: Surface revision API roundtrip, review decision schema conformance | both apps, use existing contract fixtures |
| **L4** | Component integration: Playwright against seeded ledger (Testcontainers PostgreSQL) | Phase 2 and Phase 5 gates |
| **L5** | System E2E: full workflow (author → approve → generate / snapshot → decide → record) via compose stack | Phase 2 and Phase 5 gates |

## Acceptance Criteria

- All three slices pass their test levels
- Studio displays real contracts and tracks state correctly
- Bench enforces all role constraints and projects evidence safely
- Decisions persist to ledger without data loss or race conditions
- Playwright E2E covers full workflows for each role

## Risks and Mitigations

| Risk | Mitigation |
|---|---|
| Ledger migration not deployed | Explicitly gate this work on database migration in Phase 2 validation |
| API contract changes during integration | Use exact version of surface-workflow.openapi.json at slice start; review changes explicitly |
| Race conditions in concurrent decision recording | Implement optimistic concurrency per [ADR-A33](../../architecture/decisions/ADR-A33-surface-revision-ledger-and-optimistic-concurrency.md) |
| Permission model too complex to test | Create a small fixture corpus of role×action×expected pairs; test as a matrix, not prose |

## Success Metrics

- 100% test pass rate (L1–L5)
- Zero unhandled API errors or permission bypasses in E2E
- All four roles can complete their workflows end-to-end
- No stale-snapshot conflicts in recorded decisions

## Timeline

- **S1:** Phase 2, after revision ledger migration (NG)
- **S2:** Phase 5, gated on role-safe evidence projection design (2–3 slices)
- **S3:** Phase 5, after S2 (1–2 slices)
