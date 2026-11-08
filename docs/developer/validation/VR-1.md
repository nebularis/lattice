<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: v-rig VR-1, the module

**Unit:** `v-rig` ([plan](../plans/v-rig.md), [status](../status/v-rig.md)).
**Branch:** `docs/placement-vehicles-structure`. Commits by the agent under the maintainer's authorisation of 2026-11-07, one per slice.
**Plan and test cases:** [the plan](../plans/v-rig.md), VR-1 in detail.
**Decisions:** [ADR-A153](../../architecture/decisions/ADR-A153-verification-rig-module.md), Proposed. VR-Q8, VR-Q11.

## Invariant

The representation of a case carries what a rig's format states without interpreting it, every node located and digested, a fact in exactly one of three states, and a finding with a kind, a document and a locator, and the shapes refuse anything else.

## Test cases

| Case | Expectation |
|---|---|
| VR1-01 | The three accepted examples conform to the structural shapes and the fact-state constraint with the spec loaded beside them |
| VR1-02 | A fact with no state, and a fact with two, fail the fact-state constraint |
| VR1-03 | A node with no locator fails the located shape |
| VR1-04 | A finding with no kind fails the finding shape |
| VR1-05 | The spec imports nothing and names no term of a layer |
| VR1-06 | The README's extraction matches the committed Turtle |
| VR1-07 | The catalogue lists the module as standalone, the import guard and the catalog check pass, and the release register has rows for its three documents |

## One command

Run from the repository root.

```bash
mise exec -- python -m pytest tools/test_v_rig.py -q
```

## Artefacts to inspect

`ontology/v-rig/README.md`, `spec/v-rig.ttl`, `vocab/v-rig-vocab.ttl`, `shapes/structural.ttl`, `shapes/constraints.ttl`, `shapes/.version`, the six examples, `tools/test_v_rig.py`, `repository-catalogue.md`, `docs/architecture/ontology-releases.md`, ADR-A153 and its row in the decisions index.

## Deliberate non-coverage

The tool that writes a representation (VR-2), the mapping that reads one (VR-3), and the projections (VR-4 to VR-6). The canonicalisation rules of the README's section 9 are stated here and implemented and tested in VR-2 and VR-6.

## Handoff

**Delivered 2026-11-08.** `ontology/v-rig/README.md` in ADR-A126's layout, 22 classes, 15 object properties, 35 datatype properties, 12 individuals, two views and ten finding kinds as a closed enumeration. Generated `spec/v-rig.ttl`, `vocab/v-rig-vocab.ttl`, `shapes/structural.ttl` and `shapes/constraints.ttl`, the last one SHACL constraint, the three states of a fact as `sh:xone`. Six examples, written and committed before the vocabulary. `v-rig` added to the catalogue's modules list as a standalone module with no imports. ADR-A153 Proposed with its row in the decisions index. `tools/test_v_rig.py` in `check:ontology-catalog`'s list.

**Design points settled while building, within the approved design.** Body nodes are `vrig:BodyNode` with a kind token and their text, not Wording elements, so the module imports nothing and the mapping scheme of VR-3 produces Wording's elements from them. A structured value is a `vrig:Record` carrying facts of its own, so a list of mappings in a rig needs no term. A third marker, `vrig:empty`, carries a null or an empty list, which is stated and holds nothing, distinct from the unknown marker. `vrig:Reading` is asserted by the mapping scheme on the facts of the keys it declares to carry readings, so the lifter holds no list of keys. Findings are themselves located, at the position of what they concern, so a finding's identifier is derived from its own fields.

**Checks run, with their results.**
- `mise exec -- python -m pytest tools/test_v_rig.py -q`: 10 passed.
- `mise run check:ontology-versioning -- --base-ref main`: `52 in-scope ontology document(s) checked against main: no unbumped changes`. It prints the three tags for the maintainer to create, `v-rig-v0.1.0`, `v-rig-shapes-v0.1.0` and `v-rig-vocab-v0.1.0`, on the commit that adds the register rows.
- `mise run check:import-guard`: `0 violation(s) across 9 substrate layers and 5 standalone modules`.
- `mise exec -- python tools/ontology_catalog.py check`: `ontology catalog consistent, 2 known defect(s) reported`, both MORK's, pre-existing.
- `mise run check:catalogue`: `21 module(s) and 16 tool package(s) agree with the tree`.
- `mise run check:published-decisions`: 6 passed.
- `mise run check:site-sections`: 6 passed, copies current.
- `mise run check:identifiers`: passed, 0 unresolved.
- The whole of `check:ontology-catalog` was not run for this slice. Its other suites do not read the new module.

## Results

| Case | Result |
|---|---|
| VR1-01 | pass, three tests |
| VR1-02 | pass, two tests, both facts named in the report's focus nodes |
| VR1-03 | pass |
| VR1-04 | pass |
| VR1-05 | pass, two tests. Foundation's `fnd:utility` annotation is the one `fnd:` term the spec carries, as every layer's does |
| VR1-06 | pass |
| VR1-07 | pass, by the four checks named above |
