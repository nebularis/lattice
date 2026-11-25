# SPDX-License-Identifier: MPL-2.0
"""Check that the text of every licence the repository's files name is in the licence texts root (ADR-A155).

A licence is named by the SPDX header in the first lines of a tracked file, or by an annotation of ``REUSE.toml``. Each named
identifier has its text at ``<identifier>.txt`` in the root the catalogue names ``licences``, and that root holds no text no file
names.

Usage, from the repository root::

    python tools/check_licences.py
"""

from __future__ import annotations

import re
import subprocess
import sys
import tomllib
from pathlib import Path
from typing import Dict, Iterable, List, Set

sys.path.insert(0, str(Path(__file__).resolve().parent))

import lattice_repo_catalogue  # noqa: E402

HEADER_LINES = 10
HEADER_RE = re.compile(r"SPDX-License-Identifier:\s*(?P<expression>[A-Za-z0-9.+()\- ]+?)\s*(?:-->|\*/|$)")
OPERATORS = {"AND", "OR", "WITH"}


def identifiers(expression: str) -> Set[str]:
    """The licence identifiers of an SPDX expression, without its operators and brackets."""
    return {token for token in re.split(r"[\s()]+", expression) if token and token not in OPERATORS}


def header_identifiers(text: str) -> Set[str]:
    """The identifiers an SPDX header in the first lines of a file names."""
    found: Set[str] = set()
    for line in text.splitlines()[:HEADER_LINES]:
        match = HEADER_RE.search(line)
        if match:
            found |= identifiers(match.group("expression"))
    return found


def reuse_identifiers(text: str) -> Set[str]:
    """The identifiers the annotations of a ``REUSE.toml`` name."""
    found: Set[str] = set()
    for annotation in tomllib.loads(text).get("annotations", []):
        value = annotation.get("SPDX-License-Identifier")
        for expression in [value] if isinstance(value, str) else (value or []):
            found |= identifiers(expression)
    return found


def tracked(root: Path) -> List[Path]:
    out = subprocess.run(["git", "ls-files", "-z"], cwd=root, check=True, capture_output=True).stdout
    return [root / name for name in out.decode("utf-8").split("\0") if name]


def named(root: Path, files: Iterable[Path], texts: Path) -> Dict[str, List[str]]:
    """Each identifier named, with the files that name it."""
    names: Dict[str, List[str]] = {}
    for path in files:
        if not path.is_file() or texts in path.parents:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        found = reuse_identifiers(text) if path.relative_to(root).as_posix() == "REUSE.toml" else header_identifiers(text)
        for identifier in found:
            names.setdefault(identifier, []).append(path.relative_to(root).as_posix())
    return names


def problems(root: Path, files: Iterable[Path], texts: Path) -> List[str]:
    names = named(root, files, texts)
    held = {p.stem for p in texts.glob("*.txt")} if texts.is_dir() else set()
    found = []
    for identifier in sorted(set(names) - held):
        example = sorted(names[identifier])[0]
        found.append(f"{identifier} is named by {len(names[identifier])} file(s), such as {example}, and has no text at {texts.name}/{identifier}.txt")
    for identifier in sorted(held - set(names)):
        found.append(f"{texts.name}/{identifier}.txt is the text of a licence no tracked file names")
    return found


def main() -> int:
    root = lattice_repo_catalogue.find_root()
    texts = root / lattice_repo_catalogue.load(root).area("licences")
    found = problems(root, tracked(root), texts)
    for problem in found:
        print(problem)
    if not found:
        print(f"licence texts: every identifier named has its text in {texts.name}/")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
