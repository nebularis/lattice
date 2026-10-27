<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Surface Contract Studio

A single-page React application for authoring Surface contracts without editing Turtle. It is fixture-backed. The portfolio, the validation checklist and the diff are constants in `src/studio.tsx`, and nothing calls a service or saves to one. See [Surface Contract Studio](../../docs/architecture/surface-contract-studio.md) and [ADR-A38](../../docs/architecture/decisions/ADR-A38-surface-output-publication-and-studio-authoring-boundary.md).

## What it shows

- A portfolio of contracts with kind (Promotion, Index or Projection), carrier, profile and lifecycle state.
- A typed editor with carrier, target namespace and profile controls, and a property path builder in which steps can be added and removed.
- Index controls for membership assertions, `skos:broader` closure and a population budget.
- Projection controls for kind, required evidence, result target and deterministic-only lowering.
- A technical view that previews the Turtle declaration, an inspector with a law checklist, an impact preview and a revision diff, and a read-only MORK inspector for a Projection. Mapping activation cannot be requested from the Studio.

## Build, run and test

The app is a workspace of the repository's Yarn monorepo. Install the workspace once, then run through `mise`.

```bash
mise run bootstrap:frontend
mise exec -- yarn workspace @lattice/surface-contract-studio run dev
mise exec -- yarn workspace @lattice/surface-contract-studio run check
mise exec -- yarn workspace @lattice/surface-contract-studio run test
```

The first command installs the dependencies. The second serves the app at `http://127.0.0.1:4173`. The third type-checks it. The fourth runs the Playwright end-to-end tests, which start the dev server themselves and write results under `.build/surface-contract-studio-test-results`. `mise run check:frontend` and `mise run test:frontend` run the same scripts for every workspace. A pass is a zero exit status.

## Depends on

React 19, `lucide-react`, Vite and TypeScript. The tests use `@playwright/test`. It has no dependency on another workspace.
