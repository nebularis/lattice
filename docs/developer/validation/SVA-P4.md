<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: SVA-P4, the persistence simulator pane

**Unit:** [`studio-visual-authoring`](../status/studio-visual-authoring.md), slice SVA-P4, built on 2026-11-19 in autonomous mode, from section 8.2 of the [sketch](../sketches/studio-visual-authoring.md) and ADR-A154 decisions 8, 9 and 11.

## Invariant

The simulator's state is the tab's. A sample world, one per workspace and tab, is TriG with the steps that made it, and a step's request is built from the world, the object, the operation and the compiled profile alone, so the same step sent twice is the same request. Nothing runs until the author presses Run, one step runs at a time, and the world moves forward only when a step's outcome is applied. The delta lights a canvas place when one of its `dal:GraphPlace` IRIs and its role equal a delta place's, never by a graph name's pattern.

## What changed

- `ui/SimulatorPane.tsx`, a Simulator tab in the persistence view's dock beside the canvas, on the run pane's shell. Controls on the left: the object as a form derived from the boundary shape or as Turtle typed or from a file, filled from the world on request, the operation, as another writer, the transaction time, Run and Step back, and the world's size against the 5 MiB request limit. Displays on the right: the checks, the request as it ran, the delta by landing place with the graphs no place states, and the outcome with its cause, engine and revision.
- `persistence/simulator.ts` builds a step's TriG, `simulatorStore.ts` holds the world in the tab's memory, `objectForm.ts` derives the form, and `compilation.ts` is the compilation read the canvas and the simulator share. `landing.ts` keeps each place's IRIs and role, and each operation's parameters, payload parameter and bindings.
- The contract's section on a persistence step says what the studio's simulator sends. The step number is the world's steps plus one, so a lost race adds none and a step resent is the same. The new revision and transaction id are minted from the root's local name and the step number, other IRI parameters as `urn:simulator:{name}/{n}`. The epoch is the dataset's where the profile binds one, then the row's, then 1. The expected position is the root's, one less as another writer. A delta replace's assert and retract triples are the object against the stored aggregate, read through the compiled profile's owned edges. The transaction time is stated by the author and defaults to a fixed time, never the clock.
- Operations are limited to those of the compiled profile a step runs. Append is offered and disabled, since a step does not run an append-versions write. Where a delta replace and a whole replace both serve a replace, the delta replace is the default.
- The journey's fixture, `e2e/fixtures/simulator-facility-journey.json`, holds the bodies the browser builds and the frames the real run worker gives for them. `SimulatorJourneyTest` in the run worker fails when the worker's frames differ, and `simulator.journey.test.ts` fails when the browser's bodies differ. No frame was written by hand. The fake service answers a step only when its body equals a fixture's.

## Tests

| ID | Given / When / Then | Level | The break tried | The failure it gave |
|---|---|---|---|---|
| P4-T1 | a create, a delta replace, a whole replace and a tombstone / built / the TriG of the contract's samples and of the run worker's tests | L1 | | |
| P4-T2 | the same step twice, and a lost race / built / the same TriG, and no step added | L1 | | |
| P4-T3 | a world of several steps / step back / the world before the last step | L1 | | |
| P4-T4 | a delta / lit / the canvas places whose IRI and role match, and a place two targets share lit once | L1 | | |
| P4-T5 | the journey's steps / built and checked against the fixture, and run by the run worker / the fixture's bodies and frames | L1 | | |
| P4-T6 | the facility sample on the fake service / the simulator creates a facility, changes it, loses a race as another writer and steps back / each step's displays, the canvas lighting each place a step wrote, and the world back to one step | L2 | | |
| P4-T7 | a world in the simulator / the author opens another view and returns, then gives an object as Turtle / the world is kept and the Turtle is used | L2 | | |

## Checks run

| Command | Result |
|---|---|
| `tsc --noEmit` in `apps/config-studio` | exit 0, nothing printed |
| `vitest run` | 33 files, 538 tests passed |
| the Playwright journeys on the fake service, all 69 | 69 passed |
| `mise exec -- mvn -o -f platform/pom.xml -pl config-studio-transforms -am verify` | BUILD SUCCESS, 0 failures and 0 errors |
| `mise run check:identifiers`, `check:catalogue` | passed, run by the delegated developer |

The first four were run by the delegated developer and again by the reviewer. The journeys ran from a configuration outside the commit pointing Playwright at the container's older Chromium, as SVA-P1b's did.

## Left open

- The form writes no inverse edge, and the facility sample's `DrawdownShape` has no `drawnUnder`, so a drawdown made in the form lacks the back-reference. Turtle can carry it, and the payload check passes without it.
- At 1600 pixels wide the dock stacks the controls above the displays. The author can widen it.
- A reload loses the world, as SVA-Q3 intends.

## Placement

T0. The studio's code and contract are open.
