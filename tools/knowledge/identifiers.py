# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""The stable identifiers LATTICE's working documents use, and whether each mention resolves.

A working document names decisions, register entries, slices and questions by short identifiers:
``ADR-A131``, ``PDD-08``, ``TD-34``, ``LG-Q8``, ``AIR-6.8``. Some 950 distinct identifiers appear
across the tracked Markdown at around 9,600 mention sites, and nothing checks that a mention resolves
to anything. A reference to a withdrawn or renumbered identifier reads exactly like a live one.

This module is the single place that knows how those identifiers are written and where each family is
defined. Its first consumer is the check below. The knowledge index of
``docs/developer/sketches/knowledge-index.md`` reads the same table, so a family is described once.

**Enumeration is always from ``git ls-files``, never a filesystem walk.** A checkout can hold ignored
directories of confidential third-party material, and a walk would read them.

Three facts about the corpus shape this module, each measured rather than assumed.

*One identifier has several spellings.* The clean-room decision is the file ``ADR-AC2-...`` and is
written ``ADR-A-C2`` in 125 places. Headings write ``ADR A-07`` with a space where prose writes
``ADR-A07``. So a mention is resolved on a **normalised** key, letters and digits only, and the
spelling a definition uses is the canonical one. A mention that resolves under a different spelling
is reported as a variant, never failed.

*A register entry is meant to disappear.* Both registers say an entry is removed once a plan takes it
on. So a mention of ``TD-34`` that no longer resolves means the debt was rehomed, not that the
reference is broken. Those families are marked ``removable`` and are reported, never failed.

*A decision file is never removed.* A superseded decision keeps its file and changes its status. So an
``ADR`` mention that does not resolve is either rot or a decision that was planned and never drafted,
and that is worth failing on.

``identifier-exceptions.txt``, beside this file, lists mentions known not to resolve, one per line
with a reason after ``#``. It is the baseline that lets the check fail on a new break rather than on
the corpus's history.

Usage, from the repository root::

    mise run check:identifiers           # fail on a new dangling mention
    mise exec -- python tools/knowledge/identifiers.py --report
    mise exec -- python tools/knowledge/identifiers.py --variants
"""

from __future__ import annotations

import argparse
import re
import subprocess
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
EXCEPTIONS_PATH = Path(__file__).resolve().parent / "identifier-exceptions.txt"

# The first line of a copy that tools/site_sections.py writes into docs/_includes, which names its
# source. A generated copy repeats its source's identifiers, so scanning it would double-count them.
GENERATED_COPY = re.compile(r"\A\{% comment %\}Copied from (\S+) by mise run build:site-sections")

SEPARATORS = re.compile(r"[-\u2011 _]+")
NOT_KEPT = re.compile(r"[^A-Z0-9.]+")


def normalise(identifier: str) -> str:
    """The key a mention and a definition are compared on: letters and digits, upper case.

    ``ADR-A-C2``, ``ADR-AC2`` and ``ADR AC2`` all normalise to ``ADRAC2``, so one decision written
    three ways resolves once. ``ADR-A07`` and ``ADR-A07b`` stay distinct.

    **A dot is kept.** Dropping every separator merged ``AIR-6.6`` with ``AIR-66``, which are
    different slices, so only the separators that actually vary in this corpus are removed: the
    hyphen, the non-breaking hyphen that four decisions are cited with, the space that headings
    use, and the underscore.
    """
    return NOT_KEPT.sub("", SEPARATORS.sub("", identifier).upper())


@dataclass(frozen=True)
class Family:
    """One identifier family: how a mention is written, and how a definition is recognised.

    ``mention`` matches an identifier anywhere in prose, with the identifier in group 1.

    ``definition`` names the rule that recognises a definition, and decides whether the family takes
    part in the check at all:

    ``filename``
        a file under ``defines`` whose name opens with the identifier, as the decisions do
    ``table-row``
        a table row in ``defines`` whose first cell is the identifier, as the registers do
    ``heading``
        a Markdown heading in ``defines`` that opens with the identifier
    ``none``
        no rule written yet. The family is inventoried, and never failed

    ``removable`` marks a family whose definition is meant to disappear once the entry is taken on.
    An unresolved mention there means the entry was rehomed, so it is reported and never failed.
    """

    name: str
    mention: re.Pattern[str]
    definition: str
    defines: tuple[str, ...] = ()
    removable: bool = False
    note: str = ""

    @property
    def resolvable(self) -> bool:
        return self.definition != "none"


# Ordered most specific first. The first family to match an identifier owns it.
FAMILIES: tuple[Family, ...] = (
    Family(
        name="decision",
        # ADR-A131, ADR-A07b, ADR-AC2, ADR-A-C2, ADR-A-FM2, ADR-A-CAP1, and "ADR A-07" in a heading.
        mention=re.compile(r"\b(ADR[-‑ ]A-?[A-Za-z]{0,4}-?\d+[a-z]?)\b"),
        definition="filename",
        defines=("docs/architecture/decisions/*.md",),
        note="a decision file is never removed, so an unresolved mention is rot or a decision "
        "that was planned and never drafted",
    ),
    Family(
        name="pending-decision",
        mention=re.compile(r"\b(PDD-\d+)\b"),
        definition="table-row",
        defines=("docs/developer/pending-design-decisions.md",),
        removable=True,
        note="removed from the register when an ADR, sketch or plan takes the decision on",
    ),
    Family(
        name="technical-debt",
        mention=re.compile(r"\b(TD-\d+)\b"),
        definition="table-row",
        defines=("docs/developer/technical-debt.md",),
        removable=True,
        note="removed from the register when an item gains a home in a plan",
    ),
    Family(
        name="mechanism",
        mention=re.compile(r"\b(MEC-\d+)\b"),
        definition="table-row",
        defines=("docs/developer/mechanisms.md",),
        note="what the project already has, so it is not built twice. A row is never removed, "
        "because a mechanism that goes away is a change to record rather than a row to delete",
    ),
    Family(
        name="capability",
        mention=re.compile(r"\b(CAP-\d+)\b"),
        definition="table-row",
        defines=("docs/developer/capabilities.md",),
        note="what the project's own software can already do, so new work reuses it. A row is never "
        "removed, because a capability that goes away is a change to record rather than a row to delete",
    ),
    Family(
        name="pattern",
        mention=re.compile(r"\b(PAT-\d+)\b"),
        definition="table-row",
        defines=("docs/developer/patterns.md",),
        note="a named, reusable technique with a trade-off, as a handle on the guide section that treats "
        "it. A row is never removed, because a pattern that is withdrawn is a change to record",
    ),
    Family(
        name="principle",
        mention=re.compile(r"\b(PRI-\d+)\b"),
        definition="table-row",
        defines=("docs/developer/principles.md",),
        note="a durable design commitment, as a handle on the document that states it and the decision "
        "that settled it. A row is never removed, because a principle that is withdrawn is a change to record",
    ),
    Family(
        name="standard",
        mention=re.compile(r"\b(STD-\d+)\b"),
        definition="table-row",
        defines=("docs/developer/standards.md",),
        note="prescriptive guidance, stratified from architectural to convention, whose text lives in "
        "the skill or AGENTS.md section loaded for the work",
    ),
    Family(
        name="store-discovery",
        mention=re.compile(r"\b(TSD-\d+[a-z]?)\b"),
        definition="heading",
        defines=("docs/architecture/triple-store-discovery.md",),
        note="what a triple store actually does, found by probing it. An entry is never removed, "
        "so an unresolved mention is rot",
    ),
    # Inventoried only. Their definition rules come from the corpus sweep that seeds the knowledge
    # index, and each family moves up as its rule is written.
    Family(
        name="query-rule",
        mention=re.compile(r"\b(R\d+)\b"),
        definition="none",
        defines=("docs/architecture/efficient-queries-and-shapes.md",),
        note="numbered rules of the efficient-queries guide. A bare R<n> is too common in prose "
        "to fail a build on, so the rule recognising a reference has to be narrower than this",
    ),
    Family(
        name="slice",
        mention=re.compile(r"\b((?:AIR|CCS|LG|ES|WA|FM|HQ|AOR|OD)-\d+(?:\.\d+)?[a-z]?)\b"),
        definition="none",
        note="epic slices, defined in each epic's plan",
    ),
    Family(
        name="question-or-decision-point",
        mention=re.compile(r"\b([A-Z]{1,4}\d*[a-z]?-(?:Q|D)\d+)\b"),
        definition="none",
        note="design questions and decision points, raised in plans and sketches",
    ),
)


@dataclass
class Mention:
    """Every site that writes one identifier, under the spellings actually used."""

    family: str
    key: str
    spellings: dict[str, list[tuple[Path, int]]] = field(default_factory=lambda: defaultdict(list))

    @property
    def sites(self) -> int:
        return sum(len(v) for v in self.spellings.values())


def tracked_markdown() -> list[Path]:
    """Every tracked Markdown file, from git rather than the filesystem.

    An ignored directory may hold confidential third-party material, so a walk is never used.
    """
    listing = subprocess.run(
        ["git", "-C", str(ROOT), "ls-files", "-z", "*.md"],
        capture_output=True,
        text=True,
        check=True,
    )
    return [ROOT / name for name in listing.stdout.split("\0") if name]


def scannable(paths: list[Path]) -> list[Path]:
    """The files whose identifiers count: every tracked Markdown file but a generated copy."""
    keep: list[Path] = []
    for path in paths:
        if not path.is_file():
            continue
        with path.open(encoding="utf-8", errors="replace") as handle:
            if GENERATED_COPY.match(handle.read(200)):
                continue
        keep.append(path)
    return keep


def mentions(paths: list[Path]) -> dict[str, dict[str, Mention]]:
    """Every identifier mention, as family -> normalised key -> Mention."""
    found: dict[str, dict[str, Mention]] = {family.name: {} for family in FAMILIES}
    for path in paths:
        for number, line in enumerate(
            path.read_text(encoding="utf-8", errors="replace").splitlines(), 1
        ):
            claimed: set[str] = set()
            for family in FAMILIES:
                for spelling in family.mention.findall(line):
                    if spelling in claimed:
                        continue
                    claimed.add(spelling)
                    key = normalise(spelling)
                    entry = found[family.name].setdefault(key, Mention(family.name, key))
                    entry.spellings[spelling].append((path, number))
    return found


def definitions(family: Family) -> dict[str, str]:
    """The identifiers this family defines, as normalised key -> canonical spelling."""
    if not family.resolvable:
        return {}
    defined: dict[str, str] = {}
    for pattern in family.defines:
        for path in sorted(ROOT.glob(pattern)):
            if family.definition == "filename":
                match = family.mention.match(path.stem)
                if match:
                    defined[normalise(match.group(1))] = match.group(1)
                continue
            for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
                stripped = line.strip()
                if family.definition == "table-row" and stripped.startswith("|"):
                    cells = stripped.split("|")
                    if len(cells) > 1:
                        match = family.mention.fullmatch(cells[1].strip())
                        if match:
                            defined[normalise(match.group(1))] = match.group(1)
                elif family.definition == "heading" and stripped.startswith("#"):
                    match = family.mention.match(stripped.lstrip("#").strip())
                    if match:
                        defined[normalise(match.group(1))] = match.group(1)
    return defined


def excepted() -> set[str]:
    """Normalised identifiers the baseline says do not resolve, so only a new break fails."""
    if not EXCEPTIONS_PATH.is_file():
        return set()
    entries: set[str] = set()
    for line in EXCEPTIONS_PATH.read_text(encoding="utf-8").splitlines():
        entry = line.split("#", 1)[0].strip()
        if entry:
            entries.add(normalise(entry))
    return entries


def _name(path: Path) -> str:
    return path.relative_to(ROOT).as_posix() if path.is_relative_to(ROOT) else path.as_posix()


def _sites(mention: Mention, limit: int = 4) -> str:
    sites = [site for spelling in sorted(mention.spellings) for site in mention.spellings[spelling]]
    shown = ", ".join(f"{_name(path)}:{line}" for path, line in sites[:limit])
    return shown + (f" and {len(sites) - limit} more" if len(sites) > limit else "")


@dataclass
class Findings:
    unresolved: list[tuple[Family, Mention]] = field(default_factory=list)
    rehomed: list[tuple[Family, Mention]] = field(default_factory=list)
    variants: list[tuple[Family, Mention, str]] = field(default_factory=list)


def examine(found: dict[str, dict[str, Mention]]) -> Findings:
    """Sort every mention of a resolvable family into unresolved, rehomed, or a spelling variant."""
    baseline = excepted()
    findings = Findings()
    for family in FAMILIES:
        if not family.resolvable:
            continue
        defined = definitions(family)
        for key, mention in sorted(found[family.name].items()):
            canonical = defined.get(key)
            if canonical is None:
                if key in baseline:
                    continue
                (findings.rehomed if family.removable else findings.unresolved).append(
                    (family, mention)
                )
                continue
            off = [s for s in mention.spellings if s != canonical]
            if off:
                findings.variants.append((family, mention, canonical))
    return findings


def report(found: dict[str, dict[str, Mention]], files: int) -> None:
    findings = examine(found)
    print(f"{files} tracked Markdown files scanned\n")
    header = f"{'family':<28} {'distinct':>8} {'sites':>7} {'defined':>8} {'unresolved':>11}"
    print(header)
    print("-" * len(header))
    for family in FAMILIES:
        entries = found[family.name]
        sites = sum(m.sites for m in entries.values())
        if not family.resolvable:
            print(f"{family.name:<28} {len(entries):>8} {sites:>7} {'-':>8} {'-':>11}")
            continue
        unresolved = sum(
            1 for f, _ in findings.unresolved + findings.rehomed if f.name == family.name
        )
        mark = f"{unresolved} rehomed" if family.removable else str(unresolved)
        print(
            f"{family.name:<28} {len(entries):>8} {sites:>7} "
            f"{len(definitions(family)):>8} {mark:>11}"
        )
    print("\nA family marked - has no definition rule yet and is never failed.")
    print(f"{len(findings.variants)} identifiers are written under a non-canonical spelling.")
    spread = sorted(
        ((len({p for s in m.spellings.values() for p, _ in s}), k) for d in found.values() for k, m in d.items()),
        reverse=True,
    )
    print("\nMost widely referenced identifiers, by the number of files mentioning them:")
    for count, key in spread[:12]:
        print(f"  {key:<16} {count:>3} files")


def main() -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--report", action="store_true", help="print the inventory and do not fail")
    parser.add_argument(
        "--variants", action="store_true", help="print identifiers written non-canonically"
    )
    parser.add_argument(
        "--list-unresolved", action="store_true", help="print one per line, to seed the baseline"
    )
    parser.add_argument(
        "--rehomed",
        action="store_true",
        help="print register entries that no longer resolve, so a document citing one may be stale",
    )
    arguments = parser.parse_args()

    found = mentions(paths := scannable(tracked_markdown()))

    if arguments.report:
        report(found, len(paths))
        return 0

    findings = examine(found)

    if arguments.variants:
        for family, mention, canonical in findings.variants:
            for spelling in sorted(s for s in mention.spellings if s != canonical):
                count = len(mention.spellings[spelling])
                print(f"{spelling} -> {canonical} ({family.name}, {count} sites): {_sites(mention)}")
        return 0

    if arguments.list_unresolved:
        for family, mention in findings.unresolved:
            print(f"{sorted(mention.spellings)[0]}  # {family.name}, {mention.sites} sites")
        return 0

    if arguments.rehomed:
        for family, mention in findings.rehomed:
            spelling = sorted(mention.spellings)[0]
            print(
                f"{spelling} ({family.name}, {mention.sites} sites) is no longer in its register, "
                f"so it was rehomed or resolved: {_sites(mention)}"
            )
        return 0

    for family, mention in findings.unresolved:
        spelling = sorted(mention.spellings)[0]
        print(f"ERROR: {spelling} ({family.name}) is mentioned but never defined: {_sites(mention)}")

    if findings.unresolved:
        print(
            f"\n{len(findings.unresolved)} identifiers are mentioned but defined nowhere. Define "
            f"each, correct the mention, or add it to {_name(EXCEPTIONS_PATH)} with a reason."
        )
        return 1

    resolvable = sum(len(found[f.name]) for f in FAMILIES if f.resolvable)
    print(
        f"identifier check passed: every mention of {resolvable} resolvable identifiers resolves. "
        f"{len(findings.variants)} written non-canonically (--variants), "
        f"{len(findings.rehomed)} register entries rehomed (--rehomed)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
