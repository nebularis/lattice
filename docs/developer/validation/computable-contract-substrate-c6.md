<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: CCS C6, instrument, terms and legal relations

**Unit:** [`computable-contract-substrate`](../status/computable-contract-substrate.md)
**Machine:** R (Claude Code). **Branch:** `ccs/c6-instrument-relations`. Commits are the human's
**Plan and test cases:** [CCS plan](../plans/computable-contract-substrate.md) (C6 in detail)
**Decisions:** ADR-A104 decisions 1 to 5 and 10, CC-D10, CC-D12, ADR-A96, ADR-A102, ADR-A113.
C6-Q1 to C6-Q4 open

## Invariant

Instrument states what an agreement binds its parties to: an instrument expressed in one assembled wording, terms, and the five legal relations with their parties and content. Only `ins:Instrument` is a version. Every relation arises under exactly one term and belongs to it.

## Test cases

The table in the plan section above. Each row's result is recorded under Results at
verification.

## One command

Run from the repository root on machine R, with the reasoning harness built where a row is L2.

```bash
mise run build:ontology-catalog && mise run check:ontology-versioning && mise run check:ontology-catalog && mise run check:import-guard
```

## Artefacts to inspect

- `ontology/instrument/examples/`: the four instruments, written before the model.
- `ontology/instrument/README.md`: the model, its diagrams and the worked examples.
- `ontology/instrument/shapes/`: the Core shapes, I2 and I8.

## Deliberate non-coverage

Arising, due, ending, survival and constitutive terms (C7b). Legal triggers, regimes and gating (C7a). Parameter bindings, encoding status and law I17 (C8). Amendments, consent rules and incorporation (C9). Instrument identifiers (slice F1). Evaluation, including the exception burden of law I7 (C13).

## Handoff

Written by the building machine when the work is ready for the human to commit.

- **Built:**
- **Not run:**
- **Check first:**
- **Deviations from the plan:**

## Results

Written on machine R at verification.
