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
| Hierarchical closure fixture | A concept hierarchy bound to a `HierarchicalMatch` condition materialises local `skos:broaderTransitive` closure without depending on runtime `skos:broader*` traversal | Satisfied by Gate 2 completion of `eligibility/shapes/rules.ttl` and the hierarchical example fixture |

## Gate 2.5 — Minimal Instrument

| Check | What it verifies | Status |
|---|---|---|
| Disjointness | `ins:Element`/`Provision`/`Obligation`/`Qualifier` disjointness holds | Satisfied by Gate 2.5 authoring (`instrument/spec/instrument.ttl`) |
| Versioning/supersession | No in-place mutation of an authored Instrument node; every write produces a new version with a recomputed structural hash | Satisfied by Gate 2.5 authoring (`instrument/README.md`, `instrument/shapes/constraints.ttl`) |

## Gate 3 — Behaviour declaration model

| Check | What it verifies | Status |
|---|---|---|
| Tier separation | No class serves two of declaration/occurrence/execution/state-record | Satisfied by Gate 3 authoring (`ADR-A08`, `behaviour/spec/behaviour.ttl`) |
| Effect payload completeness | Every effect operation has a typed payload; every target binding resolves | Satisfied by Gate 3 authoring (`ADR-A11`, `behaviour/spec/behaviour.ttl`, `behaviour/projection/*.ttl`) |
| Extent scope | `Sequential` absorption's conservation law (`total absorbed = min(demand, Σ drawable)`) discharged; `Proportional` absorption is declared-and-unusable, not silently absent | Partially satisfied by Gate 3 authoring. `Sequential` is modelled and fixture-backed in `behaviour/test/B-P2-sequential-allowance.ttl`; `Proportional` is declared and rejected by `behaviour/shapes/constraints.ttl`. Formal conservation-law discharge remains for Gate 4/5. |
| Allowance-target binding | Any `EffectDefinition` with `bhv:targetKind bhv:AllowanceTarget` must also declare `bhv:targetsAllowance` to the actual allowance it is directed at | Satisfied by Gate 3 completion of the `bhv:targetsAllowance` property and `behaviour/shapes/constraints.ttl` check. |
| Occupancy invariants | Exactly one current occupancy per participating space; no overlapping non-hypothetical occupancies | Satisfied at declaration level by Gate 3 constraints (`behaviour/shapes/constraints.ttl`). Full temporal-overlap discharge remains for executable profiles. |
| Hypothetical isolation | Hypothetical executions write to a separate graph role (ADR-A13); no persisted current occupancy | Satisfied at model level by Gate 3 authoring (`ADR-A13`, `behaviour/spec/behaviour.ttl`, `behaviour/shapes/constraints.ttl`) |

## Gate 4 — Derivation and validation

| Check | What it verifies | Status |
|---|---|---|
| Static constraints | Every constraint in the derivation-product model has at least one working reference realisation (SPARQL, SHACL, or reasoner) with a deliberate-defect fixture | Satisfied by Gate 4 reference corpus ([docs/architecture/derivation-and-validation.md](architecture/derivation-and-validation.md), [test/gate4/](../test/gate4/)) |
| Targeted invalidation | A non-trivial example demonstrates invalidation without full regeneration | Satisfied by Gate 4 operational guidance and derivation reference ([docs/operational-guidance.md](operational-guidance.md), [docs/architecture/derivation-and-validation.md](architecture/derivation-and-validation.md)) |

## Gate 5 — Multi-profile conformance

| Check | What it verifies | Status |
|---|---|---|
| Shared conformance corpus | At least two Eligibility profiles and two Behaviour profiles agree on every outcome in the shared corpus, differing only in excluded non-semantic metadata | Satisfied by Gate 5 corpus definition ([test/conformance/README.md](../test/conformance/README.md), [test/conformance/manifest.ttl](../test/conformance/manifest.ttl)). Automation and replay remain documented, not built. |

## Gate 6 — Residual extent completeness

| Check | What it verifies | Status |
|---|---|---|
| Proportional absorption | Two non-domain motivating examples exist before `Proportional` is discharged | Deferred by design, with prerequisites now recorded in [docs/architecture/deferred-scope-and-boundaries.md](architecture/deferred-scope-and-boundaries.md) |
| Reset-semantics edge cases | Increments above capacity, capped restore, reset-vs-pending-depletion ordering, late/retrospective stimuli, carry-over all specified | Deferred by design, with scope boundary now recorded in [docs/architecture/deferred-scope-and-boundaries.md](architecture/deferred-scope-and-boundaries.md) |

Gate 6 is therefore a close-out gate, not a semantics-expansion gate. It records the exact prerequisites for reopening deferred extent work and keeps the current public substrate contract unambiguous.
