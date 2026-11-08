<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: v-rig VR-6, P4 the findings and the report

**Unit:** `v-rig` ([plan](../plans/v-rig.md), [status](../status/v-rig.md)).
**Branch:** `docs/placement-vehicles-structure`. Commits by the agent under the maintainer's authorisation of 2026-11-07, one per slice.
**Plan and test cases:** [the plan](../plans/v-rig.md), VR-6 in detail, principles 8, 10 and 11, VR-Q1 and VR-Q7.
**Decisions:** [ADR-A153](../../architecture/decisions/ADR-A153-verification-rig-module.md) decisions 5 and 6, [ADR-A147](../../architecture/decisions/ADR-A147-skolem-rule-for-mapped-sources.md) as the manner of the rule.

## Invariant

Every finding of a run is a `vrig:Finding` whose identifier is derived from its kind, document, locator and key by the versioned rule, two runs of one rig revision give the same identifiers and bytes, a finding that is resolved disappears from a diff by id, and the report is rendered from the findings graph alone, by document and locator, naming no text of a rig.

## Test cases

| Case | Expectation |
|---|---|
| VR6-01 | Every finding has a kind, a locator and one message, and its identifier is the rule's over its own fields |
| VR6-02 | Two runs give the same identifiers and the same findings graph bytes |
| VR6-03 | Removing the mini-rig's unresolved reference from its text, in a copy, removes that finding and no finding of another document |
| VR6-04 | The report renders every finding, its documents in order, with the run's identifying lines first and the counts by kind |
| VR6-05 | The report is byte for byte the same over two runs and carries no line of body text and no invented name |

## One command

Run from the repository root.

```bash
mise run check:v-rig
```

## Artefacts to inspect

`tools/v_rig/src/v_rig/report.py`, `p1.py` (`add_findings`), `lift.py` (`findings_graph`), `tools/v_rig/tests/test_report.py`, and a run's `findings.ttl` and `report.md`.

## Deliberate non-coverage

Which findings come back as requests to the plans, which the lifecycle's rule and the maintainer decide (VR-Q7). A log of rulings on disagreements, which the rig's owner keeps (VR-Q1).

## Handoff

**Delivered 2026-11-08.** The findings were nodes of the representation from VR-2 on, under the identifier rule of the module's section 9, and every projection since added its own kinds. This slice adds the report, `report.md`, rendered from the findings graph alone, the run's identifying lines in a table first, the counts by kind, then one section per document id or tracked file in order, each a table of findings sorted by locator, kind, key and message, with the first twelve hexadecimal digits of each identifier. The report names document ids, positions, keys and the findings' generic messages. A locator's section field may carry a heading's title, since the format's headings are the positions a body has, and the deny list the tool writes carries every title, so a report line pasted into a tracked file is caught at the commit.

**One correction to what counts as mapped.** A key an input binding reads is read, as a reading key is, so the two event keys the mini-rig's extension binds stopped being unmapped-key findings. The mini-rig's run now has 264 findings, 56 unmapped keys over 25 distinct keys, 40 uncertain mappings, 142 shape violations, 14 empty queries, 8 prose-only, 3 unresolved references and 1 inconsistency, against the 268 the VR-4 pack recorded.

**Checks run, with their results.**
- `mise run check:v-rig`, `python -m pytest tools/v_rig -q`: 68 passed.
- `mise run v-rig -- --rig tools/v_rig/tests/mini-rig --extension tools/v_rig/tests/mini-rig.extension.ttl`: ran, the report of 264 findings under 11 headings, the events file, the projection graph, the four documents, the programme and the seven competency files.

## Results

| Case | Result |
|---|---|
| VR6-01 | pass |
| VR6-02 | pass |
| VR6-03 | pass, the removal also takes the shape and lookup findings of the nodes whose positions shifted, all in the same document |
| VR6-04 | pass |
| VR6-05 | pass |
