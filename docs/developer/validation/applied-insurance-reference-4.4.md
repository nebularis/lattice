<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: AIR-4.4, loss experience, cause chains, requirements and cover

**Unit:** [`applied-insurance-reference`](../status/applied-insurance-reference.md)
**Machine:** S (Copilot Business). **Branch:** `air/applied-reference`, commits `[AIR-4.4] …`
**Plan and test cases:** [Phase 4 plan](../plans/applied-insurance-reference-phase-4.md) (AIR-4.4 in detail)
**Decisions:** ADR-A98, ADR-A99, ADR-A103, epic D7 and D12. Decided 2026-10-13: Q11, Q12, Q14, R1, R3, R4, R5

## Invariant

An insured's loss experience states its period, source and completeness, each loss records its cause chain with recorded and effective characteristics kept apart, and requirements, existing cover, cover history and financial metrics are evidenced facts that gap analysis can read without any of them computing cover.

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

- `insurance/common`'s new loss event, GLIDE key scheme and class of business contract, and its 0.6.0 version IRI and every importer on the branch.
- The `losses-requirements-cover` sections of the exposure README.
- `tools/exposure_derivations.py` and `examples/losses.ttl`, which must be its output.
- The cause position notes and their case citations.

## Deliberate non-coverage

No link from a requirement to `ins:Obligation` (Phase 5). No class of business edition (AIR-4.6). No occurrence grouping under a contract (AIR-6.3). Liability populations come in AIR-4.5.

## Handoff

Written by S in the `[AIR-4.4] Handoff` commit. S runs the checks itself, so say which ran.

- **Built:**
- **Run, with the result:**
- **Not run, and why:**
- **Versions used, if they differ from the plan's snapshot:**
- **Check first:**
- **Deviations from the plan:**

## Results

Written on machine R at verification.
