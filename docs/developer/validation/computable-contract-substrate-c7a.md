<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: CCS C7a, regimes and gating

**Unit:** [`computable-contract-substrate`](../status/computable-contract-substrate.md)
**Machine:** R (Claude Code). **Branch:** `ccs/c7a-regimes`. Commits are the human's, and the change is
merged into `main` before its release tags are created
**Plan and test cases:** [CCS plan](../plans/computable-contract-substrate.md) (C7a in detail)
**Decisions:** ADR-A104 decisions 6, 7 and 8, ADR-A106 and its addendum (C11a-Q2, C11a-Q4), CC-D8,
DP6, ADR-A113. C7a-Q1 to C7a-Q5 answered 2026-10-04 (Q4: `ins:tolledIn`)

## Invariant

A contract's regimes are Behaviour state spaces that arise under a term and gate legal relations. The same legal triggers move a regime between states and make relations arise and end. State gates evaluation and never enters a design-time comparison (DP6).

## Test cases

The table in the plan section above. Each row's result is recorded under Results at
verification.

## One command

Run from the repository root on machine R, with the reasoning harness built where a row is L2.

```bash
mise run build:ontology-catalog && mise run check:ontology-versioning && mise run check:ontology-catalog && mise run check:import-guard
```

## Artefacts to inspect

- `ontology/instrument/examples/`: the four regime examples, written before the model.
- `ontology/instrument/README.md`: regimes, legal triggers and gating, with diagrams and the worked examples.
- `ontology/instrument/shapes/`: the regime, trigger and gating shapes.
- The ADR-A104 addendum, if C7a-Q1 is answered (a).

## Deliberate non-coverage

Evaluation of gating and per-occasion resolution (C12, C13). Due ranges, recurrence, survival, `ins:ends`, constitutive terms, sections and party resolution (C7b). Parameter bindings, including a regime's durations from wording variables (C8). Threshold regimes over measured values held in capacity (applied layer, §7.8). Gates whose subject is another participant's share or another agreement (held design question HQ-2). Instruments without wording (HQ-1).

## Handoff

Written by the building machine when the work is ready for the human to commit.

- **Built:**
- **Not run:**
- **Check first:**
- **Deviations from the plan:**

## Results

Written on machine R at verification.
