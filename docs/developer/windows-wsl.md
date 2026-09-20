<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Windows and WSL

Use WSL2 with Docker Desktop's WSL backend for service, worker, and CI-parity development. Clone the repository in the Linux filesystem, for example `~/src/lattice`, and open that directory through VS Code Remote - WSL.

Avoid running the full stack from `C:\Users\...`. Windows-mounted worktrees have slower file watching and can cause symlink and container-mount inconsistencies.

From the WSL shell, run `mise install`, then `mise run bootstrap`. Start reference services with `mise run services:up`.
