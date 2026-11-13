<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: SVA-O2, the ontology views on the canvas

**Unit:** [`studio-visual-authoring`](../status/studio-visual-authoring.md), slice SVA-O2 of the [plan](../plans/studio-visual-authoring.md), from section 7 of the [sketch](../sketches/studio-visual-authoring.md), built on 2026-11-13 in autonomous mode.

## Invariant

A drawing of the ontology is derived from the graphs the browser already holds and is never stored, so the views add no request and no write, and the author's positions stay in the browser. The shapes toggle only adds. Every edge drawn without shapes is drawn with the same id, ends, property and origin with them, and an edge that a domain and range and a shape both state is one edge that then names the shape. Shapes are read as the forms read them, a node shape by `sh:targetClass` or a class that is itself one, and a property shape by a plain IRI `sh:path`. A drawing is the same for any order of triples.

## What changed

- **`src/rdf/ontologyGraph.ts`.** `classGraph` and `hierarchyGraph` return nodes sorted by IRI and edges sorted by source, target, property and origin, with an optional focus and hops. `counts` says how many classes and links a view holds, and how many a shape states. The classes are those `baseline.ts` declares. An edge whose end is a class the baseline does not declare is not drawn.
- **`src/ui/OntologyCanvas.tsx`.** The read-only canvas, with the view switch, the "Include shapes" toggle, the hops selector, the count line, and the button "Draw the whole ontology" for more than 150 classes when no class is selected. A click on a class opens it in the Baseline by the route the axiom forms use.
- **`src/ui/BaselineView.tsx`.** A Details and Diagram switch heads the detail pane. Nothing the view showed before is removed.
- **`src/canvas/kit.tsx`.** One additive prop, `edgeTypes`, passed to React Flow. The layout is unchanged.
- **`src/styles.css`, `README.md`.** Appended rules for the edge labels, and the README rows.

## Tests

| ID | Given / When / Then | Level | Pass |
|---|---|---|---|
| O2-T1 | a property with a domain and a range that are classes / `classGraph` / one edge of origin `domain-range`, nodes with their labels | L1, positive | Expected edge and nodes |
| O2-T2 | a union domain and a union range / `classGraph` / an edge for each named member pair | L1, positive | Four edges |
| O2-T3 | a datatype range, a range the baseline does not declare, and a property with no domain / `classGraph` / no edge | L1, negative | No edge |
| O2-T4 | several domains and several ranges / `classGraph` / an edge for each pair | L1, positive | Four edges |
| O2-T5 | a self edge and two properties between the same classes / `classGraph` / an edge for each, told apart by property | L1, positive | Three ids |
| O2-T6 | a node shape with `sh:class` / shapes off and on / no edge, then one edge of origin `shape` naming the shape | L1, positive | Expected edge |
| O2-T7 | a property shape with `sh:node` of a shape with a target class / shapes on / an edge to that class | L1, positive | Expected edge |
| O2-T8 | a class that is itself a node shape, as source and as `sh:node` / shapes on / an edge naming the class | L1, positive | Expected edge |
| O2-T9 | a complex path, a datatype constraint, a property shape with no class, a shape with no target, and a class not declared / shapes on / no edge | L1, negative | No edge |
| O2-T10 | a shape with two targets, and a shape that is a blank node / shapes on / an edge from each target, and no shape named for the blank one | L1, positive | Expected edges |
| O2-T11 | domain and range and two shapes stating the same edge, and a shape-only edge / shapes off and on / the edges without shapes are a subset of those with, with the same id, ends, property and origin. The merged edge keeps origin `domain-range` and names both shapes | L1, positive | Expected ids, origins and shapes |
| O2-T12 | a chain of classes with a subclass / focus at 1 and 2 hops, from either end, and the default / the classes within the hops over properties and subclass links, in either direction | L1, positive | Expected node lists |
| O2-T13 | a focus / the edges among the kept classes, and the whole graph without a focus, and unlimited hops | L1, positive | Expected ids and nodes |
| O2-T14 | a shape that links a class to a far one / focus with shapes off and on / the neighbourhood grows only with shapes | L1, positive | Expected node lists |
| O2-T15 | a focus that is not a declared class / both graphs / empty | L1, negative | No nodes |
| O2-T16 | subclass links, one to an undeclared class and one by restriction / `hierarchyGraph` / an edge to each declared named superclass only | L1, positive | Three edges |
| O2-T17 | the hierarchy with a focus / `hierarchyGraph` / the neighbourhood over subclass links in either direction | L1, positive | Expected node lists |
| O2-T18 | the same graph with its quads in five other orders / every view and a focus / identical results | L1, positive | Equal JSON |
| O2-T19 | the lending baseline with the facility baseline over it, the facility sample's baseline / shapes off and on / nine classes and nine links either way. The shapes state four links, `borrower`, `arrangedBy`, `hasDrawdown` and `lender`, each already a domain and range edge and each naming `ex:FacilityShape` | L1, positive | Exact lists of ids, origins and shapes |
| O2-T20 | the facility baseline file alone / shapes on / only the links among the classes it declares | L1, positive | Three edges |
| O2-T21 | the facility sample in a workspace, the Baseline, the Diagram button / the browser / a node for a class of the sample, "9 classes and 9 links drawn.", with shapes "9 classes and 9 links, 4 stated by shapes drawn." and four edge titles naming `ex:FacilityShape`, the hierarchy "9 classes and 3 links drawn.", a click on a node selects that class in the list and the hops selector is enabled | L3, positive | The test passes |
| O2-T22 | the 25 earlier browser tests / the whole browser suite on the fake service / none changes | L3, positive | 26 tests pass |

**The one command:** `mise exec -- yarn workspace @lattice/config-studio exec vitest run src/rdf/ontologyGraph.test.ts`, from the repository root. `mise exec -- yarn workspace @lattice/config-studio exec tsc --noEmit` checks the types, and `mise run test:config-studio` runs the browser suite.

## Artefacts to inspect

- `apps/config-studio/src/rdf/ontologyGraph.ts` and its test, and `src/ui/OntologyCanvas.tsx`.
- The new browser test at the end of `apps/config-studio/e2e/studio.spec.ts`.
- On the facility sample the toggle adds no edge, since each link its shape states is already a domain and range link, so what it adds is the shape's name on four edges. A dashed edge appears only for a link no domain and range states, which the sample does not have.

## Deliberate non-coverage

- **The import graph.** It is SVA-B4.
- **OWL restrictions.** They are shown in the element's form and are not a source of edges here.
- **Editing.** The views never write, by SVA-Q9.
- **Layout quality on a large ontology.** The layout is the kit's, timed in SVA-O1. The check of more than 150 classes is by reading the code and is not exercised by a test, since no sample has that many.
- **Classes the baseline does not declare.** A range such as `skos:Concept` is not a node, so the links to it are not drawn.
- **Edges that run against the layout's direction.** A link back to an earlier column is drawn across the others, and its label can sit close to a neighbour's.

## Results

The results are filled at verification. What the builder ran on 2026-11-13, in autonomous mode:

- `vitest run src/rdf/ontologyGraph.test.ts`, 20 tests passed on the first run. The whole unit suite then printed 16 files and 254 tests passed, 234 before and the 20 new ones.
- `tsc --noEmit` for `@lattice/config-studio` printed nothing and exited 0.
- The browser suite, with a temporary Playwright config that points at the Chromium already on this machine, deleted afterwards, printed `26 passed`. The new test failed once, on a count of hierarchy links the builder had guessed as 5 and the sample gives as 3, and passed after the guess was corrected.
- A screenshot of the drawing with shapes on at device scale 2, taken from a temporary test on the facility sample with one extra shape added to the workspace so that a dashed edge shows, was read by the builder. Labels are readable, the dashed edge is visible, and the labels of the three links between the first two columns sit close together. The temporary test was deleted.
- Not run: `mise run check:config-studio` and `mise run test:config-studio` as written, and any run against the live stack.
