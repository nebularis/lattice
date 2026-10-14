# SPDX-License-Identifier: MPL-2.0
"""Checks the tutorial's Turtle excerpts and repository links against the checkout
(plan ``docs/developer/plans/lattice-tutorial.md`` §5, TUT-D5 and TUT-Q1).

The tutorial is one page of the GitHub Pages site, ``docs/tutorial.md``, whose
chapters live in ``docs/_includes/tutorial/``. Only ``docs/`` is published, so a
chapter copies its Turtle excerpts rather than including them, and links to
repository files by absolute GitHub URL. Both can go stale when an example
changes. This script finds them.

1. **Excerpts.** A fenced ``turtle`` block must follow, on the line before it
   or with only blank lines between, an HTML comment naming its source,
   ``<!-- source: ontology/<layer>/examples/<file>.ttl -->``, as a path
   relative to the repository root. The excerpt's lines must appear in that
   file, contiguous and in order, compared with trailing whitespace removed.
   A line holding only ``# …`` elides source lines. It splits the excerpt
   into parts, each checked as contiguous, and each found after the one
   before it.
2. **Links.** Every ``https://github.com/nebularis/lattice/blob/main/<path>``
   or ``…/tree/main/<path>`` must name a path that exists in the checkout.

Standard library only. Prints one ``DRIFT <chapter>: <reason>`` line per
finding and exits 1 if there is any, else prints a summary and exits 0.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Sequence
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parent.parent
CHAPTERS = Path("docs") / "_includes" / "tutorial"

SOURCE_COMMENT = re.compile(r"^\s*<!--\s*source:\s*(\S+)\s*-->\s*$")
FENCE_OPEN = re.compile(r"^\s*```\s*(\S*)\s*$")
FENCE_CLOSE = re.compile(r"^\s*```\s*$")
ELISION = "# …"
REPO_LINK = re.compile(r"https://github\.com/nebularis/lattice/(?:blob|tree)/main/([^\s)\"'<>#?]+)")


@dataclass
class Excerpt:
    source: str
    lines: List[str]
    line_no: int


@dataclass
class Report:
    findings: List[str]
    excerpts: int = 0
    links: int = 0


def parse_excerpts(text: str) -> tuple[List[Excerpt], List[str]]:
    """Return the chapter's excerpts, and a finding for each turtle block with no source."""
    excerpts: List[Excerpt] = []
    problems: List[str] = []
    lines = text.splitlines()
    pending: Optional[str] = None
    i = 0
    while i < len(lines):
        line = lines[i]
        comment = SOURCE_COMMENT.match(line)
        fence = FENCE_OPEN.match(line)
        if comment:
            pending = comment.group(1)
        elif fence:
            start = i + 1
            i += 1
            body: List[str] = []
            while i < len(lines) and not FENCE_CLOSE.match(lines[i]):
                body.append(lines[i])
                i += 1
            if fence.group(1) == "turtle":
                if pending is None:
                    problems.append(f"line {start}: turtle excerpt with no source comment before it")
                else:
                    excerpts.append(Excerpt(pending, body, start))
            pending = None
        elif line.strip():
            pending = None
        i += 1
    return excerpts, problems


def _parts(lines: Sequence[str]) -> List[List[str]]:
    parts: List[List[str]] = [[]]
    for line in lines:
        if line.strip() == ELISION:
            parts.append([])
        else:
            parts[-1].append(line.rstrip())
    trimmed = []
    for part in parts:
        while part and not part[0]:
            part.pop(0)
        while part and not part[-1]:
            part.pop()
        if part:
            trimmed.append(part)
    return trimmed


def _find(haystack: Sequence[str], needle: Sequence[str], start: int) -> int:
    for i in range(start, len(haystack) - len(needle) + 1):
        if list(haystack[i:i + len(needle)]) == list(needle):
            return i
    return -1


def _resolve(root: Path, relative: str) -> Optional[Path]:
    path = (root / relative).resolve()
    try:
        path.relative_to(root.resolve())
    except ValueError:
        return None
    return path


def check_excerpt(root: Path, excerpt: Excerpt) -> Optional[str]:
    """Return a finding, or None when every part of the excerpt is in its source, in order."""
    where = f"line {excerpt.line_no}"
    source = _resolve(root, excerpt.source)
    if source is None:
        return f"{where}: source {excerpt.source} is outside the repository"
    if not source.is_file():
        return f"{where}: source {excerpt.source} does not exist"
    haystack = [line.rstrip() for line in source.read_text(encoding="utf-8").splitlines()]
    parts = _parts(excerpt.lines)
    if not parts:
        return f"{where}: excerpt from {excerpt.source} is empty"
    position = 0
    for number, part in enumerate(parts, start=1):
        found = _find(haystack, part, position)
        if found < 0:
            label = f"part {number} of the excerpt" if len(parts) > 1 else "the excerpt"
            return f"{where}: {label} no longer matches {excerpt.source} (first line: {part[0].strip()!r})"
        position = found + len(part)
    return None


def check_links(root: Path, text: str) -> tuple[int, List[str]]:
    """Return the number of repository links and a finding for each whose path is missing."""
    problems = []
    links = REPO_LINK.findall(text)
    for link in links:
        relative = unquote(link).rstrip(".,:")
        path = _resolve(root, relative)
        if path is None or not path.exists():
            problems.append(f"link to {relative} names no path in the repository")
    return len(links), problems


def check(root: Path = ROOT) -> Report:
    report = Report(findings=[])
    chapters = root / CHAPTERS
    if not chapters.is_dir():
        report.findings.append(f"{CHAPTERS.as_posix()}: no chapter directory")
        return report
    for chapter in sorted(chapters.glob("*.md")):
        name = chapter.relative_to(root).as_posix()
        text = chapter.read_text(encoding="utf-8")
        excerpts, problems = parse_excerpts(text)
        report.findings.extend(f"{name}: {p}" for p in problems)
        for excerpt in excerpts:
            finding = check_excerpt(root, excerpt)
            if finding:
                report.findings.append(f"{name}: {finding}")
        count, link_problems = check_links(root, text)
        report.findings.extend(f"{name}: {p}" for p in link_problems)
        report.excerpts += len(excerpts)
        report.links += count
    return report


def main() -> int:
    report = check()
    for finding in report.findings:
        print(f"DRIFT {finding}")
    if report.findings:
        return 1
    print(f"OK {report.excerpts} excerpts and {report.links} repository links match the checkout")
    return 0


if __name__ == "__main__":
    sys.exit(main())
