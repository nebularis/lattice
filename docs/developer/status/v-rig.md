<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# The verification rig: status

**Unit ID:** `v-rig`
**Plan:** [v-rig.md](../plans/v-rig.md)
**ADR:** to be drafted in VR-1, Proposed
**Status:** building 2026-11-07. VR-1 picked up. VR-2 to VR-7 planned, blocked as the plan's Depends on column says.

## Board

| Slice | Deliverable | State | Blocked on |
|---|---|---|---|
| VR-1 | the module `ontology/v-rig/`, its vocabulary, shapes, Proposed ADR and catalogue entry | building 2026-11-07 |  |
| VR-2 | the synthetic mini-rig, then the lifter with the declared and blind views | planned | VR-1 |
| VR-3 | the tracked mapping scheme and the extension seam | planned | VR-2 |
| VR-4 | P1, the layer graph against shapes, reasoner and competency queries | planned | VR-3 |
| VR-5 | P2 and P3, the generated theory and the test vectors | planned | VR-3 |
| VR-6 | P4, findings as RDF with stable ids and the report rendered from them | planned | VR-4 |
| VR-7 | the seam for a read case | planned | VR-2 |

## History

- 2026-11-07: unit created on `docs/placement-vehicles-structure`. The plan was approved by the maintainer the same day from a design briefed in chat, with VR-Q1 to VR-Q11 answered and recorded in the plan. The maintainer placed this unit before the formal-methods C4 model, since P1's findings against the ensemble and ledger drafts are what ADR-A130's text should settle before C4 checks it. VR-1 marked building before any other edit.
