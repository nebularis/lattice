# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""Check that user-facing documents cite only published decisions and never a working document (ADR-A127 decision 4).

User-facing documents are the module READMEs the repository catalogue lists, the files a literate README
generates, published ADRs outside their Provenance section, and the published decisions list. Every line is
read, HTML comments and hidden blocks included. The check fails on:

- a reference to a working document: a path under ``docs/developer/`` naming its sketches, plans, status
  records, review requests, Validation Packs or notes, or the developer index. Durable guidance under
  ``docs/developer/`` may be linked
- in a README migrated to the layout of ADR-A126, and the files it generates, a citation of a decision that
  is not published
- in a published ADR, a citation of a decision that is neither accepted nor published, and a relative link to
  one that is not published, which the site hides. Such a link points at the ADR on GitHub (OD-D47)

It reports, without failing, a citation of an unpublished decision in a README not yet migrated, which is
the transition ADR-A127 allows, and a working document in one.

Usage, from the repository root::

    mise run check:sources
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))

import lattice_repo_catalogue  # noqa: E402
import literate_extract  # noqa: E402
import published_decisions as pd  # noqa: E402

WORKING_RE = re.compile(r"developer/(?:sketches|plans|status|reviews|validation|notes)/|developer/INDEX\.md")
CITATION_RE = re.compile(r"ADR[- ]?(A-?[A-Z]*-?\d+)\b")
ADR_LINK_RE = re.compile(r"\]\((?P<href>[^)\s]*ADR-(?P<id>A[\w-]*?\d+)-[\w.-]+\.md[^)\s]*)\)")
ABSOLUTE = "https://github.com/nebularis/lattice/blob/"


def _lines(text: str) -> Iterable[Tuple[int, str]]:
    return enumerate(text.splitlines(), 1)


def documents(root: Path) -> List[Tuple[Path, str, str]]:
    """(path, kind, text) for every user-facing document. Kind is migrated, unmigrated or decision."""
    found = []
    catalogue = lattice_repo_catalogue.load(root)
    for module in catalogue.modules.values():
        readme = root / module.path / "README.md"
        if not readme.is_file():
            continue
        text = readme.read_text(encoding="utf-8")
        kind = "migrated" if literate_extract.uses_layout(literate_extract.scan(text).sections) else "unmigrated"
        found.append((readme, kind, text))
        for role in lattice_repo_catalogue.EXTRACT_KEYS:
            for file in module.files(role):
                if (root / file).is_file():
                    found.append((root / file, kind, (root / file).read_text(encoding="utf-8")))
    for decision in pd.load(root).values():
        if decision.is_published:
            found.append((decision.path, "decision", decision.body()))
    listing = root / pd.locations(root).listing
    if listing.is_file():
        found.append((listing, "decision", listing.read_text(encoding="utf-8")))
    return found


def check(root: Path) -> Tuple[List[str], List[str]]:
    """(failures, reports)."""
    decisions = pd.load(root)
    failures: List[str] = []
    reports: List[str] = []
    for path, kind, text in documents(root):
        name = path.relative_to(root).as_posix()
        for number, line in _lines(text):
            where = f"{name}:{number}"
            if WORKING_RE.search(line):
                (reports if kind == "unmigrated" else failures).append(f"{where}: refers to a working document")
            for raw in sorted(set(CITATION_RE.findall(line))):
                identifier = pd.normalise(raw)
                decision = decisions.get(identifier)
                if decision is None:
                    reports.append(f"{where}: cites ADR-{raw}, which has no file")
                elif kind == "decision":
                    if not (decision.is_published or decision.status.startswith("Accepted")):
                        failures.append(f"{where}: cites ADR-{raw}, whose status is {decision.status!r}")
                elif not decision.is_current_published:
                    (failures if kind == "migrated" else reports).append(
                        f"{where}: cites ADR-{raw}, which is not published ({decision.status!r})")
            if kind == "decision":
                for match in ADR_LINK_RE.finditer(line):
                    target = decisions.get(pd.normalise(match.group("id")))
                    if target and not target.is_published and not match.group("href").startswith(ABSOLUTE):
                        failures.append(f"{where}: links ADR-{match.group('id')}, which is not published, "
                                        f"by a relative link the site cannot follow. Link {ABSOLUTE}main/...")
    return failures, reports


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check user-facing documents cite only published decisions")
    parser.add_argument("--root", default=None)
    parser.add_argument("--quiet", action="store_true", help="print only failures and a count of reports")
    args = parser.parse_args(argv)
    root = lattice_repo_catalogue.find_root(args.root)
    failures, reports = check(root)
    if not args.quiet:
        for report in reports:
            print(f"REPORT {report}")
    for failure in failures:
        print(f"SOURCES {failure}", file=sys.stderr)
    print(f"sources: {len(failures)} failure(s), {len(reports)} report(s) for READMEs not yet migrated")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
