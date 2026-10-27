<!-- SPDX-License-Identifier: MPL-2.0 -->

# Configuration Studio

A web application for authoring persistence (`dal:`) and surface (`srf:`) configuration against an applied ontology, its baseline, and compiling it. A proof of concept ([ADR-A136](../../docs/architecture/decisions/ADR-A136-configuration-studio.md)): its code and its contracts may change or be withdrawn without deprecation.

It talks to the [service](../../platform/config-studio-service) in Turtle, as [contracts/config-studio](../../contracts/config-studio/README.md) defines, and the service hands validation and compilation to the [worker](../../workers/README.md#configuration-studio-jobs-adr-a136).

## What an author does

| View | For |
|---|---|
| Workspaces | make a workspace from a sample or uploaded Turtle. Each subject is sorted into baseline, persistence or surface by its terms |
| Overview | every baseline class with the persistence nodes declared at its class scope and the contracts it carries, and buttons to add either |
| Baseline | the class tree, a class's properties and what configures it, concept schemes, and replacing the baseline with a check for terms the configuration would lose |
| Persistence, Surface | the nodes by kind, and an editor per node whose fields and options come from the vocabularies, with each option's meaning, a read path built hop by hop, and findings on the field that caused them |
| Build | compile either configuration, follow the job, and read the compiled profile, the SPARQL per operation, the surfaces, findings and gaps |

The inspector shows the selected node's Turtle and the unsaved changes as a diff. The problems drawer lists every finding and opens the node it concerns. `⌘K` goes to any view, node or class, `⌘S` saves, `⌘Z` and `⇧⌘Z` undo and redo.

## How it is built

| Module | Holds |
|---|---|
| `src/rdf/graph.ts` | an immutable graph over an n3 store, its edits, and Turtle written in a fixed order |
| `src/rdf/vocabulary.ts` | fields derived from `rdfs:domain` and `rdfs:range`, and the few properties whose range the ontology leaves open |
| `src/rdf/editors.ts` | the node kinds, how an editor groups its sections, node creation, and the reference check |
| `src/rdf/baseline.ts`, `split.ts`, `path.ts`, `report.ts` | the baseline's terms, sorting an import, the read path, and reading a job graph |
| `src/state.ts` | a workspace in the browser: saved and edited graphs, undo, live validation, saving and conflicts |
| `src/api.ts` | the HTTP API |
| `src/ui/` | the views |

## Build, run and test

```bash
mise run bootstrap:frontend
mise run check:config-studio
mise run test:config-studio
```

The first installs the dependencies. The second stages the vocabulary and samples and runs the unit tests of the stage script, the worker, the service and this application, and type-checks it. The third runs the browser tests against a fake service (`e2e/fake-service.ts`), so it needs no Fuseki or RabbitMQ, and writes results under `.build/config-studio-test-results`. A pass is a zero exit status. Run `mise exec -- yarn workspace @lattice/config-studio exec playwright install chromium` once if Playwright asks for a browser.

To run the whole studio, start Fuseki and RabbitMQ (the service's README says how, with or without Docker), then each of these in its own terminal and browse <http://127.0.0.1:4175>:

```bash
mise run studio:service
```

```bash
mise run studio:worker
```

```bash
mise run studio:web
```

With all of that up, `mise exec -- yarn workspace @lattice/config-studio run test:stack` runs a browser test over the real stack.

## Depends on

React 19, n3, `lucide-react`, Vite and TypeScript. The tests use Vitest and `@playwright/test`.
