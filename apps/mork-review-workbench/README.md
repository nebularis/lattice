<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# MORK Review Workbench

A single-page React application that shows the MORK review bench. It is fixture-backed. The queue, the evidence and the ledger entries are constants in `src/main.tsx`, and nothing calls a service. See [MORK Review Workbench](../../docs/architecture/mork-review-workbench.md), [ADR-A42](../../docs/architecture/decisions/ADR-A42-mork-review-snapshot-and-decision-learning-boundary.md) and [ADR-A43](../../docs/architecture/decisions/ADR-A43-mork-replayable-queue-and-calibrated-governance.md).

## What it shows

- An atlas queue of sections, with a calibration panel in which bulk confirmation is disabled.
- An immutable snapshot with its witness, coverage and alternative evidence.
- The six typed decisions, Confirm, Retarget, Reshape, Decline, Teach and Defer. Choosing Reshape states that it gives structural feedback only and leaves projection statistics unchanged.
- A summary of boundary workflow, template by exception, replayable governance events and pack visibility, with MORK compact notation, lint diagnostics and pack internals marked as restricted to engineering roles.

## Build, run and test

The app is a workspace of the repository's Yarn monorepo. Install the workspace once, then run through `mise`.

```bash
mise run bootstrap:frontend
mise exec -- yarn workspace @lattice/mork-review-workbench run dev
mise exec -- yarn workspace @lattice/mork-review-workbench run check
mise exec -- yarn workspace @lattice/mork-review-workbench run test
```

The first command installs the dependencies. The second serves the app at `http://127.0.0.1:4174`. The third type-checks it. The fourth runs the Playwright end-to-end tests, which start the dev server themselves and write results under `.build/mork-review-workbench-test-results`. `mise run check:frontend` and `mise run test:frontend` run the same scripts for every workspace. A pass is a zero exit status.

## Depends on

React 19, `lucide-react`, Vite and TypeScript. The tests use `@playwright/test`. It has no dependency on another workspace.
