<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: AIR-3.2, set readings and negation, Eligibility, IR, SPARQL, SHACL

**Unit:** [`applied-insurance-reference`](../status/applied-insurance-reference.md)
**Machine:** R (Claude Code). **Branch:** `air/3.2-set-readings`
**Plan and test cases:** [Phase 3 plan](../plans/applied-insurance-reference-phase-3.md) (AIR-3.2 in detail)
**Decisions:** ADR-A103

## Invariant

A bound condition reads several values by its binding's declared reading, a negated condition swaps Permitted and Denied and keeps Undetermined with its diagnostic, conditions without either evaluate as before, and SWRL and OWL refuse what they cannot yet compile.

## Test cases

The table in the plan section above. Each row's result is recorded under Results at
verification.

## One command

Run from the repository root on machine R, after `mise run build:ontology-catalog` and `mise run build:ontology-releases`.

```bash
mise run check:mork-compilers && mise run check:ontology-catalog && mise run check:ontology-versioning
```

## Artefacts to inspect

- The two examples and their recorded decisions.
- `elg:ValueReading`, `elg:valueReading`, `elg:negated`, `elg:L15`, `elg:L16`.
- The per-value aggregation and the negation swap in the SPARQL backend.
- The cascade: every re-pinned importer and its new version.

## Deliberate non-coverage

SWRL and OWL readings and negation (AIR-3.3). Correlated values across conditions (ADR-A103 decision 5).

## Handoff

Written by the building machine when the work is committed. R ran the command before handing over.

- **Built:** the two examples (`set-reading-admissions.ttl`, `set-reading-trial.ttl`),
  `elg:ValueReading`, `elg:valueReading` and `elg:negated` (Eligibility 0.7.0), the three
  readings and laws L15 and L16 (Eligibility vocabulary 0.8.0), the two structural shape
  properties (shapes 0.2.0), all mirrored in the README. The cascade: Instrument, Instrument's
  vocabulary, Behaviour, Behaviour's vocabulary and the Capacity execution profile, each 0.6.0 →
  0.7.0, with their README mirrors. In the compilers: the reading on `EvidencePath`, `negated` on
  both plans, `has_readings`, the per-value core and the `_read_set` and `_negate` wrappers in
  SPARQL, the decided shapes in SHACL, and the refusals in SWRL and OWL. `test_set_readings.py`,
  and AIR32-12 and 13 in `tools/test_eligibility_examples.py`. The compilers README and the
  Eligibility row of ontology architecture §3. Catalog and eight release rows.
- **Not run:** nothing. Every check below was run on R.
- **Check first:** the admissions example's table, and `_read_set` in `sparql_backend.py`, which
  carries the whole of L15.
- **Deviations from the plan:**
  1. `solution-design-specification.md` is not changed. It describes the platform and never
     covers Eligibility's evaluation semantics, so set readings have no section to join. The plan
     is corrected.
  2. One test beyond the table: an Undetermined set reports the diagnostic of one of its
     Undetermined values (`test_undetermined_set_reports_a_value_diagnostic`).
  3. The test helper refuses a query that returns two rows for one subject. A mutation probe
     showed that without this guard, dropping the reading entirely passed the exclusion test by
     keeping the last of several rows.

## Results

Run on machine R, 2026-09-26, on `air/3.2-set-readings`:

| Check | Result |
|---|---|
| `mise run check:mork-compilers` | 114 passed (101 before, plus 13 in `test_set_readings.py`) |
| `mise run check:ontology-catalog` | 77 tool tests passed, catalog consistent, 2 known defects |
| `mise run check:ontology-versioning` | no unbumped changes against HEAD or `main`, every version listed |
| AIR32-01 to AIR32-11 | pass (`test_set_readings.py`) |
| AIR32-12, AIR32-13 | pass (`tools/test_eligibility_examples.py`) |
| AIR32-14 | pass: no existing test changed |
| AIR32-15 | pass: the cascade is complete, versioning clean |

Tags to create at merge: `applied-capacity-execution-v0.7.0`, `behaviour-v0.7.0`,
`behaviour-vocab-v0.7.0`, `eligibility-v0.7.0`, `eligibility-shapes-v0.2.0`,
`eligibility-vocab-v0.8.0`, `instrument-v0.7.0`, `instrument-vocab-v0.7.0`.

Mutation probes, each restored after:

| Mutation | Tests that fail |
|---|---|
| `SomeValue` given `EveryValue`'s table | 5, including AIR32-01, 07 and 09 |
| negation's swap removed | 4: AIR32-06 (both), 07, 09 |
| the set reading skipped | 10, after the helper's duplicate-row guard |
| SHACL's two roles swapped | AIR32-10 |
