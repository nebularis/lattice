<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Developer Coordination Reorg — Handoff Summary

**Date:** 2026-09-22  
**Work package:** Take stock of implementation and update tracking before epic decomposition

---

## What was done

### 1. Comprehensive Status Index Created
**File:** `docs/developer/INDEX.md`

A new, single source of truth for coordinating all active work:
- **Part I (Completed):** 9 work units documented with status, artifacts, and key findings
  - RDF/SPARQL patterns guide + persistence compiler (Slices 1-2 complete, 239 tests)
  - LLM/MTP generation (346 tests passing)
  - Repository topology (ADR-A77 accepted)
  - Governance surfaces, eligibility compiler, phase handoffs
  
- **Part II (Active/Planned):** Epic decomposition and housekeeping first cut
  
- **Part III (Archived):** Phase 0-6 handoffs and historical work
  
- **Part IV:** Navigation guides (by topic, by phase, by status)
  
- **Part V:** Key decision points and open questions
  
- **Part VI:** Traceability and test coverage
  
- **Part VII:** Questions blocking epic decomposition or requiring ratification

### 2. Documentation Governance Simplified
**Changes:**
- Traceability tracking moved from CSV-first to **INDEX.md-first**
  - CSV is now optional, not mandatory
  - `.github/copilot-instructions.md` updated (line 122)
  - Each slice still updates INDEX.md as primary; CSV is supplementary

- Old tracking documents consolidated
  - `docs/developer/status/DESIGN_SKETCHES_INDEX.md` archived with pointer to new INDEX
  - Historical content retained for reference only

### 3. Epic Plan Updated
**File:** `docs/developer/plans/lattice-platform-agentic-development-v0.2.md`

**Changes:**
- **Line 473:** Status note updated — RDF patterns Slices 1-2 complete ✅
  - Compiler ready with 239 passing tests
  - Phase 2 (P2.1–P2.4) must be revised to integrate this layer
  - References INDEX.md for current status
  
- **Lines 806-807:** Open questions clarified
  - Request Query Mapping and Query Execution still deferred until A75 ratification
  - Same reference to INDEX.md for current status

---

## What's ready now

| Item | Status | Location | Notes |
|------|--------|----------|-------|
| **RDF/SPARQL Patterns Guide** | ✅ Complete | `docs/architecture/rdf-sparql-patterns-guide.md` | 30 chapters, all patterns (K/O/C/T/QP) documented |
| **Persistence Ontology** | ✅ Complete | `ontology/persistence/` | 14 examples, SHACL shapes, design notes |
| **Persistence Compiler** | ✅ Complete | `tools/persistence/` | 239 tests passing, 11 templates, injection corpus |
| **ADRs (A78/A79/A80)** | ✅ Ratified | `docs/architecture/decisions/` | Substrate, compiler, housekeeping boundaries |
| **Status Index** | ✅ New | `docs/developer/INDEX.md` | Single source of truth for all coordination |
| **LLM/MTP Work** | ✅ Complete | `tools/mork/src/mtp/` | 346 tests passing, L0-L5 curriculum generated |
| **Governance Surfaces (UI)** | 🟡 Partial | `apps/mork-review-workbench/`, `apps/surface-contract-studio/` | Skeleton complete; backend integration Phase 2/5 |

---

## What needs to happen before decomposition

### Required: Epic Plan Revision
The epic plan (v0.2) was written before the compiler was built. **Phase 2.1–2.4 must be redesigned** to:
- Replace ad hoc SPARQL construction with `ontology/persistence` profiles and `tools/persistence` templates
- Integrate the compiler's `dal:CompiledProfile` output into ingestion, plan interpretation, and query construction
- This is a significant rewrite, not a patch

**Estimated scope:** 1–2 planning slices to revise Phases 2–4 with compiler layer

### Optional (but useful): Phase 0.2–0.4 Integration
Once Phase 2 revision is done, optionally integrate RDF patterns into Phase 0.2–0.4 walking skeleton:
- Phase 0.2 (walking skeleton): Patterns T + C (metadata graphs + CAS) + pattern K (uniqueness)
- Phase 0.3 (schema): Pattern K completed (uniqueness service + integration)
- Phase 0.4 (canonicalization): Pattern O (dense ordering) + audit queries

This is not blocking epic decomposition, just improves Phase 0 architectural coherence.

---

## How to use the INDEX

### Daily coordination
When you need to know:
- **What's in progress?** → Part II
- **What tests are passing?** → Part VI (test coverage table)
- **Is pattern X built?** → Part I (search or use Ctrl+F)
- **What's blocking us?** → Part VII (key decision points)
- **Where's the reference implementation?** → Part I (location field in each unit)

### Onboarding a new contributor
1. Read [docs/developer/INDEX.md](docs/developer/INDEX.md) Parts I & IV for orientation
2. Find their unit in the index
3. Read the linked sketch, plan, and status doc in order
4. Check the validation pack for test requirements

### Decomposing the epic
1. Review [docs/developer/INDEX.md](docs/developer/INDEX.md) Parts I & II
2. Note what's complete vs. planned
3. Ratify A74/A75 decision if not already done
4. Revise Phase 2.1–2.4 to integrate compiler (new planning unit)
5. Begin Phase 0 decomposition (existing structure, updated to reference patterns)

---

## Files Changed

| File | Change | Why |
|------|--------|-----|
| `docs/developer/INDEX.md` | Created | New single source of truth for all coordination |
| `.github/copilot-instructions.md` | Modified (line 122) | CSV tracking now optional; INDEX primary |
| `docs/developer/status/DESIGN_SKETCHES_INDEX.md` | Modified (header) | Marked archived; points to INDEX |
| `docs/developer/plans/lattice-platform-agentic-development-v0.2.md` | Modified (2 locations) | Updated patterns status and open questions |

---

## Key Learnings from Patterns Implementation

What was discovered during Slice 2 execution that might affect future work:

1. **Classes need deployment-scoped targeting**: A single class deployed in multiple graph patterns needs multiple targets, tracked via `dal:coversClass`

2. **SPARQL has real constraints**: Property paths forbidden in DELETE/INSERT blocks; SPARQL variables can't represent whole triple sets (use `#PAYLOAD#` marker instead)

3. **Mustache parsing gotchas**: Comments with bare `}}` are silently truncated, corrupting everything after

4. **pyshacl defaults require explicit flags**: `allow_warnings=True` needed for non-blocking warnings

5. **Compiler determinism matters**: Permuting input triple order must produce identical output (L2 test + CI gate)

---

## Next Steps (Your Decision)

Choose one:

**Option A: Revise epic plan now** (before decomposition)
- Redesign Phase 2.1–2.4 to integrate compiler layer
- Updated epic becomes source for Phase 0-9 plans
- ~2–3 days of planning

**Option B: Decompose with conditional planning**
- Begin Phase 0–1 decomposition with current structure
- Note Phase 2 as "TBD: integrate compiler" in each slice
- Revise when Phase 1 is underway
- Faster to Phase 0 implementation, slower overall

**Recommendation:** Option A. Phase 2 is already planned in enough detail that revision is feasible and high-value. Phase 0 should not assume it will hand off to an incompatible Phase 2 model.

---

## Communication

All stakeholders now have one consistent view via `docs/developer/INDEX.md`. This is:
- Linked from epic plan ✅
- Referenced in copilot-instructions ✅
- Discoverable from any status doc (cross-references via Part III)

Updates to the index are tracked in git; no external tool needed.

---

**Ready to proceed with epic decomposition.** ✅
