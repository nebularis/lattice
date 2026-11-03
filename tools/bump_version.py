# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""Bump ontology versions, the substrate's release or one module released on its own.

Which way a module moves is fixed by its catalogue kind (ADR-A129 and its addendum of 2026-10-26):

- the substrate, the kinds in ``[conventions.release]``, is one release, every member's documents at one
  number, moved together by ``ontology_release.prepare``, with no ``.version`` file in a member's shapes
- every other module, standalone or applied, is released on its own. All of its spec documents move in
  unison (ADR-A120), its vocab documents are a separate unit, and its ``shapes/`` directory has one
  ``.version`` shared by every file in it (ADR-A86, the versioning policy)

The bump rewrites the version IRIs and ``.version`` files and renames each changed README's
``- **Unreleased**.`` release-note lead to the number (STD-125). It prints one line per literate README
whose generated files must be extracted again, ``<README>\\t<module>``, for ``extract_bumped.py``. The
mise task ``version:bump`` runs both, then regenerates the XML catalogs and the release register. What
it did and what is left for the author goes to stderr.

Usage, from the repository root::

    mise run version:bump -- --increment minor                                  # the substrate
    mise run version:bump -- --layer-target persistence --increment minor --with-shapes
    mise run version:bump -- --layer-target persistence --only-shapes --increment minor
    mise exec -- python tools/bump_version.py --layer-target surface --new-version 1.0.0 | \\
        mise exec -- python tools/extract_bumped.py
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path
from typing import Iterable, Optional, Sequence

sys.path.insert(0, str(Path(__file__).resolve().parent))

import lattice_repo_catalogue  # noqa: E402
import ontology_release  # noqa: E402
from ontology_version_check import VERSION_FILE, extract_version_iris  # noqa: E402

SEMVER_RE = re.compile(r"\d+\.\d+\.\d+")
UNRELEASED = "- **Unreleased**."


class BumpError(ValueError):
    pass


def next_version(current: str, increment: Optional[str], new: Optional[str]) -> str:
    """The number after ``current``. At major version zero a breaking change is a minor (ADR-A113), which
    the author chooses by passing ``--increment minor``."""
    if new is not None:
        if not SEMVER_RE.fullmatch(new):
            raise BumpError(f"{new!r} is not X.Y.Z")
        if tuple(map(int, new.split("."))) <= tuple(map(int, current.split("."))):
            raise BumpError(f"{new} is not after the current {current}")
        return new
    major, minor, patch = map(int, current.split("."))
    return {"major": f"{major + 1}.0.0", "minor": f"{major}.{minor + 1}.0", "patch": f"{major}.{minor}.{patch + 1}"}[increment]


def module_files(root: Path, module: lattice_repo_catalogue.Module) -> list[Path]:
    """The module's own Turtle and Markdown, as git lists them, its tests left out as they assert history."""
    listed = subprocess.run(["git", "ls-files", "--cached", "--others", "--exclude-standard", "--", module.path.as_posix()],
                            cwd=root, capture_output=True, text=True, check=True).stdout.splitlines()
    return [root / p for p in listed if Path(p).suffix in (".ttl", ".md") and "/test/" not in f"/{p}" and (root / p).is_file()]


def spec_documents(root: Path, module: lattice_repo_catalogue.Module) -> list[Path]:
    if module.literate:
        return [root / p for p in module.files("spec")]
    return sorted((root / module.path / "spec").glob("*.ttl"))


def bump_spec(root: Path, module: lattice_repo_catalogue.Module, increment: Optional[str], new: Optional[str], log: list[str]) -> str:
    """Move every spec document of the module to one new number, in unison (ADR-A120)."""
    versions: dict[str, str] = {}
    for path in spec_documents(root, module):
        for iri in extract_version_iris(path.read_text(encoding="utf-8")):
            base, _, number = iri.rpartition("/")
            if SEMVER_RE.fullmatch(number):
                versions[base] = number
    if not versions:
        raise BumpError(f"{module.name} has no spec document with a version IRI")
    if len(set(versions.values())) > 1:
        raise BumpError(f"{module.name}'s spec documents carry different versions ({', '.join(f'{b}/{v}' for b, v in sorted(versions.items()))}), "
                        "and a layer's spec documents move in unison (ADR-A120). Bring them to one number with --new-version")
    current = next(iter(versions.values()))
    version = next_version(current, increment, new)
    pattern = re.compile("(" + "|".join(re.escape(b) for b in sorted(versions)) + r")/\d+\.\d+\.\d+\b")
    for path in module_files(root, module):
        text = path.read_text(encoding="utf-8")
        rewritten, count = pattern.subn(lambda m: f"{m.group(1)}/{version}", text)
        if count:
            path.write_text(rewritten, encoding="utf-8", newline="\n")
            log.append(f"rewrote {path.relative_to(root).as_posix()} ({count})")
    log.append(f"{module.name}: {len(versions)} spec document(s) {current} -> {version}")
    elsewhere = subprocess.run(["git", "grep", "-l", "-E", "(" + "|".join(re.escape(b) for b in versions) + f")/{re.escape(current)}\\b", "--",
                                ":!" + module.path.as_posix(), ":!*catalog-v001.xml", ":!docs/architecture/ontology-releases.md"],
                               cwd=root, capture_output=True, text=True).stdout.split()
    if elsewhere:
        log.append(f"still pinned at {current}, each pin its own module's choice: {', '.join(elsewhere)}")
    return version


def bump_shapes(root: Path, module: lattice_repo_catalogue.Module, increment: Optional[str], new: Optional[str], log: list[str]) -> str:
    """Move the module's shapes directory, whose one ``.version`` every shapes file shares."""
    path = root / module.path / "shapes" / VERSION_FILE
    if not path.is_file():
        raise BumpError(f"{module.name} has no {path.relative_to(root).as_posix()}")
    current = path.read_text(encoding="utf-8").strip()
    version = next_version(current, increment, new)
    path.write_text(version + "\n", encoding="utf-8", newline="\n")
    log.append(f"{module.name}: shapes {current} -> {version}")
    return version


def name_release(root: Path, readme: Path, version: str, log: list[str]) -> None:
    """Rename the README's Unreleased release-note lead to the number (STD-125)."""
    text = readme.read_text(encoding="utf-8")
    rel = readme.relative_to(root).as_posix()
    if UNRELEASED in text:
        readme.write_text(text.replace(UNRELEASED, f"- **{version}**.", 1), encoding="utf-8", newline="\n")
        log.append(f"{rel}: the Unreleased notes are now {version}'s")
    else:
        log.append(f"{rel}: no Unreleased notes. Write {version}'s, classed as the versioning policy says (STD-293)")


def bump(root: Path, layer: Optional[str], increment: Optional[str], new: Optional[str], shapes: str, log: list[str]) -> list[tuple[str, str]]:
    """Make the bump and return ``(README, module)`` for each literate README to extract again.
    ``shapes`` is ``"no"``, ``"with"`` or ``"only"``."""
    catalogue = lattice_repo_catalogue.load(root)
    members = {m.name for m in catalogue.release_members()}
    if layer is None:
        if shapes != "no":
            raise BumpError("the substrate's shapes carry the release number and have no .version file (ADR-A129). "
                            "--with-shapes and --only-shapes are for --layer-target")
        version = next_version(catalogue.release_version, increment, new)
        counts = ontology_release.prepare(root, version)
        log += [f"rewrote {path} ({count})" for path, count in sorted(counts.items())]
        log.append(f"the substrate release {catalogue.release_version} -> {version}. The maintainer tags ontologies-v{version}")
        out = []
        for module in catalogue.modules.values():
            readme = module.path / "README.md"
            if module.literate and (module.name in members or readme.as_posix() in counts):
                out.append((readme.as_posix(), module.name))
            if module.name in members:
                name_release(root, root / readme, version, log)
            elif readme.as_posix() in counts or any(p.startswith(module.path.as_posix() + "/") for p in counts):
                log.append(f"{module.name} re-pinned its substrate imports, so it takes its own bump: "
                           f"--layer-target {module.name}, at the imported change's level (ADR-A86)")
        return out
    module = catalogue.modules.get(layer)
    if module is None:
        raise BumpError(f"{layer!r} is no module of the catalogue. Modules: {', '.join(sorted(catalogue.modules))}")
    if layer in members:
        raise BumpError(f"{layer} is {module.kind}, a member of the substrate release {catalogue.release_version}, which moves together. "
                        "Run without --layer-target")
    readme = root / module.path / "README.md"
    if shapes != "only":
        version = bump_spec(root, module, increment, new, log)
        if readme.is_file():
            name_release(root, readme, version, log)
        log.append(f"tag each document that moved as <name>-v{version} once merged, as `mise run build:ontology-releases` lists")
    if shapes != "no":
        bump_shapes(root, module, increment, new, log)
    return [(readme.relative_to(root).as_posix(), module.name)] if module.literate and shapes != "only" else []


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter,
                                     epilog="Prints '<README>\\t<module>' per README to extract, for tools/extract_bumped.py.")
    parser.add_argument("--layer-target", metavar="MODULE",
                        help="a module released on its own, by its catalogue name, e.g. persistence or applied/insurance/peril. "
                             "Without it, the substrate release moves")
    by = parser.add_mutually_exclusive_group(required=True)
    by.add_argument("--increment", choices=("major", "minor", "patch"),
                    help="from the current number. At major version zero a breaking change is a minor (ADR-A113)")
    by.add_argument("--new-version", metavar="X.Y.Z", help="an explicit number, after the current one")
    shapes = parser.add_mutually_exclusive_group()
    shapes.add_argument("--with-shapes", action="store_true", help="also move the module's shapes/.version, by the same increment or to the same number")
    shapes.add_argument("--only-shapes", action="store_true", help="move the module's shapes/.version alone")
    parser.add_argument("--root", default=None)
    args = parser.parse_args(argv)
    root = lattice_repo_catalogue.find_root(args.root)
    log: list[str] = []
    try:
        readmes = bump(root, args.layer_target, args.increment, args.new_version,
                       "only" if args.only_shapes else "with" if args.with_shapes else "no", log)
    except BumpError as error:
        print(f"BUMP {error}", file=sys.stderr)
        return 1
    for line in log:
        print(line, file=sys.stderr)
    for readme, module in readmes:
        print(f"{readme}\t{module}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
