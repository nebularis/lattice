<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Applied Ontology Readiness - Status

**Unit ID:** `applied-ontology-readiness`
**Status:** AOR-1 to AOR-9, AOR-3b, AOR-12 and AOR-13 committed (`6e36586`,
`6e9acb1`, `54caeb6`).
AOR-10, AOR-11 and AOR-14 to AOR-17 implemented and self-validated, awaiting
the human's commands (uncommitted). Every slice is now implemented.
**Last updated:** 2026-09-25
**Trigger:** human request, 2026-09-25
**Plan:** [applied-ontology-readiness.md](../plans/applied-ontology-readiness.md)
**Sketch:** [applied-ontology-readiness.md](../sketches/applied-ontology-readiness.md)
**Review request:** [applied-ontology-readiness-review.md](../review/applied-ontology-readiness-review.md)
**ADRs:** A-83, A-86 (with its addendum) and A-87 to A-96 Accepted (2026-09-25).

## Current position

On 2026-09-25 the human reported every AOR-2 to AOR-9 command passing, accepted
ADRs A-87 to A-92, chose content-hash version IRIs for generated documents,
asked for Executable to align directly to PROV-O if that imposes no functional
restriction, and asked for the Phase C ADRs and ADR-A83 to be drafted. The
`LOG.md` sign-offs are the human's to record.

Later on 2026-09-25 the human ratified ADR-A83, A-86 and its addendum, and
A-93 to A-96, chose path encoding B for ADR-A90, and asked for AOR-14 to
AOR-16 as one Quantification change with AOR-16 including the compiler work.
The ADR-A83 harness was delivered as the `eligibility-compiler` unit's Part B
([VP](../validation/eligibility-compiler-part-b.md)). The agent ran the
checks listed under Validation below. The human has not yet run them.

## Slices

| Slice | State | Validation Pack |
|---|---|---|
| AOR-1 | Done (`6b2a577`) | n/a |
| AOR-2 to AOR-4 | Committed (`6e36586`), commands passed | [aor-2](../validation/applied-ontology-readiness-aor-2.md), [aor-3](../validation/applied-ontology-readiness-aor-3.md), [aor-4](../validation/applied-ontology-readiness-aor-4.md) |
| AOR-5 to AOR-9 | Committed (`6e9acb1`), commands passed | [aor-5](../validation/applied-ontology-readiness-aor-5.md) to [aor-9](../validation/applied-ontology-readiness-aor-9.md) |
| AOR-3b | Committed (`54caeb6`) | [aor-3b](../validation/applied-ontology-readiness-aor-3b.md) |
| AOR-12 | Committed (`54caeb6`) | [aor-12](../validation/applied-ontology-readiness-aor-12.md) |
| AOR-13 | Committed (`54caeb6`) | [aor-13](../validation/applied-ontology-readiness-aor-13.md) |
| AOR-10, AOR-11 | Implemented, self-validated | [aor-10-11](../validation/applied-ontology-readiness-aor-10-11.md) |
| AOR-14 to AOR-16 | Implemented, self-validated | [aor-14-16](../validation/applied-ontology-readiness-aor-14-16.md) |
| AOR-17 | Implemented, self-validated | [aor-17](../validation/applied-ontology-readiness-aor-17.md) |

AOR-4's Protégé step has a walkthrough:
[Loading LATTICE in Protégé](../protege-import-walkthrough.md).

## Versions in `54caeb6` (against `6e9acb1`)

All MINOR. Foundation and its vocab, Vocabulary, MORK: 0.2.0 → 0.3.0.
Quantification, Party and its vocab, Surface and its vocab: 0.3.0 → 0.4.0.
Eligibility, Instrument, Behaviour (spec and vocab each) and the applied
capacity execution spec: 0.4.0 → 0.5.0. Executable: 0.3.0 → 0.4.0.
`applied/insurance` is a sketch and untouched, by instruction.

## Versions in the uncommitted change (against `HEAD`)

All MINOR. Quantification, Party and its vocab, Surface and its vocab:
0.4.0 → 0.5.0. Eligibility, Instrument, Behaviour (spec and vocab each) and
the applied capacity execution spec: 0.5.0 → 0.6.0. Executable: 0.4.0 → 0.5.0.
Mork: 0.3.0 → 0.4.0 (ADR-A97).
The catalog is regenerated.

## Validation run by the agent (2026-09-25)

`check:mork-compilers` (92 passed, reasoner tests included),
`check:python-root`, `check:ontology-versioning` (29 documents),
`check:ontology-catalog` (3 known defects), `check:reasoning-testkit`,
`check:reasoning-isolation`, `check:vocabulary`.

## Decisions awaiting the human

1. **MTP pins**: whether `build` should stop rewriting `pins.lock.json` (an MTP
   decision that `mork-teaching-pack.md` reserves for an ADR).

## Discovered, outside this unit

- The `persistence-compiler-iri-sync` commits (`772ea66`, `d19b7cf`) bumped
  `persistence/spec` without regenerating the import catalog, so
  `check:ontology-catalog` failed at `3e7d911`. Regenerated on 2026-09-25
  (uncommitted).
  `.github/copilot-instructions.md` now reminds agents of every versioning step.
- `ontology/mork/spec/Mork.ttl` did not load in the OWL API and was not OWL 2
  DL. Repaired under ADR-A97 (Mork 0.4.0, MTP re-pinned), which unblocks the
  `eligibility-compiler` unit's A2 reasoner half ([status](eligibility-compiler.md)).
- `tools/literate_extract.py` still resolves layers at `<root>/<layer>`, so
  its documented `--check` reports drift everywhere since the move to
  `ontology/`. The aggregate `mise run check` catches this, and CI runs only
  when dispatched.

- Link repair is planned as [`documentation-link-repair`](../plans/documentation-link-repair.md),
  pending. Its first slice fixes the checker scanning ignored `docs/_site/`.
- `ontology/applied/insurance` and the two MORK examples stay in
  `KNOWN_DEFECTS`, by instruction.
- Both GitHub workflows are manual-only (`workflow_dispatch`).
- rdflib: the `MIN` aggregate fails on two unbound values, and a grouped
  subquery is evaluated under the outer binding (AOR-8 VP).

## Token record

| Slices | Estimate | Actual |
|---|---|---|
| AOR-1 | 150k | not measured |
| AOR-2 to AOR-4 | 310k | not measured |
| AOR-5 to AOR-9 | 820k | not measured |
| AOR-3b, AOR-12, AOR-13, ADRs A-83 and A-93 to A-96 | 330k | not measured |
| ADR-A83 harness, AOR-10, AOR-11, AOR-14 to AOR-17 | 170k + 150k + 470k | not measured |

## Blockers

None.
