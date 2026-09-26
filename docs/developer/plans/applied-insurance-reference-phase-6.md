<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Plan: Applied Insurance Reference — Phase 6, Submission and Claims

**Unit ID:** `applied-insurance-reference-phase-6`
**Epic:** [applied-insurance-reference](applied-insurance-reference.md)
**Status:** Rolling-wave outline. AIR-6.1 is detailed at the Phase 4 gate. AIR-6.2 onwards wait
for Phase 5 (epic D2).
**Sketches:** [asset-exposure-ontology.md](../sketches/asset-exposure-ontology.md) §1,
[peril-structure-whitepaper.md](../sketches/peril-structure-whitepaper.md) §5 (N7, N10), [term-parameters.md](../sketches/term-parameters.md) §7

## Scope

`submission/` packages an exposure set version, requirements and existing cover for one
placement. `claims/` records claims, loss cause chains and the filling of claimant, harmed and
payee roles against the responding contract.

## Slices

| Slice | Content |
|---|---|
| AIR-6.1 | submission package, its lifecycle and its citation of an exposure set version |
| AIR-6.2 | claim, loss cause chain (initiating, proximate, mechanism), role occupancies filled at notification |
| AIR-6.3 | occurrence grouping into events by anchored window, if substrate track S4 has landed. Otherwise deferred |
| AIR-6.4 | causation profiles selected by governing law, only after W-Q2's legal review |

Milestone M6 closes in 6.1 and 6.2.

## Exit gate

M6 demonstrated. W-Q2 and W-Q3 answered or carried as open items in the module READMEs.
