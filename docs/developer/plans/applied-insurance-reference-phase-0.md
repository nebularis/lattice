<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Plan: Applied Insurance Reference — Phase 0, Decisions

**Unit ID:** `applied-insurance-reference-phase-0`
**Epic:** [applied-insurance-reference](applied-insurance-reference.md)
**Status:** Complete. AIR-0.1 signed off and merged (`3377a71`). All five ADRs Accepted
**Status record:** the epic [status record](../status/applied-insurance-reference.md) (lanes §5)

## Scope

Ratify the epic's Phase 0 decisions (epic §5.3). No ontology changes. Sketch material motivated by
Open CBAA stays as written (epic D3).

## Slices

### AIR-0.1: ADRs A-98, A-99, A-100, A-102 and A-103

Draft the five ADRs as `Proposed`, add catalogue rows, and write up in them the decisions
already taken: the applied layout (epic §5.2, D5 to D9) in A-98, hierarchical match over flat
schemes and crosswalks (D11) in A-100, with MB-Q3 answered there, and set readings (D12) in
A-103. A-100 and A-103 are substrate decisions and follow ADR-A-C2. In the same slice, make the sketches' citations of
Open CBAA documents (design-spec, integration specification) name that repository.

L0: `mise run topology:links` reports no failure under `docs/developer/sketches/`. Gate: human
ratification of each ADR.

## Documentation deltas

| Document | Change | Slice |
|---|---|---|
| `docs/architecture/decisions/README.md` | rows for A-98, A-99, A-100, A-102, A-103 | 0.1 |
| `docs/developer/INDEX.md` | slice row under the epic entry | 0.1 |

## Exit gate

A-98, A-99, A-100, A-102 and A-103 Accepted, with the sketches in agreement.
