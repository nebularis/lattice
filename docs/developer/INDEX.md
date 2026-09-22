<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# LATTICE Developer Coordination Index

**Last updated:** 2026-09-22  
**Purpose:** Single source of truth for all active units of work: sketches, plans, status, reviews, and validation packs.  
**Format:** By unit identifier, with links to all related documents and current status.

---

## How to read this index

Each work unit has:
- **Status** (✅ complete, 🚧 in-progress, ⏳ planned, 🗄️ archived)
- **Unit ID** (referenced in reviews and handoffs)
- **Documents** (sketch, plan, status, review, validation pack)
- **Blockers** (if any)
- **Key findings** (major discoveries or decisions)

**Navigation:** Use Ctrl/Cmd+F to search by topic (e.g., "RDF", "MTP", "housekeeping") or by unit ID.

---

# Part I — Completed Work

## 1. RDF/SPARQL Implementation Patterns and Persistence Compiler

| Field | Value |
|-------|-------|
| **Status** | ✅ Slice 1 & 2 complete; Slice 3 planned |
| **Unit ID** | `rdf-sparql-patterns-phase` |
| **Sketch** | [persistence-profile-substrate.md](sketches/persistence-profile-substrate.md) |
| **Plan** | [rdf-sparql-patterns-phase-plan.md](plans/rdf-sparql-patterns-phase-plan.md) |
| **Status Record** | [rdf-sparql-patterns-status.md](status/rdf-sparql-patterns-status.md) |
| **Architecture Guide** | [docs/architecture/rdf-sparql-patterns-guide.md](../architecture/rdf-sparql-patterns-guide.md) (Slice 1) |
| **ADRs** | ADR-A78 (persistence substrate), ADR-A79 (compiler), ADR-A80 (housekeeping) — all Accepted |
| **Implementation** | `ontology/persistence` (Turtle vocabulary + SHACL shapes + 14 examples), `tools/persistence` (Python compiler, 239 tests passing) |
| **Validation Pack** | [persistence-substrate-and-compiler.md](validation/persistence-substrate-and-compiler.md) |

### Slice Completion Status
| Slice | Deliverable | Status |
|-------|------------|--------|
| **1** | [rdf-sparql-patterns-guide.md](../architecture/rdf-sparql-patterns-guide.md) — consolidated 4 source notes into authoritative reference (30 chapters covering K/O/C/T/QP patterns) | ✅ Complete |
| **2** | `ontology/persistence` + `tools/persistence` compiler + policy enforcement + doc deltas | ✅ Complete |
| **3** | `platform/housekeeping` module (scaffolding, not execution) | 🚧 Planned, not started |

### Key Findings
- **Target model discovery:** Classes need paired `(class, deployment)` targets within each graph scope, added `dal:coversClass` property
- **SPARQL validity bugs fixed:** Property paths invalid in DELETE/INSERT blocks; payload triples need `#PAYLOAD#` marker instead of SPARQL variables
- **Mustache parsing gotcha:** Comments cannot contain bare `}}` without breaking parsing
- **pyshacl semantics:** `allow_warnings=True` needed for non-blocking `sh:Warning` severity

### Blocks
- Epic decomposition into phase plans (awaiting integration of patterns into Phase 0 plan)
- Housekeeping module first cut (Slice 3, depends on Slice 2 compiler)

---

## 2. LLM Training and MORK Teaching Pack (MTP) Generation

| Field | Value |
|-------|-------|
| **Status** | ✅ Complete and production-ready |
| **Unit ID** | `llm-training-mtp` |
| **Sketch** | [llm-training.md](sketches/llm-training.md), [MTP L2 Generator Sketch.md](sketches/MTP%20L2%20Generator%20Sketch.md) |
| **Plan** | [mtp-implementation-plan.md](sketches/mtp-implementation-plan.md) → [mtp-execution.md](status/mtp-execution.md) |
| **Status Record** | [llm-training-mtp.md](status/llm-training-mtp.md), [mtp-execution.md](status/mtp-execution.md) |
| **Implementation** | `tools/mork/src/mtp/` (Python package) |
| **Tests** | 346 tests passing under `mise run check:mtp` |
| **Deliverables** | L0-L5 curriculum: 258 terms, 895 axioms, 9 lenses, 30+ cassettes, 20 output files |

### Completion Status
- ✅ Facts extraction (S1)
- ✅ Doctrine pinning (S2)
- ✅ Axiom ownership (S3-S5)
- ✅ Lensing (S6)
- ✅ Mutation-derived ground truth (S7-S9)
- ✅ Cassette validation (S10)
- ✅ Rendering (S11-S13)
- ✅ Test determinism (L2), roundtrip validation, mutation checks

### Blocks
- Phase 7 backend integration (runtime API for MTP consumption)

---

## 3. Repository Topology and Documentation Governance

| Field | Value |
|-------|-------|
| **Status** | ✅ Accepted (ADR-A77) |
| **Unit ID** | `repository-topology-a77` |
| **Status Record** | [repository-topology-a77.md](status/repository-topology-a77.md) |
| **ADR** | [ADR-A77](../architecture/decisions/ADR-A77-repository-topology-and-documentation-governance.md) |
| **Implementation** | Relocation of semantic assets to `ontology/`, tools to `tools/`, restructuring of `docs/developer/` |
| **Doc Reference** | [.github/copilot-instructions.md](../../.github/copilot-instructions.md) — "Repository Topology and Documentation Governance" section |

### Deliverables
- ✅ Folder structure relocated per ADR-A77
- ✅ `mise` remains sole orchestration entry point
- ✅ Epic Decomposition Model documented in copilot-instructions
- ✅ Validation Pack and traceability model specified

---

## 4. MORK Eligibility Compiler

| Field | Value |
|-------|-------|
| **Status** | ⏳ Source complete, awaiting runtime validation |
| **Unit ID** | `eligibility-compiler` |
| **Status Record** | [eligibility-compiler.md](status/eligibility-compiler.md) |
| **Implementation** | `tools/mork_compilers/` — three backends (SPARQL, SHACL, SWRL) |
| **Coverage** | IntervalCondition only (other condition types deferred); positive-only per ADR-A24 |
| **Tests** | Unit tests present; need runtime validation in Python 3.11 environment with SHACL/SWRL engines |

### Deliberate Non-Coverage
- No native backend
- No Executable Projection Contract layer
- No profile-level aggregate artifact
- SWRL positive-only per ADR-A24

### Blocks
- Needs network environment with SHACL/SWRL engines to validate

---

## 5. Governance Surfaces (MORK Review Workbench, Surface Studio)

| Field | Value |
|-------|-------|
| **Status** | 🟡 Skeleton UI complete; backend integration pending |
| **Unit ID** | `governance-surfaces-integration` |
| **Sketch** | [governance-and-versioning-migration.md](sketches/governance-and-versioning-migration.md) |
| **Status Record** | [governance-surfaces.md](status/governance-surfaces.md) |
| **Plan** | [governance-surfaces-integration.md](plans/governance-surfaces-integration.md) |
| **Implementation** | `apps/mork-review-workbench/`, `apps/surface-contract-studio/` (Vite + React) |

### Deliverables
- ✅ Review Workbench: 6 decision buttons (Confirm/Retarget/Reshape/Decline/Teach/Defer), evidence ribbon (Witness/Coverage/Alternative)
- ✅ Studio: 4 fixture contracts with lifecycle transitions and diff viewer
- ⏳ Role model demonstrated (enforcement not wired)
- ⏳ Token ribbon partial (needs MCN source view)

### Remaining Work (3 slices per plan)
1. **Phase 2 Slice:** Studio backend wiring (MORK mapping integration)
2. **Phase 5 Slice:** Bench permission model + enforcement
3. **Phase 5 Slice:** Evidence projection state

---

# Part II — Active/Planned Work

## 6. Epic Decomposition: Lattice Platform Agentic Development

| Field | Value |
|-------|-------|
| **Status** | 🚧 In progress; awaiting RDF patterns integration |
| **Unit ID** | `lattice-platform-development` (epic) |
| **Plan** | [lattice-platform-agentic-development-v0.2.md](plans/lattice-platform-agentic-development-v0.2.md) |
| **Description** | Decompose epic into Phase 0-9 plans with dependency DAG and milestones |
| **Blockers** | RDF/SPARQL patterns integration; Phase 0 plan revision for compiler-generated queries |

### Scope
- 16 tracks (T-DEC through T-SEC) with hard orderings
- 9 milestones (M0: walking skeleton through M9)
- 25+ modules in Part 1
- Phases 0-1 at slice granularity; Phases 2-4 lighter initially

### Changes Needed Per RDF Patterns Completion
- Phase 0.2 (Walking skeleton): Integrate patterns T (metadata graphs) + C (CAS)
- Phase 0.3 (Schema & contracts): Integrate pattern K (uniqueness) + compiler
- Phase 0.4 (Canonicalization): Integrate pattern O (ordering)
- Phase 1+ (Ingestion/Query): Revise per compiler-generated query binding model

---

## 7. Housekeeping First Cut

| Field | Value |
|-------|-------|
| **Status** | 🚧 Slice 3 of RDF patterns; scoped, not started |
| **Unit ID** | `platform-housekeeping` |
| **Slice** | Part 2, Slice 3 of [rdf-sparql-patterns-phase-plan.md](plans/rdf-sparql-patterns-phase-plan.md) |
| **ADR** | [ADR-A80](../architecture/decisions/ADR-A80-housekeeping-component-boundary.md) |
| **Depends On** | `tools/persistence` compiler (Slice 2) |

### Deliverables (planned)
- `platform/housekeeping` module scaffolding (not execution)
- Contracts and configuration model
- Generated queries per ADR-A80
- Audit queries for gap-completeness scan and fork detection

### Blockers
- Awaits completion of persistence compiler (Slice 2 complete ✅)

---

# Part III — Archived/Historical Work

## 8. Phase Handoff Documents (0-6)

| Phase | Status Record | Key Outcome |
|-------|---|---|
| Phase 0-1 | [phase-0-1-handoff.md](status/phase-0-1-handoff.md) | 🗄️ Archived; refer to individual status docs |
| Phase 2 | [phase-2-handoff.md](status/phase-2-handoff.md) | 🗄️ Archived |
| Phase 3 | [phase-3-handoff.md](status/phase-3-handoff.md) | 🗄️ Archived |
| Phase 4 | [phase-4-handoff.md](status/phase-4-handoff.md) | 🗄️ Archived |
| Phase 5 | [phase-5-handoff.md](status/phase-5-handoff.md) | 🗄️ Archived |
| Phase 6 | [phase-6-handoff.md](status/phase-6-handoff.md) | 🗄️ Archived |

**Reference:** [platform-continuation.md](status/platform-continuation.md) describes current platform state post-Phase-6.

---

## 9. Other Completed Units

| Unit | Status | Link |
|------|--------|------|
| **MORK Package Split** | ✅ Complete | [mork-package-split.md](status/mork-package-split.md) |
| **SPC Package Split** | ✅ Complete | [spc-package-split.md](status/spc-package-split.md) |
| **Ontology Root Relocation** | ✅ Complete | [ontology-root-relocation.md](status/ontology-root-relocation.md) |
| **Validation Pause Handover** | ✅ Complete | [validation-pause-handover.md](status/validation-pause-handover.md) |
| **Validation Status** | ✅ Track record | [validation-status.md](status/validation-status.md) |
| **Implementation Handover (Phases 0-6)** | 🗄️ Archived | [implementation-handover-historical.md](status/implementation-handover-historical.md) |
| **Design Sketches (earlier batch)** | ✅ Catalogued | [DESIGN_SKETCHES_INDEX.md](status/DESIGN_SKETCHES_INDEX.md) and [design-sketches-validation-summary.md](status/design-sketches-validation-summary.md) |

---

# Part IV — How to Navigate This Index

## By Topic

### RDF/SPARQL & Persistence
- Guide: [rdf-sparql-patterns-guide.md](../architecture/rdf-sparql-patterns-guide.md)
- ADRs: A78, A79, A80
- Slice 2 (complete): `ontology/persistence` + `tools/persistence`
- Slice 3 (planned): Housekeeping

### MTP & LLM Training
- Status: [llm-training-mtp.md](status/llm-training-mtp.md)
- Execution: [mtp-execution.md](status/mtp-execution.md)
- 346 tests passing

### Architecture Decisions
- All ADRs: [docs/architecture/decisions/](../architecture/decisions/)
- Traceability: Referenced in each unit's plan/status/validation-pack

### Sketches & Plans
- Previous batch (llm-training, governance, eligibility): [DESIGN_SKETCHES_INDEX.md](status/DESIGN_SKETCHES_INDEX.md)
- Current batch (persistence): [persistence-profile-substrate.md](sketches/persistence-profile-substrate.md) + [rdf-sparql-patterns-phase-plan.md](plans/rdf-sparql-patterns-phase-plan.md)
- Epic: [lattice-platform-agentic-development-v0.2.md](plans/lattice-platform-agentic-development-v0.2.md)

### Validation Packs
- Location: `docs/developer/validation/<unit-id>.md`
- Most recent: [persistence-substrate-and-compiler.md](validation/persistence-substrate-and-compiler.md)

## By Phase

- **Phase 0:** Awaiting decomposition; blocks on RDF patterns integration
- **Phase 2:** Governance surfaces backend integration (3 slices planned)
- **Phase 7:** MTP backend integration (runtime API for curriculum delivery)

## By Status

### ✅ Complete (Ready for Handoff or Integration)
1. RDF/SPARQL patterns guide (Slice 1)
2. Persistence compiler (Slice 2) — 239 tests passing
3. LLM training / MTP generation — 346 tests passing
4. Repository topology (ADR-A77)
5. MORK eligibility compiler (awaiting runtime validation, not handoff)
6. Phase 0-6 handoff documents

### 🚧 In Progress
1. Epic decomposition (Phase 0-9 plans)
2. Housekeeping first cut (Slice 3, scoped but not started)

### ⏳ Planned
1. Housekeeping execution (tied to future store SPI)
2. Governance surfaces backend integration (Phase 2/5)
3. Phase 0-9 implementation

### 🗄️ Archived
1. Phase 0-6 handoff documents (refer to individual status records)
2. Implementation handover from earlier phases

---

# Part V — Key Decision Points (Awaiting Ratification or Decomposition)

| Item | What | Why | Next |
|------|------|-----|------|
| **Epic decomposition** | Break `lattice-platform-agentic-development-v0.2.md` into Phase 0-9 plans | Patterns are now defined; Phase 0 needs concrete slices | Integrate RDF patterns into Phase 0.2-0.4 plans |
| **Housekeeping first cut (Slice 3)** | Scaffold `platform/housekeeping` module | Compiler ready; module contracts defined in ADR-A80 | Author Slice 3 (housekeeping scaffolding) |
| **Store SPI** | Design runtime SPI for query execution | Compiler produces templates; runtime binding TBD | Separate epic/phase after housekeeping |
| **MTP backend integration (Phase 7)** | Runtime API for LLM curriculum delivery | MTP generation complete; needs HTTP endpoint | Post-Phase-6 work |

---

# Part VI — Traceability and Validation

## Validation Packs (VPACKS)
- [persistence-substrate-and-compiler.md](validation/persistence-substrate-and-compiler.md) — RDF patterns Slice 2
- More to be created as each slice/phase completes

## Test Taxonomy (L0–L8)
- **L0:** Build smoke
- **L1:** Unit / pure-function
- **L2:** Property & determinism
- **L3:** Contract validation
- **L4:** Component integration
- **L5:** System E2E
- **L6:** UI E2E
- **L7:** Non-functional (SLO, benchmark)
- **L8:** Hostile / security

## Test Coverage Status
| Unit | Tests | Command |
|------|-------|---------|
| Persistence compiler | 239 passing | `mise run check:persistence` |
| MTP | 346 passing | `mise run check:mtp` |
| Eligibility compiler | Present | `mise run check:eligibility-compiler` |

---

# Part VII — Open Questions (Blocking or Deferred)

1. **Store SPI design** — How does runtime connect compiled templates to live backend? (Deferred to separate SPI phase)
2. **Phase 0 plan revision** — What changes when using compiler-generated queries instead of hand-written SPARQL? (Needs epic decomposition)
3. **MTP backend integration** — What HTTP API shape for LLM curriculum consumption? (Phase 7, post-Phase-6)
4. **Housekeeping execution** — When is the housekeeping component itself executed (real-time vs. batch)? (ADR-A80 defers to future phase)

---

## Document Maintenance

This index is updated when:
- A new sketch is commissioned
- A plan is created or revised
- A status record is completed
- A validation pack is accepted
- A unit transitions between status states (🚧 → ✅, etc.)

**Last reviewed:** 2026-09-22  
**Next review:** Upon epic decomposition completion or Phase 0 handoff
