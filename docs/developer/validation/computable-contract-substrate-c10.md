<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: CCS C10, Behaviour below Instrument, configuration and runtime

**Unit:** [`computable-contract-substrate`](../status/computable-contract-substrate.md)
**Machine:** R (Claude Code). **Branch:** `ccs/c10-behaviour-split`
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
- **Not run:**
- **Check first:**
- **Deviations from the plan:**

## Results

Written on machine R at verification.
