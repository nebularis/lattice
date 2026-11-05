<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: Ensemble ES-0, examples first

**Unit:** `ensemble` ([plan](../plans/ensemble.md)). Its status record is created with ES-0.
**Machine:** as the maintainer assigns. **Branch:** `ensemble/es-0-examples`. Commits are the maintainer's.
**Plan and test cases:** [Ensemble plan](../plans/ensemble.md) (ES-0 in detail)
**Decisions:** ADR-A130 decisions 1 to 12, ES-Q4, ES-Q7 to ES-Q9

## Invariant

The Ensemble model accepts lending, construction and insurance arrangements of related instruments and refuses a remaining cycle, a foreign section and a relation in two ensembles, as examples written before any term enters a spec (ADR-A-C2, ADR-A130).

## Test cases

The table in the plan section above. Each row's result is recorded under Results at verification.

## One command

Run from the repository root.

```bash
mise run check
```

## Artefacts to inspect

`ontology/ensemble/examples/`: twelve files, each with its hand-written order and facts passed.

## Deliberate non-coverage

The spec and shapes (ES-1). Composition (ES-3).

## Handoff

Written by the building machine when the work is ready for the maintainer to commit.

## Results

Written at verification.
