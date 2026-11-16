<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: SVA-B2c, the baseline is validated live and its findings reach the problems drawer

**Unit:** [`studio-visual-authoring`](../status/studio-visual-authoring.md), slice SVA-B2c, built on 2026-11-16 in autonomous mode.

## Invariant

The baseline is validated by the same machinery as a configuration part, after the same debounce, with at most one job in flight, a superseded result ignored, and the waiting ended and the job deleted when the workspace's view goes. It is validated again whenever the baseline changes and whenever the set of held import digests changes, since an import held or released changes the answer without the baseline changing. Its findings reach the problems drawer once, as a warning, and never turn the workspace's state to an error. The Baseline view keeps its own list of missing imports and does not show the finding a second time.

## What changed

- **`src/state.ts`.** `useValidation` takes a part or `baseline`, and is not copied. For the baseline it validates `state.baseline.graph`, sends it as the request body, depends on `heldImportsKey` of the summary's imports, and stores its result in `state.baselineValidation`. `issues` gains a `baseline` key beside the parts.
- **`src/api.ts`.** `submit` accepts `baseline` as a target.
- **`src/ui/Workspace.tsx`.** The problems drawer lists the baseline's findings, the Baseline entry of the navigation shows the warning badge, the pill counts them, and choosing a finding opens the Baseline view. A part's warnings are shown as a `warn` badge on the entry and a `warn` chip in the pill, and only a violation turns them to `bad`. The baseline's follow the same code.
- **`e2e/fake-service.ts`.** Answers `/api/publication-units` with an empty table, so the Publish view opens and offers the release of a held import. Its answer to a baseline validation already matched the Background of the brief, with the held imports read when the job runs, so it was not changed.
- **`src/state.test.ts`, `e2e/studio.spec.ts`, `README.md`.** Three unit tests, three browser tests and one sentence. No existing test was changed.

## Tests

| ID | Given / When / Then | Level | The break tried | The failure it gave |
|---|---|---|---|---|
| B2c-T1 | a workspace whose baseline imports an ontology no held import declares / it opens on another view / the drawer lists one `ImportNotHeld` warning naming the import, the Baseline entry shows a warning badge, the pill reads "1 warning", the submitted body is the baseline, choosing the finding opens the Baseline view, and that view lists the import as missing once and shows no `ImportNotHeld` | L3, positive | `state.ts`, the effect returns for the baseline so it is never submitted | the drawer held no `ImportNotHeld` finding, expected 1, received 0 |
| B2c-T2 | the same workspace / the import is held through the import dialog, then released from the Publish view / the warning and the badge go from the drawer with no save of the baseline, and come back after the release | L3, positive | `state.ts`, the baseline's dependencies replaced by a constant, so the held imports are not in the key | after holding, the drawer did not read "No problems in any part of the workspace." |
| B2c-T3 | the baseline's validation is held in the fake / the author leaves the workspace and comes back / one baseline validation is open, none after leaving, one again after coming back | L3, positive | not tried | |
| B2c-U1 to B2c-U3 | `state.test.ts` / `heldImportsKey` is empty for no imports and for a summary not yet read, changes when an import is held or released, and is the same for any order and for any other field of the imports | L1 | | |

B2c-T2 covers the release too, since the Publish view lists each held import with a way to release it. The Publish view needed the fake to serve its publication table, which was not served, so the view showed "not found".

**Decisions the brief did not settle.**

- A finding on the baseline opens the Baseline view as a whole, not the ontology node, since the finding's focus is an ontology and the view's list of ontologies is what names the missing import.
- The pill counts the baseline's warnings and violations with the parts'. Its "Validating" and "Validation unavailable" states are not extended to the baseline, so a service that refused the baseline target would show no change to the pill. A failed baseline validation is kept in `baselineValidation` and shown nowhere.
- A baseline validation request is made whatever the baseline holds, apart from an empty baseline, which conforms by definition as an empty part does.
- The Overview's finding count reads the parts only and was not changed.

**The one command:** `mise exec -- yarn workspace @lattice/config-studio exec vitest run`, `mise exec -- yarn workspace @lattice/config-studio exec tsc --noEmit` and `mise run test:config-studio`, from the repository root.

## Artefacts to inspect

- `useValidation` and `heldImportsKey` in `apps/config-studio/src/state.ts`.
- The problems drawer and the Baseline entry of a workspace whose baseline imports an ontology that is not held.

## Deliberate non-coverage

- **The real service.** Its validation of a baseline is exercised by the real-stack suite. These tests run on the fake service, whose answer was compared with the service's contract.
- **Timing.** The tests wait on conditions and assert no duration.
- **A failed baseline validation.** It is not shown.

## Results

What the builder ran on 2026-11-16, in autonomous mode:

- `vitest run` printed 22 files and 365 tests passed, 362 before and 3 new.
- `tsc --noEmit` for `@lattice/config-studio` printed nothing.
- The browser suite, with a temporary Playwright config that points at the Chromium already on this machine, deleted afterwards. Two full runs printed `41 passed (1.8m)` and `41 passed (1.7m)`, 38 before and the 3 new.
- The two breaks of B2c-T1 and B2c-T2 were made one at a time, each test was seen to fail as the table says, and each break was restored.
- Not run: `mise run check:config-studio` and `mise run test:config-studio` as written, and any run against the live stack.
