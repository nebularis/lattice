<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Surface Layer — Outstanding Items

**Source:** Consolidated from `ontology/surface/docs/OUTSTANDING-ITEMS.md` (2026-09-18)  
**Status:** Living reference document; all items tracked in [surface-mork-unified-projection.md](surface-mork-unified-projection.md)  
**Last updated:** 2026-09-22

---

## Overview

This document tracks specific outstanding items, design decisions, deferred work, and findings that emerged during Surface-MORK unified projection implementation (Phases 0–8). For phase-level status, see [surface-mork-unified-projection.md](surface-mork-unified-projection.md).

All items listed here are **deliberately not in shipped artefacts** — no README annotations, OWL declarations, shape messages, or generated modules carry these items.

---

## 1. Decisions Taken During Implementation

### 1.1 Signature scope and law X6 — ✅ Closed

**Rationale:** The design note stated conservativity (X1) unconditionally: a surface never extends source-signature consequence set. This holds for indexing (mints own terms) but NOT for promotion (restates values onto `srf:promotesTo`). When `srf:promotesTo` is an authored property, emitted triples are over the authored signature and indistinguishable from authored facts.

**The MERIDIAN CSO→FBO case:** `fbo:hasLineOfBusiness` is authored, so `DimensionSourcing` is producing authored-signature A-box, not an index.

**Solution implemented:**
- `srf:signatureScope` on every `srf:GeneratedSurface` (values: `srf:LocalSignature` or `srf:SourceSignature`)
- X1 restated to apply to local-signature surfaces only
- Law **X6:** promotion onto a property outside the contract's target namespace declares exact or crosswalk-exact fidelity and is materialised rather than definitional

**Sign-off:** [ADR-A16 addendum](../../architecture/decisions/ADR-A16-surface-projection-mechanism.md#addendumdecision-x6-stands-as-designed-sign-off) + [ADR-A21](../../architecture/decisions/ADR-A21-signature-scope-composition-for-stacked-surfaces.md) (composition rule across stacked surfaces).

---

### 1.2 Read paths as indexed step lists, not SHACL paths — ✅ Done

**Decision:** Use `srf:PathStep` individuals with `srf:stepIndex` and `srf:stepDirection` instead of SHACL path nodes.

**Why:** SHACL path syntax nests blank nodes; labels don't survive canonicalisation without normalisation. Would have made read paths the only part of contract needing special handling.

**Result:** `srf:PathStep` gives sequence-and-inverse expressivity with a form that hashes directly, following `qnt:OrderingComponent` pattern. No SHACL engine needed. Alternation and zero-or-more remain out of scope.

**Tradeoff:** Contract cannot be handed to SHACL engine as path expression; compiler must synthesise one. Nothing currently needs that.

---

### 1.3 Derivation contract location — ⏳ Decision Needed

**Question:** Does derived-artefact contract eventually move to Foundation per ADR-A12, or does each generating layer declare its own?

**Current state:** `srf:DerivedArtefact`, `srf:GeneratedSurface`, `srf:ReadSetEntry`, `srf:LawDischarge`, `srf:derivationAuthority`, and hash properties all declared in Surface, not Foundation.

**Why it matters:** ADR-A12 anticipates Foundation-level `fnd:DerivedArtefact`; Quantification §12 and Behaviour both name it as a blocking gap. Validation reports, entailment sets, and materialised bins want the same contract.

**Implication:** When Foundation gains it, Surface's classes should become subclasses, not restructured. Classes are shaped to allow this, but migration is unplanned and duplication is real in the meantime.

**Related:** [ADR-A22](../../architecture/decisions/ADR-A22-mork-governance-and-versioning-foundation-alignment.md) resolves ontology/governance/versioning alignment for MORK; this broader Foundation question is unaffected.

---

### 1.4 Generated-term markers are parentage, not types — ✅ Done

**Design:** Every generated class is `rdfs:subClassOf srf:GeneratedClass`; every generated relation is `rdfs:subPropertyOf srf:generatedRelation`.

**Why:** MERIDIAN's approach (asserting `owl:Class` with RDF properties, creating punning) causes OWL-API toolchain issues. Parentage avoids this.

**Result:** Enumerating a surface inventory is a subclass query; no punning. Provenance lives on `srf:GeneratedSymbol` records in manifest.

---

### 1.5 Contract and example locations — ✅ Done

**Layout:**
- Generated packages: `ontology/surface/execution/<contractKey>/`
- Example contracts: `ontology/surface/examples/`
- Root ontology examples: `ontology/examples/` (for cross-layer composition, not single-layer worked examples)

**Status:** Accepted; no open action.

---

## 2. Deferred with Planned Approach

### 2.1 `srf:RangePartitionPopulation` — Deferred, planned

**What it is:** Bucketing law X7; creates nominal bucket classes for ranges within a dimension.

**Blocker:** Depends on Quantification partition semantics first.

**Five-step unblocking path:**

1. **State the partition precondition** (Quantification work): `qnt:PartitionRangeSet` subclass or `qnt:isPartition` flag with shape checking disjointness and coverage
2. **Settle boundary behaviour under each closure** (Quantification): ranges meeting at `b` must be non-overlapping and complete
3. **Decide what the symbol denotes** (Quantification + Surface): nominal bucket class needs `owl:onDatatype` with facets; profile declares `srf:OWL2DLEntailment` or materialises
4. **Naming policy** (Surface): ranges need labels, or use `DigestLocalName`, or mint from bounds (`bucket_0_100`, etc.)
5. **Invalidation** (Surface): read-set entry under existing freshness rule; no new machinery

**Effort:** Most work is steps 1–2 (Quantification). Surface's part is small once partition guarantee exists.

---

### 2.2 Stacking beyond depth 1 — Deferred, planned

**Current limit:** `srf:StackDepthReleaseCeilingShape` caps at depth 1; deleting it lifts the cap.

**What exists:** `srf:permittedStackDepth`, `srf:stackDepth`, `srf:SurfaceSource` read-set entries, `srf:S10` check.

**What must exist first:**

| Item | Status | Detail |
|------|--------|--------|
| Read set becomes a DAG | Not yet | At depth *n*, surface semantic hash must incorporate *artefact* hashes of input surfaces for three-level-deep changes to propagate |
| X1 composition law | ✅ Done | [ADR-A21](../../architecture/decisions/ADR-A21-signature-scope-composition-for-stacked-surfaces.md): `signatureScope` is `SourceSignature` if any input is |
| R1 composition law | ✅ Done | ADR-A21: every surface in stack shares one profile identity, checked statically |
| Cycle detection | Not yet | Needed before depth cap lifts |
| Invalidation cost | Not yet | Not measured on FBO chain; impact table has no stacked-regeneration row; tracked under [ADR-A27](../../architecture/decisions/ADR-A27-invalidation-and-minimal-scope-regeneration-policy.md) |

**Current use:** FBO chain (CSO → promoted dimension → nominal index) is depth 1; works today.

---

### 2.3 `srf:ExternalIndex` admission criteria — Deferred

**What it is:** Index over an external store without materialisation into the core graph.

**Status:** Declared and rejected (per `bhv:Proportional` precedent — visibly unavailable rather than silently absent).

**What's needed:**
- Way to name the store and index without substrate depending on specific store
- Statement of what "surface is fresh" means when index cannot be hashed
- Decision about whether store-native index can discharge parity (R2) at all

**Timeline:** Left until a deployment actually needs it.

---

## 3. Known Gaps

### 3.1 Foundation migration for derived-artefact contract — ⏳ Decision Needed

See §1.3 above. This is an ADR-scale decision affecting multiple layers.

---

### 3.2 ADR-A01 convention conflict — ✅ Closed

**Resolution:** Ontology header is authored in README's `turtle-spec` fence, per [ADR-A01](../../architecture/decisions/ADR-A01-layer-dependency-order.md#decision). Matches Eligibility, Behaviour, and Surface practice. Foundation, Vocabulary, and Party are outliers to correct.

---

### 3.3 Profile identity is computed, not modelled — ⏳ Blocked

**Current state:** `Profile.identity()` in compiler concatenates profile IRI, generator version, canonicalisation version, entailment regime, naming normalisation, symbol mode, and permitted stack depth. Pure computation, not represented in graph.

**Missing:** `srf:profileIdentityHash` asserted on generated surface would close this.

**Blocker:** Depends on §3.1 Foundation migration decision.

---

### 3.4 Partial implementations

| Item | Status | What's left |
|------|--------|---|
| R2 parity harness | Partial | `tools/surface/parity.py` implements comparison; wiring to shared conformance corpus remains (tracked under [ADR-A28](../../architecture/decisions/ADR-A28-parity-and-conformance-release-gate.md)) |
| MORK `mrk:ProjectionMapping` | ✅ Done | Implemented in `tools/surface/mork.py` bidirectionally against `ontology/mork/spec/Mork.ttl`; see [ADR-A18](../../architecture/decisions/ADR-A18-surface-to-mork-lowering-boundary.md) |
| insure-o port | Blocked | Correctly deferred: insure-o dropping in favour of CSO/FBO port; three non-domain examples exercise every mechanism except range partitions |
| SHACL validation of Surface shapes | Blocked | No SHACL engine in authoring environment; syntactically checked but not executed. Compiler agreement not shape validation. Mandatory CI gate under [ADR-A28](../../architecture/decisions/ADR-A28-parity-and-conformance-release-gate.md) |

---

### 3.5 Compiler Limitations

#### Entailment regimes recorded but not acted on — Deferred

**Current:** Compiler always reads asserted triples. Correct for `srf:NoEntailment`, gap for others.

**Implementation:** `tools/surface/compile.py::check_entailment_regime()` now refuses to compile under anything but NoEntailment, closing the *silent* gap. Reasoner integration for other regimes still not started.

**Decision needed:** Choose a reasoner (owlrl for RDFS/OWL 2 RL, external EL reasoner for nominal form) and decide whether compiler materialises entailments before reading or requires caller to.

#### Parity cannot check `DefinitionOnly` forms — Deferred

**Why:** Parity compares assertions; `DefinitionOnly` surfaces assert nothing. Reports as skipped with regime named rather than silently passed.

**Dependency:** Same as entailment regimes item above.

#### Blank-node labels visible in emitted modules — ✅ Accepted Tradeoff

**Design:** Minted from the term they belong to (`_:RoleAssignment_job-family_Sales_def_l0`).

**Why kept:** Stable diffs for regenerated modules. Hashing no longer depends on this (canonical form relabels blank nodes by position), so this is a style choice per law `srf:R3`.

#### Canonicalisation performance — Watch item

**Status:** `to_canonical_graph` is superlinear on blank-node-bearing graphs. Read-set inputs are almost always blank-node-free (cost is sort). Large `core.ttl` with one blank-node per population member is the case to watch.

**Action if triggered:** Hash per-subject and fold rather than abandoning canonical form.

---

### 3.6 Canonicalisation contract `srf-canon/1` → `srf-canon/2` — ✅ Closed

**Change:** Switched from sorted rendering to `rdflib.compare`'s canonical graph. Blank-node-label independent; graph read from anywhere hashes stably.

**Impact:** All previously recorded hashes are stale by design. Three committed example packages regenerated per `ontology/surface/execution/README.md`.

**Status:** Examples and fixtures declare `srf-canon/2` and generator `0.2.0`. Runbook for future cutovers tracked under [ADR-A27](../../architecture/decisions/ADR-A27-invalidation-and-minimal-scope-regeneration-policy.md).

---

### 3.7 Surface-to-MORK lowering engine (ADR-A18) — ✅ Verified

**Implementation:** `tools/surface/lowering.py` implements deterministic lowering:
- `lower_projection` — for ProjectionContract (no direct-emit form)
- `lower_contract` — for Promotion/Index (when deployment mirrors to MORK)
- `lower_all`/`link_dependencies` — one mapping graph per batch with dependency edges

**Verification:** `python -m unittest surface.test_surface -v` passes 61/61 including:
- ContractLoweringTests
- LoweringDependencyTests
- Projection lowering
- Determinism checks
- MORK interop

**Note on goldens:** No committed lowering output; regenerate with `python -m surface lower --contracts ontology/surface/examples/saas-subscription-arr-projection.ttl` and commit result under `ontology/surface/execution/`.

---

## 4. Findings 15.1–15.5

### 4.1 `elg:boundScheme` did not exist — ✅ Closed

**Fix:** Implemented as option (c), `elg:constrainedByContract`.

**Location:** `ontology/eligibility/spec/eligibility.ttl`, `ontology/eligibility/README.md`, `ontology/eligibility/shapes/rules.ttl`.

---

### 4.2 `elg:HierarchicalClosureRule` unscoped — ✅ Closed

**Fix:** Removed from `ontology/eligibility/shapes/` per [eligibility-L9-replacement.md](../../surface/docs/eligibility-L9-replacement.md).

**Status:** No remaining reference in Eligibility layer.

---

### 4.3 `ins:` vs `ino:` properties — ✅ Closed

**Status:** Dropped; insure-o is being phased out. CSO scopes peril via `hasPerilScope` on `TermApplication`.

---

### 4.4 `fnd:GovernanceState` individuals undeclared — ✅ Closed

**Previous status (wrong):** Marked "Done" — actually was a real gap.

**Fix:** Now declared in `ontology/foundation/vocab/foundation-vocab.ttl` as part of Phase 4 MORK governance work (needed them to be real).

---

### 4.5 `bhv:targetsAllowance` README⇄spec drift — ✅ Closed

**Fix:** Hand-remediated. `tools/lattice_tooling/literate_extract.py --check` catches future drifts.

---

## 5. MORK Toolchain Join Assumptions — ⏳ Decision Needed

`tools/surface/mork.py` and `tools/mork2rml.py` are written against this repository's ontologies. Before production, confirm these assumptions against a live toolchain checkout:

| Assumption | Verification |
|---|---|
| MORK terms at `http://www.nebularis.org/ontologies/Mork#` | ✅ Confirmed: `ontology/mork/spec/Mork.ttl`. `ontology/mork/targets/insure-o-target.ttl` binds `mk:` to lattice namespace — both bound in `namespaces.py`; `MORK` is the one used |
| `mrk:GenerativeMapping`, `DataMapping`, `TargetingSpec`, `ParameterBinding` (paramName/paramType/paramValue), `OwlClass`, `mappingScheme`, `mappingFor`, `reviewStatus`, `provenanceCreated` exist with those names | ⏳ Use grep before first production run; silent failures if renamed |
| `ProjectionMapping`, `generatesClassDefinition`, `ProjectionProvenance`, `hasProjectionProvenance` exist | ✅ Confirmed: `ontology/mork/spec/Mork.ttl` |
| Compiler is sibling of `mork2rml.py` under `tools/`, not in MORK package | ⏳ If toolchain has shared package, `serialise.py` and parts of `namespaces.py` may duplicate utilities |
| `mork_communities/shadow.py` is unrelated | ✅ Confirmed: builds MORK-internal `OwlAxiom` shadows; Surface shadows nothing |

**Open question:** Whether to reuse MORK's `precedes` derivation ordering for Surface's generated-module order (class definitions → memberships → closure relations) instead of `owl:imports`. Currently uses `owl:imports` (surface consumed as unit). If toolchain expects `precedes`, add to manifest.

---

## Document Status

This document is a reference for items deferred, in-progress, or requiring decisions. For phase-level status and verification checklist, see [surface-mork-unified-projection.md](surface-mork-unified-projection.md).

**Last updated:** 2026-09-22  
**Next review:** Upon SWRL verification completion (Phase 8 blocker) or Phase 9 authorization
