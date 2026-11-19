<!-- SPDX-License-Identifier: MPL-2.0 -->

# Configuration Studio

A web application for authoring vocabulary (`voc:`), quantification (`qnt:`), eligibility (`elg:`), persistence (`dal:`) and surface (`srf:`) configuration against an applied ontology, its baseline, checking it with each layer's own engine as you edit, and compiling it. It is a supported part of LATTICE ([ADR-A136](../../docs/architecture/decisions/ADR-A136-configuration-studio.md)), developed and maintained with the ontologies. Its contracts change with a deprecation, as [contracts/config-studio](../../contracts/config-studio/README.md) says.

It talks to the [service](../../platform/config-studio-service) in Turtle, as [contracts/config-studio](../../contracts/config-studio/README.md) defines, and the service hands validation and compilation to the [worker](../../workers/README.md#configuration-studio-jobs-adr-a136).

## What an author does

| View | For |
|---|---|
| Workspaces | make a workspace from a sample or uploaded Turtle. Each subject is sorted into the baseline or a configuration by the terms it uses |
| Overview | every baseline class with the persistence nodes declared at its class scope and the contracts it carries, and buttons to add either |
| Baseline | the class tree, a class's properties and what configures it, concept schemes, a list of the workspace's ontology, its held imports and its missing imports with an Import ontologies dialog (choose files or a folder, or drop them onto its drop area, a dropped folder keeping each file's path from its root, read the plan of how each import resolves, then hold the resolved documents in one request, an import of a LATTICE ontology resolving from the service's staged documents with no file chosen), and replacing the baseline with a check for terms the configuration would lose. A Diagram button draws the ontology on a canvas, as classes with a link for each object property (with the links node shapes state on request) or as the class hierarchy, around the selected class or whole, or as an import graph of the workspace's ontology, its held and missing imports and its concept schemes, with stated imports and bindings and the use of one ontology's terms by another derived and dashed. The workspace's state loads the graphs of its dependencies and held imports once, each kept apart as well as merged, and the diagram reads them from the state. The library sample shows all three kinds of edge once its imports are held |
| Vocabulary | concept schemes with their concepts as a tree, scheme contracts with a table of how each resolves for every period and set of binding scopes and a way to try one, bindings with their validity, binding scopes |
| Quantification | value spaces, units, quantities and ranges, with ranges drawn on a number line and written with their bounds in one step |
| Eligibility | conditions with each concept's decision over the resolved scheme, and tests: questions with a candidate and an expected decision, decided by the compiled query as you edit. Admission profiles |
| Persistence, Surface | the nodes by kind, and an editor per node whose fields and options come from the vocabularies, with each option's meaning, a read path built hop by hop, and findings on the field that caused them |
| Build | compile eligibility, persistence or surface configuration, follow the job, and read what it produced: decision queries and shapes, the compiled profile and its SPARQL, the surfaces, findings and gaps |

What waits on other work is shown and marked as under construction: testing an admission profile's composed decision, testing a condition that reads bound subjects, and quantification's comparisons, conversions and canonical range sets.

The author shares the page's width: the navigation, the mode's list column and the right-hand dock each collapse to a rail, the list and the dock are resized by a handle on their boundary with the middle (by the pointer, or the arrow keys, Home and End), and a double click on a handle restores its default, with each choice kept in the browser and nowhere else. The inspector shows the selected node's Turtle and the unsaved changes as a diff. The problems drawer lists every finding and opens the node it concerns. The baseline is validated live as a part is, and again when an import is held or released, so an import no held document declares is listed as a warning that opens the Baseline view. `⌘K` goes to any view, node or class, `⌘S` saves, `⌘Z` and `⇧⌘Z` undo and redo.

## How it is built

| Module | Holds |
|---|---|
| `src/rdf/graph.ts` | an immutable graph over an n3 store, its edits, and Turtle written in a fixed order |
| `src/rdf/vocabulary.ts` | fields derived from the layers' SHACL shapes first, then `rdfs:domain` and `rdfs:range`, and the few properties the ontology leaves open |
| `src/rdf/shapes.ts` | the node shapes and property shapes that place and constrain a class's properties |
| `src/rdf/editors.ts` | the node kinds, how an editor groups its sections, node creation, and the reference check |
| `src/rdf/baseline.ts`, `split.ts`, `path.ts`, `report.ts` | the baseline's terms, sorting an import into the six graphs, the read path, and reading a job graph |
| `src/rdf/ontologyGraph.ts` | the graphs the ontology drawings show, derived from the baseline and never stored. Classes and object properties from domains and ranges and, on request, shapes, and the class hierarchy, each limited to the neighbourhood of a class |
| `src/persistence/landing.ts` | the persistence canvas's pure part. It reads `compiled-profile.ttl`, which a persistence compile job gives, into the targets, boundaries and places it states, turns them into the nodes and edges of each lens, and tells whether the picture is out of date by what this browser sent with the compilation |
| `src/ui/PersistenceCanvas.tsx` | the exploded view of the Persistence view's Canvas option, read only. It draws the places the latest finished persistence compilation's compiled profile states on the canvas kit, with an aggregate, a profile and a scope node lens, and offers Compile where there is none or it is out of date |
| `src/rdf/quantity.ts`, `eligibility.ts` | ranges with their bounds and quantities, and questions as tests |
| `src/state.ts` | a workspace in the browser: saved and edited graphs, undo, live validation, saving and conflicts |
| `src/api.ts` | the HTTP API |
| `src/runs.ts` | a run's result assembled from its frames in any order with any repeats, and the controller that keeps one run in flight a pane, with the newest request waiting, a run timed by a duration, the kind's default plus a grace, from the injected timers, a failed last frame that settles a run whatever is missing, and frames from the tab's events or from the answer of a request that waits (ADR-A154) |
| `src/ui/RunPane.tsx` | the run pane every mode's runs use, controls on the left and a status line and the result's parts on the right, and the mapping dock's Sample tab, which runs the sample the mapping view keeps when Run is pressed |
| `src/ui/OutputExplorer.tsx` | the output explorer every run pane shows a part through (SVA-M4). RDF as Turtle or N-Triples text, a filterable table or a graph on the canvas kit, JSON and XML as a collapsible tree or text, anything else as text, and a part that does not parse as its media type is said so and shown as text. The rendering chosen for each media type is kept in the browser |
| `src/output/` | what the explorer computes without React. `media.ts` chooses the renderings for a media type and keeps the author's choice, `rdf.ts` parses RDF with n3 and turns it into Turtle, N-Triples, table rows and the nodes and edges of a graph, the same for any order of the triples, and `tree.ts` turns JSON and XML into tree nodes |
| `src/canvas/` | the canvas kit every canvas shares. `layout.ts` is our own layered layout behind one function, `edges.ts` routes each edge as a Bezier curve between the sides that face each other and places its label where it covers no node and no other label, `positions.ts` keeps the author's positions in the browser, `place.ts` moves a node an edit added to the nearest place clear of the nodes that kept theirs, and `kit.tsx` draws, menus and connects them with React Flow |
| `src/ui/` | the views. `Specials.tsx` holds the sections the vocabularies cannot derive |

## Build, run and test

```bash
mise run bootstrap:frontend
mise run check:config-studio
mise run test:config-studio
```

The first installs the dependencies. The second stages the vocabulary and samples and runs the unit tests of the stage script, the worker, the service and this application, and type-checks it. The third runs the browser tests against a fake service (`e2e/fake-service.ts`), so it needs no Fuseki or RabbitMQ, and writes results under `.build/config-studio-test-results`. A pass is a zero exit status. Run `mise exec -- yarn workspace @lattice/config-studio exec playwright install chromium` once if Playwright asks for a browser.

To run the whole studio in the background, `mise run studio:up`, browse <http://127.0.0.1:8090>, and `mise run studio:down` when done (the service's README, "Run it"). To run each part in its own terminal instead, start Fuseki and RabbitMQ (the service's README says how, with or without Docker), then each of these in its own terminal and browse <http://127.0.0.1:4175>:

```bash
mise run studio:service
```

```bash
mise run studio:worker
```

```bash
mise run studio:web
```

With the stack up, `mise exec -- yarn workspace @lattice/config-studio run test:stack` runs the browser tests over the real stack, against <http://127.0.0.1:8090>, or the address in `LATTICE_STUDIO_URL`.

`mise run test:config-studio` runs the browser journeys against an in-memory fake of the service, in under a minute. `mise run test:config-studio-browser` runs them, then the real-stack tests against a stack the studio harness starts in isolation, so a stack of your own is left alone. Run it before a merge into `main` of a change to the studio, by convention, and list its result in the handoff.

## Depends on

React 19, n3, `lucide-react`, Vite and TypeScript. The tests use Vitest and `@playwright/test`.
