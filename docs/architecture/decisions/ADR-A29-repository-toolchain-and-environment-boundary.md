<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# ADR-A29: Repository toolchain and environment boundary

**Status:** Accepted
**Date:** 2026-09-19
**Supersedes:** none
**Related:** Phase 0, [toolchain guide](../../developer/toolchain.md), [Windows and WSL guide](../../developer/windows-wsl.md)

## Context

LATTICE contains independent Python, Maven, Yarn, and Mix projects. Contributors need one discoverable entry point for tool versions and repository tasks, while each ecosystem must retain the lockfile and dependency mechanism expected by its native tooling. Windows development also needs a reproducible path for filesystem-sensitive and container-backed work.

## Decision

Use root `mise.toml` for tool-version selection, shared environment variables, and task aliases. Maven, Yarn through Corepack, pip or project virtual environments, and Mix remain dependency authorities. Dev Containers and Docker Compose provide the canonical service-backed environment. WSL2 with the repository stored in its Linux filesystem is the supported Windows path for that environment.

## Consequences

- `mise run` tasks are orchestration entry points. They must invoke native package managers and must not introduce a competing dependency lock.
- Each new subproject documents its authoritative manifest, lockfile, bootstrap command, validation command, and service requirements.
- The repository supports native macOS and Linux use, but native Windows is best effort until each required toolchain is demonstrated there.
- Configuration may be authored without network access, but validation status must identify unavailable runtimes, pulls, dependency resolution, and tests.
