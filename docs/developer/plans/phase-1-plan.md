<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Phase 1 — Graph-Primary Core and the Deployment Plane (Plan)

**Unit type:** Phase
**Epic:** `lattice-platform-development` ([lattice-platform-agentic-development-v0.2.md](lattice-platform-agentic-development-v0.2.md))
**Unit ID:** `phase-1`
**Status:** Not started — see [phase-1-status.md](../status/phase-1-status.md)
**Sketch:** [phase-1-sketch.md](../sketches/phase-1-sketch.md)
**Depends on:** Phase 0 exit gate (hard)
**New ADR required for this plan itself:** No.

## 1. Scope

Migrate Surface lifecycle, the release ledger, MORK review snapshots, and the governance ledger into the graph (T-GPM); stand up tenancy, the change feed, the pack builder/registry, and the activation controller (T-DEP); deliver Operations UX v1. **Milestones M2 (graph-primary lifecycle), M3 (pack + activation).**

**Authoritative slice-level detail** (P1.1 through P1.11): [epic Part 5](lattice-platform-agentic-development-v0.2.md#part-5--phase-1-graph-primary-core-and-the-deployment-plane).

## 2. Documentation obligations — `docs/architecture`

| Document | Change | Producing slice |
|---|---|---|
| `docs/architecture/data-architecture.md` | JDBC ledger removal recorded; relational system-of-record path formally closed | P1.1.4 |
| `docs/architecture/solution-design-specification.md` | §1, §2.2, §4.1, §4.5, §4.6, §7.2 — already named explicitly by the epic itself (P1.11.1); see §4 of this plan for the full delta table | P1.11.1 |
| `docs/architecture/ux-design.md` | Register model (expert/operational/task) documented (G-18) | P1.10.4 |
| SPI inventory + TCK coverage + OSS/commercial boundary doc | New. Epic (P1.11.2) does not name a path — proposed: `docs/architecture/spi-inventory.md`, consistent with every other cross-cutting platform document living under `docs/architecture/`. **Confirm placement before P1.11.2 starts** | P1.11.2 |

## 3. README obligations

| New subproject | Introducing slice | Note |
|---|---|---|
| `platform/mork-review` | P1.5.1 | Graph-resident snapshots + decision nodes |
| `platform/governance-ledger` | P1.6.1 | Hash-chained graph ledger |
| `platform/tenancy` | P1.7.1 | C-17 |
| `platform/pack-builder` | P1.8.1 | C-01 |
| `platform/activation-controller` | P1.9.1 | C-02 |
| `platform/change-feed` | P1.3.1 | C-08 |
| `packages/ui-kit` | P1.10.1 | `@lattice/ui-kit`, Storybook + axe in CI |
| `packages/client-ts` | P1.10.2 | Generated from OpenAPI |

Existing modules whose README needs a **significant-change update**, not a new README: `surface-workflow` (re-based graph-primary, P1.1–P1.2), `release-integration` (ledger → graph, P1.4).

## 4. `solution-design-specification.md` delta plan

P1.11.1 already names the sections; this table adds the specific change and cross-references this plan's other obligations so the close-out slice is not the first time anyone thinks about what goes in each section.

| SDS section | Change | Cross-reference |
|---|---|---|
| §1 Technical Capability Catalogue | Rows for Surface lifecycle governance, release ledger, MORK review, governance ledger move from "Domain logic implemented, no durable persistence wired" (their current maturity note) to graph-backed and wired; add rows for tenancy, packs, activation | — |
| §2.2 Sync/Async Boundary Rule | Add the activation state machine's phases (VALIDATING/PREPARING/SHADOW/PROMOTING) to the sync/async table — SHADOW and PROMOTING have real async/quorum semantics not covered by the existing table's binary split | P1.9.6, P1.9.7 |
| §4.1 Component Inventory | Add `mork-review`, `governance-ledger`, `tenancy`, `pack-builder`, `activation-controller`, `change-feed`, `ui-kit`, `client-ts` per §3 above | — |
| §4.5 RabbitMQ Topology | Add the change-feed's consumer library semantics (cursor, at-least-once, idempotency) as a named topology consumer, distinct from the job-family table Phase 0 already extended | P1.3.4 |
| §4.6 Failure Modes | Add activation-saga reaper, provisioning-saga reaper, and the four T1–T12 failure modes P1.3.3's audit-reconciliation job is built to catch | P1.7.2, P1.9.9 |
| §7.2 Consistency Mechanisms | Add "structural uniqueness via content-addressed revision IRIs" (replaces the JDBC conflict-rejection row once P1.2.2 lands) | P1.2.2 |
| §8 ADR Backlog | Remove or mark disposed any SDS candidate ADR that Phase 1's actual ADRs (drawn from the epic's A50+ range) supersede | Phase 1 close-out |
| §9 Traceability Matrix | Add rows for every Phase 1 capability | P1.11.1 |

## 5. Phase gate checklist

Per [epic Part 12](lattice-platform-agentic-development-v0.2.md#part-12--phase-gate-checklists):

1. All Phase 1 slice gates signed off in `docs/developer/validation/LOG.md`.
2. M2 and M3 demoed by a human against a freshly built compose stack.
3. `docs/traceability/matrix.csv` — zero claimed-but-untested requirements for Phase 1's set.
4. Every Phase 1 ADR ratified; every row in §4 above merged.
5. L7 baselines recorded.
6. L8 suites green (P1.5.3 role-restricted evidence, P1.7.5 credential scoping).
7. **Non-weakening audit**: explicit diff against Phase 0's test inventory, required at P1.2.2 (deletes the old conflict-rejection path) as well as at phase close.
8. Cold-start test.

## 6. Dependencies

Depends on Phase 0's exit gate. Blocks Phase 2 (P2.1's mapping plan compiler needs the store SPI and coordination realm Phase 0 built, and the pack/activation machinery Phase 1 built).
