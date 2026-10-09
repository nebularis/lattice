# SPDX-License-Identifier: MPL-2.0

"""Shared, session-scoped caching for the ontology test suite (plan
`python-test-melting`, TM1/TM2). Measured baseline before this file existed:
456s serial for the 25 top-level `tools/test_*.py` modules (560 passed, 67
skipped, 9 pre-existing failures unrelated to this plan). Most of that time is
pySHACL validating the same graph against the same shapes repeatedly across
call sites, and every module re-parsing the same layer Turtle and shape files
at import (python-test-melting sketch, items 1 and 2).

Two caches live here, as session-scoped fixtures (TM-Q2, option B: this file
only, no sibling support module):

- `graph_cache`: memoises a parsed/merged graph by its exact source
  arguments (each a `Path`, parsed as a file, or a `str`, parsed as inline
  Turtle). The source tuple is sorted before use as a cache key, so the same
  sources in a different order (several modules build the same layer stack
  with its pieces listed differently) still share one object.
- `validated`: memoises a whole pySHACL report, keyed on the identity of the
  data and shapes graphs plus every validation option, so the violation view
  and the warning view of the same run share one physical `validate()` call.

**A cached graph is a shared object across the whole session. A test must
never mutate one.** Every mutation helper in this suite already builds a
fresh graph for a changed example (a fresh parse, or `cached_graph + data`,
which rdflib's `Graph.__add__` already returns as a new object) rather than
changing a cached one in place, so adopting the cache changes no test's
behaviour. `_graph_cache_not_mutated`, an autouse session fixture, checks
every cached graph's triple count at the end of the session against the
count recorded when it was built, and fails loudly if anything changed, so a
cache can never silently hide a test that corrupted shared data (plan
principle 3).

**How a test module adopts the cache.** Each module that benefits declares
one `@pytest.fixture(scope="session", autouse=True)` that fetches its own
`MODEL`/`SHAPES`/`EVERY_SHAPE` (or that module's equivalents) from
`graph_cache` and assigns them onto `request.module`, so every existing test
function and helper in that module keeps referring to the same bare names it
always has: only the one assignment at the top of the file changes, from a
direct `_graph(...)` call to a cached one. A helper whose default argument
reads one of those names directly (evaluated at import time, before any
fixture runs) is changed to look it up inside its own body instead. This
keeps the caching mechanism itself centralised here, fixture-based, and
session-scoped, without rewriting every call site's signature across the 25
modules that use it (a deliberate, recorded reading of TM-Q2 option B: the
cache is the fixture, not every test that benefits from it).

`repo_files` (TM6, TD-29) replaces the five `git grep` subprocess calls the
suite used to find a retired term or a pinned version: it walks the tree
directly, so it works without `.git` (a source archive, a worktree-less
checkout), reads every file as UTF-8 explicitly instead of letting a
subprocess capture fall back to the console's codepage (the Windows-only
`UnicodeDecodeError` this replaces), and returns the same repo-relative,
forward-slash paths on every platform."""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any, Sequence

import pytest
from pyshacl import validate as _pyshacl_validate
from rdflib import Graph

ROOT = Path(__file__).resolve().parents[1]
ONTOLOGY = ROOT / "ontology"

# Every adopting module already inserts these two paths itself; inserting them
# here too (idempotently) lets conftest.py's own fixtures import sibling tools
# modules (e.g. `mork_compilers.reasoning`) before any test module has run yet.
for _extra in (ROOT / "tools", ROOT / "tools" / "mork_compilers" / "src"):
    if str(_extra) not in sys.path:
        sys.path.insert(0, str(_extra))


def _sort_key(source: Any) -> str:
    return str(source)


class GraphCache:
    """Memoises a parsed/merged graph by its source arguments, order-independent.
    Returns the SAME object for the same sources (by content, not by argument
    order) for the life of the session. Callers must treat the result as
    read-only (see the module docstring)."""

    def __init__(self) -> None:
        self._by_key: dict[tuple, Graph] = {}
        self._size_at_insert: dict[tuple, int] = {}

    def __call__(self, *sources: Any) -> Graph:
        key = tuple(sorted(sources, key=_sort_key))
        cached = self._by_key.get(key)
        if cached is not None:
            return cached
        graph = Graph()
        for source in sources:
            if isinstance(source, Path):
                graph.parse(source)
            else:
                graph.parse(data=source, format="turtle")
        self._by_key[key] = graph
        self._size_at_insert[key] = len(graph)
        return graph

    def mutated(self) -> dict[tuple, tuple[int, int]]:
        """Every cached graph whose triple count no longer matches the count
        recorded when it was built, `{sources: (built, now)}`. Empty when
        nothing cached has been mutated."""
        return {
            key: (self._size_at_insert[key], len(graph))
            for key, graph in self._by_key.items()
            if len(graph) != self._size_at_insert[key]
        }


class ValidationCache:
    """Memoises a whole pySHACL report, keyed on the identity of the data and
    shapes graphs plus every validation option, so repeated calls for the same
    graph, shape set and options run `validate()` once and share its report
    (python-test-melting sketch item 1). A graph a test built or changed
    itself is a fresh object each time, so it is simply never a cache hit here
    -- nothing needs to be invalidated, because nothing cached is ever
    mutated (see the module docstring, and `_graph_cache_not_mutated` below
    for the graphs that do come from `graph_cache`)."""

    def __init__(self) -> None:
        self._by_key: dict[tuple, tuple] = {}
        # Keeps every cached (data, shapes) pair alive for the session, so a
        # Python id() this cache has keyed on is never reused by an unrelated
        # later object (id() is only unique while the object is alive).
        self._keepalive: list[tuple[Graph, Graph]] = []

    def __call__(self, data: Graph, shapes: Graph, **options: Any) -> tuple:
        key = (id(data), id(shapes), tuple(sorted(options.items())))
        cached = self._by_key.get(key)
        if cached is not None:
            return cached
        result = _pyshacl_validate(data, shacl_graph=shapes, **options)
        self._by_key[key] = result
        self._keepalive.append((data, shapes))
        return result


_GRAPH_CACHE = GraphCache()
_VALIDATION_CACHE = ValidationCache()


@pytest.fixture(scope="session")
def repo_root() -> Path:
    return ROOT


@pytest.fixture(scope="session")
def ontology_root() -> Path:
    return ONTOLOGY


@pytest.fixture(scope="session")
def graph_cache() -> GraphCache:
    return _GRAPH_CACHE


@pytest.fixture(scope="session")
def validated() -> ValidationCache:
    return _VALIDATION_CACHE


@pytest.fixture(scope="session", autouse=True)
def _graph_cache_not_mutated() -> None:
    """TM1's guard. Runs once, at session end (see the module docstring)."""
    yield
    changed = _GRAPH_CACHE.mutated()
    assert not changed, (
        "a test mutated a shared, cached graph instead of building a fresh one -- "
        f"this would silently corrupt later tests' input: {changed}"
    )


# ---- TM6: repository scans in Python, not `git grep` (TD-29) ---------------

_SKIP_DIR_NAMES = {
    ".git", "__pycache__", "node_modules", ".venv", "venv", ".build", "build", "dist",
    "target", ".pytest_cache", ".mypy_cache", ".ruff_cache", ".idea", ".vscode",
}


def _skippable(part: str) -> bool:
    return part in _SKIP_DIR_NAMES or part.endswith(".egg-info")


def _iter_files(root: Path) -> list[Path]:
    if not root.exists():
        return []
    if root.is_file():
        return [root]
    return [
        path for path in sorted(root.rglob("*"))
        if path.is_file() and not any(_skippable(part) for part in path.relative_to(root).parts[:-1])
    ]


_FILE_LIST_CACHE: dict[tuple, list[Path]] = {}


def _files_under(roots: Sequence[str], repo_root: Path) -> list[Path]:
    key = (repo_root, tuple(sorted(roots)))
    cached = _FILE_LIST_CACHE.get(key)
    if cached is not None:
        return cached
    files: list[Path] = []
    for name in roots:
        files.extend(_iter_files(repo_root / name))
    _FILE_LIST_CACHE[key] = files
    return files


def repo_files(roots: Sequence[str], pattern: str, *, fixed: bool = False, repo_root: Path = ROOT) -> list[str]:
    """Every repo-relative, forward-slash path under `roots` (each a directory
    or a file, relative to `repo_root`) with a line containing `pattern`: a
    fixed substring if `fixed`, a regular expression otherwise, matched the
    way `git grep` matches it, line by line, so `^`/`$` anchor one line, not
    the whole file. Skips common build and dependency directories, since
    walking the tree directly (unlike `git grep`, which only sees tracked
    files) would otherwise also see untracked build output."""
    finder = (lambda line: pattern in line) if fixed else re.compile(pattern).search
    matches = []
    for path in _files_under(roots, repo_root):
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if any(finder(line) for line in text.splitlines()):
            matches.append(path.relative_to(repo_root).as_posix())
    return sorted(matches)
