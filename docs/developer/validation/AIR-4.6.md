<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: AIR-4.6, London and US profiles and worked examples

**Unit:** [`applied-insurance-reference`](../status/applied-insurance-reference.md)
**Machine:** S (Copilot Business). **Branch:** `air/applied-reference`, commits `[AIR-4.6] …`
**Plan and test cases:** [Phase 4 plan](../plans/applied-insurance-reference-phase-4.md) (AIR-4.6 in detail)
**Decisions:** ADR-A98, ADR-A99. Milestone M3, second half

## Invariant

A market profile is scheme bindings and shapes and never a class. The London and US profiles bind example editions for every market-bound contract of Phase 4 and make their market's required data mandatory, and the worked examples pass under each profile.

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

- `examples/profile-us.ttl`, `examples/profile-london.ttl` and their editions' citations.
- `shapes/profiles/market-us.ttl`, `shapes/profiles/market-london.ttl`.
- The worked examples and `examples/persistence.ttl`, which R re-checks against Persistence at the merge.

## Deliberate non-coverage

No maintained editions: every edition here is an example (epic §7).

## Handoff

Written by S in the `[AIR-4.6] Handoff` commit. S runs the checks itself, so say which ran.

- **Built:**
- **Run, with the result:**
- **Not run, and why:**
- **Versions used, if they differ from the plan's snapshot:**
- **Check first:**
- **Deviations from the plan:**

## Results

Written on machine R at verification.
