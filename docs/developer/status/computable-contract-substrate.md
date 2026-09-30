<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Computable contract substrate - Status

**Unit ID:** `computable-contract-substrate`
**Status:** 📝 Proposed. CC-D1 to CC-D7 and CC-D9 to CC-D11 decided. CC-D8 next
**Last updated:** 2026-09-30
**Plan:** [computable-contract-substrate.md](../plans/computable-contract-substrate.md)
**Sketches:** [computable-contract-substrate.md](../sketches/computable-contract-substrate.md),
[contract-amounts.md](../sketches/contract-amounts.md)
**ADRs:** A-104, A-106, A-112, A-113, none drafted
**Machine:** R

## Current position

The design is sketched and tested against four instruments and a proposed Lloyd's schedule 
(101 scenarios, S79 merged, and 50 amount constructs). No ADR is drafted and no ontology 
document is touched.

**Next action, for the human:** CC-D8.
**Next action, for the agent, once they are taken:** brief and draft C0 (A-112, A-113).

## Slice board

| # | Slice | Tranche | State | Blocked on |
|---|---|---|---|---|
| C0 | A-112, A-113 | A | waiting | CC-D1, CC-D2, CC-D4 |
| C1 | A-104 | A | waiting | CC-D5 to CC-D8 |
| C2 | A-106 | A | waiting | CC-D8 |
| C3 to C5 | Wording layer | B | waiting | Gate A |
| F1 | Foundation identifiers | Foundation window | waiting | AIR Phase 2 complete, with NRS N9 |
| C6 to C9 | Instrument rewrite | C | waiting | C5 |
| C10 to C12 | Behaviour | D | waiting | C6 |
| C13 | evaluation | E | waiting | C9, C12, AIR-3.3, NRS N1 |
| C14 to C17 | examples, docs, handoff | F | waiting | C9, C12 |

## History

- 2026-09-29 to 30: D2 walkthrough, first Instrument redesign, tests against the AIG package policy,
  the IUA broker binding authority and the Lloyd's CBAA collateral, and cross-reference with Open
  CBAA's `wim`, `stm`, `agr` and `rsk` modules and design documents.
- 2026-09-30: sketches, plan and this record written. NRS, AIR and platform plans updated.
- 2026-09-30: sectioned schedule reviewed. Segments, per-segment definitions, party details and identifiers added (S92 to S101, I15, I16, CC-D9 to CC-D11).
- 2026-09-30: CC-D1 to CC-D5 decided as recommended. CC-D7 decided with a relaxed clean-room rule (an ADR-A-C2 addendum). CC-D10 decided: Undetermined until the graph asserts how a group acts. `wrd:TextPart` decided.
- 2026-09-30: CC-D6 decided (rows in the wording, columns at the instance, long lists as variables). CC-D9 decided: identifiers in Foundation, slice F1 in the Foundation window with NRS N9. Sections proposed as parts of one instrument, no contract-of-contracts (APEX negotiation-thread excerpt reviewed).
- 2026-09-30: CC-D11 decided: sections as parts of one instrument. The sectioned schedule's names, numbers and addresses anonymised in the sketch.
