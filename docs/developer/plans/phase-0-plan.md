<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Phase 0 — Decisions and Non-Retrofittable Foundations (Plan)

**Unit type:** Phase
**Epic:** `lattice-platform-development` ([lattice-platform-agentic-development-v0.2.md](lattice-platform-agentic-development-v0.2.md))
**Unit ID:** `phase-0`
**Status:** Not started — see [phase-0-status.md](../status/phase-0-status.md)
**Sketch:** [phase-0-sketch.md](../sketches/phase-0-sketch.md)
**New ADR required for this plan itself:** No. Phase 0's job is to *ratify* the ADRs the epic already names (A44 amended, A50, A51, A54, A57, A59, A62, A63, A65–A69, A71, A74–A76). Decomposition adds no new decision.

## 1. Scope

Ratify every irreversible decision (A51, A54, A63, A65, A67, A68, A74, plus the rest of P0.1), stand up build/CI/codegen, the platform ontology, canonicalisation, the graph store SPI (Core + TCK + adapters), the coordination realm, identity/policy/HTTP host, messaging foundations, and synthetic data — while proving the whole chain end to end on a volatile stack (**M0**) and producing a signed capability/benchmark report (**M1**).

**Authoritative slice-level detail** (scope, tests, hard orderings per slice, P0.1 through P0.10): [epic Part 4](lattice-platform-agentic-development-v0.2.md#part-4--phase-0-decisions-and-non-retrofittable-foundations). This plan does not reproduce those ~90 rows; it adds the phase-level obligations the epic states exist but does not tabulate: `docs/architecture` deliverables, subproject READMEs, and the `solution-design-specification.md` delta.

**Phase exit gate (hard, restated from the epic):** all Phase 0 ADRs ratified; M0 and M1 pass; `docs/traceability/matrix.csv` has zero untested claimed requirements; `data-architecture.md` rewritten for A74 and signed off.

## 2. Pre-execution decision points (resolve before the named slice starts)

| Slice blocked | Question | Options | Owner |
|---|---|---|---|
| P0.5.1 | `platform/graph-spi` relationship to existing `platform/semantic-dataset-spi`/`semantic-dataset-fuseki` | (a) rename in place, (b) new modules replace the old ones with a deletion slice, (c) coexist during a stated migration window | Human, before P0.5 starts |
| P1.10 (Phase 1, flagged here because it is cheap to resolve now) | `apps/surface-studio`/`apps/mork-bench` vs existing `apps/surface-contract-studio`/`apps/mork-review-workbench` | (a) rename, (b) epic's Part 1 names are informal shorthand for the existing apps, no action needed | Human |

## 3. Documentation obligations — `docs/architecture`

Every row is a slice-level deliverable already named in the epic; this table exists so a phase-0 executor has one place to check off doc debt instead of re-reading all ten P0.x tables.

| Document | New or amended | Producing slice(s) |
|---|---|---|
| `docs/architecture/data-architecture.md` | Amended (§1–3, §5–7 rewritten for A74) | P0.1.1, closed out at P1.1.4 |
| `docs/architecture/iri-policy.md` | New | P0.1.3 |
| `docs/architecture/nfr.md` + `nfr.yaml` | New | P0.1.15 |
| Threat model document (owner + control per S-1…S-12) | New — place under `docs/architecture/` alongside the other normative specs (no existing home named; confirm during P0.1.14, do not invent a new top-level `docs/` root) | P0.1.14 |
| `docs/architecture/decisions/ADR-A44-*.md` | Amended, not replaced (virtual threads, minimal server, deadline propagation, role-profiled deployment) | P0.1.10 |
| `docs/architecture/decisions/ADR-A50` through `ADR-A76` (per the epic's per-slice ADR list in P0.1) | New | P0.1.1–P0.1.13, P0.2.1 |
| `docs/architecture/ontology-architecture.md` | Amended — new `platform/` layer entry, `fnd:GovernanceState` mapping table | P0.3.1, P0.3.3, P0.3.4 |
| `ontology/platform/` literate spec | New (ontology subproject, not `docs/architecture`, but cross-referenced from it per the existing pattern for `ontology/persistence`) | P0.3.3 |

## 4. README obligations

Per copilot-instructions ("any new structure/folders/projects must be documented" in the root README, and project-level READMEs for significant changes). New subprojects Phase 0 introduces, each needs its own `README.md` at creation time, not deferred:

| New subproject | Track | Introducing slice | Root `README.md` update |
|---|---|---|---|
| `platform/lattice-bom` | T-BUILD | P0.2.1 | Add row to the module tree (root README already has a "Repository Layout" table pattern to extend, not replace) |
| `platform/canonical-hash` | T-HASH | P0.4.1 | Same |
| `platform/graph-spi`, `graph-spi-tck`, `graph-adapter-tdb2`, `graph-adapter-fuseki` | T-STORE | P0.5.1, P0.5.4, P0.5.3, P0.5.12 | Same — contingent on resolving §2's first decision point first |
| `platform/coordination-spi`, `coordination-h2`, `coordination-postgres` | T-STORE (coordination realm) | P0.6.1, P0.6.2, P0.6.3 | Same |
| `platform/partitioned-queue-spi`, `partitioned-queue-rabbit`, `partitioned-queue-pg` | T-MSG | P0.8.1, P0.8.2, P0.8.3 | Same |
| `platform/runtime-host` | T-HOST | P0.7.3 | Same |
| `platform/testkit` | cross-cutting | first used at P0.7.7, formalised across P0.9 | Same |
| `platform/synth` | T-DATA | P0.9.1 | Same |
| `ontology/platform/` | T-ONT | P0.3.3 | Root README's "Ontology Layers" table gets a new row, following the pattern already used for MORK/SPC/Persistence |

Each README follows the existing per-subproject convention (see `tools/persistence/README.md` for the most recent example): purpose, install/bootstrap command (`mise run bootstrap:<name>`), test command (`mise run check:<name>`), and a pointer to the owning ADR(s).

## 5. `solution-design-specification.md` delta plan

The SDS describes the system as it exists **before** Phase 0. Phase 0 is the phase that invalidates the most of it. This is not a batch rewrite at phase close — per copilot-instructions' Doc Delta rule ("if the slice contradicts or extends a normative document, the document is edited in the same slice, no docs later"), each row below is edited by its named slice, not deferred to a Phase 0 close-out pass.

| SDS section | Change | Triggering slice |
|---|---|---|
| §1 Technical Capability Catalogue | Add rows for graph-primary lifecycle capabilities that did not exist before (canonicalisation, store SPI conformance, coordination realm); mark superseded rows (e.g. "Immutable graph-family registration" via JDBC) as superseded once P1.2.2 lands, not in Phase 0 | P0.4–P0.6 add rows; supersession is Phase 1 |
| §3 Data Architecture Summary | Rewritten to match `data-architecture.md`'s A74 rewrite — this table currently states PostgreSQL is system of record for lifecycle state; that becomes the graph once T-GPM (Phase 1) lands, but Phase 0's SPI and coordination-realm work already changes the "no component other than Control Plane/worker writes these stores" rule to "no component writes the RDF store except through `ScopedDataset`" (G1) | P0.5.1, cross-check at P0.1.1 |
| §4.1 Component Inventory | Add every new `platform/*` module from §4 of this plan, with its technology, deployment unit, and system-of-record columns | Each introducing slice, per §4 table above |
| §4.2 Control Plane Runtime | ADR-A44 is **amended**, not replaced (role-profiled deployment, virtual threads already assumed) — update the section to state the amendment explicitly, do not leave the pre-role-profiled description standing | P0.1.10, P0.7.3 |
| §4.5 RabbitMQ Topology | Extended, not replaced: add the ordering-class declarations (A59), poison-message policy (block-partition-and-page for strict per-key families), and priority/pool separation for runtime vs maintenance families that P0.8 introduces beyond the existing family table | P0.8.2, P0.8.4 |
| §5.1 Deployment Topology | Diagram gains the coordination realm (H2/Postgres) and role-profiled process boundaries once P0.7 lands; Compose reference stack gets the corrected `deployment/compose` path | P0.7.6 |
| §7 Robustness Design | §7.1's framing ("one authoritative PostgreSQL instance, one authoritative Fuseki dataset") is exactly what A74 changes — restate once the coordination realm (P0.6) and the CAP posture ADR (A48, already in the SDS backlog as a candidate) are ratified together | P0.6.4, cross-check against existing ADR-A48 candidate in SDS §8 |
| §8 Open Decisions and ADR Backlog | SDS's own candidate list (A44–A49) predates this epic. Confirm each candidate's disposition against the epic's actual ADR numbering (the epic starts new decisions at A50) before Phase 0 closes, so the backlog table does not silently drift from reality | P0.1 close-out, before phase gate |
| §9 Traceability Matrix | Add rows for every new capability from §1 above, following the existing column shape (Capability, Component(s), Data, Process map, UX surface) | Phase 0 close-out (P0.10) |

## 6. Phase gate checklist

Per [epic Part 12](lattice-platform-agentic-development-v0.2.md#part-12--phase-gate-checklists), applied to Phase 0 specifically:

1. All Phase 0 slice gates signed off in `docs/developer/validation/LOG.md`.
2. M0 (walking skeleton) and M1 (store conformance) demoed by a human against a clean-checkout compose stack.
3. `docs/traceability/matrix.csv` — zero claimed-but-untested requirements for Phase 0's G-nn/C-nn/A-nn set.
4. Every Phase 0 ADR ratified (A44 amendment through A76); every row in §5 above merged.
5. L7 baselines recorded (P0.4.7, P0.5.14).
6. L8 suites green (P0.5.8 scoping, P0.5.9 injection, P0.9.4 hostile fixtures consumed).
7. Non-weakening audit: N/A for Phase 0 (first phase, nothing prior to diff against).
8. Cold-start test: clean machine → clone → one `mise` command → stack up → seeded → E2E green, under 30 minutes.

## 7. Dependencies

Depends on nothing (first phase). Blocks all of Phase 1–4 per the epic's hard-ordering rule (Part 4, "Phase exit gate (hard)").
