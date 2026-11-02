<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: PM-1, the surface backend that keeps a promotion's rows from a write's delta

**Unit:** [`projection-maintenance`](../status/projection-maintenance.md), slice PM-1 of the [plan](../plans/projection-maintenance.md), built on 2026-11-01 in autonomous mode.

**For the maintainer:** accept or change ADR-A16's addendum of 2026-11-01, and read the deviations and decisions below.

## Invariant

After any sequence of writes to a named-graph source, each followed in its request by a promotion's `clear` and `fill` over the nodes its delta touched, the promotion's rows are the rows a rebuild from the whole source gives, whether they lie beside the source or in a graph of their own (PM-Q1 (a′), PM-Q2 (a), PM-Q9 (ii) and (iii)).

## What changed

- **`surface.maintenance`.** `maintenance(contract)` gives a promotion's `clear` and `fill`, typed operations of the persistence IR, with the request-time parameters `$source` and `$derived` and the rows slot `touched`. It refuses an index contract by name (TD-138).
- **The CLI.** `surface maintenance --contracts ... --out <folder>` writes each contract's two operations and a `manifest.json`.
- **The IR.** A graph role, `derived`, for the rows of a surface contract.
- **Debt and decision.** TD-138, and ADR-A16's addendum.

## Tests

| ID | Given / When / Then | Level | Pass |
|---|---|---|---|
| PM1-T1 | a promotion over a one-step path, a two-step path and a path with an inverse step, each placed beside its source and in a graph of its own / 40 random writes, each with its clear and fill / after every write the rows equal a rebuild's | L2 | rdflib and Oxigraph |
| PM1-T2 | a carrier whose type is removed, then added back / the writes / its rows go, then come back | L4 | |
| PM1-T3 | an index contract / `maintenance` / refused, naming TD-138 | L1, negative | |
| PM1-T4 | the studio's six contracts / `maintenance` / each renders a clear and a fill | L3 | |

**The one command:** `mise run check:python-root`, which runs `surface.test_maintenance` beside the surface compiler's other tests.

## Results, 2026-11-01

`mise exec -- python -m unittest surface.test_maintenance -v`: 4 tests, OK.

## Deviations from the plan

1. **The index contract is not maintained in the write.** Its symbols are minted under its naming policy, which the write would have to compute in SPARQL. The studio has none, so it waits as TD-138.
2. **A source in a shared data graph is not maintained in the write,** for the same reason, since its carriers must be confined to the aggregate by its owned path. The studio's sources are named graphs.
3. **The record of the contracts that built a partition moves to PM-2,** which reads it at start to decide what to rebuild (PM-Q3, PM-Q7), so it is written where it is read.
4. **The summaries template moves to PM-2,** which changes the reads that use it.

## Decisions taken alone, for the maintainer's review

1. **Touched nodes are the delta's subjects and its IRI objects,** so a read path with an inverse step finds its carrier from either end.
2. **A delta that touches nothing sends neither operation,** since there is nothing to maintain. rdflib 7.6 also fails on a `VALUES` block with no rows.
3. **The operations are the persistence IR's,** so they are rendered, guarded and statically checked as every generated write is (PRI-55, PRI-60). `tools/surface` depends on the persistence compiler for that.
