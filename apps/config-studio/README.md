<!-- SPDX-License-Identifier: MPL-2.0 -->

# Configuration Studio

A web application for authoring vocabulary (`voc:`), quantification (`qnt:`), eligibility (`elg:`), persistence (`dal:`) and surface (`srf:`) configuration against an applied ontology, its baseline, checking it with each layer's own engine as you edit, and compiling it. It is a supported part of LATTICE ([ADR-A136](../../docs/architecture/decisions/ADR-A136-configuration-studio.md)), developed and maintained with the ontologies. Its contracts change with a deprecation, as [contracts/config-studio](../../contracts/config-studio/README.md) says.

It talks to the [service](../../platform/config-studio-service) in Turtle, as [contracts/config-studio](../../contracts/config-studio/README.md) defines, and the service hands validation and compilation to the [worker](../../workers/README.md#configuration-studio-jobs-adr-a136).

## What an author does

| View | For |
|---|---|
| Workspaces | make a workspace from a sample or uploaded Turtle. Each subject is sorted into the baseline or a configuration by the terms it uses |
| Overview | every baseline class with the persistence nodes declared at its class scope and the contracts it carries, and buttons to add either |
| Baseline | the class tree, a class's properties and what configures it, concept schemes, and replacing the baseline with a check for terms the configuration would lose |
| Vocabulary | concept schemes with their concepts as a tree, scheme contracts with a table of how each resolves for every period and set of binding scopes and a way to try one, bindings with their validity, binding scopes |
| Quantification | value spaces, units, quantities and ranges, with ranges drawn on a number line and written with their bounds in one step |
| Eligibility | conditions with each concept's decision over the resolved scheme, and tests: questions with a candidate and an expected decision, decided by the compiled query as you edit. Admission profiles |
| Persistence, Surface | the nodes by kind, and an editor per node whose fields and options come from the vocabularies, with each option's meaning, a read path built hop by hop, and findings on the field that caused them |
| Build | compile eligibility, persistence or surface configuration, follow the job, and read what it produced: decision queries and shapes, the compiled profile and its SPARQL, the surfaces, findings and gaps |

What waits on other work is shown and marked as under construction: testing an admission profile's composed decision, testing a condition that reads bound subjects, and quantification's comparisons, conversions and canonical range sets.

The inspector shows the selected node's Turtle and the unsaved changes as a diff. The problems drawer lists every finding and opens the node it concerns. `⌘K` goes to any view, node or class, `⌘S` saves, `⌘Z` and `⇧⌘Z` undo and redo.

## How it is built

| Module | Holds |
|---|---|
| `src/rdf/graph.ts` | an immutable graph over an n3 store, its edits, and Turtle written in a fixed order |
| `src/rdf/vocabulary.ts` | fields derived from the layers' SHACL shapes first, then `rdfs:domain` and `rdfs:range`, and the few properties the ontology leaves open |
| `src/rdf/shapes.ts` | the node shapes and property shapes that place and constrain a class's properties |
| `src/rdf/editors.ts` | the node kinds, how an editor groups its sections, node creation, and the reference check |
| `src/rdf/baseline.ts`, `split.ts`, `path.ts`, `report.ts` | the baseline's terms, sorting an import into the six graphs, the read path, and reading a job graph |
| `src/rdf/quantity.ts`, `eligibility.ts` | ranges with their bounds and quantities, and questions as tests |
| `src/state.ts` | a workspace in the browser: saved and edited graphs, undo, live validation, saving and conflicts |
| `src/api.ts` | the HTTP API |
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

## Depends on

React 19, n3, `lucide-react`, Vite and TypeScript. The tests use Vitest and `@playwright/test`.
