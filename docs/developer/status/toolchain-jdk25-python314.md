<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Toolchain: JDK 25 LTS and Python 3.14 — Status

**Unit ID:** `toolchain-jdk25-python314`
**Status:** ✅ Complete (2026-09-23, autonomous mode)
**Plan:** [toolchain-jdk25-python314.md](../plans/toolchain-jdk25-python314.md)

## Is this unit complete?

**Yes.** Every repository check passes on JDK 25.0.2 and Python 3.14.7, with the same results as on JDK 21 and Python 3.11.

## Results

| Check | JDK 21 / Python 3.11 (baseline) | JDK 25 / Python 3.14 |
|---|---|---|
| `check:python-root` | pass (76 tests, Phase 8 conformance) | pass (same) |
| `check:workers` | 38 passed | 38 passed |
| `check:persistence` | 570 passed | 570 passed |
| `build:mtp` then `check:mtp` | `check:mtp` alone fails before `build:mtp` (pre-existing: the aggregate `check` task builds first) | pass; the rebuilt output is byte-identical to the committed output |
| `check:spc` | pass | pass |
| `check:java` | pass (19 `Tests run` report lines) | pass, identical reports; a clean build emits class files of major version 69 (Java 25) |

Unicode: Python 3.14.7 reports `unicodedata.unidata_version` 16.0.0. JDK 25.0.2 defines U+1C89 and U+10D40, both new in Unicode 16.0.

`requirements-lock.txt` resolves unchanged under 3.14, so only its header was updated.

## Changed

`mise.toml`, `platform/pom.xml`, both workflows, seven `pyproject.toml` files, `requirements-lock.txt` (header), and the current-state documents naming the versions: `docs/architecture/repository-delivery-foundation.md`, `solution-design-specification.md`, `decisions/ADR-A81-control-plane-http-runtime.md`, `docs/book.html`, `tools/README.md`, `docs/developer/plans/eligibility-compiler.md`, `docs/developer/plans/lattice-platform-agentic-development-v0.2.md` (P0.2.1).

## Not changed

Historical records that name Java 21 or Python 3.11 as they were at the time: status, handoff and review records, `.github/prompts`, `Architecture Review.md`, and `sketches/mtp-implementation-plan.md`.

## Noted in passing

`README.md` links to `docs/developer/toolchain.md`, which does not exist (pre-existing).
