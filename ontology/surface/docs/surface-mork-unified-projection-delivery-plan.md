<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Surface-MORK Unified Projection Architecture and Delivery Plan

Date: 2026-09-18  
Status: Proposed for implementation  
Owner: Surface and MORK maintainers  
Decision class: Architecture and execution roadmap

---

## 1. Executive summary

This plan adopts a single top-level authoring approach for projection in LATTICE:

- Authors write high-level Surface contracts
- The system lowers those contracts into MORK mappings
- MORK remains the provenance-rich, reviewable, versioned, machine-facing mapping graph
- Compiler backends generate executable artefacts such as SPARQL, SHACL, SWRL, RML, and native plans

This is the preferred direction over introducing a third standalone projection language.

The architecture keeps the practical strength of a staged compiler pipeline while reducing author burden and avoiding duplication of mapping semantics.

This version also incorporates still-relevant carry-over work from the earlier outstanding-items remediation plan, and explicitly treats already-completed ProjectionMapping baseline work as closed.

---

## 2. Decision and rationale

### 2.1 Chosen direction

We choose a unified approach that combines the strengths of Option B and Option E:

- **Top-level authoring model**: Surface
- **Lowering model**: Surface contracts compile to MORK mappings
- **Execution model**: staged compiler pipeline from MORK to executable artefacts

This decision means Surface grows to include a third subsystem, Projection, alongside Promotion and Index.

### 2.2 Why this direction

1. It avoids a third mapping language with overlapping purpose.
2. It preserves MORK as the machine contract for governance, provenance, and review.
3. It addresses the original pain point, where direct MORK authoring is too complex for many domain authors.
4. It supports current and future compiler targets, including Eligibility compilation to SPARQL, SHACL, and SWRL.
5. It keeps staged architecture clarity without forcing authors to learn every internal representation.

### 2.3 Architecture principle

Domain authors declare projection intent and semantic bindings in Surface.  
MORK captures compilation-grade mapping detail and provenance.  
Compilers generate deterministic behavioural artefacts from validated graphs.

---

## 3. Comparison of Option B and Option E in this repository context

### 3.1 Option B, Surface as front-end that compiles to MORK

Strengths:

- Minimal new authoring surface for users already learning Surface
- Strong fit with existing Surface contract style and generated artefact model
- Natural place to declare projection intent for Promotion, Index, and Projection uniformly

Risks:

- Surface scope expands and needs strict subsystem boundaries
- Requires careful law and shape updates to prevent semantic blur

### 3.2 Option E, staged hybrid compiler

Strengths:

- Clean internal compiler phases and explicit handoff boundaries
- Good fit for complex transformations including node synthesis and derivation

Risks:

- Can feel like another framework unless authoring remains unified
- May raise conceptual overhead if presented as a separate top-level system

### 3.3 Resolution

Implement both as one architecture:

- **Externally**: Option B user experience, one top-level contract language in Surface
- **Internally**: Option E staged pipeline for determinism, testability, and target fan-out

---

## 4. Target architecture

## 4.1 Surface subsystems

Surface becomes a unified projection contract layer with three explicit subsystems:

1. **Promotion**
   - deterministic restatement onto direct properties
2. **Index**
   - deterministic retrieval surfaces and closure surfaces
3. **Projection**
   - declarative mapping intents that may require graph construction, derivation, joins, and expansions

Projection contracts are authored in Surface and lowered into MORK.

### 4.2 Core pipeline

```text
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
  - MORK to RML
  - MORK to SPARQL
  - MORK to SHACL
  - MORK to SWRL
  - MORK to native execution plan
        ↓
Generated artefacts with provenance, governance, and version records
```

### 4.3 Responsibility split

- **Surface**
  - authoring contract
  - semantic role binding
  - projection intent
  - profile and policy declarations
- **MORK**
  - machine mapping graph
  - explicit dependencies and parameter bindings
  - compiler-ready shape and rule definitions
  - provenance and governance evidence
- **Compilers**
  - deterministic lowering to executable targets
  - backend-specific constraints and diagnostics

---

## 5. Scope and non-goals

### 5.1 In scope

- Surface Projection subsystem specification and implementation
- Surface-to-MORK lowering compiler
- MORK governance and versioning hardening
- Eligibility executable compilation flow from Surface and MORK to SPARQL, SHACL, SWRL, and native IR
- Conformance, parity, and invalidation support across the full pipeline
- Outstanding-items truth-source normalization and status reconciliation in Surface docs
- ADR convention conflict resolution and Foundation migration boundary decisions that directly affect implementation
- Deferred-feature operationalization for explicitly unavailable features such as ExternalIndex

### 5.2 Out of scope for first tranche

- Full automated migration of all legacy projection assets without review
- Full support for all Quantification edge cases in initial SWRL generation
- New deployment platform features unrelated to mapping and compilation

### 5.3 Explicitly closed items

The following are treated as already remediated and are excluded from active delivery scope except for documentation hygiene:

- MORK ProjectionMapping baseline presence in ontology and Surface interop path
- Eligibility `elg:constrainedByContract` carry-through
- Eligibility L9 shape replacement and closure-law reshaping

---

## 6. Proposed Surface Projection model

### 6.1 Contract shape

Add `srf:ProjectionContract` with author-facing fields aligned to existing Surface design language.

Minimum required fields:

- carrier class
- source semantic operation or projection kind
- source read or binding roles
- target namespace and target binding policy
- fidelity and authority declarations
- realisation mode and profile
- backend request policy

### 6.2 Projection role binding

Add explicit role-binding resources to avoid ambiguous path interpretation in complex projections.

Representative roles:

- evaluation subject
- candidate evidence
- required evidence source
- result target
- closure basis where relevant
- transform dependency references

### 6.3 Projection policy controls

Add policy fields that drive lowering and backend eligibility:

- backend allow-list and deny-list
- deterministic-only mode toggle
- LLM-completion allowed or disallowed
- template allow-list
- source-signature policy and fidelity gating

---

## 7. Surface to MORK lowering design

### 7.1 Lowering outputs

For each `srf:ProjectionContract`, lowering emits one or more MORK mapping nodes:

- `mork:DataMapping` for semantic linkage
- `mork:ShapeMapping` for validation artefacts
- `mork:RuleMapping` for inference artefacts
- `mork:QueryTemplate` for SPARQL evaluation artefacts
- `mork:TransformMapping` or equivalent for graph construction targets
- `mork:ProjectionMapping` where class generation is required

### 7.2 Deterministic lowering requirements

Lowering must be deterministic for identical validated input graph and profile identity.

Required invariants:

1. stable lowering order
2. stable identifier minting policy
3. stable parameter binding order
4. stable dependency graph derivation
5. stable provenance field population

### 7.3 LLM role in lowering

LLM usage is optional and policy bound.

- deterministic mode: no LLM completion
- bounded completion mode: LLM may fill only declared gaps using approved templates and ontology signals
- every LLM completion is materialised as explicit proposed graph nodes and requires governance state before production

---

## 8. MORK enhancements required

This section combines current MORK direction and the MorkEnhancements plan in Surface docs.

### 8.1 Governance and versioning integration

Add first-class versioning and governance semantics to MORK using Foundation alignment.

Plan:

1. add Foundation import in MORK ontology
2. add governance state links for mappings and generated artefacts
3. add version identity and supersession fields for mapping sets
4. add effective time windows for mapping applicability
5. add migration shapes that require governance state in production compile mode

### 8.2 Compiler family completion

Extend from current RML-focused compiler toward full family:

- MORK to RML, existing and enhanced
- MORK to SPARQL, new
- MORK to SHACL, new
- MORK to SWRL, new
- MORK to native execution IR, new

### 8.3 Artefact taxonomy completion

Maintain parity in first-class provenance-bearing status across all generated artefact families including RML, SHACL, SWRL, SPARQL, and native plans.

### 8.4 ProjectionMapping maturity

Harden `ProjectionMapping` support end-to-end:

- ontology terms and constraints
- lowering support
- compiler dispatch support
- provenance and dependency support
- conformance tests

---

## 9. Eligibility executable roadmap integration

### 9.1 Authoring model

Eligibility remains declarative in Eligibility and Quantification layers.  
Surface Projection contracts provide domain binding and operational intent.  
MORK captures compiler-grade executable mapping.

### 9.2 Semantic core

Adopt shared executable IR for Eligibility operations to avoid backend divergence.

IR must support:

- interval containment
- three-valued outcomes, permitted denied undetermined
- diagnostics with source trace
- profile aggregation policies, all-required and any-sufficient
- missing evidence and incompatibility handling

### 9.3 Backend delivery order

1. native evaluator and SPARQL
2. SHACL for readiness and diagnostics
3. SWRL for positive monotonic classifications where semantics fit

### 9.4 Eligibility specific MORK templates

Define approved template catalog for Eligibility lowering:

- interval-containment query template
- interval-readiness shape template
- scalar-range SWRL template
- profile-aggregation query template

---

## 10. Full implementation plan

## Phase 0, architecture lock and ADR updates

Deliverables:

1. ADR confirming Surface as unified top-level projection authoring layer
2. ADR confirming staged compilation model and Surface-to-MORK lowering
3. ADR confirming MORK governance and versioning adoption path with Foundation import
4. glossary updates for Projection subsystem terminology

Exit criteria:

- decision signed off by maintainers
- no unresolved architectural blockers

## Phase 1, Surface Projection specification

Deliverables:

1. Normalize `surface/docs/OUTSTANDING-ITEMS.md` and `surface/docs/OUTSTANDING-ITEMS 2.md` into one authoritative status source with `Done / Deferred / Decision needed / Blocked` tags.
2. Freeze and mark already-remediated entries as closed, including ProjectionMapping and Eligibility L9-related carry-overs.
3. ADR confirming Surface as unified top-level projection authoring layer
4. ADR confirming staged compilation model and Surface-to-MORK lowering
5. ADR confirming MORK governance and versioning adoption path with Foundation import
6. ADR-A01 convention resolution decision for README-vs-spec header authoring and extraction workflow
7. glossary updates for Projection subsystem terminology

Exit criteria:

- decision signed off by maintainers
- no unresolved architectural blockers
- outstanding-items source-of-truth document published and linked from Surface docs

## Phase 1, Surface Projection specification and policy carry-over

Deliverables:

1. `srf:ProjectionContract` and related vocabulary in Surface spec and vocab
2. structural and constraints shapes for Projection contracts
3. laws for projection fidelity and signature scope composition
4. profile fields for backend policy and LLM completion policy
5. examples in Surface examples directory
6. `srf:ExternalIndex` deferral policy encoded as explicit admission criteria and non-goals in Surface docs and constraints
7. ADR-A01 convention decision applied consistently across Surface, Eligibility, and Behaviour README extraction patterns

Exit criteria:

- shapes parse and pass against valid examples
- invalid fixture corpus covers all new constraint failures

## Phase 2, Surface compiler refactor and entailment policy

Deliverables:

1. compiler split into modular pipeline stages
2. normalisation stage for all contract kinds
3. lowering stage interfaces for MORK and direct emit
4. explicit profile identity hashing across all stages
5. deterministic minting shared utility
6. explicit entailment-regime handling policy for `NoEntailment` and reasoned modes, including DefinitionOnly parity strategy

Exit criteria:

- existing Promotion and Index outputs unchanged for same inputs
- deterministic regeneration tests pass

## Phase 3, Surface to MORK lowering engine

Deliverables:

1. lowering rules from Projection contracts to MORK graph patterns
2. lowering support for Promotion and Index to MORK where configured
3. emitted mapping dependency graph
4. emitted parameter bindings and targeting specs
5. emitted mapping provenance including source contract linkage

Exit criteria:

- lowering goldens for representative Projection scenarios
- MORK validation passes on lowered graphs

## Phase 4, MORK governance and versioning enhancements

Deliverables:

1. Foundation import in MORK ontology
2. governance state and review-state constraints for production mode
3. mapping set versioning and supersession model
4. effective time constraints for mapping applicability
5. migration docs for existing MORK assets
6. Foundation migration boundary record for derived-artefact contract placement and layer-local vs foundation-owned responsibilities

Exit criteria:

- governance validation test suite green
- backward compatibility story documented and tested

## Phase 5, compiler family implementation

Deliverables:

1. MORK to SPARQL compiler
2. MORK to SHACL compiler
3. MORK to SWRL compiler
4. MORK to native IR compiler
5. shared compiler core for parameter resolution and precedence derivation

Exit criteria:

- generated artefacts validated by target parsers
- provenance records complete and queryable

## Phase 6, Eligibility tranche

Deliverables:

1. executable IR for Eligibility interval semantics
2. lowering templates for interval containment from Surface to MORK
3. SPARQL decision backend for three-valued output and diagnostics
4. SHACL readiness and diagnostic backend
5. SWRL positive classification backend for supported scalar cases
6. range-partition two-track remediation plan wired to implementation backlog, Quantification partition semantics first, Surface admission second

Exit criteria:

- interval containment conformance corpus passes
- parity checks between native and SPARQL backends pass
- known unsupported semantics produce undetermined with diagnostic codes

## Phase 7, provenance and invalidation hardening

Deliverables:

1. full provenance chain from generated result to source contracts and source declaration nodes
2. read-set capture across Surface, MORK, and generated artefacts
3. invalidation policy for graph changes, profile changes, and mapping version changes
4. regeneration planner for minimal impacted rebuild
5. canonicalisation cutover runbook for profile migrations including stale-surface expectations and regeneration order

Exit criteria:

- end-to-end trace query works across at least three sample domains
- invalidation tests prove minimal-scope regeneration

## Phase 8, conformance and parity framework

Deliverables:

1. shared conformance corpus extension for Projection subsystem
2. parity harness for source versus generated query behaviour
3. regression gates in CI for deterministic output and parity
4. defect fixtures for known edge classes
5. SHACL execution gates and extraction-drift checks as mandatory CI checks

Exit criteria:

- CI gates active
- parity failures block release
- SHACL and extraction drift failures block release

## Phase 9, migration and rollout

Deliverables:

1. migration guides for existing Surface and MORK authors
2. compatibility mode and deprecation policy
3. phased rollout profiles, draft, review, production
4. release checklist and change management docs

Exit criteria:

- one pilot domain migrated
- rollback path tested

## Phase 10, scale and optimisation

Deliverables:

1. performance baselines for lowering and compilers
2. caching strategy for intermediate graphs
3. large vocabulary and large population stress tests
4. profile for high-throughput generation mode

Exit criteria:

- target performance SLOs met
- no correctness regressions under load

---

## 11. Repository change plan by area

### 11.1 Surface layer

- `surface/README.md`
- `surface/spec/surface.ttl`
- `surface/vocab/surface-vocab.ttl`
- `surface/shapes/structural.ttl`
- `surface/shapes/constraints.ttl`
- `surface/examples/*`
- `surface/docs/OUTSTANDING-ITEMS.md`
- `surface/docs/OUTSTANDING-ITEMS 2.md`
- `tools/surface/*`

### 11.2 MORK layer

- `mork/spec/Mork.ttl`
- `mork/spec/Mork.owl`
- `mork/README.md`
- `mork/src/python/*` compilers and validators

### 11.3 Eligibility and executable integration

- `eligibility/*` for declarative sources and examples
- `surface/docs/MorkEnhancements.md` as detailed source plan
- new executable semantics documents under Surface or dedicated executable layer once agreed

### 11.4 Cross-layer governance and conventions

- `docs/adr/ADR-A01-layer-dependency-order.md`
- `docs/adr/ADR-A12-identity-and-derivation-model.md`
- `foundation/README.md`
- `behaviour/README.md`
- `tools/literate_extract.py`

---

## 12. Acceptance criteria

## 12.1 Authoring experience

1. A domain author can produce valid projection intent without writing raw MORK internals.
2. The same projection contract can generate at least two backend artefact families.
3. Authoring docs are sufficient for first successful compile in one session.

## 12.2 Correctness

1. deterministic regeneration for identical inputs
2. parity between source semantics and generated artefacts within declared profile
3. traceable provenance from decision or output artefact to source contracts and declarations

## 12.3 Governance

1. production compile mode rejects unapproved mappings or templates
2. mapping version and effective date policies are enforced
3. review state and provenance completeness are queryable by policy checks

## 12.4 Eligibility readiness

1. interval containment and profile aggregation work end-to-end
2. undetermined outcomes are explicit and diagnostic-backed
3. SPARQL and native backends agree on benchmark corpus

---

## 13. Risk register and mitigations

1. **Risk** Surface scope expansion causes conceptual drift  
   **Mitigation** strict subsystem boundaries, separate shapes, separate laws, separate compiler modules

2. **Risk** MORK governance changes break compatibility  
   **Mitigation** compatibility profile mode, migration scripts, staged validation levels

3. **Risk** Backend semantics divergence  
   **Mitigation** shared executable IR and parity tests

4. **Risk** LLM completion introduces unstable mappings  
   **Mitigation** deterministic mode default in production, governance gate for LLM-derived nodes

5. **Risk** Performance cost at scale  
   **Mitigation** phase 10 optimisation plan with cache and incremental regeneration

---

## 14. Governance model and release gates

Define three operational modes:

1. **Draft mode**
   - allows unapproved templates and optional LLM completion
2. **Review mode**
   - requires explicit review state and provenance completeness
3. **Production mode**
   - deterministic lowering only unless explicitly permitted
   - approved governance state required for mappings and templates
   - release parity gates enforced

A release cannot pass production gate without:

- deterministic hash stability checks
- parity suite pass
- provenance completeness pass
- governance state pass

---

## 15. Implementation sequencing and team split

### 15.1 Team workstreams

1. Surface spec and shapes
2. Surface compiler and lowering
3. MORK ontology and governance
4. Compiler backends
5. Eligibility semantic core
6. Conformance and CI

### 15.2 Suggested execution order

1. Phase 0 and 1 in parallel with Phase 4 design prep
2. Phase 2 and 3 once Surface spec is stable
3. Phase 4 before production usage of lowered mappings
4. Phase 5 and 6 in parallel after lowering reaches beta
5. Phase 7 and 8 before first production rollout
6. Phase 9 and 10 after pilot acceptance

---

## 16. Immediate next actions

1. Approve this architecture direction and phase plan.
2. Publish a single outstanding-items status source and mark closed items explicitly.
3. Open ADR set for Surface Projection subsystem and Surface-to-MORK lowering.
4. Open MORK governance enhancement epic with Foundation import task.
5. Start Surface Projection spec draft in `surface/spec` and `surface/vocab`.
6. Start lowering prototype for one Eligibility interval example from Surface to MORK to SPARQL.

---

## 18. Carry-over merge checklist from older remediation plan

This checklist records where still-relevant items from the earlier remediation plan now live.

| Older remediation concern | Status in this plan |
|---|---|
| Outstanding-items source normalization | Added to Phase 0 and repository plan |
| Freeze already-remediated ProjectionMapping and Eligibility L9 carry-over | Added as explicit closed scope and Phase 0 task |
| X6 governance decision and ADR alignment | Already covered by architecture lock ADR wave and retained |
| ADR-A01 README/spec convention conflict | Added to Phase 0 and Phase 1 deliverables |
| Foundation migration boundary for derived artefacts | Added to Phase 4 deliverables |
| RangePartitionPopulation two-track remediation | Added to Phase 6 deliverables |
| Stacking law formalization beyond depth 1 | Already covered under Phase 1 and Phase 2 law and compiler work |
| ExternalIndex deferred with explicit criteria | Added to Phase 1 deliverables |
| Shared conformance corpus parity integration | Already covered under Phase 8 and retained |
| Entailment-regime remediation strategy | Added to Phase 2 deliverables |
| Canonicalisation cutover runbook | Added to Phase 7 deliverables |
| Mandatory SHACL and extraction drift CI gates | Added to Phase 8 deliverables and exit criteria |

---

## 17. Definition of done for this programme

The programme is complete when all of the following hold:

1. Authors can declare projection intent in Surface without writing raw MORK graph internals.
2. Surface contracts lower deterministically into valid, governance-compliant MORK mappings.
3. MORK compilers generate and validate at least SPARQL, SHACL, SWRL, RML, and native IR artefacts.
4. Eligibility interval and profile semantics execute correctly with three-valued outcomes and diagnostics.
5. Full provenance, versioning, governance, parity, and invalidation controls are enforced in production mode.
