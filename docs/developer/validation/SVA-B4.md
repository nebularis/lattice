<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: SVA-B4, the import graph

**Unit:** [`studio-visual-authoring`](../status/studio-visual-authoring.md), slice SVA-B4 of the [plan](../plans/studio-visual-authoring.md), from section 5.2 of the [sketch](../sketches/studio-visual-authoring.md), built on 2026-11-13 in autonomous mode.

## Invariant

The import graph is derived from the graphs the browser already holds and is never stored, so the view adds no write and its only requests are the reads of a dependency's graph the Baseline view makes when the diagram is open. A stated edge is drawn as stated. An `imports` edge is an `owl:imports` statement resolved by ontology IRI or version IRI, or to a missing node, and a `binds` edge is a scheme contract's property, declared by the ontology node whose graph states it, joined to each scheme a binding of the contract or the contract's fallback names. A derived `uses` edge is marked as derived with a dashed line and a title, and is never drawn between a pair a stated edge already joins, in either direction. No edge joins a node to itself. The drawing is the same for any order of triples and of held imports.

## What changed

- **`src/rdf/importGraph.ts`.** `importGraph` returns nodes of kind `own`, `held`, `missing` and `scheme` and edges of kind `imports`, `binds` and `uses`, each sorted by kind and id. A scheme node says where it is declared (baseline, vocabulary, held import or dependency). `importCounts` and `importSummary` give the line above the canvas.
- **`src/ui/OntologyCanvas.tsx`.** A third view, "Import graph", top to bottom, with the legend line, node styles by kind, and the shapes and hops controls hidden for it. A click on a missing import opens the import dialog, and a click on a scheme declared in the baseline or the vocabulary opens it there.
- **`src/ui/BaselineView.tsx`.** Passes the held imports, the vocabulary part's graph, the dependencies' graphs (read only while the diagram is open) and the way to open the import dialog.
- **`src/styles.css`, `README.md`.** Appended rules for the node kinds, and the Baseline row.

## Tests

| ID | Given / When / Then | Level | Pass |
|---|---|---|---|
| B4-T1 | a baseline that imports nothing / `importGraph` / the own node alone | L1, positive | Expected node, no edge |
| B4-T2 | imports named by ontology IRI, by version IRI and one no document declares / `importGraph` / held nodes, a missing node, and one `imports` edge each | L1, positive | Expected ids |
| B4-T3 | a held import whose graph is loaded and imports another held import and a missing one, and held imports with no graph / `importGraph` / edges from the loaded graph only | L1, positive | Expected edges |
| B4-T4 | a scheme in the vocabulary part, one declared with `voc:ConceptScheme`, one in a held import and one in a dependency / `importGraph` / a node each with its place of declaration, and the counts | L1, positive | Expected labels, places and counts |
| B4-T5 | one own ontology, two held, one missing, three schemes / `importSummary` / the line of the brief | L1, positive | "1 ontology of the workspace, 2 imports held, 1 missing, 3 schemes." |
| B4-T6 | contracts, bindings and a fallback `voc:boundScheme` stated as the facility sample states them / `importGraph` / one `binds` edge per scheme named, from the declaring ontology, labelled with the contract, and none for a property no loaded graph declares | L1, positive and negative | Expected edges |
| B4-T7 | the property declared in a held import / `importGraph` / the `binds` edge runs from the held node | L1, positive | Expected edge |
| B4-T8 | terms used as a predicate and as a type, and an import stated one way / `importGraph` / a `uses` edge only where no stated import joins the pair, in either direction | L1, positive and negative | Expected edges |
| B4-T9 | `rdfs:subClassOf`, `rdfs:domain` and `rdfs:range` to a held class, and a document using only its own terms / `importGraph` / one `uses` edge, and no self edge | L1, positive and negative | Expected edges |
| B4-T10 | a concept, a scheme and a bound property in the baseline / `importGraph` / `uses` edges to the schemes named, and none to the scheme a `binds` edge already reaches | L1, positive and negative | Expected edges |
| B4-T11 | the same graphs in four orders of triples and of held imports / `importGraph` / identical JSON, with all three edge kinds and a missing node present | L1, positive | Equal JSON |
| B4-T12 | the lending baseline, the facility baseline and the facility vocabulary, split as the studio splits them / `importGraph` / the seven nodes and five `binds` edges listed below, no `imports` and no `uses` edge | L1, positive | Exact lists |
| B4-T13 | a workspace with one import held and one missing, the Baseline, Diagram, Import graph / the browser / a node for the workspace's ontology, the held import and the missing import, the count line "1 ontology of the workspace, 1 import held, 1 missing, 0 schemes.", two `imports` edges, no derived edge, no Include shapes and no Hops control, and a click on the missing node opens the import dialog | L3, positive | The test passes |
| B4-T14 | the 30 earlier browser tests / the whole browser suite on the fake service / none changes | L3, positive | 31 tests pass |

The facility sample of B4-T12, with `ex:` for `https://example.org/lending#`:

- Nodes: `own` (label Lending, `https://example.org/lending`) and six schemes, all declared in the vocabulary, `ex:OutcomeScheme`, `ex:RegionAmericas`, `ex:RegionContinents`, `ex:RegionEmea`, `ex:SectorScheme2026` and `ex:SectorScheme2027`.
- Edges, all `binds` from `own`: `ex:RegionContract` to `ex:RegionAmericas`, `ex:RegionContinents` (the contract's fallback) and `ex:RegionEmea`, and `ex:SectorContract` to `ex:SectorScheme2026` and `ex:SectorScheme2027`.

**The one command:** `mise exec -- yarn workspace @lattice/config-studio exec vitest run src/rdf/importGraph.test.ts`, from the repository root. `mise exec -- yarn workspace @lattice/config-studio exec tsc --noEmit` checks the types, and `mise run test:config-studio` runs the browser suite.

## Artefacts to inspect

- `apps/config-studio/src/rdf/importGraph.ts` and its test, and the third view in `src/ui/OntologyCanvas.tsx`.
- The new browser test at the end of `apps/config-studio/e2e/studio.spec.ts`.
- The facility sample holds no import, so on it the drawing shows `binds` edges only. The three kinds of edge together appear in the unit tests (B4-T11) and the held and missing imports in the browser test.

## Deliberate non-coverage

- **A `uses` edge on the facility sample.** Its instance data names concepts of schemes its contracts already bind, so a `uses` edge to each would repeat a `binds` edge and is not drawn.
- **A scheme with no binding or declaring ontology edge.** `ex:OutcomeScheme` is drawn with no edge, since no stated relation joins it to an ontology.
- **Dependencies in the browser.** The Baseline view reads a dependency's graph as the workspace does, and no browser test holds a dependency.
- **Editing.** The view never writes, by SVA-Q9.
- **Layout of a wide graph.** The layout is the kit's. A graph of more than five nodes opens at a fixed zoom, so a sixth scheme of a row can lie beyond the pane and is reached by panning.

## Results

The results are filled at verification. What the builder ran on 2026-11-13, in autonomous mode:

- `vitest run`, the whole unit suite, printed 19 files and 308 tests passed, 296 before and the 12 new ones.
- `tsc --noEmit` for `@lattice/config-studio` printed nothing.
- The browser suite, with a temporary Playwright config that points at the Chromium already on this machine, deleted afterwards, printed `31 passed`.
- Two screenshots at device scale 2, from a temporary spec since deleted, were read by the builder. The first drawing overlapped its nodes, since the layout was not given their size, and was fixed with size hints, and the rank gap was then set to leave room for the edge labels. In the final facility picture every label reads, the five labelled solid edges run apart from the ontology to their schemes, and the sixth node is cut at the pane's edge. In the picture of one held and two missing imports the solid edges are plain, the held node has a green border, and the missing nodes are orange with a dashed border. No dashed `uses` edge appears in either picture, so that style was not seen.
- Not run: `mise run check:config-studio` and `mise run test:config-studio` as written, and any run against the live stack.
