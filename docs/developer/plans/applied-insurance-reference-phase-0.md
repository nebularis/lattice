<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Plan: Applied Insurance Reference — Phase 0, Decisions

**Unit ID:** `applied-insurance-reference-phase-0`
**Epic:** [applied-insurance-reference](applied-insurance-reference.md)
**Status:** AIR-0.1 implemented 2026-09-26, awaiting ADR ratification
**Status record:** epic [status](../status/applied-insurance-reference.md) until the phase starts

## Scope

Ratify the epic's Phase 0 decisions (epic §5.3). No ontology changes. Sketch material motivated by
Open CBAA stays as written (epic D3).

## Slices

### AIR-0.1: ADRs A-98, A-99, A-100 and A-102

Draft the four ADRs as `Proposed`, add catalogue rows, and write up in them the decisions
already taken: the applied layout (epic §5.2, D5 to D9) in A-98, and the scheme profile module's
home (D10) in A-100, with MB-Q3 answered there. In the same slice, make the sketches' citations of
Open CBAA documents (design-spec, integration specification) name that repository.

L0: `mise run topology:links` reports no failure under `docs/developer/sketches/`. Gate: human
ratification of each ADR.

## Documentation deltas

| Document | Change | Slice |
|---|---|---|
| `docs/architecture/decisions/README.md` | rows for A-98, A-99, A-100, A-102 | 0.1 |
| `docs/developer/INDEX.md` | slice row under the epic entry | 0.1 |

## Exit gate

A-98, A-99, A-100 and A-102 Accepted.
