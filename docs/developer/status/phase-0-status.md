<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Phase 0 — Decisions and Non-Retrofittable Foundations (Status)

**Unit type:** Phase
**Unit ID:** `phase-0`
**Status:** ⏳ Not started
**Last updated:** 2026-09-22
**Plan:** [phase-0-plan.md](../plans/phase-0-plan.md)
**Sketch:** [phase-0-sketch.md](../sketches/phase-0-sketch.md)

---

## Current state

Decomposed from the epic ([lattice-platform-agentic-development-v0.2.md](../plans/lattice-platform-agentic-development-v0.2.md)) on 2026-09-22. No slice has started. This status record exists so the phase has a place to accumulate state as P0.1–P0.10 execute, per the Epic Decomposition Model — it is the sole authoritative live-state document for this phase from this point forward.

## Pre-execution blockers

| Blocker | Detail | Resolution owner |
|---|---|---|
| `graph-spi` vs `semantic-dataset-spi` relationship undecided | See [phase-0-plan.md §2](../plans/phase-0-plan.md#2-pre-execution-decision-points-resolve-before-the-named-slice-starts) | Human — must resolve before P0.5.1 |

Nothing else blocks P0.1 starting immediately.

## Slice status

Not tracked row-by-row here until slices begin — the epic's Part 4 tables (P0.1.1 through P0.10.2) are the slice inventory. This section will convert to a per-slice status table (slice ID, status, VP link, sign-off date) once the first slice starts, matching the pattern in [rdf-sparql-patterns-status.md](rdf-sparql-patterns-status.md).

## Milestone tracker

| Milestone | Demonstrable outcome | Status |
|---|---|---|
| M0 | Walking skeleton (browser → HTTP → domain → response, in compose, one correlation ID traceable, Playwright smoke) | Not demonstrated |
| M1 | Store conformance (signed capability + benchmark report, TDB2 + Fuseki, hostile scoping suite green) | Not demonstrated |

## ADR ratification tracker

| ADR | Subject | Status |
|---|---|---|
| A44 | Control Plane HTTP runtime (amendment: role-profiled deployment) | Existing ADR, amendment not yet drafted |
| A50 | Role-profiled deployment | Not drafted |
| A51 | IRI & identity policy | Not drafted |
| A54 | Dataset topology | Not drafted |
| A57 | Change feed | Not drafted |
| A59 | `PartitionedWorkQueue` abstraction | Not drafted |
| A62 | SPC namespace harmonisation | Not drafted |
| A63 | `projectId` vs `environmentId` | Not drafted |
| A65 | Provenance | Not drafted |
| A66 | Principal model | Not drafted |
| A67 | Bi-temporal | Not drafted |
| A68 | PII & erasure | Not drafted |
| A69 | Pack trust model / safe SPARQL subset | Not drafted |
| A71 | Platform licence MPL-2.0 + SPI seam | Not drafted |
| A74 | Graph-primary realm model | Not drafted |
| A75 | Three-tier store SPI | Not drafted |
| A76 | Maven vs Gradle | Not drafted |

## Documentation and README debt tracker

Tracks [phase-0-plan.md §3–5](../plans/phase-0-plan.md#3-documentation-obligations--docsarchitecture) as it is worked off. All rows currently outstanding — nothing in this phase has started.

## Next steps

1. Human resolves the `graph-spi`/`semantic-dataset-spi` decision point.
2. Begin P0.1 (decision pack) — draft ADR-A74 (P0.1.1) and ADR-A75 (P0.1.2) first, per the epic's own critical-path note (Part 14).
3. Convert this file's "Slice status" section to a per-slice table once P0.1.1 starts.
