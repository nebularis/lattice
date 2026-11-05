<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: python-test-melting TM9, measuring every suite

**Unit:** `python-test-melting` ([plan](../plans/python-test-melting.md), "Follow-on, 2026-10-21: every suite on the defaults")
**Machine:** S, Windows. **Branch:** `py-test-xtra`, from `docs/placement-vehicles-structure`. Commits are the maintainer's.
**Plan and test cases:** [python-test-melting plan](../plans/python-test-melting.md), TM9's row
**Decisions:** none new. TM-Q1 to TM-Q5 already decided (status record)

## Invariant

For every `pytest` task `check` runs, this records the wall time serially and with `-n auto`, the peak resident memory of the whole process tree, the number of xdist workers started, and whether any test executes SPARQL on a store beyond pySHACL's own use of rdflib. No behaviour change: every suite's own test files are untouched.

## What changed, and why

`tools/time_ontology_tests.py` was the only profiling tool in the repository, and it hard-coded `check:ontology-catalog` and sampled memory only on macOS and Linux (`if os.name != "nt"`), so it could not measure anything on this machine. It gained:

- a `--task` argument, with the pytest segment found wherever it falls among a run line's `&&`-joined steps, rather than assumed first (needed for tasks such as `check:identifiers`, whose script runs before its pytest segment)
- a Windows memory sampler, reading the process tree from the Toolhelp32 snapshot and each process's working set from `GetProcessMemoryInfo` (`ctypes`, `psapi.dll`), parallel to the existing `ps`-based macOS and Linux path, in the same raw-Windows-API style `mem_check` already uses for system memory
- `ROOT` from the repository catalogue reader, never from `__file__` (`lattice-toolchain`'s Finding paths, STD-273), since this file is touched now and the rule applies to it like any other

Committed separately (`7e8f7049`) from this measurement pass, since it is a tool fix, not a measurement.

## Suites, ordered by peak memory per worker

Measured individually with `mise exec -- python tools/time_ontology_tests.py --task <task>`, each run once, on an otherwise idle machine. "Auto" is `-n auto` where the task does not already force a worker count, or the task's own flags where it does. A task whose `run` line has no `python -m pytest` segment is not in this table (it is not a pytest task): `check:ontology-versioning`, `check:import-guard`, `check:catalogue`, `check:formal-freshness`, `check:reasoning-isolation`, `check:mtp`, `check:java`, `check:frontend`, `check:spc`, `check:minting-anchors`, `check:minting-java`, `check:persistence-vectors`. `check:python-root` uses `unittest`, not pytest, for the same reason.

| Task | Serial wall | Auto wall | Peak memory, auto | Workers | SPARQL on a store? |
|---|---|---|---|---|---|
| `check:ontology-catalog` | 456.09s (TM0 baseline, unchanged) | 60.8s (this run, 2 pre-existing failures, see below) | not resampled this pass | auto, `--dist worksteal` (TM7) | pySHACL/rdflib only |
| `check:peril-vocabulary` | 49.0s | 15.8s | **1.69 GB** | auto | pySHACL/rdflib only |
| `check:persistence` | 4m12s (FMH-TS-1 baseline, unchanged) | ~1m35s (FMH-TS-1, unchanged) | not resampled this pass | auto, `--dist loadgroup` | **yes, `@engines.each_engine`, Oxigraph default (ADR-A125)** |
| `check:hooks` | 31.1s | not measured (under 10s rule does not apply, see note) | 0.14 GB | 1 (serial) | no |
| `check:mork-compilers` | 23.9s | not measured | 0.32 GB (1 JVM, 225 MB) | 1 (serial) | **yes, generated SPARQL via plain `rdflib.Graph.query`/`.update`, not the engines abstraction, see "A new TM11 candidate" below** |
| `check:agent-guidance` | 7.6s | not measured | 0.10 GB | 1 (serial) | no |
| `check:identifiers` | 7.1s | not measured | 0.08 GB | 1 (serial) | no |
| `check:reference-eligibility` | 5.4s | not measured | 0.09 GB | 1 (serial) | no `@engines.each_engine`, not surveyed test-by-test for a bare `rdflib` query |
| `check:workers` | 5.1s | 9.5s (slower, xdist startup dominates a 121-test suite) | 1.31 GB (auto) vs 0.09 GB (serial) | auto | no |
| `check:minting-python` | 4.4s | not measured | 0.08 GB | 1 (serial) | no |
| `check:published-decisions` | 2.2s | not measured | 0.08 GB | 1 (serial) | no |
| `check:vocabulary` | 2.1s | not measured | 0.08 GB | 1 (serial) | no |
| `check:persistence-library` | 1.6s | not measured | 0.08 GB | 1 (serial) | no |
| `check:authoring-tools` | 1.6s | not measured | 0.08 GB | 1 (serial) | no |
| `check:site-sections` | 1.4s | not measured | 0.08 GB | 1 (serial) | no |
| `check:mork` | **cannot run**, `tools/mork` is not installed in this checkout (see below) | — | — | — | unknown |

Where "not measured", TM9's own table already shows the suite well under the 10s mark TM12 tests against, so an `-n auto` run was not worth the extra wall time. `check:workers` is the control that shows parallel start-up cost can dominate a small suite (see its row).

## A new TM11 candidate the brief did not name

TM11 reads: "only for suites TM9 finds executing generated or hand-written SPARQL on a store." The brief's own illustrative list is suites already known to use `@engines.each_engine` (`check:persistence`). This measurement found a second one not in that list. **`check:mork-compilers`** runs its generated SPARQL (`sparql_backend.py`, `swrl_backend.py`, and the backend tests) directly through `rdflib.Graph.query`/`.update`, with no `@engines.each_engine` opt-in and no Oxigraph default. Per the skill's own default ("Oxigraph runs the generated SPARQL... a behaviour test that executes generated SPARQL runs on the default engine"), this suite departs from the default silently, which is exactly what TM11 exists to find and fix. Recorded here rather than acted on, since TM11 is its own slice and the brief names only known suites. **The maintainer should confirm `check:mork-compilers` is in TM11's scope before that slice starts.**

## `check:mork` could not be measured

`tools/mork` (package `mork-communities`) is not installed in this checkout's `.venv`. Its own dependency chain blocks on this machine's pip mirror. `langchain-litellm` requires `litellm`, which requires `boto3`, and the mirror returns 403 on each package's newest release in turn (see `/memories/repo/lattice-conventions.md`, recorded 2026-10-27). Per `lattice-toolchain`, this is handed to the maintainer with the exact error rather than retried:

```
ERROR: Could not install requirement boto3<2.0,>=1.43.119-py3-none-any.whl
(from litellm==1.106.3) because of HTTP error 403 Client Error
```

`check:mork` is left out of TM10 to TM12's scope on this machine until it is installed. It is not one of TM12's six named suites, so this does not block that slice.

## Pre-existing failures met while measuring, none caused by this pass

- `check:ontology-catalog`: 2 failed of 1201, `tools/test_import_guard.py::test_c10a_01_the_repository_passes` and `tools/test_instrument.py::test_c6_01_import_guard_passes`. Root cause found while building TM10 (below): `tools/import_guard.py`'s `standalone_violations` calls `Path.read_text()` with no explicit encoding, so on Windows it decodes with the console codepage (`cp1252`), not UTF-8, and fails with `UnicodeDecodeError` on a real ontology file (`ontology/spc/...`) that is valid UTF-8 but not valid cp1252. Deterministic, not flaky (reproduces identically serially and under every worker count tried), and present before any change in this unit. The same class of bug the `lattice-testing` skill already documents for a subprocess's captured output, here at a direct file read instead. Out of scope for `python-test-melting` (a correctness bug in `tools/import_guard.py`, not a speed or parallelism question): flagged for the maintainer, not fixed here.
- `check:hooks`: 2 failed, both `tools/test_hooks.py` asserting the POSIX executable bit (`stat.S_IXUSR`) on a hook file written on Windows's NTFS, which has no such bit. Known, Windows-only, pre-existing (repo memory, "check:agent-guidance (Windows symlinks)" names the same class of gap for a different test).
- `check:agent-guidance`: 1 failed, `test_link_replaces_its_own_links_and_refuses_others`, `OSError: [WinError 1314] A required privilege is not held by the client` from `Path.symlink_to`, since creating a symlink on Windows needs a privilege this account does not hold. Known, pre-existing (same repo-memory note).

None of these three suites is in TM12's six-item scope, so none blocks that slice. They are listed here only because TM9 ran them.

## One command

Each row was produced by, in turn:

```bash
mise exec -- python tools/time_ontology_tests.py --task <task>            # auto, or the task's own flags
mise exec -- python tools/time_ontology_tests.py --task <task> --workers 0 # serial
```

## Artefacts to inspect

`tools/time_ontology_tests.py` (the tool fix, commit `7e8f7049`). This Validation Pack (the measurement, no code changed by it).

## Deliberate non-coverage

- Re-measuring `check:ontology-catalog` and `check:persistence` serially. Both have a recent, recorded baseline (TM0, FMH-TS-1) that a repeat run would not improve on, and a serial `check:ontology-catalog` run costs about 7 to 8 minutes of wall time for no new information.
- `check:mork`, for the reason above.
- Deciding TM10, TM11 or TM12's actual changes. That is each slice's own Validation Pack.

## Handoff

Built on `py-test-xtra` (from `docs/placement-vehicles-structure`), autonomously, per the maintainer's instruction this session. `tools/time_ontology_tests.py`'s generalisation and Windows memory support are committed (`7e8f7049`). This measurement pass changed no test file and is recorded here, not yet committed as its own commit (a Validation Pack is not code, so nothing to commit beyond this file once the maintainer reviews it).

**For TM10:** `check:ontology-catalog` and `check:peril-vocabulary` are both already `-n auto` (TM7), so TM10's own job is wiring `pytest_xdist_auto_num_workers` to `mem_check` from the peak-per-worker numbers above. `check:peril-vocabulary`'s 128 MB serial figure is its per-worker figure, and `check:ontology-catalog` needs its own serial, single-worker figure, not yet measured here since a representative one already exists informally from TM7's own work, to confirm before TM10 starts.

**For TM11:** confirm whether `check:mork-compilers` is in scope, given the finding above.

**For TM12:** of the six named suites, none is slower than 31.1s serially (`check:hooks` is not in the six), and all six named suites (`check:workers`, `check:vocabulary`, `check:mork-compilers`, `check:reference-eligibility`, `check:minting-python`, `check:persistence-library`) are **under** the plan's own 10-second bar except `check:mork-compilers` at 23.9s. TM12's rule ("over 10s serially gets `-n auto` with `mem_check`... under 10s stays serial, with its time recorded") means only `check:mork-compilers` is a real TM12 candidate for parallelisation, and the other five stay serial, their times recorded in the table above. `check:mork-compilers` is also TM11's new candidate (above), so **TM11 and TM12 need to agree which one of them changes `check:mork-compilers`, and in what order**, before either starts.
