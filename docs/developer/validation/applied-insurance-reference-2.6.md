<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: AIR-2.6, intensity measures, thresholds and units

**Unit:** [`applied-insurance-reference`](../status/applied-insurance-reference.md)
**Machine:** S (Copilot Business). **Branch:** `air/applied-reference`, commits `[AIR-2.6] …`
**Plan and test cases:** [Phase 2 plan](../plans/applied-insurance-reference-phase-2.md) (AIR-2.6 in detail)
**Decisions:** ADR-A98 (namespaces, addendum), ADR-A99

## Invariant

Each intensity measure has its own value space with a unit contract, threshold-defined cause concepts point at range sets on their measures' spaces, and units, currencies among them, are declared once in `insurance/common`, aligned to QUDT and ISO 4217.

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

- `vocab/peril-intensity.ttl` and its README sections.
- The units section of `insurance/common`'s README and `common-vocab.ttl`.
- The seven threshold range sets, read against the plan's table and its cited sources.
- The currency list, against ISO 4217 List One as published on the day of verification.

## Deliberate non-coverage

No exposure attribute links (`prl:relevantAttribute`, `prl:minimumGeoPrecision`), which AIR-4.2 writes in the exposure vocabulary. No parametric triggers.

## Handoff

Written by S in the `[AIR-2.6] Handoff` commit. S runs the checks itself, so say which ran.

- **Built:**
- **Run, with the result:**
- **Not run, and why:**
- **Versions used, if they differ from the plan's snapshot:**
- **Check first:**
- **Deviations from the plan:**

## Results

Written on machine R at verification.
