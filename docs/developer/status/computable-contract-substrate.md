<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Computable contract substrate - Status

**Unit ID:** `computable-contract-substrate`
**Status:** 📝 Proposed. CC-D1 to CC-D11 decided. Sketches and plan awaiting human review
**Last updated:** 2026-10-01
**Plan:** [computable-contract-substrate.md](../plans/computable-contract-substrate.md)
**Sketches:** [computable-contract-substrate.md](../sketches/computable-contract-substrate.md),
[contract-amounts.md](../sketches/contract-amounts.md)
**ADRs:** A-104, A-106, A-112, A-113, none drafted
**Machine:** R

## Current position

The design is sketched and tested against four instruments and a proposed Lloyd's schedule 
(101 scenarios, S79 merged, and 58 amount constructs). Every decision is taken. No ADR is drafted
and no ontology document is touched.

**Next action, for the human:** review the CC-D8 write-up (sketch §6.3, §7, §5.11, contract-amounts
§1.7) and the reordered plan, uncommitted.
**Next action, for the agent, after the review:** brief and draft C0 (A-112, A-113, the ADR-A-C2
addendum).

## Slice board

| # | Slice | Tranche | State | Blocked on |
|---|---|---|---|---|
| C0 | A-112, A-113, ADR-A-C2 addendum | A | waiting | human review of the write-up |
| C1 | A-104 | A | waiting | human review of the write-up |
| C2 | A-106 | A | waiting | human review of the write-up |
| C3 to C5 | Wording layer | B | waiting | Gate A |
| C10, C10a, C11, C11a | Behaviour below Instrument, import guard, records, nested states | C | waiting | Gate A |
| F1 | Foundation identifiers | Foundation window | waiting | AIR Phase 2 complete, with NRS N9 |
| C6 to C9, C8a | Instrument rewrite, template library | D | waiting | C5, C10 |
| C12, C13 | runtime evaluator, relation plans | E | waiting | C9, C11, C11a, AIR-3.3, NRS N1 |
| C14 to C17 | examples, docs, handoff | F | waiting | C8a, C9, C12 |

## History

- 2026-09-29 to 30: D2 walkthrough, first Instrument redesign, tests against the AIG package policy,
  the IUA broker binding authority and the Lloyd's CBAA collateral, and cross-reference with Open
  CBAA's `wim`, `stm`, `agr` and `rsk` modules and design documents.
- 2026-09-30: sketches, plan and this record written. NRS, AIR and platform plans updated.
- 2026-09-30: sectioned schedule reviewed. Segments, per-segment definitions, party details and identifiers added (S92 to S101, I15, I16, CC-D9 to CC-D11).
- 2026-09-30: CC-D1 to CC-D5 decided as recommended. CC-D7 decided with a relaxed clean-room rule (an ADR-A-C2 addendum). CC-D10 decided: Undetermined until the graph asserts how a group acts. `wrd:TextPart` decided.
- 2026-09-30: CC-D6 decided (rows in the wording, columns at the instance, long lists as variables). CC-D9 decided: identifiers in Foundation, slice F1 in the Foundation window with NRS N9. Sections proposed as parts of one instrument, no contract-of-contracts (APEX negotiation-thread excerpt reviewed).
- 2026-09-30: CC-D11 decided: sections as parts of one instrument. The sectioned schedule's names, numbers and addresses anonymised in the sketch.
- 2026-10-01: CC-D8 decided: Behaviour below Instrument, split into configuration and runtime, regimes (synonym dispensation) and legal triggers specialising Behaviour, DP6 restated as B8, evidence rule B6, import guard B7. Sketch §6.3, §7 and §5.11 written with diagrams. Bases catalogued in contract-amounts §1.7 (A51 to A58). Plan reordered: tranche C (Behaviour) before tranche D (Instrument), new slices C8a, C10a, C11a. NRS, AIR, phase-3 and phase-5 notes updated.
