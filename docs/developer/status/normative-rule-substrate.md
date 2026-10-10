<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Normative rule substrate - Status

**Unit ID:** `normative-rule-substrate`
**Status:** 📝 Proposed. Nothing implemented in this unit. N4, N5 and the Behaviour part of N8 are
CCS's. D1, D4 and D5 open, and the unit's remaining scope is open (NQ-1 to NQ-4)
**Last updated:** 2026-10-10
**Trigger:** request, 2026-09-29, following the LegalRuleML mapping analysis
**Plan:** [normative-rule-substrate.md](../plans/normative-rule-substrate.md)
**Sketches:** [legalruleml-mapping.md](../sketches/legalruleml-mapping.md),
[rule-layers.md](../sketches/rule-layers.md),
[rule-layers-cross-check.md](../sketches/rule-layers-cross-check.md)
**ADRs:** A-104 to A-111 reserved. A-104 and A-106 accepted in CCS (2026-10-01). A-105 moved to CCS
HQ-6a (2026-10-10). A-107 to A-111 not drafted
**Machine:** single. This unit does not use the applied-insurance epic's two-machine model

---

## Current position

The analysis is complete and the plan is written. This unit has drafted no ADR, touched no ontology
document and started no slice. Its first blocker, D2, was answered on 2026-09-30.

**2026-09-30:** D2 and D3 are answered, and slice N4 moves to the new
[computable-contract-substrate](../plans/computable-contract-substrate.md) unit (CCS), which also
takes N8's Behaviour work and revises N2, N5 and N6 (the plan's slice notes).

**2026-10-10:** N5 moved to CCS as its held question HQ-6 (HQ6-Q1), split into HQ-6a
before CCS C9b3 and HQ-6b before CCS C12 (HQ6-Q2, the plan's N5 note). D7 is answered with it. This
unit now holds N1, N2, N3, N6's and N8's remainders, N7, N9 and N10 to N13, none started. CCS waits
on N1 (C13, C13a) and N3 waits on CCS C13a.

**Next action, for the maintainer:** answer NQ-1 to NQ-4 below, and D1.

**Next action, once NQ-1 and NQ-2 are answered:** brief the first slice they leave
this unit, which under the leanings is N1 (in CCS) or N2.

## Dependency position against the applied-insurance epic

Measured on 2026-09-29 by enumerating external importers per layer across `ontology/`, and by
reading the remaining slice definitions in the epic's Phase 2, 3, 4 and substrate plans. Full
analysis in the plan's §4.

**Verdict: most of this unit runs in parallel with the epic. One slice must be serialised.**

| Position | Slices | Constraint |
|---|---|---|
| Parallel-safe now | N2, N4 (CCS), N6, N8 | Instrument and Behaviour have 1 external importer each and no applied module. The epic does not touch Instrument until Phase 5, which decision D2 defers |
| Sequenced behind AIR-3.3 | N1, N3, N7 | Share `tools/mork_compilers/` with AIR-3.3 |
| Coordinate with substrate S2 | N5 (CCS HQ-6 since 2026-10-10, see NQ-4) | Both touch Eligibility |
| **Serialised, must wait** | **N9** | Foundation has 14 external importers including the two peril files AIR-2.2 to AIR-2.7 are authoring region by region |

**Ordering answer: the rule work goes first, specifically slice N4.** Not because rules outrank
insurance, but because Instrument is currently the cheapest layer in the repository to change
(one re-pin, no applied module), because the cross-check requires R1 to land before
applied-insurance Phase 5 starts, and because Phase 5's deferral under epic decision D2 is exactly
the window in which Instrument can change undisturbed. That window closes when Phase 5 is
un-deferred.

**The one constraint in the other direction:** N9 must not start until Phase 2 completes.

**Re-checked 2026-10-10.** The applied-insurance epic is still in round 3. AIR-3.3 is unmerged,
Phase 2 is incomplete and S2 and S7 have not started, so N1's, N9's and N10's constraints stand.
Instrument's position has changed, since after CCS C10 nothing outside Instrument imports it.

## Slice board

| # | Slice | Tranche | State | Blocked on |
|---|---|---|---|---|
| N2 | Declare the importable rule-body fragment (A-109), revised for stratified state reads (ADR-A104 decision 15) | A | waiting | D1, NQ-2 |
| N4 | Deontic extension of Instrument (A-104, R1) | B | moved to CCS 2026-09-30, delivered | CCS C1, C6 to C9 |
| N1 | Condition composition acyclicity (R4). CCS C13 and C13a wait on it | A | waiting | AIR-3.3 merge, NQ-2 |
| N6 | Scheduled triggers as positioned stimuli (R3), built with CCS C12 | B | waiting | CCS C12, NQ-3 |
| N3 | Self-contradiction design-time check | B | waiting | CCS C13a, NQ-2 |
| N5 | Closure declarations (A-105, R2) | C | moved to CCS 2026-10-10 | CCS HQ-6a before C9b3, HQ-6b before C12 |
| N7 | Measure the OASIS conformance corpus | C | waiting | CCS C9, N1 |
| N8 | Breach-chain checks (Behaviour records and evaluator moved to CCS C11, C12) | B | waiting | CCS HQ-6a, C12, C13, NQ-3 |
| N9 | Multi-axis temporal scope (A-108) | D | waiting | **D4, Phase 2 complete** |
| N10 | Norm priority and defeasibility (A-107) | E | deferred | D5 |
| N11 | Controlled-English rendering (R5) | E | deferred | ingestion vision Phase 2 |
| N12 | LegalRuleML and ODRL interchange (A-111) | E | conditional | a trigger from the plan's §2 |
| N13 | US Code §504 acceptance milestone | E | deferred | all of the above |

## Decisions owed

| # | Decision | State |
|---|---|---|
| D1 | Unit rather than epic, with tranche gates | open |
| D2 | Is `ins:Obligation` deontic or structural? | answered 2026-09-30: deontic (CCS sketch) |
| D3 | How far should ODRL alignment go? | answered 2026-09-30: align where free, map through MORK otherwise |
| D4 | Does N9 wait for Phase 2, or does the epic accept a freeze? | open |
| D5 | Does priority wait for Phase 5? | open |
| D6 | Is substrate S2 authored together with N5? | overtaken 2026-10-10: N5 is CCS HQ-6. Restated as NQ-4 |
| D7 | Refuse an unlicensed absence-dependent check, or compile it to `Undetermined`? | answered 2026-10-10: refuse, in CCS HQ-6a (HQ6-Q2), consistent with CCS C9b0-Q2 |

D5 has new evidence: CCS C7c declared `ins:prevailsOver` between definitions only (D13, 2026-10-06),
the planned C9c widens it to an incorporated document, and terms are left to N10. D1's pattern, a unit in
tranches with validation gates, is the one CCS runs under (CCS plan header).

## Open questions from the CCS alignment (2026-10-10)

Raised for the maintainer. None is decided.

| # | Question | Leaning |
|---|---|---|
| NQ-1 | **Does NRS still have a reason to exist as a unit?** With N4, N5 and N8's Behaviour part in CCS, what is left is either on CCS's path (N1, N2, N3, N6's and N8's remainders) or independent of contracts (N7, N9, N10 to N13). Options: (a) keep NRS as the home of the independent slices, (b) close NRS and move every remaining slice to CCS or to a later unit, (c) keep it unchanged | (a). N9, N10 and N12 concern norms beyond contracts and have their own gates (Phase 2, S7, a trigger), which CCS should not carry. Close NRS once those are placed |
| NQ-2 | **Do N1, N2 and N3 move to CCS?** CCS C13 and C13a wait on N1. ADR-A104 decision 15 already states N2's revision, and C13 builds the stratified state reading it governs. N3 follows C13a and uses its task | move N1 and N2 to CCS, as N4, N5 and N8 did, since CCS waits on both. N3 may follow, or stay as a small slice after C13a |
| NQ-3 | **What remains of N6 and N8?** C12 builds positioned stimuli for scheduled triggers (N6). For N8, `ins:OnBreach` names only an obligation (`ins:ofObligation`), and law I6's acyclicity is checked with C13 | N6 and N8 are absorbed by CCS C12 and C13. Confirm with each brief, and retire both here when they merge |
| NQ-4 | **Does substrate S2 still pair with N5 (D6)?** The AIR plan (§3b, substrate plan row S2) says S2 is authored with NRS N5. HQ-6a and HQ-6b as split do not name an Eligibility change, while CCS C9b3 is Eligibility's own slice with an ADR | pair S2 with C9b3 instead, or release it back to the AIR substrate track. Either needs the AIR plan's row updated |

## Key findings from the analysis

Findings of 2026-09-29, kept as the record. Instrument's importer count changed with CCS C10 (above),
and the N8 blocking finding now applies to CCS HQ-6a.

- **Instrument is the safest layer in the repository to change.** One external importer
  (`behaviour/spec/behaviour.ttl`), no applied module, and no epic slice touches it until deferred
  Phase 5. The unit's largest deliverable is also its least disruptive.
- **Foundation is the most dangerous, and the danger is at its peak now.** Fourteen external
  importers, five of them applied, two of which (`peril/spec/peril.ttl` and
  `peril/vocab/peril-vocab.ttl`) are being authored region by region across the whole of Phase 2.
- **Eligibility profiles nest.** `elg:AdmissionProfile ⊑ elg:Condition` per ADR-A03, so nested
  bodies are expressible and the gap is narrower than first thought: composition is unchecked for
  cycles, which is the cross-check's R4.
- **Closure declarations are a prerequisite, not a parallel concern.** Without one, a violation
  can never be derived and every compensation chain is inert. Slice N8 is blocked on N5 for this
  reason, not for convenience.
- **ADR-A103 and closure declarations compose rather than conflict.** Set readings say how to read
  several values. A closure says whether no values may mean false. Different questions.
- **Norm priority (N10) is adjacent to substrate S7.** Both are precedence models on
  Foundation-adjacent data. Designed separately, the repository acquires two precedence
  vocabularies that do not compose.

## Is this unit complete?

No. Nothing in this unit has started. The plan is proposed, D1, D4 and D5 are open, D6 is restated as
NQ-4, and NQ-1 to NQ-4 decide its remaining scope.

## History

- 2026-09-29: LegalRuleML mapping sketch written, then reconciled against the pre-existing
  `rule-layers` and `rule-layers-cross-check` sketches. Three conclusions in the mapping sketch
  were corrected in that reconciliation: profiles do nest, negation as failure gains a licence
  rather than a refusal, and closure declarations are a prerequisite for the deontic work.
- 2026-09-29: plan and this status record written. Dependency check against the applied-insurance
  epic measured rather than assumed, by enumerating per-layer external importers.
- 2026-09-30: D2 and D3 answered. N4 moved to CCS, N2, N5, N6 and N8 revised.
- 2026-10-10: aligned with CCS. We moved N5 to CCS as HQ-6 (HQ6-Q1) and split it into HQ-6a
  before C9b3 and HQ-6b before C12 (HQ6-Q2), answering D7 (refuse). Plan and record updated: ADR states
  (A-104 and A-106 accepted 2026-10-01, A-105 moved), F1's separate Foundation window, N1 on CCS's
  path, Eligibility's README its source again, `ins:prevailsOver` evidence for D5, the retired
  validation log. D6 overtaken. NQ-1 to NQ-4 raised for the maintainer
