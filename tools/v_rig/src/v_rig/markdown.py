# SPDX-License-Identifier: MPL-2.0
"""A line-oriented reader of a document body laid out by the format's conventions. It knows headings, numbered
clauses, list items, definitions, table rows and paragraphs, and nothing else. Anything it does not recognise is a
paragraph, so a body that lacks a convention never fails."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

_H1 = re.compile(r"^#\s+(.*)$")
_H2 = re.compile(r"^##\s+(.*)$")
_H3 = re.compile(r"^###\s+(.*)$")
_NUMBERED_HEADING = re.compile(r"^(Section|Endorsement|Schedule|Part|Annex|Appendix)\s+([\dA-Z]+)\s*(.*)$", re.IGNORECASE)
_CLAUSE = re.compile(r"^(\d+(?:\.\d+)+)\s+(.*)$")
_ITEM = re.compile(r"^\s*(?:[-*+]|(\d+)[.)])\s+(.*)$")
_DEFINITION = re.compile(r"^\*\*(.+?)\*\*\s+means\b\s*(.*)$", re.IGNORECASE)
_ROW = re.compile(r"^\|(.*)\|\s*$")
_SEPARATOR = re.compile(r"^\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)*\|?\s*$")
_ROW_LABEL = re.compile(r"^(\d+)\.\s+(.*)$")
_LABEL_LINE = re.compile(r"\binvented\b", re.IGNORECASE)

REFERENCE = re.compile(
    r"\b(Section|Item|Condition|Clause|Endorsement|Schedule|Part|Annex)\s+(\d+(?:\.\d+)*|[A-Z])"
    r"(?:\s+of\s+the\s+(Followed|Primary|Underlying)\s+Policy)?",
    re.IGNORECASE,
)


@dataclass
class Node:
    kind: str
    line: int
    number: str | None = None
    title: str | None = None
    text: str | None = None
    term: str | None = None
    children: list["Node"] = field(default_factory=list)


def _heading(kind_default: str, text: str, line: int) -> Node:
    match = _NUMBERED_HEADING.match(text.strip())
    if match:
        word, number, title = match.groups()
        return Node(word.lower(), line, number=number, title=title.strip() or None)
    return Node(kind_default, line, title=text.strip())


def parse(body: str, first_line: int = 1) -> list[Node]:
    """The top-level nodes of a body: the title, the label line, sections, and anything outside a section."""
    top: list[Node] = []
    section: Node | None = None
    container: list[Node] = top
    paragraph: list[str] = []
    paragraph_line = 0
    table_header_seen = False
    seen_label = False

    def flush() -> None:
        nonlocal paragraph, paragraph_line, seen_label
        if not paragraph:
            return
        text = " ".join(paragraph)
        clause = _CLAUSE.match(text)
        if clause:
            container.append(Node("clause", paragraph_line, number=clause.group(1), text=clause.group(2)))
        elif not seen_label and not section and _LABEL_LINE.search(text):
            container.append(Node("label", paragraph_line, text=text))
            seen_label = True
        else:
            container.append(Node("paragraph", paragraph_line, text=text))
        paragraph = []

    for offset, raw in enumerate(body.split("\n")):
        line = first_line + offset
        stripped = raw.rstrip()
        if not stripped.strip():
            flush()
            table_header_seen = False
            continue
        h1, h2, h3 = _H1.match(stripped), _H2.match(stripped), _H3.match(stripped)
        if h1 and not h2:
            flush()
            top.append(Node("title", line, title=h1.group(1).strip()))
            continue
        if h2 and not h3:
            flush()
            section = _heading("section", h2.group(1), line)
            top.append(section)
            container = section.children
            continue
        if h3:
            flush()
            node = _heading("subsection", h3.group(1), line)
            (section.children if section else top).append(node)
            container = node.children
            continue
        row = _ROW.match(stripped)
        if row:
            flush()
            if _SEPARATOR.match(stripped):
                continue
            cells = [c.strip() for c in row.group(1).split("|")]
            if not table_header_seen:
                table_header_seen = True
                continue
            label = _ROW_LABEL.match(cells[0]) if cells else None
            if label:
                container.append(Node("row", line, number=label.group(1), title=label.group(2),
                                      text=" | ".join(cells[1:]) or None))
            else:
                container.append(Node("row", line, text=" | ".join(cells)))
            continue
        item = _ITEM.match(stripped)
        if item and not _CLAUSE.match(stripped.strip()):
            flush()
            number, text = item.group(1), item.group(2).strip()
            definition = _DEFINITION.match(text)
            if definition:
                container.append(Node("definition", line, number=number, term=definition.group(1).strip(), text=text))
            else:
                container.append(Node("item", line, number=number, text=text))
            continue
        if not paragraph:
            paragraph_line = line
        paragraph.append(stripped.strip())
    flush()
    return top


def references(text: str) -> list[tuple[str, str, str, bool]]:
    """(text as written, target kind, target number, external) for each cross-reference in a text."""
    found = []
    for match in REFERENCE.finditer(text):
        kind, number, other = match.group(1).lower(), match.group(2), match.group(3)
        found.append((match.group(0), kind, number, other is not None))
    return found
