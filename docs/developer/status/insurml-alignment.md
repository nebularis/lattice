<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# InsurML Alignment: Status

**Unit ID:** `insurml-alignment` (epic)
**Status:** 📝 Proposed. Vision, sketches, epic plan and Phase 0 plan drafted, awaiting the maintainer's review
**Last updated:** 2026-10-06
**Plan:** [insurml-alignment.md](../plans/insurml-alignment.md), [phase 0](../plans/insurml-alignment-phase-0.md)
**Vision:** [insurml-alignment-vision.md](../../architecture/insurml-alignment-vision.md)
**Sketches:** [insurml-bridge.md](../sketches/insurml-bridge.md),
[insurml-toolchain-and-ai.md](../sketches/insurml-toolchain-and-ai.md),
[insurml-typing.md](../sketches/insurml-typing.md),
[wording-assembly-interface.md](../sketches/wording-assembly-interface.md)
**Notes:** [identity, for the InsurML team](../notes/insurml-identity.md)

## Current position

Nothing is built. The epic waits for the maintainer's review of the vision, the sketches and the plans,
and for the gate-0 decisions. CCS remains the active unit, with C7c next.

**Decided 2026-10-05:** IMA-D1 (depth 5, depth 6 to be discussed with InsurML's owner), IMA-D3 (two
documents in one module), IMA-D5 (publication permitted). **Open at gate 0:** IMA-D2 (explanation
given in chat, decision pending), IMA-D4 (explored in the [typing sketch](../sketches/insurml-typing.md)),
IMA-D16, IMA-D17 (the assembly interface). **Answered by InsurML's owner, 2026-10-06:** Q-16. A contract may be a template or an instance. Its consequences are applied across the vision, sketches, identity note and analysis notes. Follow-ups Q-19 to Q-21 are open.

**Next action, for the maintainer:** decide IMA-D2, IMA-D4 and IMA-D17, and take Q-19 to Q-21 to InsurML's owner.

## Phase board

| Phase | State | Blocked on |
|---|---|---|
| 0 Decisions and engagement | not started | review of this epic |
| 1 Profile | not started | gate 0 |
| 2 Lift and lower | not started | phase 1 |
| 3 Wording changes | not started | phase 2, CCS C9 |
| 4 Assembly and passes | not started | phase 2 |
| 5 Meaning and placement | not started | phase 4, CCS C7c to C9, AIR-5.1 to AIR-5.4 |
| 6 Authoring and exchange | not started | phases 2 and 4 |
| 7 Packs and ingestion | not started | phase 2 |
| 8 Engagement | not started | phase 2 |

## Phase 0

| Slice | State |
|---|---|
| IMA-0.1 engagement brief | not started |
| IMA-0.2 licence and publication record | not started |
| IMA-0.3 ADR, profile | not started |
| IMA-0.4 ADR, bridge tooling and kits | not started |
| IMA-0.5 ADR, transclusion | not started |
| IMA-0.6 ADR, inline parts | not started |
| IMA-0.8 ADR, assembly interface | not started |
| IMA-0.7 alignment edits | not started. Pointers added on 2026-10-05, final edits after gate 0 |

### Licence and publication record

| Date | Item | State |
|---|---|---|
| 2026-10-05 | publication of documentation and analysis of InsurML's current draft | permitted by InsurML's owner. "Not for release" marks the draft's alpha state |
| | licence of InsurML's ontology, shapes and schemas for import and test (Q-2, Q-11) | open |
| | use of InsurML's example wording in LATTICE tests (Q-3) | open. Fixtures stay clean-room |
- 2026-10-06: IMA-3.3, references to a persistent identity, moved to CCS slice C8b, which follows C8. IMA-D8's identity half now lands with C8b

## Estimates and actuals

| Phase | Estimate (tokens) | Actual |
|---|---|---|
| 0 | 0.15M to 0.3M | |
| vision, sketches and plans (2026-10-05) | not estimated | not recorded |
