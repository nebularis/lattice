<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# The verification rig: status

**Unit ID:** `v-rig`
**Plan:** [v-rig.md](../plans/v-rig.md)
**ADR:** [ADR-A153](../../architecture/decisions/ADR-A153-verification-rig-module.md), Proposed 2026-11-08
**Status:** building 2026-11-08. VR-1 built, VR-2 picked up. VR-3 to VR-7 planned, blocked as the plan's Depends on column says.

## Board

| Slice | Deliverable | State | Blocked on |
|---|---|---|---|
| VR-1 | the module `ontology/v-rig/`, its vocabulary, shapes, Proposed ADR and catalogue entry | built 2026-11-08 |  |
| VR-2 | the synthetic mini-rig, then the lifter with the declared and blind views | building 2026-11-08 |  |
| VR-3 | the tracked mapping scheme and the extension seam | planned | VR-2 |
| VR-4 | P1, the layer graph against shapes, reasoner and competency queries | planned | VR-3 |
| VR-5 | P2 and P3, the generated theory and the test vectors | planned | VR-3 |
| VR-6 | P4, findings as RDF with stable ids and the report rendered from them | planned | VR-4 |
| VR-7 | the seam for a read case | planned | VR-2 |

## History

- 2026-11-07: unit created on `docs/placement-vehicles-structure`. The plan was approved by the maintainer the same day from a design briefed in chat, with VR-Q1 to VR-Q11 answered and recorded in the plan. The maintainer placed this unit before the formal-methods C4 model, since P1's findings against the ensemble and ledger drafts are what ADR-A130's text should settle before C4 checks it. VR-1 marked building before any other edit.
- 2026-11-08: VR-1 built. The module `ontology/v-rig/` at 0.1.0, its six examples committed before the vocabulary, ADR-A153 Proposed, the catalogue and release register updated, `tools/test_v_rig.py` in the catalog check, ten tests passing. The Validation Pack [VR-1](../validation/VR-1.md) records the checks run. Three release tags wait for the maintainer, `v-rig-v0.1.0`, `v-rig-shapes-v0.1.0` and `v-rig-vocab-v0.1.0`. Body nodes carry a kind token under `vrig:` rather than Wording's element types, so the module imports nothing and VR-3's scheme produces Wording's elements. VR-2 marked building in the same commit, under the maintainer's authorisation of 2026-11-07 to build the unit through.
