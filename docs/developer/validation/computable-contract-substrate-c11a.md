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

- **Built:** `docs/developer/sketches/nested-states-and-history.md`, the ADR-A106 addendum
  (Proposed), the ADR index row, and a pointer from the CCS sketch §7.10.
- **Not run:** nothing beyond the link check. Phase 1 is paper.
- **Check first:** history declared per transition, not per composite state (sketch §4), which
  departs from the brief's wording. Then the four questions in sketch §11.
- **Deviations from the plan:** the history decision above. Garden leave, listed by the brief as a
  nesting case, is worked as two separate regimes, and gives the rule for when to nest (sketch §3.1).
  The standstill case (§9.4) carries the deep-history example instead.

## Results

Written on machine R, 2026-10-02.

| ID | Result |
|---|---|
| C11a-01 | every topic of the brief is decided in the sketch (§2 to §8, §10), or raised: C11a-Q1 to Q4 (§11) |
| C11a-02 | the six worked cases (§9) are each written as configuration and, where they turn on history or sequence, as records step by step. 9.5 and 9.6 rest on C11a-Q2 and C11a-Q4 for one detail each |
| C11a-03 | the addendum is Proposed and restates only the sketch's decisions, listing the four questions as open |
| C11a-04 | `mise run topology:links` reports no broken link in the files touched. It fails on links elsewhere in the repository that were already broken |
