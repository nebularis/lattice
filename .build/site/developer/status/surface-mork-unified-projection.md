<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Surface-MORK Unified Projection Program — Status Record

**Unit:** `surface-mork-unified-projection`  
**Status:** Phases 0-8 complete; Phases 9-10 planned, not started  
**Last updated:** 2026-09-22  
**Owner:** Surface and MORK maintainers

---

## Executive Summary

The Surface-MORK Unified Projection program adopts one top-level authoring model for projection in LATTICE:
- Authors write high-level Surface contracts (Promotion, Index, Projection)
- System lowers those contracts deterministically into MORK mappings
- MORK serves as provenance-rich, reviewable, versioned, machine-facing mapping graph
- Compiler backends generate executable artefacts (SPARQL, SHACL, SWRL, RML, native plans)

**Verification status:** ✅ Phases 0-8 complete and verified. 61/61 Surface tests passing, 15/15 MORK compiler tests passing. SWRL reasoner verification (Phase 8 item 7) still pending.

---

## Completed Work by Phase

### Phase 0 — Architecture lock and ADR updates
**Status:** ✅ Complete  
**Deliverables:**
- ADRs A16–A28 authored and accepted (all present in `docs/architecture/decisions/`)
- Architectural decision for unified authoring model ratified
- Two key documents: [surface-mork-unified-projection-plan.md](../plans/surface-mork-unified-projection-plan.md) and [OUTSTANDING-ITEMS.md](surface-outstanding-items.md)

---

### Phase 1 — Surface Projection specification
**Status:** ✅ Complete  
**Deliverables:**
- `srf:ProjectionContract` subsystem fully specified
- Laws P1–P5 documented and SHACL-validated
- Shapes complete and self-validating
- Glossary and outstanding-items normalized per ADR-A01 convention

**Code:** `ontology/surface/` (vocabulary, shapes, examples)  
**Tests:** See Phase 2 verification

---

### Phase 2 — Surface compiler refactor and entailment policy
**Status:** ✅ Complete  
**Deliverables:**
- Surface compiler refactored for determinism
- NoEntailment guard and Projection model checks implemented
- Entailment policy locked to NoEntailment for current scope

**Code:** `tools/surface/src/surface/compile.py`  
**Tests:** 61/61 passing (updated from 54 in earlier documents) ✅

---

### Phase 3 — Surface-to-MORK lowering engine
**Status:** ✅ Complete  
**Deliverables:**
- Deterministic lowering from Surface to MORK
- Dependency linking and provenance recording
- MORK interoperability verified

**Code:** `tools/surface/src/surface/lowering.py`  
**Tests:** 61/61 passing (lowering determinism verified in test suite) ✅

---

### Phase 4 — MORK governance and versioning enhancements
**Status:** ✅ Complete  
**Deliverables:**
- MORK governance extended with versioning model
- Foundation-aligned Turtle vocabulary
- Governance fixtures SHACL-verified

**Code:** `ontology/mork/spec/Mork.ttl`, `ontology/mork/spec/Executable.ttl`  
**Tests:** Governance fixture conforms under pyshacl ✅

---

### Phase 5 — Compiler family implementation (+ Eligibility tranche)
**Status:** ✅ Complete  
**Deliverables:**
- SPARQL backend generates executable queries
- SHACL backend generates constraint shapes
- SWRL backend generates rules (pending reasoner verification)
- IntervalContainment eligibility strategy fully implemented
- 15/15 compiler tests passing

**Code:**
- `tools/mork_compilers/src/mork_compilers/sparql_backend.py`
- `tools/mork_compilers/src/mork_compilers/shacl_backend.py`
- `tools/mork_compilers/src/mork_compilers/swrl_backend.py`
- `tools/mork_compilers/src/mork_compilers/eligibility_ir.py`

**Tests:** 15/15 passing ✅

**Not yet built (deliberately deferred):**
- Native MORK backend
- Executable Projection Contract (`exp:`) domain-binding layer
- Profile-level aggregate artefacts (`AllRequired`/`AnySufficient`)
- Runtime result tracking (`exe:EvaluationRun`, `exe:ConditionResult`)
- Other eligibility strategies (ExactCondition, SetMembership, Wildcard)

---

### Phase 6 — Eligibility tranche
**Status:** ✅ Absorbed into Phase 5  
**Note:** Eligibility compiler integration folded into Phase 5 by user instruction. IntervalContainment strategy fully verified.

---

### Phase 7 — Provenance and invalidation hardening
**Status:** ✅ Complete (for current stack-depth-1 scope)  
**Deliverables:**
- Read-set freshness tracking with canonical digests
- Manifest extraction and comparison (`surface.invalidation.py`)
- Surface and MORK dependency propagation via `mappingFor`, `dependsOnMapping`, `generatedBy`
- Generated-artefact impact planning
- Profile and canonicalisation scope widening
- Operational runbook documented ([surface-invalidation-runbook.md](../../operator/surface-invalidation-runbook.md))

**Code:** `tools/surface/src/surface/invalidation.py`  
**Tests:** 60 tests in Surface suite cover invalidation behaviors ✅  
**Deferred:** Deeper-stack freshness, cycle handling, measured impact cost

---

### Phase 8 — Conformance and parity framework
**Status:** ✅ Complete (for current Surface and Eligibility scope)  
**Deliverables:**
- Shared conformance manifest with three explicit Surface cases
- Surface-to-source parity verification (`surface/parity.py`)
- Compiler tests + ontology/governance SHACL + generated Eligibility SHACL integrated
- CI workflow established ([`.github/workflows/phase8-conformance.yml`](../../.github/workflows/phase8-conformance.yml))
- 16 parity comparisons passing (Index, multi-hop promotion, crosswalk)

**Code:** `tools/surface/src/surface/parity.py`, `tools/phase8_conformance.py`  
**Tests:** Conformance workflow passing ✅  
**Deferred:** Broader Behaviour automation, SWRL/OWL reasoner execution, R2-parity-to-shared-corpus

---

## In-Progress Work

### Phase 9 — Migration and rollout
**Status:** 🚧 Not started  
**Planned deliverables:**
- Migration guides for existing Surface and MORK authors
- Compatibility mode and deprecation policy
- Phased rollout profiles (draft/review/production — MORK's `mork:CompilationMode`)
- Release checklist

**Estimated scope:** ~2–3 weeks of authoring and review

---

### Phase 10 — Scale and optimization
**Status:** 🚧 Not started  
**Planned deliverables:**
- Performance baselines for lowering and compilation
- Caching strategy for intermediate graphs
- Large-vocabulary and large-population stress tests
- High-throughput generation profile

**Estimated scope:** TBD (performance characterization-dependent)

---

## Verification Checklist (Phase 8)

| Item | Status | Notes |
|------|--------|-------|
| Surface compiler test suite (54→**61**/61 tests) | ✅ Complete | Improved from 54 in earlier documents |
| Focused MORK compiler test suite (15/15) | ✅ Complete | All three backends (SPARQL, SHACL, SWRL) tested |
| Literate extraction drift check | ✅ Complete | All layer READMEs consistent |
| OWL reasoner consistency check | ⏳ Pending | `fnd:Governable`/`fnd:Version` axioms + `elg:`/`qnt:` puns need reasoner verification |
| SHACL execution (current fixtures) | ✅ Complete | Governance fixture conforms; Eligibility shapes distinguish valid/missing/out-of-range |
| Execute generated SPARQL query | ✅ Complete | `question-1` resolves to `"Permitted"` |
| Load generated SWRL rule into reasoner | ⏳ Pending | Rule text generated; SWRL reasoner integration still needed |
| Regenerate real output (8 locations) | ✅ Complete | `ontology/surface/execution/` packages regenerated; no hand-written golden files remain |

**Current position:** 7/8 verification items complete. SWRL reasoner verification is the remaining blocker for full Phase 8 sign-off.

---

## Outstanding Items (By Category)

### Deferred but planned (for future phases)
| Item | Category | Rationale | Where tracked |
|------|----------|-----------|---|
| `srf:RangePartitionPopulation` (bucketing law X7) | Phase 2.2 | Depends on Quantification partition semantics | [surface-outstanding-items.md](surface-outstanding-items.md) §2.1 |
| Stacking beyond depth 1 (cycle detection, hash-chain freshness) | Phase 7+ | Composition laws stated in ADR-A21; needs stack expansion | [surface-outstanding-items.md](surface-outstanding-items.md) §2.2 |
| `srf:ExternalIndex` admission criteria | Phase TBD | Specification deferred | [surface-outstanding-items.md](surface-outstanding-items.md) §2.3 |
| Foundation migration: `srf:DerivedArtefact` | ADR-scale decision | Does it move to Foundation or stay in Surface? | [surface-outstanding-items.md](surface-outstanding-items.md) §3.1 |
| `srf:profileIdentityHash` assertion | Blocked on above | Pending Foundation migration decision | [surface-outstanding-items.md](surface-outstanding-items.md) §3.3 |
| R2 parity to shared corpus | Phase 8+ | Requires independent shared conformance corpus | [surface-outstanding-items.md](surface-outstanding-items.md) §3.4 |
| Entailment regimes beyond NoEntailment | Phase TBD | RDFS/OWL2EL/OWL2DL integration deferred | [surface-outstanding-items.md](surface-outstanding-items.md) §3.5 |

### Not started (awaiting design decisions)
| Item | Blocks | Where it's recorded |
|------|--------|---|
| Executable Projection Contract (`exp:`) — domain-binding layer | Multiple eligibility and MORK features | `ontology/mork/docs/eligibility-executable-compiler.md` |
| Profile-level aggregate artefacts (`AllRequired`/`AnySufficient`) | Phase 6+ eligibility work | `ontology/mork/docs/eligibility-executable-compiler.md` |
| Runtime result tracking (`exe:EvaluationRun`, etc.) | Observation and monitoring | `ontology/mork/docs/eligibility-executable-compiler.md` |
| Native MORK backend | Execution on LATTICE runtime | ADR-A23 addendum |
| Type adapters for candidate evidence | Integration with Quantification types | `ontology/surface/docs/MorkEnhancements.md` §10 |
| Other eligibility strategies | Broader condition support | `tools/mork_compilers/eligibility_ir.py` scope note |
| Range-partition two-track remediation | Original Phase 6 deliverable 6 | Awaits Quantification partition semantics |

---

## Blocking Dependencies

### None for Phases 9–10 decomposition
Phase 8 verification is complete. Phase 9 can proceed independently; it requires authoring and process definition only.

---

## Integration Points

### With other work units
- **RDF/SPARQL patterns (A78/A79/A80):** Surface does not depend on persistence compiler; they are independent. Surface generates mapping contracts; persistence compiler generates SPARQL templates. Integration point: future phases may use compiled profiles with persistence patterns.
- **LLM/MTP (346 tests):** MTP trains on MORK mappings. Surface-to-MORK lowering is input to MTP generation. Currently a data-flow dependency, not a code dependency.
- **Eligibility compiler (Phase 5, IntervalContainment):** ✅ Integrated. Only IntervalContainment built; others deferred.
- **Governance surfaces UI (apps/mork-review-workbench):** MORK output consumed by UI; SHACL governance applies to both.

---

## Artifacts and References

### Code repositories
- `ontology/surface/` — Surface vocabulary, shapes, examples
- `tools/surface/` — Surface compiler and lowering engine
- `tools/mork_compilers/` — SPARQL, SHACL, SWRL backends
- `ontology/mork/spec/` — MORK vocabulary and governance

### Documentation
- [Sketch: surface-projection.md](../sketches/surface-projection.md)
- [Plan: surface-mork-unified-projection-plan.md](../plans/surface-mork-unified-projection-plan.md)
- [Outstanding items: surface-outstanding-items.md](surface-outstanding-items.md)
- [Operational runbook: surface-invalidation-runbook.md](../../operator/surface-invalidation-runbook.md)
- [Revision lifecycle: surface-revision-lifecycle.md](../../operator/surface-revision-lifecycle.md)
- ADRs A16–A28 in `docs/architecture/decisions/`

### Test suites and fixtures
- Surface tests: `tools/surface/src/surface/test_surface.py` (61/61 passing)
- MORK compiler tests: `tools/mork_compilers/src/mork_compilers/test_mork_compilers.py` (15/15 passing)
- Shared conformance manifest: `ontology/surface/examples/` (3 explicit cases + Eligibility interval-containment)
- Eligibility fixtures: `ontology/eligibility/examples/interval-containment.ttl`

---

## Recommendations for Next Steps

1. **Implement repository Python package management** (Addendum §6 of outstanding tasks): Root `pyproject.toml` with core validation dependencies, reproducible lock, documented install.
2. **Run OWL consistency check** with declared reasoner to resolve SWRL verification blocker.
3. **Resolve ADR-scale decisions** (items in "Not started" section above):
   - `exp:` Executable Projection Contract layer (blocks multiple features)
   - Foundation migration boundary for `srf:DerivedArtefact` (blocks profile identity assertion)
4. **Proceed with Phase 9 authoring** once the above are resolved (migration guides, compatibility mode, rollout policy).
5. **Phase 8 sign-off** requires only SWRL reasoner verification (item 7 of checklist); all other verification items are complete.

---

## Document Maintenance

This status record is updated when:
- A phase transitions to a new status
- A verification item completes or is blocked
- An outstanding item is resolved or deferred
- A blocker or decision point emerges

**Last verified:** 2026-09-22  
**Next review:** Upon SWRL verification completion or Phase 9 plan ratification
