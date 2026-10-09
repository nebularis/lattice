---
name: lattice-testing
description: Diagnosing and speeding up a slow test suite, and writing or extending Python tests under tools/ that parse ontology graphs or call pySHACL. Use when a check task is slow, when adding a test that validates a graph against shapes, when sharing state across test modules with pytest fixtures, or when a repository-wide text scan needs to work on every platform.
---

# Testing in LATTICE

Grounded in the `python-test-melting` unit (2026-10-09), which took the ontology test suite from
456s serial to about 124s under `pytest-xdist`, with zero change to any test's meaning. Full
detail: [the plan](../../../docs/developer/plans/python-test-melting.md) and
[its status record](../../../docs/developer/status/python-test-melting.md).

## Measure before changing anything

A slow suite's cause is a hypothesis until profiled. Guessing wrong costs more than measuring.

- `mise run dev:time-ontology-tests` profiles `check:ontology-catalog` as one real run, with the
  task's own flags and a JUnit report, and prints the wall time, the slowest files and the slowest
  tests. A tail made of a few big files, or one stalled test, shows up here. A run reports nothing
  until it ends, so `-- --per-file` runs each file in its own process with a `--timeout` and marks
  the one that hangs. Its sum exceeds a real run.
- `python -m pytest <file> -q -p no:cacheprovider --durations=40 --durations-min=1.0` for one
  file's own ranking.
- Before changing a shared fixture, capture a baseline you can diff against exactly:
  ```powershell
  python -m pytest <files> -q -p no:cacheprovider -rA 2>&1 |
    Select-String '^(PASSED|FAILED|SKIPPED|ERROR)' | Sort-Object > before.txt
  ```
  After a change, regenerate the same way and `Compare-Object before.txt after.txt`. Anything other
  than an expected cosmetic difference (see "Reading a diff" below) is a regression until explained.
- **A whole-suite number can be misleading once several independent causes are at play.** This
  unit's own measurement: re-running the slowest family of modules together in one process, after
  adding a shared cache, showed almost no improvement over running them as separate subprocesses
  (289s against 293s, within noise), even though the cache was demonstrably correct and working.
  Profiling confirmed why: for a suite whose tests mostly validate necessarily-distinct, freshly
  mutated graphs, the dominant cost is the sheer number of `pyshacl.validate()` calls (SPARQL
  constraint evaluation), which no cache collapses, since no two calls share input. Parallelising
  the *files themselves* (`pytest-xdist`) was what moved the number, not sharing parsed graphs.
  Don't assume a caching layer is the fix: measure the combined effect, not just that the cache
  itself works.

## `pytest-xdist`: the first thing to try

`-n auto --dist loadfile` runs each file in its own worker process, so files are independent and
parallel-safe by construction (no intra-file race). This was the single highest-value change in
this unit: roughly a 3.6x reduction, confirmed with byte-identical outcomes. Try this before
building anything else. A shared, session-scoped fixture (below) is still real and still worth
doing, but each `xdist` worker gets its own fresh copy — cross-file sharing only happens for files
that land in the same worker, which `loadfile` does not guarantee.

## The shared graph and validation cache (`tools/conftest.py`)

Two session-scoped fixtures, available to every test under `tools/`:

- `graph_cache(*sources)`: memoises a parsed/merged `rdflib.Graph` by its source arguments (each a
  `Path`, parsed as a file, or a `str`, parsed as inline Turtle), order-independent (sources are
  sorted before use as the key, so two modules building "the same layer stack" in a different
  literal order still share one object).
- `validated(data_graph, *, shacl_graph, **options)`: a drop-in replacement for `pyshacl.validate`
  (same parameter names, so an existing call site needs no change once substituted in), memoising
  the whole report.

**How a module adopts it**, without rewriting every call site's signature:

```python
@pytest.fixture(scope="module", autouse=True)
def _cached_graphs(request: pytest.FixtureRequest, graph_cache, validated) -> None:
    module = request.module
    module.MODEL = graph_cache(*[ONTOLOGY / p for p in LOWER], SPEC, VOCAB)
    module.SHAPES = graph_cache(LAYER / "shapes" / "structural.ttl", LAYER / "shapes" / "constraints.ttl")
    module.validate = validated
```

The existing `MODEL`/`SHAPES` names, and every test and helper that already references them, keep
working unchanged: this assigns onto the module's own namespace, so a bare `MODEL` or a call to
`validate(...)` resolves to the cached version from here on.

**Pitfalls found by building this, not predicted in advance:**

- **`request.module` needs function, class or module scope, never session.** A first draft used
  `scope="session"` for the per-module adoption fixture and failed immediately with
  `AttributeError: module not available in session-scoped context`. Use `scope="module"`: it still
  runs once per module, and the *cache underneath* (`graph_cache`/`validated` themselves) stays
  session-scoped, so sharing across modules is unaffected.
- **A default argument that reads a cached name breaks at import time.** `def _results(data,
  shapes=SHAPES): ...` evaluates `SHAPES` the moment the `def` line runs, before any fixture has
  assigned it. Change it to `def _results(data, shapes=None): shapes = SHAPES if shapes is None else
  shapes`, which defers the lookup into the function body (by which point, for any test actually
  calling it, the fixture has already run).
- **Key the validation cache on graph *content*, never on Python identity alone.** A real test in
  this suite builds a graph, validates it, mutates the *same* object in place (`data.remove(...)`),
  then validates it again expecting a different answer. An `(id(data), id(shapes), options)` key
  would return the first, stale report for the second call — this was caught because that exact
  test failed under the first design. Fix: key on `hash(frozenset(graph))` instead. Costs one linear
  pass per call, far cheaper than the `validate()` call it may save, and correctly treats two
  independently-built graphs with identical triples as one cache entry too.
- **`pyshacl`'s own `advanced=True` mode mutates the shapes graph you give it**, once, idempotently
  (confirmed empirically: it adds a couple of fixed RDFS/OWL compatibility axioms the first time it
  sees a given shapes graph, never again after). A guard that asserts a cached graph never changes
  size will trip on this unless it re-snapshots the graph's size immediately after a real
  `validate()` call — not a test bug, `pyshacl`'s own documented-by-behaviour side effect.
- **A cache must still catch a real test mutating shared state.** `tools/conftest.py`'s
  `_graph_cache_not_mutated` fixture runs once, at session end, and asserts no cached graph's triple
  count drifted from what it was when built (aside from the one pySHACL exception above). Probe it
  for real before trusting it: add a throwaway test that does `graph_cache(...).add((s, p, o))` and
  confirm the session fails at teardown, then delete the probe.

## Repository-wide text scans: don't shell out to `git grep`

`git grep` has two real, confirmed cross-platform failure modes, not hypothetical ones:

- **On Windows, a subprocess's captured output decodes with the console codepage (`cp1252`), not
  UTF-8**, by default when a parent process doesn't force it. A real test in this suite crashed with
  `UnicodeDecodeError: 'charmap' codec can't decode byte 0x81` for exactly this reason.
  `text=True` alone does not fix it; decode explicitly as UTF-8 instead of shelling out at all.
- **POSIX ERE has no `\b`, and some platforms' `git grep -E` silently ignore it rather than erroring
  on it**, so a pattern using `\b` can pass on one platform while finding nothing real on another.
  Use `([^A-Za-z0-9_]|$)` instead, which means the same thing on every platform.

`tools/conftest.py`'s `repo_files(roots, pattern, *, fixed=False, repo_root=ROOT)` replaces a
`git grep` subprocess call: it walks the tree directly (so it also works in a source archive, with
no `.git`), reads every file as UTF-8 explicitly, and matches line by line the way `git grep` does
(so `^`/`$` anchor one line, not the whole file).

**The one real cost of walking the tree instead of asking git**: it sees *untracked* files too,
which `git grep` would not. This bit the roll-out for real: a new test fixture file
(`test_repo_files.py`) contained the literal string `"ins:Element"` as test data for exercising the
pattern matcher itself, and a retired-term scan over `tools/` picked it up as a false positive.
Fixed the same way the suite already handled its own `RETIRED`-constant test file: add the new file
to the scan's own allow-list. If this keeps happening, it is a sign the roots are too broad, not
that the approach is wrong (skip a named list of build/dependency directories; `.git`, `__pycache__`,
`node_modules`, `.venv`, `.build`, `build`, `dist`, `target`, `.pytest_cache`, and similar).

## Writing a new SHACL-validating test

1. Does an existing module already parse the same layer stack or shape files? If so, reuse
   `graph_cache` rather than a fresh `Graph().parse(...)` — check `tools/conftest.py`'s own tests
   (`test_graph_cache.py`) for the exact call pattern.
2. Never mutate a graph `graph_cache` returned. Build a fresh one for a changed example (a fresh
   parse, or `cached_graph + data`, which is already how every mutation helper in this suite works:
   `Graph.__add__` returns a new graph, never mutates either operand).
3. Call `validate(...)` exactly as `pyshacl.validate` is documented (`shacl_graph=`, not a bare
   positional second argument) if the module has substituted `validated` in for it — this is what
   makes the substitution a true drop-in.
4. If the test will shell out for a repository-wide check, use `repo_files` instead, not a fresh
   `subprocess.run(["git", "grep", ...])` call.

## A pytest quirk on Windows worth knowing

A long multi-line PowerShell command block sent to a persistent terminal can appear to echo stale
output from an earlier command, or seem to hang, when it is in fact still executing — check the
actual redirected output file directly (`Get-Content <file> -Tail N`) rather than trusting the
terminal capture buffer for a long-running background command.
