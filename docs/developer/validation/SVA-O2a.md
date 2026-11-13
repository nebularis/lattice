<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: SVA-O2a, edge routes and label places on the canvas kit

**Unit:** [`studio-visual-authoring`](../status/studio-visual-authoring.md), slice SVA-O2a, a follow-up to [SVA-O2](SVA-O2.md), built on 2026-11-13 in autonomous mode.

## Invariant

An edge's path and its label's place are a deterministic function of the node boxes and the edges, so the same boxes and edges in any order give the same routes. A label covers no node and no other label wherever a free place exists on its edge, and where none is free it takes the place that covers least, so a label is always placed. An edge never wraps around its own node, since it leaves and enters by the sides that face the other node. Edges between one pair of nodes, in either direction, attach at different points and do not coincide.

## What changed

- **`src/canvas/edges.ts`.** New, pure, with no React and no DOM. `chooseSides` picks the sides, `routeEdges` returns a cubic Bezier for each edge with the label's box, and `curvePoint` gives the point at a parameter, so the path and the label come from the same numbers.
- **`src/canvas/kit.tsx`.** Additive. `useEdgeRoutes` routes from the nodes where they are now, including while one is dragged. `RoutedEdge` draws the routed path and puts its HTML label where the kit placed it. `Canvas` takes an optional `routing` prop that gives each edge its route as `data.route`. The mapping canvas does not pass it and keeps React Flow's edges.
- **`src/ui/OntologyCanvas.tsx`.** Both views use `RoutedEdge` in place of the edge that put a label at a fixed fraction. Titles, the dashed shape-only edge, the subclass edge's style and the count line are as they were. `LAYOUTS` is exported so the test uses the canvas's own options, and its values are unchanged.
- **`src/styles.css`, `README.md`.** The label rule also names the kit's class, the ontology canvas's handles are not shown, and the `src/canvas/` row names `edges.ts`.

The drawing ignores where React Flow would attach an edge and draws from the node boxes, since that keeps an edge and its label following a node as it is dragged and lets an edge attach at any side. A node keeps its two handles because React Flow does not draw an edge between nodes that have none.

## Tests

| ID | Given / When / Then | Level | Pass |
|---|---|---|---|
| O2a-T1 | a target to the right in LR / `routeEdges` / leaves by the right, enters by the left, and the path starts and ends on those points | L1, positive | Expected sides and points |
| O2a-T2 | a target to the left in LR / `routeEdges` / leaves by the left, enters by the right, and the curve stays within the gap between the nodes | L1, positive | Expected sides and extent |
| O2a-T3 | two nodes in one column in LR, either above the other / `routeEdges` / bottom to top where the target is lower, top to bottom where it is higher | L1, positive | Expected sides and points |
| O2a-T4 | nodes whose extents along the direction overlap a little, and nodes that do not / `chooseSides` / the first are one rank and the second are two | L1, positive | Expected sides |
| O2a-T5 | TB / `chooseSides` and `routeEdges` / the rule turned through a quarter | L1, positive | Expected sides and points |
| O2a-T6 | an edge from a node to itself / `routeEdges` / a loop on the right side that bulges out | L1, positive | Expected sides and extent |
| O2a-T7 | an edge to a node not given / `routeEdges` / it is left out | L1, negative | Only the other edge |
| O2a-T8 | a straight run / `curvePoint` / the start at 0, the end at 1, the middle at 0.5 | L1, positive | Expected points |
| O2a-T9 | two edges between one pair, in one direction / `routeEdges` / different attachment points at both ends and curves at least 8 apart | L1, positive | Expected points and distance |
| O2a-T10 | two edges between one pair, in opposite directions / `routeEdges` / the same sides, different points and curves at least 8 apart | L1, positive | Expected points and distance |
| O2a-T11 | three edges between one pair, given out of order / `routeEdges` / spread around the middle in order of id and kept on the side | L1, positive | Expected order |
| O2a-T12 | edges between different pairs sharing a node / `routeEdges` / none is moved | L1, positive | Middle of the side |
| O2a-T13 | nothing in the way / `routeEdges` / the label is centred at t = 0.5 and as wide as its text and padding | L1, positive | Expected box |
| O2a-T14 | other width, height and padding / `routeEdges` / the label's box takes them | L1, positive | Expected size |
| O2a-T15 | options given as undefined / `routeEdges` / the defaults | L1, positive | Equal routes |
| O2a-T16 | an edge with no label / `routeEdges` / no label box | L1, negative | No box |
| O2a-T17 | a node box covering t = 0.5 / `routeEdges` / a label that covers it not, centred at another candidate | L1, positive | No overlap |
| O2a-T18 | two edges that cross at their middles / `routeEdges` / the first takes t = 0.5, the second moves and the labels do not overlap | L1, positive | No overlap |
| O2a-T19 | a label wider than the room, so no candidate is free / `routeEdges` / the candidate covering the least area, ties by the order of preference | L1, positive | Expected box |
| O2a-T20 | two wide labels on one pair / `routeEdges` / both are placed and differ | L1, positive | Two boxes |
| O2a-T21 | the same nodes and edges shuffled five ways and repeated / `routeEdges` / identical results in order of id | L1, positive | Equal results |
| O2a-T22 | the facility sample's classes with shapes off, laid out by the kit with the canvas's options and node size / `routeEdges` / nine labels, none on a node and none on another label | L1, positive | No overlap |
| O2a-T23 | the same with shapes on / `routeEdges` / the same | L1, positive | No overlap |
| O2a-T24 | the earlier browser tests, the ontology test among them, unchanged / the browser suite on the fake service / none changes | L3, positive | 26 tests pass |

**The one command:** `mise exec -- yarn workspace @lattice/config-studio exec vitest run src/canvas/edges.test.ts`, from the repository root. `mise exec -- yarn workspace @lattice/config-studio exec tsc --noEmit` checks the types, and `mise run test:config-studio` runs the browser suite.

## Artefacts to inspect

- `apps/config-studio/src/canvas/edges.ts` and its test, `RoutedEdge` and `useEdgeRoutes` in `src/canvas/kit.tsx`, and `src/ui/OntologyCanvas.tsx`.
- The drawing of the facility sample with "Include shapes" on and no class selected, in both views. The three labels between the first two columns no longer sit on one another, `ex:hasDrawdown` leaves Facility by its left side and enters Drawdown by its right, and no label covers a class.

## Deliberate non-coverage

- **Edges crossing one another.** They are not minimised. That is the layout's part, and BL-23's.
- **An edge that spans more than one rank or column.** Its curve is not bent around the nodes between its ends, so on the facility sample `ex:applicant` and `ex:branch` pass behind Facility and Guarantor. Only its label is kept off the nodes.
- **A label on another edge's line.** A label avoids nodes and labels and not the lines of edges.
- **The label's measured size.** The width is the text's length times a character width, which is an estimate for a proportional font. The defaults were read from the label in Chromium on 2026-11-13 with a margin, and a label whose text is wider than its estimate can touch a neighbour by a pixel or two.
- **The mapping canvas.** It keeps React Flow's edges and does not pass `routing`.

## Results

The results are filled at verification. What the builder ran on 2026-11-13, in autonomous mode:

- `vitest run`, the whole unit suite, printed 17 files and 277 tests passed, 254 before and the 23 new ones. The two acceptance tests failed on the first run, since `ex:applicant` runs two columns across the layout and its label sat on Facility. A ceiling of 120 on how far a control point lies from its attachment point let the label sit in the gap beside Facility, and they passed without the assertion being changed. The column and row gaps are unchanged.
- `tsc --noEmit` for `@lattice/config-studio` printed nothing and exited 0.
- The browser suite, with a temporary Playwright config that points at the Chromium already on this machine, deleted afterwards, printed `26 passed` with no test edited.
- Two screenshots at device scale 2 of the facility sample with "Include shapes" on and no class selected, from a temporary test removed afterwards, were read by the builder. The first drawing showed no labels at all, since an option passed as undefined overrode a default and gave a label an invalid position. That is now O2a-T15, and the second drawing was read. In the classes view no label lies on another or on a class, the backward edge `ex:hasDrawdown` runs straight back with its arrowhead at Drawdown and no edge loops behind a node, and the labels of the first gap are close together and legible. In the hierarchy view the three links meet Party's bottom side with the arrowhead pointing up at it. The two edges that span a column pass behind a class.
- Not run: `mise run check:config-studio` and `mise run test:config-studio` as written, a drag of a node in a browser to see the edges follow, and any run against the live stack.
