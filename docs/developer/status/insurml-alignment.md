<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# InsurML Alignment: Status

**Unit ID:** `insurml-alignment` (epic)
**Status:** planned . 📝 Proposed. Vision, sketches, epic plan and Phase 0 plan drafted, awaiting the maintainer's review
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

| Slice | Deliverable | State | Blocked on |
|---|---|---|---|
| IMA-0.1 | engagement brief | planned |  |
| IMA-0.2 | licence and publication record | planned |  |
| IMA-0.3 | ADR, profile | planned |  |
| IMA-0.4 | ADR, bridge tooling and kits | planned |  |
| IMA-0.5 | ADR, transclusion | planned |  |
| IMA-0.6 | ADR, inline parts | planned |  |
| IMA-0.8 | ADR, assembly interface | planned |  |
| IMA-0.7 | alignment edits | planned 2026-10-05, Pointers added on, final edits after gate 0 |  |
| IMA-1.1 | module skeleton, element type scheme, scheme binding in an insurance binding scope, key schemes for identifiers and LWR codes | planned |  |
| IMA-1.2 | containment shapes generated from InsurML's rules held as data, builder properties | planned |  |
| IMA-1.3 | alignment document, the collision table as fixtures, clean-room component library | planned |  |
| IMA-2.1 | lift kit: XSLT 3.0 normalisation, emission, minted IRIs, identities and keys, provenance | planned |  |
| IMA-2.2 | lower kit: component files, manifests, derived variables for richer conditions | planned |  |
| IMA-2.3 | fidelity table as tests, golden round trips, the MORK record of the structure mapping | planned |  |
| IMA-3.1 | transclusion, law W8, W3 and W5 read through transclusions | planned |  |
| IMA-3.2 | inline parts, W2's fourth form | planned |  |
| IMA-3.3 | references to a persistent identity with display text: **moved to CCS C8b** (2026-10-06), since CCS C8's stated meaning names variables by identity and the text should too. This epic's lift adopts it | planned |  |
| IMA-4.1 | assembly models, the record's new terms (`wrd:assembledUnder`, resolution and numbering records), diagnostics for each stage, laws WA-1 to WA-7 | planned |  |
| IMA-4.1a | assembler interface and the baseline adapter: Eligibility-decided inclusion with three values and declared treatments, alternatives, transclusions, resolution records | planned |  |
| IMA-4.1b | InsurML assembly model in the profile, and the InsurML adapter over the lifted graph | planned |  |
| IMA-4.2 | parity suite: baseline against InsurML adapter, and InsurML adapter against InsurML's processor, over every fixture configuration | planned |  |
| IMA-4.3 | renderer and numbering, with the rule chosen for Q32 | planned |  |
| IMA-4.4 | verification passes: references in every configuration, dependency acyclicity. Alternatives for every condition kind join when CCS C13a lands | planned |  |
| IMA-4.5 | optimisation passes: question plans, dead components, specialisation | planned |  |

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
