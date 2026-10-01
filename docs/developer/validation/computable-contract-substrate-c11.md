<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: CCS C11, runtime records and occasions

**Unit:** [`computable-contract-substrate`](../status/computable-contract-substrate.md)
**Machine:** R (Claude Code). **Branch:** `ccs/c11-runtime-records`
**Plan and test cases:** [CCS plan](../plans/computable-contract-substrate.md) (C11 in detail)
**Decisions:** ADR-A106 decisions 4 and 5, laws B1, B2, B6, ADR-A92, ADR-A113. Questions C11-Q1, C11-Q2 decided 2026-10-01

## Invariant

Configuration gains declared initial states. The runtime document gains occasions, with a fixed core state space refined by sub-states (C11a), and records named without any Instrument term. Every state entry is recorded (B6), occasion occupancies are derived (B1), and an occasion's parties are fixed at arising (I11).

## Test cases

The table in the plan section above. Each row's result is recorded under Results at
verification.

## One command

Run from the repository root on machine R, with the reasoning harness built where a row is L2.

```bash
mise run build:ontology-catalog && mise run check:ontology-versioning && mise run check:ontology-catalog && mise run check:python-root
```

## Artefacts to inspect

- `ontology/behaviour/spec/behaviour-runtime.ttl`: the occasion and the six record classes.
- `ontology/behaviour/shapes/`: B6, B1 and the I11 probe.
- `ontology/behaviour/vocab/behaviour-vocab.ttl`: the occasion state space and its initial state.
- `ontology/behaviour/spec/behaviour.ttl`: `bhv:initialState`.

## Deliberate non-coverage

The evaluator that derives occasions and records (C12). Nested states and history (C11a). Positions on stimuli (NRS N6, with C12).

## Handoff

Written by the building machine when the work is committed.

- **Built:**
- **Not run:**
- **Check first:**
- **Deviations from the plan:**

## Results

Written on machine R at verification.
