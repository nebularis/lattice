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
import json
import os
import re
import sys
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

CATALOGUE_FILE = "repository-catalogue.md"
BLOCK_TAG = "toml repository-catalogue"
ANY_FENCE_RE = re.compile(r"^ {0,3}(?P<fence>`{3,}|~{3,})(?P<info>.*)$")

# The schema. A key not listed here is an error, so later keys (for example a downstream
# catalogue's ``extends``, ADR-A121 decision 7) can be added without ambiguity.
ROOT_KEYS = {"catalogue": {"schema", "modules"}, "conventions": {"roles", "kinds", "versioned", "artefact-directories"}}
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
class Catalogue:
    root: Path
    conventions: Dict[str, Any]
    modules: Dict[str, Module]

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


def load(root: Path | str | None = None) -> Catalogue:
    """Read and validate the whole catalogue."""
    base = find_root(root)
    data = _read(base / CATALOGUE_FILE)
    for key, value in data.items():
        if key not in ROOT_KEYS:
            raise CatalogueError(f"{CATALOGUE_FILE}: unknown key {key!r}")
        unknown = set(value) - ROOT_KEYS[key]
        if unknown:
            raise CatalogueError(f"{CATALOGUE_FILE}: unknown key(s) {', '.join(sorted(unknown))} in [{key}]")
    conventions = data.get("conventions", {})
    kinds = conventions.get("kinds", {})
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
    return Catalogue(base, conventions, modules)


def check(catalogue: Catalogue) -> List[str]:
    """Problems between the catalogue and the tree, in both directions. Empty when they agree."""
    root, problems = catalogue.root, []
    known_roles = set(catalogue.conventions.get("roles", []))
    for module in catalogue.modules.values():
        directory = root / module.path
        on_disk = {p.name for p in directory.iterdir() if p.is_dir() and not p.name.startswith(".")}
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
    return problems


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
            problems = check(catalogue)
            for problem in problems:
                print(f"CATALOGUE {problem}", file=sys.stderr)
            if problems:
                return 1
            print(f"repository catalogue: {len(catalogue.modules)} module(s) agree with the tree")
    except CatalogueError as error:
        print(f"CATALOGUE {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
