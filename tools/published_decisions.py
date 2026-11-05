# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""Read the architecture decisions' status, and write the list of published ones (ADR-A127 decisions 1 to 3).

A published ADR's status line reads ``**Status:** Published, YYYY-MM-DD. Accepted YYYY-MM-DD.`` (OD-D49), and
its header names the documents that describe it in ``**Described in:**``. It opens with Jekyll front matter
saying ``published: true``. The site excludes every ADR in ``docs/_config.yml`` and includes each published one
by name, in a region this tool writes. Jekyll's ``published: false`` default does not reach a page with no
front matter, so it cannot hide the others. A superseded decision that was
published reads ``**Status:** Superseded by ADR-An. Published YYYY-MM-DD.`` and stays on the list, marked.

Usage, from the repository root::

    mise run build:published-decisions
    mise run check:published-decisions
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence

sys.path.insert(0, str(Path(__file__).resolve().parent))

import lattice_repo_catalogue  # noqa: E402

LIST_NAME = "published-architecture-decisions.md"
CONFIG_RE = re.compile(r"(?ms)^# BEGIN GENERATED published-decisions\..*?\n# END GENERATED published-decisions\n")
FILENAME_RE = re.compile(r"^ADR-(?P<id>A[\w-]*?\d+)-[\w.-]+\.md$")
HEADER_STATUS_RE = re.compile(r"^\*\*Status:\*\*\s*(?P<status>.+?)\s*$")
PUBLISHED_RE = re.compile(r"^Published, (?P<published>\d{4}-\d{2}-\d{2})\. Accepted (?P<accepted>\d{4}-\d{2}-\d{2})\.$")
SUPERSEDED_RE = re.compile(r"^Superseded by (?P<by>ADR-A[\w-]*?\d+)\. Published (?P<published>\d{4}-\d{2}-\d{2})\.$")
DESCRIBED_RE = re.compile(r"^\*\*Described in:\*\*\s*(?P<docs>.+?)\s*$")
LINK_RE = re.compile(r"\[(?P<text>[^\]]+)\]\((?P<href>[^)\s]+)\)")
TITLE_RE = re.compile(r"^#\s+ADR[- ]?A[\w-]*?\d+:\s*(?P<title>.+?)\s*$")
FRONT_RE = re.compile(r"\A---\n(?P<body>.*?)\n---\n", re.S)


@dataclass(frozen=True)
class Locations:
    """Where the decisions, their list and the site's configuration are, relative to the repository root,
    found from the repository catalogue's ``docs/architecture/`` area (ADR-A121)."""

    decisions: Path
    listing: Path
    config: Path


def locations(root: Path) -> Locations:
    areas = [Path(a.path) for a in lattice_repo_catalogue.load(root).docs if a.path.rstrip("/").endswith("/architecture")]
    if len(areas) != 1:
        raise lattice_repo_catalogue.CatalogueError("declare the architecture documents, docs/architecture/, as one [[docs]] area")
    architecture = areas[0]
    return Locations(architecture / "decisions", architecture / LIST_NAME, architecture.parent / "_config.yml")


def normalise(identifier: str) -> str:
    """``A-05``, ``A05`` and ``A-FM1`` as one form: ``A05``, ``A05`` and ``A-FM1``."""
    match = re.fullmatch(r"A-?(\d+)", identifier)
    return f"A{int(match.group(1)):02d}" if match else identifier


@dataclass(frozen=True)
class Decision:
    """One ADR file, read for what the list and the sources check need."""

    identifier: str
    path: Path
    title: str
    status: str
    published: Optional[str]
    superseded_by: Optional[str]
    described_in: tuple
    front_published: Optional[bool]
    text: str

    @property
    def is_published(self) -> bool:
        return self.published is not None

    @property
    def is_current_published(self) -> bool:
        return self.published is not None and self.superseded_by is None

    def body(self) -> str:
        """The text outside the Provenance section, which ADR-A127 holds to the sources rule."""
        return re.split(r"^## Provenance\s*$", self.text, maxsplit=1, flags=re.M)[0]


def _status(lines: List[str]) -> str:
    for line in lines:
        match = HEADER_STATUS_RE.match(line)
        if match:
            return match.group("status")
    for index, line in enumerate(lines):
        if line.strip() == "## Status":
            return next((l.strip() for l in lines[index + 1:] if l.strip()), "")
    return ""


def read(path: Path) -> Decision:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    identifier = normalise(FILENAME_RE.match(path.name).group("id"))
    title = next((m.group("title") for l in lines if (m := TITLE_RE.match(l))), path.stem)
    status = _status(lines)
    published = superseded_by = None
    if match := PUBLISHED_RE.match(status):
        published = match.group("published")
    elif match := SUPERSEDED_RE.match(status):
        published, superseded_by = match.group("published"), match.group("by")
    described = next((m.group("docs") for l in lines if (m := DESCRIBED_RE.match(l))), "")
    front = FRONT_RE.match(text)
    front_published = None
    if front and (m := re.search(r"^published:\s*(true|false)\s*$", front.group("body"), re.M)):
        front_published = m.group(1) == "true"
    return Decision(identifier, path, title, status, published, superseded_by,
                    tuple(LINK_RE.findall(described)), front_published, text)


def load(root: Path) -> Dict[str, Decision]:
    """Every ADR by its normalised identifier."""
    return {d.identifier: d for d in (read(p) for p in sorted((root / locations(root).decisions).glob("ADR-A*.md"))
                                      if FILENAME_RE.match(p.name))}


def problems(decisions: Dict[str, Decision]) -> List[str]:
    """What keeps a published decision from meeting ADR-A127 decision 2, and front matter that disagrees."""
    found = []
    for d in decisions.values():
        name = d.path.name
        if d.is_published:
            if not d.described_in:
                found.append(f"{name}: published with no **Described in:** link")
            if "## Provenance" not in d.text:
                found.append(f"{name}: published with no Provenance section")
            if d.front_published is not True:
                found.append(f"{name}: published, so its front matter says published: true")
        elif d.status.startswith("Published") or d.status.startswith("Superseded by") and "Published" in d.status:
            found.append(f"{name}: status {d.status!r} is not 'Published, YYYY-MM-DD. Accepted YYYY-MM-DD.'")
        elif d.front_published is True:
            found.append(f"{name}: front matter says published: true, but its status is {d.status!r}")
    return found


def render(decisions: Dict[str, Decision]) -> str:
    rows = []
    for d in sorted((d for d in decisions.values() if d.is_published), key=lambda d: _order(d.identifier)):
        title = f"{d.title} (superseded by {d.superseded_by})" if d.superseded_by else d.title
        described = ", ".join(f"[{text}]({_relative(d.path.parent, href)})" for text, href in d.described_in)
        rows.append(f"| [{d.identifier}](decisions/{d.path.name}) | {title} | {d.published} | {described} |")
    return "\n".join([
        "<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->",
        "",
        "# Published architecture decisions",
        "",
        "The architecture decisions the maintainer has published, with the documents that describe each.",
        "Generated by `mise run build:published-decisions` from each decision's Status and Described in lines.",
        "Do not edit it by hand.",
        "",
        "| Decision | Title | Published | Described in |",
        "|---|---|---|---|",
        *rows,
        "",
    ])


def config_block(decisions: Dict[str, Decision]) -> str:
    """The site's include list: Jekyll's exclusion of the decisions directory's ADRs is lifted for each
    published one, by file name, which is how Jekyll 3 matches an include inside an excluded glob."""
    names = sorted(d.path.name for d in decisions.values() if d.is_published)
    return "\n".join([
        "# BEGIN GENERATED published-decisions. Written by `mise run build:published-decisions`. Do not edit by hand.",
        "include:", *(f"  - {name}" for name in names), "# END GENERATED published-decisions", ""])


def _order(identifier: str):
    match = re.fullmatch(r"A(\d+)", identifier)
    return (0, int(match.group(1)), "") if match else (1, 0, identifier)


def _relative(base: Path, href: str) -> str:
    """A link written in an ADR, rewritten for the list one directory up."""
    if re.match(r"^[a-z]+:", href) or href.startswith("#"):
        return href
    return (Path("decisions") / href).as_posix() if not href.startswith("../") else href[3:]


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Write or check the list of published architecture decisions")
    parser.add_argument("command", choices=("build", "check"))
    parser.add_argument("--root", default=None)
    args = parser.parse_args(argv)
    root = lattice_repo_catalogue.find_root(args.root)
    decisions = load(root)
    found = problems(decisions)
    expected = render(decisions)
    where = locations(root)
    LIST, CONFIG = where.listing, where.config
    target = root / LIST
    config = (root / CONFIG).read_text(encoding="utf-8")
    if not CONFIG_RE.search(config):
        found.append(f"{CONFIG} has no generated published-decisions region")
    refreshed = CONFIG_RE.sub(lambda _: config_block(decisions), config)
    if args.command == "build":
        target.write_text(expected, encoding="utf-8", newline="\n")
        (root / CONFIG).write_text(refreshed, encoding="utf-8", newline="\n")
        print(f"wrote {LIST} and {CONFIG}'s include list ({sum(d.is_published for d in decisions.values())} published)")
    else:
        if (target.read_text(encoding="utf-8") if target.exists() else None) != expected:
            found.append(f"{LIST} is stale. Run mise run build:published-decisions")
        if refreshed != config:
            found.append(f"{CONFIG}'s include list is stale. Run mise run build:published-decisions")
    for problem in found:
        print(f"PUBLISHED {problem}", file=sys.stderr)
    return 1 if found else 0


if __name__ == "__main__":
    raise SystemExit(main())
