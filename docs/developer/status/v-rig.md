<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# The verification rig: status

**Unit ID:** `v-rig`
**Plan:** [v-rig.md](../plans/v-rig.md)
**ADR:** [ADR-A153](../../architecture/decisions/ADR-A153-verification-rig-module.md), Proposed 2026-11-08
**Status:** built 2026-11-08. VR-1 to VR-7 built, the unit awaits the maintainer's review, ADR-A153's acceptance and the module's four release tags.

## Board

| Slice | Deliverable | State | Blocked on |
|---|---|---|---|
| VR-1 | the module `ontology/v-rig/`, its vocabulary, shapes, Proposed ADR and catalogue entry | built 2026-11-08 |  |
| VR-2 | the synthetic mini-rig, then the lifter with the declared and blind views | built 2026-11-08 |  |
| VR-3 | the tracked mapping scheme and the extension seam | built 2026-11-08 |  |
| VR-4 | P1, the layer graph against shapes, reasoner and competency queries | built 2026-11-08 |  |
| VR-5 | P2 and P3, the generated theory and the test vectors | built 2026-11-08 |  |
| VR-6 | P4, findings as RDF with stable ids and the report rendered from them | built 2026-11-08 |  |
| VR-7 | the seam for a read case | built 2026-11-08 |  |

## History

- 2026-11-07: unit created on `docs/placement-vehicles-structure`. The plan was approved by the maintainer the same day from a design briefed in chat, with VR-Q1 to VR-Q11 answered and recorded in the plan. The maintainer placed this unit before the formal-methods C4 model, since P1's findings against the ensemble and ledger drafts are what ADR-A130's text should settle before C4 checks it. VR-1 marked building before any other edit.
- 2026-11-08: VR-1 built. The module `ontology/v-rig/` at 0.1.0, its six examples committed before the vocabulary, ADR-A153 Proposed, the catalogue and release register updated, `tools/test_v_rig.py` in the catalog check, ten tests passing. The Validation Pack [VR-1](../validation/VR-1.md) records the checks run. Three release tags wait for the maintainer, `v-rig-v0.1.0`, `v-rig-shapes-v0.1.0` and `v-rig-vocab-v0.1.0`. Body nodes carry a kind token under `vrig:` rather than Wording's element types, so the module imports nothing and VR-3's scheme produces Wording's elements. VR-2 marked building in the same commit, under the maintainer's authorisation of 2026-11-07 to build the unit through.
- 2026-11-08: VR-2 built. The mini-rig under `tools/v_rig/tests/mini-rig/` and the lifter `tools/v_rig/`, a catalogued tool package with `bootstrap:v-rig` and `check:v-rig`, 27 tests passing. The Validation Pack [VR-2](../validation/VR-2.md) records the checks. The deny-terms check reads one list, so the generated list is fed by `LATTICE_DENY_TERMS` for a run of the check, and reading every candidate list is proposed as a debt row rather than changed here. VR-3 marked building in the same commit.
- 2026-11-08: VR-3 built. The tracked scheme `ontology/v-rig/projection/layers.mork.ttl` with its reference data, the mini-rig's extension beside the mini-rig, and the P1 runner in `tools/v_rig/p1.py`, 41 tests passing. The Validation Pack [VR-3](../validation/VR-3.md) records the checks and what the scheme leaves to the competency queries. The module gained the `projection` role, ordered lists as fact values and `vrig:readingKey`, all within the unreleased 0.1.0. VR-4 marked building in the same commit.
- 2026-11-08: VR-4 built. `tools/v_rig/p1_checks.py` runs each target layer's shapes, the reasoning test kit's consistency check and the competency queries under `ontology/v-rig/projection/competency/` over P1, 52 tests passing. On the mini-rig the layers refuse the projection 142 times, the reasoner finds it inconsistent over a date where Foundation wants a dateTime, and 14 of 28 competency questions have no answer. The Validation Pack [VR-4](../validation/VR-4.md) names each group, the requirements they are for the ensemble, ledger and programme plans. VR-5 marked building in the same commit.
- 2026-11-08: VR-5 built. `cases.py`, `p2.py` and `p3.py` in `tools/v_rig/`, the vector schema `contracts/v-rig/vectors.schema.json` at `lattice-v-rig-vectors/1`, and `vrig:InputBinding` in the vocabulary, 63 tests passing. The generated session built once on HOL in 2 seconds. The Validation Pack [VR-5](../validation/VR-5.md) records the checks and what waits for track E. VR-6 marked building in the same commit.
- 2026-11-08: VR-6 built. `report.py` renders `report.md` from the findings graph, by document and locator, with the run's identifying lines first, 68 tests passing. A key an input binding reads now counts as mapped. The Validation Pack [VR-6](../validation/VR-6.md) records the checks. VR-7 marked building in the same commit.
- 2026-11-08: VR-7 built, and with it the unit. `readcase.py` takes a Turtle graph in the vocabulary from outside, validates it and compares it with the declared view, 73 tests passing. The Validation Pack [VR-7](../validation/VR-7.md) records the checks and states the plan's Done when against the mini-rig. The unit waits on the maintainer for ADR-A153, the tags `v-rig-v0.1.0`, `v-rig-projection-v0.1.0`, `v-rig-shapes-v0.1.0` and `v-rig-vocab-v0.1.0`, and a run on a rig.
