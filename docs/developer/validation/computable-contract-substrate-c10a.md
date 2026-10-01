<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: CCS C10a, the import guard

**Unit:** [`computable-contract-substrate`](../status/computable-contract-substrate.md)
**Machine:** R (Claude Code). **Branch:** `ccs/c10a-import-guard`
**Plan and test cases:** [CCS plan](../plans/computable-contract-substrate.md) (C10A in detail)
**Decisions:** ADR-A01 and its addendum, ADR-A106 law B7. Questions C10a-Q1, C10a-Q2 decided 2026-10-01

## Invariant

A design-time check, over the substrate layers only, fails when a layer imports a higher layer, or when any Turtle file under it names a higher or sibling layer's namespace. Today it finds nothing.

## Test cases

The table in the plan section above. Each row's result is recorded under Results at
verification.

## One command

Run from the repository root on machine R, with the reasoning harness built where a row is L2.

```bash
mise run check:import-guard && mise run check:ontology-catalog
```

## Artefacts to inspect

- `tools/import_guard.py`: the order table and the two checks.
- `tools/fixtures/import_guard/`: the five failing cases.

## Deliberate non-coverage

Applied modules, MORK, SPC, Surface, Persistence and `ontology/examples` (C10a-Q2). Markdown prose naming a higher layer.

## Handoff

Written by the building machine when the work is committed.

- **Built:**
- **Not run:**
- **Check first:**
- **Deviations from the plan:**

## Results

Written on machine R at verification.
