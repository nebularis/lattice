<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: CCS C5, Wording amendments and law shapes

**Unit:** [`computable-contract-substrate`](../status/computable-contract-substrate.md)
**Machine:** R (Claude Code). **Branch:** `ccs/c5-wording-laws`. Commits are the human's
**Plan and test cases:** [CCS plan](../plans/computable-contract-substrate.md) (C5 in detail)
**Decisions:** ADR-A112 decision 3, ADR-A113, C4-Q2's refinement. C5-Q1, C5-Q2a to C5-Q2d decided 2026-10-02

## Invariant

Wording gains textual amendments, and laws W1 to W6 become shapes, so a consumer without the LATTICE runtime can check a wording and an assembled instance completely. New violation-level shapes are breaking under ADR-A113.

## Test cases

The table in the plan section above. Each row's result is recorded under Results at
verification.

## One command

Run from the repository root on machine R, with the reasoning harness built where a row is L2.

```bash
mise run build:ontology-catalog && mise run check:ontology-versioning && mise run check:ontology-catalog && mise run check:import-guard
```

## Artefacts to inspect

- `ontology/wording/shapes/constraints.ttl`: one shape per law, the slot set check and the amendment rules.
- `ontology/wording/examples/facility-amendment.ttl`: the second facility version.
- `ontology/wording/README.md`: the laws section, the how-to and the release notes.

## Deliberate non-coverage

Evaluating inclusion conditions at assembly (Eligibility's, in question form). Slot conditions other than intervals over one governing variable, beyond the structural check (C5-Q1): the full check by reasoner is slice C13a. The legal effect of an amendment (C9).

## Handoff

Written by the building machine when the work is ready for the human to commit.

- **Built:** wording, wording-vocab and wording-shapes 0.3.0 (README §5.10, §5.13, §6, §7, §8 to §10),
  the new `shapes/constraints.ttl`, catalog and release rows, and the C5 rows in `tools/test_wording.py`.
- **Not run:** `check:java`, `check:frontend` and the other suites C5 does not touch.
- **Check first:** the slot range check in §8 (candidate points: endpoints, a step either side,
  midpoints on dense spaces), and W5's two exemptions.
- **Deviations from the plan:**
  - The laws are in a second shapes file, `shapes/constraints.ttl`, as in Behaviour and Surface.
    `structural.ttl` stays SHACL Core.
  - W5 does not require variables to be included (they are declarations, shown by their values,
    and no example includes them), and accepts a mandatory child removed by a delete that
    generated the assembled wording.
  - `wrd:variantOf` is no longer functional, and the Core shape "variant of at most one slot" is
    gone: a draft release puts a variant in a second version of its slot, which W1 allows.
  - On a discrete space the step is the space's granularity floor, or 1 when it declares none. A
    governing variable with no admissible values must be covered for every number.
  - Every amendment states exactly one `wrd:expressedIn`. Only a strike and substitute states
    struck or substituted text, and it has no replacement.
  - Rows C5-15 and C5-16 and `wrd:CellShape` came with the CC-D6 amendment. C4-04's fixtures and
    C4-05 now use fields and entries, and C4-05 counts per assembled version.

## Results

Written on machine R at verification, 2026-10-02. `tools/test_wording.py`: 94 passed, the reasoner
rows included. `check:ontology-versioning`, `check:ontology-catalog`, `check:import-guard`,
`check:reasoning-isolation` and `check:mork-compilers` pass.

| ID | Test | Result |
|---|---|---|
| C5-01 | `test_c4_02_c5_01_every_example_conforms`, `test_c3_14_*` | pass |
| C5-02 to C5-06 | `test_c5_02_to_06_laws_w1_to_w5_are_reported` (12 cases, each matched on its law's message), `test_c5_06_a_revision_or_a_delete_stands_for_a_mandatory_child` | pass |
| C5-07 | `test_c5_07_values_must_match_their_variable` (4 cases) | pass |
| C5-08 | `test_c5_08_slot_ranges_are_disjoint_and_cover` (7 cases), `test_c5_08_other_slots_*` | pass |
| C5-09 | `test_c5_09_each_operation_has_what_it_needs` (6 cases) | pass |
| C5-10 | `test_c5_10_the_second_facility_replaces_and_supersedes` | pass |
| C5-11 | `test_c3_09_readme_blocks_equal_the_files`, `test_c5_11_release_notes_mark_0_3_0_breaking` | pass |
| C5-12 | the C3 and C4 rows | pass |
| C5-13 | `test_c5_13_an_instance_never_versions_a_library_element` | pass |
| C5-14 | `test_c5_14_the_draft_release_derives_from_the_bespoke_revision` | pass |
| C5-15 | `test_c5_15_cells_and_orientations` (2 cases) | pass |
| C5-16 | `test_c5_16_one_cell_per_declared_field_and_entry` | pass |
