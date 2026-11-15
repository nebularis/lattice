<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: SVA-O4, routes round nodes, spread attachment points, fitted opening and unlinked nodes beside the drawing

**Unit:** [`studio-visual-authoring`](../status/studio-visual-authoring.md), slice SVA-O4, a follow-up to [SVA-O2a](SVA-O2a.md), built on 2026-11-15 in autonomous mode.

## Invariant

An edge passes through no node but its own two ends wherever a clear route exists, and where none exists the route that comes least near is returned, so a route is always returned. Edges that share one side of a node attach apart, in the order of where they go along the side. A drawing opens fitted to its pane, with a padding and never zoomed in beyond 1, and opens fitted again when its content is replaced. A node with no link sits in a block beside the drawing, on the side the layout does not run along. All of it is a deterministic function of the node boxes and the edges, so the same boxes and edges in any order give the same routes and positions.

## What changed

- **`src/canvas/edges.ts`.** `routeEdges` takes three steps. It chooses the sides as before. It then reads the ranks from the boxes, as the nodes whose extents along the direction overlap, so it holds after a node is dragged. An edge whose curve between the middles of its sides would come within `CLEARANCE` (8 px) of another node is given waypoints. It crosses each rank between its ends in the free channel nearest to the straight line between them, ties by the lower coordinate, along a level run entered and left 14 px outside the rank's nodes. Edges that use one channel take lanes of their own, 6 px apart in order of id. The path is a chain of cubic segments with the same tangent either side of a waypoint, so it has no kink. Two nodes of one rank with a node between them across it are joined by a detour round the rank on the side with less intrusion. It then spreads the edges that share a side of a node between margins of 8 px from the corners, ordered by the position of the other end along the side's axis (the first or last waypoint where there is one), ties by id.
- **The shape of `EdgeRoute.curve`.** It was one `Curve` and is now `Curve[]`, one segment where there is no waypoint. `curvePoint` accepts either. A single segment is read at its Bezier parameter, as before. A path of several segments is read by arc length, approximated by 32 chords for each segment, and the point is found on the curve, so it lies on the path and only its distance along it is approximate. The kit needed no change, since it uses `path` and `label` only.
- **Labels.** The seven candidate fractions are unchanged. Where none covers nothing, a label now looks for a free place among 73 finer fractions, nearest the middle first, before it falls back to the candidate covering the least area. The facility sample needed it, since a route that crosses a rank runs level along a channel only 15 px wide, and six labels share the first gap.
- **`src/canvas/layout.ts`.** A node with no edge and no rank of its own is no longer put in a final rank. It goes in a block beside the drawing, under it in LR and to its right in TB, in rows (LR) or columns (TB) that wrap at the drawing's extent along the ranks, sorted by id. The pitch along a row is the `columnGap` plus the widest node of the block, and across rows the `rowGap` plus the tallest, as among the ranks. The block starts a `rowGap` beyond the drawing's far edge. A graph of only such nodes is a grid of about square shape. A node with an explicit rank is untouched, so the mapping canvas's positions do not change.
- **`src/canvas/kit.tsx`.** A canvas that gives neither `defaultViewport` nor `fitViewUpTo` is fitted to its pane whatever the number of nodes, with a padding of 0.1 and a zoom of at most 1. A canvas that gives either keeps its rule, so the mapping canvas, which gives `defaultViewport`, opens as it did. The author's stored positions still win over the layout.
- **`src/ui/OntologyCanvas.tsx`.** The fixed zoom for the import graph and the count of 60 are removed. The canvas's `key` also holds the shapes switch, whether the whole ontology is drawn and the counts of nodes and edges, so a drawing whose content is replaced opens fitted again.

## Tests

| ID | Given / When / Then | Level | Pass |
|---|---|---|---|
| O4-T1 | an edge to a node that shares the source's side with another edge, the other end differing / `routeEdges` / the two attach at different points of the side, inside it (replaces the old rule, see below) | L1, positive | Distinct points |
| O4-T2 | four edges leaving one side, given out of order / `routeEdges` / distinct points inside the margins, ordered by the other end's position along the side | L1, positive | Expected order |
| O4-T3 | edges entering and leaving by one side of one node / `routeEdges` / the points differ | L1, positive | Distinct points |
| O4-T4 | a node in the straight line between the ends, in a rank between them / `routeEdges` / the route crosses the rank in the gap nearest the line and stays at least 7 px from every node | L1, positive | Clear route |
| O4-T5 | a wall no channel of the rank holds the line in / `routeEdges` / the route goes round it, above it at the tie, clear of it | L1, positive | Clear route |
| O4-T6 | two edges through one channel / `routeEdges` / separate lanes at least 5 px apart, in order of id, both clear | L1, positive | Distinct lanes |
| O4-T7 | a wall against the source that no route clears / `routeEdges` / a route with finite numbers is returned, from the source to the target | L1, negative | A route |
| O4-T8 | a route with a waypoint / `routeEdges` / the segments join, and the control points either side of the waypoint are collinear with it and on either side of it | L1, positive | Zero cross product |
| O4-T9 | a node between two nodes of one rank / `routeEdges` / a detour clear of it | L1, positive | Clear route |
| O4-T10 | the same rule in TB / `routeEdges` / a clear route through the channel | L1, positive | Clear route |
| O4-T11 | a route of several segments with a label / `routeEdges` / the label is centred on the path, covers no node, and its parameter is at the middle by arc length within 2 percent, and the path's ends are at 0 and 1 | L1, positive | On the path |
| O4-T12 | a routed set shuffled six ways and repeated / `routeEdges` / identical results | L1, positive | Equal results |
| O4-T13 | the facility sample's classes with shapes off, as the canvas draws it / `routeEdges` / a route for every edge, none within the clearance of a node but its ends, no label on a node or on another label | L1, positive | Three tests |
| O4-T14 | the same with shapes on / `routeEdges` / the same | L1, positive | Three tests |
| O4-T15 | the facility sample's class hierarchy / `routeEdges` / the same | L1, positive | Three tests |
| O4-T16 | the facility sample's import graph, with the vocabulary's six schemes and five binds edges, laid out with the canvas's hints / `routeEdges` / the same | L1, positive | Three tests |
| O4-T17 | unlinked nodes and a chain in LR / `layered` / the block under the drawing, rows of three, sorted by id | L1, positive | Expected positions |
| O4-T18 | unlinked nodes and a chain in TB / `layered` / the block to the right, columns that wrap at the drawing's height | L1, positive | Expected positions |
| O4-T19 | the same with node sizes / `layered` / pitches count the sizes | L1, positive | Expected positions |
| O4-T20 | only unlinked nodes / `layered` / a grid sorted by id, and one node at the origin | L1, positive | Expected positions |
| O4-T21 | unlinked nodes among a generated graph, shuffled and repeated / `layered` / identical positions, all distinct, all beyond the drawing | L1, positive | Equal results |
| O4-T22 | the mapping canvas's depth and row / `layered` / positions unchanged (the existing test) | L1, positive | Unchanged |
| O4-T23 | the earlier browser tests, the ontology and import graph tests among them, unchanged / the browser suite on the fake service / none changes | L3, positive | 31 tests pass |

**The one command:** `mise exec -- yarn workspace @lattice/config-studio exec vitest run src/canvas`, from the repository root. `mise exec -- yarn workspace @lattice/config-studio exec tsc --noEmit` checks the types, and `mise run test:config-studio` runs the browser suite.

## Tests replaced

Two existing tests asserted a rule this slice replaces. Neither was weakened to pass.

- **`edges.test.ts`, "do not move an edge that has no other between its pair".** It asserted that two edges from one node to different nodes both attach at the side's middle. That is the rule that bunched the labels, and the slice replaces it with a spread along the side. O4-T1 asserts the new rule for the same nodes.
- **`layout.test.ts`, "puts nodes with no edge in a rank after the rest, sorted by id".** It asserted that nodes with no edge take a final rank. That is the fault the slice closes, an unlinked node in a column of its own. O4-T17 to O4-T20 assert the new placement. Its last line, that two unlinked nodes start at the origin, is kept as part of O4-T20 in the form the new rule gives, a grid from the origin.

The test of the mapping canvas's positions and every other test of `layout.test.ts` and `edges.test.ts` pass unchanged.

## Artefacts to inspect

- `apps/config-studio/src/canvas/edges.ts`, `layout.ts` and `kit.tsx`, their tests, and `src/ui/OntologyCanvas.tsx`.
- The drawings of the facility sample at device scale 2, with "Include shapes" on and no class selected: the classes view, the class hierarchy and the import graph. In the classes view `ex:applicant` and `ex:branch` cross the middle rank in the gaps beside Facility and no edge runs through a class it does not join. Party sits under the drawing. In the import graph the five binds edges leave the workspace's ontology at five points and the unbound scheme sits beside the drawing.

## Deliberate non-coverage

- **Edges crossing one another.** They are not minimised. That is the layout's part and BL-23's. The edges between Drawdown and Loan application still cross one another and their labels sit on one another's lines.
- **A label on another edge's line.** A label avoids nodes and labels and not the lines of edges.
- **The mapping canvas.** It keeps React Flow's edges and its own opening rule, and moves onto this routing in SVA-O5.
- **Dragging a node.** The routes are recomputed from the boxes as they are, so an edge follows a node, and the tests move no node. A browser test of dragging is held by SVA-O5.
- **The width of the diagram pane.** A page's `.editor` caps it at 920 px, so the pane is about 864 px wide in the studio as it is. The screenshots at 1200 px and more lifted that cap with a temporary style.
- **The size of an import node.** The acceptance test takes the 240 by 76 the canvas gives the layout, and the rendered node may be a few pixels shorter.

## Results

The results are filled at verification. What the builder ran on 2026-11-15, in autonomous mode:

- `vitest run`, the whole unit suite, printed 20 files and 344 tests passed, 319 before and the 25 new ones. The first acceptance run failed on a label of `ex:applicant` that covered Facility, since the seven candidate fractions all fell on the level run or on other labels. The finer fractions of the labels section fixed it with no assertion changed.
- `tsc --noEmit` for `@lattice/config-studio` printed nothing.
- The browser suite, with a temporary Playwright config that points at the Chromium already on this machine, deleted afterwards, printed `31 passed` with no test edited.
- Three screenshots at device scale 2 from a temporary test removed afterwards, in a pane of 1988 px, and a fourth of the classes view at the studio's own pane width of 864 px, were read by the builder. The classes view and the import graph show no edge through a class it does not join, the whole drawing in view, Party and the unbound scheme beside the drawing, arrowheads at the targets and smooth curves. The labels are apart, though several sit on other edges' lines and the edges between Drawdown and Loan application cross. The hierarchy view shows its three links meeting Party's bottom side at three points, and its five unlinked classes in three columns to the right of the drawing, which makes the drawing wide.
- Not run: `mise run check:config-studio` and `mise run test:config-studio` as written, a drag of a node in a browser, and any run against the live stack.
