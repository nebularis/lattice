<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Computable contract substrate - Status

**Unit ID:** `computable-contract-substrate`
**Status:** 📝 Proposed. Nothing implemented. Blocked on the plan's §8 decisions CC-D1 to CC-D8
**Last updated:** 2026-09-30
**Plan:** [computable-contract-substrate.md](../plans/computable-contract-substrate.md)
**Sketches:** [computable-contract-substrate.md](../sketches/computable-contract-substrate.md),
[contract-amounts.md](../sketches/contract-amounts.md)
**ADRs:** A-104, A-106, A-112, A-113, none drafted
**Machine:** R

## Current position

The design is sketched and tested against four instruments (91 scenarios, 50 amount constructs).
No ADR is drafted and no ontology document is touched.

**Next action, for the human:** take CC-D1 to CC-D8.
**Next action, for the agent, once they are taken:** brief and draft C0 (A-112, A-113).

## Slice board

| # | Slice | Tranche | State | Blocked on |
|---|---|---|---|---|
| C0 | A-112, A-113 | A | waiting | CC-D1, CC-D2, CC-D4 |
| C1 | A-104 | A | waiting | CC-D5 to CC-D8 |
| C2 | A-106 | A | waiting | CC-D8 |
| C3 to C5 | Wording layer | B | waiting | Gate A |
| C6 to C9 | Instrument rewrite | C | waiting | C5 |
| C10 to C12 | Behaviour | D | waiting | C6 |
| C13 | evaluation | E | waiting | C9, C12, AIR-3.3, NRS N1 |
| C14 to C17 | examples, docs, handoff | F | waiting | C9, C12 |

## History

- 2026-09-29 to 30: D2 walkthrough, first Instrument redesign, tests against the AIG package policy,
  the IUA broker binding authority and the Lloyd's CBAA collateral, and cross-reference with Open
  CBAA's `wim`, `stm`, `agr` and `rsk` modules and design documents.
- 2026-09-30: sketches, plan and this record written. NRS, AIR and platform plans updated.
