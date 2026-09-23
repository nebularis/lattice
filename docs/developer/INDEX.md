<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# LATTICE Developer Coordination Index

**Last updated:** 2026-09-22 — Surface-MORK migration complete (Phases 0–8 consolidated)  
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
- Housekeeping module first cut (Slice 3, depends on Slice 2 compiler)

Epic decomposition into phase plans is **no longer blocked**: the required Phase 2 (P2.1/P2.3/P2.4) revision integrating this compiler is complete — see Part II, §6.

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
| **Status** | ⏳ Source complete; verification plan authored (2026-09-23), not yet executed |
| **Unit ID** | `eligibility-compiler` |
| **Plan** | [eligibility-compiler.md](plans/eligibility-compiler.md) — verification (Part A) + shared test-only reasoning/rules-engine infrastructure (Part B) |
| **Status Record** | [eligibility-compiler.md](status/eligibility-compiler.md) |
| **Implementation** | `tools/mork_compilers/` — three backends (SPARQL, SHACL, SWRL) |
| **Coverage** | IntervalCondition only (other condition types deferred); positive-only per ADR-A24 |
| **Tests** | Unit tests present; need runtime validation. SPARQL (`rdflib`) and SHACL (`pyshacl`) validation need no new dependency; SWRL/OWL-reasoner validation is gated on Part B's new shared test-only module |

### Deliberate Non-Coverage
- No native backend
- No Executable Projection Contract layer
- No profile-level aggregate artifact
- SWRL positive-only per ADR-A24

### Blocks
- SWRL/OWL-reasoner validation needs `platform/reasoning-testkit` (new, proposed by the plan above, ADR-A81) — a shared, test-scope-only Maven module, consumed by Python test suites via a CLI subprocess rather than a direct dependency. Explicitly never a runtime dependency of any product package.
- DL-safety check complete (2026-09-23): ADR-A24's SWRL subset **is DL-safe** (verified against `swrl_backend.py`, `eligibility_ir.py`, the example fixture, and both governing ontology specs — no `owl:equivalentClass`/`someValuesFrom`/`hasValue` on any relevant term). This rules HermiT in as a candidate reasoner but does not settle the engine choice, because the generated rules also need `swrlb:` numeric built-ins, which HermiT does not implement natively.
- Licence check (2026-09-23): Openllet is **AGPL-3.0** (inherited from Pellet — an earlier plan draft wrongly said Apache-2.0), usable only under the module's isolation design (test-scope + subprocess CLI, never linked or distributed). A better-licensed path is unverified but promising: **SWRLAPI (BSD-2-Clause) + its Drools-based rule engine (Apache-2.0)**, which evaluates `swrlb:` built-ins itself independent of the underlying OWL reasoner — if it accepts **HermiT (LGPL-3.0)** in place of Pellet, the whole pipeline avoids AGPL. Spiking that combination is the first task of ADR-A81. See [eligibility-compiler.md](plans/eligibility-compiler.md) §B.4

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
| **Status** | ✅ Decomposed into 5 phase chunks (2026-09-22). Phase 0 ready to execute, pending one pre-execution decision (below) |
| **Unit ID** | `lattice-platform-development` (epic) |
| **Plan** | [lattice-platform-agentic-development-v0.2.md](plans/lattice-platform-agentic-development-v0.2.md) |
| **Description** | Decomposed into Phase 0-4 plans with dependency DAG and milestones |
| **Blockers** | See "Pre-execution decision points" under Phase 0 below |

### Scope
- 16 tracks (T-DEC through T-SEC) with hard orderings
- 9 milestones (M0: walking skeleton through M9)
- 25+ modules in Part 1
- Phases 0-1 at slice granularity; Phases 2-4 lighter initially

### Required Epic Plan Revision — ✅ Done (2026-09-22)
Part 6 (Phase 2) of the epic plan now integrates the persistence compiler instead of constructing SPARQL ad hoc:
- **P2.1 (C-05, mapping plan compiler):** new slice P2.1.4a resolves each `writeTarget`'s `ontology/persistence` profile and emits a `dal:CompiledProfile` plus instantiated (still-unbound) SPARQL Update text via `tools/persistence`, as part of `CompiledMappingSet`.
- **P2.3 (C-04, ingestion gateway):** the `assert` step (P2.3.1) and commit step (P2.3.6) bind request-scoped parameters into those pre-instantiated templates — never construct SPARQL at request time. Deliberately scoped narrower than the still-deferred Request Query Mapping library (Part 13, open question 11).
- **P2.4 (C-12, query plane):** the typed read API (P2.4.1) reuses the same resolved profile (ordering grain, receipt model) to shape read queries, consistent with the write path by construction.

See [rdf-sparql-patterns-phase-plan.md](plans/rdf-sparql-patterns-phase-plan.md) and [persistence-profile-substrate.md](sketches/persistence-profile-substrate.md) for the underlying substrate; no new ADR was needed (refinement of ADR-A78/A79 within existing guardrail G5).

### Optional Phase 0.2–0.4 Integration — ✅ Done (2026-09-22)
Per [COORDINATION_REORG_HANDOFF.md](../COORDINATION_REORG_HANDOFF.md), Phase 0 of the epic plan (Part 4) now carries a "Persistence-pattern coherence" note plus cross-references so its vocabulary is `dal:`-nameable from day one, without Phase 0 depending on `tools/persistence`:
- **Pattern C (CAS)** ↔ `dal:ConcurrencyStrategy`, cross-referenced at P0.5.2 (`conditionalWrite`/`guardSatisfied`) and P0.5.6 (concurrency TCK).
- **Pattern T (named-graph-per-batch)** ↔ `dal:MetaTopologyProfile`/`dal:ReceiptModel`, cross-referenced at P0.1.5 (ADR-A65) and P0.3.6 (`provenance.ttl`).
- **Pattern K (uniqueness)** ↔ `dal:UniquenessConstraint`, cross-referenced at P0.1.3 (ADR-A51).
- **Pattern O (dense ordering)** ↔ `dal:OrderingGrain`/`dal:DatasetTierModel`, cross-referenced at P0.4.4 (canonicalisation) and P0.5.7 (`CommitSequence` + ordering TCK).
- New slice **P0.3.9** (documentation only) produces `ontology/persistence/docs/platform-vocabulary-alignment.md`, proving no namespace/semantic collision between the six `dal:` dimensions and the platform vocabulary P0.3 defines.
- New guardrail **G11** (§0.4): no `dal:`-governed write path may hand-construct SPARQL, reserved at P0.2.7 and enforced in full once P0.5.2's write surface exists.

### Epic Decomposition — ✅ Done (2026-09-22)

| Phase | Plan | Status | Sketch | Depth |
|---|---|---|---|---|
| 0 — Decisions and foundations | [phase-0-plan.md](plans/phase-0-plan.md) | [phase-0-status.md](status/phase-0-status.md) | [phase-0-sketch.md](sketches/phase-0-sketch.md) | Full slice detail (epic Part 4, referenced not duplicated) |
| 1 — Graph-primary core and deployment plane | [phase-1-plan.md](plans/phase-1-plan.md) | [phase-1-status.md](status/phase-1-status.md) | [phase-1-sketch.md](sketches/phase-1-sketch.md) | Full slice detail (epic Part 5) |
| 2 — Ingestion and query planes | [phase-2-plan.md](plans/phase-2-plan.md) | [phase-2-status.md](status/phase-2-status.md) | [phase-2-sketch.md](sketches/phase-2-sketch.md) | Rolling-wave placeholder, expands at P1.11.3 |
| 3 — Operation plane | [phase-3-plan.md](plans/phase-3-plan.md) | [phase-3-status.md](status/phase-3-status.md) | [phase-3-sketch.md](sketches/phase-3-sketch.md) | Rolling-wave placeholder, expands at P2.11.4 |
| 4 — Maturity | [phase-4-plan.md](plans/phase-4-plan.md) | [phase-4-status.md](status/phase-4-status.md) | [phase-4-sketch.md](sketches/phase-4-sketch.md) | Placeholder, sized after Phase 3 measurement |

Each phase plan adds three obligations the epic's slice tables name but never tabulate: a `docs/architecture` deliverables table, a subproject-README table, and a `solution-design-specification.md` delta table (which SDS section changes, and at which slice).

**Three mechanical corrections made to the epic during decomposition** (not architectural decisions — corrections against already-established convention): `deploy/` → `deployment/` (root already exists under that name), `make`/`just` → `mise` tasks (copilot-instructions mandates `mise` as sole orchestrator, ADR-A29 not superseded), `docs/adr/` → `docs/architecture/decisions/`.

**Pre-execution decision points surfaced, not resolved** (see [phase-0-plan.md §2](plans/phase-0-plan.md#2-pre-execution-decision-points-resolve-before-the-named-slice-starts)):
- Relationship between the epic's proposed `platform/graph-spi` family and the existing `platform/semantic-dataset-spi`/`semantic-dataset-fuseki` — blocks P0.5.1.
- `apps/surface-studio`/`apps/mork-bench` (epic's Part 1 names) vs existing `apps/surface-contract-studio`/`apps/mork-review-workbench` — blocks P1.10, lower urgency.

No code was written and no new Phase 0→Phase 2 dependency was introduced — this is cross-referencing and one new documentation-only slice.

---

## 7. Surface Projection and MORK Unified Compiler (Phases 0–10)

| Field | Value |
|-------|-------|
| **Status** | ✅ Phases 0–8 complete; Phases 9–10 planned |
| **Unit ID** | `surface-mork-unified-projection` (Epic) |
| **Sketch** | [surface-projection.md](sketches/surface-projection.md) |
| **Plan** | [surface-mork-unified-projection-plan.md](plans/surface-mork-unified-projection-plan.md) |
| **Status Records** | [surface-mork-unified-projection.md](status/surface-mork-unified-projection.md), [surface-outstanding-items.md](status/surface-outstanding-items.md) |
| **Implementation** | `tools/surface/` (compiler), `tools/mork_compilers/` (backends), `ontology/surface/` (vocabulary + shapes + examples) |
| **ADRs** | A16–A28 (13 decisions covering projection, lowering, governance, compilers, parity, conformance, invalidation) |
| **Tests** | 61/61 Surface tests; 15/15 MORK backend tests; 346/346 LLM/MTP tests |

### Phase Completion Status

| Phase | Scope | Status | Tests | Key Document |
|-------|-------|--------|-------|---|
| **0** | Vocabulary and layer semantics | ✅ Complete | ontology conforms | [Status §0](status/surface-mork-unified-projection.md#phase-0) |
| **1** | Projection, promotion, index contracts | ✅ Complete | all validate | [Status §1](status/surface-mork-unified-projection.md#phase-1) |
| **2** | Surface compiler architecture | ✅ Complete | 61/61 | [Status §2](status/surface-mork-unified-projection.md#phase-2) |
| **3** | Surface-to-MORK lowering | ✅ Complete | 61/61 | [Status §3](status/surface-mork-unified-projection.md#phase-3) |
| **4** | MORK governance and versioning | ✅ Complete | governance shapes | [Status §4](status/surface-mork-unified-projection.md#phase-4) |
| **5** | MORK compiler backends | ✅ Complete | 15/15 (SPARQL, SHACL, SWRL, Eligibility IR) | [Status §5](status/surface-mork-unified-projection.md#phase-5) |
| **6** | LLM training curriculum generation | ✅ Complete | 346/346 | [Status §6](status/surface-mork-unified-projection.md#phase-6) |
| **7** | Invalidation and minimal-scope regeneration | ✅ Complete | 60+ invalidation tests | [Status §7](status/surface-mork-unified-projection.md#phase-7) |
| **8** | Conformance, parity, and CI gates | ✅ Complete | parity ≥99%; 7/8 verification items; 1 SWRL integration pending | [Status §8](status/surface-mork-unified-projection.md#phase-8) |
| **9** | Migration guides and phased rollout | ⏳ Planned | — | [Plan §9](plans/surface-mork-unified-projection-plan.md#phase-9) |
| **10** | Scale, performance, optimization | ⏳ Planned | — | [Plan §10](plans/surface-mork-unified-projection-plan.md#phase-10) |

### Key Findings
- **Projection mechanism:** Unified abstraction for promotion (restating as direct properties) and shadow indexing (generating lookup symbols)
- **Deterministic lowering:** Surface contracts lower to MORK with full provenance tracking and minimal-scope regeneration
- **Compiler family:** Four production backends (SPARQL, SHACL, SWRL, Eligibility IR) + one deferred native backend
- **Parity guarantees:** Generated output matches source contract semantics at ≥99% fidelity
- **Verification checklist:** 7/8 items passing; SWRL reasoner integration (Phase 8, item 7) remains open

### Completed Slices

| Slice ID | Deliverable | Status | Reference |
|----------|-------------|--------|-----------|
| `surface-projection` | Design sketch + plan + status | ✅ | [Status §§1–2](status/surface-mork-unified-projection.md) |
| `surface-to-mork-lowering` | Lowering engine (Phase 3) | ✅ | [Plan §3](plans/surface-mork-unified-projection-plan.md#phase-3) |
| `mork-governance-and-versioning` | Foundation integration (Phase 4) | ✅ | [Plan §4](plans/surface-mork-unified-projection-plan.md#phase-4) |
| `mork-compiler-family` | All backends (Phase 5) | ✅ | [Plan §5](plans/surface-mork-unified-projection-plan.md#phase-5) |
| `surface-invalidation-and-regeneration` | Read-set tracking (Phase 7) | ✅ | [Plan §7](plans/surface-mork-unified-projection-plan.md#phase-7) |
| `surface-conformance-and-parity` | CI gates (Phase 8) | ✅ | [Plan §8](plans/surface-mork-unified-projection-plan.md#phase-8) |

### Operational Documentation
- [Invalidation Runbook](../operator/surface-invalidation-runbook.md) — 4 operational scenarios with release gates
- [Revision Lifecycle](../operator/surface-revision-lifecycle.md) — State machine, versioning, canonicalisation cutover procedures

### Outstanding Items
| Item | Status | Link |
|------|--------|------|
| Signature scope and law X6 | ✅ Closed | [Outstanding items §3.1](status/surface-outstanding-items.md#31-signature-scope-and-law-x6--closed) |
| Foundation migration (`srf:DerivedArtefact`) | ⏳ Needed | [Outstanding items §3.2](status/surface-outstanding-items.md#32-adr-a01-convention-conflict--closed) |
| Profile identity assertion | ⏳ Blocked | [Outstanding items §3.3](status/surface-outstanding-items.md#33-profile-identity-assertion--blocked) |
| MORK toolchain join assumptions | ⏳ Needed | [Outstanding items §3.4](status/surface-outstanding-items.md#34-mork-toolchain-join-assumptions--needed) |

### Deferred Items (Explicit Scoping)
- `srf:RangePartitionPopulation` (bucketing) — blocked on Quantification layer
- Stacking beyond depth 1 — composition laws drafted, full support deferred
- Other eligibility strategies beyond IntervalContainment — deferred to broader Eligibility expansion
- `srf:ExternalIndex` — admitted but deferred, no criteria yet
- Entailment regimes beyond NoEntailment — deferred to Phase TBD

### Blockers
- Phase 8 SWRL verification: Reasoner integration for generated SWRL rules (1/8 checklist item remaining)
- Phase 9 decomposition: Awaits Phase 8 sign-off

---

## 8. Housekeeping First Cut

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

### Surface Projection and MORK Compiler
- Sketch: [surface-projection.md](sketches/surface-projection.md)
- Plan: [surface-mork-unified-projection-plan.md](plans/surface-mork-unified-projection-plan.md)
- Status: [surface-mork-unified-projection.md](status/surface-mork-unified-projection.md), [surface-outstanding-items.md](status/surface-outstanding-items.md)
- ADRs: A16–A28 (13 decisions)
- Implementation: `tools/surface/` (compiler), `tools/mork_compilers/` (backends), `ontology/surface/` (vocab + shapes)
- Tests: 61/61 Surface, 15/15 MORK backends, 346/346 LLM/MTP
- Operations: [surface-invalidation-runbook.md](../operator/surface-invalidation-runbook.md), [surface-revision-lifecycle.md](../operator/surface-revision-lifecycle.md)

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
6. Surface Projection Phases 0–8 — 61/61 Surface tests, 15/15 MORK backends, 7/8 verification items
7. Phase 0-6 handoff documents

### 🚧 In Progress
1. Epic decomposition (Phase 0-9 plans)
2. Housekeeping first cut (Slice 3, scoped but not started)
3. Surface MORK Phase 8 verification (SWRL reasoner integration, 1/8 items pending)

### ⏳ Planned
1. Housekeeping execution (tied to future store SPI)
2. Governance surfaces backend integration (Phase 2/5)
3. Phase 0-9 implementation
4. Surface MORK Phase 9 — Migration guides and phased rollout
5. Surface MORK Phase 10 — Scale and performance optimization

### 🗄️ Archived
1. Phase 0-6 handoff documents (refer to individual status records)
2. Implementation handover from earlier phases

---

# Part V — Key Decision Points (Awaiting Ratification or Decomposition)

| Item | What | Why | Next |
|------|------|-----|------|
| **Epic decomposition** | Break `lattice-platform-agentic-development-v0.2.md` into Phase 0-9 plans | Required Phase 2 (P2.1/P2.3/P2.4) revision and the optional Phase 0.2-0.4 coherence note are both complete (2026-09-22) | Begin Phase 0 decomposition |
| **Surface MORK Phase 8 verification** | SWRL rule load into OWL reasoner (final verification item) | 7/8 verification items complete; SWRL backend generates rules but integration needed | Resolve before Phase 9 sign-off |
| **Surface MORK Phase 9 decomposition** | Break migration and phased rollout into slices | Phase 8 complete (except SWRL integration); Phase 9 is planned but not decomposed | Decompose after Phase 8 verification complete |
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
| Surface compiler | 61 passing | `pytest tools/surface/src/surface/test_surface.py -v` |
| MORK compiler backends | 15 passing | `pytest tools/mork_compilers/src/mork_compilers/test_mork_compilers.py -v` |
| LLM/MTP | 346 passing | `mise run check:mtp` |
| Persistence compiler | 239 passing | `mise run check:persistence` |
| Eligibility compiler | Present | `mise run check:eligibility-compiler` |

---

# Part VII — Open Questions (Blocking or Deferred)

1. **Store SPI design** — How does runtime connect compiled templates to live backend? (Deferred to separate SPI phase)
2. ~~Phase 0.2–0.4 walking-skeleton pattern integration~~ — done (2026-09-22): Part 4 of the epic plan carries the Pattern C/T/K/O ↔ `dal:` cross-references, new slice P0.3.9, and guardrail G11. See Part II, §6 and Part V.
3. **MTP backend integration** — What HTTP API shape for LLM curriculum consumption? (Phase 7, post-Phase-6)
4. **Housekeeping execution** — When is the housekeeping component itself executed (real-time vs. batch)? (ADR-A80 defers to future phase)
5. **Surface MORK Phase 9 decomposition** — How to slice migration guides and phased rollout? (Blocking Phase 9, needs decomposition after Phase 8 SWRL verification)
6. **Foundation migration for `srf:DerivedArtefact`** — Should profile identity be a Foundation concept or Surface-only? (Blocking profile identity assertion in Surface; see [surface-outstanding-items.md](status/surface-outstanding-items.md#33-profile-identity-assertion--blocked))
7. **MORK toolchain join assumptions** — Pre-production verification checklist for join operations in mapping compilation (see [surface-outstanding-items.md](status/surface-outstanding-items.md#34-mork-toolchain-join-assumptions--needed))

---

## Document Maintenance

This index is updated when:
- A new sketch is commissioned
- A plan is created or revised
- A status record is completed
- A validation pack is accepted
- A unit transitions between status states (🚧 → ✅, etc.)

**Last updated:** 2026-09-22 — Surface-MORK documentation migration (Phases 0–8) merged into INDEX  
**Last reviewed:** 2026-09-22  
**Next review:** Upon Phase 8 SWRL verification completion and Phase 9 decomposition
