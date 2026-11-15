<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: SVA-O5, the canvas kit's behaviour held in a browser, and the mapping canvas on the kit's routing

**Unit:** [`studio-visual-authoring`](../status/studio-visual-authoring.md), slice SVA-O5, a follow-up to [SVA-O4](SVA-O4.md), built on 2026-11-15 in autonomous mode.

## Invariant

What the canvas kit does when a node is dragged, a page is loaded again, a link is dropped or a menu item is chosen is held by a browser test that fails when the behaviour is broken, and every canvas routes its edges one way. A dragged node's edges and labels follow it while the button is held and still end on its box. A position the author left is kept across a reload and forgotten by "lay out again", also across a reload. A link dropped on a mapping makes it a child or gives it a source, as `connect` says, and undo takes it back. Each item of the mapping canvas's node, edge and pane menus has the effect its label says. The mapping canvas draws its edges with the kit's `routing` and `RoutedEdge` like the ontology canvas, with its nodes where they were.

## What changed

- **`e2e/studio.spec.ts`.** Five browser tests and their helpers, appended. A drag is the mouse API in steps, a wait is on a condition, and a node's place is read from its transform, so it does not depend on the zoom. The mapping tests run on a workspace made from the author's own Turtle, since the sample the existing test uses declares no source concept and so draws none. It holds a datum with a source, a child with a source, a child data mapping, a root with a template and the template.
- **`src/ui/MappingCanvas.tsx`.** The edges are of type `link`, drawn by `RoutedEdge`, and the canvas is given `routing`. The ids (`parent|…`, `template|…`, `source|…`), the arrowhead of the parent edge, the dashes of the template and source edges, the label "template" and the handles are as they were. Each edge has a title that names what it says, which the browser shows and a screen reader reads. Its nodes, hints, opening rule and `onConnect` are untouched, so the positions test in `layout.test.ts` passes unchanged.
- **Nothing else.** `kit.tsx`, `styles.css` and `fake-service.ts` are unchanged.

## Order of work

The four mapping tests (O5-T3 to O5-T5) and the two ontology tests were written and run first against the mapping canvas as it was, drawn with React Flow's default edges, and all passed. The canvas was then moved onto the routing and the same tests passed again. One locator changed, in O5-T5 (see below).

## Tests

Each break was made in the source for one run, the test was run and failed, and the source was restored from a copy. None is left in place.

| ID | Given / When / Then | Level | The break tried | The failure it gave |
|---|---|---|---|---|
| O5-T1 | the facility sample's classes view / a class is dragged 120 px down with the mouse / while the button is still held, the path and the label of each of its five edges have changed, and each path's end lies within 3 px of the class's box | L3, positive | `kit.tsx`, `useEdgeRoutes(nodes, edges, …)` became `useEdgeRoutes(laid, edges, …)`, so the routes follow a drop and not a drag | `the path of ex:drawnUnder, from Drawdown to Facility`, expected not to be `M 240 16.75 C 330 16.75, 330 100.75, 420 100.75`, timed out |
| O5-T2 | the same drawing / a class is dragged, the page is loaded again and the diagram opened / the class is where it was left, and a class nobody moved is at the layout's place | L3, positive | `kit.tsx`, the call of `writePositions` in `keep` commented out | the class was at `{x: 420, y: 84}`, the layout's place, where `{x: 325.112, y: 225.47}` was expected |
| O5-T3 | the mapping canvas of a scheme with a source / a mapping is dragged, the page loaded again, "Lay the scheme out again" chosen, and the page loaded again | L3, positive | `kit.tsx`, the call of `writePositions` commented out, and then separately the call of `clearPositions` in `layOutAgain`, and then separately `setSaved({})` | at the first reload the mapping was at the layout's `{x: 280, y: 128}` and not where it was left. With `clearPositions` gone it failed at the second reload, at `{x: 319.789, y: 276.842}`, where it was left and not at the layout's place. With `setSaved({})` gone it failed straight after the menu item, with the same two places |
| O5-T4 | the same canvas / a link is dragged from a mapping to another, from a mapping to one that has a parent, and from a source concept to a mapping, then from a child to its parent and to the empty pane / the new link is drawn from the right node, a saved Turtle holds one more `compositeBroaderMapping` or `mappingFor`, undo removes each, a move of a parent is undone, and a cycle and a drop on the pane change nothing | L3, positive and negative | `MappingCanvas.tsx`, `setParent(g, c.target!, c.source!)` became `setParent(g, c.source!, c.target!)`, and then separately `setSource(g, c.target!, c.source!)` became `setSource(g, c.source!, c.target!)` | no edge `parent|…#Status` was drawn, expected one. With the other, no edge `source|…#Status` was drawn, expected one |
| O5-T5 | the same canvas / each item of the node, edge and pane menus is chosen in turn / "Delete the mapping" asks first, removes the mapping and its links, and undo brings them back. An edge's menu removes that link only, as the parent, source and template links. "Detach from its parent" keeps the mapping and removes its parent link. A child datum and a child data mapping are named by a prompt, and a cancelled prompt adds nothing. "Add a root datum" adds one with no parent. "Lay the scheme out again" moves a dragged mapping and leaves no two mappings at one place. A mapping with no parent has no detach item | L3, positive and negative | `MappingCanvas.tsx`, the `window.confirm(…) &&` of the delete item removed, then separately the detach item made to remove the `source` link, then separately the lay-out item made `() => undefined` | the delete asked nothing, so the dialog's message was `""` where it should contain `Delete Policy?`. With detach changed, the parent link of Cover was still drawn after the item was chosen. With the lay-out item changed, the mapping stayed where it was dragged |

The existing test "the mapping canvas draws a node for each mapping, offers its menus and opens a mapping's card on a click" passes unchanged on both canvases, as do the 344 unit tests, with the positions test of `layout.test.ts` among them.

**Locator that changed.** O5-T5 opens the template edge's menu by right-clicking its label (`.canvas-edge-label`), since the edge between the template and its mapping is shorter than the label that sits on it, so no point of the line is free. Before the move the test found a free point on the line. A right click on the label opens the edge's menu, as it did when the label was drawn inside the edge, because the label is a child of the edge's component and React passes the event up. The other two edges are still opened at a free point of their lines.

**The one command:** `mise run test:config-studio`, from the repository root, runs the browser suite. `mise exec -- yarn workspace @lattice/config-studio exec vitest run` and `mise exec -- yarn workspace @lattice/config-studio exec tsc --noEmit` run the unit tests and check the types.

## Artefacts to inspect

- `apps/config-studio/e2e/studio.spec.ts`, from the heading "What the canvas kit does when a node is dragged" to the end, and `src/ui/MappingCanvas.tsx`.
- The mapping canvas of the "Policies from XML and JSON" sample at device scale 2. The parent edges leave the right side of Policy at separate points, run in the gap beside the nodes and enter each child from the left with an arrowhead, and none passes through a node it does not join.
- The same canvas for a scheme with a template and a source link. The source edges are dotted, the parent edges are solid with an arrowhead and the template edge is dashed with its label.

## Deliberate non-coverage

- **A new node over another.** A node added by an edit is laid out where the layout puts it, and the nodes already there keep their places, so a new node can sit over one of them. It happened in O5-T5 when a child was added under a mapping that had just been detached. "Lay the scheme out again" clears it, which O5-T5 asserts, and the kit does not avoid it. It is a design question for the kit and is recorded for the maintainer, with no test asserting either way.
- **A template edge shorter than its label.** Two nodes one above the other with a gap of about 28 px in the flow leave a route shorter than the "template" label, so the label hides the edge. The label is readable and the link is still named by it and by the edge's title.
- **A drop on a node's body.** The tests drop on the target's handle, the way React Flow connects. A drop on the body of a node away from its handle is not asserted.
- **Several edges between one pair, and edges crossing.** As in SVA-O4, crossings are not minimised.
- **The ontology canvas's pane menu.** It offers none, so "lay out again" is tested on the mapping canvas.
- **Timing.** The tests wait on conditions and assert no duration.

## Results

The results are filled at verification. What the builder ran on 2026-11-15, in autonomous mode:

- `vitest run` printed 20 files and 344 tests passed.
- `tsc --noEmit` for `@lattice/config-studio` printed nothing.
- The browser suite, with a temporary Playwright config that points at the Chromium already on this machine, deleted afterwards. Three full runs printed `36 passed (1.6m)`, then `35 passed (1.7m)` with one failure, then `36 passed (1.7m)`, 31 before and the 5 new. The one failure was "the meaning view reads each clause's stated meaning, edits a template, enters meaning by hand and reviews a proposal", a test this slice does not touch. Run alone eight times in a row it passed each time, and a fourth full run printed `36 passed (1.6m)`. The five new tests passed in all four full runs.
- A screenshot of each canvas at device scale 2 from a temporary test, removed afterwards, was read by the builder. The parent edges of the sample leave Policy at separate points and reach each child from the left, with no edge through a node it does not join. In the scheme with a template, the three kinds of edge are told apart, the "template" label is readable, and the label covers the whole of the short template edge. The edge colour is the pale grey it was.
- Not run: `mise run check:config-studio` and `mise run test:config-studio` as written, and any run against the live stack.
