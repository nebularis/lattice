<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: WA9a, Ribbon and right-click commands

**Unit:** `word-authoring-poc` (WAP), ADR-A114
**Plan:** [word-authoring-poc.md](../plans/word-authoring-poc.md) section "WA9a: Ribbon and right-click commands"
**Status record:** [word-authoring-poc.md](../status/word-authoring-poc.md)

## Invariant

An author can mark up a document without opening the task pane: select text, then either click a
ribbon button or pick a right-click item, and the mark happens (or the author is told exactly why
not). Decision WA-D13 (a shared runtime) means the commands and the task pane run in the same
JavaScript context, so a command needing input (a variable's key and type, or which definition a
term refers to) can hand the task pane a filled-in draft rather than failing or guessing. No
command ever leaves Word waiting: every handler calls `event.completed()`, in a `finally` block,
whether it succeeded, found nothing to do, or threw.

## Test case table

| ID | Given / When / Then | Level | Invariant protected | Pass criterion | +/- |
|---|---|---|---|---|---|
| S9a-01 | the manifest / parsed / a V1_1 override requiring `SharedRuntime` 1.1, one long-lived runtime, the function file and every `ShowTaskpane` on `Taskpane.Url`, eight controls in `LatticeGroup`, six items under `ContextMenuText`, `FunctionName`s equal to `COMMAND_IDS` without `showPane`, every `resid` defined and at most 32 characters | L1 | the manifest Office actually loads matches what the commands expect to be associated with | `manifest.test.ts`'s 7 new tests pass | + |
| S9a-02 | `registerCommands` with an `Office.actions.associate` stub | L1 | every command id gets exactly one association, never zero, never two | `register.test.ts` passes | + |
| S9a-03 | the handlers over the fake port, a valid selection; a port that throws | L1 | a command always calls `event.completed()` exactly once, success or failure, and a thrown error still reaches the author as a message | `handlers.test.ts`'s 5 tests pass | +/- |
| S9a-04 | a selection `GBP 250`; an empty selection | L1 | `markVariable` never marks text itself; it only ever proposes a draft for the author to confirm | `handlers.test.ts`'s `markVariable` tests pass | +/- |
| S9a-05 | the facility sample, `markDefinedTerm` on `Loans`, then on `Agent` | L1 | a plural or possessive selection still finds its definition; an unmatched selection never marks anything | `handlers.test.ts`'s `markDefinedTerm` tests pass | +/- |
| S9a-06 | `suggestKey` and `guessValueType` against every case of `suggested-keys.json` | L3 | the ribbon's key and type guesses agree exactly with the Java detector (S3-02), not just approximately | `keys.test.ts` (7 cases) passes | + |
| S9a-07 | the harness, a selection over `GBP 250`, `__harness.command("markVariable")`, then Mark variable | L6 | the whole bridge round trip works end to end in a real browser, not just in isolated unit tests | `S9a-07` passes | + |
| S9a-08 | the harness, `__harness.command("analyse")` | L6 | the Analyse command reaches the real `handleAnalyse` even though it runs inside a `useEffect` closure registered once at mount | `S9a-08` passes | + |

77 tests in total for the add-in workspace (69 Vitest: 45 from WA8/WA9 plus 24 new — `keys.test.ts`
7, `register.test.ts` 1, `handlers.test.ts` 9, `manifest.test.ts` 7 new; 13 Playwright: 11 from WA9
plus 2 new). All pass.

## One command

```
mise run test:authoring-addin
```

## Artefacts to inspect

- [`apps/word-authoring-addin/src/commands/handlers.ts`](../../../apps/word-authoring-addin/src/commands/handlers.ts), [`register.ts`](../../../apps/word-authoring-addin/src/commands/register.ts), [`ids.ts`](../../../apps/word-authoring-addin/src/commands/ids.ts)
- [`apps/word-authoring-addin/src/app/uiBridge.ts`](../../../apps/word-authoring-addin/src/app/uiBridge.ts)
- [`apps/word-authoring-addin/src/domain/keys.ts`](../../../apps/word-authoring-addin/src/domain/keys.ts)
- [`apps/word-authoring-addin/manifest/manifest.xml`](../../../apps/word-authoring-addin/manifest/manifest.xml) (the nested `VersionOverridesV1_1`)
- [`docs/architecture/ux-design.md`](../../architecture/ux-design.md) section 4.6

## Self-probe

Plan: "move `event.completed()` out of the `finally` block into the success path. S9a-03's
throwing case fails."

Moved it into the `try` block, right after `await action()`, in `handlers.ts`'s shared `run`
helper. Ran `handlers.test.ts`'s throwing-port test alone: it failed exactly as predicted
(`completedCount()` was `0`, not `1`, since the thrown error skips the line after `await action()`
entirely). Reverted; the full suite (69 Vitest, 13 Playwright) passes again. The fourth slice
running (after WA7, WA8, WA9) whose prescribed self-probe bites exactly as written, with no
replacement test needed.

## Implementer choices

| Choice | Reasoning |
|---|---|
| `FakeWordPort` gained `selectUnmarked(sectionKey, text)` and a real `wrapSelectionAsElement` implementation (previously a stub always returning `outside-section`, per WA9's own documented gap) | WA9a's `markClause`/`markDefinition` handlers are the first thing in this unit that actually exercises marking *unmarked* text into a new element, so the fake port needed a genuine implementation, not just a shape. Closes the gap WA9's Validation Pack flagged under "Deliberate non-coverage" |
| `App.tsx`'s bridge subscription calls `handleAnalyseRef.current()`, a ref kept fresh by an unconditional `useEffect`, rather than calling `handleAnalyse()` directly | found as a real bug, not predicted: the subscription effect only runs once (`[bridge]` never changes), so a direct call closed over the *initial* (`null`) `metadata` forever. The `analyse` ribbon command's own S9a-08 e2e test caught this; the ref pattern is the standard fix for a stale closure inside a long-lived subscription |
| `markDefinedTerm`'s "term equals the text, or the text without a final suffix" tries `'s`, `\u2019s`, then plain `s`, longest first | matches the plan's own wording literally ("a final `s`, `'s` or `’s`"); trying the two-character suffixes before the one-character `s` avoids stripping only the `s` of a `'s` and comparing against the wrong remainder |
| The four new icon colours (purple, orange, green, grey) are generated once by the same throwaway, not-committed Python snippet WA8 and WA9 used, not hand-drawn | keeps every icon-writing step in this unit identical and auditable; `markClause`'s and `showPane`'s icons reuse WA8's existing blue set rather than duplicating it, since they are the same colour |
| The V1_1 override's `showPane`-equivalent control uses a distinct id (`ShowPaneButton1`) and `TaskpaneId` (`ButtonId2`) from the outer V1_0 button | Word manifests require unique ids across the whole document; the two overrides coexist (a build without the shared runtime falls back to V1_0), so their ids must not collide even though they represent "the same" button conceptually |

## Deliberate non-coverage

- Keyboard shortcuts are explicitly out of scope (plan: "Word's support for add-in shortcuts would
  need checking first").
- `unmarkSelection`'s exact reason mapping when nothing is marked is still not pinned by any test
  (carried over from WA9); WA9a's own `unmark` test only exercises the already-marked case.
- The manifest's per-command tooltips (`bt:LongStrings`) are not individually asserted beyond the
  generic resid-definition check in S9a-01; a reviewer should read them directly in
  `manifest.xml`.
