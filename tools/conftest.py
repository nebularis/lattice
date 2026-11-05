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

A third speed-up sits under `validated`. pySHACL runs each SPARQL constraint once
per focus node and rdflib parses the query text again every time, which was about
90% of a validation's cost in `test_exposure_ontology.py`. `_sparql_translated_once`
parses each distinct text once while `validated` runs pySHACL. Tests that call
`pyshacl.validate` directly do not get it.

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
one `@pytest.fixture(scope="module", autouse=True)` that fetches its own
`MODEL`/`SHAPES`/`EVERY_SHAPE` (or that module's equivalents) from the
session-scoped `graph_cache` and assigns them onto `request.module`, so every
existing test function and helper in that module keeps referring to the same
bare names it always has: only the one assignment at the top of the file
changes, from a direct `_graph(...)` call to a cached one. The fixture itself
is module-scoped, not session-scoped, since `request.module` is only
available at function, class or module scope; the cache underneath it is
session-scoped regardless, so the same parsed graph is still shared across
every module that asks for the same sources. A helper whose default argument
reads one of those names directly (evaluated at import time, before any
fixture runs) is changed to look it up inside its own body instead. The same
fixture also assigns `module.validate = validated`: `ValidationCache` is
callable with exactly `pyshacl.validate`'s own signature (`data_graph`,
`shacl_graph=...`, every other keyword passed through), so every existing
`validate(data, shacl_graph=shapes, ...)` call site in the module gains TM2's
cache with no change of its own, including inside the module's own helper
functions. This keeps the caching mechanism itself centralised here,
fixture-based, and session-scoped underneath, without rewriting every call
site's signature across the 25 modules that use it (a deliberate, recorded
reading of TM-Q2 option B: the cache is the fixture, not every test that
benefits from it).

`repo_files` (TM6, TD-29) replaces the five `git grep` subprocess calls the
suite used to find a retired term or a pinned version: it asks `git ls-files`
(tracked and untracked files that are not ignored) and refuses a checkout
without `.git`, so a scan never reads a gitignored directory. It reads every file as UTF-8 explicitly instead of letting a
subprocess capture fall back to the console's codepage (the Windows-only
`UnicodeDecodeError` this replaces), and returns the same repo-relative,
forward-slash paths on every platform."""

from __future__ import annotations

import contextlib
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Iterator, Sequence

import pytest
from pyshacl import validate as _pyshacl_validate
from rdflib import Graph
from rdflib.plugins.sparql.algebra import translateQuery
from rdflib.plugins.sparql.parser import parseQuery
from rdflib.plugins.sparql.processor import SPARQLProcessor

ROOT = Path(__file__).resolve().parents[1]
ONTOLOGY = ROOT / "ontology"

# Every adopting module already inserts these two paths itself; inserting them
# here too (idempotently) lets conftest.py's own fixtures import sibling tools
# modules (e.g. `mork_compilers.reasoning`) before any test module has run yet.
for _extra in (ROOT / "tools", ROOT / "tools" / "mork_compilers" / "src"):
    if str(_extra) not in sys.path:
        sys.path.insert(0, str(_extra))

PER_WORKER = 900 * 1024 ** 2
"""One worker's peak resident memory, for check:ontology-catalog and check:peril-vocabulary alike
(the second is a subset of the first's files, so one process-tree figure covers both). Measured
with -n 0 (python-test-melting TM10): 0.80 GB for the whole tree, the largest Python process at
305 MB, and up to 3 JVMs concurrently holding 584 MB (a reasoning test's own thread pool over
several subprocesses, not one JVM per xdist worker). Rounded up from the observed ~0.89 GB."""


def pytest_xdist_auto_num_workers(config):
    """What ``-n auto`` means for check:ontology-catalog and check:peril-vocabulary.
    ``PYTEST_XDIST_AUTO_NUM_WORKERS`` decides when it is set. Otherwise mem_check gives as many
    workers as fit in the memory available, up to the machine's count and never fewer than two
    (ADR-A125, python-test-melting TM10)."""
    if os.environ.get("PYTEST_XDIST_AUTO_NUM_WORKERS"):
        return None
    try:
        import mem_check
    except ImportError:
        return None
    return mem_check.workers(os.cpu_count() or 1, PER_WORKER)


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

    def resnapshot(self, graph: Graph) -> None:
        """Re-records `graph`'s current triple count as its new baseline, if it is
        one of this cache's own objects (a no-op otherwise). `ValidationCache`
        calls this after a real pySHACL run, because pySHACL's own `advanced=True`
        mode adds a small, fixed, idempotent set of RDFS/OWL compatibility axioms
        to the shapes graph it is given the first time it sees it (confirmed:
        `owl:Class rdfs:subClassOf rdfs:Class` and similar, never growing further
        on a second call) -- pySHACL's own documented behaviour, not a test's, and
        not a sign that caching has hidden anything. A later, *further* change to
        the same graph still trips `mutated()`, since this only accepts the one
        delta pySHACL itself is known to make."""
        for key, cached in self._by_key.items():
            if cached is graph:
                self._size_at_insert[key] = len(graph)
                return


_CANONICAL_QUERIES: dict[str, str] = {}
_DECLARED_PREFIXES: dict[str, frozenset[str]] = {}
_UNUSED_TREES: dict[str, Any] = {}
_TRANSLATED_QUERIES: dict[tuple, Any] = {}
_PREFIX_DECLARATION = re.compile(r"\s*PREFIX[ \t]+([^\s:]*):[ \t]*<[^>\s]*>", re.IGNORECASE)


def _canonical_query(text: str) -> str:
    """`text` with its leading `PREFIX` declarations sorted, one per line.

    pySHACL writes the declarations from a dict that follows the shapes graph, so
    the same constraint reaches rdflib with its prefixes in a different order from
    one validation to the next (511 distinct texts in 512 parses for the wording
    tests). Order does not change what a query means, unless a prefix is declared
    twice and the later one wins, so a text that declares one twice is left as it is."""
    canonical = _CANONICAL_QUERIES.get(text)
    if canonical is None:
        declarations, position = [], 0
        while (found := _PREFIX_DECLARATION.match(text, position)):
            declarations.append((found.group(1), found.group(0).strip()))
            position = found.end()
        names = [name for name, _ in declarations]
        if len(declarations) < 2 or len(set(names)) != len(names):
            canonical = text
        else:
            canonical = "\n".join(sorted(declaration for _, declaration in declarations)) + "\n" + text[position:]
        _CANONICAL_QUERIES[text] = canonical
    return canonical


def _declared_prefixes(text: str) -> frozenset[str]:
    """The prefixes `text`'s own `PREFIX` lines declare, from one parse per text.
    The tree from that parse is kept for the first translation only, because
    translating may rewrite the tree it is given, so a later translation of the
    same text parses again."""
    declared = _DECLARED_PREFIXES.get(text)
    if declared is None:
        parsed = parseQuery(text)
        declared = _DECLARED_PREFIXES[text] = frozenset(d.get("prefix", "") for d in parsed[0] if d.name == "PrefixDecl")
        _UNUSED_TREES[text] = parsed
    return declared


@contextlib.contextmanager
def _sparql_translated_once() -> Iterator[None]:
    """While active, `SPARQLProcessor.query` parses and translates each distinct
    query text once and reuses the result, instead of doing both on every call.

    pySHACL evaluates a SPARQL constraint with one `graph.query(text,
    initBindings=...)` per focus node, and rdflib parses and translates `text`
    from scratch each time with its pure-Python `pyparsing` grammar. Profiled on
    `test_exposure_ontology.py`, one `validate()` issued 937 queries made of 30
    distinct texts, and parsing plus translating them was about 90% of its 13s.
    A translated query is the same object `prepareQuery` returns, which rdflib
    documents as reusable with different `initBindings`, so only the repeated
    parse is skipped. The text is first put in a canonical order of its `PREFIX`
    declarations (`_canonical_query`).

    Translation resolves a prefixed name from the query's own `PREFIX` lines,
    and otherwise from the graph's namespace bindings, and resolves relative
    IRIs against the base. The key therefore holds the text, the base, and the
    graph's bindings for the prefixes the text uses without declaring. Keying on
    all of a graph's bindings missed the cache whenever two graphs bound
    different prefixes that the query never mentions (1,258 parses for 94
    distinct texts in `test_parameter_bindings.py`). A prefix is counted as used
    when `prefix:` occurs anywhere in the text, which can only include more
    bindings than needed and so only splits entries, never shares a wrong one.

    Scoped to the one pySHACL call it wraps and undone afterwards, so a test
    that runs SPARQL on rdflib directly (the engine tests, for one) sees
    rdflib's own behaviour. The caches outlive the call, so later validations
    in the same process reuse earlier translations."""
    original = SPARQLProcessor.query

    def query(self, strOrQuery, initBindings=None, initNs=None, base=None, DEBUG=False):
        if isinstance(strOrQuery, str):
            text = _canonical_query(strOrQuery)
            declared = _declared_prefixes(text)
            used = tuple(sorted(
                (prefix, str(namespace)) for prefix, namespace in dict(initNs or {}).items()
                if prefix not in declared and f"{prefix}:" in text
            ))
            key = (text, base, used)
            translated = _TRANSLATED_QUERIES.get(key)
            if translated is None:
                parsed = _UNUSED_TREES.pop(text, None) or parseQuery(text)
                translated = _TRANSLATED_QUERIES[key] = translateQuery(parsed, base, initNs)
            strOrQuery = translated
        return original(self, strOrQuery, initBindings, initNs, base, DEBUG)

    SPARQLProcessor.query = query
    try:
        yield
    finally:
        SPARQLProcessor.query = original


class ValidationCache:
    """Memoises a whole pySHACL report, keyed on the *content* of the data and
    shapes graphs (not their Python identity) plus every validation option, so
    repeated calls for the same graph, shape set and options run `validate()`
    once and share its report (python-test-melting sketch item 1).

    Content, not `id()`, because a test may mutate its own graph in place and
    validate it again (`data.remove(...)` then re-validate the same Python
    object, a real, existing pattern in this suite, confirmed by a test that
    failed under an identity-only key during this plan's own roll-out): an
    identity-only cache would wrongly return the first, now-stale report.
    Fingerprinting costs one linear pass over each graph, which is still far
    cheaper than the `validate()` call it may save, and correctly treats two
    *different* graph objects with identical triples as the same cache entry
    too, a bonus hit neither this plan nor the sketch assumed.

    Callable with the same signature as `pyshacl.validate` itself
    (`data_graph`, `shacl_graph=...`, every other keyword passed through), so
    an adopting module can substitute it directly for its own `validate` name
    (`request.module.validate = validated`) and every existing call site
    gains the cache with no change of its own."""

    def __init__(self, graph_cache: "GraphCache | None" = None) -> None:
        self._by_key: dict[tuple, tuple] = {}
        # Defaults to the module's own singleton, so the `validated` fixture
        # needs no wiring of its own; a test may inject its own GraphCache to
        # exercise `resnapshot` in isolation (test_graph_cache.py).
        self._graph_cache = _GRAPH_CACHE if graph_cache is None else graph_cache

    @staticmethod
    def _fingerprint(graph: Graph) -> int:
        return hash(frozenset(graph))

    def __call__(self, data_graph: Graph, *args: Any, shacl_graph: Graph, **options: Any) -> tuple:
        key = (self._fingerprint(data_graph), self._fingerprint(shacl_graph), tuple(sorted(options.items())))
        cached = self._by_key.get(key)
        if cached is not None:
            return cached
        with _sparql_translated_once():
            result = _pyshacl_validate(data_graph, *args, shacl_graph=shacl_graph, **options)
        # pySHACL itself may have just added its own idempotent axioms to
        # either graph (see GraphCache.resnapshot's docstring); accepted, not
        # hidden, as this cache's own call is the only path a shapes graph
        # from `graph_cache` is ever validated through. Done before the final
        # fingerprint below, so a shapes graph pySHACL just touched is keyed
        # on its settled content, not its pre-validation content.
        self._graph_cache.resnapshot(data_graph)
        self._graph_cache.resnapshot(shacl_graph)
        settled_key = (self._fingerprint(data_graph), self._fingerprint(shacl_graph), key[2])
        self._by_key[settled_key] = result
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


@pytest.fixture(scope="session")
def sparql_translated_once() -> Iterator[None]:
    """Run the whole session under `_sparql_translated_once` (H1), for a suite that calls pySHACL and runs queries on rdflib in many
    places and cannot adopt `validated` in each (tools/persistence/tests). Evaluation is unchanged. Only the parse and the translation
    of a query text that was seen before are skipped."""
    with _sparql_translated_once():
        yield


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


def _iter_files(root: str, repo_root: Path) -> list[Path]:
    """The files git lists under `root`, tracked or untracked but not ignored, so a scan never reads an
    ignored directory. Refuses a checkout without git metadata."""
    if not (repo_root / ".git").exists():
        raise RuntimeError(
            f"{repo_root} has no .git, and a scan needs a git checkout, since it asks git which files "
            "are in the repository and never walks the tree (an ignored directory may hold material "
            "that is not for the repository)"
        )
    listing = subprocess.run(
        ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard", "--", root],
        cwd=repo_root, capture_output=True, check=True,
    ).stdout.decode("utf-8")
    base = Path(root)
    files = []
    for name in sorted(set(filter(None, listing.split("\0")))):
        path = repo_root / name
        below_root = Path(name).relative_to(base).parts[:-1] if base != Path(name) else ()
        if path.is_file() and not any(_skippable(part) for part in below_root):
            files.append(path)
    return files


_FILE_LIST_CACHE: dict[tuple, list[Path]] = {}


def _files_under(roots: Sequence[str], repo_root: Path) -> list[Path]:
    key = (repo_root, tuple(sorted(roots)))
    cached = _FILE_LIST_CACHE.get(key)
    if cached is not None:
        return cached
    files: list[Path] = []
    for name in roots:
        files.extend(_iter_files(name, repo_root))
    _FILE_LIST_CACHE[key] = files
    return files


def repo_files(roots: Sequence[str], pattern: str, *, fixed: bool = False, repo_root: Path = ROOT) -> list[str]:
    """Every repo-relative, forward-slash path under `roots` (each a directory
    or a file, relative to `repo_root`) with a line containing `pattern`: a
    fixed substring if `fixed`, a regular expression otherwise, matched the
    way `git grep` matches it, line by line, so `^`/`$` anchor one line, not
    the whole file. Files come from `git ls-files`, so an ignored file is
    never read, and a `repo_root` with no `.git` raises RuntimeError. Skips
    common build and dependency directories, since untracked files that are
    not ignored (unlike `git grep`, which only sees tracked files) would
    otherwise include build output."""
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


# ---- environment banner -----------------------------------------------------
# A reasoner row, a proof or a Compose test skips or fails without its tool, and a green run
# says nothing about the rows that never ran. This names the missing tools at the end of the
# run (the terminal summary shows under -q, the report header does not). Only the xdist
# controller runs it.

def _isabelle_found() -> bool:
    sys.path.insert(0, str(ROOT / "spikes" / "formal-prover" / "env"))
    try:
        from install_native import isabelle_executable
        return isabelle_executable() is not None
    except Exception:  # an unreadable installer must not break the run
        return shutil.which("isabelle") is not None
    finally:
        sys.path.pop(0)


def _reasoner_found() -> bool:
    try:
        from mork_compilers import reasoning
        return reasoning.available()
    except ImportError:
        return False


# (name, probe, what is lost, how to get it)
_TOOLS = (
    ("reasoner (reasoning-testkit jar and Java)", _reasoner_found, "every needs_reasoner test skips", "mise run bootstrap:reasoning-testkit"),
    ("Isabelle", _isabelle_found, "check:proofs cannot run", "mise run bootstrap:formal-native-isabelle"),
    ("Docker", lambda: shutil.which("docker") is not None, "Compose and Fuseki or RabbitMQ ITs cannot start", "install Docker"),
)


def missing_tools() -> list[tuple[str, str, str]]:
    return [(name, lost, fix) for name, probe, lost, fix in _TOOLS if not probe()]


def pytest_terminal_summary(terminalreporter) -> None:
    missing = missing_tools()
    if not missing:
        return
    terminalreporter.write_sep("=", "environment: tools missing", yellow=True, bold=True)
    for name, lost, fix in missing:
        terminalreporter.write_line(f"WARNING {name} not found. {lost}. Fix: {fix}", yellow=True)
