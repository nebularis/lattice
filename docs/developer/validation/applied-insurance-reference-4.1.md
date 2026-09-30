<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: AIR-4.1, exposure core

**Unit:** [`applied-insurance-reference`](../status/applied-insurance-reference.md)
**Machine:** S (Copilot Business). **Branch:** `air/4.1-exposure-core`
**Plan and test cases:** [Phase 4 plan](../plans/applied-insurance-reference-phase-4.md) (AIR-4.1 in detail)
**Decisions:** ADR-A98 (layout, namespaces), ADR-A102

## Invariant

An exposure set version, its locations, assets, interests and valuations, and the parties and control relations behind them, exist on LATTICE's own constructs, with the regions later Phase 4 slices fill.

## Test cases

The table in the plan section above. Each row's result is recorded under Results at
verification.

## One command

Run from the repository root on machine R, after `mise run build:ontology-catalog` and `mise run build:ontology-releases`.

```bash
mise run check:ontology-catalog && mise run check:ontology-versioning
```

## Artefacts to inspect

- `ontology/applied/insurance/exposure/spec/exposure.ttl`: imports, the seven classes, disjointness.
- `vocab/exposure-vocab.ttl`: the six contracts, their schemes and the programme roles.
- `shapes/structural.ttl` and `shapes/constraints.ttl`: the valuation either-or rule and the control cycle rule.
- `examples/core.ttl` and `tools/test_exposure_ontology.py`.

## Deliberate non-coverage

No peril link, zones, attributes, dependencies, metrics, losses or liability (AIR-4.2 to AIR-4.5). No persistence or privacy profiles (AIR-4.6).

## Handoff

Written by the building machine when the work is committed. S could not run the tests, so R runs them first.

- **Built:**
- **Not run:**
- **Check first:**
- **Deviations from the plan:**

## Results

Written on machine R at verification.
