<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: Ledger LG-1, the configuration document

**Unit:** `ledger` ([plan](../plans/ledger.md)). Its status record is created with LG-0.
**Machine:** as the maintainer assigns. **Branch:** `ledger/lg-1-configuration`. Commits are the maintainer's.
**Plan and test cases:** [Ledger plan](../plans/ledger.md) (LG-1 in detail)
**Decisions:** ADR-A131 decisions 1 to 3, 5, 6 and 8, LG-Q1, LG-Q2, LG-Q6 to LG-Q8

## Invariant

Account definitions, their tree, owner kinds, merge rules, rounding, reset, keys, purposes, ceilings and conversion are configuration, and shapes refuse every malformed tree, with Ledger importing only Foundation, Vocabulary and Quantification (ADR-A131, ADR-A01's 2026-10-19 addendum).

## Test cases

The table in the plan section above. Each row's result is recorded under Results at verification.

## One command

Run from the repository root.

```bash
mise run check
```

## Artefacts to inspect

`ontology/ledger/README.md`, `spec/ledger.ttl`, `vocab/ledger-vocab.ttl`, `shapes/`, the root catalogue, `tools/test_ledger.py`, the release notes.

## Deliberate non-coverage

Runtime records (LG-2). Behaviour's migration (LG-3).

## Handoff

Written by the building machine when the work is ready for the maintainer to commit.

## Results

Written at verification.
