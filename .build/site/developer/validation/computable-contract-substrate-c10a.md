<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: CCS C10a, the import guard

**Unit:** [`computable-contract-substrate`](../status/computable-contract-substrate.md)
**Machine:** R. **Branch:** `ccs/c10a-import-guard`
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

- **Built:** `tools/import_guard.py` (the order table, an imports check and a namespace scan),
  `check:import-guard` in `mise.toml` and in `check`'s dependencies, six fixture trees under
  `tools/fixtures/import_guard/`, `tools/test_import_guard.py` in `check:ontology-catalog`'s list,
  the check named beside the diagram in `ontology-architecture.md`, and an implementation note on
  ADR-A01.
- **Not run:** nothing skipped.
- **Check first:**
  - Behaviour's configuration and runtime documents share one namespace, so the namespace scan
    treats them as one layer. The runtime document's import of configuration is the same layer.
  - Namespaces outside the order (Executable, MORK, Surface, Persistence) are not judged, so a
    substrate layer naming one passes.
  - C10a-04 parses the diagram's tree, including Instrument's "also imports behaviour
    configuration", so a change to either the diagram or the table fails the test until both agree.
- **Deviations from the plan:** six fixture trees instead of "one passing layer and four failing
  ones": the brief's own list names five failing cases, and the passing tree also carries the
  projection case (C10a-03).

## Results

Verified on machine R, 2026-10-01.

| ID | Result |
|---|---|
| C10a-01 | pass: 0 violations across the 8 substrate layers |
| C10a-02 | pass: all five failing fixtures exit 1 with file, line and namespace |
| C10a-03 | pass |
| C10a-04 | pass: the diagram parses to the table, layer for layer |
| C10a-05 | pass |

Also: `check:ontology-catalog` 148 tests, `check:ontology-versioning` exits 0, links at the
baseline (427).
