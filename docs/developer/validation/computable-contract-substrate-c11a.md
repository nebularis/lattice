<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: CCS C11a, nested states, history and concurrent regimes

**Unit:** [`computable-contract-substrate`](../status/computable-contract-substrate.md)
**Machine:** R. **Branch:** `ccs/c11a-nested-states`. Commits are the maintainer's
**Plan and test cases:** [CCS plan](../plans/computable-contract-substrate.md) (C11A in detail)
**Decisions:** ADR-A106, C11-Q1, C11-Q2

## Invariant

Behaviour can express composite states, history, and concurrent regimes on one subject with stated interaction rules, as configuration data evaluated by C12 without inference. Phase 1 is paper: a sketch and an A-106 addendum, gated by a maintainer before Phase 2 changes the ontology.

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

Written by the building machine when the work is ready for the maintainer to commit.

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

## Phase 2

Built on machine R, 2026-10-02, after we committed the brief and examples (`03d8e8e`).
Not committed, pending the maintainer.

- **Built:** `behaviour` and `behaviour-runtime` 0.10.0 (additive), `behaviour-vocab` 0.10.0
  (breaking: `bhv:Live` and `bhv:LiveStates`), shapes 0.4.0 (breaking), `applied/capacity`'s
  execution profile re-pinned at 0.10.0, the README's §5.3 model, §6 occasion statechart and §10
  worked state machines (20 Mermaid diagrams, Turtle fragments, occupancy timelines), release notes,
  `tools/test_behaviour_nested.py`, catalog and release rows.
- **Check first:** B11's rule that a refinement region applies only to its own relation's
  occasions, and B5's acceptance of the evaluator's executions, which name no transition.
- **Deviations from the plan:** none beyond the two refinements the brief recorded when the examples
  were written. The C10 and C11 tests take the new versions and the seventh occasion state. Two
  sketch diagrams were corrected so Mermaid parses them (an aliased composite state, and `Default`,
  a Mermaid keyword, as a state id).

| ID | Test | Result |
|---|---|---|
| C11a-05 | `test_c11a_05_every_example_conforms` (12 examples), `..._the_eight_worked_examples_exist` | pass |
| C11a-06 | `test_c11a_06_examples_are_consistent` (8, reasoner) | pass |
| C11a-07 to C11a-09 | `test_c11a_07_to_09_configuration_rules` (10 cases, each matched on its message) | pass |
| C11a-10, C11a-11 | `test_c11a_10_11_runtime_rules` (7 cases), `..._refinement_applies_only_to_its_relation_s_occasions` | pass |
| C11a-12 | `test_c11a_12_deep_and_shallow_history_in_the_standstill` | pass |
| C11a-13 | `test_c11a_13_ordered_draws_read_what_the_draw_before_left` | pass |
| C11a-14 | `test_c11a_14_the_occasion_states_with_live` | pass |
| C11a-15 | `test_c11a_15_readme_blocks_and_release_notes`, `..._versions_and_release_rows` | pass |
| C11a-16 | `mise run check:ontology-catalog` (276 tests), `check:ontology-versioning`, `check:import-guard`, `check:reasoning-isolation` | pass |

Every Mermaid diagram in the Behaviour README and both C11a sketches (30) parses under Mermaid 11.
