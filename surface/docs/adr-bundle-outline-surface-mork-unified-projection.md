<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# ADR bundle outline — Surface-MORK unified projection

Date: 2026-09-18  
Status: Draft outline for authoring  
Source plan: [surface-mork-unified-projection-delivery-plan.md](surface-mork-unified-projection-delivery-plan.md)

---

## 1. Purpose

This bundle defines the ADR set needed to implement the Surface-MORK unified projection direction.

The intent is to:

- keep one top-level authoring model in Surface
- lower deterministically into MORK for machine-grade mappings
- preserve staged compilation to multiple executable backends
- harden governance, versioning, provenance, parity, and invalidation

This is an outline only, not the ADR bodies.

---

## 2. Proposed ADR set

Numbering below assumes continuation from A-16. If repository maintainers prefer a different scheme, retain titles and dependency order.

| Proposed ADR | Title | Initial status | Core decision |
|---|---|---|---|
| A-17 | Surface unified projection authoring model | Proposed | Surface is the top-level authoring layer for Promotion, Index, and Projection contracts. |
| A-18 | Surface-to-MORK lowering boundary | Proposed | Surface contracts lower to MORK as the canonical machine mapping graph. |
| A-19 | Staged compiler architecture and backend fan-out | Proposed | Compilers operate in deterministic stages from validated graphs to target artefacts. |
| A-20 | Projection subsystem semantics and law model | Proposed | Introduce Projection as a first-class Surface subsystem with explicit laws and constraints. |
| A-21 | Signature-scope and conservativity composition in stacked surfaces | Proposed | Define composition rules for `LocalSignature` and `SourceSignature` through stack depth. |
| A-22 | MORK governance and versioning with Foundation alignment | Proposed | MORK adopts governance state and versioning contract, aligned with Foundation. |
| A-23 | MORK compiler family completion policy | Proposed | RML, SPARQL, SHACL, SWRL, and native IR are first-class compiler targets. |
| A-24 | Eligibility executable semantics and backend strategy | Proposed | Eligibility compiles via shared IR to SPARQL and SHACL first, SWRL where semantically safe. |
| A-25 | LLM participation and deterministic production gate | Proposed | LLM is proposal-only under policy; production can enforce deterministic lowering only. |
| A-26 | Provenance chain completeness across Surface, MORK, and artefacts | Proposed | Every generated artefact and runtime result must expose full graph-native provenance chain. |
| A-27 | Invalidation and minimal-scope regeneration policy | Proposed | Regeneration is dependency-scoped and profile-aware, never broad by default. |
| A-28 | Parity and conformance gate for generated behaviours | Proposed | Generated outputs must pass parity and conformance corpus checks before release. |

---

## 3. ADR dependencies and sequence

## Wave 1 — architecture lock

1. **A-17** Surface unified projection authoring model
2. **A-18** Surface-to-MORK lowering boundary
3. **A-19** staged compiler architecture

Reason: these define the non-reversible architecture spine.

## Wave 2 — semantic and governance hardening

4. **A-20** Projection subsystem semantics
5. **A-21** signature-scope composition
6. **A-22** MORK governance and versioning

Reason: these prevent semantic drift and governance gaps during implementation.

## Wave 3 — compiler target commitments

7. **A-23** compiler family completion
8. **A-24** Eligibility executable strategy
9. **A-25** LLM and deterministic gate

Reason: these constrain implementation order and production policy.

## Wave 4 — operational guarantees

10. **A-26** provenance completeness
11. **A-27** invalidation and regeneration
12. **A-28** parity and conformance gate

Reason: these define release readiness and runtime trust.

---

## 4. ADR-by-ADR outline

Each subsection gives scope and completion intent for the eventual ADR body.

## A-17 — Surface unified projection authoring model

### Context

- Existing Surface supports Promotion and Index.
- New delivery direction requires top-level projection authoring without introducing a separate third language.

### Decision

- Surface formally includes Promotion, Index, and Projection subsystems.

### Consequences to capture

- Surface contract vocabulary expands.
- Existing Surface contracts remain valid.
- Projection contracts become first-class authoring units.

### Acceptance checks

- Surface spec and vocab include Projection core classes and relations.
- Structural shapes validate all three subsystems.

## A-18 — Surface-to-MORK lowering boundary

### Context

- MORK is machine-facing and provenance-rich.
- Domain authors should not need to author full MORK internals.

### Decision

- Surface contracts are lowered deterministically into MORK mappings.

### Consequences to capture

- MORK remains canonical execution mapping graph.
- Surface remains semantic authoring surface.
- Lowering output must satisfy MORK completeness checks.

### Acceptance checks

- Lowering emits valid `DataMapping`, `ShapeMapping`, `RuleMapping`, `QueryTemplate`, `ProjectionMapping` where needed.

## A-19 — Staged compiler architecture and backend fan-out

### Context

- Multiple backends are required with shared semantics.

### Decision

- Enforce staged pipeline: validate, normalise, lower, compile, emit, record provenance.

### Consequences to capture

- Backends share stable intermediate model.
- Deterministic output constraints apply at each stage.

### Acceptance checks

- Stage interfaces are explicit and testable.
- Same input and profile produce identical outputs.

## A-20 — Projection subsystem semantics and law model

### Context

- Projection introduces richer mapping behavior than Promotion and Index.

### Decision

- Projection laws and constraints are explicit, with clear separation from existing Surface laws.

### Consequences to capture

- New law register entries and constraints.
- New defect fixtures for projection-specific invalid states.

### Acceptance checks

- Projection laws are represented in vocab and enforced in compiler and shapes.

## A-21 — Signature-scope and conservativity composition in stacked surfaces

### Context

- Existing X6 captures signature discipline for promotions.
- Stack-depth composition rules need formalization.

### Decision

- Composition rule for signature scope is defined and enforced.

### Consequences to capture

- `SourceSignature` propagation through stacks.
- Conservativity claims become conditional on composed scope.

### Acceptance checks

- Compiler computes composed signature scope deterministically.
- Tests cover mixed local and source signature stacks.

## A-22 — MORK governance and versioning with Foundation alignment

### Context

- MORK currently captures mapping richness but needs stronger governance and version contracts.

### Decision

- Align MORK with Foundation-level governance and versioning model.

### Consequences to capture

- import and compatibility impacts
- production compile gating by governance state
- mapping supersession and effective date rules

### Acceptance checks

- MORK shapes enforce governance and version presence in production mode.

## A-23 — MORK compiler family completion policy

### Context

- RML has active support and other target families are planned.

### Decision

- SHACL, SWRL, SPARQL, and native IR are promoted to first-class compiler families.

### Consequences to capture

- common artefact taxonomy and provenance schema
- shared compiler core and target adapters

### Acceptance checks

- each target has minimum viable compiler and fixture coverage.

## A-24 — Eligibility executable semantics and backend strategy

### Context

- Eligibility declarations require executable realization beyond OWL entailment.

### Decision

- Shared executable IR drives backend generation.
- Delivery order is native and SPARQL, then SHACL, then SWRL for safe monotonic subsets.

### Consequences to capture

- three-valued decisions are first-class
- diagnostics are mandatory
- unsupported semantics return undetermined, not silent denial

### Acceptance checks

- interval-containment and profile aggregation pass conformance corpus.

## A-25 — LLM participation and deterministic production gate

### Context

- LLM assistance is valuable but must not weaken production determinism and governance.

### Decision

- LLM output is proposal-grade unless policy elevates it after review.
- deterministic-only mode is available and recommended for production.

### Consequences to capture

- review-state requirements for LLM-originated graph nodes
- policy profile fields for LLM participation

### Acceptance checks

- production gate rejects non-compliant LLM-originated mappings.

## A-26 — Provenance chain completeness across Surface, MORK, and artefacts

### Context

- Traceability must span from source declarations to runtime decisions.

### Decision

- Full provenance chain is mandatory for generated plans, artefacts, and runtime outputs.

### Consequences to capture

- source-node links in every phase
- provenance completeness checks in CI

### Acceptance checks

- one query can trace decision to source contract and declaration nodes.

## A-27 — Invalidation and minimal-scope regeneration policy

### Context

- Changes should trigger the smallest safe rebuild set.

### Decision

- dependency-scoped invalidation and regeneration rules are normative.

### Consequences to capture

- read-set and profile identity are part of regeneration planning
- profile changes trigger larger rebuild by design

### Acceptance checks

- fixture tests prove minimal-scope regeneration.

## A-28 — Parity and conformance gate for generated behaviours

### Context

- Generated outputs require behaviour parity with declared source semantics.

### Decision

- parity and conformance become release gates for relevant profiles.

### Consequences to capture

- shared corpus ownership and evolution model
- release block semantics on parity failure

### Acceptance checks

- CI gates fail on parity regressions.

---

## 5. Mapping to delivery plan phases

| Delivery phase | Primary ADR anchors |
|---|---|
| Phase 0 architecture lock | A-17, A-18, A-19 |
| Phase 1 Surface Projection specification | A-17, A-20, A-21 |
| Phase 2 Surface compiler refactor | A-19, A-21 |
| Phase 3 Surface to MORK lowering | A-18, A-19 |
| Phase 4 MORK governance and versioning | A-22 |
| Phase 5 compiler family implementation | A-23 |
| Phase 6 Eligibility tranche | A-24, A-25 |
| Phase 7 provenance and invalidation | A-26, A-27 |
| Phase 8 conformance and parity | A-28 |
| Phase 9 migration and rollout | A-22, A-25, A-28 |
| Phase 10 scale and optimisation | A-19, A-27 |

---

## 6. Suggested authoring order and lightweight timeline

1. Author A-17 to A-19 first and circulate for architecture sign-off.
2. Author A-20 to A-22 before projection subsystem implementation reaches beta.
3. Author A-23 to A-25 before first multi-backend release candidate.
4. Author A-26 to A-28 before production gate activation.

---

## 7. Proposed next file targets for full ADRs

When you are ready to proceed, suggested ADR file names under `docs/adr`:

- `ADR-A17-surface-unified-projection-authoring-model.md`
- `ADR-A18-surface-to-mork-lowering-boundary.md`
- `ADR-A19-staged-compiler-architecture-and-backend-fanout.md`
- `ADR-A20-projection-subsystem-semantics-and-laws.md`
- `ADR-A21-signature-scope-composition-for-stacked-surfaces.md`
- `ADR-A22-mork-governance-and-versioning-foundation-alignment.md`
- `ADR-A23-mork-compiler-family-completion-policy.md`
- `ADR-A24-eligibility-executable-semantics-backend-strategy.md`
- `ADR-A25-llm-participation-and-deterministic-production-gate.md`
- `ADR-A26-provenance-chain-completeness-across-surface-mork-artefacts.md`
- `ADR-A27-invalidation-and-minimal-scope-regeneration-policy.md`
- `ADR-A28-parity-and-conformance-release-gate.md`

This outline intentionally stops at bundle definition as requested.
