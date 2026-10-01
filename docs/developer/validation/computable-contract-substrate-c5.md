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

- `ontology/wording/shapes/`: one shape per law, and the slot set check.
- `ontology/wording/examples/facility-amendment.ttl`: the second facility version.
- `ontology/wording/README.md`: the laws section, the how-to and the release notes.

## Deliberate non-coverage

Evaluating inclusion conditions at assembly (Eligibility's, in question form). Slot conditions other than intervals over one governing variable, beyond the structural check (C5-Q1): the full check by reasoner is slice C13a. The legal effect of an amendment (C9).

## Handoff

Written by the building machine when the work is ready for the human to commit.

- **Built:**
- **Not run:**
- **Check first:**
- **Deviations from the plan:**

## Results

Written on machine R at verification.
