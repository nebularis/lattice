<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: AIR-3.2, set readings and negation, Eligibility, IR, SPARQL, SHACL

**Unit:** [`applied-insurance-reference`](../status/applied-insurance-reference.md)
**Machine:** R (Claude Code). **Branch:** `air/3.2-set-readings`
**Plan and test cases:** [Phase 3 plan](../plans/applied-insurance-reference-phase-3.md) (AIR-3.2 in detail)
**Decisions:** ADR-A103

## Invariant

A bound condition reads several values by its binding's declared reading, a negated condition swaps Permitted and Denied and keeps Undetermined with its diagnostic, conditions without either evaluate as before, and SWRL and OWL refuse what they cannot yet compile.

## Test cases

The table in the plan section above. Each row's result is recorded under Results at
verification.

## One command

Run from the repository root on machine R, after `mise run build:ontology-catalog` and `mise run build:ontology-releases`.

```bash
mise run check:mork-compilers && mise run check:ontology-catalog && mise run check:ontology-versioning
```

## Artefacts to inspect

- The two examples and their recorded decisions.
- `elg:ValueReading`, `elg:valueReading`, `elg:negated`, `elg:L15`, `elg:L16`.
- The per-value aggregation and the negation swap in the SPARQL backend.
- The cascade: every re-pinned importer and its new version.

## Deliberate non-coverage

SWRL and OWL readings and negation (AIR-3.3). Correlated values across conditions (ADR-A103 decision 5).

## Handoff

Written by the building machine when the work is committed. R ran the command before handing over.

- **Built:**
- **Not run:**
- **Check first:**
- **Deviations from the plan:**

## Results

Written on machine R at verification.
