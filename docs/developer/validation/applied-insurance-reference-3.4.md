<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: AIR-3.4, crosswalks and lifting at ingestion

**Unit:** [`applied-insurance-reference`](../status/applied-insurance-reference.md)
**Machine:** S (Copilot Business). **Branch:** `air/applied-reference`, commits `[AIR-3.4] …`
**Plan and test cases:** [Phase 3 plan](../plans/applied-insurance-reference-phase-3.md) (AIR-3.4 in detail)
**Decisions:** ADR-A100, ADR-A13. Pending AIR-3.4-Q1 and Q2, built at their leanings

## Invariant

A crosswalk is a reviewed graph of SKOS mapping triples and characteristic values, recorded as a derived artefact whose read set is the two scheme editions. Only an exact mapping lifts a value to the reference, and a crosswalk is stale as soon as either edition changes.

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

- `crosswalk/oed-perils.ttl` against the OED specification and AIR-2.3's notations.
- `crosswalk/house-list.ttl` and its notes on inexact matches.
- `tools/peril_crosswalk.py` (`lift`, `stale`).
- The ingestion mapping and its compiled RML.

## Deliberate non-coverage

No crosswalk of the CBAA cause-of-loss list (AIR-3.4-Q1). RML is compiled, not run.

## Handoff

Written by S in the `[AIR-3.4] Handoff` commit. S runs the checks itself, so say which ran.

- **Built:**
- **Run, with the result:**
- **Not run, and why:**
- **Versions used, if they differ from the plan's snapshot:**
- **Check first:**
- **Deviations from the plan:**

## Results

Written on machine R at verification.
