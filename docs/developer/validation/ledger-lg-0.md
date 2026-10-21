<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: Ledger LG-0, examples first

**Unit:** `ledger` ([plan](../plans/ledger.md)). Its status record is created with LG-0.
**Machine:** as the maintainer assigns. **Branch:** `ledger/lg-0-examples`. Commits are the maintainer's.
**Plan and test cases:** [Ledger plan](../plans/ledger.md) (LG-0 in detail)
**Decisions:** ADR-A131 (decisions 3 to 6), LG-Q1 to LG-Q8

## Invariant

The Ledger model accepts licensing, lending, grants, delegated authority and insurance arrangements of amounts consumed and restored, and refuses a cyclic tree, a unit mismatch, an unrounded proportional rule and an overdraw under the refuse rule, as examples written before any term enters a spec (ADR-A-C2, ADR-A131).

## Test cases

The table in the plan section above. Each row's result is recorded under Results at verification.

## One command

Run from the repository root.

```bash
mise run check
```

## Artefacts to inspect

`ontology/ledger/examples/`: ten files, each with its hand-computed table.

## Deliberate non-coverage

The spec and shapes (LG-1, LG-2). Computing the records (B4a, CCS C12).

## Handoff

Written by the building machine when the work is ready for the maintainer to commit.

## Results

Written at verification.
