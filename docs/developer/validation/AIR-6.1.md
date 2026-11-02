<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: AIR-6.1, submission

**Unit:** [`applied-insurance-reference`](../status/applied-insurance-reference.md)
**Machine:** S (Copilot Business). **Branch:** `air/applied-reference`, commits `[AIR-6.1] …`
**Plan and test cases:** [Phase 6 plan](../plans/applied-insurance-reference-phase-6.md) (AIR-6.1 in detail)
**Decisions:** ADR-A98 (the `sbm:` prefix). AIR-6.1-Q1, decided 2026-10-14. Milestone M6, first half

## Invariant

A submission cites one exposure set version and the requirements and existing cover of that version, records which insurers were approached and how each responded, and records what each insurer asked for. Information gaps are derived from the data, never authored, and adding data only ever closes gaps.

## Test cases

The table in the plan section above. Each row's result is recorded under Results at
verification.

## One command

Run from the repository root. S runs it before the handoff commit. R runs it again at verification,
after `mise run build:ontology-catalog` and `mise run build:ontology-releases`, which S cannot do.

```bash
mise exec -- python -m pytest tools/test_submission.py tools/test_exposure_ontology.py -q && mise run check:ontology-catalog && mise run check:ontology-versioning
```

## Artefacts to inspect

- The new module `ontology/applied/insurance/submission/` and its README.
- `tools/submission_gaps.py` and the monotonicity test.
- `examples/submission.ttl`.

## Deliberate non-coverage

No claims (AIR-6.2, after Phase 5). No workflow around requests: [leftovers](../plans/air-leftovers.md) §1.

## Handoff

Written by S in the `[AIR-6.1] Handoff` commit. S runs the checks itself, so say which ran.

- **Built:**
- **Run, with the result:**
- **Not run, and why:**
- **Versions used, if they differ from the plan's snapshot:**
- **Check first:**
- **Deviations from the plan:**

## Results

Written on machine R at verification.
