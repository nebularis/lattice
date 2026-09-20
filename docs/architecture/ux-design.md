<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Platform UX Design

Companion to [Platform Solution Design Specification](solution-design-specification.md). Two products sit on the platform: the MORK Review Workbench and the Surface Contract Studio. Their UX design is documented at equivalent depth here. This document bridges design intent to the concrete APIs and data in [data-architecture.md](data-architecture.md), it does not restate either.

## 1. MORK Review Workbench

The canonical design is [MORK UXD](../../mork/docs/MORK%20UXD.md). It is a complete, independently authored thesis on reviewable semantic alignment: the six-verb decision model (Confirm, Retarget, Reshape, Decline, Teach, Defer), the role perimeter table, the yield-ordered queue, the Bench/Atlas/Dossier/Boundary/Ledger/Studio surface set, the anti-pattern catalogue, and the build order. Read it in full before changing the Workbench. This section does not repeat it, it maps it onto the platform built around it.

### 1.1 Role-to-API bridge

| MORK UXD role | Platform principal role claim | API surface | Data source |
|---|---|---|---|
| Domain Steward | `mork_domain_steward` | `MorkAnalysisApi` (role-projected view only) | `mork_review_snapshot` filtered through `project_evidence()` |
| Integration Engineer | `mork_integration_engineer` | `MorkAnalysisApi` (full technical view), Boundary API | `mork_review_snapshot` unfiltered, `governance_ledger_entry` |
| Ontology Owner | `mork_ontology_owner` | Minting and retrospective-challenge API | `ontology-minting-request`, `retrospective-challenge` contracts |
| Pack Maintainer | `mork_pack_maintainer` | Studio API (failure signatures, calibration, cassette corpus) | Aggregated, never individual mapping content, per Part 10 of MORK UXD |

This mapping is the enforcement point the UXD document calls for when it says perimeters must be enforced in the UI, not merely documented. The platform enforces it server-side: `mork_analysis_worker.py`'s `process_mork_analysis` builds the Domain Steward's response from `project_evidence()`, the browser never receives the unfiltered snapshot and redacts it client-side. A client-side filter would be a UX bug masquerading as a security control.

### 1.2 Surface-to-API mapping

| MORK UXD surface | Backing contract | Backing table | Current implementation state |
|---|---|---|---|
| Bench | `review-snapshot.schema.json`, `review-decision.schema.json` | `mork_review_snapshot`, `mork_review_decision` | Fixture-rendered in `apps/mork-review-workbench/src/main.tsx`, one hardcoded snapshot |
| Atlas / queue | `review-queue.schema.json` | Not yet persisted, see [data-architecture.md §7](data-architecture.md#7-open-gaps) | Fixture only |
| Boundary | Governance ledger entries of kind `boundary_obstruction` | `governance_ledger_entry` | Fixture only |
| Ledger | `governance-ledger-entry.schema.json` | `governance_ledger_entry` | Fixture only |
| Studio (Pack Maintainer) | Aggregated failure signatures (no schema yet) | Not yet modelled | Not implemented |
| Dossier | Extension of the Bench's evidence panel, no separate contract | `mork_review_snapshot.evidenceProjection` | Not implemented |

The Workbench's near-term implementation path (see the master specification's process maps) is to replace the fixture with these APIs in the order MORK UXD's own Part 13 build order specifies: Bench first, typed rejections wired end to end second, token ribbon third, Atlas and yield queue fourth.

## 2. Surface Contract Studio

No equivalent design document exists yet for Surface Studio, only its fixture UI and [surface-contract-studio.md](surface-contract-studio.md)'s architecture note. This section is that design, at the depth MORK UXD sets for its own product.

### 2.1 Roles

| Role | Knows | Primary surface | Cannot do |
|---|---|---|---|
| **Author** | The domain contract they are drafting, Promotion/Index/Projection shape | Portfolio, Editor | Approve their own revision, activate a MORK mapping, submit Turtle directly |
| **Reviewer / Approver** | The contract's business intent, organisational approval authority | Editor (review mode), Inspector | Edit contract fields while reviewing, bypass optimistic concurrency |
| **Release Operator** | Release policy, environment topology, external release-stack operation | Release view (new, see §2.4) | See MORK mapping content, alter semantic gate evidence |
| **Technical Inspector** (engineering) | Compiler internals, graph families, MCN staging status | Technical view, Inspector | Change lifecycle state without going through a typed transition |

This mirrors MORK UXD's own principle: perimeters are enforced by what the API returns per role, not by hiding a button while sending full data to the browser.

### 2.2 Information architecture

```text
Portfolio (list, filter by state)
  -> Editor (Promotion | Index | Projection, selected by contract kind)
       -> Path builder / population controls / projection role bindings
       -> Technical view (generated declaration preview, read-only)
  -> Inspector (persistent right rail)
       -> Law checklist
       -> Impact preview (read-set, dependent surfaces)
       -> Generated-output diff
       -> MORK Technical Inspector panel (Projection contracts only)
  -> Release view (new)
       -> Release candidate summary (semantic gate evidence, generated output digest)
       -> Publish action (Release Operator only)
       -> Release ledger history for this contract
```

The Editor, Inspector, and Release view share one persistent selection, the same principle MORK UXD states for its own six linked views: the model is an IDE's active symbol, not a stack of independent pages.

### 2.3 Interaction model

| Interaction | Mechanism | Failure surfaced as |
|---|---|---|
| Save a lifecycle transition | Typed `SurfaceRevisionTransition` command with `expectedVersion`, per [SurfaceRevisionApi](../../platform/surface-workflow/src/main/java/org/nebularis/lattice/surface/SurfaceRevisionApi.java) | `409` rendered as "this revision changed since you loaded it, review the newer version" with a diff of what changed, never a silent overwrite |
| Request generation | Enqueues a `generation` job, returns immediately with a job reference | Studio polls `GET /surface/jobs/{jobId}` and shows a progress state (`pending`, `running`, `succeeded`, `failed`) until resolved |
| View technical declaration | Read-only rendering of the contract graph, never an editable Turtle box | N/A, this is deliberately not an editing surface |
| Attempt to activate a MORK mapping | No such control exists in the Studio UI | The Technical Inspector panel states explicitly: "Mapping activation is governed by the MORK workflow and cannot be requested here," already present in the current fixture and preserved as a hard rule |
| Publish a release | Only available once revision state is `GENERATED` and required semantic gates are attached | Missing gate evidence blocks the publish action with the specific missing gate named, mirroring MORK UXD's "show the axiom that excluded it" principle rather than a generic disabled button |

### 2.4 The Release view (new design, not yet built)

The master specification resolves who calls `release-integration` and where its evidence goes. This section is the corresponding UX: Studio needs a screen, not just an API, or the Release Operator has no way to inspect what the facade decided.

```text
┌─ RELEASE ──────────────────────────────────────────────────────────┐
│ Contract: Subscription currency          Revision r-2026-09-19-001 │
│ State: GENERATED                                                   │
│                                                                     │
│ Semantic gate evidence                                             │
│  ✓ approval        approval-2026-09-19-004                        │
│  ✓ determinism     sha256:9f2c…  (verified by worker)              │
│  ✓ parity          passed, 2026-09-19T10:04Z                       │
│  ✓ impact          3 dependent surfaces, reviewed                  │
│                                                                     │
│ [ Publish release candidate ]     (Release Operator only)          │
│                                                                     │
│ Release ledger                                                     │
│  release-1  PUBLISHED   sha256:3af1…   2026-09-19T10:06Z           │
│  release-1  PLANNED     sha256:3af1…   2026-09-19T10:05Z           │
└──────────────────────────────────────────────────────────────────—┘
```

Design rules for this view:

- It never shows MORK mapping content, even if the release includes a Projection contract, only Surface-facing evidence and digests.
- A missing gate is named specifically ("impact evidence missing," not "cannot publish"), the same evidence-first principle as MORK UXD's checklist metaphor for challenges and witnesses.
- The ledger list is read from `release_ledger_event`, append-only, and is never edited from this screen, it is an audit view.
- The Publish action is the only mutation, and it is exposed to exactly one role.

### 2.5 Anti-patterns to avoid (Studio-specific)

| Anti-pattern | Why tempting | What it costs |
|---|---|---|
| A free-text Turtle box "for power users" | Feels flexible | Bypasses immutable graph-family registration and hash verification, the exact bypass ADR-A34 exists to prevent |
| Showing MORK staging graph IRIs as editable | Looks integrated | Breaks the Surface/MORK activation boundary ADR-A41 establishes |
| Optimistic UI that applies a transition locally before the server confirms it | Feels responsive | Produces a UI that lies about lifecycle state during a `409`, which is worse than a brief wait |
| One generic "processing" spinner for all async jobs | Simple to build | Hides whether a job is queued, running, or has failed and is awaiting retry, exactly the ambiguity MORK UXD warns against for confidence display |
| Silent success on release publish | Minimal UI | Denies the Release Operator the digest they need to hand to the external release stack |

### 2.6 Build order

1. Replace fixture reads with the typed Surface API (portfolio, get, transition) against a real Control Plane.
2. Add job submission and polling for generation, parity, and invalidation, with explicit pending/running/failed states.
3. Add the Release view, gated on real semantic gate evidence from the release ledger.
4. Add the Projection editor's Technical Inspector panel wired to real staging-graph data, preserving the existing "cannot be requested here" rule.
5. Add real-stack Playwright coverage per the continuation plan in [docs/developer/current](../developer/current/README.md).

## 3. Cross-Cutting UX Principles

Both products share these, stated once here rather than in each product's section:

- **Server-enforced role perimeters.** A role never receives data it is not entitled to see, filtered or not, the response is constructed differently per role.
- **Evidence before action.** No approval, generation, release, or decision control is enabled without showing what evidence backs it, and no missing evidence is rendered as a generic disabled state.
- **Optimistic concurrency is visible, not hidden.** A stale-write conflict is shown as a conflict with a diff, never silently retried or silently dropped.
- **Async work has a visible state machine.** Pending, running, succeeded, and failed are distinct, persisted states, not a single spinner.
- **No client-side security.** Every redaction, permission check, and role-scoping rule lives in the Control Plane or worker tier. The browser renders what it is given.
