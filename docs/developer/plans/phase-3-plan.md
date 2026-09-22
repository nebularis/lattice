<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Phase 3 — Operation Plane (Plan)

**Unit type:** Phase
**Epic:** `lattice-platform-development` ([lattice-platform-agentic-development-v0.2.md](lattice-platform-agentic-development-v0.2.md))
**Unit ID:** `phase-3`
**Status:** Rolling-wave placeholder — see [phase-3-status.md](../status/phase-3-status.md)
**Sketch:** [phase-3-sketch.md](../sketches/phase-3-sketch.md)
**Depends on:** Phase 2 exit gate
**Full VP-level expansion scheduled at:** P2.11.4

## 1. Scope

Projections stay fresh, tanks respond, values flow back. **Milestones M7 (projections live), M8 (tanks respond), M9 (write-back).**

**Authoritative slice-level detail:** [epic Part 7](lattice-platform-agentic-development-v0.2.md#part-7--phase-3-operation-plane). **Hard gate restated from the epic:** no C-09 slice starts until C-07 reconciliation (P3.1.7) is green for a full week of nightly runs, injected-divergence scenario included.

## 2. Documentation obligations — `docs/architecture` (known now)

| Document | Change | Producing slice |
|---|---|---|
| `docs/architecture/data-architecture.md` | Add valid-time cold partitioning and archive dataset conventions | P3.5.5 |
| Runbook: restore-from-backup / restore-from-bundle | New — place under `docs/operator/` (existing home for operational runbooks, e.g. `release-stack-reference.md`), not a new top-level `docs/runbooks/` | P3.5.3 |
| Full doc table | Deferred | P2.11.4 |

## 3. README obligations (known now)

| New subproject | Track |
|---|---|
| `platform/projection-engine` | C-07 |
| `platform/behaviour-engine` | C-09 |
| `platform/writeback` | C-10 |

## 4. `solution-design-specification.md` delta plan (known now)

| SDS section | Change | Note |
|---|---|---|
| §7 Robustness Design | Add projection freshness contracts, aggregate lease/fencing, write-back conflict handling (never last-write-wins) | Full table at P2.11.4 |
| §5.1 Deployment Topology | Add role-profiled HA posture (≥2 control, ≥3 edge, partitioned behaviour with failover) | P3.5.1 |

## 5. Phase gate checklist

Standard per [epic Part 12](lattice-platform-agentic-development-v0.2.md#part-12--phase-gate-checklists).

## 6. Dependencies

Depends on Phase 2 exit gate. Blocks Phase 4 (maturity work measures against this phase's benchmarks, per P3.6.1–P3.6.3).
