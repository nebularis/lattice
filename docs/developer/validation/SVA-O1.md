<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: SVA-O1, the canvas kit and its layered layout

**Unit:** [`studio-visual-authoring`](../status/studio-visual-authoring.md), slice SVA-O1 of the [plan](../plans/studio-visual-authoring.md), from section 7 of the [sketch](../sketches/studio-visual-authoring.md), built on 2026-11-12 in autonomous mode.

## Invariant

A canvas's picture is a deterministic function of its nodes, its edges and the author's stored positions. The same nodes and edges in any order give the same positions, a node the author or an edit already placed stays where it is, and only a new node is laid out. The layout is one function from nodes and edges to positions, so another layout is one more entry in `layouts` and no canvas changes (SVA-Q8, answered 2026-11-12 for our own layered layout, with `elkjs` and `dagre` left to BL-23). A position is kept in the browser under a key and never enters a graph.

## What changed

- **`src/canvas/layout.ts`.** `layered` breaks cycles by a depth first search from the sources and ignores the edges that go back, ranks each node by its longest path unless it carries a rank, orders each rank by its explicit orders or by four sweeps of the barycentre heuristic with a group first and ties by id, and places nodes from rank and position with the gaps and any sizes. A node with no edge and no rank of its own goes in a final rank sorted by id. An edge to a missing node, a self edge and a repeated edge are ignored, and a repeated id throws. `layouts` registers it.
- **`src/canvas/positions.ts`.** Reads, writes and clears the author's positions in a store that may be absent or refuse, and resolves where each node sits.
- **`src/canvas/kit.tsx`.** `Canvas` wraps React Flow with the studio's defaults, the layout, the stored positions and the menus. `ContextMenu` and the `Menu` types are exported.
- **`src/ui/MappingCanvas.tsx`.** It keeps its node components, edges, `connect`, `removeLink` and menus, and takes everything generic from the kit. Its props are unchanged. Each mapping's `depth` and `row` are its rank and order, and the source concepts are rank -1 in the order the scheme lists them.
- **Nothing else.** No new dependency, no change to `MappingView.tsx` or `styles.css`, and no graph, service or contract change.

## Tests

| ID | Given / When / Then | Level | Pass |
|---|---|---|---|
| O1-T1 | a chain of three / `layered` / one column each, left to right | L1, positive | Positions equal x 0, 280, 560 |
| O1-T2 | a diamond, and a graph with a short and a long path to one node / `layered` / the two middle nodes share a column, and the node takes its longest path | L1, positive | Expected positions and ranks |
| O1-T3 | cycles of three and of two, and a cycle with no source / `layered` / it ends and ranks the rest by the edges that remain | L1, negative | Every node placed, ranks as expected |
| O1-T4 | a small scheme with its depth and row as rank and order, and the source concepts at rank -1, in shuffled order / `layered` / each position is what the mapping canvas computed from `depth * 280` and `row * 64`, the sources one column before | L1, positive | Every position equal to the formula |
| O1-T5 | explicit orders with a gap and a repeated order / `layered` / the order is a slot, so the gap stays, and the repeat moves to the next slot | L1, positive | y values 0, 192 and 256 |
| O1-T6 | nodes with no edge, with and without a rank / `layered` / the first go in a final rank sorted by id, the second keep their rank and order | L1, positive | Expected positions |
| O1-T7 | children in two groups / `layered` / each group is contiguous within the rank | L1, positive | Order c1, c3, c2, c4 |
| O1-T8 | two edges that cross in the id order / `layered` / the barycentre sweeps remove the crossing | L1, positive | The lower node of the second rank follows the upper |
| O1-T9 | nodes with sizes, in LR and in TB / `layered` / the gaps are added to the extents along and across the ranks | L1, positive | Expected positions |
| O1-T10 | the same graph with its nodes and edges shuffled four ways, repeated, and with groups / `layered` / the same positions each time | L1, positive | Sorted entries equal |
| O1-T11 | a generated graph of 300 nodes with a few back edges / `layered` / no two nodes share a position, and in the acyclic part every edge runs from a lower x to a higher one | L1, positive | Distinct positions, each edge increasing |
| O1-T12 | an edge to a node not given, an edge to itself and a repeated edge / `layered` / each is ignored | L1, negative | Two nodes, expected positions |
| O1-T13 | a repeated node id / `layered` / it throws and names the id | L1, negative | The error message |
| O1-T14 | no nodes / `layered` / an empty map | L1, negative | Size 0 |
| O1-T15 | generated graphs of 100, 500 and 2,000 nodes / `layered` / each finishes with a position for every node and prints its time | L1, positive | Never fails on time (ADR-A124) |
| O1-T16 | the registry / `layouts` / `layered` is the one entry | L1, positive | Keys equal `["layered"]` |
| O1-T17 | positions written / `readPositions` / read back under their key and not under another | L1, positive | Equal to what was written |
| O1-T18 | no store, and a store that throws on every call / read, write and clear / nothing is thrown and a read is empty | L1, negative | No error, `{}` |
| O1-T19 | text that is not JSON, a JSON array, and entries that are not points / `readPositions` / those are dropped | L1, negative | Only valid points remain |
| O1-T20 | positions written, then cleared (lay out again) / `readPositions` / nothing | L1, positive | `{}` |
| O1-T21 | a node nobody placed, one the author placed, and one placed now / `resolvePositions` / the layout, the saved position and the current position, in that order of precedence | L1, positive | Expected map |
| O1-T22 | an edit that adds a node / `resolvePositions` with the current positions / every existing node stays and only the new node is laid out | L1, positive | Expected map |
| O1-T23 | the mapping sample, the canvas drawing chosen / the e2e test written before the kit existed, then run again after / a node for a mapping of the scheme, the pane menu offering "Add a root datum" and "Lay the scheme out again", and a click on a mapping node opening its card | L3, positive | Passes on the old code and on the kit |
| O1-T24 | the 24 existing browser tests / the whole browser suite on the fake service / none changes | L3, positive | 25 tests pass, 24 before and the new one |

**The one command:** `mise exec -- yarn workspace @lattice/config-studio exec vitest run src/canvas`, from the repository root. `mise exec -- yarn workspace @lattice/config-studio exec tsc --noEmit` checks the types, and `mise run test:config-studio` runs the browser suite. The timing figures print with `vitest run src/canvas/layout.test.ts -t "lays out" --disableConsoleIntercept`.

## Artefacts to inspect

- `apps/config-studio/src/canvas/layout.ts`, `positions.ts` and `kit.tsx`, and the two test files.
- `apps/config-studio/src/ui/MappingCanvas.tsx`, which is smaller by what moved into the kit.
- The new browser test at the end of `apps/config-studio/e2e/studio.spec.ts`.

## Layout time

Each run is a separate process of the timing tests alone, so each figure includes the engine's warm-up on its first call. The graphs are layered DAGs from a seeded generator, with about 1.3 to 1.6 edges a node (127, 743 and 3,142 edges) and a few edges back. Times are in milliseconds.

| Run | 100 nodes | 500 nodes | 2,000 nodes |
|---|---|---|---|
| 1 | 2.4 | 5.9 | 17.8 |
| 2 | 3.1 | 6.7 | 19.7 |
| 3 | 2.0 | 5.5 | 16.4 |
| 4 | 1.8 | 4.9 | 19.6 |
| 5 | 1.8 | 4.7 | 15.1 |

Machine: Intel Xeon Processor @ 2.30GHz (from `/proc/cpuinfo`), 4 logical processors, Node v22.23.4, Linux 6.18, running under vitest 5.0.5. The figure for 500 nodes is the one section 7 of the sketch left to this slice. It is about 5 to 7 ms here, so a web worker is not called for by these times. A browser on another machine, and a real ontology's shape, may differ, so a view that proves slow is a reason to revisit this.

## Deliberate non-coverage

- **The ontology views.** Drawing classes, properties and the hierarchy, and the toggle between domain and range and shapes, are SVA-O2.
- **Another layout.** `elkjs` and `dagre` are BL-23. Only the registry and the signature are here.
- **A web worker for layout.** It is taken up only if times like these call for it, and they do not.
- **React Flow's own drawing.** Edges, handles and zoom are the library's. The kit is covered where the studio's behaviour is, through the browser test of the mapping canvas.
- **Dragging, connecting and the menu actions in a browser.** The existing tests never opened the mapping canvas, so the new test covers drawing, the pane menu and a click. A drag that keeps a position, a link dropped on a node and the other menu items were checked by reading the code, and are not exercised by a test.
- **Storage that persists across a reload.** The stored positions are tested against a fake store, and no browser test reloads a canvas.

## Results

The results are filled at verification. What the builder ran on 2026-11-12, in autonomous mode:

- The new browser test, written and run first against the old `MappingCanvas.tsx`, printed `1 passed`. The kit was moved in afterwards, and the whole browser suite then printed `25 passed`, the new test among them.
- `vitest run`, the whole unit suite of `@lattice/config-studio`, 15 files and 234 tests passed, none failed.
- `tsc --noEmit` for `@lattice/config-studio` printed nothing.
- The timing tests were run five times, and the table above holds each run's figures.
- The browser suite ran with a temporary Playwright config that points at the Chromium already on this machine, deleted afterwards.
- Not run: `mise run check:config-studio` and `mise run test:config-studio` as written, a mutation probe of the ordering sweeps, and any run against the live stack.
