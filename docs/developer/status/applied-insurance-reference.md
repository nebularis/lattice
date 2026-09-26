<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Applied Insurance Reference - Status

**Unit ID:** `applied-insurance-reference` (epic)
**Status:** Proposed. Decisions D1 to D10 recorded 2026-09-26. Ready for Phase 0.
**Last updated:** 2026-09-26
**Trigger:** human request, 2026-09-26
**Plan:** [applied-insurance-reference.md](../plans/applied-insurance-reference.md)

## Current position

The five sketches were moved into `docs/developer/sketches/` by the human. The epic and its phase
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

## Phases

| Phase | Plan | State | Status record |
|---|---|---|---|
| 0 Decisions | [plan](../plans/applied-insurance-reference-phase-0.md) | ⏳ ready: AIR-0.1 | this file |
| 1 Module split | [plan](../plans/applied-insurance-reference-phase-1.md) | ⏳ | created at phase start |
| 2 Peril vocabulary | [plan](../plans/applied-insurance-reference-phase-2.md) | ⏳ | created at phase start |
| 3 Bridge and tiers | [plan](../plans/applied-insurance-reference-phase-3.md) | ⏳ | created at phase start |
| 4 Exposure | [plan](../plans/applied-insurance-reference-phase-4.md) | ⏳ | created at phase start |
| 5 Contract module | [plan](../plans/applied-insurance-reference-phase-5.md) | 🅿️ deferred until Open CBAA integration of 1 to 4 (D2) | created at phase start |
| 6 Submission, claims | [plan](../plans/applied-insurance-reference-phase-6.md) | ⏳ | created at phase start |
| S Substrate track | [plan](../plans/applied-insurance-reference-substrate.md) | ⏳ | created per item |

## Blockers

None.

## Next action

AIR-0.1: draft ADRs A-98, A-99, A-100 and A-102.
