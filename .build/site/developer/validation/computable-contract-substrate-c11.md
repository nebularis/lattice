<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: CCS C11, runtime records and occasions

**Unit:** [`computable-contract-substrate`](../status/computable-contract-substrate.md)
**Machine:** R. **Branch:** `ccs/c11-runtime-records`
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
  - configuration `behaviour` 0.9.0 with `bhv:initialState`
  - runtime `behaviour-runtime` 0.9.0 with `bhv:Occasion`, `bhv:Record` and six record kinds,
    `bhv:enteredBy` and 18 properties, each stating its subject and value
  - `behaviour-vocab` 0.9.0 with `bhv:OccasionStates`, its six states and `bhv:Pending` initial
  - shapes 0.3.0 (breaking): B6 and I11 in SHACL Core, B1 and the initial-state rule in SHACL-SPARQL,
    and a subject and a class shape per new property
  - capacity's execution profile 0.9.0, re-pinned to runtime 0.9.0
  - two examples, the README's records table, extension rule and release notes, and
    `tools/test_behaviour_records.py`
- **Not run:** nothing skipped. The reasoner rows ran.
- **Check first:**
  - The brief put `fnd:recordedAt` and `fnd:assertedBy` on records. Foundation declares both on
    `fnd:Evidence`, so a record carries them on its evidence, and its valid time on a
    `fnd:TemporalScope`, as state occupancies already do. Putting them on the record would have
    inferred every record a piece of evidence.
  - `bhv:Record` is added above the six record kinds, so `fromStimulus` and `actor` have one domain.
  - `bhv:forCase` has no domain, since an occasion and an act record both use it. A Core shape checks
    its subject is one of the two.
  - An occasion's executions name no transition definition, because its transitions are the
    evaluator's (C12), not declared.
  - B6 cannot tell evidence of taking effect from evidence of an external log: both are
    `fnd:hasEvidence`. Telling them apart needs the evidence kinds C12 will write.
- **Deviations from the plan:** the record evidence and `bhv:Record`, as above.
- **Tags for the maintainer:** `behaviour-v0.9.0`, `behaviour-runtime-v0.9.0`, `behaviour-vocab-v0.9.0`,
  `behaviour-shapes-v0.3.0`, `applied-capacity-execution-v0.9.0`.

## Results

Verified on machine R, 2026-10-01, with the reasoning harness built.

| ID | Result |
|---|---|
| C11-01 | pass |
| C11-02 | pass: all four Behaviour examples conform |
| C11-03 | pass (B6 mandatory probe) |
| C11-04 | pass |
| C11-05 | pass (B1) |
| C11-06 | pass: a persistent identity as party fails, a later-superseded occupancy version conforms (I11 mandatory probe) |
| C11-07 | pass, 19 properties |
| C11-08 | pass |
| C11-09 | pass, both new examples consistent |
| C11-10 | pass: five release rows, shapes 0.3.0 marked breaking in the README |
| C11-11 | pass: `check:ontology-catalog` 155, `check:python-root` 84 and Phase 8 conformance, `check:mork-compilers` 114 |
| C11-12 | pass |
| C11-13 | pass: `0.9.0`, and every existing fixture and the conformance case still conform |

`mise run topology:links`: 427, the baseline.
