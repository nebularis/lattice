<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Phase 4 — Maturity (Plan)

**Unit type:** Phase
**Epic:** `lattice-platform-development` ([lattice-platform-agentic-development-v0.2.md](lattice-platform-agentic-development-v0.2.md))
**Unit ID:** `phase-4`
**Status:** Placeholder — sub-programmes sized after Phase 3 measurement, see [phase-4-status.md](../status/phase-4-status.md)
**Sketch:** [phase-4-sketch.md](../sketches/phase-4-sketch.md)
**Depends on:** Phase 3 exit gate (specifically P3.6.1–P3.6.3's benchmark, load, and cost-model outputs)
**Full expansion scheduled at:** P3.6.4

## 1. Scope

Agent orchestration full, drift analytics, a second store adapter (GraphDB or chosen commercial store), an RDF4J embedded adapter, optional SPC integration, commercial packaging, and an explicit non-goal (multi-region). Sub-programmes, not slices — see [epic Part 8](lattice-platform-agentic-development-v0.2.md#part-8--phase-4-maturity).

## 2. Documentation obligations — `docs/architecture` (known now)

| Document | Change |
|---|---|
| New store adapter's capability report | Per P4.3, "admission by TCK, never by assertion" — the report is the artefact, produced the same way Phase 0's TDB2/Fuseki reports were |
| SPC namespace/session-type lift documentation, if P4.5 is adopted | Conditional — the epic itself gates this on whether Phase 1–3's state machines were documented in the uniform shape P4.5 needs, audited at the P3 gate |

## 3. README obligations

New subprojects are named by whichever sub-programme is eventually staffed (e.g. a second adapter module under `platform/`, a sample external adapter repo for P4.6's zero-patch proof). Not enumerable yet.

## 4. `solution-design-specification.md` delta plan

Deferred to P3.6.4, when Phase 3's actual measurements exist to size this phase's sub-programmes against.

## 5. Phase gate checklist

Not applicable in the epic's standard form — Phase 4 is sub-programmes, several explicitly conditional. Each sub-programme, once staffed, follows the standard slice/VP model per copilot-instructions.

## 6. Dependencies

Depends on Phase 3 exit gate. Terminal phase in the epic's DAG (no phase depends on Phase 4).
