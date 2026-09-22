<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Phase 2 — Ingestion and Query Planes (Plan)

**Unit type:** Phase
**Epic:** `lattice-platform-development` ([lattice-platform-agentic-development-v0.2.md](lattice-platform-agentic-development-v0.2.md))
**Unit ID:** `phase-2`
**Status:** Rolling-wave placeholder — see [phase-2-status.md](../status/phase-2-status.md)
**Sketch:** [phase-2-sketch.md](../sketches/phase-2-sketch.md)
**Depends on:** Phase 1 exit gate
**Full VP-level expansion scheduled at:** P1.11.3 (Phase 1's own close-out slice), per the epic's stated rolling-wave methodology (Part 0.5)

## 1. Scope

Data gets in, questions get answered, lineage is provable. **Milestones M4 (ingestion), M5 (query + lineage), M6 (content pipeline).**

**Authoritative slice-level detail** (lighter than Phase 0/1 by the epic's own design, expanded further at P1.11.3): [epic Part 6](lattice-platform-agentic-development-v0.2.md#part-6--phase-2-ingestion-and-query-planes). The persistence-compiler integration across P2.1/P2.3/P2.4 is already fully specified there (see the Part 6 preamble) and is not repeated here.

This plan intentionally does **not** contain a full test-case enumeration or a finished module-by-module README/doc table the way Phase 0/1's plans do — producing one now would contradict the epic's explicit reasoning for deferring Phase 2 detail until Phase 1's store-SPI learnings land. What follows is scoped to what is already concretely decided.

## 2. Documentation obligations — `docs/architecture` (known now)

| Document | Change | Producing slice |
|---|---|---|
| `docs/architecture/rdf-sparql-patterns-guide.md` | No change expected — Phase 2 consumes it, does not extend it, unless P2.1.4a's implementation surfaces a guide gap the way Slice 2 of `rdf-sparql-patterns-phase` did | P2.1.4a |
| `ontology/persistence/docs/platform-vocabulary-alignment.md` | Consumed, not produced, here (produced in Phase 0 per P0.3.9) | — |
| Anything P1.11.3 names as a new doc obligation for Phase 2 | Deferred | P1.11.3 |

## 3. README obligations (known now)

| New subproject | Track | Note |
|---|---|---|
| `workers/mapping_plan_compiler` | C-05 | Python, design-time only, per P2.1 |
| `platform/plan-ir` | shared IR boundary | C-04/C-05 boundary |
| `platform/reasoning-validation` | C-13 | P2.2 |
| `platform/ingestion-gateway` | C-04 | |
| `platform/query-plane` | C-12 | |
| `platform/lineage` | C-19 | |
| `platform/metering` | C-16 | |
| `platform/push-gateway` | C-18 | |
| `platform/feedback-router` | C-15 | |
| `workers/content_pipeline` | C-06 | |
| `workers/agent_orchestrator` | C-14 | Build before C-06 per the epic's explicit ordering note |
| `clients/client-java`, `clients/client-python` | Generated SDKs | P2.10.6 |

Full README content (beyond "one exists") is written when each module's first slice lands, per copilot-instructions.

## 4. `solution-design-specification.md` delta plan (known now)

| SDS section | Change | Note |
|---|---|---|
| §1 Technical Capability Catalogue | Add ingestion, query/decision, lineage, metering, push, feedback-router capabilities | Full rows written when P1.11.3 expands this phase |
| §3 Data Architecture Summary | Add `INGEST_STAGING` graph family and the staging-never-queried rule | P2.3.4 |
| §4.1 Component Inventory | Add every module in §3 above | Per introducing slice |
| §7 Robustness Design | Add the write-back loop cap and poison-stimulus policy once those land (Phase 3, not this phase — noted here only so the eventual Phase 2 close-out slice does not claim them) | N/A — cross-phase note |

A full delta table, matching Phase 0/1's depth, is produced at P1.11.3 alongside the slice expansion.

## 5. Phase gate checklist

Standard per [epic Part 12](lattice-platform-agentic-development-v0.2.md#part-12--phase-gate-checklists), applied once slices exist to gate.

## 6. Dependencies

Depends on Phase 1 exit gate. Blocks Phase 3 (C-07/C-09 need C-04's ingestion path and C-12/C-19 for query/lineage).
