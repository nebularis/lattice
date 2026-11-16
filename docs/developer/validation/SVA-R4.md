<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: SVA-R4, the studio's run client and the run pane

**Unit:** [`studio-visual-authoring`](../status/studio-visual-authoring.md), slice SVA-R4, built on 2026-11-16 in autonomous mode.

## Invariant

A run's result is assembled the same from its frames in any order and with any duplicates, keeping the first frame seen for a sequence number, and it is complete only when a last frame is present and every number from 0 to its own is. A pane has one run in flight, and of the requests that come while it is, only the newest waits and is sent when the run ends. A run not complete at its deadline is incomplete, listing what arrived, and a frame of a run the pane no longer shows is ignored. The same assembly serves frames that reach the tab's events and the array a request that waits (`wait=true`) answers, so a tab with no events, or whose connection is down, gets the same state ([ADR-A154](../../architecture/decisions/ADR-A154-runs-in-the-configuration-studio.md) decisions 8, 9 and 10). Time is an input of the controller, through its clock and its timers.

## What changed

- **`src/runs.ts`.** `assemble` is a pure function of the frames, with the schema's rules that matter to assembly, and gives `complete`, `partial` (the missing numbers, the lowest absent number, and the outcome of a last frame that came without what it ends) or `invalid` with a reason. `createRunController` keeps the pane's numbering, the one run in flight, the newest waiting request, the deadline from the injected clock and timers, and the states `idle`, `queued`, `running`, `complete`, `failed`, `incomplete` and `refused`.
- **`src/events.ts`.** `onRunFrame` gives a listener the body of each run frame event, with no watch, and `tabId` the tab's identifier. `watch` and `connected` are unchanged.
- **`src/api.ts`.** `startRun` gives the run's IRI, the frames, the `504` of a deadline or a typed refusal.
- **`src/ui/RunPane.tsx`, `Workspace.tsx`, `MappingView.tsx`, `styles.css`.** The pane has controls on the left and a status line and the parts on the right. The dock of mapping mode has a Sample tab that runs the sample the view keeps when Run is pressed. The view's finding or making of a compilation moved into one function that the automatic sample run and the pane both call, with no change to when the automatic run happens.
- **`e2e/fake-service.ts`, `e2e/studio.spec.ts`, `README.md`.** Four switches of the fake (a status to refuse every run with, a failed last frame, a number of runs to end with `504`, and a delay), five browser tests, two rows.

## Tests

| ID | Given / When / Then | Level | The break tried | The failure it gave |
|---|---|---|---|---|
| R4-T1 | the frames of a run in any order, 200 seeded runs / assembled / the same result, with or without the run named | L1, property | | |
| R4-T2 | the same frames with any duplicates / assembled / the same result | L1, property | `runs.ts`, a later frame for a number replaces the first | none, the duplicates are identical, which R4-T3 covers |
| R4-T3 | a later frame for a number that differs from the first / assembled / the first is kept, whichever order they came in | L1 | `runs.ts`, a later frame for a number replaces the first | `keeps the first frame seen for a number and ignores a later one` failed |
| R4-T4 | a run with any one frame removed / assembled / partial, `next` is the removed number, `missing` names it when it is not the last, the parts are those before the gap | L1, property | `runs.ts`, the completeness check dropped | 5 tests failed, this one among them |
| R4-T5 | the two example runs of the contract, read from disk / assembled / the first is complete with a report part and an artefact part of two frames, the second is a failed run with its message | L1 | | |
| R4-T6 | frames of another run / assembled / ignored | L1 | | |
| R4-T7 | text split at code point boundaries, empty pieces and line ends / assembled / the exact concatenation | L1 | | |
| R4-T8 | each rule the assembler holds, such as a text with no part, a last frame with no status, an unknown role, two last frames, a frame after the last / assembled / invalid with a reason, never a throw | L1 | | |
| R4-T9 | a repeat on the same frames / assembled / the same result, and the frames unchanged | L1 | | |
| R4-T10 | the controller with fake api, events and timers / a run starts, frames arrive, the last one before one between / running with parts so far, then complete | L1 | the completeness check dropped | the test failed |
| R4-T11 | frames that arrive before the `202` returns / the IRI becomes known / frames of that run are read and those of other runs dropped, and the buffer holds at most 512 | L1 | | |
| R4-T12 | three quick starts / the first is sent, the second never, the third when the first ends, whether it was complete, failed, refused or incomplete | L1 | | |
| R4-T13 | a run that is no longer shown / its late frames arrive / ignored | L1 | | |
| R4-T14 | the deadline / it passes / incomplete, listing what arrived and what is missing, the wait aborted, and with the service's own failed frame when one came | L1 | | |
| R4-T15 | the connection drops in flight / the deadline passes / incomplete, and the run is not sent again | L1 | | |
| R4-T16 | events not connected / a run starts / sent with `wait`, the array assembled, and the state equal to the one frames over events give | L1 | | |
| R4-T17 | the `504`, an answer that is not a list, an answer that breaks the contract / handled / incomplete, failed, failed | L1 | | |
| R4-T18 | each of `429`, `409`, `404`, `400`, `413`, `415`, `503` and a request that fails / answered / refused with the status and text, and for `429` the `Retry-After` | L1 | | |
| R4-T19 | dispose / called in flight / the timers and the wait end, the queue is dropped, and nothing after is acted on | L1 | | |
| R4-T20 | `events.ts` / a run frame event arrives / its body reaches each listener, no watch is sent, a job's event wakes only its watcher, a listener that left hears nothing, and a listener that comes first opens the connection | L1 | | |
| R4-T21 | the Sample tab, nothing pressed / Run is pressed / nothing ran before, then running, then complete with the report and the artefact in order, with their text, path and group, from the compile job the status names | L3 | | |
| R4-T22 | the fake refuses every run / Run is pressed / refused (429) with the text and 3 seconds, then refused (409) with no wait | L3 | | |
| R4-T23 | the fake answers a failed last frame / Run is pressed / failed with its message | L3 | | |
| R4-T24 | the fake ends a waiting run with `504` / Run is pressed, then Run again / incomplete with Run again, then complete | L3 | | |
| R4-T25 | a workspace not in mapping mode / the dock opens / the Sample tab is not there | L3 | | |

**Decisions the brief did not settle.**

- `assemble(frames, run)` takes the run as an optional second argument. Without it the lowest run IRI among the frames stands for the run, so the result does not depend on their order. The controller always names the run.
- `received` counts the frames held, and the parts shown are those of the frames that follow one another from 0, so a part is never shown with a gap inside it.
- A part's `index` must be the number of parts before it, and a frame with text and no part must follow a part. A frame without `part` is taken to continue the current part whether or not the one before said `more`.
- A deadline that is a `504` for a request that waits is incomplete, as is one that passes with no frame at all.
- The frames that arrive before the `202` are kept for the first 512, whatever run they are of.
- A request that fails before an answer, such as a network error, is refused with status 0.
- The Sample tab sits beside the Inspector in the dock of mapping mode, and widens the dock. The dock is closed below 1560 pixels, as it was, so the tab is behind its toggle there. The pane stays mounted while the Inspector shows, so a run in flight and its result are not lost by looking at the Inspector.
- Run compiles through the view's cache, so a Turtle sample, which the automatic run dry-runs without compiling, is compiled when Run is first pressed.

**The one command:** `mise exec -- yarn workspace @lattice/config-studio exec vitest run`, `mise exec -- yarn workspace @lattice/config-studio exec tsc --noEmit` and `mise run test:config-studio`, from the repository root.

## Artefacts to inspect

- `assemble` and `createRunController` in `apps/config-studio/src/runs.ts`.
- `onRunFrame` in `apps/config-studio/src/events.ts` and `startRun` in `apps/config-studio/src/api.ts`.
- The Sample tab of the dock in mapping mode, `apps/config-studio/src/ui/RunPane.tsx`.

## Deliberate non-coverage

- **Frames over real MQTT.** Their delivery, loss and order through the broker are exercised by SVA-R5 on the real stack. The fake service offers no events, so the browser tests run the path that waits.
- **The service and the worker.** The service's route, its `202`, its limits and its deadline frame are SVA-R2, and the run worker is SVA-R3.
- **The output explorer.** The parts are shown as plain blocks. SVA-M4 replaces them.
- **The sample pane's own controls.** SVA-M3b.
- **Timing.** The unit tests use a fake clock and fake timers, and the browser tests wait on conditions and assert no duration.

## Results

What the builder ran on 2026-11-16, in autonomous mode:

- `vitest run` printed 24 files and 409 tests passed, 374 before and 35 new (33 in `runs.test.ts`, 2 in `events.test.ts`).
- `tsc --noEmit` for `@lattice/config-studio` printed nothing and exited 0.
- The browser suite, with a temporary Playwright config that points at the Chromium already on this machine, deleted afterwards. Two full runs printed `52 passed (2.3m)` and `52 passed (2.2m)`, 47 before and the 5 new. The test that fails now and then did not fail in either.
- Two breaks of `assemble` were made one at a time and restored. Taking the last frame seen for a number failed one test (R4-T3). Dropping the completeness check failed five (R4-T4 among them). Each was restored and the file compared with its copy.
- A screenshot at device scale factor 2 of mapping mode with the Sample tab open and a completed run, from a temporary test that was removed. Controls are on the left and the status line and the two parts in order on the right. The dock widens to 620 pixels with the tab, which squeezes the mapping tree beside it, whose right-hand column is cut off.
- Not run: `mise run check:config-studio` and `mise run test:config-studio` as written, and any run against the live stack.
