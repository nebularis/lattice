<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: SVA-U1, collapsible and resizable columns

**Unit:** [`studio-visual-authoring`](../status/studio-visual-authoring.md), slice SVA-U1, built on 2026-11-16 in autonomous mode.

## Invariant

The author decides how the page's width is shared. The navigation, the mode's list column and the dock each collapse to a rail that holds only the button that brings the column back, and each returns. The boundary between the list and the middle and the one between the middle and the dock move within limits that keep every column usable, and a drag stops at a limit and never pushes content off the page. The choice is kept in this browser, once for the navigation and the dock and per view for the list, and nowhere else, so it never enters a graph and is never sent to the service. A browser that keeps nothing starts from the defaults and the page still lays out. All of it works from the keyboard, and a collapsed column holds nothing that Tab reaches.

## What changed

- **`src/ui/columns.ts`.** The pure part: the keys, reading and writing a column's state tolerantly (as `positions.ts` does), the limits, the clamping to a minimum and to what the window allows, the dock's default width and default state, and what a key does to a handle.
- **`src/ui/kit.tsx`.** `Split` (a view's list beside its middle, so a view gives the two parts it always did), `ResizeHandle` (a `separator` with its values in pixels), `CollapseButton`, and the hooks that follow the window and keep a column's state.
- **`src/ui/Workspace.tsx`.** The grid takes its navigation and dock widths from the kept state. The dock's header toggle and the dock's own button are one state. The Sample pane stays mounted while the dock is collapsed, so a run in flight is not lost.
- **The views with a list.** The six views that wrote a `.split` use `Split`, with their old widths as defaults.
- **`src/canvas/kit.tsx`.** A canvas that opens fitted is fitted again when its pane changes width.
- **`src/styles.css`, `RunPane.tsx`.** The two workarounds are gone, the dock's 620 px widening and the closed start below 1560 px, and so is the fixed dock overlay at 1100 px. The run pane stacks its controls above its displays by a container query where the dock is narrower than 480 px. `RunPane.tsx` needed no change.

## Tests

| ID | Given / When / Then | Level | The break tried | The failure it gave |
|---|---|---|---|---|
| U1-T1 | the three columns / a key is made / one for the navigation, one for the dock and one per view for the list | L1 | | |
| U1-T2 | a state written / read back, or nothing kept / the same state, or the defaults | L1 | | |
| U1-T3 | a stored value that is not JSON, not an object, or has a wrong type or a width that is not positive / read / ignored part by part | L1 | | |
| U1-T4 | a browser whose storage throws, or none / read and written / the defaults and no throw | L1 | | |
| U1-T5 | a stored width / resolved against the window and the other columns / raised to the minimum, lowered to what the window allows less the middle's minimum, the minimum where the window allows less | L1 | | |
| U1-T6 | the dock's defaults / resolved for several windows / wide only where the middle keeps 700 px beside it, collapsed only where the middle could not have its 360 px beside an open dock, the navigation and a list | L1 | | |
| U1-T7 | the keys of a handle / pressed / 16 px by the arrows, the minimum on Home, the maximum on End, stopping at the limits, other keys ignored | L1 | | |
| U1-T8 | a mapping workspace at 1440 by 900 with the Sample tab / each of the navigation, the list and the dock is collapsed and expanded by its button / `aria-expanded` follows, the column is a 36 px rail, the middle grows by more than 100 px and returns to its width, and the header toggle means the dock's own | L3 | | |
| U1-T9 | the same / the navigation and the list are collapsed / the mapping tree's right edge lies inside its container, nothing scrolls inside it and the run pane is whole beside it | L3 | `Workspace.tsx` and `kit.tsx`, a collapsed navigation and list keep their width | the right edge was 1497 where 1071.5 was the most |
| U1-T10 | the same / the dock's handle is dragged left, then far right, then left again / the dock grows by the drag, stops at 300, and its width and a collapsed list are the same after a reload | L3 | `kit.tsx`, a width is not written to the browser | after the reload the dock was 340 where 450 was kept |
| U1-T11 | the same / the handles are focused and keys pressed / Home and End reach the minimum and the maximum the handle names, the arrows move it 16 px in the direction of the boundary, and with all three columns collapsed 40 presses of Tab reach nothing inside a collapsed column | L3 | | |
| U1-T12 | 1100 px wide / the dock is opened with the Sample tab / no horizontal scroll bar, the dock starts collapsed, the controls are above the displays, and at 1920 px, with nothing kept, they are left of them | L3 | | |
| U1-T13 | the mapping canvas and the ontology drawing / columns are resized and collapsed / every node lies inside its pane | L3 | `canvas/kit.tsx`, the refit is switched off | the test failed |

**Decisions the brief did not settle.**

- The list column is kept per view, not per mode, since each view's list holds different things. Its limits are 220 px minimum and 280 px default, and the views that held an outline, 300 px and 460 px, and the mapping view, 280 px and 340 px, which were their old widths.
- The navigation is collapsed and expanded and not resized, since the brief names two boundaries.
- A collapsed list stays mounted and hidden (`hidden`), so what it holds, such as a filter or a sample being edited, is there when it returns, and nothing in it takes focus. The same holds for the dock's Sample pane.
- The dock's wide default of 620 px is for mapping mode only and needs the middle to keep 700 px beside it, from a window of about 1920 px. With only the 360 px minimum, the dock took 620 px at 1600 px and squeezed the mapping canvas, and an existing test that drags a link between its nodes failed, so the default was changed and the test left as it is. The default does not follow what is collapsed, so collapsing a column gives its room to the middle and never to the dock.
- The dock starts collapsed below 1176 px, the width the navigation, a list, a dock at its minimum and the middle at its minimum need.
- Where the window cannot give a column its minimum and the middle its minimum, the middle yields and the page does not scroll.
- The fixed overlay the dock had at 1100 px or less is removed, since the dock takes part in the grid and collapses.
- A canvas that opens fitted is fitted again when its pane changes width. It does not follow a height change, and a canvas that opens at its own viewport keeps it.

**The one command:** `mise exec -- yarn workspace @lattice/config-studio exec vitest run`, `mise exec -- yarn workspace @lattice/config-studio exec tsc --noEmit` and `mise run test:config-studio`, from the repository root.

## Artefacts to inspect

- `apps/config-studio/src/ui/columns.ts` and `Split`, `ResizeHandle` and `CollapseButton` in `apps/config-studio/src/ui/kit.tsx`.
- The page with every column open, with the navigation and the list collapsed, and with the dock dragged wide beside the canvas, at 1440 by 900.
- The `Canvas` refit in `apps/config-studio/src/canvas/kit.tsx`.

## Deliberate non-coverage

- **Touch devices.** The handle takes pointer events and keys, and a touch drag is not tried.
- **A column's height.** Only widths are shared.
- **The problems drawer's own height.** Unchanged.
- **Other windows' storage.** Two tabs of one browser share what is kept and the tabs do not follow each other until a reload.

## Results

What the builder ran on 2026-11-16, in autonomous mode:

- `vitest run` printed 25 files and 427 tests passed, 409 before and 18 new in `columns.test.ts`.
- `tsc --noEmit` printed nothing and exited 0.
- The browser suite on the fake service printed `58 passed (2.6m)` and, run again, `58 passed (2.7m)`, 52 before and 6 new. The first full run of the new tests had one existing test fail, the link drag on the mapping canvas, because the dock's wide default squeezed the canvas at 1600 px. The default was changed (see the decisions) and the test left as it is.
- The breaks of U1-T9, U1-T10 and U1-T13 were tried and restored, each test failing as the table says.
- Three screenshots at 1440 by 900 and a device scale factor of 2 were read: everything open, the navigation and the list collapsed, and the dock dragged wide beside the canvas. The rails and their buttons are tidy and the handles show as a small grip. The dock at its default 340 px stacks the run pane's controls above its displays, and the dragged-wide dock puts them on the left. The canvas drawing is whole in a narrow middle but small. Nothing is clipped.
