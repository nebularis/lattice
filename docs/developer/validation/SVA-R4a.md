<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: SVA-R4a, the run contract corrected by its first client

**Unit:** [`studio-visual-authoring`](../status/studio-visual-authoring.md), slice SVA-R4a, built on 2026-11-16 in autonomous mode.

## Invariant

The contract says what a client of runs must know and do without reading the service's code. It states the shape of the event a frame arrives in, so a client reads the frame from `data` and recognises it by `type`. A client leaves the deadline to the service and times a run by a duration from sending its request, the kind's default plus a grace of 2 seconds, so no two clocks need to agree and the service's failed frame at the deadline can arrive before the client gives up. A failed last frame settles a run as failed whatever frames are missing before it, and only a `succeeded` last frame needs every frame from 0 to it. A waiting request may be abandoned. `more` is a hint, a part's `index` has no gap, and frames may reach a tab before the `202` ([ADR-A154](../../architecture/decisions/ADR-A154-runs-in-the-configuration-studio.md) decisions 6, 8 and 10). The client and the fake service follow it.

## What changed

- **`contracts/config-studio/README.md`, Runs.** The request's `deadline` and `wait` rows, the event's attributes in a table, `more`, `index` and a failed last frame in the frame tables, the new example, and "What a client must do" rewritten with the grace, the duration, the failed last frame, the early frames and the abandoned request. The limits table has the grace.
- **`contracts/config-studio/run-frame.schema.json`.** The descriptions of `more`, `message`, `status` and `index`. No constraint changed.
- **`contracts/config-studio/samples/run-frames-deadline.example.json`.** A run whose frame 2 was lost and whose last frame is the service's failed frame at the deadline.
- **`apps/config-studio/src/runs.ts`.** `assemble` gives `failed` for a failed last frame with a gap, with the parts whole before the gap. The controller sends no `deadline`, times a run by `DEADLINE_MS` plus `GRACE_MS` from the send, and reads no clock. `src/api.ts` takes `deadline` as optional and sends it only when given. `src/ui/RunPane.tsx` says that a failed run's parts are partial output.
- **`e2e/fake-service.ts`.** No change, since its route already accepted a request with no `deadline`.

## Tests

| ID | Given / When / Then | Level | The break tried | The failure it gave |
|---|---|---|---|---|
| R4a-T1 | the deadline example, read from disk / each frame validated / valid, with `seq` 0, 1, 3 and 4 and a failed last frame | L1 | | |
| R4a-T2 | the deadline example in any order and with duplicates / assembled / `failed` with the service's message and only the report part, as partial | L1, property | `runs.ts`, `assemble` treats a failed last frame with a gap as partial | 4 tests failed, this one among them |
| R4a-T3 | a failed last frame and one frame removed, 100 seeded runs / assembled / `failed`, with the parts whole before the gap, and the same run with a succeeded last frame is `partial` | L1, property | the same break | this one failed |
| R4a-T4 | the service's failed frame arrives one millisecond before the deadline plus the grace / the controller reads it / `failed` with the service's message, not `incomplete` | L1 | the timer is the deadline with no grace | this one failed |
| R4a-T5 | a failed last frame, with no frame before it / the controller reads it / `failed` with `partial` and no parts at once | L1 | the same break as R4a-T2 | this one failed |
| R4a-T6 | a succeeded last frame with a gap, the deadline passes / the grace passes / running, then `incomplete` | L1 | the timer with no grace | this one failed |
| R4a-T7 | a run starts / the request is read / no `deadline` is sent | L1 | | |
| R4a-T8 | a clock that throws, and a page clock an hour away / a run starts and its timer ends / `incomplete` after the default plus the grace, and no clock read | L1 | | |
| R4a-T9 | a simulate run / the timer runs / running one millisecond before 17 seconds, then `incomplete` | L1 | the timer with no grace | this one failed |
| R4a-T10 | a waiting request / the timer ends, or the controller is disposed / the request's signal is aborted | L1 | | |
| R4a-T11 | the permutation and duplication properties of R4 / run again / unchanged, since a generated run ends with a succeeded frame | L1, property | | |

**The existing tests changed, and why.** Each is a deliberate change of a stated behaviour, and none was weakened. The run controller's tests, all in `src/runs.test.ts`:

| Test | Change | Reason |
|---|---|---|
| `starts idle, sends a run with the tab, a deadline from the clock and no wait, and shows running` | asserts the query has no `deadline` | correction 3, a browser leaves the deadline to the service |
| `uses the kind's own deadline` | now `times a run by the kind's own default plus the grace`, asserting running until 17 seconds and `incomplete` at it | corrections 2 and 3, it asserted the `deadline` parameter |
| `gives incomplete at the deadline, listing what arrived and what is missing, and ends the wait` | the boundary moved from 119,999 and 120,000 milliseconds to the same plus the grace | correction 2 |
| `gives incomplete, with the service's own failure, for a last frame that came without the frames before it` | now `gives failed, with the service's own message, ...` and ends at once, with `partial` | correction 5, a failed last frame settles a run |
| `gives incomplete when the connection drops, the run is not sent again, and the run ends at its deadline` | advances the default plus the grace | correction 2 |
| `shows only the newest run: ...` and `sends the waiting request when the run in flight fails, is refused or is incomplete` | advance the default plus the grace where they advanced the default | correction 2 |

No test of `assemble`, of the browser or of the contract changed. The contract's tests gained one.

**Decisions the brief did not settle.**

- A failed last frame with a gap is its own assembly state, `failed`, where a failed last frame with every frame present stays `complete` with `status` `failed`, so no existing assertion on the second moved. The controller gives `failed` for both, and `partial` is set on the first only.
- The last part before a gap is not shown as whole, since the missing frames may continue it and `more` cannot be relied on. The deadline example therefore shows its report part only.
- The `clock` of the controller's dependencies is optional and unused, so callers that pass one are unchanged.
- `api.ts` is outside the files the brief named, and `startRun` needed `deadline` optional, so it changed by two lines.
- The fake service needed no change. The brief's four conditions on it did not arise.

**The one command:** `mise exec -- python -m pytest tools/test_config_studio_contract.py -q`, `mise exec -- yarn workspace @lattice/config-studio exec vitest run` and `mise exec -- yarn workspace @lattice/config-studio exec tsc --noEmit`, from the repository root.

## Artefacts to inspect

- "Runs" in `contracts/config-studio/README.md`, from "The request" to "Limits".
- `assemble` and `createRunController` in `apps/config-studio/src/runs.ts`.
- `contracts/config-studio/samples/run-frames-deadline.example.json`.

## Deliberate non-coverage

- **The service and the worker.** The service's collection of a waiting request's frames, its abandonment and its failed frame at the deadline are SVA-R2, and the worker's deadline is SVA-R3.
- **Frames over real MQTT.** Their order and loss are SVA-R5. The browser tests run the path that waits, whose `504` gives incomplete at once.
- **A browser test of the grace.** It would wait two seconds, and the unit tests hold the timing with fake timers.

## Results

What the builder ran on 2026-11-16, in autonomous mode:

- `pytest tools/test_config_studio_contract.py -q` printed 32 passed, 31 before and 1 new.
- `vitest run` printed 25 files and 433 tests passed, 427 before and 6 new in `runs.test.ts`.
- `tsc --noEmit` printed nothing.
- `playwright test`, with the temporary configuration that names the installed browser, printed 58 passed, none failed, once. The temporary configuration was deleted.
- Break 1, the controller's timer set to the deadline with no grace, failed 4 tests in `runs.test.ts`. Break 2, `assemble` treating a failed last frame with a gap as partial, failed 4 tests. Each was restored and `vitest run` printed 433 passed again.
