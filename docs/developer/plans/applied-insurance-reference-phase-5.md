<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Plan: Applied Insurance Reference — Phase 5, Contract Module

**Unit ID:** `applied-insurance-reference-phase-5`
**Epic:** [applied-insurance-reference](applied-insurance-reference.md)
**Status:** Deferred (epic D2). Starts after Phases 1 to 4 are wired into Open CBAA, and is
detailed then, with ADR A-101.
**Sketch:** [term-parameters.md](../sketches/term-parameters.md)

## Scope

A new contract module (the legacy one is dropped in Phase 1): terms, term parameters and term relations on Instrument, party roles and
derived liability direction in `common/`, and the optional compiled route into Capacity with
parity against the direct route.

## Slices

| Slice | Content | Sketch |
|---|---|---|
| AIR-5.1 | `ctr:TermParameter ⊑ ins:Qualifier`, parameter kind scheme with governed admission (an unadmitted kind is carried but not evaluated) | §3 (T3, T7), §4 |
| AIR-5.2 | limit, retention, defence cost, claims basis, waiting, indemnity and extended reporting parameters | §4 |
| AIR-5.3 | aggregate, occurrence grouping, reinstatement, trigger, collateral, pool share, premium and declaration parameters | §4 |
| AIR-5.4 | term relations and bundle shapes per term function | §3 (T6), §4 |
| AIR-5.5 | party role parameters and direction derivation over roles and the exposure relationship graph, with the D&O example | §7, milestone M4 |
| AIR-5.6 | defect catalogue as shapes | §8 |
| AIR-5.7 | route R2: compile one check family into Capacity runtime forms, parity suite against R1, no write-back | §5, milestone M5 |

5.7 needs L-P5 (substrate track S4) only if the chosen check family groups occurrences. The
default candidate is bind-time authority, which does not.

## Documentation deltas

Contract module README, `ontology/applied/capacity/docs/architecture-overview.md` (the compiled
route and its parity contract), `solution-design-specification.md` (compilation is optional),
`docs/architecture/ontology-architecture.md` §3.

## Exit gate

M4 and M5 demonstrated. TP-Q3 answered.
