<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: AIR-2.4, peril causes H, P, C, F and L, cross-group links

**Unit:** [`applied-insurance-reference`](../status/applied-insurance-reference.md)
**Machine:** S (Copilot Business). **Branch:** `air/applied-reference`, commits `[AIR-2.4] …`
**Plan and test cases:** [Phase 2 plan](../plans/applied-insurance-reference-phase-2.md) (AIR-2.4 in detail, and the shared rules for AIR-2.3 and AIR-2.4)
**Decisions:** ADR-A98 (namespaces, addendum), ADR-A99

## Invariant

Every concept of peril vocabulary §5.4 to §5.8 exists once with its characteristics, and every link between the two family groups exists once in `cross-group-links`.

## Test cases

The table in the plan section above. Each row's result is recorded under Results at
verification.

## One command

Run from the repository root. S runs it before the handoff commit. R runs it again at verification,
after `mise run build:ontology-catalog` and `mise run build:ontology-releases`, which S cannot do.

```bash
mise run check:ontology-catalog && mise run check:ontology-versioning
```

## Artefacts to inspect

- `vocab/peril-vocab.ttl`: regions `cause-H` to `cause-L` and `cross-group-links`.
- The overrides for H.WRA, P.PV.STK, F and L, read against the plan's tables.
- Ten definitions picked at random, read against the style rules.

## Deliberate non-coverage

No collections (AIR-2.5). No crosswalk (AIR-3.4).

## Handoff

Written by S in the `[AIR-2.4] Handoff` commit. S runs the checks itself, so say which ran.

- **Built:**
- **Run, with the result:**
- **Not run, and why:**
- **Versions used, if they differ from the plan's snapshot:**
- **Check first:**
- **Deviations from the plan:**

## Results

Written on machine R at verification.
