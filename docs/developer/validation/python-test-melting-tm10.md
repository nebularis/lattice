<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: python-test-melting TM10, mem_check-driven worker sizing

**Unit:** `python-test-melting` ([plan](../plans/python-test-melting.md), TM10's row)
**Machine:** S, Windows. **Branch:** `py-test-xtra`, from `docs/placement-vehicles-structure`. Commits are the maintainer's.
**Plan and test cases:** [python-test-melting plan](../plans/python-test-melting.md), TM10's row
**Decisions:** none new. TM-Q1 to TM-Q5 already decided (status record)
**Depends on:** [TM9](python-test-melting-tm9.md)

## Invariant

`check:ontology-catalog` and `check:peril-vocabulary` answer `pytest_xdist_auto_num_workers` with `mem_check`, from a measured peak per worker, so a short machine runs fewer workers instead of swapping. `PYTEST_XDIST_AUTO_NUM_WORKERS` still overrides it. Every test outcome is the same as before, aside from the pre-existing failure found and explained below.

## What changed

`tools/conftest.py` gains the `pytest_xdist_auto_num_workers` hook, the same shape as `tools/persistence/tests/conftest.py`'s (TM9's reference point), with its own `PER_WORKER` constant. The two check tasks share one `conftest.py`, since `check:peril-vocabulary`'s one file is already part of `check:ontology-catalog`'s own run, so one hook and one constant serve both, rather than two separate ones answering the same question about the same process.

`PER_WORKER` is 900 MiB, from a fresh measurement with `-n 0` (one worker, the whole suite): 0.80 GB for the process tree, the largest single Python process at 305 MB, and up to 3 JVMs concurrently holding 584 MB. The 3 JVMs are not one per xdist worker (there is only one worker at `-n 0`): a reasoning test's own thread pool starts several subprocesses at once within that single worker, so the figure already reflects what one worker can ask for at its peak, not an undercount that parallelism would later expose. 900 MiB rounds up from the observed ~0.89 GB, the same margin `tools/persistence/tests/conftest.py` takes over its own measured 649 MB (700 MiB).

On this machine, `mem_check.workers(os.cpu_count(), 900 MiB)` returns the machine's own core count (16), since over 30 GB is available. The hook changes nothing observable here. Its value is for a short machine, for example an 8 GB laptop with an editor open, where it now runs fewer workers instead of the same count regardless of what is free.

## A correctness bug found while measuring, not caused by this change

Comparing serial and auto runs for TM9 and TM10 both surfaced the same two failures, identically, under every worker count tried (`-n 0`, `-n auto`, `--workers 2`): `tools/test_import_guard.py::test_c10a_01_the_repository_passes` and `tools/test_instrument.py::test_c6_01_import_guard_passes`. Both call `tools.import_guard.check()`, whose `standalone_violations` reads a file with `Path.read_text()` and no explicit encoding. On Windows that decodes with the console codepage (`cp1252`), not UTF-8, so a real ontology file (`ontology/spc/...`) that is valid UTF-8 but not valid cp1252 raises `UnicodeDecodeError`. Deterministic, not flaky, and present before this unit's first commit on this machine. TM9's own Validation Pack guessed "flaky, a reasoning-server timeout among them" before this was traced, corrected there now. This is a correctness bug in `tools/import_guard.py`, not a speed or parallelism question, so it is out of scope for `python-test-melting`: flagged for the maintainer, not fixed here. The fix, when someone takes it up, is the one `lattice-testing`'s skill already gives for the same class of bug in a subprocess's captured output: read explicitly as UTF-8.

## Test cases

| ID | Given / When / Then | Level | +/- |
|---|---|---|---|
| TM10-01 | the hook / `MEM_CHECK_AVAILABLE_MIB` unset, plenty of memory / `check:peril-vocabulary` starts the same worker count as plain `-n auto`, 39 passed | L1 | + |
| TM10-02 | the hook / `check:ontology-catalog` under `-n auto` / the two known encoding failures only, same identity as serial, no new failure | L1 | + |
| TM10-03 | `MEM_CHECK_AVAILABLE_MIB` set low, simulating a short machine (not yet run, see Deliberate non-coverage) | L1 | not run |

## One command

```bash
mise exec -- python -m pytest tools/test_peril_vocabulary.py -q -n auto
mise exec -- python tools/time_ontology_tests.py --task check:ontology-catalog
```

## Artefacts to inspect

`tools/conftest.py`'s new `PER_WORKER` constant and `pytest_xdist_auto_num_workers` hook.

## Deliberate non-coverage

TM10-03: showing the hook actually reduces the worker count under `MEM_CHECK_AVAILABLE_MIB` set low, as the plan's own validation section asks for TM10 and TM12 together. Not run this pass, since this machine has no short-memory condition to observe directly and a forced-low run was not yet scripted. Worth adding before this slice is called complete, flagged for the maintainer or a follow-up pass.

## Handoff

Built on `py-test-xtra`, autonomously, per the maintainer's instruction this session. `tools/conftest.py`'s hook is ready to commit. The `lattice-toolchain` reminder to use the catalogue reader for paths was followed in TM9's tool fix, and considered again here: `tools/conftest.py`'s own `ROOT = Path(__file__).resolve().parents[1]` is the same pattern, used by dozens of existing fixtures (`repo_root()` among them) across every adopting test module. Changing it here was judged out of scope and too risky for this slice: `lattice-toolchain` itself notes the catalogue's scan does not yet read tests (TD-54), so this is acknowledged, pre-existing debt, not something TM10 introduces or is asked to close.

**TM11 and TM12, see TM9's Validation Pack:** `check:mork-compilers` is confirmed in TM11's scope (the maintainer, 2026-10-27). My leaning, acted on next: TM11 goes first for that one suite, since it decides what the default `check:mork-compilers` task even contains (its conformance tests move to a new `check:mork-compilers-conformance` task), and only once that split exists does a serial time for the remaining default task mean anything to size workers against. TM11 therefore gives both of its resulting tasks `-n auto` with `mem_check` sizing immediately, built to the skill's stated defaults from the start rather than retrofitted twice. TM12's own six-item list then needs no separate entry for `check:mork-compilers`, since TM11 already leaves it on the defaults, and TM12 covers the remaining five.
