<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Governance Review Surfaces (MORK Bench and Surface Studio) Implementation Status

**Unit:** `governance-surfaces`
**State:** Skeleton UIs implemented, fixture-backed, pending backend integration
**Sketches:**
- [governance-and-versioning-migration.md](../sketches/governance-and-versioning-migration.md) — UX design and role model
- Related Phase 2 and Phase 5 handoffs for backend integration

**Governing ADRs:** [ADR-A38](../../architecture/decisions/ADR-A38-surface-output-publication-and-studio-authoring-boundary.md), [ADR-A42](../../architecture/decisions/ADR-A42-mork-review-snapshot-and-decision-learning-boundary.md)

## What was built

Two fixture-backed UI shells that demonstrate the governance surface designs without backend integration:

### Surface Contract Studio
- **Location:** [apps/surface-contract-studio/src/studio.tsx](../../../apps/surface-contract-studio/src/studio.tsx)
- **Implements:** Surface Promotion/Index/Projection contract authoring and review
- **UI components:** Contract portfolio, lifecycle state display, contract diff viewer, Technical Inspector
- **Fixture data:** 4 sample contracts showing state transitions and change impacts
- **Design alignment:** Matches [ADR-A38](../../architecture/decisions/ADR-A38-surface-output-publication-and-studio-authoring-boundary.md) authoring boundary

### MORK Review Workbench
- **Location:** [apps/mork-review-workbench/src/main.tsx](../../../apps/mork-review-workbench/src/main.tsx)
- **Implements:** The six MORK review decisions (Confirm, Retarget, Reshape, Decline, Teach, Defer) per [ADR-A42](../../architecture/decisions/ADR-A42-mork-review-snapshot-and-decision-learning-boundary.md)
- **UI components:** Review snapshot display, evidence ribbon (Witness/Coverage/Alternative), decision buttons, calibration state, boundary workflow sidebar
- **Fixture data:** ARR derivation example snapshot with structured evidence
- **Role modeling:** Tenant/project scoping shown; role-restricted evidence projections demonstrated

### Design Sketch Coverage

[governance-and-versioning-migration.md](../sketches/governance-and-versioning-migration.md) specifies:

| Design element | Implemented | Status |
|---|---|---|
| Thesis: MORK is substrate, not interface | Yes | Both UIs hide MORK graph, show domain claims |
| Four roles with separate perimeters | Partially | Studio shown for Surface author; Bench shown for Domain Steward; perimeter enforcement incomplete |
| Six review decisions (Confirm/Retarget/Reshape/Decline/Teach/Defer) | Yes | All six buttons present in Bench |
| Section as unit of judgement | Yes | Bench shows sections in queue sidebar |
| Token ribbon evidence display | Partially | Evidence displayed (Witness/Coverage/Alternative); token granularity not yet shown |
| MCN source affordance (`View source`) | No | Not yet implemented |
| Role-restricted content (no pack internals, teaching, syntax for Steward) | Partially | Fixture demonstrates restriction; not enforced in live integration |

## Gaps and Constraints

- **Backend integration:** Both UIs are fixture-backed and do not connect to Platform control plane or graph stores
- **Permission enforcement:** Role-based visibility rules demonstrated but not enforced in code
- **Evidence projection:** Evidence shown as static fixtures; not actually projected from review snapshots
- **State persistence:** No ledger integration or real lifecycle state management
- **E2E flows:** Playwright tests exist but only validate UI rendering, not workflow

## Evidence

- **Build:** `yarn check` and `yarn build` pass for both applications
- **Tests:** Playwright E2E specs exist ([surface-contract-studio/e2e/studio.spec.ts](../../../apps/surface-contract-studio/e2e/studio.spec.ts), [mork-review-workbench/e2e/bench.spec.ts](../../../apps/mork-review-workbench/e2e/bench.spec.ts))
- **Repository integration:** Both apps use Vite + React, follow [ADR-A29](../../architecture/decisions/ADR-A29-repository-toolchain-and-environment-boundary.md) (root `package.json` with Yarn workspaces)

## Next Phase Work (Phase 2 and Phase 5 handoffs)

To move from skeleton to integrated surfaces:

1. **Backend wiring** (Phase 2): Connect Studio to [Surface revision API](../../../contracts/openapi/surface-workflow.openapi.json); connect Bench to [review snapshot schema](../../../contracts/mork/review-snapshot.schema.json)
2. **Permission model** (Phase 2, Phase 5): Enforce role-based visibility for Steward/Engineer/Owner/Maintainer roles
3. **Evidence projection** (Phase 5): Implement dynamic evidence projection per [ADR-A42](../../architecture/decisions/ADR-A42-mork-review-snapshot-and-decision-learning-boundary.md)
4. **State management** (Phase 2, Phase 5): Wire lifecycle state machine and decision persistence to ledger
5. **Token ribbon rendering** (Phase 5+): Detailed MCN token-level evidence display for Teaching pack integration

## Acceptance

The design sketch is well understood and the UI shells correctly demonstrate its intent. Skeleton implementation is complete. Full acceptance requires backend integration work in Phase 2 and Phase 5 validation gates.

## Deferred (out of scope for skeleton phase)

- Atlas, Boundary, and Coverage surfaces (mentioned in sketch Part 2 but not implemented)
- Pack Maintainer surface and aggregated failure signatures
- LLM teaching pack integration with Workbench prompts
- Live ledger and permission enforcement
