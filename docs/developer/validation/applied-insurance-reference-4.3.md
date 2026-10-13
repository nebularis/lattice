<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: AIR-4.3, dependencies, peril metrics and exposure units

**Unit:** [`applied-insurance-reference`](../status/applied-insurance-reference.md)
**Machine:** S (Copilot Business). **Branch:** `air/applied-reference`, commits `[AIR-4.3] …`
**Plan and test cases:** [Phase 4 plan](../plans/applied-insurance-reference-phase-4.md) (AIR-4.3 in detail)
**Decisions:** ADR-A90, ADR-A98, epic E3, R8, R9. Milestone M3, first half

## Invariant

Dependencies between locations, assets and third parties are evidenced relations, peril metrics are derived artefacts with comparable scopes, and exposure units are computed on demand for the perils a check asks about, never asserted by hand and never required to be stored.

## Test cases

The table in the plan section above. Each row's result is recorded under Results at
verification.

## One command

Run from the repository root. S runs it before the handoff commit. R runs it again at verification,
after `mise run build:ontology-catalog` and `mise run build:ontology-releases`, which S cannot do.

```bash
mise exec -- python -m pytest tools/test_exposure_ontology.py -q && mise run check:ontology-catalog && mise run check:ontology-versioning
```

## Artefacts to inspect

- The `dependencies-metrics-units` sections of the exposure README.
- `exposure_units` in `tools/exposure_derivations.py`.
- `examples/units.ttl` and the M3 decisions, and that the source graph holds no units afterwards.
- The Open Results Data citations.

## Deliberate non-coverage

No maximum foreseeable interruption derivation. No catastrophe model results (epic §7).

## Handoff

Written by S in the `[AIR-4.3] Handoff` commit. S runs the checks itself, so say which ran.

- **Built:**
- **Run, with the result:**
- **Not run, and why:**
- **Versions used, if they differ from the plan's snapshot:**
- **Check first:**
- **Deviations from the plan:**

## Results

Written on machine R at verification.
