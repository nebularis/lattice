<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Computable contract substrate - Status

**Unit ID:** `computable-contract-substrate`
**Status:** 🔨 In progress. Gate A passed. Tranche B and C briefed (C3, C10)
**Last updated:** 2026-10-02
**Plan:** [computable-contract-substrate.md](../plans/computable-contract-substrate.md)
**Sketches:** [computable-contract-substrate.md](../sketches/computable-contract-substrate.md),
[contract-amounts.md](../sketches/contract-amounts.md)
**ADRs:** A-104, A-106, A-112, A-113, none drafted
**Machine:** R

## Current position

Gate A passed on 2026-10-01. C3, C4, C5, C10, C10a and C11 are merged to `main` and tagged:
Wording 0.3.0, Behaviour 0.9.0, shapes 0.3.0, the import guard in `mise run check`. Tranche D is
unblocked. C11a phase 1 is drafted. From C5 on, the agent builds and verifies, and the human
commits by hand.

**Next action, for the human:** review and commit C11a phase 2's model, then merge and tag
`behaviour-v0.10.0`, `behaviour-runtime-v0.10.0`, `behaviour-vocab-v0.10.0`,
`behaviour-shapes-v0.4.0` and `applied-capacity-execution-v0.10.0`. **Then:** tranche D (C6, then
C7a and C7b).

## Slice board

| # | Slice | Tranche | State | Blocked on |
|---|---|---|---|---|
| C0 | A-112, A-113, A-01 and ADR-A-C2 addenda | A | accepted | |
| C1 | A-104 | A | accepted | |
| C2 | A-106 | A | accepted | |
| C3 | Wording spec, vocab and shapes | B | merged, tagged | |
| C4 | Wording tables, assembly, variable values | B | merged, tagged | |
| C5 | Wording amendments, law shapes, how-to | B | merged, tagged | |
| C10 | Behaviour split and layer flip | C | merged, tagged | |
| C10a | import guard | C | merged | |
| C11 | runtime records, occasions, initial states | C | merged, tagged | |
| C11a | nested states, history, concurrent regimes | C | phase 2 built and verified, awaiting the human's commit | branch |
| F1 | Foundation identifiers | Foundation window | waiting | AIR Phase 2 complete, with NRS N9 |
| C6, C7b, C8, C9, C8a | Instrument rewrite, template library | D | waiting | C5 and C10 done. C8 after C7a and C7b |
| C7a | regimes and gating, split from C7 | D | waiting | C6, C11a phase 2 |
| C12, C13 | runtime evaluator, relation plans | E | waiting | C9, C11, C11a, AIR-3.3, NRS N1 |
| C13a | design-time joint satisfiability: slot conditions by reasoner, the task NRS N3 reuses (deferred from C5) | E | waiting | C5, NRS N1 |
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
- 2026-10-01: C4, C10a and C11 rebased into one chain, merged to `main` (squashed, `c9bfbea`) and tagged. C5 and C11a briefed, with Validation Pack skeletons. From here the human commits by hand.
- 2026-10-02: C5 decided: SHACL-SPARQL slot checks for intervals now, the full reasoner check deferred to a new slice C13a (tranche E, before NRS N3, risk R9). Amendment operations closed, recorded with PROV, library elements amended in an instance as bespoke revisions, which a draft library release may adopt upstream as a new version or a variant.
- 2026-10-02: C5 examples written and committed by the human (`9515254`), with rows and columns. The CC-D6 amendment followed in the working tree. Agreed with the human: `wrd:placedUnder` for an instance's new elements, W5 accepts a revision, W1 reworded. CC-D6 amended: tables in fields and entries with `wrd:fieldsAs`, replacing rows and columns, folded into wording 0.3.0. Sketch §4.3, A-112 and the C5 brief updated.
- 2026-10-02: C5 model built: wording, wording-vocab and wording-shapes 0.3.0 (breaking), laws W1 to W6 and the slot range check in a new `shapes/constraints.ttl`, amendments, tables in fields and entries. `test_wording.py` 94 passed. Deviations in the Validation Pack. Not committed.
- 2026-10-02: C5 merged to `main` (`0def0e9`) and tagged 0.3.0 by the human.
- 2026-10-02: C11a phase 1 drafted: the nested states sketch (SCXML as reference, regions by `bhv:regionOf`, history per transition, occupancies per level, both forms of concurrency, the macrostep, occasions by `bhv:perOccasionOf`, six worked cases, B5 restated, B9 to B11) and the ADR-A106 addendum, Proposed. Four questions raised. Not committed.
- 2026-10-02: Garden leave reworked as two regimes, giving the rule for when to nest (sketch §3.1). C11a-Q1, Q2 and Q4 answered as recommended. C11a-Q3 under discussion. Phase 2 to give the Behaviour README a section of worked state machines with diagrams and Turtle.
- 2026-10-02: C7 split into C7a (regimes and gating, after C11a phase 2) and C7b (terms in time and constitutive terms). Instrument versions after C7 shift by one MINOR. Internal transitions decided: a self-transition is internal unless declared External. C11a-Q3 (b or c) pending a discussion of contract amounts.
- 2026-10-02: C11a-Q3 answered: `AllMatches` over internal transitions, sequential environment only. The unplanned [evaluation context](../sketches/evaluation-context.md) sketch written, linked from the CCS and AIR plans: ledger, combinators, sequential and parallel environments, stratification and a stratified Datalog form.
- 2026-10-02: C11a gate passed (addendum accepted, committed `c40df81`). Phase 2 briefed: eight examples first, then configuration, runtime and vocab 0.10.0, shapes 0.4.0, the README's worked state machines.
- 2026-10-02: C11a phase 2's eight examples written: covenant default, run-off, standstill, garden leave, force majeure, occasion refinement, disputed occasion, ordered draws. All conform to the 0.3.0 shapes and are consistent. The brief gains B1 over the occasion tree and B5 for the evaluator's reinstatement.
- 2026-10-02: C11a phase 2 built: Behaviour 0.10.0 with regions, history, internal transitions, guards on states, `bhv:Live`, shapes 0.4.0 with B5, B9, B11 and the `AllMatches` rules, the README's worked state machines. All checks pass. Not committed.
