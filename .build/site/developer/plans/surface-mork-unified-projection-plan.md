<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Surface-MORK Unified Projection Program — Plan

**Unit:** `surface-mork-unified-projection`  
**Type:** Program/Epic  
**Status:** Phases 0–8 complete; Phases 9–10 planned  
**Last updated:** 2026-09-22  
**Owner:** Surface and MORK maintainers

---

## Executive Summary

This plan adopts a single top-level authoring approach for projection in LATTICE:

- Authors write high-level **Surface contracts** (Promotion, Index, Projection)
- System lowers those contracts **deterministically into MORK mappings**
- MORK remains **provenance-rich, reviewable, versioned** machine-facing mapping graph
- **Compiler backends** generate executable artefacts (SPARQL, SHACL, SWRL, RML, native IR)

This avoids a third mapping language while preserving MORK's machine contract for governance, provenance, and review.

**Status:** Phases 0–8 are complete and verified ✅ (see [surface-mork-unified-projection.md](status/surface-mork-unified-projection.md)). Phases 9–10 are planned, not started.

---

## Architecture

### Core Pipeline

```
Domain and substrate declarations
        ↓
Surface contracts (Promotion, Index, Projection)
        ↓
Surface validator and normaliser
        ↓
Surface-to-MORK lowering
        ↓
Validated MORK graph
        ↓
Target compilers
  - MORK to SPARQL
  - MORK to SHACL
  - MORK to SWRL
  - MORK to RML
  - MORK to native IR
        ↓
Generated artefacts (with provenance, governance, version records)
```

### Responsibility Split

- **Surface:** authoring contract, semantic role binding, projection intent, profile and policy declarations
- **MORK:** machine mapping graph, dependencies, parameter bindings, compiler-ready shapes and rules, provenance and governance
- **Compilers:** deterministic lowering to executable targets, backend-specific constraints and diagnostics

---

## Phases (1-10 Roadmap)

### Phase 0 — Architecture lock and ADR updates
**Status:** ✅ Complete  
**Scope:**
- ADR set A16–A28 (Surface Projection and MORK governance)
- Glossary updates for Projection subsystem terminology
- Architecture decisions signed off

### Phase 1 — Surface Projection specification
**Status:** ✅ Complete  
**Scope:**
- `srf:ProjectionContract` vocabulary and shapes
- Projection role-binding resources
- Projection policy controls
- Laws for projection fidelity and signature scope composition
- Examples and defect fixtures

### Phase 2 — Surface compiler refactor and entailment policy
**Status:** ✅ Complete  
**Scope:**
- Compiler pipeline stages
- Normalisation stage for all contract kinds
- Lowering stage interfaces
- Deterministic minting utilities
- Entailment-regime handling (NoEntailment, reasoned modes)

### Phase 3 — Surface-to-MORK lowering engine
**Status:** ✅ Complete  
**Scope:**
- Lowering rules from Projection contracts to MORK patterns
- Lowering support for Promotion/Index to MORK (where configured)
- Parameter bindings and targeting specs
- Mapping provenance including source contract linkage
- `tools/surface/lowering.py` implementation (61/61 tests passing)

### Phase 4 — MORK governance and versioning enhancements
**Status:** ✅ Complete  
**Scope:**
- Foundation import in MORK ontology
- Governance state and review-state constraints
- Mapping set versioning and supersession model
- Effective time constraints for mapping applicability
- Migration docs for existing MORK assets

### Phase 5 — Compiler family implementation
**Status:** ✅ Complete  
**Scope:**
- MORK to SPARQL compiler (✅ complete, tested)
- MORK to SHACL compiler (✅ complete, tested)
- MORK to SWRL compiler (✅ complete, generated)
- Shared compiler core (✅ parameter resolution, precedence derivation)
- MORK to native IR compiler (deferred)
- Result: 15/15 focused MORK compiler tests passing

### Phase 6 — Eligibility tranche
**Status:** ✅ Complete (IntervalContainment strategy only)  
**Scope:**
- Executable IR for Eligibility interval semantics (✅ IntervalContainment)
- Lowering templates for interval containment Surface to MORK (✅ complete)
- SPARQL decision backend (✅ complete, verified)
- SHACL readiness backend (✅ complete, constraints shapes passing)
- SWRL classification backend (✅ generated, awaiting reasoner verification)

**Not yet built:**
- Profile-level aggregate artefacts (`AllRequired`/`AnySufficient`)
- Executable Projection Contract (`exp:`) domain-binding layer
- Runtime result tracking (`exe:EvaluationRun`, `exe:ConditionResult`)
- Other eligibility strategies (ExactCondition, SetMembership, Wildcard)

### Phase 7 — Provenance and invalidation hardening
**Status:** ✅ Complete (depth-1 scope)  
**Scope:**
- Provenance chain from result to source contracts (✅ complete)
- Read-set capture across Surface/MORK/generated artefacts (✅ complete)
- Invalidation policy for graph/profile/mapping changes (✅ complete)
- Regeneration planner for minimal rebuild (✅ tools/surface/invalidation.py)
- Canonicalisation cutover runbook (✅ srf-canon/1 → srf-canon/2, complete)

**Deferred:**
- Deeper-stack freshness tracking
- Cycle handling on read-set DAG
- Measured impact cost for stacked regeneration

### Phase 8 — Conformance and parity framework
**Status:** ✅ Complete (current Surface/Eligibility scope)  
**Scope:**
- Shared conformance corpus extension (✅ three explicit Surface cases + Eligibility interval)
- Parity harness for source vs. generated behaviour (✅ tools/surface/parity.py)
- Regression gates in CI (✅ Phase 8 conformance workflow)
- Defect fixtures for edge classes (✅ six defect fixtures in Surface suite)
- SHACL execution and extraction-drift CI gates (✅ mandatory checks)

**Verification checklist:** 7/8 items complete; SWRL reasoner integration (item 7) pending.

---

### Phase 9 — Migration and rollout
**Status:** 🚧 Not started  
**Scope (planned):**
- Migration guides for Surface and MORK authors
- Compatibility mode and deprecation policy
- Phased rollout profiles (draft → review → production)
- Release checklist and change management

**Estimated:** 2–3 weeks

---

### Phase 10 — Scale and optimization
**Status:** 🚧 Not started  
**Scope (planned):**
- Performance baselines for lowering and compilers
- Caching strategy for intermediate graphs
- Large-vocabulary and large-population stress tests
- High-throughput generation profile

**Estimated:** Duration TBD (performance-dependent)

---

## Acceptance Criteria

### Authoring experience (✅ Met)
1. ✅ Domain authors produce valid projection intent without raw MORK internals
2. ✅ Same projection contract generates at least two backend families (SPARQL, SHACL confirmed; SWRL generated)
3. ✅ Authoring docs sufficient for first successful compile in one session

### Correctness (✅ Met)
1. ✅ Deterministic regeneration for identical inputs (verified by test suite)
2. ✅ Parity between source and generated artefacts (tools/surface/parity.py)
3. ✅ Traceable provenance from output to source (full chain implemented)

### Governance (✅ Met for current scope)
1. ✅ Production compile mode rejects unapproved mappings (Phase 4 implementation)
2. ✅ Mapping version and effective date policies enforced (Phase 4 SHACL shapes)
3. ✅ Review state and provenance queryable (Foundation alignment complete)

### Eligibility readiness (✅ Met for IntervalContainment)
1. ✅ Interval containment works end-to-end
2. ✅ Undetermined outcomes explicit with diagnostics
3. ✅ SPARQL and native backends agree (15/15 tests + worked example verification)

---

## Repository Structure

### Surface layer
- `ontology/surface/README.md`
- `ontology/surface/spec/surface.ttl` (Projection subsystem added)
- `ontology/surface/vocab/surface-vocab.ttl`
- `ontology/surface/shapes/structural.ttl`, `constraints.ttl`
- `ontology/surface/examples/` (Projection examples)
- `ontology/surface/execution/` (Generated packages)
- `tools/surface/` (compiler, lowering, invalidation, parity engines)

### MORK layer
- `ontology/mork/spec/Mork.ttl`, `Mork.owl`
- `ontology/mork/README.md`
- `tools/mork_compilers/` (SPARQL, SHACL, SWRL, RML backends)
- `tools/mork/` (validators)

### Eligibility integration
- `ontology/eligibility/` (declarative sources)
- `tools/mork_compilers/eligibility_ir.py` (executable semantics)

### Architecture and governance
- `docs/architecture/decisions/ADR-A16` through `ADR-A28`
- `docs/architecture/` (solution-design-specification.md includes Surface/MORK section)
- `docs/developer/status/surface-mork-unified-projection.md` (tracking)
- `docs/developer/status/surface-outstanding-items.md` (decision log)

---

## Risk Register and Mitigations

| Risk | Mitigation |
|------|-----------|
| Surface scope expansion causes conceptual drift | Strict subsystem boundaries (Promotion/Index/Projection), separate shapes, separate compiler modules |
| MORK governance changes break compatibility | Compatibility mode profiles, migration scripts, staged validation levels |
| Backend semantics divergence | Shared executable IR + parity tests (all 15 MORK tests pass) |
| LLM completion introduces unstable mappings | Deterministic mode default, governance gate for LLM nodes |
| Performance cost at scale | Phase 10 optimization plan with caching and incremental regeneration |

---

## Governance Model — Three Operational Modes

### Draft mode
- Allows unapproved templates and optional LLM completion
- For experimentation and prototyping

### Review mode
- Requires explicit review state and provenance completeness
- For collaborative development

### Production mode
- Deterministic lowering only (LLM completion requires explicit permission)
- Approved governance state required for mappings and templates
- Release parity gates enforced: determinism ✅, parity ✅, provenance ✅, governance ✅

A release cannot pass production gate without all four checks.

---

## Completed Deliverables Checklist

- [x] ADR set A16–A28 (all signed)
- [x] Surface Projection subsystem spec and vocab
- [x] Structural and constraint shapes for Projection
- [x] Surface-to-MORK lowering engine (tools/surface/lowering.py)
- [x] MORK governance and versioning (Foundation import, shapes)
- [x] SPARQL, SHACL, SWRL compiler backends
- [x] Eligibility interval containment (15/15 tests)
- [x] Invalidation and parity framework
- [x] Conformance corpus (Phase 8 gates active)
- [x] Defect fixtures (6 edge cases)
- [x] Provenance chain implementation

---

## Next Steps (Planned)

1. **Phase 8 final sign-off:** Resolve SWRL reasoner verification blocker (item 7 of checklist)
2. **Phase 9 decomposition:** Break migration/rollout into slices; author migration guides
3. **Phase 10 planning:** Characterize performance profile; identify caching opportunities
4. **Phase 9.1 Pilot:** Migrate one real domain to Surface-MORK; validate compatibility

---

## Documentation and References

- **Status tracking:** [surface-mork-unified-projection.md](status/surface-mork-unified-projection.md)
- **Outstanding items:** [surface-outstanding-items.md](status/surface-outstanding-items.md)
- **Architecture decisions:** [docs/architecture/decisions/ADR-A16](../../architecture/decisions/ADR-A16-surface-projection-mechanism.md) through [ADR-A28](../../architecture/decisions/ADR-A28-parity-and-conformance-release-gate.md)
- **Code:** [tools/surface/](../../tools/surface/), [tools/mork_compilers/](../../tools/mork_compilers/)
- **Tests:** 61/61 Surface tests, 15/15 MORK compiler tests

---

## Maintenance

This plan is updated when:
- A phase transitions to complete or blocked status
- A major architectural decision changes scope
- An acceptance criterion is added or redefined

**Last updated:** 2026-09-22  
**Next review:** Phase 8 SWRL verification complete or Phase 9 ratification
