<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: AIR-3.1, hierarchical match over flat schemes

**Unit:** [`applied-insurance-reference`](../status/applied-insurance-reference.md)
**Machine:** R (Claude Code). **Branch:** `air/3.1-flat-hierarchy`
**Plan and test cases:** [Phase 3 plan](../plans/applied-insurance-reference-phase-3.md) (AIR-3.1 in detail)
**Decisions:** ADR-A100 and its implementation note

## Invariant

Under `elg:HierarchicalMatch`, a resolved scheme in which no member has a `skos:broader` link to another member decides only the concepts a condition names. Every other member is Undetermined with `exe:NoHierarchy` in every backend, and hierarchical schemes evaluate as before.

## Test cases

The table in the plan section above. Each row's result is recorded under Results at
verification.

## One command

Run from the repository root on machine R, after `mise run build:ontology-catalog` and `mise run build:ontology-releases`.

```bash
mise run check:mork-compilers && mise run check:ontology-catalog && mise run check:ontology-versioning
```

## Artefacts to inspect

- The two examples in `ontology/eligibility/examples/` and their recorded decisions.
- `elg:L14` in the vocabulary and README, and `exe:NoHierarchy`.
- The flat branch in `eligibility_ir._expand` and `sparql_backend.concept_select`.

## Deliberate non-coverage

Set readings and negation (AIR-3.2, AIR-3.3). Kind-only matching (substrate S2).

## Handoff

Written by the building machine when the work is committed. R ran the command before handing over.

- **Built:** the two examples (`flat-scheme-lending.ttl`, `flat-scheme-employment.ttl`),
  `elg:L14` in the Eligibility vocabulary and README (vocabulary 0.6.0 → 0.7.0),
  `exe:NoHierarchy` (Executable 0.5.0 → 0.6.0), `ConceptPlan.no_hierarchy` and the L14 branch of
  `_expand`, the SPARQL branch and diagnostic, the SHACL message, the OWL refusal,
  `test_flat_schemes.py`, the examples in `tools/test_eligibility_examples.py`, the compilers
  README, the Eligibility row of ontology architecture §3, the catalog and two release rows.
- **Not run:** nothing. Every check below was run on R.
- **Check first:** the lending example's comment table, which is the argument for L14 in one
  place, and the rule that the lender's list reuses only concepts whose parents lie outside it.
- **Deviations from the plan:** the plan section now matches what was built.
  1. The lending example's recorded decisions changed. A list reusing both a parent and its child
     would carry their `skos:broader` link, so the list holds only concepts whose parent lies
     outside it, and the condition requires manufacturing or retail.
  2. The new tests are in `test_flat_schemes.py`, not `test_hierarchical_conditions.py`, to avoid
     an import cycle with `test_concept_backends.py`.
  3. One existing test changed: `test_concept_backends.py`'s closed set of diagnostics gains
     `exe:NoHierarchy`. The test fails whenever `Executable.ttl` declares a diagnostic it does not
     list, so this extends it and weakens nothing.

## Results

Run on machine R, 2026-09-26, on `air/3.1-flat-hierarchy`:

| Check | Result |
|---|---|
| `mise run check:mork-compilers` | 101 passed (92 before, plus 9 in `test_flat_schemes.py`) |
| `mise run check:ontology-catalog` | 59 tool tests passed, catalog consistent, 3 known defects (unchanged) |
| `mise run check:ontology-versioning` | no unbumped changes, every version listed. Tags to create: `eligibility-vocab-v0.7.0`, `executable-v0.6.0` |
| AIR31-01 to AIR31-09 | pass (`test_flat_schemes.py`) |
| AIR31-10 | pass (`tools/test_eligibility_examples.py`) |
| AIR31-11 | pass: no existing hierarchical test changed |
| probe: L14 branch removed from `_expand` | AIR31-06, 07 and 08 fail |
| probe: L14 branch removed from `concept_select` | AIR31-03, 04, 06 and 07 fail |
