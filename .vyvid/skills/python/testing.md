Grounded in the `python-test-melting` unit (2026-10-09), which took the ontology test suite from
456s serial to about 124s under `pytest-xdist`, with zero change to any test's meaning. Full
detail: [the plan](../../../docs/developer/plans/python-test-melting.md) and
[its status record](../../../docs/developer/status/python-test-melting.md).

## The defaults for every suite

- **Sized to the memory available.** The suite's `conftest.py` answers `pytest_xdist_auto_num_workers` with `mem_check` (below), from
  its own measured peak per worker, and `PYTEST_XDIST_AUTO_NUM_WORKERS` still overrides it.
- **Paths from the catalogue.** A test finds a module's examples, a register or the root through the catalogue reader, as skill `lattice-toolchain`'s Finding paths shows (STD-273), never from `__file__` or a written path. The catalogue's scan does not read tests yet (TD-54), so a reviewer holds this.

- **Oxigraph runs the generated SPARQL.** A behaviour test that executes generated SPARQL runs on the default engine, Oxigraph
  (ADR-A125, addendum of 2026-10-21). rdflib stays the library the tools and pySHACL are built on.

Benchmarks fail on a wrong result, never on time (ADR-A124).

## Memory: sizing workers

free. `tools/testing/mem_check` (`mise run bootstrap:testing-mem-check`, standard library only, macOS, Linux and Windows) reads what
is available and `mem_check.workers(default, per_worker)` gives as many workers as fit in it less a 1 GiB reserve, up to the default
count and never fewer than two, which runs longer and smaller. `MEM_CHECK_AVAILABLE_MIB` stands in for the machine. A suite adopts it with
the hook its README shows, giving its own peak per worker, measured with `-n 0` (`tools/persistence/tests/conftest.py` gives 700 MiB
from a measured 649 MB). Any other suite that can run short of memory, or that starts more than two workers, may use it the same way.

## Measure before changing anything

- `mise run dev:time-ontology-tests` profiles `check:ontology-catalog` as one real run, with the
  task's own flags and a JUnit report, and prints the wall time, the slowest files and the slowest
  tests. A tail made of a few big files, or one stalled test, shows up here. A run reports nothing
  until it ends, so `-- --per-file` runs each file in its own process with a `--timeout` and marks
  the one that hangs. Its sum exceeds a real run.

`mise run dev:time-ontology-tests` prints the memory state and when each worker finished (design record H7 and H8, in `docs/architecture/efficient-queries-and-shapes.md`).

## `pytest-xdist`: the first thing to try

and `mise run dev:time-ontology-tests -- --workers N --dist MODE` compares settings and reports
when each worker finished and the peak memory.

## Lessons from a large suite (replace)

Lessons from the persistence suite (FMH-TS-1)

`check:persistence` went from 4m12s serial to about 1m35s on a loaded machine. What paid, in order: `-n auto --dist loadgroup`, a
session-wide `_sparql_translated_once` (H1) for a suite that calls `pyshacl.validate` directly in many places, running the children of
a hash-seed sweep side by side (a thread pool over `subprocess.run`), memoising a pure function that parses SPARQL
(`templatecheck.analyse`), and parsing a fixture once per process (`witness._load_fixture`). A module whose tests share one slow
per-process computation goes in one `xdist_group` (`--dist loadgroup`), or every worker repeats it. Count parses before caching them:
a profile showed 5901 SPARQL parses of 1675 distinct texts, and the update texts of a sweep are distinct per history, so only reads gain.
The summed CPU time rises with the worker count on 4 performance plus 4 efficiency cores, so keep `auto`. Not tried successfully: sharing
rdflib's update parse tree between sweep children by pickle (`ParseResults` did not round-trip).

## Repository-wide text scans: don't shell out to `git grep`

`tools/conftest.py`'s `repo_files(roots, pattern, *, fixed=False, repo_root=ROOT)` replaces a `git grep` subprocess call: it lists files with `git ls-files` (tracked, and untracked but not ignored, so a file just written is scanned and an ignored directory never is), reads every file as UTF-8 explicitly, and matches line by line the way `git grep` does (so `^`/`$` anchor one line, not the whole file). In a checkout with no `.git` it raises, since a scan there cannot tell an ignored file from a tracked one.

**The one real cost of including untracked files**: it sees them too, which `git grep` would not. This bit the roll-out for real: a new test fixture file (`test_repo_files.py`) contained the literal string `"ins:Element"` as test data for exercising the pattern matcher itself, and a retired-term scan over `tools/` picked it up as a false positive. Fixed the same way the suite already handled its own `RETIRED`-constant test file: add the new file to the scan's own allow-list. If this keeps happening, it is a sign the roots are too broad, not that the approach is wrong (skip a named list of build and dependency directories, namely `.git`, `__pycache__`, `node_modules`, `.venv`, `.build`, `build`, `dist`, `target`, `.pytest_cache`, and similar).
