<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: v-rig VR-7, the seam for a read case

**Unit:** `v-rig` ([plan](../plans/v-rig.md), [status](../status/v-rig.md)).
**Branch:** `docs/placement-vehicles-structure`. Commits by the agent under the maintainer's authorisation of 2026-11-07, one per slice.
**Plan and test cases:** [the plan](../plans/v-rig.md), VR-7 in detail, principle 7, VR-Q1 and VR-Q5.
**Decisions:** [ADR-A153](../../architecture/decisions/ADR-A153-verification-rig-module.md) decisions 4 and 6, PRI-75 for the validation at the seam.

## Invariant

A Turtle graph in the `vrig:` vocabulary written outside the repository is accepted as a read case once the module's shapes accept it, refused with the report otherwise, and compared with the declared view by document and key, a differing value or state a disagreement finding, with nothing in the comparison depending on what wrote the case.

## Test cases

| Case | Expectation |
|---|---|
| VR7-01 | A conforming read case loads with its facts |
| VR7-02 | A read case the shapes refuse is refused by name |
| VR7-03 | A differing value and a differing state are disagreements located at the declared fact, an agreeing fact and a key the declared view lacks are not, and the message names no value |
| VR7-04 | Disagreements become findings under the identifier rule, each about the read fact, carried into the representation |
| VR7-05 | The same facts under another reader's identifiers give the same disagreements |

## One command

Run from the repository root.

```bash
mise run check:v-rig
```

## Artefacts to inspect

`tools/v_rig/src/v_rig/readcase.py`, the `--case` option in `cli.py`, `tools/v_rig/tests/read-case.ttl` and `test_readcase.py`.

## Deliberate non-coverage

A reader. The seam takes what one wrote and nothing here reads a body into facts. A ruling on a disagreement, which the rig's owner keeps (VR-Q1).

## Handoff

**Delivered 2026-11-08.** `readcase.py` loads a read case, validates it with the module's shapes and specification under pySHACL and refuses one that does not conform, compares each of its facts whose document and key the declared view also states, by the canonical JSON of the fact's state and value, and makes a `vrig:Disagreement` finding of each difference, located at the declared fact and about the read one, with a message that names no value. The read case's nodes are carried into the representation so the finding's `vrig:about` resolves there. `mise run v-rig -- ... --case <ttl>` takes one or more, and the run record counts the disagreements. The tracked read case over the mini-rig, invented like the mini-rig, agrees twice, differs on a value and on a state, and states one key the declared view lacks.

**The unit is built.** Every slice of the plan is built and its pack written, and the plan's Done when holds on the mini-rig. The tool runs end to end and its tests pass. A rig outside the repository is named at run time and nothing of one is in a tracked file, a test or a commit, and the deny list the tool writes is fed to the deny-terms check by naming it, with TD-157 recording that the check reads one list. Adding a key, a token or a reading to a rig needs a mapping row, a reference node or a declaration, and no code. A fact unknown, a fact negative and a fact absent give three outputs in the representation, the layer graph, the vectors and the theory. The findings regenerate byte for byte and two runs give the same identifiers. Swapping one rig for another of the format needs no change to the tool, which the tests prove on a copy of the mini-rig with one line changed.

**Checks run, with their results.**
- `mise run check:v-rig`, `python -m pytest tools/v_rig -q`: 73 passed.
- `mise run v-rig -- --rig tools/v_rig/tests/mini-rig --extension tools/v_rig/tests/mini-rig.extension.ttl --case tools/v_rig/tests/read-case.ttl`: ran, two disagreements among 266 findings.

## Results

| Case | Result |
|---|---|
| VR7-01 | pass |
| VR7-02 | pass |
| VR7-03 | pass |
| VR7-04 | pass |
| VR7-05 | pass |
