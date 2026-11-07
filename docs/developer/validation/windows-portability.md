<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: the build and its tests on Windows, Linux and macOS, XP-0 to XP-7

**Unit:** [`windows-portability`](../status/windows-portability.md)
**Plan:** [windows-portability.md](../plans/windows-portability.md)
**Decisions:** the maintainer's answers of 2026-11-07, recorded in the plan. STD-322 and STD-323 ratified 2026-11-07

## Invariant

`mise run bootstrap` and `mise run check` do the same on Windows, Linux and macOS. A task needing a shell feature, or text with a set encoding or line ending, runs a Python script (STD-322). A test skips only for a Python package the environment cannot provide, named in its marker and in the run's last line, never for its platform, and `LATTICE_REQUIRE_ALL=1` fails it instead (STD-323). `tools/claude-cloud-setup.sh` is not changed.

## Test cases

| ID | Given / When / Then | Level | +/- | Result |
|---|---|---|---|---|
| XP2-01 | a fresh checkout without the Teaching Pack output / `check:mork` and `check:workers` / `build:mtp` runs first | L4 | + | pass |
| XP2-02 | a secret file ending `\r\n`, `\n` or `\r\r\n`, written as bytes / read / one line ending dropped, nothing else | L1 | +/- | pass |
| XP2-03 | Trang run on Windows / `DocumentSchemaTest` / matches the committed XSD with line endings normalised | L3 | + | pass |
| XP2-04 | Windows refusing a symlink / `agent_guidance.link` / a junction, the skill read through it, the link removed and the skill kept | L4 | + | pass |
| XP2-05 | the installed hook, `mise` off the path, Windows' `python3` a stub / commit a denied term / refused by the dispatcher on the first Python that starts | L5 | - | pass |
| XP2-06 | a fake `vyd` as a Python script with a `.cmd` or `sh` launcher / a `vyd` that did not run / skipped with its reason, on Windows too | L4 | + | pass |
| XP3-01 to XP3-03 | a test marked `requires` / its package missing, present, or missing with `LATTICE_REQUIRE_ALL=1` / skipped naming it and counted at the end, run, or an error | L1 | +/- | pass |
| XP3-04 | `anthropic` refused by this mirror / `check:workers` / the one test that makes its client skipped, the rest of provider selection run | L4 | + | pass |
| XP4-01 | `claude-cloud-setup.sh` unchanged / its session, deferral and time-limit tests under Git Bash / every path POSIX, every file `\n`, the background process asked through bash | L4 | + | pass |
| XP5-01 | `build:persistence-execution` / bash and Python / the same 401 files byte for byte | L3 | + | pass |
| XP5-02 | `build:minting-vectors` / bash and Python / the same 22 files, the committed copies unchanged | L3 | + | pass |
| XP5-03 to XP5-08 | a scratch tree / each clean area / removes what the old tasks did, keeps a results folder's dotfiles, never walks `.venv`, removes a link and never its target, removes a read-only file, skips a missing path | L1 | +/- | pass |
| XP6-01 to XP6-09 | a `run` with a multi-line script, `rm`, `cd`, `&&`, `;`, a pipe, a redirect, a glob or a variable / the check / refused, naming the feature | L1 | - | pass |
| XP6-10 | plain commands, an array, a template, `dir` / the check / passes | L1 | + | pass |
| XP6-11 | `run_windows` / the check / refused unless listed with its reason | L1 | +/- | pass |
| XP6-12, XP6-13 | text calls and skips in source / the check / unencoded calls and skips on the platform found, bytes and package skips not | L1 | +/- | pass |
| XP6-14 | the baseline / a file gains, a new file, a file loses / refused, refused, asked to lower the baseline | L1 | +/- | pass |
| XP6-15 | this tree / `tools/portability.py` / no problem | L4 | + | pass |
| XP7-01 | a symbolic link refused with error 1314 / `link_directory` / a junction made | L1 | + | pass |
| XP7-02 | no link can be made / `agent_guidance.link` / each skill copied with its marker, and linked on the next run once linking works | L1 | +/- | pass |
| XP7-03 | an unelevated Windows account / `agent_guidance.py link` into a scratch folder / a junction for each of the 15 skills, reported as such | L4 | + | pass |

## One command

```bash
mise run --continue-on-error check
```

Run on Windows 2026-11-07 with an editable Вивід 0.2.15, every task passed but `check:workers`, which read the Teaching Pack before `build:mtp` wrote it. `check:workers` now depends on `build:mtp`, and alone after the output was removed it gave 211 passed and 1 skipped, the skip naming `anthropic`. The suites `mise run check:portability`, `check:testing-requires` and `check:vyvid-binding` hold the new tests.

## Adversarial probes

| Probe | Result |
|---|---|
| the `&&` rule taken out of `tools/portability.py` in memory | `python a.py && python b.py` let through, which XP6's parametrised test refuses |
| `test_vm8_03` before XP-4 | passed on Windows with the script never running, so it now asserts the deferred task was tried |
| a junction to a scratch folder removed by `rmdir`, `rd /s /q`, `Remove-Item -Recurse -Force`, `.Delete()` and `shutil.rmtree` | the first four removed the junction and kept the target's file, and `shutil.rmtree` refused it |

## Not run

- Linux and macOS. No CI is chosen yet, and this was built on Windows.
- `clean:frontend` on this checkout, since it removes `node_modules`. Its test runs over a scratch tree.
- `check:conformance`, `test:frontend` and the studio's browser suites, which `check` leaves out.
- The reasoner timeout of TD-153 did not recur in the whole check above, and stays recorded.
