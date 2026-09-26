<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: AIR-1.1, drop the legacy contract module, create the layout

**Unit:** [`applied-insurance-reference`](../status/applied-insurance-reference.md)
**Machine:** S (Copilot Business). **Branch:** `air/1.1-layout`
**Plan and test cases:** [Phase 1 plan](../plans/applied-insurance-reference-phase-1.md) (AIR-1.1)
**Decisions:** ADR-A98 (decisions 1, 5, 6, 8, and its addendum)

## Invariant

The legacy module and its known defect are gone, no ontology or tool file refers to it, and the applied layer's READMEs describe the layout of ADR-A98.

## Test cases

The table in the plan section above. Each row's result is recorded under Results at
verification.

## One command

Run from the repository root on machine R, after `mise run build:ontology-catalog`.

```bash
mise run check:ontology-catalog && mise run check:ontology-versioning && ! grep -rnE 'ontology/nsd|neuro-semantic/insurance/contract|structure-vocab' ontology tools
```

## Artefacts to inspect

- `ontology/applied/README.md` and `ontology/applied/insurance/domain-README.md` against ADR-A98.
- The `KNOWN_DEFECTS` table in `tools/ontology_catalog.py`.

## Deliberate non-coverage

No new module is created. `insurance/common/` and `classification/` are AIR-1.2.

## Handoff

Written by the building machine when the work is committed. S could not run the command, so R runs it first.

- **Built:**
- **Not run:**
- **Check first:**
- **Deviations from the plan:**

## Results

Written on machine R at verification.
