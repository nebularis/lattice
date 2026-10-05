<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Computable contract substrate - Status

**Unit ID:** `computable-contract-substrate`
**Status:** 🔨 In progress. Gate A passed. Tranche B and C briefed (C3, C10)
**Last updated:** 2026-10-04
**Plan:** [computable-contract-substrate.md](../plans/computable-contract-substrate.md)
**Sketches:** [computable-contract-substrate.md](../sketches/computable-contract-substrate.md),
[contract-amounts.md](../sketches/contract-amounts.md)
**ADRs:** A-104, A-106, A-112, A-113, none drafted
**Machine:** R

## Current position

Gate A passed on 2026-10-01. Tranches B and C are merged to `main` and tagged: Wording 0.3.0,
Behaviour 0.10.0 (shapes 0.4.0) with nested states and history, the import guard in `mise run
check`. Tranche D begins with C6, briefed. From C5 on, the agent builds and verifies, and the human
commits by hand.

**Next action, for the human:** review and commit the C7b model on `ccs/c7b-terms-in-time` (Validation
Pack handoff, phase 2), merge it into `main`, then create the release tags on the merged commit.

🔴 RELEASE TAGS REQUIRED after the merge (21): `quantification-v0.7.0`, `quantification-shapes-v0.2.0`,
`party-v0.7.0`, `party-vocab-v0.7.0`, `eligibility-v0.9.0`, `eligibility-vocab-v0.10.0`,
`wording-v0.5.0`, `wording-vocab-v0.5.0`, `behaviour-v0.12.0`, `behaviour-runtime-v0.12.0`,
`behaviour-vocab-v0.12.0`, `surface-v0.7.0`, `surface-vocab-v0.7.0`, `instrument-v0.11.0`,
`instrument-shapes-v0.4.0`, `instrument-vocab-v0.11.0`, `applied-capacity-execution-v0.12.0`,
`insurance-common-v0.3.0`, `insurance-common-vocab-v0.3.0`, `insurance-peril-v0.3.0`,
`insurance-peril-vocab-v0.3.0`.

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
| C11a | nested states, history, concurrent regimes | C | merged, tagged | |
| F1 | external and natural keys (ADR-A114) | Foundation, now | merged, tagged | |
| C6 | instrument, terms, the five relations, parties, content | D | merged, tagged | |
| C7b | terms in time | D | model built and verified on `ccs/c7b-terms-in-time`, not committed | the human's commit, merge and tags |
| C7c | what terms are, and who they bind (split from C7b) | D | waiting, to be briefed | C7b |
| C8, C9, C8a | Instrument rewrite, template library | D | waiting | C8 after C7a and C7b |
| C7a | regimes and gating, split from C7 | D | merged to `main` (`c6e5853`) and tagged | |
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
- 2026-10-02: C11a merged to `main` (`a236207`) and tagged by the human. C6 briefed with its Validation Pack: four examples first, Instrument 0.8.0, four questions (ownership in C6, identifiers to F1, party details, the party union's name).
- 2026-10-02: C6-Q1 (ownership's core in C6), C6-Q3 and C6-Q4 answered. C6-Q2 opened the question of taking F1 now: no AIR branch has work in flight, so Foundation has a quiet window.
- 2026-10-03: Keys designed with the human: `externalKey` locates, `naturalKey` identifies, the word "identifier" avoided beside "identity". Two mixins, `fnd:MergedOnNaturalKey` with `owl:hasKey` and Persistence's optional `dal:PersistenceKeyed` without, over a common `fnd:NaturallyKeyed`. ADR-A114 "External and natural keys" drafted, Proposed. F1 briefed to run now, before C6, with a phase 0 impact analysis of Persistence, Surface and the cascade. C6-Q2 answered. AIR-4.1's coordination note revised.
- 2026-10-03: F1 phase 0 analysis written (`keys-impact.md`). No change to Persistence's compiler or to Surface. Persistence needs `persistent-foundation` and one key class per scheme. The cascade is 25 documents, and takes Instrument 0.8.0 from C6. MORK's teaching pack lock regenerates. Gate questions G1 to G3.
- 2026-10-03: F1 gate. G2 (the property chain) and G3 (C6 to C9 shift by one MINOR, Instrument 0.8.0 in the cascade) accepted, plan, ADR-A104 and ADR-A114 updated. G1 revised in answer to the human: a key class per scheme defined by an OWL restriction, replacing `dal:keyClassFor`, with three shapes in `persistent-foundation`. Follow-ups FU-F1a (exact pipeline, `identity-minting`) and FU-F1b (compiler-derived constraint) recorded with owners, risk R10.
- 2026-10-03: G1 confirmed and ADR-A114 accepted. F1's three examples written, their key IRIs minted by the recipes the Persistence example compiles to. F1-Q1 raised. Not committed.
- 2026-10-03: Every Persistence example compiled into `ontology/persistence/execution` (`mise run build:persistence-execution`), F1's included, with a crosswalk in the Persistence README §11.5. `instantiate` fixed to write one directory per target (it overwrote repeated operation names). Technical debt register started (`plans/technical-debt.md`, TD-01 to TD-14). Not committed.
- 2026-10-03: `ontology/persistence/execution` removed from git by the human: it is generated on demand by `mise run build:persistence-execution`, and the README §11.5 says so. The Surface keys example gains a second promotion contract (`fnd:externalKey`), and the Foundation example an external key on the agreement's identity for it to promote. F1-15 added. Not committed.
- 2026-10-03: F1-Q1 answered (b). F1 built: Foundation 0.4.0 with keys and its first shapes, its README again the literate source; `persistent-foundation` 0.1.0 and its shapes; 24 importers re-pinned with release rows, the catalog and the MTP lock; `tools/test_keys.py` 30 tests. All ontology, Persistence, Surface, MORK and MTP checks pass. Deviations in the Validation Pack. Procedure for ontology changes written into `.github/copilot-instructions.md`. TD-15 and TD-16 added. Not committed.
- 2026-10-03: F1 merged to `main` (`76790ad`) and tagged by the human. C6 branch moved to it. C6's four examples written (facility agreement, trial protocol, product warranty, software licence), each conforming to the lower layers' shapes but for one finding, raised as C6-Q5 (a path-only evidence binding). Not committed.
- 2026-10-03: C6 examples reviewed for simplicity (Ponytail) and simplified as decided by the human: relations carry no `ins:boundIn`, `ins:party` stays authored (a beneficiary who is no party shown), `ins:resolvedBy` and group modes move to C7b (C6-Q5 deferred), activities name acts not scopes, placeholders commented, one term with two relations. Plan gains slice C16a (simplification sweep) and a C9 example. Ponytail guardrails added to `.github/copilot-instructions.md`. Not committed.
- 2026-10-03: "Bound" kept as a technical term (a bound variable), SPC's "binder" left alone, both in `.github/copilot-instructions.md`. C6 model built: Instrument 0.9.0, its vocab 0.9.0 and shapes 0.2.0, the README as literate source, `tools/test_instrument.py` 41 tests, all ontology and tool checks passing. Not committed.
- 2026-10-04: C6 squash-merged to `main` (`e931cbf`) and tagged by the human. The rule "merge to `main` before tagging, branch from `main`" added to `.github/copilot-instructions.md`. C7a briefed, before C7b because C7b's arising uses C7a's legal triggers, with its Validation Pack skeleton and four questions: regimes in one tier (C7a-Q1), `ins:activity` on triggers (Q2), arising and ending moved into C7a (Q3), and `ins:pausedIn` (Q4).
- 2026-10-04: C7a-Q1 to Q3 and the new Q5 answered. Regimes are stated once (Q1 (a) with two refinements), with the reasoning as an insurance use-case in the sketch's §7.4.1. `ins:activity` loses its domain (Q2), and the domain and range principle is recorded in `.github/copilot-instructions.md`. Arising and ending move into C7a (Q3). Gates default to the relation's own agreement or occasion, with qualified gates held (Q5, HQ-2). Instruments without wording held as HQ-1. Q4 revised to `ins:tolledIn`, the legal word for a period that stops running.
- 2026-10-04: C7a-Q4 answered: `ins:tolledIn`. All five C7a questions answered.
- 2026-10-04: C7a examples written (licence notice, supply suspension, facility cure period, service dispute) with the ADR-A104 addendum "a regime is stated once". All four conform to the lower layers' shapes. Found while writing: stated regimes must assert Behaviour's types and engine policies themselves, since no binding step does (addendum decision 5).
- 2026-10-04: C7a-R1 decided: the asserted `bhv:` terms stay the baseline, and `owl:hasValue` restrictions with three trigger domains let an OWL 2 RL reasoner supply them. Value shapes use `sh:in` (tested: `sh:hasValue` fails both modes). `owl:AllDifferent` in Behaviour is follow-up FU-C7a-a (TD-17). Addendum decision 5, sketch §7.3, plan and Validation Pack updated.
- 2026-10-04: C7a model built: Instrument 0.10.0 (additive), its vocab 0.10.0 and shapes 0.3.0, generated from the README (new §10 Legal Triggers, §11 Regimes and Gating, §12 Authoring With and Without a Reasoner, four worked examples, 46 diagrams parsed). `tools/test_regimes.py` and `tools/test_instrument.py` pass (105 tests). Found while building: SHACL's `sh:class` follows subclass axioms in the data graph, so the B4 shapes check `rdf:type` directly. The addendum's first draft is corrected on this and on which layer requires a trigger kind. Tolling is checked per state space, not per regime. Not committed.
- 2026-10-04: README review: arising explained in §4.2.4 and regimes in §4.2.13, with 13 more diagrams (59, all rendered). Arising and ending restricted to the four triggers other than an expiry (sketch §5.5), with a test. 106 tests pass. Not committed.
- 2026-10-04: C7a merged to `main` (`c6e5853`) and tagged by the human (`instrument-v0.10.0`, `instrument-shapes-v0.3.0`, `instrument-vocab-v0.10.0`). C7b briefed with its Validation Pack skeleton and seven questions: a split into terms in time (C7b) and what terms are (C7c), whether every obligation falls due, named anchors for due ranges and recurrences, ending by a regime's state with a new trigger on entering a state, survival, and deferring `ins:computedBy`.
- 2026-10-04: C7b questions answered. C7b split from C7c (Q1). An obligation has at most one due range, and reasonable time is not modelled unless the words define it (Q2). Survival as a node (Q6), `ins:computedBy` deferred (Q7). Anchored time and ending designed in a new [terms in time sketch](../sketches/terms-in-time.md), which proposes a Quantification context value (TQ1), windows on powers (TQ3), ending as entering a state with an `ins:OnEntry` trigger (TQ4) and expiry at a date (TQ6). The plan's C8 row corrected: stated and bound meaning moved into C6. C9 takes 0.14.0.
- 2026-10-05: terms in time sketch decided (TQ1 to TQ7). Anchored time goes in Quantification (0.7.0, ADR-A115, with a re-pin cascade). Business day conventions and times of day held as HQ-3. Windows on powers and permissions, ending as entering a state with `ins:OnEntry`, implicit survival of termination consequences, expiry at a date, and pending occasions ending on termination. Quantification's README found not to be its literate source (no header block, one shapes block for three files, graphs equal), to be restored first in C7b.
- 2026-10-05: C7b examples written (trial reporting, lease expiry, licence survival, evergreen services, and a Quantification context value example), with ADR-A115 and the ADR-A104 addendum "terms in time". Quantification's README restored as its literate source, with no graph change. Three examples conform to the lower layers' shapes, and two fail only where TQ4 and TQ6 change the model. The evergreen notice window is a region of each period, since its anchor lies inside the regime. Not committed.
- 2026-10-05: C7b model built. Quantification 0.7.0 (context values, unit-bearing offsets, ADR-A115) from its restored README, re-pinned through 18 importers. Instrument 0.11.0, vocab 0.11.0 and shapes 0.4.0: due ranges, windows, recurrences, ending as entering a state with `ins:OnEntry`, expiry at a time, survival, with README §4.7, §13 and §14 and four worked examples. 85 diagrams render. Found: context roles from several sources cannot all bind to one contract (held design question HQ-4). Not committed.
- 2026-10-05: Quantification README given a guided tour of the layer (§5.1) and diagrams for containment, law prerequisites and its consumers, 20 diagrams in all, at the human's request. No change to its generated files. Not committed.
- 2026-10-05: Quantification README: scales of measure and additivity explained (§5.1.3), operations across two spaces and overlap against containment illustrated (§5.1.9), stale paths, importers and authoring framing corrected, and open question 7 (semi-additive aggregation) recorded. No change to its generated files. Not committed.
- 2026-10-05: ADR-A115 and ADR-A104's addenda of 2026-10-04 (a regime is stated once) and 2026-10-05 (terms in time) accepted by the human, before C7b's merge.
