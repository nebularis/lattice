<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation and Test Plan

This document records the checks the substrate is expected to satisfy, as they become relevant gate by gate. Checks here are **documented, not built**: no CI workflow exists yet under `.github/workflows`. Building automation for these checks is deliberately deferred until the mechanisms they check are stable enough that the automation itself is not churn.

## Gate 1 — Architecture baseline

| Check | What it verifies | Status |
|---|---|---|
| Import closure | Every layer's `owl:imports` matches the order in [ADR-A01](adr/ADR-A01-layer-dependency-order.md) | Documented, not built |
| No upward reference | No layer's `spec/*.ttl` names a term from a layer above it in the dependency order | Documented, not built |
| Substrate inventory emptiness | Eligibility ships zero `elg:DimensionSet`/`elg:ScopeDimension` individuals; Behaviour ships zero state spaces, states, transitions, or allowances, outside `turtle-example` fences | Documented, not built |
| SPDX/reuse-lint | Every file carries a correct SPDX header as its first non-blank line | Existing project convention (`reuse lint`), unchanged by this plan |
| README ⇄ spec/vocab/shapes consistency | `spec/*.ttl`, `vocab/*-vocab.ttl`, `shapes/*.ttl` are byte-consistent with their README's fenced blocks, concatenated in document order | Documented, not built |

## Gate 2 — Eligibility core correction

| Check | What it verifies | Status |
|---|---|---|
| Retired-name absence | `elg:compatibleWith` and `elg:IntervalOverlap` do not appear in Eligibility substrate artefacts (historical design notes excluded) | Satisfied by Gate 2 authoring |
| Disagreement corpus | At least one fixture where `positiveOverlapCandidate` is non-empty and `coAdmissible` is empty for the same pair | Pending Gate 2 authoring |
| Law discharge | L1–L4, L5a, L5b, L6, L7 discharged for every baseline strategy; L8 discharged for every strategy declaring `supportsExclusion` | Pending Gate 2 authoring |
| Profile parity (E1/E2) | Direct-SPARQL and SHACL evaluation agree on the shared conformance corpus before any generated surface exists | Pending Gate 5 |
| IntervalContainment fixture | At least one admission/meet fixture using `qnt:Range`/`qnt:RangeSet` | Satisfied by Gate 2 authoring (`eligibility/test/E2-interval-containment.ttl`) |

## Gate 2.5 — Minimal Instrument

| Check | What it verifies | Status |
|---|---|---|
| Disjointness | `ins:Element`/`Provision`/`Obligation`/`Qualifier` disjointness holds | Pending Gate 2.5 authoring |
| Versioning/supersession | No in-place mutation of an authored Instrument node; every write produces a new version with a recomputed structural hash | Pending Gate 2.5 authoring |

## Gate 3 — Behaviour declaration model

| Check | What it verifies | Status |
|---|---|---|
| Tier separation | No class serves two of declaration/occurrence/execution/state-record | Pending Gate 3 authoring |
| Effect payload completeness | Every effect operation has a typed payload; every target binding resolves | Pending Gate 3 authoring |
| Extent scope | `Sequential` absorption's conservation law (`total absorbed = min(demand, Σ drawable)`) discharged; `Proportional` absorption is declared-and-unusable, not silently absent | Pending Gate 3 authoring |
| Occupancy invariants | Exactly one current occupancy per participating space; no overlapping non-hypothetical occupancies | Pending Gate 3 authoring |
| Hypothetical isolation | Hypothetical executions write to a separate graph role (ADR-A13); no persisted current occupancy | Pending Gate 3 authoring |

## Gate 4 — Derivation and validation

| Check | What it verifies | Status |
|---|---|---|
| Static constraints | Every constraint in the derivation-product model has at least one working reference realisation (SPARQL, SHACL, or reasoner) with a deliberate-defect fixture | Pending Gate 4 |
| Targeted invalidation | A non-trivial example demonstrates invalidation without full regeneration | Pending Gate 4 |

## Gate 5 — Multi-profile conformance

| Check | What it verifies | Status |
|---|---|---|
| Shared conformance corpus | At least two Eligibility profiles and two Behaviour profiles agree on every outcome in the shared corpus, differing only in excluded non-semantic metadata | Pending Gate 5 |

## Gate 6 — Residual extent completeness

| Check | What it verifies | Status |
|---|---|---|
| Proportional absorption | Two non-domain motivating examples exist before `Proportional` is discharged | Deferred, not yet scheduled |
| Reset-semantics edge cases | Increments above capacity, capped restore, reset-vs-pending-depletion ordering, late/retrospective stimuli, carry-over all specified | Deferred, not yet scheduled |
