<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Plan: the build and its tests on Windows, Linux and macOS

**Unit ID:** `windows-portability`
**Prefix:** XP
**Status record:** [windows-portability.md](../status/windows-portability.md)
**Status:** built 2026-11-07, autonomously at the maintainer's request, each slice committed locally and nothing pushed. Handed back for review. [Validation Pack](../validation/windows-portability.md).

## Scope

`mise run bootstrap` and `mise run check` run the same way on Windows, Linux and macOS. A whole check on a Windows machine, after bootstrap and with `vyd` installed, failed six tasks for reasons unrelated to `vyd` itself: tests that assume a POSIX shell or file system, text written with the platform's line ending, a symlink Windows refuses without a privilege, a task missing a dependency, and a package the environment cannot install. Two multi-line `run` strings fail silently on Windows, since `cmd.exe` runs only their first line.

Python is the portable layer. A task that needs a shell feature, or reads or writes text where the encoding or line ending matters, runs a Python script (STD-322). A test skips only for a capability the environment cannot provide, named in its marker, never for the operating system (STD-323).

Out of scope:

- Вивід itself. Its encoding fixes are made upstream and brought here separately.
- `tools/claude-cloud-setup.sh`, which configures Claude's cloud environment and runs only in its Linux containers. It is not edited. Its tests are made to run under Git Bash on Windows.
- CI on Windows and macOS, until a CI provider is chosen.
- The reasoner's timeout under a whole parallel check (TD-153).

## Decisions taken

| # | Decision | Date |
|---|---|---|
| 1 | a task needing a shell feature, or text with a set encoding or line ending, runs a Python script, and Windows-only `run_windows` variants are replaced (STD-322, retiring STD-190) | 2026-11-07 |
| 2 | a test skips only for a missing capability, named, never for an operating system. `LATTICE_REQUIRE_ALL=1` turns every such skip into a failure (STD-323) | 2026-11-07 |
| 3 | tests that need `anthropic` skip where it cannot be installed, and run wherever it can | 2026-11-07 |
| 4 | `claude-cloud-setup.sh` stays as it is. Its tests run under Git Bash on Windows, and only if that proves impossible do they run on Linux alone | 2026-11-07 |
| 5 | what the `tools` domain's `mise` skill says about LATTICE's own build moves into LATTICE's additions, and the domain keeps what holds for any project using `mise` | 2026-11-07 |
| 6 | STD-322, STD-323 and STD-190's supersession are ratified. `skills:link` links on Windows too, by junction where a symbolic link is refused, and copies only where neither can be made | 2026-11-07 |

## Slices

| Slice | Delivers | Validation |
|---|---|---|
| **XP-0** | this plan, the status record, STD-322 and STD-323, STD-190 marked as superseded, TD-153 | `check:identifiers`, `check:knowledge` |
| **XP-1** | the `tools` domain's `mise` skill keeps what holds for any project, and LATTICE's additions (`.vyvid/skills/tools/mise.md`) take the rest, with STD-322's rule. The skills recomposed | `check:skills`, `check:agent-guidance` |
| **XP-2** | `check:mork` depends on `build:mtp`. The secret reader reads a file's own line ending, and its test writes bytes. `DocumentSchemaTest` compares text with line endings normalised. `agent_guidance.py link` makes a directory junction where Windows refuses a symlink. The git hook runs the first interpreter that starts, and its test checks git runs it rather than reading a POSIX mode bit | `check:mork`, `check:workers`, `check:java`, `check:agent-guidance`, `check:hooks` |
| **XP-3** | a `requires` marker in the shared test configuration, a skip that names the missing package, and `LATTICE_REQUIRE_ALL`. The tests needing `anthropic` declare it | `check:workers`, a run with `LATTICE_REQUIRE_ALL=1` failing on the skip |
| **XP-4** | `tools/test_vyvid_binding.py` runs `claude-cloud-setup.sh` under Git Bash on Windows: POSIX paths, a fake `mise` found on a POSIX `PATH`, and the background process checked from Python | `check:vyvid-binding` on Windows and Linux |
| **XP-5** | `build:persistence-execution`, `build:minting-vectors` and `clean` as Python scripts, and the `clean-win` tasks removed | each task run, and its output compared with the shell version's run under Git Bash |
| **XP-6** | a portability check in `check`: a multi-line or shell-dependent `run` string in `mise.toml`, and a text read or write without an explicit encoding under `tools/` | `check:portability` and its tests |
| **XP-7** | STD-322 and STD-323 ratified. `skills:link` makes a symbolic link, else a junction, else a copy, on every platform, and says which. [Directory links on Windows](../windows-links.md) explains junctions, what can refuse one and how to remove one. The `tools` domain's `windows` skill gains the rule, with its evidence as NOTE-14 and NOTE-15 | `check:agent-guidance`, `check:knowledge`, `check:skills` |

## Done when

`mise run --continue-on-error check` on Windows fails no task but for a skip STD-323 allows, named in its output, and the same tasks pass on Linux. `LATTICE_REQUIRE_ALL=1` fails that run on the skip.
