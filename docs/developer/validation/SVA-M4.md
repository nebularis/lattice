<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: SVA-M4, the output explorer

**Unit:** [`studio-visual-authoring`](../status/studio-visual-authoring.md), slice SVA-M4, built on 2026-11-17 in autonomous mode.

## Invariant

A part's content is shown in every rendering its media type allows. RDF is a text, a table or a graph on the canvas kit, JSON and XML are a tree or a text, and anything else is a text. The author chooses the rendering and the choice is kept in this browser for each media type, and nowhere else. Turtle text is the default for RDF, written by the graph's own writer, with N-Triples offered. A part that does not parse in its media type is shown as text with the parser's reason and never breaks the pane. A large part never blocks the page, since it is parsed after the page is drawn and only once, the table draws a page of rows at a time and a graph of many nodes is drawn only when asked. A canvas keeps the view its author set when its pane changes size, and is fitted again only while the author has not moved it since its last fit.

## What changed

- **`src/output/media.ts`.** The renderings a media type offers, the default first, and the author's choice for each media type and the text format, read part by part and written tolerantly as `canvas/positions.ts` does.
- **`src/output/rdf.ts`.** Parsing with n3 for each RDF media type, Turtle and N-Triples text, the table rows, the filter, and the nodes and edges of a graph. Each is a function of the set of triples, so any order or repeat of them gives the same result.
- **`src/output/tree.ts`.** JSON and XML as tree nodes, and pretty-printed JSON. XML is read with the browser's `DOMParser`.
- **`src/ui/OutputExplorer.tsx`.** The component, with the switch between renderings, Copy and Download for a text, the table with a filter and a "Show more" button, the graph on the canvas kit, and the tree.
- **`src/ui/RunPane.tsx`.** Each part is shown through the explorer in place of the plain block, under the same heading.
- **`src/canvas/kit.tsx`.** A canvas refits on a resize only while the author has not moved the view since its last fit. A pan, a zoom with the wheel or the buttons, counts as moving it, and the fit button makes it fitted again. Once moved, a resize keeps the view's centre and zoom.
- **`e2e/fake-service.ts`.** One switch, `runArtefact`, gives the sample run's artefact another text, for a part that does not parse.

## Tests

| ID | Given / When / Then | Level | The break tried | The failure it gave |
|---|---|---|---|---|
| M4-T1 | each media type / its renderings are asked for / RDF offers text, table and graph, JSON and XML a tree then text, anything else text, with parameters and case ignored | L1 | | |
| M4-T2 | a kept choice / read back, ignored where the media type does not offer it, read from bad or absent or throwing storage / the choice, the default, and no throw | L1 | | |
| M4-T3 | Turtle, N-Triples, N-Quads and TriG / parsed / the quads and the prefixes the text declares, and for a text that does not parse the parser's message and no throw | L1 | | |
| M4-T4 | IRIs, blank nodes and literals of each kind / written as terms / compacted under the longest prefix, an IRI no prefix covers in angle brackets, a literal with its language or datatype | L1 | | |
| M4-T5 | a set of triples, with quads / made into rows, filtered / sorted by subject, predicate and object, the graph kept for a quad, a filter matching in any column and a blank one keeping every row | L1 | | |
| M4-T6 | a set of triples / made into rows, nodes, edges and text in any order and with a repeat / the same result each time | L1 | | |
| M4-T7 | triples with literals, blank nodes, a type and a link to the node itself / made into a graph / a node for each IRI or blank node, no node for a literal, which is a row inside its subject's node, the type shown by the node, an edge labelled with its predicate for each link between two nodes, and the graphs of a dataset merged | L1 | | |
| M4-T8 | a graph / written as Turtle and as N-Triples / each parses back to the same triples, the N-Triples is sorted and has one line for each distinct triple, and the prefixes the writer declared are read back | L1 | | |
| M4-T9 | a JSON text with a value of each kind / made into a tree / a key for each object entry in order, an index for each item, each kind named, a unique path for each node, and for a text that is not JSON the message | L1 | | |
| M4-T10 | XML with namespaces, attributes, mixed text, CDATA and a comment / made into a tree / the prefix as written, the attributes first with the namespace declarations among them, text and elements in order, no comment, and for a text not well formed the message | L1 | | |
| M4-T11 | N-Triples of 1 and of 5 MiB / parsed and made into a table, Turtle, N-Triples and a graph / each finishes with its rows, and the milliseconds are printed | L1 | | |
| M4-T12 | a sample run in mapping mode / the artefact is looked at / it opens as Turtle text with the Turtle format chosen, N-Triples is offered, Copy and Download are there, the table lists the triple and narrows by a filter with its count, the graph shows a node for the subject, and the choice is the same after a reload for that media type only | L3 | `media.ts`, the default for RDF is the table | the Text button was not pressed where Text was expected |
| M4-T13 | the same run / the report is looked at / it opens as text with `sh:conforms true`, and its table lists its three rows with the types and the boolean literal | L3 | | |
| M4-T14 | the same run with an artefact that is not N-Triples / the part is looked at in text and in the table / the message and "Its text is shown as received." are there with the text, the report beside it still reads, and the run is complete | L3 | | |
| M4-T15 | the mapping canvas zoomed with the wheel / the dock is made narrower and wider / the zoom and the centre of the view are the same, and after the fit button the view is the fitted one, and a resize then fits it again, to the view the fit button gives at that width | L3 | `canvas/kit.tsx`, refit on every resize as before | the zoom was 0.293 where the author's 0.259 was kept |

**The one command:** `mise exec -- yarn workspace @lattice/config-studio exec vitest run`, `mise exec -- yarn workspace @lattice/config-studio exec tsc --noEmit` and `mise run test:config-studio`, from the repository root.

## Measured

The times M4-T11 printed on 2026-11-17, from one run on the builder's machine. They depend on the machine and nothing asserts on them. "Table rows" is the rows built and sorted, and the table draws 200 of them at a time, so the page itself draws no more than that.

| Part | Triples | Parse | Table rows | Turtle | N-Triples | Graph model |
|---|---|---|---|---|---|---|
| 1 MiB | 11,584 | 38 ms | 74 ms | 235 ms | 33 ms | 66 ms |
| 5 MiB | 57,290 | 86 ms | 228 ms | 853 ms | 168 ms | 290 ms |

## Artefacts to inspect

- `apps/config-studio/src/ui/OutputExplorer.tsx`, and `src/output/rdf.ts` for the one place a table, a graph and the text take their prefixes from.
- The Sample pane after a run in mapping mode, as Turtle text, as the table and as the graph, at 1600 by 1000 with the navigation and the scheme list collapsed and the dock widened.
- The refit in `apps/config-studio/src/canvas/kit.tsx`.

## Deliberate non-coverage

- **The simulators' own panes.** SVA-P4 and SVA-S3 build them and show their parts through this component.
- **A part over its limit in a browser.** The unit test measures a 5 MiB part's parse and the preparation of each rendering, and no browser test draws one.
- **A drawing of more than 150 nodes.** The rule is the ontology drawing's own, shared as `DRAW_AT_ONCE`, and no browser test draws one.
- **Graph names in a text.** Turtle and N-Triples text leave the graph of a quad out. The table shows it, and the graph merges the graphs of a dataset.
- **The clipboard.** Copy writes through `navigator.clipboard`, and a browser that refuses it leaves the text selectable. No test reads the clipboard.
- **Touch devices.** The wheel and pointer are tried, a touch pan is not.

## Decisions the brief did not settle

- **Prefixes.** The explorer takes an optional `prefixes` map, which the run pane does not give, since a run source holds no workspace prefixes. The studio's known prefixes and the part's own apply, and the Turtle text, the table and the graph all use the prefixes the graph's writer declared at the head of the Turtle, including the ones it makes up for a namespace used twice. The table and the graph therefore wait for the Turtle to be written.
- **Types in the graph.** An `rdf:type` to an IRI is shown by the node as a line of types and is not an edge to a node for the class, which would draw one node for each class beside the data. A link from a node to itself is a row of the node.
- **Blank nodes.** A blank node is read under the label the text gives it, and the parser's own prefix for them is left off so a label is the same for any order. The Turtle writer inlines one that is used once.
- **The text format.** Where Text is chosen for RDF, Turtle and N-Triples are a second switch with its own kept choice. A part is shown as received while its Turtle is written.
- **Where the choice is kept.** One key in local storage holds the renderings and the formats by media type, and every part of a media type changes together.
- **Copy and Download.** They are offered in the text rendering only, and act on the text shown. A download takes the part's file name with the extension of the format shown.
- **A table's pages.** It draws 200 rows at a time under a "Show more" button, and the count reads "Showing 200 of 57,290 rows" and, with a filter, "Showing 12 of 12 matching rows, 57,290 held".
- **A tree's children.** A node draws 100 children at a time, under a "Show more" button.
- **The fit button and zoom buttons.** React Flow does not tell a call from the author's own move for these, so the controls' own handlers mark the view moved or fitted.
- **The refit's reach.** Only a canvas that refits, one of up to its fit limit of nodes, keeps the centre. A canvas that opens at its own viewport is left as it was.

## Results

What the builder ran on 2026-11-17, in autonomous mode:

- `vitest run` printed 29 files and 468 tests passed, 433 before and 35 new in four files under `src/output/`.
- `tsc --noEmit` printed nothing and exited 0.
- The browser suite on the fake service, run three times with the headless Chromium already on the machine. The first run printed `61 passed (3.2m)` and one failure, the existing test "a handle moves with the arrow keys, Home and End, and a collapsed column takes no focus on Tab", which waited for a dock width of 316 after one arrow key. It passed on its own three times in a row and in the two runs after, and no change of this slice touches what it checks, so it is recorded as a flake that is not yet in the debt register. The second run printed `62 passed (3.1m)` and the third `62 passed (3.0m)`, 58 before and 4 new.
- The two breaks of the table were each made in the source, run, seen to fail and restored. With the default for RDF the table, M4-T12 failed on the Text button, and with a refit on every resize, M4-T15 failed on the zoom, 0.293 where 0.259 had been kept.
- Three screenshots at a device scale factor of 2, of the Sample pane after a run in mapping mode with the navigation and the scheme list collapsed and the dock widened, were taken by a temporary test that is removed. The artefact as Turtle text, as the table and as the graph read plainly, with the switch in two small groups above the text, the literals inside their subject's nodes in the graph, and long literals ending in an ellipsis with their full text in the node's title. The first graph drawn showed tiny nodes under full IRIs, since the table and the graph did not yet use the prefixes of the text and the columns were 300 px apart, and both were changed. The temporary configuration for the browser and the temporary test are removed.
