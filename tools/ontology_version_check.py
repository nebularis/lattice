# SPDX-License-Identifier: MPL-2.0
"""Ontology semantic versioning: narrow "changed but not bumped" check
(ADR-A86, docs/architecture/ontology-versioning-policy.md).

This does not classify a change as MAJOR/MINOR/PATCH -- that stays a contributor's
judgement call against the policy document's table. It checks one
narrow, mechanical fact: for every ``.ttl`` file under ``ontology/`` that
declares an ``owl:Ontology``, if the file's content differs from a base git
ref, at least one ``owl:versionIRI`` literal in the file must also differ.
"Content changed, version literal did not" is always a defect; "content
changed, version literal also changed" is not evaluated further here.

It also checks that every ontology document under a ``spec/`` or ``vocab/``
directory carries an ``owl:versionIRI`` at all. Examples and test fixtures
may declare ``owl:Ontology`` without one (ADR-A86 addendum, item 2).

A layer's ``shapes/`` and ``projection/`` directories declare no ontology,
so each carries a ``.version`` file holding one semantic version shared by
all its files. A change to any file in the directory must change its
``.version`` too, and the file must exist (ADR-A86 second addendum).

The modules the repository catalogue's ``[conventions.release]`` names are
released together (OD-D55). For them the per-document rules give way to three
others: every member document's ``owl:versionIRI`` ends with the release
number, every reference anywhere under ``ontology/`` to a member document's
version IRI names that number, and a change to any member's documents, shapes
or projections since the base ref needs a new release number. A member's
artefact directories have no ``.version`` file, since the number lives in the
catalogue (OD-D59).

Usage::

    python tools/ontology_version_check.py [--root .] [--base-ref HEAD]
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import tomllib
from pathlib import Path
from typing import Optional, Set

import lattice_repo_catalogue

CATALOGUE = lattice_repo_catalogue.load()
ROOT = CATALOGUE.root
ONTOLOGY_ROOT = "ontology"

VERSION_IRI_RE = re.compile(r"owl:versionIRI\s+<([^>]+)>")
ONTOLOGY_MARKER_RE = re.compile(r"\bowl:Ontology\b")
# Which documents carry an owl:versionIRI, and which directories a .version file, are the
# repository catalogue's conventions (ADR-A121).
VERSIONED_DIRECTORIES = frozenset(CATALOGUE.conventions["versioned"])
ARTEFACT_DIRECTORIES = tuple(CATALOGUE.conventions["artefact-directories"])
VERSION_FILE = ".version"
SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")


def repository_files(root: Path, suffix: str) -> list[Path]:
    """Every file under ``ontology/`` ending in ``suffix`` that git tracks or
    would track: tracked files and untracked files that are not ignored.
    Ignored build output (``**/execution/*``) exists only on the machine that
    built it, so no check may depend on it."""
    result = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "--", ONTOLOGY_ROOT],
        cwd=root, capture_output=True, text=True, check=True,
    )
    paths = {root / line for line in result.stdout.splitlines() if line.endswith(suffix)}
    return sorted(path for path in paths if path.exists())


def find_in_scope_ttl_files(root: Path) -> list[Path]:
    """Every ``.ttl`` file under ``ontology/`` that declares an
    ``owl:Ontology`` somewhere in its content. A file with no such
    declaration (a shapes file, a bare vocab-individuals file, an example
    fixture with no ontology header of its own) carries no ``owl:versionIRI``
    of its own and is out of this check's scope, per the versioning-unit
    rule in the policy document."""
    files: list[Path] = []
    for path in repository_files(root, ".ttl"):
        text = path.read_text(encoding="utf-8", errors="ignore")
        if ONTOLOGY_MARKER_RE.search(text):
            files.append(path)
    return files


def git_show(root: Path, ref: str, relative_posix_path: str) -> Optional[str]:
    """The file's content at ``ref``, or ``None`` if it did not exist there
    (a newly added file has nothing to compare against, and is not a version
    omission by definition)."""
    result = subprocess.run(
        ["git", "show", f"{ref}:{relative_posix_path}"],
        cwd=root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="ignore",
    )
    if result.returncode != 0:
        return None
    return result.stdout


def extract_version_iris(text: str) -> Set[str]:
    return set(VERSION_IRI_RE.findall(text))


RELEASE_DIRECTORIES = ("spec", "vocab", "shapes", "projection")


def release(root: Path) -> tuple[Optional[str], list[str]]:
    """The release number and its members' directories, relative to the root, or (None, []) where the
    root has no catalogue or no release."""
    if not (root / lattice_repo_catalogue.CATALOGUE_FILE).is_file():
        return None, []
    catalogue = lattice_repo_catalogue.load(root)
    return catalogue.release_version, [m.path.as_posix() for m in catalogue.release_members()]


def is_member(relative: str, members: list[str]) -> bool:
    return any(relative.startswith(f"{member}/") for member in members)


def base_release(root: Path, base_ref: str) -> Optional[str]:
    """The release number at the base ref, read from that commit's catalogue."""
    text = git_show(root, base_ref, lattice_repo_catalogue.CATALOGUE_FILE)
    if text is None:
        return None
    for block in lattice_repo_catalogue.blocks(text):
        found = tomllib.loads(block).get("conventions", {}).get("release", {}).get("version")
        if found:
            return found
    return None


def check_release(root: Path) -> list[str]:
    """Every member document carries the release number, and every reference to a member document's
    version IRI names it."""
    version, members = release(root)
    if version is None:
        return []
    problems: list[str] = []
    bases: Set[str] = set()
    for path in find_in_scope_ttl_files(root):
        relative = path.relative_to(root).as_posix()
        if not (is_member(relative, members) and requires_version_iri(Path(relative))):
            continue
        for iri in extract_version_iris(path.read_text(encoding="utf-8")):
            base, _, number = iri.rpartition("/")
            bases.add(base)
            if number != version:
                problems.append(f"{relative}: owl:versionIRI {iri} is not at the release, {version}")
    pattern = re.compile("(" + "|".join(re.escape(b) for b in sorted(bases)) + r")/(\d+\.\d+\.\d+)\b") if bases else None
    for path in sorted(repository_files(root, ".ttl") + repository_files(root, ".md")):
        relative = path.relative_to(root).as_posix()
        if not relative.startswith(f"{ONTOLOGY_ROOT}/") or pattern is None:
            continue
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            for match in pattern.finditer(line):
                if match.group(2) != version:
                    problems.append(f"{relative}:{number}: names {match.group(0)}, not the release, {version}")
    for directory in artefact_directories(root):
        if is_member(directory + "/", members) and (root / directory / VERSION_FILE).exists():
            problems.append(f"{directory}/{VERSION_FILE}: a release member's directory carries no version of its own")
    return problems


def check_release_bumped(root: Path, base_ref: str) -> list[str]:
    """A change to any member's documents, shapes or projections since the base ref needs a new release."""
    version, members = release(root)
    if version is None or base_release(root, base_ref) != version:
        return []
    paths = [f"{m}/{d}" for m in members for d in RELEASE_DIRECTORIES if (root / m / d).is_dir()]
    changed = set(git_lines(root, "diff", "--name-only", base_ref, "--", *paths)) if paths else set()
    changed |= set(git_lines(root, "ls-files", "--others", "--exclude-standard", "--", *paths)) if paths else set()
    if not changed:
        return []
    return [f"{len(changed)} release member file(s) changed since {base_ref}, for example {sorted(changed)[0]}, "
            f"but the release is still {version}. Run mise run release:prepare -- <next version>"]


def requires_version_iri(relative: Path) -> bool:
    """A document under a ``spec/`` or ``vocab/`` directory is a published
    ontology document and must carry its own version IRI."""
    return bool(VERSIONED_DIRECTORIES & set(relative.parts[:-1]))


def check_unversioned(root: Path) -> list[str]:
    """Return one message per ontology document that must carry an
    ``owl:versionIRI`` and does not, and per artefact directory without a
    valid ``.version``."""
    problems: list[str] = []
    _, members = release(root)
    for directory in artefact_directories(root):
        if is_member(directory + "/", members):
            continue
        version = artefact_version(root, directory)
        if version is None or not SEMVER_RE.match(version):
            problems.append(f"{directory}/{VERSION_FILE}: missing, or not a semantic version X.Y.Z")
    for path in find_in_scope_ttl_files(root):
        relative = path.relative_to(root)
        if not requires_version_iri(relative):
            continue
        if not extract_version_iris(path.read_text(encoding="utf-8")):
            problems.append(f"{relative.as_posix()}: declares owl:Ontology without owl:versionIRI")
    return problems


def git_lines(root: Path, *args: str) -> list[str]:
    result = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, check=True)
    return result.stdout.splitlines()


def artefact_directories(root: Path) -> list[str]:
    """Every ``shapes/`` or ``projection/`` directory beside a layer's
    ``spec/`` directory. Examples and fixtures have no ``spec/``."""
    layers = set()
    for path in find_in_scope_ttl_files(root):
        parts = path.relative_to(root).parts
        if "spec" in parts[:-1]:
            layers.add("/".join(parts[: parts.index("spec")]))
    return sorted(f"{layer}/{name}" for layer in layers for name in ARTEFACT_DIRECTORIES if (root / layer / name).is_dir())


def artefact_files(root: Path, directory: str) -> list[str]:
    """The directory's tracked or trackable files, without its ``.version``."""
    files = git_lines(root, "ls-files", "--cached", "--others", "--exclude-standard", "--", directory)
    return sorted({f for f in files if Path(f).name != VERSION_FILE and (root / f).exists()})


def artefact_version(root: Path, directory: str) -> Optional[str]:
    path = root / directory / VERSION_FILE
    return path.read_text(encoding="utf-8").strip() if path.exists() else None


def check_artefacts(root: Path, base_ref: str) -> list[str]:
    """Return one message per artefact directory whose files changed relative
    to ``base_ref`` while its ``.version`` did not."""
    problems: list[str] = []
    _, members = release(root)
    for directory in artefact_directories(root):
        if is_member(directory + "/", members):
            continue
        version_path = f"{directory}/{VERSION_FILE}"
        changed = set(git_lines(root, "diff", "--name-only", base_ref, "--", directory))
        changed |= set(git_lines(root, "ls-files", "--others", "--exclude-standard", "--", directory))
        changed.discard(version_path)
        old = git_show(root, base_ref, version_path)
        if changed and old is not None and old.strip() == artefact_version(root, directory):
            problems.append(f"{', '.join(sorted(changed))}: changed since {base_ref} but {version_path} is unchanged ({old.strip()})")
    return problems


def check(root: Path, base_ref: str) -> list[str]:
    """Return one message per file whose content changed relative to
    ``base_ref`` but whose set of ``owl:versionIRI`` literals did not."""
    problems: list[str] = []
    _, members = release(root)
    for path in find_in_scope_ttl_files(root):
        relative = path.relative_to(root).as_posix()
        if is_member(relative, members):
            continue  # released together, checked by check_release_bumped
        old_text = git_show(root, base_ref, relative)
        if old_text is None:
            continue  # new file: nothing to have forgotten to bump
        new_text = path.read_text(encoding="utf-8")
        if old_text == new_text:
            continue  # untouched
        old_versions = extract_version_iris(old_text)
        new_versions = extract_version_iris(new_text)
        if old_versions and old_versions == new_versions:
            problems.append(
                f"{relative}: content changed since {base_ref} but "
                f"owl:versionIRI is unchanged ({', '.join(sorted(old_versions))})"
            )
    return problems


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Flag ontology files whose content changed without a version bump"
    )
    parser.add_argument("--root", default=str(ROOT), help="repository root (default: repo root)")
    parser.add_argument(
        "--base-ref",
        default="HEAD",
        help="git ref to compare the working tree against (default: HEAD)",
    )
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    unbumped = check(root, args.base_ref) + check_artefacts(root, args.base_ref) + check_release_bumped(root, args.base_ref)
    unversioned = check_unversioned(root)
    released = check_release(root)

    for problem in unbumped:
        print(f"UNBUMPED {problem}", file=sys.stderr)
    for problem in unversioned:
        print(f"UNVERSIONED {problem}", file=sys.stderr)
    for problem in released:
        print(f"RELEASE {problem}", file=sys.stderr)
    if unbumped or unversioned or released:
        print(
            f"{len(unbumped)} ontology file(s) changed without a version bump "
            f"relative to {args.base_ref}, {len(unversioned)} without a version IRI, {len(released)} off the release. "
            "See docs/architecture/ontology-versioning-policy.md.",
            file=sys.stderr,
        )
        return 1

    in_scope_count = len(find_in_scope_ttl_files(root))
    print(f"{in_scope_count} in-scope ontology document(s) checked against {args.base_ref}: no unbumped changes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
