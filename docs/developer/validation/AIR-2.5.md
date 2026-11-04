<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: AIR-2.5, collections and the open-perils example

**Unit:** [`applied-insurance-reference`](../status/applied-insurance-reference.md)
**Machine:** S (Copilot Business). **Branch:** `air/applied-reference`, commits `[AIR-2.5] …`
**Plan and test cases:** [Phase 2 plan](../plans/applied-insurance-reference-phase-2.md) (AIR-2.5 in detail)
**Decisions:** ADR-A87, ADR-A99, ADR-A100. Milestone M1

## Invariant

Collections are editioned with the vocabulary, a collection used in a scope is expanded into concepts when the scope is bound, and an open-perils grant with exclusions admits and denies perils as the sketch states, with no Eligibility change.

## Test cases

The table in the plan section above. Each row's result is recorded under Results at
verification.

## One command

Run from the repository root. S runs it before the handoff commit. R runs it again at verification,
after `mise run build:ontology-catalog` and `mise run build:ontology-releases`, which S cannot do.

```bash
mise exec -- python -m pytest tools/test_peril_vocabulary.py -q && mise run check:ontology-catalog && mise run check:ontology-versioning
```

## Artefacts to inspect

- `vocab/peril-collections.ttl` and its README section.
- `tools/peril_binding.py`.
- `examples/open-perils.ttl`, which must equal the function's output, and the M1 decision table.
- The OED group codes, against the OED specification.

## Deliberate non-coverage

No special-form exclusion collection for the US edition. No generated classes from collections (substrate S5).

## Handoff

Written by S in the `[AIR-2.5] Handoff` commit. S runs the checks itself, so say which ran.

- **Built:**
- **Run, with the result:**
- **Not run, and why:**
- **Versions used, if they differ from the plan's snapshot:**
- **Check first:**
- **Deviations from the plan:**

## Results

Written on machine R at verification.
