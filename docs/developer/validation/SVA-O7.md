<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: SVA-O7, a new node is drawn clear of the nodes that kept their places, and a label never hides the edge it names

**Unit:** [`studio-visual-authoring`](../status/studio-visual-authoring.md), slice SVA-O7, closing the two faults [SVA-O5](SVA-O5.md) recorded as deliberate non-coverage, built on 2026-11-16 in autonomous mode.

## Invariant

A node an edit adds is drawn clear of every node that kept its place, and the nodes that kept their places never move. Where the layout's place for a new node is taken, the node takes the nearest place whose box covers no other node's, found by a bounded search that is the same for any order of the input. "Lay out again" still gives every node the layout's own place. A label never hides the edge it names. Where an edge is shorter than its label along its own direction, the label is placed beside the edge, on the side that is free, so the line stays visible and can be right-clicked.

## What changed

- **`src/canvas/place.ts`, new.** `placeClear` is pure. A new node whose wanted place is free keeps it. Any other takes the nearest of the places a whole step away, a step across the layout being the node's size and a row gap and a step along it the node's size and a column gap, at most six steps each way, in order of the distance moved. New nodes are placed in order of id, each seeing the ones before it. Where no place is free the layout's place is kept.
- **`src/canvas/positions.ts`.** `resolvePositions` takes an optional clearance and applies `placeClear` to the nodes that kept no place, where some node did. Given none, or where no node kept a place, it is as it was.
- **`src/canvas/kit.tsx`.** Gives `resolvePositions` the sizes of the nodes as measured, and else as expected.
- **`src/canvas/edges.ts`.** `besideEdge` places the label of an edge shorter than the label along the edge's direction beside it, to the right of a path that runs down and then to the left, moved out in steps of 6 px to the first place that covers no node and no label placed before it, no further than clears the two nodes together. It applies only where the label is no longer than the two nodes together along the path, so a label too long for any place beside the edge is placed as before.
- **`src/canvas/place.test.ts`, `edges.test.ts`, `e2e/studio.spec.ts`.** Twelve and six unit tests and two browser tests, appended. No existing test was changed.

## Tests

| ID | Given / When / Then | Level | Run that failed before the fix | The break tried after it | The failure it gave |
|---|---|---|---|---|---|
| O7-T1 | the mapping canvas of the probe scheme / a mapping is detached, a child datum is added under its old parent, a child data mapping under it, and a root datum / no two mapping boxes share an area, every mapping opens its card on a click, and "lay out again" leaves no two at one place | L3, positive | On the code as it was, `Cover` was drawn over `Rate`, and the test failed at the first overlap assertion with `Array ["Coverwrites nothing over Ratewrites nothing"]` | `kit.tsx`, the clearance given to `resolvePositions` in the effect replaced by `undefined` | the same overlap, `Cover` over `Rate` |
| O7-T2 | the same canvas / the template edge is looked at and its line right-clicked / the label's box does not meet the edge's own path box, the path is shorter than the label, a point of the line outside the label opens the menu "Remove the template link" | L3, positive | not run on the code as it was, the test was written after the fix and its break stands for it | `edges.ts`, the label placed beside the edge made unreachable (`if (false && beside)`) | the label's box met the path's box, expected `false`, received `true` |
| O7-U1 to O7-U12 | `place.test.ts` / a free place is kept, an occupied place gives the nearest free one, the next free one where that is taken, a place within the margin is refused, two new nodes wanting one place get two, the result is the same for any order and on a repeat, TB runs along y, a crowded canvas keeps the layout's place, and `resolvePositions` moves only the new node, takes a saved place as kept, gives the layout's own places where none was kept and is as before without a clearance | L1 | | | |
| O7-U13 to O7-U18 | `edges.test.ts` / a short edge's label does not meet the edge's own path, covers no node and no other label, sits on the right and on the left where a node holds the right, a long edge's label is still on its path, and the result is the same for any order | L1 | | with the beside placement made unreachable, three of the six failed | the short edge's label met its path |

The 50 tests of `edges.test.ts` that were there pass unchanged, and so do the rest of the 344 unit tests.

**Decisions the brief did not settle.**

- A new node is one with neither a position among the nodes now drawn nor a saved one. Placing applies only where at least one node kept a place, so laying out again, which forgets every saved place and every drawn one, is unchanged.
- Spacing is one node's size and the layout's gap, so a node moved to a free place keeps the look of the layout. Places at one distance are tried downward first, then further along.
- A label beside an edge is moved out until it covers no node, which for two stacked nodes 240 px wide is just beyond their side. The brief's wording, half the label's size and a gap, would leave a label of 21 px over two nodes 13 px apart covering 4 px of each. A label longer than the two nodes together along the path is left to the old rule, since an existing test holds that a label wider than any place takes the place of least overlap on its path.

**The one command:** `mise run test:config-studio`, from the repository root, runs the browser suite. `mise exec -- yarn workspace @lattice/config-studio exec vitest run` and `mise exec -- yarn workspace @lattice/config-studio exec tsc --noEmit` run the unit tests and check the types.

## Artefacts to inspect

- `apps/config-studio/src/canvas/place.ts` and `besideEdge` in `src/canvas/edges.ts`.
- The mapping canvas of a scheme with a template at device scale 2. The template edge between Status and Template is drawn as a visible line, and its label sits to the right of it, outside the two nodes' sides.

## Deliberate non-coverage

- **A label beside a short edge is some way from it.** Where the nodes are wide and close, a place that covers no node is outside their sides, so the label is about 150 px from the line, and the edge's title still names it.
- **Sizes of a new node.** A new node is placed by the size it is expected to have, since it is not measured yet.
- **A node dragged onto another.** A drag is the author's and is not moved.
- **Timing.** The tests wait on conditions and assert no duration.

## Results

What the builder ran on 2026-11-16, in autonomous mode:

- `vitest run` printed 21 files and 362 tests passed, 344 before and 18 new.
- `tsc --noEmit` for `@lattice/config-studio` printed nothing.
- The browser suite, with a temporary Playwright config that points at the Chromium already on this machine, deleted afterwards. Two full runs printed `38 passed (1.6m)` and `38 passed (1.6m)`, 36 before and the 2 new.
- A screenshot at device scale 2 from a temporary test, removed afterwards, was read by the builder. The template edge is a short visible line between Status and Template and its label sits to its right.
- Not run: `mise run check:config-studio` and `mise run test:config-studio` as written, and any run against the live stack.
