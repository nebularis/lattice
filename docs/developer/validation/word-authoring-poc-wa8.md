<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: WA8, Add-in domain

**Unit:** `word-authoring-poc` (WAP), ADR-A118
**Plan:** [word-authoring-poc.md](../plans/word-authoring-poc.md) section "WA8: Add-in domain"
**Status record:** [word-authoring-poc.md](../status/word-authoring-poc.md)

## Invariant

The add-in's domain layer is the one place that knows how a document's Wording maps onto Word's
own OOXML shape (content controls, runs, paragraphs) and onto the platform's JSON contracts. It
must read a real Word document's messy, Word-generated XML (tracked changes, bookmarks, proof
marks, split runs, hyperlinks) into exactly the same element model the Java service and the
Python worker already agree on, write that model back as OOXML Word accepts, and validate every
JSON shape crossing the HTTP boundary against the same schemas the service and the worker use. No
UI exists yet (WA9); this slice is pure, Office.js-free domain logic, so every rule here is
testable under Vitest without Word.

## Test case table

| ID | Given / When / Then | Level | Invariant protected | Pass criterion | +/- |
|---|---|---|---|---|---|
| S8-01 | the tag codec / each kind encoded and decoded, a value that fails its own pattern, an upper-case key, `lat:x:1` / round trip; throw; throw; `null` | L1 | a tag is never written that `decode` cannot read back, and an unrecognised tag is never mistaken for one of ours | `tags.test.ts` (6 tests) passes | +/- |
| S8-02 | each of the three WA1 samples (with its template's headings) / written as OOXML, wrapped as a package, parsed, and built into a snapshot / equals the sample exactly, with no warnings | L2 | the writer and parser are exact inverses for every real sample, not just a synthetic one | `snapshot.test.ts`'s three parametrised cases pass | + |
| S8-03 | `fixtures/word-like-facility.xml`, hand-written in Word's own style (`w:rPr`, `w:proofErr`, `w:bookmarkStart`, `w:hyperlink`, `w:ins`, `w:del`, `w:smartTag`, `w:tab`, split runs) / parsed / the expected model in `fixtures/word-like-facility.expected.json`, and `w:delText` never appears in the output | L1 | the parser reads exactly the run-level rules of the plan against real Word artefacts, not an idealised document | `ooxml.test.ts`'s two S8-03 tests pass | + |
| S8-04 | a section with a heading, an unmarked paragraph, and an empty element, plus a paragraph outside all sections / parsed / two unmarked entries (one with a null section key), the empty element dropped with a warning | L1 | the zero-parts case is handled, not silently miscounted | `ooxml.test.ts`'s S8-04 test passes | - |
| S8-05 | a variable `w:sdt` nested inside a reference `w:sdt` / parsed / the nested marker's text folded in as literal text, with a warning | L1 | only one level of inline marker is ever semantically meaningful; a nested one degrades safely instead of crashing or silently losing text | `ooxml.test.ts`'s S8-05 test passes | - |
| S8-06 | a parse with an undeclared variable key and two adjacent literal runs / built into a snapshot / the declaration added as `text` with a warning, the literals merged, the snapshot validates | L1 | `buildSnapshot` never produces a document with an undeclared variable reference | `snapshot.test.ts`'s S8-06 test passes | + |
| S8-07 | Ajv over the 14 schemas / the WA1 valid and invalid fixtures, and the samples and templates / the same outcomes as the Python/Java contract tests (AC-05 to AC-07) | L3 | the three runtimes (Java, Python, TypeScript) agree on every schema, not just two of them | `schemas.test.ts` (5 tests) passes | +/- |
| S8-08 | `occurrenceIndex` with repeated text past an astral character, `escapeWordSearch("a^b")` | L1 | a search occurrence index is never off by one around a surrogate pair | `offsets.test.ts` (4 tests) passes | + |
| S8-09 | the facility graph view golden of WA6 / `toMermaid` / deterministic text, `n0...` node ids, a quote escaped as `#quot;` | L1 | the Graph tab (WA9) renders the same diagram on every call, and never outputs an unescaped quote that would break the Mermaid source | `mermaid.test.ts` (3 tests) passes | + |
| S8-10 | `HttpApiClient` with a fake `fetch` / a PUT, a 409 answer, a `fetch` that never settles / the right URL, method, headers and body; an `ApiError` with status 409; a timeout rejection | L1 | the client never hangs forever waiting on a broker or network fault, and a non-2xx answer is always distinguishable from a successful one | `client.test.ts` (3 tests) passes | +/- |
| S8-11 | the manifest / parsed / a GUID `Id`, every URL under `https://localhost:3443/addin/` (except the bare `AppDomain`), `ReadWriteDocument`, `WordApi` 1.4 | L1 | the manifest Word actually loads matches the dev server's own origin and API surface | `manifest.test.ts` (3 tests) passes | + |
| S8-12 | `pollJob` with fake timers / completed after three polls, never completing, failed at once / resolves completed; rejects `timeout`; resolves immediately | L1 | the Analyse panel (WA9) never polls forever, and never waits an interval after an already-final answer | `poll.test.ts` (3 tests) passes | +/- |

All 38 tests pass. `mise run check:authoring-addin` runs `tsc --noEmit` then `vitest run`
(10 files, 38 tests).

## One command

```
mise run check:authoring-addin
```

## Artefacts to inspect

- [`apps/word-authoring-addin/src/domain/ooxml.ts`](../../../apps/word-authoring-addin/src/domain/ooxml.ts)
- [`apps/word-authoring-addin/src/domain/tags.ts`](../../../apps/word-authoring-addin/src/domain/tags.ts)
- [`apps/word-authoring-addin/src/domain/schemas.ts`](../../../apps/word-authoring-addin/src/domain/schemas.ts)
- [`apps/word-authoring-addin/src/domain/fixtures/word-like-facility.xml`](../../../apps/word-authoring-addin/src/domain/fixtures/word-like-facility.xml) and its `.expected.json`
- [`apps/word-authoring-addin/manifest/manifest.xml`](../../../apps/word-authoring-addin/manifest/manifest.xml)

## Self-probe

Plan: "make the parser read `w:delText`. S8-03 fails."

Temporarily changed `walkElementContent` so a `w:del` wrapper is descended into (instead of
skipped) and its `w:delText` child is read as literal text. Ran `vitest run
src/domain/ooxml.test.ts` only: both S8-03 tests failed exactly as predicted, the first on the
golden comparison (`"won'tBorrower..."` instead of `"Borrower..."`) and the second on the explicit
`not.toContain("won't")` assertion. Reverted; the full suite (38 tests) passes again. This is the
second slice running (after WA7) whose prescribed self-probe bites exactly as written, with no
replacement test needed.

## Implementer choices

| Choice | Reasoning |
|---|---|
| `WritableSection` (the writer's own input shape) carries `heading` and an optional `unmarked: string[]`, not just the `document-snapshot` schema's `Section` | the schema's `Section` has no heading (that lives in the template) and no per-section unmarked text (that is a document-level array keyed by section). The writer needs both to round-trip a real sample exactly; the round-trip test looks the heading up from the matching template and groups `unmarked` entries by section key itself |
| A definition's defined term is located inside its single literal part by `indexOf`, and wrapped in a `term` content control only at that point, leaving the surrounding quotes as literal text either side | mirrors how a real author would select just the term inside a sentence like `"Borrower" means ...`, and keeps the parts list a single merged literal part on round trip, exactly matching the WA1 samples' own shape |
| `newTemplateElementId` (for `writeTemplate`) is a small dependency-free UUID v4 generator, not `crypto.randomUUID()` | avoids relying on a global whose availability differs slightly across the Node/Vitest/jsdom/Office.js runtimes this module runs under; the plan does not prescribe a specific generator here |
| `toMermaid` escapes `"` as `#quot;` and uses `n0, n1, ...` aliases in the graph view's own (already sorted) node order | satisfies S8-09's literal wording directly; Mermaid's own HTML-entity-style escapes (`#quot;`, `#35;`, etc.) are its documented way of getting a literal character into quoted text |
| `HttpApiClient`'s timeout races the `fetch` call against a `setTimeout`-driven rejection, rather than relying solely on `AbortController` | a fake `fetch` that never settles and ignores its abort signal (S8-10's third case) would otherwise hang forever; racing a timeout promise works regardless of whether the underlying `fetch` implementation honours the signal |
| `occurrenceIndex` returns a 0-based count | matches the 0-based indexing Office.js's `RangeCollection.items[n]` uses after a `search()` call, which is `markOccurrence`'s eventual consumer (WA9) |
| Schema imports in `schemas.ts` use relative paths four directories up into `contracts/`, resolved by Vite's built-in JSON-module support | avoids copying or symlinking the schemas into the add-in's own tree, keeping one copy of each schema exactly as WA1 committed it |

## Deliberate non-coverage

- No React component exists yet (`App.tsx`, the panels, `officePort.ts`, `fakePort.ts`): that is
  WA9. This slice has no Office.js dependency to mock, by design.
- `writeTemplate` is implemented and type-checked but has no dedicated test in this slice: it has
  no committed golden to compare against yet (the "Apply template" flow is a WA9 UI feature). It
  will be exercised indirectly once WA9's S9-03 ("Apply template on the licence") runs against it.
- The Playwright `e2e/` harness, `playwright.config.ts` and the `test`/`test:stack` scripts are not
  exercised in this slice (no `.spec.ts` files exist yet): WA9 adds the harness and the first
  Playwright-level tests (S9-xx).
