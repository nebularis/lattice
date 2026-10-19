<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: AIR-3.5, lowering, list to list, and milestone M2

**Unit:** [`applied-insurance-reference`](../status/applied-insurance-reference.md)
**Machine:** S (Copilot Business). **Branch:** `air/applied-reference`, commits `[AIR-3.5] …`
**Plan and test cases:** [Phase 3 plan](../plans/applied-insurance-reference-phase-3.md) (AIR-3.5 in detail)
**Decisions:** ADR-A100, ADR-A103. Milestone M2

## Invariant

A reference concept lowers to a list's code only through an exact mapping, a list-to-list correspondence through the reference is exact only when both legs are, and the cyber write-back check decides on the reference, is Undetermined with a reason on a flat list, and decides exactly mapped codes of a crosswalked list.

## Test cases

The table in the plan section above. Each row's result is recorded under Results at
verification.

## One command

Run from the repository root. S runs it before the handoff commit. R runs it again at verification,
after `mise run build:ontology-catalog` and `mise run build:ontology-releases`, which S cannot do.

```bash
mise exec -- python -m pytest tools/test_peril_vocabulary.py tools/test_exposure_ontology.py -q && mise run check:ontology-catalog && mise run check:ontology-versioning
```

## Artefacts to inspect

- `lower` and `compose` in `tools/peril_crosswalk.py`.
- `insurance/exposure/examples/m2.ttl` and the M2 decision table, with diagnostics.

## Deliberate non-coverage

SWRL and OWL agreement waits for AIR-3.3, built on R.

## Handoff

Written by S in the `[AIR-3.5] Handoff` commit. S runs the checks itself, so say which ran.

- **Built:**
- **Run, with the result:**
- **Not run, and why:**
- **Versions used, if they differ from the plan's snapshot:**
- **Check first:**
- **Deviations from the plan:**

## Results

Written on machine R at verification.
