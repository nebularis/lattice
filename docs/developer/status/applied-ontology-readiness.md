<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Applied Ontology Readiness - Status

**Unit ID:** `applied-ontology-readiness`
**Status:** AOR-1 (governance records) written, awaiting human review. No
implementation started.
**Last updated:** 2026-09-25
**Trigger:** human request, 2026-09-25
**Plan:** [applied-ontology-readiness.md](../plans/applied-ontology-readiness.md)
**Sketch:** [applied-ontology-readiness.md](../sketches/applied-ontology-readiness.md)
**ADRs:** A-87 to A-92 and the A-86 addendum, all Proposed

## Current position

AOR-1 is written: six Proposed ADRs, a proposed addendum to ADR-A86, the
sketch, the plan, this record, the ADR catalogue rows, and the `INDEX.md`
entry. The ADR catalogue also gained the A-86 row, which was missing. Nothing
under `ontology/`, `tools/`, `mise.toml` or `.github/` has changed.

## Baseline evidence (2026-09-25, commit `9a12da4`)

A read-only pySHACL run of each Eligibility example, with
`ontology/eligibility/spec/eligibility.ttl` as ontology graph and the three
Eligibility shape files, gave:

| Example | Warnings | Violations |
|---|---|---|
| `hierarchical-match.ttl` | declaration warning on `ex:hierarchical-condition` | three `elg:ConditionShape` violations on `ex:hierarchical-profile` (no match strategy, compatibility operation or wildcard policy), one L8 violation on `ex:decision` (no operational profile) |
| `condition-taxonomy.ttl` | declaration warnings on `ex:exact-condition` and `ex:set-condition` | none |
| `interval-containment.ttl` | declaration warning on `ex:profile-a`, an admission profile | one L8 violation on `ex:decision-1` |

The warning on `ex:profile-a` is a defect in the shape added by `9a12da4`,
since an admission profile's concepts belong to its conditions. ADR-A87 item 4
records the correction. The violations predate `9a12da4`.

Other facts the plan relies on, checked the same day:

- Importers of `lattice/eligibility/0.3.0`: Eligibility vocab, Instrument spec
  and README, Behaviour spec and README, the applied capacity execution spec.
- Nine MORK example and test documents declare `owl:Ontology` without a
  version IRI.
- `check:ontology-versioning` is in the aggregate `mise run check`, but no
  GitHub workflow runs it.
- The job-family modules under `ontology/surface/execution/` import the
  retired `surface/0.0.1` IRI.
- The repository's `reasoning` extra provides `owlrl` only. No DL reasoner is
  available to tests until the ADR-A83 harness exists.

## Decisions awaiting the human

1. Ratify, amend or reject ADRs A-87 to A-92 and the A-86 addendum.
2. Sketch open question 1: keep giving admission profiles a match strategy in
   examples, or exempt profiles from `elg:ConditionShape`.
3. Sketch open question 2: bind `hierarchical-match.ttl` to a scheme contract
   in AOR-2.
4. Sketch open question 3: keep one unit, or promote to an epic with one plan
   per phase.
5. The order of work. AOR-2 needs only ADR-A87.

## Slices

| Slice | State |
|---|---|
| AOR-1 | Written, awaiting review |
| AOR-2 to AOR-17 | Not started |

## Token record

| Slice | Estimate | Actual |
|---|---|---|
| AOR-1 | 150k | not measured |

## Blockers

None for AOR-1. Every later slice waits on its ADR.
