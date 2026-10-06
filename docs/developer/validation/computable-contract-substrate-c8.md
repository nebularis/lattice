<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: CCS C8, parameter bindings

**Unit:** [`computable-contract-substrate`](../status/computable-contract-substrate.md)
**Machine:** R (Claude Code). **Branch:** `ccs/c8-parameter-bindings`. Commits are the human's, and
the change is merged into `main` before its release tags are created
**Plan and test cases:** [CCS plan](../plans/computable-contract-substrate.md) (C8 in detail)
**Decisions:** ADR-A104 decision 13 and its 2026-10-06 addendum, ADR-A92, ADR-A51, ADR-A85,
ADR-A115. Laws I13 and I17. C8-Q1 to C8-Q6, with HQ-4 decided after the formal-methods epic's
track C2. An ADR-A104 addendum, to be drafted with the examples

## Invariant

An instrument stores only what differs from its form, and its values are among that. Stated meaning names roles, words and variables. Bound meaning names occupancies, meanings and values, and is generated from the form and the instance. An instrument version binds exactly the stated meaning of the elements its wording includes (I17). Nothing here evaluates.

## Test cases

The table in the plan section above. Each row's result is recorded under Results at
verification.

## One command

Run from the repository root on machine R, with the reasoning harness built where a row is L2.

```bash
mise run build:ontology-catalog && mise run check:ontology-versioning && mise run check:ontology-catalog && mise run check:import-guard
```

## Artefacts to inspect

- `ontology/instrument/examples/`: the new and reworked examples, written before the model.
- `ontology/instrument/README.md`: values in stated meaning, schedules, value words, encoding
  status, generation, law I17.
- `ontology/instrument/shapes/`: variables and words in bound meaning, encoding status, I17, and the
  form's overlap and word resolution checks.
- `tools/instrument_binder.py`: the reference binder.
- The ADR-A104 addendum.

## Deliberate non-coverage

Evaluation (C12, C13). Computed amounts, bases, aggregation and `ins:computedBy` (contract amounts). Sharing bound meaning across instruments, its cache and subgraph (C16b). Amendments, consent rules and incorporation (C9).

## Handoff

Written by the building machine when the work is ready for the human to commit.

## Results

Recorded at verification.
