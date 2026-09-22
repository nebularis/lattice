<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Design Sketch Implementation Validation — Document Index (ARCHIVED)

**Status:** Superseded. See `docs/developer/INDEX.md` for the current, consolidated tracking of all design sketches, plans, status records, reviews, and validation packs.

This document is kept for historical reference. For current work status, consult:
- **Consolidated index:** [`docs/developer/INDEX.md`](../INDEX.md)
- **RDF/SPARQL patterns:** [rdf-sparql-patterns-status.md](./rdf-sparql-patterns-status.md) + [rdf-sparql-patterns-phase-plan.md](../plans/rdf-sparql-patterns-phase-plan.md)
- **LLM/MTP work:** [llm-training-mtp.md](./llm-training-mtp.md) + [mtp-execution.md](./mtp-execution.md)
- **Governance surfaces:** [governance-surfaces.md](./governance-surfaces.md) + [governance-surfaces-integration.md](../plans/governance-surfaces-integration.md)
- **Other sketches:** See Part V in `INDEX.md` for archived/historical work

---

## Historical Contents (Below - for reference only)

**Date completed:** 2026-09-20
**Task:** Validate extent of implementation for 7 design sketches in `/docs/developer/sketches/`
**Deliverables:** Status docs (completed), plan docs (deferred work), summary cross-reference

---

## Status Documents Created

### Fully Implemented & Validated ✅

| Sketch | Status Document | Summary |
|---|---|---|
| **llm-training.md** | [llm-training-mtp.md](./llm-training-mtp.md) | L0-L5 curriculum fully generated; 258 terms, 895 axioms; 9 lenses, 30+ cassettes; 20 output files; 346 tests passing |
| **MTP-L0 Generator Sketch** | (included in llm-training-mtp.md) | Facts extractor, doctrine pinning, axiom ownership gates all operational |
| **MTP L2 Generator Sketch.md** | (included in llm-training-mtp.md) | S1–S13 pipeline (corpus, partition, fidelity, mutate, render); mutation-derived ground truth working |
| **mtp-implementation-plan.md** | [mtp-execution.md](./mtp-execution.md) | Plan fully executed; every slice authored and validated; ready for Phase 7 backend integration |

### Implemented, Awaiting Runtime Validation ⏳

| Sketch | Status Document | Summary |
|---|---|---|
| **mork-eligibility-compiler.md** | [eligibility-compiler.md](./eligibility-compiler.md) | Source complete (`tools/mork_compilers/`); three backends (SPARQL, SHACL, SWRL); 7 deliberate non-coverage areas documented; unit tests present, not yet executed |

### Partially Implemented (Skeleton UI) 🟡

| Sketch | Status Document | Plan Document | Summary |
|---|---|---|---|
| **governance-and-versioning-migration.md** | [governance-surfaces.md](./governance-surfaces.md) | [governance-surfaces-integration.md](./governance-surfaces-integration.md) | Studio and Bench fixture shells correct, role model demonstrated, permission enforcement not yet wired; 3 integration slices needed for Phase 2 & 5 |

### Superseded/Archived 🗄️

| Sketch | Status Document | Summary |
|---|---|---|
| **implementation-handover.md** | [implementation-handover-historical.md](./implementation-handover-historical.md) | Phase 0–6 handover archived; refer to individual phase handoffs and platform-continuation status instead |

---

## Cross-Reference Document

**Comprehensive validation summary:** [design-sketches-validation-summary.md](./design-sketches-validation-summary.md)

This single document provides:
- Overview of all 7 sketches
- Implementation status table
- What was validated vs. awaiting validation
- Next actions per sketch
- Links to all status and plan documents

---

## Plan Documents Created

### New Work Identified

| Unit | Plan Document | Phase | Scope |
|---|---|---|---|
| **governance-surfaces-integration** | [governance-surfaces-integration.md](../plans/governance-surfaces-integration.md) | Phase 2 & 5 | 3 slices: Studio backend wiring, Bench permission model, evidence projection state |

---

## How to Use These Documents

### To review implementation status:
1. Start with [design-sketches-validation-summary.md](./design-sketches-validation-summary.md) for the overview
2. Find your sketch in the summary table
3. Follow the link to the status document for that sketch
4. Status documents cite evidence (code locations, test results, ADRs)

### To find deferred work:
1. Check [design-sketches-validation-summary.md](./design-sketches-validation-summary.md) for "Partially Implemented"
2. Open the linked plan document
3. Plan documents describe slices, test strategy, and acceptance criteria

### To understand MTP completion:
1. Read [llm-training-mtp.md](./llm-training-mtp.md) — describes what's built
2. Read [mtp-execution.md](./mtp-execution.md) — describes plan execution (every slice done)
3. Read [mtp-implementation-plan.md](../sketches/mtp-implementation-plan.md) — original plan document

### To track governance surfaces work:
1. Read [governance-surfaces.md](./governance-surfaces.md) — what exists (fixture shells)
2. Read [governance-surfaces-integration.md](../plans/governance-surfaces-integration.md) — what's needed (3 slices)

---

## Key Results

- **7/7 sketches validated** ✅
- **4/7 fully implemented** ✅ (llm-training, L0 sketch, L2 sketch, mtp-implementation-plan)
- **1/7 implemented, awaiting runtime test** ⏳ (eligibility-compiler)
- **1/7 partially implemented** 🟡 (governance-and-versioning) — skeleton UI correct, 3 integration slices identified
- **1/7 archived** 🗄️ (implementation-handover)

## Governing ADRs

All sketches are governed by their respective ADRs:
- LLM Training: [A25](../../architecture/decisions/ADR-A25-llm-participation-and-deterministic-production-gate.md), [A44](../../architecture/decisions/ADR-A44-mork-teaching-pack-generated-content-boundary.md)
- Eligibility Compiler: [A23](../../architecture/decisions/ADR-A23-mork-compiler-family-completion-policy.md), [A24](../../architecture/decisions/ADR-A24-eligibility-executable-semantics-backend-strategy.md)
- Governance Surfaces: [A38](../../architecture/decisions/ADR-A38-surface-output-publication-and-studio-authoring-boundary.md), [A42](../../architecture/decisions/ADR-A42-mork-review-snapshot-and-decision-learning-boundary.md)
- Repository: [A77](../../architecture/decisions/ADR-A77-repository-topology-and-documentation-governance.md)

---

**Next review:** After Phase 7 LLM backend integration or Phase 2/5 governance surfaces implementation
