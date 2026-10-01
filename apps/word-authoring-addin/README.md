<!-- SPDX-License-Identifier: MPL-2.0 -->

# LATTICE Authoring (Word add-in, proof of concept)

A Word add-in for the word authoring proof of concept (ADR-A114): mark clauses, definitions,
variables and defined-term references in a document, then read them as Logical English and
review the proposed `ins:` graph against [`platform/authoring-service`](../../platform/authoring-service).
Not a platform contract; its code, markup and manifest may change or be withdrawn without
deprecation.

This slice (WA8) is the add-in's domain layer only: the OOXML parser/writer, the tag codec, the
contract types and Ajv validation, the HTTP client and the `DocumentPort` seam. The task pane UI
(WA9) and the ribbon/right-click commands (WA9a) are not implemented yet.

## Modules (`src/`)

| Module | Holds |
|---|---|
| `domain/types.ts` | hand-written TypeScript types for every schema under `contracts/authoring` and `contracts/events` |
| `domain/schemas.ts` | one Ajv 2020-12 instance over the same 14 schemas, `validate(name, value): string[]` |
| `domain/tags.ts` | the content-control tag codec: `encode`/`decode`, and `title` |
| `domain/offsets.ts` | `occurrenceIndex` and `escapeWordSearch`, for `Range.search` |
| `domain/xml.ts` | small shared DOM helpers used by `ooxml.ts` and `metadata.ts` |
| `domain/ooxml.ts` | `parseBody`, `writeSections`, `writeTemplate`, `writePackage` |
| `domain/snapshot.ts` | `buildSnapshot(parsed, metadata)`, validated against `document-snapshot` |
| `domain/metadata.ts` | `toXml`/`fromXml` for the document's custom XML metadata part |
| `domain/mermaid.ts` | `toMermaid(graphView)`, a deterministic Mermaid `flowchart` renderer |
| `domain/poll.ts` | `pollJob(api, jobId, options)` |
| `api/client.ts` | `ApiClient`, `HttpApiClient`, `ApiError` |
| `word/port.ts` | the `DocumentPort` interface, `MarkResult`, `InlineMark`, `AuthoringMetadata` |

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

Today the manifest declares one ribbon button, "Show pane" (`manifest/manifest.xml`), which opens
the task pane. WA9a adds the mark-up and right-click commands.

## Running the tests

```
mise run check:authoring-addin
```

Type-checks with `tsc --noEmit` and runs the Vitest unit suite (`vitest run`).
