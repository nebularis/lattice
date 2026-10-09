<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: CCS C9b0, Eligibility sources

**Unit:** [`computable-contract-substrate`](../status/computable-contract-substrate.md)
**Machine:** R (Claude Code). **Branch:** `ccs/c9b0-eligibility-sources`, in its own worktree, merged
first into `ccs/c9b-groundwork` (the plan's "How C9b0 to C9b2 run"). Built and committed by a
sub-agent on its branch, never pushed or tagged
**Plan:** [CCS plan](../plans/computable-contract-substrate.md), C9b0 in detail
**Decisions:** TD-16 (Eligibility's part), ADR-A120, law L9 as amended by FM-EP's B2.2
(`2a438b15`). C9b0-Q1 and C9b0-Q2, both answered (a) on 2026-10-09

## Invariant

Eligibility's README generates every Eligibility spec, vocab and shapes file, and the literate
`--check` proves it. No shape, law text or ontology header exists only in a generated file, and no
shape is declared in two files, so no violation is reported twice. Releasing L9's amendment moves
`eligibility-vocab` only, and the spec and shapes graphs stay as released. A hierarchical condition
with no resolved scheme, which L9 makes Undetermined for every candidate, is refused by the
compilers and never answered Denied by a backend (C9b0-Q2 (a)).

## Test cases

| ID | Given / When / Then | Level | Invariant | Pass criterion | +/- |
|---|---|---|---|---|---|
| C9b0-01 | Eligibility's README / the literate `--check` with all three shape files, `--proofs-root` and `--reference-root` / every generated file matches | L3 | the README is the whole source | exit 0, "7 extracted artefact(s) consistent" | + |
| C9b0-02 | a copy of the layer with `shapes/constraints.ttl` edited by hand / the same check / drift reported | L3 | a generated file cannot diverge unnoticed | exit 1 | − |
| C9b0-03 | the three shape files / each node shape's IRI / declared in one file only | L1 | no shape in two files | no IRI seen twice | + |
| C9b0-04 | a bare `elg:Condition` / shapes / `ConditionShape` reports its three missing properties, once each | L1 | the once-duplicated structural shape fires once | 3 violations on the probe | − |
| C9b0-05 | a `WildcardCondition` with `NoWildcard` and the `Wildcard` strategy / shapes / `WildcardPolicyConsistency` fires | L1 | ADR-A06 kept | 1 violation | − |
| C9b0-06 | an `AdmissionProfile` with no condition / shapes / `AdmissionProfileShape` fires | L1 | file-only shape kept | 1 violation | − |
| C9b0-07 | an empty `EligibilityDecision` / shapes / `EligibilityDecisionShape` fires on profile, question, value and operational profile | L1 | L6 to L8 kept | 4 violations | − |
| C9b0-08 | a hierarchical condition whose contract's scheme has a cycle / shapes / `HierarchyWellFoundednessShape` fires | L1 | L9 clause (a) kept | 1 violation | − |
| C9b0-09 | an `IntervalCondition` with no range set / shapes / `IntervalContainmentRequiresRangeSet` fires, under its released name | L1 | L4 kept, name unchanged | 1 violation from that IRI | − |
| C9b0-10 | every probe of C9b0-04 to C9b0-09 / its violations keyed by owning shape, focus, path and component / no key twice | L1 | no violation reported twice | all keys distinct | + |
| C9b0-11 | a hierarchical condition with required concepts and no `elg:constrainedByContract` / compiled / refused | L1 | C9b0-Q2 (a) | `IRCompileError` | − |
| C9b0-12 | a compiled hierarchical plan with its scheme removed by hand / the SPARQL and SHACL backends / both refuse | L1 | no backend answers Denied where L9 says Undetermined | `IRCompileError` from each | − |
| C9b0-13 | the regenerated files against the branch base / git and rdflib `graph_diff` over `to_isomorphic` / spec and shapes byte-identical, the vocab differs by its version IRI and L9's comment only | L3 | only `eligibility-vocab` moves | as stated, `check:ontology-versioning` clean against the base, one release row, release note in README §11 | + |
| C9b0-14 | the earlier suites / run / pass | L3 | non-weakening | the checks under Results pass | + |

## One command

Run from the repository root on machine R.

```bash
python tools/literate_extract.py ontology/eligibility/README.md --layer eligibility --root . --shapes shapes/structural.ttl shapes/constraints.ttl shapes/rules.ttl --proofs-root tools/proofs --reference-root tools/reference --check && python -m pytest tools/test_eligibility_examples.py tools/mork_compilers/src/mork_compilers/test_hierarchical_conditions.py -q
```

No `check:eligibility-sources` task is added. The pytest modules already run in
`check:ontology-catalog` and `check:mork-compilers`.

## Artefacts to inspect

- `ontology/eligibility/README.md`: §3's extraction contract and command, the vocab header in §6's
  first block, the paragraph after §6.4's laws on the compilers' refusal, §7's three blocks, §11's
  release note
- `ontology/eligibility/vocab/eligibility-vocab.ttl`: `0.12.0` and L9's comment
- `tools/test_eligibility_examples.py`: C9b0-01 to C9b0-10
- `tools/mork_compilers/src/mork_compilers/test_hierarchical_conditions.py`: C9b0-11 and C9b0-12,
  and the guards in `sparql_backend.py` (`_concept_core`) and `shacl_backend.py` (`concept_sets`)

## Deliberate non-coverage

- The no-applicable-binding case, a binding-time deferral, still refused rather than Undetermined
  (C9b3, as C9b0-Q2's answer requires)
- Law registers for L1 to L8 and a shape for L5 (TD-27)
- The OWL and SWRL backends get no guard, since the brief names only SPARQL and SHACL. A hand-built
  hierarchical plan with no scheme can still reach them, and their reading of it is not examined
- Foundation, Vocabulary and Party, TD-16's other parts

## Handoff

2026-10-09:

- **Built:**
  - README §7 as three `turtle-shapes` blocks carrying `structural.ttl`, `constraints.ttl` and
    `rules.ttl` unchanged, so `WildcardPolicyConsistency`, `AdmissionProfileShape`,
    `EligibilityDecisionShape`, `HierarchyWellFoundednessShape` and
    `UndeterminedWhenNoCandidateInput` join the README. `IntervalConditionShape` is gone, and its
    body survives as `IntervalContainmentRequiresRangeSet`. §3 names every file and the command
  - the vocab header in the README, `eligibility-vocab` 0.12.0, catalog and release register
    regenerated, release note in a new §11
  - the literate check and probes replacing `test_readme_mirrors_shape_file`
  - the §6.4 paragraph, the backend guards and their tests (C9b0-Q2 (a))
- **Run by the agent:** every check under Results, with this worktree's packages first on
  `PYTHONPATH`, since the editable installs point at another clone. Adversarial probes:
  - with `ConditionShape` appended to `constraints.ttl`, C9b0-01, C9b0-03 and C9b0-04 fail
  - with either backend guard disabled, C9b0-12 fails for that backend
  - against the shapes `main`'s README generated, C9b0-05 to C9b0-09 find no violation from their
    shape. With `main`'s README output beside the committed `structural.ttl` and `rules.ttl`, the
    bare condition reports 6 violations, 3 distinct (C9b0-04 and C9b0-10), and C9b0-05 and C9b0-09
    still find none
- **Check first:** the deviations, then §7 and the §6.4 paragraph.
- **Deviations from the plan:**
  - **Pack name.** The plan names `ccs-c9b0.md`. This pack follows C9a's name, as the brief asked
  - **Spec `@base` moved.** The spec block's `@base` moves from §5's header block into §2's prefix
    block, so `spec/eligibility.ttl` regenerates byte for byte. Otherwise one blank line changes,
    and `ontology_version_check.py`, which compares text, reports the spec unbumped against the base
  - **A release notes section is added.** The brief asks for the note in the README's release notes
    section, which Eligibility did not have. §11 starts with 0.12.0 and points to the release
    register for earlier versions
  - **The guards raise `IRCompileError`**, not `assert`, so they hold under `python -O` and callers
    handle them as the IR's own refusals
  - **One command** is the literate check and two pytest modules, not a new mise task

## Results

| Row | Result | Evidence |
|---|---|---|
| C9b0-01 | pass | `test_readme_generates_every_file`, and the command in §3 |
| C9b0-02 | pass | `test_a_generated_file_edited_by_hand_fails_the_check` |
| C9b0-03 | pass | `test_no_shape_is_declared_in_two_files` |
| C9b0-04 to C9b0-10 | pass | `test_moved_shape_fires_once_on_its_probe`, six probes |
| C9b0-11 | pass | `test_required_concepts_without_a_contract_are_refused` |
| C9b0-12 | pass | `test_backends_refuse_a_hierarchical_plan_with_no_scheme` |
| C9b0-13 | pass | `git diff 080a8af8 -- ontology/eligibility/spec ontology/eligibility/shapes` is empty. `graph_diff` of the vocab: 83 triples each side, one only in each for the version IRI and one for L9's comment. `ontology_version_check.py --base-ref 080a8af8`: no unbumped changes |
| C9b0-14 | pass | pass, with two failures outside the slice. `check:ontology-catalog`: 556 passed, 67 skipped, 1 failed, `test_c6_10_no_retired_term_outside_history` on `insure-o` (TD-28, red on `main`, no file of this slice). `ontology_catalog.py check`, run on its own since the failure stops the task: consistent. `check:mork-compilers` (109 passed, 7 skipped), `check:reference-eligibility` (66), `check:formal-freshness`, `check:ontology-versioning`, `check:import-guard`, `check:python-root`, `check:vocabulary` (16), `build:mtp` (no file changed), `check:mtp`, `check:deny-terms`. `check:persistence`: 778 passed on the first run, and 777 with `test_export_recipes_writes_each_recipe_and_refuses_a_tampered_one` failing on the second. That test fails about one run in six on its own, touches no file of this slice, and is flaky outside it |

The one command: 41 passed.
