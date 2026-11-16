#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Check the writing rules of AGENTS.md on the lines a change adds to Markdown (ADR-A133).

  python tools/writing_rules.py                every line staged for commit
  python tools/writing_rules.py FILE...        every line of the named files

Prose only: a fenced code block, front matter, an HTML comment, an inline code span, a URL and an
HTML entity are never judged. Five rules fail and one warns:

- a semicolon in prose. Use a period or a comma
- "this document" in a literate README, which generates several documents (skill
  lattice-ontology-authoring)
- a decision cited in a layer README outside its Design decisions section and its release notes,
  in prose or inside a fenced block, since a block is extracted into a published document. State
  the constraint or feature the decision gives (STD-337, skill lattice-publication-hygiene)
- a bare "decision 6" anywhere in a layer README, which names no record
- a working-document identifier anywhere in a layer README: a register entry, a question, or a slice
  the developer index defines. State the fact it stood for (STD-142)
- a hard-wrapped line: paragraph or list text that continues the line before it, where a paragraph
  belongs on one line (a warning, since editing one word of an older wrapped paragraph adds such a
  line)

Standard library only.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

GENERATED = ("docs/_includes/", ".github/copilot-instructions.md", "docs/architecture/ontology-releases.md")
CODE_SPAN = re.compile(r"(`+)(?:(?!\1).)+?\1")
URL = re.compile(r"<?https?://\S+")
ENTITY = re.compile(r"&(?:[A-Za-z][A-Za-z0-9]*|#[0-9]+|#x[0-9A-Fa-f]+);")
LIST_ITEM = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+")
FENCE = re.compile(r"^\s*(`{3,}|~{3,})")
FIELD = re.compile(r"^\*\*[^*\n]{1,60}?(?::\*\*|\*\*:)")
DECISION = re.compile(r"\bADR-A[-0-9A-Z]*\d")
BARE_DECISION = re.compile(r"\b[Dd]ecisions? \d")
CITES_DECISIONS = ("design decisions", "release notes")
# ponytail: the registers under docs/developer are listed here. Read vyvid.toml's families if they change often.
WORKING = re.compile(r"\b(?:(?:STD|PRI|PAT|MEC|CAP|TD|PDD|BL)-\d+|(?!TSD-)[A-Z]{1,4}\d*[a-z]?-Q\d+)\b")
SLICE = re.compile(r"\b[A-Z]{2,5}-[A-Z]*\d+[a-z]?(?:\.[A-Z]*\d+[a-z]?)*\b")
SLICE_ROW = re.compile(r"^\| ([A-Z]{2,5}-[A-Za-z0-9.]+) \|")
INDEX = "docs/developer/INDEX.md"


@dataclass(frozen=True)
class Finding:
    path: str
    line: int
    rule: str
    blocking: bool

    def __str__(self) -> str:
        return f"{self.path}:{self.line}: {self.rule}"


def judged(path: str) -> bool:
    return path.endswith(".md") and not path.startswith(GENERATED) and "/vendor/" not in path \
        and not path.startswith("node_modules/")


def literate_readme(path: str) -> bool:
    return path.startswith("ontology/") and path.endswith("/README.md")


def kinds(lines: Sequence[str]) -> list[str]:
    """For each line: code, frontmatter, comment, blank, heading, table, quote, field, item,
    continuation or text. An item starts a list entry. A continuation is indented text inside a list
    entry. A field opens with a bold label, as a document's header lines do (**Status:** ...)."""
    out, fence, comment, front = [], None, False, bool(lines) and lines[0].strip() == "---"
    in_item = False
    for number, line in enumerate(lines):
        stripped = line.strip()
        if front:
            out.append("frontmatter")
            if number > 0 and stripped == "---":
                front = False
            continue
        opening = FENCE.match(line)
        if fence:
            out.append("code")
            if opening and opening.group(1)[0] == fence[0] and len(opening.group(1)) >= len(fence):
                fence = None
            continue
        if opening:
            fence = opening.group(1)
            out.append("code")
            continue
        if comment or stripped.startswith("<!--"):
            out.append("comment")
            comment = "-->" not in stripped
            continue
        if not stripped:
            out.append("blank")
            in_item = False if not line.startswith(" ") else in_item
            continue
        if stripped.startswith("#"):
            kind = "heading"
        elif stripped.startswith("|"):
            kind = "table"
        elif stripped.startswith(">"):
            kind = "quote"
        elif FIELD.match(stripped):
            kind, in_item = "field", False
        elif LIST_ITEM.match(line):
            kind, in_item = "item", True
        elif in_item and line.startswith(" "):
            kind = "continuation"
        else:
            kind, in_item = "text", False
        out.append(kind)
    return out


def prose(text: str) -> str:
    return ENTITY.sub("", URL.sub("", CODE_SPAN.sub("", text)))


def sections(lines: Sequence[str], line_kinds: Sequence[str]) -> list[str | None]:
    """For each line, the nearest heading of a section above it, in lower case, or None before the first. The
    document's title is no section, so the lines under it are before the first."""
    out: list[str | None] = []
    current = None
    for line, kind in zip(lines, line_kinds):
        if kind == "heading" and line.lstrip().startswith("##"):
            current = line.strip().lstrip("#").strip().lower()
        out.append(current)
    return out


def slice_ids(root: Path) -> frozenset[str]:
    """The slices the developer index defines, by the first cell of its rows. A token is a slice only where it is
    one of these, so SHA-256 and UTF-8 are never read as one."""
    index = root / INDEX
    if not index.is_file():
        return frozenset()
    rows = (SLICE_ROW.match(line) for line in index.read_text(encoding="utf-8").splitlines())
    return frozenset(row.group(1) for row in rows if row)


def working_rule(line: str, slices: frozenset[str]) -> str | None:
    """What an added line of a layer README breaks by naming a working document's entry, if anything (STD-142)."""
    found = WORKING.search(line) or next((m for m in SLICE.finditer(line) if m.group(0) in slices), None)
    if found:
        return f"a working-document identifier, {found.group(0)}. State the fact it stood for"
    return None


def decision_rule(line: str, section: str | None) -> str | None:
    """What an added line of a layer README breaks by naming a decision, if anything (STD-337). A decision is cited
    in the Design decisions section and in a release note, and before the first section, where the layout is named."""
    cited = DECISION.search(line)
    if BARE_DECISION.search(line) and not cited:
        return 'a bare decision number, which names no record. State the constraint or feature it gives'
    if cited and section is not None and not any(name in section for name in CITES_DECISIONS):
        return ("a decision cited outside the Design decisions section. State the constraint or feature it gives, "
                "since a decision record is written for those who build")
    return None


def check_file(path: str, text: str, added: Iterable[int], slices: frozenset[str] = frozenset()) -> list[Finding]:
    """The findings on the given line numbers (1-based) of one file. ``slices`` is the slices the index defines."""
    if not judged(path):
        return []
    lines = text.splitlines()
    line_kinds = kinds(lines)
    line_sections = sections(lines, line_kinds)
    findings = []
    for number in sorted(set(added)):
        if not 1 <= number <= len(lines):
            continue
        kind, line = line_kinds[number - 1], lines[number - 1]
        if literate_readme(path) and kind not in ("frontmatter", "blank"):
            for broken in (decision_rule(line, line_sections[number - 1]), working_rule(line, slices)):
                if broken:
                    findings.append(Finding(path, number, broken, True))
        if kind in ("code", "frontmatter", "comment", "blank"):
            continue
        if ";" in prose(line):
            findings.append(Finding(path, number, "a semicolon in prose. Use a period or a comma", True))
        if literate_readme(path) and "this document" in prose(line).lower():
            findings.append(Finding(path, number, '"this document" in a literate README, which generates several '
                                                  "documents. Describe the layer or name the file", True))
        previous = line_kinds[number - 2] if number > 1 else "blank"
        if kind in ("text", "continuation") and previous in ("text", "item", "continuation", "quote") \
                and not lines[number - 2].endswith("  "):
            findings.append(Finding(path, number, "a hard-wrapped line. Keep a paragraph or a list entry on one line",
                                    False))
    return findings


def check(root: Path, added: Iterable[tuple[str, int, str]]) -> list[Finding]:
    """The findings on added lines, given as (path, line number, text), reading each file from the
    working tree for its context (ADR-A133 decision 8)."""
    by_file: dict[str, list[int]] = {}
    for path, number, _ in added:
        by_file.setdefault(path, []).append(number)
    findings, slices = [], slice_ids(root)
    for path, numbers in by_file.items():
        file = root / path
        if judged(path) and file.is_file():
            findings += check_file(path, file.read_text(encoding="utf-8"), numbers, slices)
    return findings


def staged(root: Path) -> list[tuple[str, int, str]]:
    out = subprocess.run(["git", "diff", "--cached", "-U0", "--no-color", "--no-ext-diff"], cwd=root,
                         capture_output=True, text=True, check=True, encoding="utf-8", errors="replace").stdout
    path, number, added = None, 0, []
    for line in out.splitlines():
        if line.startswith("+++ "):
            path = None if line[4:] == "/dev/null" else line[6:]
        elif line.startswith("@@"):
            number = int(line.split("+", 1)[1].split(",")[0].split(" ")[0])
        elif line.startswith("+") and path:
            added.append((path, number, line[1:]))
            number += 1
    return added


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("files", nargs="*", help="check every line of these files instead of the staged lines")
    args = parser.parse_args(argv)
    root = Path.cwd()
    if args.files:
        added = [(f, n, "") for f in args.files for n in range(1, len((root / f).read_text(encoding="utf-8").splitlines()) + 1)]
    else:
        added = staged(root)
    findings = check(root, added)
    for finding in findings:
        print(f"{'' if finding.blocking else 'warning: '}{finding}")
    blocking = [f for f in findings if f.blocking]
    print(f"writing rules: {len(blocking)} failure(s), {len(findings) - len(blocking)} warning(s)")
    return 1 if blocking else 0


if __name__ == "__main__":
    sys.exit(main())
