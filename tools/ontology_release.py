# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""Prepare a release of the ontologies released together (OD-D55 to OD-D59).

Every member module's documents take the release's number in one substitution. For each member document's
version IRI base, every ``<base>/X.Y.Z`` under ``ontology/``, in Turtle and in the READMEs that generate it,
and in the tool packages' sources, becomes ``<base>/<version>``. Imports, the applied modules' pins and the
literate READMEs' header tables therefore move together. The catalogue's number is set, member artefact
directories lose any ``.version`` file, and the XML catalogs and the release register are regenerated. Release
notes, and tests that name a version, are the author's. The tag is the maintainer's to create.

Usage, from the repository root::

    mise run release:prepare -- 0.18.0
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path
from typing import Dict, Sequence

sys.path.insert(0, str(Path(__file__).resolve().parent))

import lattice_repo_catalogue  # noqa: E402
from ontology_version_check import (  # noqa: E402
    VERSION_FILE,
    artefact_directories,
    extract_version_iris,
    find_in_scope_ttl_files,
    is_member,
    release,
    requires_version_iri,
)

RELEASE_LINE_RE = re.compile(r'(?m)^(version\s*=\s*")(\d+\.\d+\.\d+)(")')


def member_bases(root: Path, members: list[str]) -> set[str]:
    """Every member document's version IRI without its number."""
    bases = set()
    for path in find_in_scope_ttl_files(root):
        relative = path.relative_to(root).as_posix()
        if is_member(relative, members) and requires_version_iri(Path(relative)):
            bases |= {iri.rpartition("/")[0] for iri in extract_version_iris(path.read_text(encoding="utf-8"))}
    return bases


def candidates(root: Path) -> list[Path]:
    """The files that can name a member's version: Turtle and READMEs under ``ontology/``, and the tool
    packages' sources, never their tests, which assert history as well as the present."""
    listed = subprocess.run(["git", "ls-files", "--cached", "--others", "--exclude-standard", "--", "ontology", "tools"],
                            cwd=root, capture_output=True, text=True, check=True).stdout.splitlines()
    keep = []
    for line in listed:
        path = Path(line)
        if line.startswith("ontology/") and path.suffix in (".ttl", ".md"):
            keep.append(root / path)
        elif line.startswith("tools/") and "/src/" in line and path.suffix == ".py" and not path.name.startswith("test_"):
            keep.append(root / path)
    return [p for p in keep if p.is_file()]


def prepare(root: Path, version: str) -> Dict[str, int]:
    """Rewrite every member reference to ``version``. Returns the number of replacements per file."""
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        raise ValueError(f"{version!r} is not X.Y.Z")
    current, members = release(root)
    if current is None:
        raise ValueError("the catalogue's [conventions.release] names no release")
    bases = member_bases(root, members)
    pattern = re.compile("(" + "|".join(re.escape(b) for b in sorted(bases)) + r")/\d+\.\d+\.\d+\b")
    counts: Dict[str, int] = {}
    for path in candidates(root):
        text = path.read_text(encoding="utf-8")
        rewritten, count = pattern.subn(lambda m: f"{m.group(1)}/{version}", text)
        if rewritten != text:
            path.write_text(rewritten, encoding="utf-8", newline="\n")
            counts[path.relative_to(root).as_posix()] = count
    catalogue = root / lattice_repo_catalogue.CATALOGUE_FILE
    text = catalogue.read_text(encoding="utf-8")
    block = text[text.index("[conventions.release]"):]
    updated = RELEASE_LINE_RE.sub(lambda m: f"{m.group(1)}{version}{m.group(3)}", block, count=1)
    catalogue.write_text(text[: len(text) - len(block)] + updated, encoding="utf-8", newline="\n")
    for directory in artefact_directories(root):
        if is_member(directory + "/", members) and (root / directory / VERSION_FILE).exists():
            (root / directory / VERSION_FILE).unlink()
    return counts


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Prepare a release of the ontologies released together")
    parser.add_argument("command", choices=("prepare",))
    parser.add_argument("version", help="the release number, X.Y.Z")
    parser.add_argument("--root", default=None)
    args = parser.parse_args(argv)
    root = lattice_repo_catalogue.find_root(args.root)
    try:
        counts = prepare(root, args.version)
    except ValueError as error:
        print(f"RELEASE {error}", file=sys.stderr)
        return 1
    for path, count in sorted(counts.items()):
        print(f"rewrote {path} ({count})")
    for command in (["tools/ontology_catalog.py", "write"], ["tools/ontology_releases.py", "write"]):
        subprocess.run([sys.executable, *command], cwd=root, check=True)
    print(f"release {args.version} prepared in {len(counts)} file(s). Write each layer's release notes, run the"
          f" checks, commit, and the maintainer tags ontologies-v{args.version}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
