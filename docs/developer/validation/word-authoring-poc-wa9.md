<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: WA9, Add-in task pane and harness

**Unit:** `word-authoring-poc` (WAP), ADR-A118
**Plan:** [word-authoring-poc.md](../plans/word-authoring-poc.md) section "WA9: Add-in task pane and harness"
**Status record:** [word-authoring-poc.md](../status/word-authoring-poc.md)

## Invariant

The task pane is the one place a drafter sees the whole loop close: mark text in Word, submit it,
see what the platform made of it, and accept its suggestions back into the document. Every panel
is a plain function of the same `DocumentPort`/`ApiClient` seam WA8 defined, so the harness
(`FakeWordPort`, mocked HTTP) and the real add-in (`OfficeWordPort`, real Word, real service) run
the identical `App` component. Nothing the add-in shows is computed by trusting a server response
blindly: every mark goes through the `MarkResult` reason path, every poll has a timeout, and every
piece of document or API text reaches the screen as React text, never as HTML.

## Test case table

| ID | Given / When / Then | Level | Invariant protected | Pass criterion | +/- |
|---|---|---|---|---|---|
| S9-01 | the fake port / mark inside a literal, across two parts, inside a variable, with no selection, an unknown element | L1 | marking never corrupts the part model and never marks over an existing mark | `fakePort.test.ts` (5 tests) passes | +/- |
| S9-02 | the harness with health ok | L6 | the Document tab reflects the real connection and catalogue state, not a stub | `S9-02` passes | + |
| S9-03 | Apply template on the licence | L6 | a freshly applied template has exactly the sections and (empty) elements the template declares, in order | `S9-03` passes | + |
| S9-04 | Insert sample facility | L6 | inserting a sample reproduces its sections, variables and gets a fresh document identity | `S9-04` passes | + |
| S9-05 | select `GBP 250` in element 11, Mark variable `prepayment-fee`/money | L6 | the chosen value type reaches the declared variable, not a default | `S9-05` passes | + |
| S9-06 | Analyse the facility sample | L6 | Analyse submits exactly one well-formed request and shows what the service answered | `S9-06` passes | + |
| S9-07 | Accept on `[Agent]` | L6 | accepting a detection marks the exact occurrence the detection named, by translating its offset through `occurrenceIndex` | `S9-07` passes | + |
| S9-08 | a completed job, Logical English tab | L6 | every element of the analysis is shown, with its own role legend | `S9-08` passes | + |
| S9-09 | Graph tab, Turtle toggle | L6 | the diagram's node count matches the graph view exactly | `S9-09` passes | + |
| S9-10 | health failing, then a 500 | L6 | the user is always told, in words, when something is actually wrong | `S9-10` passes | - |
| S9-11 | `pollTimeoutMs=1000`, a job stuck `queued` | L6 | the UI never hangs waiting on a job forever | `S9-11` passes | - |
| S9-12 | `main.tsx`'s requirement check, `Office` stub answering false | L1 | the add-in never runs against a Word host too old for its own API calls | `main.test.ts` (2 tests) passes | - |
| S9-13 | a malicious element text | L8 | document text is never interpreted as markup | `S9-13` passes | - |

38 WA8 Vitest tests plus 7 new (`fakePort.test.ts` 5, `main.test.ts` 2) = 45, all pass. 11
Playwright tests, all pass.

## One command

```
mise run test:authoring-addin
```

(`check:authoring-addin` first: `tsc --noEmit` and `vitest run`, 45 tests; then the Playwright
suite, 11 tests, against a real `msedge` channel and the dev server.)

## Artefacts to inspect

- [`apps/word-authoring-addin/src/app/App.tsx`](../../../apps/word-authoring-addin/src/app/App.tsx) and the five panel components beside it
- [`apps/word-authoring-addin/src/word/fakePort.ts`](../../../apps/word-authoring-addin/src/word/fakePort.ts) and [`officePort.ts`](../../../apps/word-authoring-addin/src/word/officePort.ts)
- [`apps/word-authoring-addin/src/main.tsx`](../../../apps/word-authoring-addin/src/main.tsx) and [`harness.tsx`](../../../apps/word-authoring-addin/src/harness.tsx)
- [`apps/word-authoring-addin/e2e/taskpane.spec.ts`](../../../apps/word-authoring-addin/e2e/taskpane.spec.ts) and [`support.ts`](../../../apps/word-authoring-addin/e2e/support.ts)
- [`docs/architecture/ux-design.md`](../../architecture/ux-design.md) section 4

## Self-probe

Plan: "render span text with `dangerouslySetInnerHTML`. S9-13 fails."

Changed `LogicalEnglishPanel`'s tail-text branch (the one that renders an unmatched element's
whole text, exactly S9-13's case) from `<span>{text}</span>` to
`<span dangerouslySetInnerHTML={{ __html: text }} />`, and ran S9-13 alone. It failed: the
malicious string stopped appearing as literal text (the browser parsed it into a real, textless
`<img>` element instead), which is the vulnerability made visible rather than hidden. Reverted;
the full suite (45 Vitest, 11 Playwright) passes again. The third slice running (after WA7, WA8)
whose prescribed self-probe bites exactly as written, with no replacement test needed.

## Implementer choices

| Choice | Reasoning |
|---|---|
| `writeTemplate`'s placeholder element carries a single space, not a literally empty paragraph | an empty paragraph round-trips to zero parts and gets dropped by the parser's own "empty literals are dropped" rule (WA8, confirmed by S8-04); `LiteralPart.text` also requires at least one character. A single space is schema-valid and survives, while reading as empty to the author |
| `HttpApiClient`'s default `fetchImpl` wraps the global `fetch` in an arrow function, not a bare reference | the native `fetch` throws "Illegal invocation" when extracted from `window` and called as `this.fetchImpl(...)`, since its implementation relies on internal slots only the literal global call site has. Found by running the harness in a real browser, not by reasoning about it in the abstract |
| `officePort.ts` uses the real `Word`/`OfficeExtension` ambient types `@types/office-js` declares, not a hand-rolled local surface | an earlier draft assumed (wrongly) that `@types/office-js` only covered the common `Office.*` surface; it in fact declares the full Word object model (`declare namespace Word` at line 95517 of its `index.d.ts`). Verified by grep before committing to either approach, since officePort.ts can never be exercised by a test that would catch a wrong guess |
| `Accept` on a detection goes through `occurrenceIndex` before calling `markOccurrence` | a `Detection`'s `start`/`end` are absolute element-text offsets (plan WA1), but `markOccurrence`'s Office.js implementation can only address a search result by occurrence count, matching `officePort.ts`'s `search()`-based design. `occurrenceIndex` (domain/offsets.ts, WA8) is exactly the bridge between the two addressing schemes |
| The Markup panel's "Mark variable" value type is threaded through `handleMark`'s second, optional parameter rather than added to `InlineMark` | `InlineMark`'s `variable` case (`word/port.ts`, fixed by the plan's own code block) carries only `variableKey` and `label`; the chosen value type is purely a detail of *how a new declaration gets recorded*, not of what gets written to the document, so it travels beside the mark rather than inside it |
| The Graph tab's Mermaid SVG is inserted via `dangerouslySetInnerHTML`, the one deliberate exception to "never render document or API text as HTML" | Mermaid's own `securityLevel: "strict"` sanitizes node labels before they reach the SVG string; there is no supported way to get a React element tree out of `mermaid.render` instead. Documented in `ux-design.md` so the exception is visible, not silent |
| `e2e/support.ts`'s JSON schema imports needed `with { type: "json" }` import attributes | `schemas.ts` is loaded two ways: bundled by Vite for the app (which accepts bare JSON imports) and loaded directly by Playwright's own Node-based test runner (which, under Node 22's ESM loader, requires the import attribute for JSON). Adding it satisfies both; found by running the real Playwright suite, not by reasoning about module resolution in the abstract |

## Deliberate non-coverage

- `wrapSelectionAsElement` (the "Clause"/"Definition" buttons) has no S9-level test: no S9 test
  case exercises marking *unmarked* text into a new element, since the fake port's selection model
  (`select(elementId, start, end)`, matching the plan's own wording) only ever addresses an
  *existing* element's text. `FakeWordPort.wrapSelectionAsElement` always returns
  `outside-section` as a result. A later slice should extend the fake port's selection model to
  also address unmarked text if this path needs real coverage.
- `unmarkSelection`'s exact reason mapping ("nothing marked here" returns `outside-element`, not a
  dedicated reason) is an implementer choice with no test pinning it, since no S9 case exercises
  Unmark on a part that was never marked.
- `officePort.ts` is never executed: no test harness here has access to a real Word host. Its
  correctness rests on type-checking against the real `Word` namespace (see "Implementer choices")
  and on the Playwright suite's own, functionally identical exercise of every `DocumentPort`
  method through `FakeWordPort` instead.
