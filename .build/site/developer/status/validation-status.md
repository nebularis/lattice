<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Implementation Validation Status

**Status:** Accepted with recorded residuals
**Governing ADR:** [ADR-A29](../../architecture/decisions/ADR-A29-repository-toolchain-and-environment-boundary.md)

Date: 2026-09-20  
Implementation merge: `ba04e5611efa39ec8d5cf753e854f5fa3e09d007`  
Validation baseline revision: `25bc56b050d5dc7853d37c09b03ab1cb2f989532`

## Purpose

This record tracks validation of the authoring-complete Phase 0 through Phase 6 implementation. Architecture documents describe intended behavior. This file records observed validation evidence and bounded blockers.

The handover's new Phase 7 compiler and SPC work is out of scope until Phases 0 through 6 are validated and accepted.

## Host Baseline

- Host: macOS Darwin 23.6.0, Apple arm64
- Existing unrelated worktree change: `docs/_includes/theory/00-thesis.md`
- Python: 3.9.13, below the repository's canonical Python 3.11
- Java: OpenJDK 24.0.1, not the pinned Java 21
- Maven: available through Homebrew, version validation pending
- Node: 24.2.0, not the pinned Node 22
- Corepack: available
- Missing from `PATH`: `mise`, `yarn`, `docker`, `oras`, `cosign`, `jq`

## Stabilisation Controls

- `.github/workflows/platform.yml` is retained but manual-only.
- `.github/workflows/phase8-conformance.yml` is retained but manual-only.
- Workflows remain manual until package locks, tool versions, and their command matrices pass locally or in the canonical Dev Container.

## Evidence Log

| Area | Command | Result | Evidence or blocker |
|---|---|---|---|
| Baseline | `git rev-parse HEAD` | Recorded | Current revision above; implementation merge confirmed in history. |
| Host tools | executable and version inventory | Blocked | Canonical tool versions are not currently installed. |
| Worktree | `git status --short` | Recorded | One pre-existing theory edit is outside this validation work and must not be reverted. |

## Status Vocabulary

- **Not run**: no command has executed.
- **Blocked**: a named prerequisite prevents execution.
- **Failed**: the command executed and returned a defect.
- **Passed**: the command executed successfully with evidence.
- **Accepted residual**: a bounded limitation is explicitly accepted for Phase 0-6 validation.

## Next Gate

1. Install and validate `mise`.
2. Install the pinned Java, Maven, Node, and Python versions through `mise`.
3. Repair dependency locks before running repository-wide checks.
4. Validate or move into the canonical Dev Container for Docker-backed integration.
