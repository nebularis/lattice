<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: AIR-2.1, peril spec, scheme declarations and shapes

**Unit:** [`applied-insurance-reference`](../status/applied-insurance-reference.md)
**Machine:** S (Copilot Business). **Branch:** `air/2.1-peril-spec`
**Plan and test cases:** [Phase 2 plan](../plans/applied-insurance-reference-phase-2.md) (AIR-2.1 in detail)
**Decisions:** ADR-A98 (namespaces), ADR-A99

## Invariant

The `prl:` properties exist with the characteristics ADR-A99 fixes, every peril scheme of the reference edition is declared, and the well-formedness shapes accept a well-formed fixture and reject each defect they name.

## Test cases

The table in the plan section above. Each row's result is recorded under Results at
verification.

## One command

Run from the repository root on machine R, after `mise run build:ontology-catalog` and `mise run build:ontology-releases`.

```bash
mise run check:ontology-catalog && mise run check:ontology-versioning
```

## Artefacts to inspect

- `ontology/applied/insurance/peril/spec/peril.ttl`: `prl:canTrigger` and `prl:overlaps`.
- `vocab/peril-vocab.ttl`: the eight schemes and the region markers.
- `examples/well-formed.ttl` and `tools/test_peril_vocabulary.py`.

## Deliberate non-coverage

No concepts beyond the fixture (AIR-2.2 to AIR-2.4). The collections and crosswalk shapes are AIR-2.5 and AIR-3.4. The applied README and ontology architecture rows are added by R at verification.

## Handoff

Written by the building machine when the work is committed. S could not run the tests, so R runs them first.

- **Built:**
- **Not run:**
- **Check first:**
- **Deviations from the plan:**

## Results

Written on machine R at verification.
