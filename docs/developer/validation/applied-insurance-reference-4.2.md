<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: AIR-4.2, zones, pools, attributes and assessments

**Unit:** [`applied-insurance-reference`](../status/applied-insurance-reference.md)
**Machine:** S (Copilot Business). **Branch:** `air/applied-reference`, commits `[AIR-4.2] …`
**Plan and test cases:** [Phase 4 plan](../plans/applied-insurance-reference-phase-4.md) (AIR-4.2 in detail)
**Decisions:** ADR-A98, ADR-A99. Decided 2026-10-13: the AIR-4.2 proposal, Q13, R6

## Invariant

A location carries zone designations and pool participations, every hazard attribute arrives as an attribute value in an evidenced assessment, and the peril vocabulary says which attributes and which geocoding precision each peril needs, so the shapes can warn when an exposure set lacks them.

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

- The `zones-attributes-assessments` sections of the exposure README and the Turtle they generate.
- The attribute type tables, each type's form, family and space, contract or datatype, and the OED fields cited, against the OED specification.
- The peril links table, read against the attribute types it names.
- `shapes/profiles/construction-protection.ttl` and `shapes/profiles/cyber-posture.ttl`.

## Deliberate non-coverage

No zone or class editions (AIR-4.6). No shapes for the six other profile families. Completeness is checked per location, not per asset. Peril scope comes only from `aeo:perilScope` on exposure set members until AIR-4.3 and AIR-4.4 add metrics and requirements.

## Handoff

Written by S in the `[AIR-4.2] Handoff` commit. S runs the checks itself, so say which ran.

- **Built:**
- **Run, with the result:**
- **Not run, and why:**
- **Versions used, if they differ from the plan's snapshot:**
- **Check first:**
- **Deviations from the plan:**

## Results

Written on machine R at verification.
