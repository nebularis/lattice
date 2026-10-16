<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Plan: Applied Insurance Reference — Phase 5, Contract Module

**Unit ID:** `applied-insurance-reference-phase-5`
**Epic:** [applied-insurance-reference](applied-insurance-reference.md)
**Status:** Deferred (epic D2). Starts after Phases 1 to 4 are wired into Open CBAA and after
[computable-contract-substrate](computable-contract-substrate.md) C9 (ADR-A104 Instrument and
ADR-A112 Wording) is merged, and is detailed then, with ADR A-101 built on A-104 (epic §3b). NRS N4
moved into that unit on 2026-09-30.
**Sketch:** [term-parameters.md](../sketches/term-parameters.md)

## Scope

A new contract module (the legacy one is dropped in Phase 1): terms, term parameters and term relations on Instrument, party roles and
derived liability direction in `common/`, and the optional compiled route into Capacity with
parity against the direct route.

**Changed by CCS (2026-09-30).** The contract module builds on the Wording layer (policy wordings,
forms, endorsements as wording amendments) and the rewritten Instrument (`ins:Term`, the legal
relation classes, templates). `ctr:TermParameter ⊑ ins:Qualifier` qualifies an `ins:Term` or a
legal relation, not an `ins:Provision` (retired). Amount semantics come from
[contract-amounts.md](../sketches/contract-amounts.md).

**Changed by CCS CC-D8 (2026-10-01).** Insurance regimes (policy period, discovery period, run-off,
suspension) are templates on the CCS template library (C8a), not new classes. Bases (per occurrence,
per claim, aggregate windows, hours clauses) stay on term parameters as designed, and the substrate's
general basis pattern, if any, comes from contract-amounts §1.7. The running totals against a limit
are dynamic and live in `applied/capacity` through a Surface projection.

**Comes back in: the evaluation context (2026-10-02).** The unplanned
[evaluation-context.md](../sketches/evaluation-context.md) sketch outlines limits, retentions,
aggregates, reinstatements and bases as ledger accounts, combinators and environments. This phase
should not start its contract module until that design is settled (its §13).

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
| AIR-5.8 | insurance renderings of the policy scenarios of the CCS sketch §10 (the PKG rows: S10 to S14, S18 to S26, S28, S29, S33, S34, S37, S42 and the shared rows), as examples with expected decisions | CCS sketch §9, §10 |
| AIR-5.9 | the LMA WIM profile in `applied/insurance/wording/` (CCS decision CC-D3): the four levels as element types, their containment rules as shapes, the LMA typing schemes and `applicableTo`. Open CBAA imports it | CCS sketch §3.2, CCS plan §7 |

**AIR-5.9 proposed to move (2026-10-05).** The [insurml-alignment](insurml-alignment.md) epic
proposes to build the LMA WIM profile with InsurML in view, as its Phase 1, before this phase starts,
since the profile needs Wording and not Instrument. The move waits for decision IMA-D2.

5.7 needs L-P5 (substrate track S4) only if the chosen check family groups occurrences. The
default candidate is bind-time authority, which does not.

## Documentation deltas

Contract module README, `ontology/applied/capacity/docs/architecture-overview.md` (the compiled
route and its parity contract), `solution-design-specification.md` (compilation is optional),
`docs/architecture/ontology-architecture.md` §3.

## Exit gate

M4 and M5 demonstrated. TP-Q3 answered.
