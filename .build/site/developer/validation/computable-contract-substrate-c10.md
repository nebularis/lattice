<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: CCS C10, Behaviour below Instrument, configuration and runtime

**Unit:** [`computable-contract-substrate`](../status/computable-contract-substrate.md)
**Machine:** R. **Branch:** `ccs/c10-behaviour-split`
**Plan and test cases:** [CCS plan](../plans/computable-contract-substrate.md) (C10 in detail)
**Decisions:** ADR-A106, ADR-A11 as amended, ADR-A01's addendum, ADR-A113. C10-Q1, C10-Q2 decided 2026-10-01

## Invariant

Behaviour imports nothing above Eligibility and names no Instrument term. Configuration and
runtime are two documents in one namespace, split by ADR-A08's tiers. Effects target any
resource, occupancies may be for any subject, a transition needs no effect, and policies stay
required. Existing fixtures keep their meaning.

## Test cases

The table in the plan section above. Each row's result is recorded under Results at
verification.

## One command

Run from the repository root on machine R.

```bash
mise run build:ontology-catalog && mise run check:ontology-versioning && mise run check:ontology-catalog && mise run check:python-root
```

## Artefacts to inspect

- `ontology/behaviour/spec/behaviour.ttl` and `behaviour-runtime.ttl`: which class is in which.
- `ontology/behaviour/shapes/structural.ttl`: the target rule's alternative paths.
- `tools/test_behaviour_split.py`: the before-and-after fixture comparison, C10-10.

## Deliberate non-coverage

Occasions, records and the evidence rule's shapes (C11). The import guard (C10a). Instrument's
`ins:InstrumentTarget` (C6). Nested states and history (C11a).

## Handoff

Written by the building machine when the work is committed.

- **Built:**
  - configuration `behaviour` 0.8.0 and the new `behaviour-runtime` 0.8.0, split by ADR-A08's tiers
  - `bhv:targets` (no range) with `targetsOccupancy` and `targetsAllowance` as sub-properties
  - `bhv:forSubject` without a range, the `hasEffect` minimum removed, the Instrument import removed
  - `behaviour-vocab` 0.8.0 with `bhv:InstrumentTarget` deprecated
  - shapes 0.2.0 with `EffectDefinitionShape`, projection 0.2.0 without `instrument.ttl`
  - capacity's execution profile 0.8.0, importing runtime
  - the three fixtures renamed, the README with a release notes section, `tools/test_behaviour_split.py`
  - the architecture documents' Behaviour rows
- **Not run:** nothing skipped.
- **Check first:**
  - The README is again the literate source of configuration, vocab and structural shapes, which
    repairs their existing drift (a missing property, the vocab header, a missing shape). The
    runtime document is authored as a file, since the extractor writes one spec per layer.
  - The three fixtures that targeted `ins:Obligation` now declare their own target kind and target
    class (`ex:ApplicationTarget`, `ex:RecordTarget`), as ADR-A106 decision 2 has the owner of a
    target declare its kind. None uses the deprecated `bhv:InstrumentTarget`. Revised in review.
  - `tools/test_ontology_catalog.py`'s closure test encoded ADR-A01's old order. It now asserts
    the accepted one: Behaviour reaches the layers below it and not Instrument.
  - `applied/capacity` gains a README (added in review): what is authored (the `capx` execution
    profile) and what is only designed (the `cap:` source ontology), where it sits, and release
    notes with the 0.8.0 breaking entry.
- **Deviations from the plan:** none. C10-02 was first scoped to the layer's documents, then
  restored to every file once the fixtures were made neutral.
- **Tags for the maintainer:** `behaviour-v0.8.0`, `behaviour-runtime-v0.8.0`, `behaviour-vocab-v0.8.0`,
  `behaviour-shapes-v0.2.0`, `behaviour-projection-v0.2.0`, `applied-capacity-execution-v0.8.0`.

## Results

Verified on machine R, 2026-10-01.

| ID | Result |
|---|---|
| C10-01 | pass |
| C10-02 | pass: every Behaviour file and the conformance case, no deprecated kind in a fixture |
| C10-03 | pass, `targets` and `forSubject` |
| C10-04 | pass: 13 declaration classes in configuration, 5 runtime classes in runtime |
| C10-05 | pass |
| C10-06 | pass: no selection policy, and `PriorityOrdered` without a priority, each fail |
| C10-07 | pass: a target through `bhv:targets` and through `bhv:targetsAllowance` |
| C10-08 | pass: no target, and no target kind, each fail |
| C10-09 | pass: under RDFS closure neither subject nor target gains a type |
| C10-10 | pass: all five fixtures conform, as they did before the change |
| C10-11 | pass: capacity reaches runtime and configuration, and no Instrument document |
| C10-12 | pass |
| C10-13 | pass: six release rows. `check:ontology-versioning` exits 0 |
| C10-14 | pass: `check:ontology-catalog` 139, `check:python-root` 84 and Phase 8 conformance, `check:mork-compilers` 114 |

`mise run topology:links`: 427 broken links, the baseline, none in a changed file.
