<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: CCS C11a, nested states, history and concurrent regimes

**Unit:** [`computable-contract-substrate`](../status/computable-contract-substrate.md)
**Machine:** R (Claude Code). **Branch:** `ccs/c11a-nested-states`. Commits are the human's
**Plan and test cases:** [CCS plan](../plans/computable-contract-substrate.md) (C11A in detail)
**Decisions:** ADR-A106, C11-Q1, C11-Q2

## Invariant

Behaviour can express composite states, history, and concurrent regimes on one subject with stated interaction rules, as configuration data evaluated by C12 without inference. Phase 1 is paper: a sketch and an A-106 addendum, gated by the human before Phase 2 changes the ontology.

## Test cases

The table in the plan section above. Each row's result is recorded under Results at
verification.

## One command

Run from the repository root on machine R, with the reasoning harness built where a row is L2.

```bash
mise run topology:links
```

## Artefacts to inspect

- `docs/developer/sketches/nested-states-and-history.md`: every topic of the brief decided or raised.
- ADR-A106's addendum.

## Deliberate non-coverage

Phase 2, the ontology change, which is briefed after the gate. The evaluator itself (C12).

## Handoff

Written by the building machine when the work is ready for the human to commit.

- **Built:**
- **Not run:**
- **Check first:**
- **Deviations from the plan:**

## Results

Written on machine R at verification.
