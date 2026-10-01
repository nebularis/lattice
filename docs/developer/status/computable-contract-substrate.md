<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Computable contract substrate - Status

**Unit ID:** `computable-contract-substrate`
**Status:** 📝 Proposed. Tranche A drafted on `ccs/c0-adrs`, uncommitted, awaiting human review
**Last updated:** 2026-10-01
**Plan:** [computable-contract-substrate.md](../plans/computable-contract-substrate.md)
**Sketches:** [computable-contract-substrate.md](../sketches/computable-contract-substrate.md),
[contract-amounts.md](../sketches/contract-amounts.md)
**ADRs:** A-104, A-106, A-112, A-113, none drafted
**Machine:** R

## Current position

The design is sketched and tested against four instruments and a proposed Lloyd's schedule 
(101 scenarios, S79 merged, and 58 amount constructs). Every decision is taken. Tranche A is drafted
on `ccs/c0-adrs`: ADR-A104, A-106, A-112 and A-113, and addenda to A-01 and A-C2, all `Proposed`.
No ontology document is touched.

**Next action, for the human:** review the uncommitted tranche, settle the three open points at
acceptance (A-104: `ins:Element`, `ins:fulfilledBy`. A-106: engine settings), commit, then Gate A.
**Next action, for the agent, after Gate A:** brief C3 (Wording spec) and C10 (Behaviour split),
which may run side by side.

## Slice board

| # | Slice | Tranche | State | Blocked on |
|---|---|---|---|---|
| C0 | A-112, A-113, A-01 and ADR-A-C2 addenda | A | drafted, verified | human review |
| C1 | A-104 | A | drafted, verified | human review, two open points |
| C2 | A-106 | A | drafted, verified | human review, one open point |
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
- 2026-10-01: Logical English alignment sketched (unplanned, CCS sketch §14). C0 briefed with its Validation Pack skeleton, raising C0-Q1 (A-01 addendum or supersession), C0-Q2 (measuring CC-D7) and C0-Q3 (marking a breaking 0.x change).
- 2026-10-01: C0-Q1 to C0-Q3 accepted as recommended. Tranche A drafted on `ccs/c0-adrs` in one run: A-112, A-113, the A-01 and A-C2 addenda (C0), A-104 (C1), A-106 (C2), with C1 and C2 briefs and all three Validation Packs verified. Not committed, pending review.
