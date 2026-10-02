<!-- SPDX-License-Identifier: MPL-2.0 -->

# LATTICE Authoring (Word add-in, proof of concept)

A Word add-in for the word authoring proof of concept (ADR-A114): mark clauses, definitions,
variables and defined-term references in a document, then read them as Logical English and
review the proposed `ins:` graph against [`platform/authoring-service`](../../platform/authoring-service).
Not a platform contract; its code, markup and manifest may change or be withdrawn without
deprecation.

The add-in has a domain layer (WA8: OOXML parser/writer, tag codec, contract types and Ajv
validation, HTTP client, `DocumentPort` seam), a task pane UI (WA9: `App.tsx` and five panels,
`officePort.ts`/`fakePort.ts`, a Playwright harness), and ribbon/right-click commands (WA9a, this
slice), running in a shared JavaScript runtime with the task pane (decision WA-D13).

## Modules (`src/`)

| Module | Holds |
|---|---|
| `domain/types.ts` | hand-written TypeScript types for every schema under `contracts/authoring` and `contracts/events` |
| `domain/schemas.ts` | one Ajv 2020-12 instance over the same 14 schemas, `validate(name, value): string[]` |
| `domain/tags.ts` | the content-control tag codec: `encode`/`decode`, and `title` |
| `domain/offsets.ts` | `occurrenceIndex` and `escapeWordSearch`, for `Range.search` |
| `domain/keys.ts` | `suggestKey`/`guessValueType`, ported from WA3's Java detector |
| `domain/xml.ts` | small shared DOM helpers used by `ooxml.ts` and `metadata.ts` |
| `domain/ooxml.ts` | `parseBody`, `writeSections`, `writeTemplate`, `writePackage` |
| `domain/snapshot.ts` | `buildSnapshot(parsed, metadata)`, validated against `document-snapshot` |
| `domain/metadata.ts` | `toXml`/`fromXml` for the document's custom XML metadata part |
| `domain/mermaid.ts` | `toMermaid(graphView)`, a deterministic Mermaid `flowchart` renderer |
| `domain/poll.ts` | `pollJob(api, jobId, options)` |
| `domain/uuid.ts` | a dependency-free UUID v4 generator |
| `api/client.ts` | `ApiClient`, `HttpApiClient`, `ApiError` |
| `word/port.ts` | the `DocumentPort` interface, `MarkResult`, `InlineMark`, `AuthoringMetadata` |
| `word/officePort.ts` | `DocumentPort` over the real Word API |
| `word/fakePort.ts` | `DocumentPort` over an in-memory model, for tests and the harness |
| `app/App.tsx` | the task pane root: tabs, error banner, all shared state |
| `app/DocumentPanel.tsx`, `MarkupPanel.tsx`, `AnalysePanel.tsx`, `LogicalEnglishPanel.tsx`, `GraphPanel.tsx` | one component per tab |
| `app/uiBridge.ts` | the observable store bridging ribbon/right-click commands and the task pane |
| `commands/ids.ts` | `COMMAND_IDS`, the eight command ids |
| `commands/handlers.ts` | `createHandlers(deps)`, one handler per command (no Office global touched) |
| `commands/register.ts` | `registerCommands(handlers)`, the only module that calls `Office.actions.associate` |
| `main.tsx` / `harness.tsx` | the real and harness entry points |

## Tag codec

| Kind | Tag | Title | Appearance | Colour |
|---|---|---|---|---|
| section | `lat:s:<sectionKey>` | `Section: <heading>` | BoundingBox | `#5B6B7F` |
| clause | `lat:e:<uuid>` | `Clause` | BoundingBox | `#1F6FB2` |
| definition | `lat:d:<uuid>` | `Definition` | BoundingBox | `#6A3FB5` |
| term | `lat:term` | `Term` | Tags | `#6A3FB5` |
| variable | `lat:v:<variableKey>` | `Variable: <label>` | Tags | `#C46A00` |
| reference | `lat:r:<uuid>` | `Defined term: <term>` | Tags | `#2E7D32` |

## Commands

| Id | Ribbon | Right-click | Does |
|---|---|---|---|
| `showPane` | Show pane | | opens the task pane |
| `markClause` | Clause | Mark as clause | wraps the selected paragraphs as a clause |
| `markDefinition` | Definition | Mark as definition | wraps the selected paragraphs as a definition |
| `markTerm` | Term | Mark as defined term (in its definition) | marks the selection as the defined term |
| `markVariable` | Variable… | Mark as variable… | drafts a variable from the selection, opens the pane on the Markup tab |
| `markDefinedTerm` | Defined term… | Mark as reference to a defined term… | marks a reference when exactly one definition matches, otherwise drafts one |
| `unmark` | Unmark | Remove LATTICE mark | removes the mark, keeping the text |
| `analyse` | Analyse | | opens the pane on the Analyse tab and starts the analysis |

A command never fails silently: a `MarkResult` that is not `ok`, or an exception, posts the reason
to the Markup tab and opens the pane.

## Running the tests

```
mise run check:authoring-addin
mise run test:authoring-addin
```

`check:authoring-addin` type-checks with `tsc --noEmit` and runs the Vitest unit suite.
`test:authoring-addin` additionally runs the Playwright suite (`e2e/`) against a real `msedge`
channel and the harness, using fake/mocked API responses.

`e2e-stack/` (plan WA10) is a second Playwright suite that runs against the real compose stack in
[`deployment/compose/authoring`](../../deployment/compose/authoring) instead — the real service,
worker, Fuseki and RabbitMQ, through the real Caddy proxy, no mocking. Run it with:

```
mise run check:authoring-stack
```

See [`deployment/compose/authoring/README.md`](../../deployment/compose/authoring/README.md) for
what the stack is and how to browse it directly.

## Loading the add-in in real Word

Sideloading `manifest/manifest.xml` into real Word is a separate step from running the compose
stack above (plan WA11); it is not yet documented here.

