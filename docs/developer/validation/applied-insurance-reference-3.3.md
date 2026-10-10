<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: AIR-3.3, set readings and negation, SWRL and OWL

**Unit:** [`applied-insurance-reference`](../status/applied-insurance-reference.md)
**Machine:** R. **Branch:** `air/3.3-readings-swrl-owl`
**Plan and test cases:** [Phase 3 plan](../plans/applied-insurance-reference-phase-3.md) (AIR-3.3 in detail)
**Decisions:** ADR-A103

## Invariant

SWRL derives only what a set reading fixes from positive facts, with heads swapped under negation, and agrees with SPARQL on everything it derives. OWL compiles `SomeValue` as `∃`, `EveryValue` as `∀ ⊓ ∃⊤`, and negation as a complement, for design-time checks. Plans without either compile as before.

## Test cases

The table in the plan section above. Each row's result is recorded under Results at
verification.

## One command

Run from the repository root on machine R, with the reasoning harness built (`mise run bootstrap:reasoning-testkit`), so the L2 rows do not skip.

```bash
mise run check:ontology-catalog
```

## Artefacts to inspect

- `tools/mork_compilers/src/mork_compilers/swrl_backend.py`: which rules each reading emits, and the head swap.
- `owl_backend.py`: `_along` under each reading, and the negated class.
- `test_set_readings.py`: the soundness row, AIR33-06.

## Deliberate non-coverage

No Denied from SWRL for an interval read `EveryValue`, and no Undetermined from SWRL at all (ADR-A24). The negated OWL class holds subjects SPARQL leaves Undetermined. Correlation between conditions (ADR-A103 decision 5).

## Handoff

Written by the building machine when the work is committed.

- **Built:**
- **Not run:**
- **Check first:**
- **Deviations from the plan:**

## Results

Written on machine R at verification.
