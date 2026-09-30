<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Normative rule substrate - Status

**Unit ID:** `normative-rule-substrate`
**Status:** 📝 Proposed. Nothing implemented. Blocked on the seven decisions in the plan's §9
**Last updated:** 2026-09-30
**Trigger:** human request, 2026-09-29, following the LegalRuleML mapping analysis
**Plan:** [normative-rule-substrate.md](../plans/normative-rule-substrate.md)
**Sketches:** [legalruleml-mapping.md](../sketches/legalruleml-mapping.md),
[rule-layers.md](../sketches/rule-layers.md),
[rule-layers-cross-check.md](../sketches/rule-layers-cross-check.md)
**ADRs:** A-104 to A-111, none drafted
**Machine:** single. This unit does not use the applied-insurance epic's two-machine model

---

## Current position

The analysis is complete and the plan is written. No ADR has been drafted, no ontology document
has been touched, and no slice has started.

The unit is waiting on decision **D2** above all others: whether `ins:Obligation` is a deontic
operator or a structural document element. ADR-A07b chose Instrument's minimal shape deliberately
but did not decide this question, and slice N4 cannot be authored without the answer.

**2026-09-30:** D2 and D3 are answered, and slice N4 moves to the new
[computable-contract-substrate](../plans/computable-contract-substrate.md) unit (CCS), which also
takes N8's Behaviour work and revises N2, N5 and N6 (the plan's slice notes).

**Next action, for the human:** take D1, and CCS's CC-D1 to CC-D8.

**Next action, for the agent, once D1 to D3 are taken:** draft ADR-A109 (slice N2, the importable
rule-body fragment), which needs no ontology change and is independent of everything else.

## Dependency position against the applied-insurance epic

Measured on 2026-09-29 by enumerating external importers per layer across `ontology/`, and by
reading the remaining slice definitions in the epic's Phase 2, 3, 4 and substrate plans. Full
analysis in the plan's §4.

**Verdict: most of this unit runs in parallel with the epic. One slice must be serialised.**

| Position | Slices | Constraint |
|---|---|---|
| Parallel-safe now | N2, N4, N6, N8 | Instrument and Behaviour have 1 external importer each and no applied module. The epic does not touch Instrument until Phase 5, which decision D2 defers |
| Sequenced behind AIR-3.3 | N1, N3, N7 | Share `tools/mork_compilers/` with AIR-3.3 |
| Coordinate with substrate S2 | N5 | Both touch Eligibility |
| **Serialised, must wait** | **N9** | Foundation has 14 external importers including the two peril files AIR-2.2 to AIR-2.7 are authoring region by region |

**Ordering answer: the rule work goes first, specifically slice N4.** Not because rules outrank
insurance, but because Instrument is currently the cheapest layer in the repository to change
(one re-pin, no applied module), because the cross-check requires R1 to land before
applied-insurance Phase 5 starts, and because Phase 5's deferral under epic decision D2 is exactly
the window in which Instrument can change undisturbed. That window closes when Phase 5 is
un-deferred.

**The one constraint in the other direction:** N9 must not start until Phase 2 completes.

## Slice board

| # | Slice | Tranche | State | Blocked on |
|---|---|---|---|---|
| N2 | Declare the importable rule-body fragment (A-109), revised for stratified state reads | A | waiting | D1 |
| N4 | Deontic extension of Instrument (A-104, R1) | B | moved to CCS | CCS C1, C6 to C9 |
| N1 | Condition composition acyclicity (R4) | A | waiting | AIR-3.3 merge |
| N6 | Scheduled triggers as positioned stimuli (R3), built with CCS C12 | B | waiting | CCS C11 |
| N3 | Self-contradiction design-time check | B | waiting | CCS C9 |
| N5 | Closure declarations (A-105, R2) | C | waiting | D6, D7, substrate S2 |
| N7 | Measure the OASIS conformance corpus | C | waiting | CCS C9, N1 |
| N8 | Breach-chain checks (Behaviour records and wiring moved to CCS C11, C12) | B | waiting | N5, CCS C12 |
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
| D6 | Is substrate S2 authored together with N5? | open |
| D7 | Refuse an unlicensed absence-dependent check, or compile it to `Undetermined`? | open |

## Key findings from the analysis

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

No. Nothing has started. The plan is proposed and the decisions in its §9 are open.

## History

- 2026-09-29: LegalRuleML mapping sketch written, then reconciled against the pre-existing
  `rule-layers` and `rule-layers-cross-check` sketches. Three conclusions in the mapping sketch
  were corrected in that reconciliation: profiles do nest, negation as failure gains a licence
  rather than a refusal, and closure declarations are a prerequisite for the deontic work.
- 2026-09-29: plan and this status record written. Dependency check against the applied-insurance
  epic measured rather than assumed, by enumerating per-layer external importers.
- 2026-09-30: D2 and D3 answered. N4 moved to CCS, N2, N5, N6 and N8 revised.
