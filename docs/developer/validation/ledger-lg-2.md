<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: Ledger LG-2, the runtime document

**Unit:** `ledger` ([plan](../plans/ledger.md)). Its status record is created with LG-0.
**Machine:** as the maintainer assigns. **Branch:** `ledger/lg-2-runtime`. Commits are the maintainer's.
**Plan and test cases:** [Ledger plan](../plans/ledger.md) (LG-2 in detail)
**Decisions:** ADR-A131 decisions 4 and 6, LG-Q3 to LG-Q8

## Invariant

Postings, balance records and merge records are derived artefacts with natural keys, and their recorded values satisfy Ledger's laws (the fold, availability along the path, the credit ceiling, conservation after rounding), checked as shapes over the records (ADR-A131).

## Test cases

The table in the plan section above. Each row's result is recorded under Results at verification.

## One command

Run from the repository root.

```bash
mise run check
```

## Artefacts to inspect

`ontology/ledger/spec/ledger-runtime.ttl`, the runtime shapes, persistence's record families, the triple-store discovery entry for `owl:rational`, `tools/test_ledger.py`.

## Deliberate non-coverage

Computing postings and the two phases' order independence (B4a, CCS C12). Behaviour's migration (LG-3). Allocation (LG-4). Throughput (LG-5).

## Handoff

Written by the building machine when the work is ready for the maintainer to commit.

## Results

Written at verification.
