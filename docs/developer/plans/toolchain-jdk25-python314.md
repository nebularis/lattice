<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Toolchain: JDK 25 LTS and Python 3.14 — Plan

**Unit ID:** `toolchain-jdk25-python314`
**Status:** Executed — see [status](../status/toolchain-jdk25-python314.md)
**Decided:** 2026-09-23, with the human, while scoping [`identity-minting`](../sketches/identity-minting.md)

## Why

The identity-minting libraries pin their Unicode data to one version, and rely on each runtime's built-in NFC for code points assigned in that version. The pinned version is therefore capped by the oldest Unicode any supported runtime ships. On JDK 21 and Python 3.11 that was Unicode 14.0. JDK 25 (LTS) and Python 3.14 both ship Unicode 16.0, so the pair moves together. Newer JDKs (26, 27) would add nothing, because Python 3.14 sets the ceiling, and neither is LTS.

## Scope

- `mise.toml`: `java = "25"`, `python = "3.14"`.
- `platform/pom.xml`: `maven.compiler.release` 25.
- `.github/workflows/*.yml`: `python-version` and `java-version`.
- `requires-python = ">=3.14"` in every `pyproject.toml` (root, `tools/*`, `workers`).
- `requirements-lock.txt`: re-resolve under 3.14 and regenerate if needed.
- Current-state documentation that names the versions. Historical records (status, handoff, review, prompt records) are left as written.

## Validation

Baseline every check on the old toolchain, then re-run the same set on the new one and compare: `check:python-root`, `check:workers`, `check:persistence`, `build:mtp` then `check:mtp`, `check:spc`, `check:java` (including a clean build), plus a direct check that each runtime defines Unicode 16.0 characters. `check:frontend` is unaffected (Node is unchanged).
