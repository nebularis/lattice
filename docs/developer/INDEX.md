<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# LATTICE Developer Coordination Index

**Last updated:** 2026-09-25 — `applied-ontology-readiness` AOR-12/13 and ADRs A-83, A-93 to A-96 drafted. `documentation-link-repair` planned  
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

## Persistence and IRI patterns: the change package at a glance

Is it complete? **No.** The documentation is complete and every review is closed. The compiler is three slices into a six-slice re-sync, housekeeping has not started, and the identity decisions await ratification. Row by row (as of 2026-09-23):

| Unit | State | Remaining | Blocked on |
|---|---|---|---|
| `rdf-sparql-patterns-phase` Slices 1–2 (guide, `ontology/persistence`, `tools/persistence`) | ✅ Complete | — | — |
| `rdf-sparql-patterns-remediation` (first review of the guide) | ✅ Complete, closed | nothing; deferred items handed to the units below | — |
| `iri-patterns-post-3866b21-remediation` (second review, plus template alignment) | ✅ Complete, closed | nothing; follow-ons listed in its [status](status/iri-patterns-post-3866b21-remediation.md#is-this-unit-complete) | — |
| `persistence-compiler-iri-sync` (compiler catches up with the vocabulary) | 🚧 Slices 1–4 done (Slice 4 human-validated 2026-09-25). Slice 5 implemented 2026-09-25, not yet run | Human review/test-run of Slice 5, Slice 6 close-out. Gap table in its [status](status/persistence-compiler-iri-sync.md#is-this-unit-complete) | — |
| `rdf-sparql-patterns-phase` Slice 3 / `platform-housekeeping` | ⏳ Not started | the whole slice, including the retention and audit changes noted in its plan | — |
| P0.1.3: ADR-A82 and `iri-identity-patterns.md` | 📝 Drafted and revised, Proposed | human ratification, and the point 5 amendment proposed by `identity-minting` | Phase 0 ratification pass |
| `identity-minting` (minting recipes, conformance vectors, standalone Java and Python libraries, `dal:claimsConstraint`) | 🚧 M0–M3 of M0–M4 done: [plan](plans/identity-minting.md), [status](status/identity-minting.md) | M4 specification and human walk-through. One open question: default-ignorables in the upper- and lowercase pipelines | — |
| `toolchain-jdk25-python314` (JDK 25 LTS, Python 3.14, Unicode 16.0) | ✅ Complete: [plan](plans/toolchain-jdk25-python314.md), [status](status/toolchain-jdk25-python314.md) | — | — |
| `identity-minting-shared-core` (one Rust minting engine, WebAssembly-hosted in each runtime) | 🅿️ [Sketch](sketches/identity-minting-shared-core.md), deferred | revisit after `persistence-compiler-iri-sync` Slice 6. M2 and M3 proceed with native libraries | `persistence-compiler-iri-sync` Slice 6 first (priority) |

## 1. RDF/SPARQL Implementation Patterns and Persistence Compiler

| Field | Value |
|-------|-------|
| **Status** | ✅ Slices 1 and 2 complete; compiler re-sync with the extended vocabulary in progress (unit 1a); Slice 3 not started |
| **Unit ID** | `rdf-sparql-patterns-phase` |
| **Sketch** | [persistence-profile-substrate.md](sketches/persistence-profile-substrate.md) |
| **Plan** | [rdf-sparql-patterns-phase-plan.md](plans/rdf-sparql-patterns-phase-plan.md) |
| **Status Record** | [rdf-sparql-patterns-status.md](status/rdf-sparql-patterns-status.md) |
| **Architecture Guide** | [docs/architecture/rdf-sparql-patterns-guide.md](../architecture/rdf-sparql-patterns-guide.md) (Slice 1) |
| **ADRs** | ADR-A78 (persistence substrate), ADR-A79 (compiler), ADR-A80 (housekeeping) — all Accepted |
| **Implementation** | `ontology/persistence` (Turtle vocabulary + SHACL shapes + 22 example fixtures, extended 2026-09-23), `tools/persistence` (Python compiler, 570 tests passing; privacy and claim-scheme profiles not yet wired, see unit 1a) |
| **Validation Pack** | [persistence-substrate-and-compiler.md](validation/persistence-substrate-and-compiler.md) |
| **Sync gap** | See unit 1a below |
| **Earlier review** | `rdf-sparql-patterns-remediation`: [plan](plans/rdf-sparql-patterns-remediation.md), [status](status/rdf-sparql-patterns-remediation.md) — ✅ complete, closed |

### Slice Completion Status
| Slice | Deliverable | Status |
|-------|------------|--------|
| **1** | [rdf-sparql-patterns-guide.md](../architecture/rdf-sparql-patterns-guide.md) — consolidated 4 source notes into authoritative reference (30 chapters covering K/O/C/T/QP patterns) | ✅ Complete |
| **2** | `ontology/persistence` + `tools/persistence` compiler + policy enforcement + doc deltas | ✅ Complete |
| **3** | `platform/housekeeping` module (scaffolding, not execution) | 🚧 Planned, not started |

### Key Findings
- **Target model discovery:** Classes need paired `(class, deployment)` targets within each graph scope, added `dal:coversClass` property
- **SPARQL validity bugs fixed:** Property paths invalid in DELETE/INSERT blocks; payload triples need a text slot instead of SPARQL variables (originally `#PAYLOAD#`, since `persistence-compiler-iri-sync` Slice 2 the Mustache slot `{{{payloadTriples}}}`)
- **Mustache parsing gotcha:** Comments cannot contain bare `}}` without breaking parsing
- **pyshacl semantics:** `allow_warnings=True` needed for non-blocking `sh:Warning` severity

### Blocks
- Housekeeping module first cut (Slice 3, depends on Slice 2 compiler)

Epic decomposition into phase plans is **no longer blocked**: the required Phase 2 (P2.1/P2.3/P2.4) revision integrating this compiler is complete — see Part II, §6.

## 1a. Persistence Compiler / IRI-Patterns Sync (new, tracks the 2026-09-23 gap)

| Field | Value |
|-------|-------|
| **Status** | ✅ Slices 1–4 complete (Slice 4 human-validated 2026-09-25: 669 passed, adversarial probes checked). 🚧 Slice 5 implemented 2026-09-25 (autonomous mode), not yet run in this sandbox. Slice 6 not started |
| **Unit ID** | `persistence-compiler-iri-sync` |
| **Sketch (gap analysis)** | [persistence-compiler-iri-sync.md](sketches/persistence-compiler-iri-sync.md) |
| **Plan** | [persistence-compiler-iri-sync.md](plans/persistence-compiler-iri-sync.md) |
| **Status Record** | [persistence-compiler-iri-sync.md](status/persistence-compiler-iri-sync.md) |
| **Validation Packs** | [Slice 1](validation/persistence-compiler-iri-sync-slice-1.md), [Slice 2](validation/persistence-compiler-iri-sync-slice-2.md), [Slice 3](validation/persistence-compiler-iri-sync-slice-3.md), [Slice 4](validation/persistence-compiler-iri-sync-slice-4.md), [Slice 5](validation/persistence-compiler-iri-sync-slice-5.md) |
| **Triggering commit** | `c276afb` "[iri-patterns] remediate docs and update persistence ontology vocabulary" |

### Gap summary
Three new profile dimensions (`dal:IdentityProfile`, `dal:EpochProfile`, `dal:PrivacyProfile`), extensions to six existing ones, and eight new SHACL shapes were added to `ontology/persistence`, none consumed by `tools/persistence`. One finding (G1) is a live correctness issue, not just missing coverage: the compiler's CAS/tombstone templates generate the epoch-guard shape the vocabulary now documents as unsafe (`dal:RowLevelGuardOnly`), unconditionally, with no way to configure the safe `dal:DatasetLevelGuard` alternative.

### Slices
1. **✅ Complete, 290/290 passing.** Dataset-level epoch guard — `dal:epochGuardScope` resolvable, `dal:DatasetLevelGuard` template variant for the three named write shapes, warning diagnostic fires even on the platform baseline default. See the [VP](validation/persistence-compiler-iri-sync-slice-1.md).
2. **✅ Complete, 526/526 passing.** Extension properties resolved one dimension each, baseline defaults, two refusals and six warnings mirroring the SHACL shapes, `dal:PreCreatedRow` emits `bootstrap-version-row`, request-time values as Mustache slots. See the [VP](validation/persistence-compiler-iri-sync-slice-2.md).
3. **✅ Complete, 570/570 passing.** Identity resolved per resource role (`identity:<Role>`), winning profile node as a unit, emitted to the compiled profile, five refusals and one warning. See the [VP](validation/persistence-compiler-iri-sync-slice-3.md).
4. **✅ Complete, human-validated 2026-09-25 (669 passed, adversarial probes checked).** Privacy/erasure profile (`dal:privacyClass`/`dal:erasureStrategy`/`dal:erasurePrecedence`/`dal:perSubjectScoped`, one dimension each) plus the G3 remainder (`dal:epochAuthority` promoted to its own dimension, carrying the remaining restore-surface properties as its extras), two refusals mirroring `dal:PersonalDataRequiresErasureShape` and `dal:PersonalDataReceiptCompatibilityShape`, and Worked example 4's privacy profile now resolving and emitting cleanly. See the [VP](validation/persistence-compiler-iri-sync-slice-4.md).
5. **🚧 Implemented 2026-09-25, autonomous mode, not yet run.** Uniqueness `dal:onViolation` selects a reconciler operation, never the guarded write itself (decision 1, Option A — guide §7.5, not §6): `key-claim-duplicate-audit` (`dal:Reject`, the default), `key-claim-merge-rewrite` (`dal:Merge`, with `MergeRelationRequired`), `key-claim-quarantine` (`dal:Quarantine`). `dal:ClaimScheme` `dal:Dual` rotation selects `key-claim-write-dual.mustache`. The registry-token digest-scheme relaxation (found in `identity-minting` M3) is also folded in: `dal:DigestSchemeRequiredShape` now exempts `dal:PositionDerivedEvent` + `dal:RegistryTokenDerivation` only. `ontology/persistence` bumped PATCH, 0.2.0 → 0.2.1. See the [VP](validation/persistence-compiler-iri-sync-slice-5.md) and the status record's Blockers section.
6. ⏳ Documentation close-out (final pass; the cross-document updates it listed were done early on 2026-09-23)

## 1b. IRI and RDF Patterns, Post-3866b21 Remediation

| Field | Value |
|-------|-------|
| **Status** | ✅ Documentation remediation complete, and `tools/persistence` templates aligned (2026-09-23), 471/471 tests passing |
| **Unit ID** | `iri-patterns-post-3866b21-remediation` |
| **Review** | [iri-patterns-post-3866b21-review.md](review/iri-patterns-post-3866b21-review.md) |
| **Status Record** | [iri-patterns-post-3866b21-remediation.md](status/iri-patterns-post-3866b21-remediation.md) |
| **Documents** | [rdf-sparql-patterns-guide.md](../architecture/rdf-sparql-patterns-guide.md) (Appendix D.3), [iri-identity-patterns.md](../architecture/iri-identity-patterns.md), [iri-policy.md](../architecture/iri-policy.md) (body removed) |

All 7 critical (A), 14 major (B), 9 safety (C), 7 cross-document (D) and 10 editorial (E) findings are fixed in the documents. The main design choices (lazy epoch rebase, request digest, pinned heads, row-driven gap audit, `NFKC_Casefold`) are recorded once in the status record. The compiler templates now generate the corrected write shapes and audits. A pre-existing bug that wrote key claims into the txn graph is fixed.

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
- SWRL/OWL-reasoner validation needs `platform/reasoning-testkit` (new, proposed by the plan above, ADR-A83, renumbered from A81 to avoid the collision with the Control Plane ADR) — a shared, test-scope-only Maven module wrapping an OWL/SWRL reasoner and, if a second consumer emerges, Drools (Apache-2.0, no licence concern), consumed by Python test suites via a CLI subprocess rather than a direct dependency. Explicitly never a runtime dependency of any product package.
- Licence check complete (2026-09-23): Openllet is **AGPL-3.0** (inherited from Pellet, not Apache-2.0 as an earlier draft wrongly stated), usable only because the module's isolation design (test-scope + subprocess CLI, never linked or distributed) avoids creating a combined/derivative work. **HermiT (LGPL-3.0)** is a lower-risk alternative but supports DL-safe SWRL rules only — open question is whether ADR-A24's SWRL subset is DL-safe. See [eligibility-compiler.md](plans/eligibility-compiler.md) §B.4

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
- **Pattern K (uniqueness)** ↔ `dal:UniquenessConstraint`, cross-referenced at P0.1.3 through the configurable minting and identity profiles described by ADR-A82.
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

### IRI and Identity Patterns — Proposed (2026-09-23)

The unratified universal IRI policy in ADR-A51 was superseded by [ADR-A82](../architecture/decisions/ADR-A82-framework-neutral-identity-pattern-selection.md). The new [IRI and Identity Patterns](../architecture/iri-identity-patterns.md) guide treats entity, aggregate, component, lineage, content-revision, graph-locator, key-claim, and event-occurrence identities as independently configurable patterns. It crosswalks those choices to the K/O/C/T/QP RDF and SPARQL patterns and specifies the future `dal:` identity-profile vocabulary boundary. The `dal:IdentityProfile` vocabulary is specified in `ontology/persistence`, and the compiler resolves it per resource role (`persistence-compiler-iri-sync` Slice 3, complete). The guide and ADR-A82 were revised on 2026-09-23 by `iri-patterns-post-3866b21-remediation` and await ratification (P0.1.3). `iri-policy.md` is now a short historical record.

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
| Foundation migration (`srf:DerivedArtefact`) | ✅ Done (ADR-A92) | [Outstanding items §3.2](status/surface-outstanding-items.md#32-adr-a01-convention-conflict--closed) |
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
| **Depends On** | `tools/persistence` compiler (Slice 2) ✅ |

### Deliverables (planned)
- `platform/housekeeping` module scaffolding (not execution)
- Contracts and configuration model
- Generated queries per ADR-A80: the row-driven gap scan, the txn-cardinality fork audit and the two receipt-side duplicate audits
- The retention job's own write queries: advance the low-water mark, carry live heads into the pinned-head graph, prefix-only drops (guide §24.2). See the plan's Slice 3 "Changes since this slice was scoped" note

### Blockers
- None. The compiler dependency is met

---

# Vocabulary Scoped and Temporal Binding — Closed (2026-09-25)

| Field | Value |
|-------|-------|
| **Status** | ✅ Closed. Vocabulary suite, Surface, and Eligibility consumers all verified green. ADR-A85 Accepted |
| **Unit ID** | `vocabulary-temporal-binding` |
| **Trigger** | `65ac4a85e11cc1f8616e3e0c24efd59bf4ca410d` (`[vocabulary] time-bound binding`) |
| **Sketch** | [vocabulary-temporal-binding.md](sketches/vocabulary-temporal-binding.md) |
| **Plan** | [vocabulary-temporal-fixes.md](plans/vocabulary-temporal-fixes.md) |
| **Status Record** | [vocabulary-temporal-binding.md](status/vocabulary-temporal-binding.md) |
| **Validation Pack** | [vocabulary-temporal-binding.md](validation/vocabulary-temporal-binding.md) |
| **ADR** | [ADR-A85](../architecture/decisions/ADR-A85-vocabulary-scoped-temporal-binding-resolution.md), Accepted |

The conformance package (12 fixtures, populated Vocabulary SHACL files, a
deterministic reference resolver) is authored and verified: `mise run
check:vocabulary` passes 14/14. Both real consumers now resolve scoped
bindings instead of reading `voc:boundScheme` directly: Surface's compiler
calls the resolver in `enumerate_population`, and Eligibility's
`HierarchyWellFoundednessShape` checks every scheme a contract could resolve
to. `python -m unittest surface.test_surface -q` passes 62/62 (including a new
scoped-binding fixture and test), and `mise run check:python-root` passes
77/77 plus Phase 8 conformance. See the status record for exact findings.

### Slices

1. ADR-A85, architecture mirror, fixture and traceability skeleton — done
2. Examples plus structural and SHACL-SPARQL validation — done, verified
3. Reference resolver and deterministic test suite — done, verified
4. Consumer/provenance checks and documentation close-out — done, verified (Surface and Eligibility both resolve scoped bindings)

### Closure cross-reference (2026-09-25)

A cross-reference of this unit's Surface/Eligibility integration against
[docs/architecture/rdf-sparql-patterns-guide.md](../architecture/rdf-sparql-patterns-guide.md)
found the work internally consistent, with four follow-on hardening items and
one accepted terminology note. None block closure. See
[Vocabulary Consumer Hardening](#vocabulary-consumer-hardening--planned-2026-09-25)
below.

## 8.5 Vocabulary Conformance — Closed

See the unit record above. This heading is intentionally a navigation anchor
between active platform work and archived material.

---

# Ontology Semantic Versioning — Implemented, ADR pending ratification (2026-09-25)

| Field | Value |
|-------|-------|
| **Status** | ✅ Slices 1-4 implemented (human directed autonomous implementation, 2026-09-25). ADR-A86 remains Proposed pending ratification |
| **Unit ID** | `ontology-semantic-versioning` |
| **Trigger** | Human request, 2026-09-25 — adopt SemVer 2.0.0 for ontology documents |
| **Sketch** | [ontology-semantic-versioning.md](sketches/ontology-semantic-versioning.md) |
| **Plan** | [ontology-semantic-versioning.md](plans/ontology-semantic-versioning.md) |
| **Status Record** | [ontology-semantic-versioning.md](status/ontology-semantic-versioning.md) |
| **Policy** | [ontology-versioning-policy.md](../architecture/ontology-versioning-policy.md) |
| **ADR** | [ADR-A86](../architecture/decisions/ADR-A86-ontology-semantic-versioning.md), Proposed |

Every `owl:Ontology` document under `ontology/` carried an ungoverned
`owl:versionIRI`, or none, with no documented rule for when it changed. The
sketch's inventory found four distinct problems: no bump rule beyond one ad
hoc note in `vocabulary/README.md`; an already-inconsistent versioning unit
(`spec/*.ttl` vs `vocab/*.ttl` independently versioned and already drifted);
two ontologies (MORK, SPC) with no version identity at all; and one
(`applied/insurance/contract.ttl`) with two disagreeing version signals and a
namespace base outside the `lattice/` tree. ADR-A86 adopted SemVer 2.0.0 per
`owl:Ontology` document, a MAJOR/MINOR/PATCH mapping table, a one-time
baseline reset to `0.2.0`, and a narrow "changed but not bumped" check.

### Slices

1. ADR-A86, sketch, plan, status record, ADR-index and INDEX.md entries — done
2. Developer/agent guidance (`ontology-versioning-policy.md` + `CONTRIBUTING.md`/`ontology-architecture.md` cross-references) — done
3. Baseline reset (every in-scope document to `0.2.0`, `lattice/` base-URI normalisation, full `owl:imports` cascade, one discovered non-ontology importer fixed: `tools/surface`'s `SURFACE_ONTOLOGY` constant) — done, with one recorded deviation (README⇄spec extraction was not re-run; see status record)
4. Narrow "changed but not bumped" enforcement tooling (`tools/ontology_version_check.py`, `mise run check:ontology-versioning`) — done, validated by mutation probe

**Discovered while implementing, not yet acted on:** `tools/literate_extract.py --check`
does not currently pass for any of the seven core literate-spec layers
(pre-existing README⇄spec drift, unrelated to this unit). Recorded in the
policy document as a candidate future remediation unit.

## 8.6 Ontology Semantic Versioning — Implemented, ADR pending ratification

See the unit record above. This heading is intentionally a navigation anchor
between active platform work and archived material.

# Vocabulary Consumer Hardening — Implemented (2026-09-25)

| Field | Value |
|-------|-------|
| **Status** | ✅ All 4 findings implemented (human directed "proceed with the attached plan", 2026-09-25). Not yet executed in this sandbox (no rdflib) — authored and statically verified, hand-off for `mise run check:vocabulary` / `python -m unittest surface.test_surface` |
| **Unit ID** | `temporal-binding-consumer-hardening` |
| **Trigger** | Cross-reference of `vocabulary-temporal-binding`'s Surface/Eligibility integration against [rdf-sparql-patterns-guide.md](../architecture/rdf-sparql-patterns-guide.md) |
| **Plan** | [temporal-binding-consumer-hardening.md](plans/temporal-binding-consumer-hardening.md) |
| **Status Record** | [temporal-binding-consumer-hardening.md](status/temporal-binding-consumer-hardening.md) |

Four items carried forward from the `vocabulary-temporal-binding` closure
review, all implemented:

1. **Finding 3 (docs).** `vvp:resolvedAt` clarified as a valid-time "as-of"
   point, not a transaction-time "recorded when" timestamp, in
   `ontology/vocabulary/shapes/constraints.ttl`, `tools/vocabulary/README.md`,
   and the validation pack.
2. **Finding 4 (test).** `tools/vocabulary/tests/test_architecture.py`: no
   module under `tools/vocabulary/src/vocabulary/` may call a wall-clock
   function, mirroring `tools/persistence`. Mutation-probed in this session
   (fails when a `datetime.now()` call is introduced, passes otherwise).
3. **Finding 1, Option B (compiler + CLI + law text).** `tools/surface`'s CLI
   (`command_compile`/`command_check`/`command_parity`/`command_mork`) now
   refuses to default `produced_at` to wall-clock time for any contract whose
   population could resolve a caller-scoped `voc:SchemeBinding`
   (`contracts_needing_explicit_resolution_time` in `cli.py`); `srf:R1`'s law
   text and `compile.py`'s module docstring updated to state the
   determinism guarantee precisely. The parity command's `--shared-corpus`
   path is not guarded (deliberate non-coverage; no scoped fixture is in that
   corpus today).
4. **Finding 2 (ontology + compiler + manifest).** New `srf:resolvedAt`,
   `srf:resolvedBindingScope`, `srf:resolvedBinding`, `srf:resolvedViaFallback`
   on `srf:ReadSetEntry`, populated on every `BoundSchemeSource` entry via a
   `vocabulary.Resolution` object now threaded through `enumerate_population`
   instead of discarded; a new `srf:BoundSchemeSourceResolutionRecordedShape`
   SHACL-SPARQL check; new tests proving the recorded trace changes when the
   caller's context does.

Finding 5 (terminology overload of "scope") remains accepted, no action.

# Applied Ontology Readiness — AOR-2 to AOR-9 committed, AOR-12/13 implemented (2026-09-25)

| Field | Value |
|-------|-------|
| **Status** | 🚧 AOR-2 to AOR-9 committed. AOR-3b, AOR-12, AOR-13 implemented, uncommitted. AOR-10/11 wait on ADR-A83 and a path-encoding decision. AOR-14 to AOR-17 wait on ADRs A-93 to A-96 |
| **Unit ID** | `applied-ontology-readiness` |
| **Trigger** | Human request, 2026-09-25 — close the gaps an applied (domain) ontology meets when built on LATTICE |
| **Sketch** | [applied-ontology-readiness.md](sketches/applied-ontology-readiness.md) |
| **Plan** | [applied-ontology-readiness.md](plans/applied-ontology-readiness.md) |
| **Status Record** | [applied-ontology-readiness.md](status/applied-ontology-readiness.md) |
| **Review** | [applied-ontology-readiness-review.md](review/applied-ontology-readiness-review.md) |
| **ADRs** | [A-87](../architecture/decisions/ADR-A87-eligibility-concept-inclusion-and-exclusion.md), [A-88](../architecture/decisions/ADR-A88-ontology-import-resolution-for-consumers.md), [A-89](../architecture/decisions/ADR-A89-eligibility-ir-concept-conditions-and-profile-aggregation.md), [A-90](../architecture/decisions/ADR-A90-eligibility-design-time-owl-class-backend.md), [A-91](../architecture/decisions/ADR-A91-eligibility-candidate-evidence-binding.md), [A-92](../architecture/decisions/ADR-A92-derived-artefact-contract-and-prov-o-alignment.md), and a proposed [A-86 addendum](../architecture/decisions/ADR-A86-ontology-semantic-versioning.md#proposed-addendum-2026-09-25-guarantees-consumers-rely-on), all Proposed |

Thirteen gaps (AO1 to AO13) that any applied ontology meets: Eligibility
examples that warn or violate since `9a12da4`, no reproducible way to load
LATTICE's import closure, versioning guarantees not enforced in CI, compilers
limited to interval conditions and to candidates held on questions, no OWL
backend for design-time checks, provenance not aligned with PROV-O, and four
substrate extensions (derived rates, calendar binding, per-unit alternative
bounds, one obligation in several provisions).

### Slices

1. Phase A, consumable baseline: AOR-1 governance records — done. AOR-2 examples and the declaration warning, AOR-3 versioning guarantees, AOR-4 import catalog — implemented, [VPs](validation/applied-ontology-readiness-aor-2.md)
2. Phase B, executable coverage: AOR-5 to AOR-9 (concept conditions, hierarchical match, SHACL and SWRL, diagnostics, profile aggregation, conformance corpus, evidence bindings) — implemented. AOR-10 and AOR-11 (OWL backend) — paused on the ADR-A83 harness and an encoding decision
3. Phase C, substrate extensions: AOR-12 (Foundation derived-artefact contract) and AOR-13 (Executable to PROV-O) — implemented. AOR-14 to AOR-17 — ADRs A-93 to A-96 drafted

# Documentation Link Repair — Pending (2026-09-25)

| Field | Value |
|-------|-------|
| **Status** | ⏳ Pending. Not started |
| **Unit ID** | `documentation-link-repair` |
| **Plan** | [documentation-link-repair.md](plans/documentation-link-repair.md) |
| **Status Record** | [documentation-link-repair.md](status/documentation-link-repair.md) |

`mise run topology:links` reports 419 broken links (340 distinct). 290 are in
the ignored Jekyll output `docs/_site/`, which the checker should not scan.
The other 50 are wrong relative depths, moved targets, and targets that no
longer exist. Five slices, about 180k tokens.

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

### Vocabulary Binding
- Sketch: [vocabulary-temporal-binding.md](sketches/vocabulary-temporal-binding.md)
- Plan: [vocabulary-temporal-fixes.md](plans/vocabulary-temporal-fixes.md)
- Status: [vocabulary-temporal-binding.md](status/vocabulary-temporal-binding.md)
- Validation pack: [vocabulary-temporal-binding.md](validation/vocabulary-temporal-binding.md)
- Implementation: `ontology/vocabulary/shapes/`, `ontology/vocabulary/examples/` (12 fixtures), `tools/vocabulary/` (reference resolver + pytest suite) — verified, 14/14 tests passing
- ADR: [A85](../architecture/decisions/ADR-A85-vocabulary-scoped-temporal-binding-resolution.md), Accepted
- Follow-on: [temporal-binding-consumer-hardening.md](plans/temporal-binding-consumer-hardening.md) — implemented (2026-09-25), see its own INDEX entry

### Ontology Semantic Versioning
- Sketch: [ontology-semantic-versioning.md](sketches/ontology-semantic-versioning.md)
- Plan: [ontology-semantic-versioning.md](plans/ontology-semantic-versioning.md)
- Status: [ontology-semantic-versioning.md](status/ontology-semantic-versioning.md)
- Policy: [ontology-versioning-policy.md](../architecture/ontology-versioning-policy.md)
- ADR: [A86](../architecture/decisions/ADR-A86-ontology-semantic-versioning.md), Proposed

### Applied Ontology Readiness
- Sketch: [applied-ontology-readiness.md](sketches/applied-ontology-readiness.md)
- Plan: [applied-ontology-readiness.md](plans/applied-ontology-readiness.md)
- Status: [applied-ontology-readiness.md](status/applied-ontology-readiness.md)
- ADRs: A87 to A92 and the A86 addendum, Proposed
- Implementation: `docs/architecture/ontology-versioning-policy.md`, `tools/ontology_version_check.py` (`mise run check:ontology-versioning`), every in-scope `.ttl` document reset to `0.2.0` — done, ADR ratification still pending

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
2. Persistence compiler (Slice 2) — 570 tests passing after the 2026-09-23 sync and remediation work; the sync itself is still in progress (see "In Progress")
3. LLM training / MTP generation — 346 tests passing
4. Repository topology (ADR-A77)
5. MORK eligibility compiler (awaiting runtime validation, not handoff)
6. Surface Projection Phases 0–8 — 61/61 Surface tests, 15/15 MORK backends, 7/8 verification items
7. Phase 0-6 handoff documents

### 🚧 In Progress
1. Epic decomposition (Phase 0-9 plans)
2. Persistence compiler / IRI-patterns sync (`persistence-compiler-iri-sync`) — Slices 1–3 of 6 done, nothing blocked
3. Housekeeping first cut (Slice 3, scoped but not started)
4. Surface MORK Phase 8 verification (SWRL reasoner integration, 1/8 items pending)

### ⏳ Planned
1. Housekeeping execution (tied to future store SPI)
2. Governance surfaces backend integration (Phase 2/5)
3. Phase 0-9 implementation
4. Surface MORK Phase 9 — Migration guides and phased rollout
5. Surface MORK Phase 10 — Scale and performance optimization
6. Vocabulary scoped and temporal binding conformance — closed 2026-09-25
7. Vocabulary consumer hardening (`temporal-binding-consumer-hardening`) — implemented, not yet executed in this sandbox
8. Ontology semantic versioning (ADR-A86) — implemented; ADR ratification pending
9. Applied ontology readiness (`applied-ontology-readiness`) — AOR-2 to AOR-9 committed, AOR-12/13 implemented, review requested
10. Documentation link repair (`documentation-link-repair`) — pending

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
| **Housekeeping first cut (Slice 3)** | Scaffold `platform/housekeeping` module | Compiler ready; module contracts defined in ADR-A80; job duties extended by the 2026-09-23 guide remediation | Author Slice 3 (housekeeping scaffolding) |
| **Store SPI** | Design runtime SPI for query execution | Compiler produces templates; runtime binding TBD | Separate epic/phase after housekeeping |
| **MTP backend integration (Phase 7)** | Runtime API for LLM curriculum delivery | MTP generation complete; needs HTTP endpoint | Post-Phase-6 work |
| **Vocabulary temporal binding conformance** | Examples, SHACL, resolver, consumer provenance checks | Closed 2026-09-25: executed and verified, ADR-A85 Accepted | None. Follow-on hardening tracked as `temporal-binding-consumer-hardening` |
| **Vocabulary consumer hardening** | `produced_at`/hash conflation, missing resolution trace, `vvp:resolvedAt` naming, vocabulary architecture test | Implemented 2026-09-25 (all 4 findings); not yet executed in this sandbox (no rdflib) | Run `mise run check:vocabulary` and `python -m unittest surface.test_surface -v`, then close out |
| **Ontology semantic versioning** | ADR-A86, versioning-policy doc, baseline reset, narrow enforcement check | Implemented (2026-09-25): policy doc, `0.2.0` baseline reset across 29 ontology documents, `check:ontology-versioning` tooling | Ratify ADR-A86; decide whether the discovered `literate_extract.py` drift becomes its own unit |
| **Applied ontology readiness** | ADRs A-87 to A-92, A-86 addendum, 17 slices in three phases | Gaps any applied ontology meets when built on LATTICE (loading, examples, compilation, provenance, substrate extensions) | Ratify ADR-A83 and A-93 to A-96, choose the OWL path encoding (ADR-A90 open question) |

---

# Part VI — Traceability and Validation

## Validation Packs (VPACKS)
- [persistence-substrate-and-compiler.md](validation/persistence-substrate-and-compiler.md) — RDF patterns Slice 2
- [persistence-compiler-iri-sync-slice-1.md](validation/persistence-compiler-iri-sync-slice-1.md) — compiler sync Slice 1
- [persistence-compiler-iri-sync-slice-2.md](validation/persistence-compiler-iri-sync-slice-2.md) — compiler sync Slice 2
- [persistence-compiler-iri-sync-slice-3.md](validation/persistence-compiler-iri-sync-slice-3.md) — compiler sync Slice 3
- [applied-ontology-readiness-aor-2.md](validation/applied-ontology-readiness-aor-2.md) to [aor-9](validation/applied-ontology-readiness-aor-9.md), [aor-3b](validation/applied-ontology-readiness-aor-3b.md), [aor-12](validation/applied-ontology-readiness-aor-12.md), [aor-13](validation/applied-ontology-readiness-aor-13.md) — applied ontology readiness
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
| MORK compiler backends | 74 passing (2026-09-25) | `mise run check:mork-compilers` |
| LLM/MTP | 346 passing | `mise run check:mtp` |
| Persistence compiler | 669 passing (confirmed 2026-09-25, after Slice 4). Slice 5 adds more, not yet run | `mise run check:persistence` |
| Ontology tools (catalog, versioning, Eligibility examples, PROV-O alignment) | 35 passing | `mise run check:ontology-catalog` |
| Ontology versioning | tool run | `mise run check:ontology-versioning` |

---

# Part VII — Open Questions (Blocking or Deferred)

1. **Store SPI design** — How does runtime connect compiled templates to live backend? (Deferred to separate SPI phase. The caller contract it must honour is now documented in `tools/persistence/README.md`, "Using the generated SPARQL directly")
2. ~~Phase 0.2–0.4 walking-skeleton pattern integration~~ — done (2026-09-22): Part 4 of the epic plan carries the Pattern C/T/K/O ↔ `dal:` cross-references, new slice P0.3.9, and guardrail G11. See Part II, §6 and Part V.
3. **MTP backend integration** — What HTTP API shape for LLM curriculum consumption? (Phase 7, post-Phase-6)
4. **Housekeeping execution** — When is the housekeeping component itself executed (real-time vs. batch)? (ADR-A80 defers to future phase)
5. **Surface MORK Phase 9 decomposition** — How to slice migration guides and phased rollout? (Blocking Phase 9, needs decomposition after Phase 8 SWRL verification)
6. ~~**Foundation migration for `srf:DerivedArtefact`**~~ — resolved 2026-09-25 by ADR-A92 (AOR-12). Original question: Should profile identity be a Foundation concept or Surface-only? (Blocking profile identity assertion in Surface; see [surface-outstanding-items.md](status/surface-outstanding-items.md#33-profile-identity-assertion--blocked)). Proposed resolution: [ADR-A92](../architecture/decisions/ADR-A92-derived-artefact-contract-and-prov-o-alignment.md)
7. **MORK toolchain join assumptions** — Pre-production verification checklist for join operations in mapping compilation (see [surface-outstanding-items.md](status/surface-outstanding-items.md#34-mork-toolchain-join-assumptions--needed))

---

## Document Maintenance

This index is updated when:
- A new sketch is commissioned
- A plan is created or revised
- A status record is completed
- A validation pack is accepted
- A unit transitions between status states (🚧 → ✅, etc.)

**Last updated:** 2026-09-23 — persistence and IRI patterns change package: cross-document disposition pass  
**Last reviewed:** 2026-09-22  
**Next review:** Upon Phase 8 SWRL verification completion and Phase 9 decomposition
