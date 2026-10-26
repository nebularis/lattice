# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""The repository catalogue's reader (ADR-A121).

The only code that finds the repository root and reads the catalogue. The catalogue is
``repository-catalogue.md`` at the root, holding the conventions and the ordered list of
modules, and one entry in each module's README. Data sits in fenced blocks tagged
``toml repository-catalogue``. A block shown inside another fence is text.

Standard library only, so it runs in any checkout's own interpreter, including where
packages cannot install.

Usage::

    python tools/lattice_repo_catalogue.py path <module> <role>    # a role's directory
    python tools/lattice_repo_catalogue.py paths <module> <role>   # an extraction contract, in order
    python tools/lattice_repo_catalogue.py check
    python tools/lattice_repo_catalogue.py dump --json
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import re
import subprocess
import sys
import tomllib
import warnings
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

CATALOGUE_FILE = "repository-catalogue.md"
BLOCK_TAG = "toml repository-catalogue"
ANY_FENCE_RE = re.compile(r"^ {0,3}(?P<fence>`{3,}|~{3,})(?P<info>.*)$")

EXCEPTIONS_FILE = "tools/lattice_repo_catalogue_exceptions.txt"
DEBT_FILE = "docs/developer/technical-debt.md"
SCAN_SKIP_DIRS = {"node_modules", "__pycache__", "build", "dist"}

# The schema. A key not listed here is an error, so later keys (for example a downstream
# catalogue's ``extends``, ADR-A121 decision 7) can be added without ambiguity.
ROOT_KEYS = {
    "catalogue": {"schema", "modules"},
    "conventions": {"roles", "kinds", "versioned", "artefact-directories", "release"},
    "generated": {"paths"},
}
# Blocks written as lists of tables, [[roots]] and so on, and the keys of each table.
ENTRY_KEYS = {
    "roots": {"path", "owns", "adrs", "row", "group"},
    "docs": {"path", "owns", "adrs", "row", "group"},
    "tools": {"name", "path", "import-names", "reaches"},
    "site": {"name", "title", "page", "layout", "order", "sources"},
}
MODULE_KEYS = {"kind", "roles", "imports", "extract"}
EXTRACT_KEYS = ("spec", "vocab", "shapes")


class CatalogueError(ValueError):
    """The catalogue cannot be read, or does not hold what was asked of it."""


@dataclass(frozen=True)
class Module:
    name: str
    path: Path
    kind: str
    roles: Tuple[str, ...]
    imports: Optional[Tuple[str, ...]]
    extract: Dict[str, Tuple[Path, ...]] = field(default_factory=dict)

    @property
    def literate(self) -> bool:
        return bool(self.extract)

    def directory(self, role: str) -> Path:
        """The directory of one of the module's roles."""
        if role not in self.roles:
            raise CatalogueError(
                f"module {self.name!r} has no role {role!r}: declare it in the roles of the catalogue entry in "
                f"{self.path.as_posix()}/README.md"
            )
        return self.path / role

    def files(self, role: str) -> Tuple[Path, ...]:
        """The files a literate module's README generates for one role, in extraction order."""
        if role not in EXTRACT_KEYS:
            raise CatalogueError(f"{role!r} is not an extracted role, expected one of {', '.join(EXTRACT_KEYS)}")
        return self.extract.get(role, ())


@dataclass(frozen=True)
class Area:
    """A root or a documentation area. ``row`` is the text of its row in AGENTS.md's table. The first
    entry of a group carries it, and the rest of the group share that row."""
    path: str
    owns: str
    adrs: Tuple[str, ...]
    row: Optional[str]
    group: Optional[str]


@dataclass(frozen=True)
class ToolPackage:
    name: str
    path: str
    import_names: Tuple[str, ...]
    reaches: Tuple[str, ...]


@dataclass(frozen=True)
class Section:
    """A section of the documentation site (OD-D29). ``page`` and ``sources`` are paths from the repository root.
    ``layout`` is a file of ``docs/_layouts`` without its suffix, or ``none`` for a page that carries its own HTML."""
    name: str
    title: str
    page: str
    layout: str
    order: int
    sources: Tuple[str, ...]


@dataclass(frozen=True)
class Catalogue:
    root: Path
    conventions: Dict[str, Any]
    modules: Dict[str, Module]
    roots: Tuple[Area, ...] = ()
    docs: Tuple[Area, ...] = ()
    tools: Tuple[ToolPackage, ...] = ()
    generated: Tuple[str, ...] = ()
    site: Tuple[Section, ...] = ()

    @property
    def release_version(self) -> Optional[str]:
        """The one release number every member module's documents carry (OD-D55), or None."""
        return (self.conventions.get("release") or {}).get("version")

    def release_members(self) -> List[Module]:
        """The modules released together: those of the kinds the release names."""
        kinds = set((self.conventions.get("release") or {}).get("kinds", ()))
        return [m for m in self.modules.values() if m.kind in kinds]

    def is_generated(self, path: str) -> bool:
        """Whether a path is, or lies under, a generated path that a check may find missing."""
        return any(path.rstrip("/") == g.rstrip("/") or path.startswith(g.rstrip("/") + "/") for g in self.generated)

    def module(self, name: str) -> Module:
        if name not in self.modules:
            raise CatalogueError(f"no module {name!r}: list it under [catalogue] modules in {CATALOGUE_FILE}")
        return self.modules[name]

    def modules_of_kind(self, kind: str) -> List[Module]:
        return [m for m in self.modules.values() if m.kind == kind]


def find_root(root: Path | str | None = None) -> Path:
    """The repository root: an explicit ``root``, then ``LATTICE_ROOT``, then the nearest
    directory at or above the working directory that holds the catalogue file. Never a
    count of ``__file__``'s parents, and never git (ADR-A121 decision 4)."""
    if root is not None:
        return Path(root).resolve()
    if os.environ.get("LATTICE_ROOT"):
        return Path(os.environ["LATTICE_ROOT"]).resolve()
    here = Path.cwd().resolve()
    for candidate in (here, *here.parents):
        if (candidate / CATALOGUE_FILE).is_file():
            return candidate
    raise CatalogueError(
        f"no {CATALOGUE_FILE} at or above {here}: run from inside the repository, or set LATTICE_ROOT"
    )


def root_above(path: Path | str) -> Optional[Path]:
    """The nearest directory at or above ``path`` that holds the catalogue file, or None. A
    caller that knows which file it is working on passes the result to ``load()`` as its
    explicit root, so it works from any working directory."""
    here = Path(path).resolve()
    for candidate in (here, *here.parents):
        if (candidate / CATALOGUE_FILE).is_file():
            return candidate
    return None


def blocks(markdown: str) -> List[str]:
    """The bodies of a document's catalogue blocks. Any other fence is skipped whole."""
    lines, found, index = markdown.splitlines(), [], 0
    while index < len(lines):
        match = ANY_FENCE_RE.match(lines[index])
        if match is None:
            index += 1
            continue
        fence = match.group("fence")
        closing = re.compile(rf"^ {{0,3}}{re.escape(fence[0])}{{{len(fence)},}}\s*$")
        end = index + 1
        while end < len(lines) and not closing.match(lines[end]):
            end += 1
        if end >= len(lines):
            raise CatalogueError(f"unterminated fence opened at line {index + 1}")
        if match.group("info").strip() == BLOCK_TAG:
            found.append("\n".join(lines[index + 1:end]))
        index = end + 1
    return found


def _merge(into: Dict[str, Any], data: Dict[str, Any], where: str, prefix: str = "") -> None:
    for key, value in data.items():
        dotted = f"{prefix}{key}"
        if key in into and isinstance(into[key], dict) and isinstance(value, dict):
            _merge(into[key], value, where, f"{dotted}.")
        elif key in into:
            raise CatalogueError(f"{where}: key {dotted!r} is defined twice")
        else:
            into[key] = value


def _check_release(release: Any, kinds: Dict[str, Any]) -> None:
    """``[conventions.release]``: the release number, and the kinds of module released together (OD-D55)."""
    if release is None:
        return
    where = f"{CATALOGUE_FILE}: [conventions.release]"
    if not isinstance(release, dict) or set(release) != {"version", "kinds"}:
        raise CatalogueError(f"{where} holds exactly version and kinds")
    if not isinstance(release["version"], str) or not re.fullmatch(r"\d+\.\d+\.\d+", release["version"]):
        raise CatalogueError(f"{where}: version {release['version']!r} is not X.Y.Z")
    unknown = set(_strings(release["kinds"], f"{where}: kinds")) - set(kinds)
    if unknown:
        raise CatalogueError(f"{where}: kinds {', '.join(sorted(unknown))} are not conventions' kinds")


def _read(path: Path) -> Dict[str, Any]:
    if not path.is_file():
        raise CatalogueError(f"{path.as_posix()} does not exist")
    merged: Dict[str, Any] = {}
    for body in blocks(path.read_text(encoding="utf-8")):
        try:
            data = tomllib.loads(body)
        except tomllib.TOMLDecodeError as error:
            raise CatalogueError(f"{path.as_posix()}: a catalogue block does not parse ({error})") from None
        _merge(merged, data, path.as_posix())
    return merged


def _strings(value: Any, where: str) -> Tuple[str, ...]:
    if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
        raise CatalogueError(f"{where} must be a list of strings")
    return tuple(value)


def _entries(value: Any, key: str, required: Sequence[str]) -> List[Dict[str, Any]]:
    """The tables of a ``[[key]]`` block, each with known keys only, its required keys, and text as strings."""
    if not isinstance(value, list) or not all(isinstance(v, dict) for v in value):
        raise CatalogueError(f"{CATALOGUE_FILE}: {key} must be a list of tables, written [[{key}]]")
    for number, entry in enumerate(value, 1):
        where = f"{CATALOGUE_FILE}: {key} entry {number}"
        unknown = set(entry) - ENTRY_KEYS[key]
        if unknown:
            raise CatalogueError(f"{where}: unknown key(s) {', '.join(sorted(unknown))}")
        for name in required:
            if name not in entry:
                raise CatalogueError(f"{where}: needs {name!r}")
        for name, item in entry.items():
            if name not in ("adrs", "import-names", "reaches", "sources", "order") and not isinstance(item, str):
                raise CatalogueError(f"{where}: {name!r} must be a string")
    return value


def _areas(value: Any, key: str) -> Tuple[Area, ...]:
    areas = []
    for entry in _entries(value, key, ("path", "owns")):
        adrs = _strings(entry.get("adrs", []), f"{CATALOGUE_FILE}: {key} {entry['path']}: adrs")
        areas.append(Area(entry["path"], entry["owns"], adrs, entry.get("row"), entry.get("group")))
    for index, area in enumerate(areas):
        follows = area.group is not None and index > 0 and areas[index - 1].group == area.group
        if follows and area.row is not None:
            raise CatalogueError(f"{CATALOGUE_FILE}: {key} {area.path} follows the first entry of its group, so it takes no 'row'")
        if not follows and area.row is None:
            raise CatalogueError(f"{CATALOGUE_FILE}: {key} {area.path} needs 'row', the text of its row in AGENTS.md")
        if area.group is not None and not follows and any(a.group == area.group for a in areas[:index]):
            raise CatalogueError(f"{CATALOGUE_FILE}: the entries of group {area.group!r} must be next to each other")
    return tuple(areas)


def _tools(value: Any) -> Tuple[ToolPackage, ...]:
    return tuple(
        ToolPackage(
            e["name"], e["path"], _strings(e["import-names"], f"{CATALOGUE_FILE}: tools {e['name']}: import-names"),
            _strings(e.get("reaches", []), f"{CATALOGUE_FILE}: tools {e['name']}: reaches"),
        )
        for e in _entries(value, "tools", ("name", "path", "import-names"))
    )


SECTION_NAME_RE = re.compile(r"^[a-z][a-z0-9-]*$")


def _site(value: Any) -> Tuple[Section, ...]:
    sections = []
    for entry in _entries(value, "site", ("name", "title", "page", "layout", "order")):
        where = f"{CATALOGUE_FILE}: site {entry['name']}"
        if not SECTION_NAME_RE.match(entry["name"]):
            raise CatalogueError(f"{where}: the name must be lower case words joined by hyphens")
        if isinstance(entry["order"], bool) or not isinstance(entry["order"], int) or entry["order"] < 1:
            raise CatalogueError(f"{where}: 'order' must be a whole number from 1")
        if not entry["page"].startswith("docs/") or ".." in entry["page"].split("/"):
            raise CatalogueError(f"{where}: the page must be a path under docs/")
        sources = _strings(entry.get("sources", []), f"{where}: sources")
        if any(s.startswith("/") or ".." in s.split("/") for s in sources):
            raise CatalogueError(f"{where}: a source is a path from the repository root, never absolute or upward")
        sections.append(Section(entry["name"], entry["title"], entry["page"], entry["layout"], entry["order"], sources))
    for field_name in ("name", "title", "page", "order"):
        values = [getattr(s, field_name) for s in sections]
        if len(set(values)) != len(values):
            raise CatalogueError(f"{CATALOGUE_FILE}: two site sections have the same {field_name}")
    return tuple(sorted(sections, key=lambda s: s.order))


def _site_problems(catalogue: Catalogue) -> List[str]:
    """Problems between the site's sections and the tree: a missing page, layout or source."""
    problems = []
    for s in catalogue.site:
        if not (catalogue.root / s.page).is_file():
            problems.append(f"site {s.name}: page {s.page} does not exist")
        if s.layout != "none" and not (catalogue.root / "docs" / "_layouts" / f"{s.layout}.html").is_file():
            problems.append(f"site {s.name}: layout {s.layout!r} is not a file of docs/_layouts")
        for source in s.sources:
            if not (catalogue.root / source).exists():
                problems.append(f"site {s.name}: source {source} does not exist")
    return problems


def load(root: Path | str | None = None) -> Catalogue:
    """Read and validate the whole catalogue."""
    base = find_root(root)
    data = _read(base / CATALOGUE_FILE)
    for key, value in data.items():
        if key not in ROOT_KEYS and key not in ENTRY_KEYS:
            raise CatalogueError(f"{CATALOGUE_FILE}: unknown key {key!r}")
        if key in ENTRY_KEYS:
            continue
        unknown = set(value) - ROOT_KEYS[key]
        if unknown:
            raise CatalogueError(f"{CATALOGUE_FILE}: unknown key(s) {', '.join(sorted(unknown))} in [{key}]")
    conventions = data.get("conventions", {})
    kinds = conventions.get("kinds", {})
    _check_release(conventions.get("release"), kinds)
    names = _strings(data.get("catalogue", {}).get("modules", []), f"{CATALOGUE_FILE}: [catalogue] modules")
    if len(set(names)) != len(names):
        raise CatalogueError(f"{CATALOGUE_FILE}: a module is listed twice")
    modules: Dict[str, Module] = {}
    for name in names:
        path = Path("ontology") / name
        readme = base / path / "README.md"
        entry = _read(readme)
        where = f"{(path / 'README.md').as_posix()}"
        if set(entry) != {"module"}:
            raise CatalogueError(f"{where}: needs one catalogue entry, a [module] table, and nothing else")
        module = entry["module"]
        unknown = set(module) - MODULE_KEYS
        if unknown:
            raise CatalogueError(f"{where}: unknown key(s) {', '.join(sorted(unknown))} in [module]")
        kind = module.get("kind")
        if kind not in kinds:
            raise CatalogueError(f"{where}: kind {kind!r} is not one of the conventions' kinds ({', '.join(kinds)})")
        extract: Dict[str, Tuple[Path, ...]] = {}
        for role, files in module.get("extract", {}).items():
            if role not in EXTRACT_KEYS:
                raise CatalogueError(f"{where}: unknown extracted role {role!r}, expected one of {', '.join(EXTRACT_KEYS)}")
            extract[role] = tuple(path / f for f in _strings(files, f"{where}: extract.{role}"))
        imports = module.get("imports")
        modules[name] = Module(
            name=name,
            path=path,
            kind=kind,
            roles=_strings(module.get("roles", []), f"{where}: roles"),
            imports=None if imports is None else _strings(imports, f"{where}: imports"),
            extract=extract,
        )
    generated = data.get("generated", {})
    return Catalogue(
        base, conventions, modules,
        _areas(data.get("roots", []), "roots"), _areas(data.get("docs", []), "docs"), _tools(data.get("tools", [])),
        _strings(generated.get("paths", []), f"{CATALOGUE_FILE}: [generated] paths"),
        _site(data.get("site", [])),
    )


def _walk(directory: Path, suffixes: Sequence[str]) -> List[Path]:
    """Files under ``directory`` ending in one of ``suffixes``, skipping hidden, build and cache directories."""
    found = []
    for base, names, files in os.walk(directory):
        names[:] = sorted(n for n in names if not n.startswith(".") and n not in SCAN_SKIP_DIRS and not n.endswith(".egg-info"))
        found += [Path(base) / f for f in sorted(files) if f.endswith(tuple(suffixes))]
    return found


def _path_problems(catalogue: Catalogue) -> List[str]:
    """Declared roots, documentation areas, tool packages and the paths a package reaches must exist, unless
    generated, and every tool package on disk must be declared."""
    root, problems = catalogue.root, []

    def missing(path: str, what: str) -> None:
        if not catalogue.is_generated(path) and not (root / path.rstrip("/")).exists():
            problems.append(f"{what} {path} does not exist, and is not under [generated] paths")

    for kind, areas in (("roots", catalogue.roots), ("docs", catalogue.docs)):
        for area in areas:
            missing(area.path, f"{kind} entry")
    for tool in catalogue.tools:
        missing(tool.path, f"tool package {tool.name}:")
        if not (root / tool.path / "pyproject.toml").is_file():
            problems.append(f"tool package {tool.name}: {tool.path} has no pyproject.toml")
        for reached in tool.reaches:
            missing(reached, f"tool package {tool.name} reaches")
    if catalogue.tools:
        declared = {t.path.rstrip("/") for t in catalogue.tools}
        for pyproject in _walk(root / "tools", ("pyproject.toml",)):
            package = pyproject.parent.relative_to(root).as_posix()
            if package not in declared:
                problems.append(f"{package} is a tool package (it has a pyproject.toml), but is not in the catalogue's tools")
    return problems


def _subdirectories(root: Path, directory: Path) -> set:
    """The subdirectories of a module that hold a file git does not ignore, so that local build output
    left in an ignored directory is not taken for a role. Outside git, every subdirectory on disk."""
    try:
        listed = subprocess.run(["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z", "--",
                                 directory.relative_to(root).as_posix()],
                                cwd=root, capture_output=True, text=True, check=True).stdout
    except (OSError, subprocess.CalledProcessError):
        return {p.name for p in directory.iterdir() if p.is_dir() and not p.name.startswith(".")}
    names = (Path(f).relative_to(directory.relative_to(root)).parts for f in listed.split("\0") if f)
    return {parts[0] for parts in names if len(parts) > 1 and not parts[0].startswith(".")}


def check(catalogue: Catalogue, scan: Optional["Scan"] = None) -> List[str]:
    """Problems between the catalogue and the tree, in both directions. Empty when they agree."""
    root, problems = catalogue.root, []
    known_roles = set(catalogue.conventions.get("roles", []))
    for module in catalogue.modules.values():
        directory = root / module.path
        on_disk = _subdirectories(root, directory)
        for role in sorted(set(module.roles) - on_disk):
            problems.append(f"{module.name}: declares role {role!r}, but {module.path.as_posix()}/{role} does not exist")
        for role in sorted(on_disk - set(module.roles)):
            problems.append(f"{module.name}: {module.path.as_posix()}/{role} exists, but is not one of its roles")
        for role, files in module.extract.items():
            for file in files:
                if not (root / file).is_file():
                    problems.append(f"{module.name}: extracts {file.as_posix()}, which does not exist")
                elif file.parts[len(module.path.parts)] != role:
                    problems.append(f"{module.name}: extracts {file.as_posix()} as {role}, outside its {role}/")
        for imported in module.imports or ():
            if imported not in catalogue.modules:
                problems.append(f"{module.name}: may import {imported!r}, which is not a module")
    declared = {root / m.path for m in catalogue.modules.values()}
    for readme in sorted((root / "ontology").glob("**/README.md")):
        directory = readme.parent
        if directory in declared or any(d in directory.parents for d in declared):
            continue
        if any((directory / role).is_dir() for role in known_roles):
            problems.append(f"{directory.relative_to(root).as_posix()} holds a module, but is not in the catalogue")
    return problems + _path_problems(catalogue) + _site_problems(catalogue) + (scan if scan is not None else bypass_scan(catalogue)).problems


@dataclass(frozen=True)
class Scan:
    found: Dict[str, int]    # file -> number of path constructions to a catalogued root
    known: Dict[str, str]    # file -> reason, from the exceptions file
    problems: List[str]


def _is_test(path: Path) -> bool:
    return path.name.startswith("test_") or path.name == "conftest.py" or "tests" in path.parts


def _first_segment(node: ast.AST) -> Optional[str]:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value.split("/", 1)[0]
    return None


def count_bypasses(source: str, names: frozenset) -> int:
    """Path constructions that name a catalogued root, as in ``base / "ontology"`` or ``Path("ontology/x")``."""
    count = 0
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")  # other files' invalid escapes are not this scan's to report
        tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
            count += _first_segment(node.right) in names
        elif isinstance(node, ast.Call) and node.args:
            func = node.func.id if isinstance(node.func, ast.Name) else getattr(node.func, "attr", "")
            count += func in ("Path", "PurePath", "PurePosixPath") and _first_segment(node.args[0]) in names
    return count


def bypass_scan(catalogue: Catalogue) -> Scan:
    """Non-test Python under tools/ that builds a path to a catalogued root itself (ADR-A121 decision 5).
    A listed file is reported. An unlisted file, a listed file that no longer occurs, and a technical debt
    row giving the wrong count are problems, so the list only shrinks. Tests are not scanned until after
    RC4 (ADR-A121, addendum of 2026-10-19), and the reader is not scanned."""
    root, problems = catalogue.root, []
    names = frozenset(a.path.rstrip("/").split("/", 1)[0] for a in (*catalogue.roots, *catalogue.docs))
    if not names:
        return Scan({}, {}, [])
    found: Dict[str, int] = {}
    for file in _walk(root / "tools", (".py",)):
        relative = file.relative_to(root)
        if _is_test(relative) or relative.as_posix() == "tools/lattice_repo_catalogue.py":
            continue
        try:
            count = count_bypasses(file.read_text(encoding="utf-8"), names)
        except SyntaxError as error:
            problems.append(f"{relative.as_posix()}: the bypass scan cannot parse it ({error.msg}, line {error.lineno})")
            continue
        if count:
            found[relative.as_posix()] = count
    known: Dict[str, str] = {}
    listing = root / EXCEPTIONS_FILE
    for number, line in enumerate(listing.read_text(encoding="utf-8").splitlines() if listing.is_file() else [], 1):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        path, bar, reason = (part.strip() for part in line.partition("|"))
        if not bar or not reason:
            problems.append(f"{EXCEPTIONS_FILE}:{number}: write 'path | reason', every exception has a reason")
        elif path in known:
            problems.append(f"{EXCEPTIONS_FILE}:{number}: {path} is listed twice")
        else:
            known[path] = reason
    for path in sorted(set(found) - set(known)):
        problems.append(
            f"{path} builds a path to a catalogued root {found[path]} time(s). Ask the reader instead, or, for a known "
            f"case, list it in {EXCEPTIONS_FILE} with a reason"
        )
    for path in sorted(set(known) - set(found)):
        problems.append(f"{EXCEPTIONS_FILE} lists {path}, which no longer builds such a path. Remove it from the list")
    name, debt = Path(EXCEPTIONS_FILE).name, root / DEBT_FILE
    rows = [r for r in debt.read_text(encoding="utf-8").splitlines() if name in r] if debt.is_file() else []
    if listing.is_file() and len(rows) != 1:  # a tree with no exceptions file has no row to check
        problems.append(f"{DEBT_FILE} needs one row that names {name} and says 'lists N files'")
    elif listing.is_file():
        stated = re.search(r"lists (\d+) files", rows[0])
        if stated is None or int(stated.group(1)) != len(known):
            says = f"lists {stated.group(1)} files" if stated else "gives no count"
            problems.append(f"the technical debt row for {name} must say 'lists {len(known)} files', and {says}")
    return Scan(found, known, problems)


def where_things_are(catalogue: Catalogue) -> str:
    """AGENTS.md's "Where things are" table: the roots, then the documentation areas. A group is one row."""
    lines, areas = ["| Root | Owns |", "|---|---|"], [*catalogue.roots, *catalogue.docs]
    for index, area in enumerate(areas):
        if area.group is not None and index > 0 and areas[index - 1].group == area.group:
            continue
        members = [a.path for a in areas if a.group == area.group] if area.group is not None else [area.path]
        lines.append(f"| {', '.join(f'`{p}`' for p in members)} | {area.row} |")
    return "\n".join(lines)


def _dump(catalogue: Catalogue) -> Dict[str, Any]:
    return {
        "root": catalogue.root.as_posix(),
        "conventions": catalogue.conventions,
        "modules": {
            m.name: {
                "path": m.path.as_posix(),
                "kind": m.kind,
                "roles": list(m.roles),
                "imports": None if m.imports is None else list(m.imports),
                "extract": {role: [f.as_posix() for f in files] for role, files in m.extract.items()},
            }
            for m in catalogue.modules.values()
        },
        "roots": [vars(a) for a in catalogue.roots],
        "docs": [vars(a) for a in catalogue.docs],
        "tools": [vars(t) for t in catalogue.tools],
        "generated": list(catalogue.generated),
        "site": [vars(s) | {"sources": list(s.sources)} for s in catalogue.site],
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Read the repository catalogue (ADR-A121)")
    parser.add_argument("--root", default=None, help="the repository root, if not found from the working directory")
    commands = parser.add_subparsers(dest="command", required=True)
    for name, text in (("path", "print a role's directory"), ("paths", "print a role's extracted files, in order")):
        sub = commands.add_parser(name, help=text)
        sub.add_argument("module")
        sub.add_argument("role")
    commands.add_parser("check", help="fail when the catalogue and the tree disagree")
    dump = commands.add_parser("dump", help="print the resolved catalogue")
    dump.add_argument("--json", action="store_true", required=True)
    args = parser.parse_args(argv)
    try:
        catalogue = load(args.root)
        if args.command == "path":
            print(catalogue.module(args.module).directory(args.role).as_posix())
        elif args.command == "paths":
            for file in catalogue.module(args.module).files(args.role):
                print(file.as_posix())
        elif args.command == "dump":
            print(json.dumps(_dump(catalogue), indent=2))
        else:
            scan = bypass_scan(catalogue)
            for path, reason in scan.known.items():
                if path in scan.found:
                    print(f"bypass scan, known: {path} builds {scan.found[path]} path(s) itself ({reason})")
            problems = check(catalogue, scan)
            for problem in problems:
                print(f"CATALOGUE {problem}", file=sys.stderr)
            if problems:
                return 1
            print(f"repository catalogue: {len(catalogue.modules)} module(s) and {len(catalogue.tools)} tool package(s) "
                  f"agree with the tree. Bypass scan: {len(scan.known)} known file(s)")
    except CatalogueError as error:
        print(f"CATALOGUE {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
