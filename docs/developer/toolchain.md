<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Toolchain

`mise` is the repository entry point for tool versions, shared environment variables, and task aliases. Maven, Yarn, pip, and Mix remain the dependency authorities for their projects.

Run `mise install` to install declared toolchains. Then use `mise run bootstrap` to install project dependencies and `mise run check` to execute the repository checks. The bootstrap task needs network access and is intentionally not run in restricted authoring environments.

The Java reactor is under `platform/` and uses its Maven Wrapper. The Yarn workspace is reserved for applications under `apps/` and shared packages under `packages/`. The root Python environment validates ontologies and compiler sources. `workers/` is a separate deployable Python package.
