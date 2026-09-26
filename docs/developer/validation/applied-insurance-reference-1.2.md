<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: AIR-1.2, shared contracts

**Unit:** [`applied-insurance-reference`](../status/applied-insurance-reference.md)
**Machine:** S (Copilot Business). **Branch:** `air/1.2-shared-contracts`
**Plan and test cases:** [Phase 1 plan](../plans/applied-insurance-reference-phase-1.md) (AIR-1.2)
**Decisions:** ADR-A98 (decisions 1, 5, 6), ADR-A102

## Invariant

Every classification the epic needs has one `voc:SchemeContract` at the lowest level of sharing that covers its users, the liability role types exist as `pty:Role` individuals, and the cross-domain module imports nothing from a domain.

## Test cases

The table in the plan section above. Each row's result is recorded under Results at
verification.

## One command

Run from the repository root on machine R, after `mise run build:ontology-catalog` and `mise run build:ontology-releases`.

```bash
mise run check:ontology-catalog && mise run check:ontology-versioning
```

## Artefacts to inspect

- `ontology/applied/classification/` and `ontology/applied/insurance/common/`: both documents of each, and their READMEs.
- `tools/test_applied_shared_contracts.py`.

## Deliberate non-coverage

No reference editions are bound (AIR-2.2 onwards). The loss event (AIR-4.4) and the liability direction scheme (Phase 5) come later.

## Handoff

Written by the building machine when the work is committed. S could not run the tests, so R runs them first.

- **Built:**
- **Not run:**
- **Check first:**
- **Deviations from the plan:**

## Results

Written on machine R at verification.
