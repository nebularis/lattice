<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Computable contract substrate - Status

**Unit ID:** `computable-contract-substrate`
**Status:** 🔨 In progress. Gate A passed. Tranche B and C briefed (C3, C10)
**Last updated:** 2026-10-01
**Plan:** [computable-contract-substrate.md](../plans/computable-contract-substrate.md)
**Sketches:** [computable-contract-substrate.md](../sketches/computable-contract-substrate.md),
[contract-amounts.md](../sketches/contract-amounts.md)
**ADRs:** A-104, A-106, A-112, A-113, none drafted
**Machine:** R

## Current position

Gate A passed on 2026-10-01. C3 (Wording 0.1.0) and C10 (Behaviour below Instrument, 0.8.0) are
merged and tagged. C4, C10a and C11 are briefed, with Validation Pack skeletons. They share no file
but `mise.toml`'s test lists and this record, so they may run side by side.

**Decided 2026-10-01:** C4-Q1 to C4-Q3, C10a-Q1, C10a-Q2, C11-Q1 (a fixed occasion core refined by
sub-states) and C11-Q2 (declared initial states). CC-D3 confirmed: the LMA WIM profile is in
LATTICE. The Open CBAA migration notes are current in both repositories.

**Next action, for the human:** commit the briefs to `main` (and Open CBAA's plan in `open-dare`),
then create `ccs/c4-wording-assembly`, `ccs/c10a-import-guard` and `ccs/c11-runtime-records`.
**Next action, for the agent:** build the three slices on their branches. C5 and C11a briefs follow.

## Slice board

| # | Slice | Tranche | State | Blocked on |
|---|---|---|---|---|
| C0 | A-112, A-113, A-01 and ADR-A-C2 addenda | A | accepted | |
| C1 | A-104 | A | accepted | |
| C2 | A-106 | A | accepted | |
| C3 | Wording spec, vocab and shapes | B | merged, tagged | |
| C4 | Wording tables, assembly, variable values | B | built, verified on `ccs/c4-wording-assembly` | human review, tags |
| C5 | Wording amendments, law shapes, how-to | B | waiting | C4 |
| C10 | Behaviour split and layer flip | C | merged, tagged | |
| C10a | import guard | C | built, verified on `ccs/c10a-import-guard` | human review |
| C11 | runtime records, occasions, initial states | C | built, verified on `ccs/c11-runtime-records` | human review, tags |
| C11a | nested states, history, concurrent regimes | C | waiting | C11 |
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
- 2026-10-01: CC-D12 decided: meaning belongs to its text (stated meaning owned by an element version, bound meaning by an instrument version, only wordings, elements and instruments versioned). Sketch §5.1, §5.2, §5.8, §5.9, laws I2, I13, I17, I18 and A-104 decisions 1, 2 and 13 rewritten. A-106 gains the identity rule for runtime state. `ins:Element` retired, `ins:fulfilledBy` replaced, engine settings stay explicit (A-09, A-10 stand).
- 2026-10-01: Gate A passed. The four ADRs and two addenda accepted, A-07b superseded, A-11 amended. C3 and C10 briefed with Validation Pack skeletons. The plan's C3 row gains the vocab and the README's start, C4 takes vocab 0.2.0.
- 2026-10-01: C3-Q1 (a baseline element type scheme covering every type Wording's docs and examples use), C3-Q2 (`applicableTo` in the LMA WIM profile), C10-Q1 and C10-Q2 decided. Tranche A merged to `main`, branches `ccs/c3-wording-spec` and `ccs/c10-behaviour-split` created.
- 2026-10-01: C3 built and verified on `ccs/c3-wording-spec`: Wording 0.1.0 and its vocab 0.1.0, two examples, `tools/test_wording.py` (18 tests, reasoner rows run), the versioning policy's major-version-zero rule, and the layer order in the root README and ontology architecture.
- 2026-10-01: C3 revised in review: unions named once, each property's subject and value in its comment, and SHACL Core shapes (`wording-shapes` 0.1.0) so verification needs no reasoner. 34 Wording tests.
- 2026-10-01: C10 built and verified on `ccs/c10-behaviour-split`: Behaviour below Instrument, configuration and runtime 0.8.0, `bhv:targets`, vocab, shapes, projection and capacity bumps, 21 tests. C3 merged and tagged.
- 2026-10-01: C10 merged and tagged, with neutral fixture targets and a README for `applied/capacity`. C4, C10a and C11 briefed with Validation Pack skeletons.
- 2026-10-01: C4, C10a and C11 questions decided. C11-Q1 became a fixed occasion core refined by sub-states (C11a), and C11-Q2 declared initial states. CC-D3 confirmed. Open CBAA migration notes brought up to date in this plan's §7, the sketch §12.2, AIR-5.9 and Open CBAA's plan.
- 2026-10-01: C4 built and verified on `ccs/c4-wording-assembly`: Wording, its vocab and shapes at 0.2.0, the facility form example, 15 tests.
- 2026-10-01: C10a built and verified on `ccs/c10a-import-guard`: `check:import-guard`, part of `mise run check`, finds no violation today.
- 2026-10-01: C11 built and verified on `ccs/c11-runtime-records`: occasions, six record kinds, declared initial states, B6, B1 and I11 as shapes, 15 tests.
