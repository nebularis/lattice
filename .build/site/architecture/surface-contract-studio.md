<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Surface Contract Studio

The Surface Contract Studio is the Phase 2 authoring workspace at `apps/surface-contract-studio`. It gives an author a typed route through Promotion and Index configuration without requiring direct Turtle editing. It is a work-focused editor, not a public landing page.

## Current Screens and Flows

The portfolio lists Surface contracts with kind, carrier, profile, and lifecycle state. Selecting one opens a typed editor with carrier, target namespace, and profile controls. Promotion uses the property path builder. Index adds population budget, membership materialisation, and `skos:broader` closure controls.

The inspector shows law checklist evidence, declared read-set impact, and a generated-output summary. Technical users can open an inspectable Turtle declaration preview. Draft save state is local fixture state until an HTTP adapter implements `contracts/openapi/surface-workflow.openapi.json`.

The E2E definition in `apps/surface-contract-studio/e2e/studio.spec.ts` verifies Promotion path editing, technical inspection, local draft save state, Index selection, and closure controls.

## API Boundary

The Studio must send typed revision transitions through the OpenAPI contract, including `expectedVersion`, and must handle `409` as either a stale-revision conflict or an invalid state transition. It must never submit RDF payloads, compiler commands, filesystem paths, broker credentials, or release-stack credentials.

Generated-output diff, impact preview, and law checklist will bind to immutable graph-family and worker-result descriptors. The UI does not calculate semantic parity or closure itself. It displays evidence returned by trusted control-plane and worker components.

## Build and Validation

The workspace uses React, Vite, Lucide, TypeScript, and Playwright. `yarn check` typechecks workspaces, `yarn build` produces the Studio bundle, and `yarn test` runs browser definitions. The package versions are declared exactly, but the root Yarn lockfile has not been regenerated in this restricted environment. Run `yarn install` in the validation environment, review and commit the resulting lockfile, then run check, build, and E2E commands without unrelated changes.
