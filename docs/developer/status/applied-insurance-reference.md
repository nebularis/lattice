<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Applied Insurance Reference - Status

**Unit ID:** `applied-insurance-reference` (epic)
**Status:** Phase 0 complete. AIR-0.1 signed off in `LOG.md` and on `main` (`3377a71`). Phase 1
and Phase 3 branches may be created (lanes §4, round 0).
**Last updated:** 2026-09-26
**Trigger:** human request, 2026-09-26
**Plan:** [applied-insurance-reference.md](../plans/applied-insurance-reference.md)
**Review request:** [applied-insurance-reference-review.md](../review/applied-insurance-reference-review.md)

## Current position

The five sketches were moved into `docs/developer/sketches/`. The epic and its phase
plans were written on 2026-09-26. In the same session `prl:canTrigger` was corrected in the
peril vocabulary and whitepaper sketches: it is now a sub-property of `skos:semanticRelation`,
because `skos:related` is symmetric, and `prl:overlaps` is declared symmetric itself.

Later on 2026-09-26 the human decided (epic §5.1): drop the legacy contract module (D1), defer a
new contract module until Phases 1 to 4 are wired into Open CBAA (D2), keep Open CBAA material in
the sketches as motivation (D3), and point Open CBAA's documents at LATTICE instead of local
copies (D4, done). The human then agreed the applied layout (epic §5.2, D5 to D10): three levels of
sharing, `capacity` and new `classification` and `scheme-profile` modules as cross-domain applied
modules, `insurance/common/` for insurance-only shared contracts, role types and the loss event,
and the peril vocabulary as the `insurance/peril/` sub-domain. The sketches' paths were updated
to match.

Later on 2026-09-26 the slices were analysed for parallel work. Seven lanes and a strict
merge order are in [lanes and merge order](../plans/applied-insurance-reference-lanes.md). Two
dependency errors were corrected: the characteristic schemes now precede the cause families
(renumbered AIR-2.2), and AIR-3.1 to AIR-3.3 no longer wait for Phase 2.

AIR-0.1 was carried out autonomously on 2026-09-26: ADRs A-98, A-99, A-100 and A-102 drafted as
Proposed, catalogue rows added with A-101 reserved, a citation note added to each sketch naming
Open CBAA's documents, and the sketches' prefixes aligned (`brg:` to `spf:`, `common:` to `icm:`).
The [validation pack](../validation/applied-insurance-reference-0.1.md) command was run by the
agent and printed nothing. Nothing is committed.

The human then accepted A-98, A-99 and A-102, and challenged A-100's applied placement. A-100
was rewritten: structural capabilities, profiles and crosswalks belong to Vocabulary, and the gate
that reads them to Eligibility, closing a defect in Eligibility's hierarchical match (epic D11,
reversing D10). A-98 gained an addendum removing `applied/scheme-profile/`. Phase 3 and the lanes
were re-planned (AIR-3.1 merges second, AIR-3.3 is an Eligibility slice), and the sketches were
revised to agree: MORK bridge §1, §3 and §8, peril vocabulary §6.8, §9.1 and §10, the whitepaper's
N16, D35 and phasing, and the exposure ontology's layout.

A walkthrough with the human then reduced A-100 to Eligibility's law and compilers (the
compilers already resolve the scheme and expand its decisions, so no Vocabulary profile is
needed), moved crosswalks to SKOS with Foundation provenance and MORK as the proposal channel,
and confirmed that checks across cause and characteristics are Eligibility profiles over one
subject. That needs set readings (ADR-A103, formerly substrate item S3, now AIR-3.2 and AIR-3.3)
and one node per link of a loss's cause chain (`aeo:LossCause`). Epic D11 was reworded and D12
added. Phase 3, the lanes, and the peril vocabulary (§6.8 now the worked check), MORK bridge,
whitepaper and exposure sketches were revised to agree.

The human accepted A-100 and A-98's addendum, and A-103 with negation added
(`elg:negated`: evaluate, then swap Permitted and Denied, keeping Undetermined). The lanes file
gained the merge gate and the merge points (§3).

AIR-0.1 was signed off and committed (`3377a71`). The lanes plan was rewritten around the two
machines and three agents actually available (runtime machine: Claude Code, Copilot Pro+.
Sandbox machine: Copilot Business, no runtime, pull only).

## Phases

| Phase | Plan | State | Status record |
|---|---|---|---|
| 0 Decisions | [plan](../plans/applied-insurance-reference-phase-0.md) | ✅ AIR-0.1 merged (`3377a71`) | this file |
| 1 Module split | [plan](../plans/applied-insurance-reference-phase-1.md) | ⏳ | created at phase start |
| 2 Peril vocabulary | [plan](../plans/applied-insurance-reference-phase-2.md) | ⏳ | created at phase start |
| 3 Readings and crosswalks | [plan](../plans/applied-insurance-reference-phase-3.md) | ⏳ | created at phase start |
| 4 Exposure | [plan](../plans/applied-insurance-reference-phase-4.md) | ⏳ | created at phase start |
| 5 Contract module | [plan](../plans/applied-insurance-reference-phase-5.md) | 🅿️ deferred until Open CBAA integration of 1 to 4 (D2) | created at phase start |
| 6 Submission, claims | [plan](../plans/applied-insurance-reference-phase-6.md) | ⏳ | created at phase start |
| S Substrate track | [plan](../plans/applied-insurance-reference-substrate.md) | ⏳ | created per item |

## Blockers

None.

## Next action

Round 0 of the lanes plan: on the runtime machine, create and push `air/1.1-layout`,
`air/2.1-peril-spec` and `air/3.1-flat-hierarchy`. Then round 1.
