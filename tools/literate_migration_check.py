# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""Prove that migrating a module's README to the layout of ADR-A126 changed none of its graphs (OD-D9).

For every file the module's repository catalogue entry says its README generates, the file in the working
tree and the file at a git ref are parsed and compared as graphs. Each difference is a triple only at the
ref or only in the tree, written as a line with canonical blank node labels. A reconciliation file lists the
differences the maintainer has approved, one such line each, and the check passes only when every
difference is listed and every listed line is still a difference.

Usage, from the repository root::

    mise run check:literate-migration -- eligibility <ref>
    mise run check:literate-migration -- eligibility <ref> --reconciliations <file>
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from typing import List, Optional, Sequence, Set

from rdflib import Graph
from rdflib.compare import graph_diff, to_isomorphic

sys.path.insert(0, str(Path(__file__).resolve().parent))

import lattice_repo_catalogue  # noqa: E402


def _graph(text: str) -> Graph:
    return Graph().parse(data=text, format="turtle")


def differences(path: str, at_ref: Optional[str], in_tree: Optional[str]) -> List[str]:
    """The lines describing how one file's graph differs between a ref and the tree, sorted."""
    if at_ref is None or in_tree is None:
        return [f"{path} {'added in the tree' if at_ref is None else 'removed from the tree'}"]
    _, only_ref, only_tree = graph_diff(to_isomorphic(_graph(at_ref)), to_isomorphic(_graph(in_tree)))
    lines = [f"{path} only-at-ref {s.n3()} {p.n3()} {o.n3()} ." for s, p, o in only_ref]
    lines += [f"{path} only-in-tree {s.n3()} {p.n3()} {o.n3()} ." for s, p, o in only_tree]
    # One difference per line, so a literal's line breaks, for example in a SPARQL query, are escaped.
    return sorted(line.replace("\r", "\\r").replace("\n", "\\n") for line in lines)


def _at_ref(root: Path, ref: str, path: str) -> Optional[str]:
    result = subprocess.run(["git", "show", f"{ref}:{path}"], cwd=root, capture_output=True, text=True)
    return result.stdout if result.returncode == 0 else None


def check(root: Path, module: str, ref: str, reconciled: Set[str]) -> List[str]:
    """Problems with a module's migration: unreconciled differences, and reconciliations that no longer apply."""
    catalogue = lattice_repo_catalogue.load(root)
    entry = catalogue.module(module)
    if not entry.literate:
        raise lattice_repo_catalogue.CatalogueError(f"module {module!r} has no extraction contract to check")
    found: Set[str] = set()
    for role in lattice_repo_catalogue.EXTRACT_KEYS:
        for file in entry.files(role):
            path = file.as_posix()
            current = (root / file).read_text(encoding="utf-8") if (root / file).is_file() else None
            found.update(differences(path, _at_ref(root, ref, path), current))
    problems = [f"unreconciled: {line}" for line in sorted(found - reconciled)]
    problems += [f"reconciliation no longer applies: {line}" for line in sorted(reconciled - found)]
    return problems


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check a README migration left its module's graphs unchanged")
    parser.add_argument("module", help="the module's name in the repository catalogue, e.g. eligibility")
    parser.add_argument("ref", help="the git ref holding the module before its migration")
    parser.add_argument("--reconciliations", default=None, help="a file of approved differences, one per line")
    parser.add_argument("--root", default=None, help="the repository root, if not found from the working directory")
    args = parser.parse_args(argv)
    try:
        root = lattice_repo_catalogue.find_root(args.root)
        reconciled: Set[str] = set()
        if args.reconciliations:
            text = Path(args.reconciliations).read_text(encoding="utf-8")
            reconciled = {line.strip() for line in text.splitlines() if line.strip() and not line.startswith("#")}
        problems = check(root, args.module, args.ref, reconciled)
    except lattice_repo_catalogue.CatalogueError as error:
        print(f"MIGRATION {error}", file=sys.stderr)
        return 1
    for problem in problems:
        print(f"MIGRATION {problem}", file=sys.stderr)
    if problems:
        print(f"{args.module}: {len(problems)} problem(s) against {args.ref}", file=sys.stderr)
        return 1
    print(f"{args.module}: every generated graph is the same as at {args.ref}"
          + (f", with {len(reconciled)} reconciled difference(s)" if reconciled else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
