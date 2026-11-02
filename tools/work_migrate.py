# SPDX-License-Identifier: MPL-2.0
"""Move the slice boards and slice ids onto the work board's shape (plan work-board, WB-2).

  python tools/work_migrate.py rename [--apply]       the crosswalk from the historic ids, then the sweep
  python tools/work_migrate.py normalise [--apply]    every board into the standard columns and state words
  python tools/work_migrate.py adopt [--apply]        slices a record's other tables, a Validation Pack or a plan name onto the board

Both are idempotent, so a branch runs them once after merging main and is then on the new ids and
the new boards. Without ``--apply`` each prints what it would do and writes nothing but the
crosswalk, which the maintainer reads first.

The grammar. A slice id is ``PREFIX-segment(.segment)*``, a segment being optional capitals, digits
and one lowercase letter, the prefix declared on the unit's plan's ``**Prefix:**`` line. A historic
id is crossed over by taking its body after its old letters and joining its digit groups with dots,
so ``C9b3b`` is ``CCS-9b.3b`` and ``H2.6d`` is ``FMH-2.6d``.

A state cell opens with a word of the closed set and the day it was reached. The historic words map
onto the set, and a cell with no day takes the day its text was committed, read from git, since a
day is a fact the record already held and never invented here.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional, Sequence

sys.path.insert(0, str(Path(__file__).resolve().parent))
import work_board as wb  # noqa: E402

SEGMENT_RE = re.compile(r"[A-Z]*\d+[a-z]?")
CROSSWALK = "slice-crosswalk-2026-11.md"
PACKS = "validation pack"  # the unit column of a crosswalk row that records a Validation Pack's file name


def crossed(prefix: str, body: str) -> str:
    return f"{prefix}-{'.'.join(SEGMENT_RE.findall(body))}"


@dataclass(frozen=True)
class Rule:
    """How one unit's historic ids read. ``patterns`` match a whole id and give its body, and
    ``packs`` match a Validation Pack's file stem and give the body the same way."""
    unit: str
    prefixes: tuple[str, ...]
    patterns: tuple[str, ...] = ()
    packs: tuple[str, ...] = ()
    bare: bool = False  # ids that are bare numbers, read in the board's id cell only


# The historic shapes, counted on 2026-11-02 (sketch work-board §9a). A unit absent here keeps its ids.
RULES: tuple[Rule, ...] = (
    Rule("applied-insurance-reference", ("AIR",), (r"S(\d)",), (r"applied-insurance-reference-(\d+\.\d+[a-z]?)",)),
    Rule("applied-ontology-readiness", ("AOR",), (), (r"applied-ontology-readiness-aor-(\d+[a-z]?)",)),
    Rule("computable-contract-substrate", ("CCS", "HQ"), (r"C(\d+[a-z]?(?:\d+[a-z]?)*)", r"(F\d+)"),
         (r"computable-contract-substrate-c(\d+[a-z]?(?:\d+[a-z]?)*)",)),
    Rule("formal-methods", ("FM",), (r"(D\d+)", r"(PF\d+)"), (r"formal-methods-(\d+)", r"formal-methods-(c\d+)")),
    Rule("formal-methods-track-b", ("FMB",), (r"B(\d+(?:\.\d+)?[a-z]?)",)),
    Rule("formal-methods-track-c", ("FMC",), (r"C(\d+(?:\.\d+)?[a-z]?)",)),
    Rule("formal-methods-track-e", ("FME",), (r"E(\d+(?:\.\d+)?[a-z]?)",)),
    Rule("formal-methods-track-h", ("FMH",), (r"H(\d+(?:\.\d+)?[a-z]?)", r"(HO\d+)"),
         (r"FMH-H(\d+)-(\d+[a-z]?)", r"FMH-(HO\d+)")),
    Rule("identity-minting", ("IM",), (r"M(\d+)",), (r"identity-minting-m(\d+)",)),
    Rule("improved-ontology-documentation", ("OD",), (r"OD(\d+[a-z]?)", r"(RC\d+[a-z]?)", r"(DOC\d+[a-z]?)", r"(MC\d+[a-z]?)"),
         (r"OD(\d+[a-z]?)", r"(RC\d+[a-z]?)", r"(DOC\d+[a-z]?)", r"(MC\d+[a-z]?)")),
    Rule("multi-store-conformance", ("MSC",), (), (r"multi-store-conformance-msc(\d+)",)),
    Rule("normative-rule-substrate", ("NRS",), (r"N(\d+)",)),
    Rule("persistence-compiler-iri-sync", ("PCI",), (r"(\d+)",), (r"persistence-compiler-iri-sync-slice-(\d+)",), bare=True),
    Rule("phase-0-status", ("PLT",), (r"P(\d+(?:\.\d+)*[a-z]?)",)),
    Rule("rdf-sparql-patterns-status", ("RSP",), (r"(\d+)\.?",), bare=True),
    Rule("vocabulary-temporal-binding", ("VTB",), (r"(\d+)\.?",), bare=True),
    Rule("word-authoring-poc", ("WA",), (r"WA(\d+[a-z]?)",), (r"word-authoring-poc-wa(\d+[a-z]?)",)),
    Rule("ensemble", ("ES",), (), (r"ensemble-es-(\d+)",)),
    Rule("ledger", ("LG",), (), (r"ledger-lg-(\d+)",)),
    Rule("git-hooks", ("GH",)),
    Rule("insurml-alignment", ("IMA",)),
    Rule("ontology-remediation", ("OR",)),
    Rule("work-board", ("WB",)),
)

# The historic state words, longest first, each mapped onto the set. A cell is read lowercased
# with its bold and emoji stripped.
WORDS: tuple[tuple[str, str], ...] = (
    ("merged and signed off", "merged"), ("merged by squash", "merged"), ("squash-merged", "merged"),
    ("merged", "merged"), ("tagged", "tagged"), ("released", "tagged"),
    ("signed off", "verified"), ("signed-off", "verified"), ("accepted", "verified"), ("approved", "verified"),
    ("verified", "verified"), ("passed", "verified"), ("validated", "verified"),
    ("complete", "built"), ("done", "built"), ("committed", "built"), ("implemented", "built"), ("built", "built"),
    ("delivered", "built"), ("placed", "built"), ("drafted", "built"), ("handed off", "built"), ("handed over", "built"),
    ("written", "built"), ("in review", "built"), ("awaiting review", "built"),
    ("half built", "building"), ("in progress", "building"), ("building", "building"), ("started", "building"),
    ("attempted", "building"), ("under way", "building"), ("underway", "building"),
    ("briefed", "briefed"), ("brief written", "briefed"),
    ("retired", "dropped"), ("dropped", "dropped"), ("superseded", "dropped"), ("moved to", "dropped"),
    ("folded into", "dropped"), ("withdrawn", "dropped"), ("abandoned", "dropped"),
    ("blocked", "blocked"), ("waiting", "blocked"), ("on hold", "blocked"), ("paused", "blocked"),
    ("not started", "planned"), ("queued", "planned"), ("outline only", "planned"), ("outlined", "planned"),
    ("scoped", "planned"), ("planned", "planned"), ("proposed", "planned"), ("pending", "planned"), ("open", "planned"),
    ("deferred", "planned"), ("conditional", "planned"), ("not yet", "planned"),
)
DAY_RE = re.compile(r"\b(\d{4}-\d{2}-\d{2})\b")
BRANCH_LINE_RE = re.compile(r"^\*\*Branch:\*\*[^\n]*\n", re.M)
UNIT_ID_RE = re.compile(r"^\*\*Unit ID:\*\*[^\n]*$", re.M)


def map_state(cell: str, blocked: str) -> Optional[tuple[str, str, str]]:
    """(state, day, remainder) for a historic cell, or None where no word maps. The earliest word
    in the cell wins, the longest on a tie, so "not started" is read before "started". A cell that
    says merged anywhere is at least merged. The remainder is the cell with the word, the day and
    the bold stripped, kept after the dated word."""
    text = cell.replace("**", "").replace("✅", "").replace("🔨", "").replace("📝", "").replace("⏳", "").strip()
    lower = text.lower()
    if wb.STATE_RE.match(lower) and lower.split()[0] in wb.STATES and not (lower.startswith("merged") and "tagged" in lower):
        return None  # already on the set
    found = [(lower.find(word), -len(word), word, state) for word, state in WORDS if 0 <= lower.find(word) <= 24]
    if not found:
        return None
    at, _, word, state = min(found)
    cleared = blocked.strip().lower() in ("", "nothing", "none", "—", "-")
    if state == "blocked" and word == "waiting" and cleared:
        state = "planned"
    if "merged" in lower and state in ("verified", "built", "building", "merged"):
        state = "tagged" if "tagged" in lower else "merged"
    day = DAY_RE.search(text)
    remainder = text[:at] + text[at + len(word):]
    if day:
        remainder = remainder.replace(day.group(1), "")
    if state in ("merged", "tagged") and word not in ("merged", "tagged"):
        remainder = re.sub(r"\b(merged|tagged)\b", "", remainder)
    remainder = re.sub(r"\s+([,.])(?=\s|$)", r"\1", remainder)
    remainder = re.sub(r"([,.])(?:\s*[,.])+(?=\s|$)", r"\1", remainder).strip(" ,.:")
    if remainder.startswith("(") and remainder.endswith(")") and remainder.count("(") == 1:
        remainder = remainder[1:-1].strip()
    return state, day.group(1) if day else "", remainder


# ---- the crosswalk --------------------------------------------------------------------------------

@dataclass(frozen=True)
class Crossing:
    unit: str
    old: str
    new: str


def unit_ids(repo: wb.Repo, unit: str) -> list[str]:
    path = repo.root / repo.status / f"{unit}.md"
    if not path.exists():
        return []
    parsed = wb.parse_unit(unit, path.read_text(encoding="utf-8"))
    return [row.id for row in (parsed.board.rows if parsed.board else ())]


def crosswalk(repo: wb.Repo) -> list[Crossing]:
    """One crossing per historic id on a unit's board, from the unit's rule. An id the rule does
    not match, and an id already in the grammar, are left out."""
    out: list[Crossing] = []
    for rule in RULES:
        for old in unit_ids(repo, rule.unit):
            new = cross(rule, old)
            if new and new != old:
                out.append(Crossing(rule.unit, old, new))
    return sorted(set(out), key=lambda c: (c.unit, c.old))


def cross(rule: Rule, old: str) -> Optional[str]:
    if re.fullmatch(r"[A-Z]{2,5}-[A-Z]*\d+[a-z]?(?:\.[A-Z]*\d+[a-z]?)*", old):
        return old
    for pattern in rule.patterns:
        m = re.fullmatch(pattern, old)
        if m:
            return crossed(rule.prefixes[0], m.group(1))
    return None


def pack_target(rule: Rule, stem: str) -> Optional[str]:
    for pattern in rule.packs:
        m = re.fullmatch(pattern, stem)
        if m:
            return crossed(rule.prefixes[0], ".".join(g for g in m.groups()))
    return None


def own_files(repo: wb.Repo, unit: str) -> set[Path]:
    """The unit's own documents: its record, its plans, its review and its Validation Packs, by the
    unit's name or, for a pack, its prefix. A longer unit name wins a file it shares a start with,
    so formal-methods-track-b owns its own record and formal-methods does not."""
    dev = repo.root / repo.developer
    longer = [r.unit for r in RULES if r.unit != unit and r.unit.startswith(unit + "-")]
    found: set[Path] = set()
    for kind in ("status", "plans", "review", "validation"):
        for path in dev.glob(f"{kind}/{unit}*.md"):
            if not any(path.stem == o or path.stem.startswith(o + "-") for o in longer):
                found.add(path)
    rule = next((r for r in RULES if r.unit == unit), None)
    for prefix in (rule.prefixes if rule else ()):
        found |= set(dev.glob(f"validation/{prefix}-*.md"))
    return found


def sweep_files(repo: wb.Repo) -> list[Path]:
    """Every file the sweep rewrites: the developer and architecture areas, the skills and the
    identifier exceptions baseline, each found through the catalogue, never by a path written here."""
    files: list[Path] = []
    for area in (repo.developer, repo.architecture, repo.skills):
        if area is not None and (repo.root / area).is_dir():
            files += sorted((repo.root / area).rglob("*.md"))
    files += [p for p in repo.exceptions if p.exists()]
    return [f for f in files if f.name != CROSSWALK]


def pattern_for(old: str) -> re.Pattern[str]:
    """The whole id, not inside another id: not after a word character, a hyphen, a slash or a
    dot, and not before one, nor before a question, decision or test suffix such as -Q1 or -01."""
    return re.compile(r"(?<![\w\-/.])" + re.escape(old) + r"(?![\w.]|-[A-Z]?\d)")


def distinctive(old: str) -> bool:
    """An id safe to replace outside its unit's own documents: prefixed, dotted, or with an inner
    letter, since a bare letter and digit such as C2 or B1 is also prose."""
    return "-" in old or "." in old or re.search(r"\d[a-z]\d", old) is not None or re.match(r"[A-Z]{2,}", old) is not None


def rename(repo: wb.Repo, apply: bool) -> list[str]:
    """Build the crosswalk, write it, then sweep. A unit's own documents take every crossing of the
    unit. Every other file takes only a distinctive old id that one unit claims."""
    crossings = crosswalk(repo)
    report: list[str] = []
    notes = repo.root / repo.developer / "notes"
    notes.mkdir(exist_ok=True)
    walk = notes / CROSSWALK
    kept: set[Crossing] = set()  # rows written by an earlier run, pack renames among them
    if walk.exists():
        for line in walk.read_text(encoding="utf-8").splitlines():
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) == 3 and cells[0] not in ("Was", "---") and not set(cells[0]) <= set("-"):
                kept.add(Crossing(cells[2], cells[0], cells[1]))
    every = sorted(kept | set(crossings), key=lambda c: (c.unit, c.old))
    table = ["<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->", "", "# Slice id crosswalk, 2026-11",
             "", "The historic slice ids and the ids the grammar gives them (plan work-board, WB-2), kept so an old commit message or tag note still resolves. Written by `mise run work:rename`, which keeps every row it ever wrote, never by hand.", "",
             "| Was | Is | Unit |", "|---|---|---|"]
    table += [f"| {c.old} | {c.new} | {c.unit} |" for c in every]
    if every:
        walk.write_text("\n".join(table) + "\n", encoding="utf-8")
    report.append(f"crosswalk: {len(crossings)} ids over {len({c.unit for c in crossings})} units this run, {len(every)} rows in docs/developer/notes/{CROSSWALK}")
    by_unit: dict[str, list[Crossing]] = {}
    claims: dict[str, set[str]] = {}
    for c in crossings:
        by_unit.setdefault(c.unit, []).append(c)
        claims.setdefault(c.old, set()).add(c.unit)
    every = [c for c in every if c.unit != PACKS] + [c for c in every if c.unit == PACKS]
    shared = sorted(old for old, units in claims.items() if len(units) > 1 and not old.rstrip(".").isdigit())
    if shared:
        report.append("claimed by two units, left for the hand outside their own documents: " + ", ".join(shared))
    bare_units = {r.unit for r in RULES if r.bare}
    by_unit = {u: cs for u, cs in by_unit.items() if u not in bare_units}
    general = [c for c in crossings if len(claims[c.old]) == 1 and distinctive(c.old) and c.unit not in bare_units]
    changed = 0
    for path in sweep_files(repo):
        text = path.read_text(encoding="utf-8")
        new = text
        owner = max((u for u in by_unit if path in own_files(repo, u)), key=len, default=None)
        rules = sorted(by_unit.get(owner, []), key=lambda c: -len(c.old)) if owner else []
        rules += [c for c in sorted(general, key=lambda c: -len(c.old)) if c.unit != owner]
        for c in rules:
            new = pattern_for(c.old).sub(c.new, new)
        for prefix in {p for r in RULES for p in r.prefixes}:
            new = re.sub(rf"\b{prefix} ({prefix}-)", r"\1", new)
        if new != text:
            changed += 1
            if apply:
                path.write_text(new, encoding="utf-8")
    report.append(f"mentions: {changed} files {'rewritten' if apply else 'would change'}")
    # Validation Packs
    validation = repo.root / repo.developer / "validation"
    moves: list[tuple[str, str]] = []
    unmatched: list[str] = []
    for pack in sorted(validation.glob("*.md")):
        target = next((t for r in RULES if (t := pack_target(r, pack.stem))), None)
        if target and target != pack.stem:
            moves.append((pack.name, f"{target}.md"))
        elif not target and not re.fullmatch(r"[A-Z]{2,5}-[A-Z]*\d+[a-z]?(?:\.[A-Z]*\d+[a-z]?)*", pack.stem):
            unmatched.append(pack.name)
    if apply:
        for old, new in moves:
            subprocess.run(["git", "mv", f"{validation / old}", f"{validation / new}"], cwd=repo.root, check=True)
        recorded = {(c.old, c.new) for c in every if c.unit == PACKS} | set(moves)
        for path in sweep_files(repo):
            text = path.read_text(encoding="utf-8")
            new_text = text
            for old, new in recorded:
                new_text = new_text.replace(f"validation/{old}", f"validation/{new}").replace(f"]({old})", f"]({new})").replace(f"](./{old})", f"]({new})").replace(f"]({old}#", f"]({new}#")
            if new_text != text:
                path.write_text(new_text, encoding="utf-8")
        every = sorted(set(every) | {Crossing(PACKS, old, new) for old, new in moves}, key=lambda c: (c.unit, c.old))
        if every:
            walk.write_text("\n".join(table[:8] + [f"| {c.old} | {c.new} | {c.unit} |" for c in every]) + "\n", encoding="utf-8")
    report.append(f"validation packs: {len(moves)} {'renamed' if apply else 'to rename'}, {len(unmatched)} left as they are: " + ", ".join(unmatched))
    return report


# ---- normalising -----------------------------------------------------------------------------------

def committed_day(root: Path, path: Path, needle: str) -> str:
    rel = path.relative_to(root).as_posix()
    out = subprocess.run(["git", "log", "-1", "--format=%cs", f"-S{needle}", "--", rel], cwd=root,
                         capture_output=True, text=True).stdout.strip()
    if not out:
        out = subprocess.run(["git", "log", "-1", "--format=%cs", "--", rel], cwd=root, capture_output=True, text=True).stdout.strip()
    return out


def split_ids(cell: str) -> list[str]:
    """``AOR-10, AOR-11`` and ``PF1/PF4`` are two slices, ``AOR-2 to AOR-4`` three."""
    cell = cell.strip("`* ")
    m = re.fullmatch(r"([A-Z]+-?)(\d+)\s+to\s+\1(\d+)", cell)
    if m:
        return [f"{m.group(1)}{n}" for n in range(int(m.group(2)), int(m.group(3)) + 1)]
    head = cell.split("(")[0].strip()
    parts = [p.strip("`* ") for p in re.split(r"[,/]| and ", head) if p.strip("`* ")]
    ids = [p.split(" ")[0].strip("`*,;:") for p in parts]
    if len(parts) > 1 and all(re.fullmatch(r"[A-Z]{0,5}-?\d[\w.]*|\d+\.?", i) for i in ids) and all(" " not in p for p in parts):
        return ids
    return [ids[0]] if ids and ids[0] else [cell]


def normalise_record(repo: wb.Repo, path: Path) -> tuple[str, list[str]]:
    """The record's text with its board on the standard columns and words, its Branch line gone and
    a Unit ID line present, plus the cells no word maps, left as they were."""
    root = repo.root
    text = path.read_text(encoding="utf-8")
    unit = path.stem
    notes: list[str] = []
    text = BRANCH_LINE_RE.sub("", text)
    if not UNIT_ID_RE.search(text):
        text = re.sub(r"^(# [^\n]*\n)", rf"\1\n**Unit ID:** `{unit}`\n", text, count=1, flags=re.M)
    parsed = wb.parse_unit(unit, text)
    board = parsed.board
    if board:
        lines = text.splitlines()
        header = list(board.columns)
        lower = [h.lower() for h in header]
        keep = [i for i, h in enumerate(lower) if h not in ("#", "slice", "state", "status", "deliverable", "delivers", "scope") and not h.startswith("blocked")]
        new_rows: list[str] = []
        for row in board.rows:
            raw = wb.cells(lines[row.line - 1])
            raw += [""] * (len(header) - len(raw))
            id_cell = raw[lower.index("#")] if "#" in lower else raw[lower.index("slice")]
            ids = split_ids(id_cell)
            rule = next((r for r in RULES if r.unit == unit and r.bare), None)
            if rule:
                ids = [cross(rule, i) or i for i in ids]
            deliverable = row.deliverable
            if not deliverable and "#" not in lower:
                rest = id_cell.strip("`* ")
                m = re.match(r"\S+\s*\(?(.*?)\)?$", rest)
                deliverable = m.group(1).strip() if m and m.group(1) and m.group(1) != rest else ""
            if row.state is None:
                mapped = map_state(row.raw, row.blocked_on)
                if mapped:
                    state, day, remainder = mapped
                    if state in wb.DATED and not day:
                        day = committed_day(root, path, raw[lower.index("state") if "state" in lower else lower.index("status")])
                    cell = f"{state} {day}".strip() + (f", {remainder}" if remainder else "")
                else:
                    cell = row.raw
                    notes.append(f"{path.relative_to(root).as_posix()}:{row.line}: no word maps '{row.raw[:50]}'")
            else:
                cell = row.raw
                if row.state in wb.DATED and not row.day:
                    cell = f"{row.state} {committed_day(root, path, row.raw)}" + row.raw[len(row.state):]
            blocked = row.blocked_on
            if blocked.strip().lower() in ("nothing", "none", "—", "-"):
                blocked = ""
            extras = [raw[i] for i in keep]
            for slice_id in ids:
                new_rows.append("| " + " | ".join(c.replace(";", ",") for c in [slice_id, deliverable, cell, blocked, *extras]) + " |")
        new_header = "| " + " | ".join(["Slice", "Deliverable", "State", "Blocked on", *[header[i] for i in keep]]) + " |"
        separator = "|" + "---|" * (4 + len(keep))
        first, last = board.line - 1, board.rows[-1].line if board.rows else board.line + 1
        lines[first:last] = [new_header, separator, *new_rows]
        text = "\n".join(lines) + "\n"
        parsed = wb.parse_unit(unit, text)
    status = wb.STATUS_LINE_RE.search(text)
    if status and parsed.state is None:
        if parsed.board and parsed.board.rows:
            nxt = next((r for r in parsed.board.rows if r.id == parsed.next), None)
            row = nxt or max(parsed.board.rows, key=lambda r: r.key)
            state, day = (row.state or "planned"), row.day
            if not day and state in wb.DATED:
                day = committed_day(root, path, status.group(1)[:40])
            text = text.replace(status.group(0), f"**Status:** {state} {day}. {status.group(1)}".replace("  ", " "), 1)
        else:
            notes.append(f"{path.relative_to(root).as_posix()}: Status line opens with no state word and the record has no board")
    elif not status and parsed.board and parsed.board.rows:
        nxt = next((r for r in parsed.board.rows if r.id == parsed.next), None)
        row = nxt or max(parsed.board.rows, key=lambda r: r.key)
        state, day = (row.state or "planned"), row.day
        line = f"**Status:** {state} {day}.".replace(" .", ".")
        m = UNIT_ID_RE.search(text)
        text = text[:m.end() + 1] + line + "\n" + text[m.end() + 1:]
    elif not status:
        notes.append(f"{path.relative_to(root).as_posix()}: no Status line")
    return text, notes


def declare_prefixes(repo: wb.Repo, apply: bool) -> list[str]:
    out: list[str] = []
    for rule in RULES:
        plan = repo.root / repo.plans / f"{rule.unit}.md"
        if not plan.exists():
            continue
        text = plan.read_text(encoding="utf-8")
        if wb.PREFIX_RE.search(text) or "**Prefix:**" in text:
            continue
        line = f"**Prefix:** {', '.join(rule.prefixes)}\n"
        m = UNIT_ID_RE.search(text)
        new = text[:m.end() + 1] + line + text[m.end() + 1:] if m else re.sub(r"^(# [^\n]*\n)", rf"\1\n{line}", text, count=1, flags=re.M)
        out.append(f"{plan.relative_to(repo.root).as_posix()}: Prefix {', '.join(rule.prefixes)}")
        if apply:
            plan.write_text(BRANCH_LINE_RE.sub("", new), encoding="utf-8")
    return out


def normalise(repo: wb.Repo, apply: bool) -> list[str]:
    report: list[str] = []
    changed = 0
    for path in sorted((repo.root / repo.status).glob("*.md")):
        new, notes = normalise_record(repo, path)
        report += notes
        if new != path.read_text(encoding="utf-8"):
            changed += 1
            if apply:
                path.write_text(new, encoding="utf-8")
    for plan in sorted((repo.root / repo.plans).glob("*.md")):
        text = plan.read_text(encoding="utf-8")
        if BRANCH_LINE_RE.search(text):
            changed += 1
            if apply:
                plan.write_text(BRANCH_LINE_RE.sub("", text), encoding="utf-8")
    report += declare_prefixes(repo, apply)
    report.append(f"records and plans: {changed} {'rewritten' if apply else 'would change'}")
    return report


# ---- adopting ----------------------------------------------------------------------------------------

GRAMMAR_RE = re.compile(r"[A-Z]{2,5}-(?![QD]\d)[A-Z]*\d+[a-z]?(?:\.[A-Z]*\d+[a-z]?)*")
EXCEPTIONS_HEADING = "# Slices a plan names"


def tables_in(text: str) -> list[tuple[int, list[str], list[list[str]]]]:
    """Every table as (header line number, headers, rows of cells)."""
    lines = text.splitlines()
    out: list[tuple[int, list[str], list[list[str]]]] = []
    for number, line in enumerate(lines, 1):
        if not line.startswith("|") or number >= len(lines) or not wb.SEPARATOR_RE.match(lines[number].strip()):
            continue
        header = wb.cells(line)
        rows: list[list[str]] = []
        for body in lines[number + 1:]:
            if not body.startswith("|"):
                break
            row = wb.cells(body)
            rows.append(row + [""] * (len(header) - len(row)))
        out.append((number, header, rows))
    return out


def first_commit_day(root: Path, path: Path) -> str:
    rel = path.relative_to(root).as_posix()
    out = subprocess.run(["git", "log", "--follow", "--diff-filter=A", "--format=%cs", "--", rel], cwd=root, capture_output=True, text=True).stdout.strip()
    return out.splitlines()[-1] if out else committed_day(root, path, "")


def candidates_for(repo: wb.Repo, unit: str, prefixes: tuple[str, ...], record_text: str, board: wb.Board) -> dict[str, tuple[str, str, str, str]]:
    """Slices the unit names outside its board, as id -> (state cell, deliverable, blocked on, source),
    the record's other tables first, then the Validation Packs, then the plans' tables."""
    root = repo.root
    found: dict[str, tuple[str, str, str, str]] = {}
    mine = lambda i: GRAMMAR_RE.fullmatch(i) and i.split("-")[0] in prefixes

    def take(header: list[str], rows: list[list[str]], source: str, default_state: str, day_for: Callable[[], str]) -> None:
        lower = [h.lower() for h in header]
        id_at = next((i for i, h in enumerate(lower) if h in ("slice", "#", "id", "slices")), None)
        if id_at is None:
            return
        state_at = next((i for i, h in enumerate(lower) if h in ("state", "status")), None)
        blocked_at = next((i for i, h in enumerate(lower) if h.startswith(("blocked", "depends", "start after", "waits"))), None)
        text_at = next((i for i, h in enumerate(lower) if i != id_at and h in ("deliverable", "delivers", "content", "scope", "note", "slice")), None)
        for row in rows:
            for slice_id in split_ids(row[id_at]):
                if not mine(slice_id) or slice_id in found:
                    continue
                cell = row[state_at] if state_at is not None else ""
                state, day, _ = wb.parse_state(cell)
                if state is None and cell:
                    mapped = map_state(cell, row[blocked_at] if blocked_at is not None else "")
                    if mapped:
                        state, day, _ = mapped
                state = state or default_state
                if state in wb.DATED and not day:
                    day = day_for()
                found[slice_id] = (f"{state} {day}".strip(), row[text_at] if text_at is not None else "", row[blocked_at] if blocked_at is not None else "", source)

    record = root / repo.status / f"{unit}.md"
    for number, header, rows in tables_in(record_text):
        if number != board.line:
            take(header, rows, f"{record.relative_to(root).as_posix()}:{number}", "planned", lambda: committed_day(root, record, ""))
    for prefix in prefixes:
        for pack in sorted((root / repo.developer / "validation").glob(f"{prefix}-*.md")):
            if mine(pack.stem) and pack.stem not in found:
                found[pack.stem] = (f"built {first_commit_day(root, pack)}", "", "", pack.relative_to(root).as_posix())
    for plan in sorted((root / repo.plans).glob(f"{unit}*.md")):
        text = plan.read_text(encoding="utf-8")
        for number, header, rows in tables_in(text):
            take(header, rows, f"{plan.relative_to(root).as_posix()}:{number}", "planned", lambda: committed_day(root, plan, ""))
    return found


def adopt(repo: wb.Repo, apply: bool) -> list[str]:
    """Append to each unit's board the slices its record's other tables, its Validation Packs and its
    plans name and the board lacks, each in the state its source gives, then drop them from the
    identifier exceptions baseline. Idempotent, and reports without ``--apply``."""
    report: list[str] = []
    adopted: set[str] = set()
    for unit, parsed in wb.units_here(repo).items():
        prefixes = tuple(p.strip() for p in parsed.prefix.split(",") if p.strip())
        if not prefixes:
            continue
        record = repo.root / repo.status / f"{unit}.md"
        text = record.read_text(encoding="utf-8")
        if not parsed.board:
            # A record with no board gains the standard one at its end, so the unit's slices have a home.
            text = text.rstrip("\n") + "\n\n## Board\n\n| Slice | Deliverable | State | Blocked on |\n|---|---|---|---|\n"
            parsed = wb.parse_unit(unit, text, "")
            if not parsed.board:
                report.append(f"{unit}: no board to adopt onto")
                continue
            report.append(f"{unit}: a board added at the end of the record")
        have = {row.id for row in parsed.board.rows}
        new = {i: c for i, c in candidates_for(repo, unit, prefixes, text, parsed.board).items() if i not in have}
        if not new:
            continue
        lines = text.splitlines()
        last = parsed.board.rows[-1].line if parsed.board.rows else parsed.board.line + 1
        extra = len(parsed.board.columns) - 4
        for slice_id, (state, deliverable, blocked, source) in sorted(new.items()):
            cells = [slice_id, plain_cell(deliverable), state, plain_cell(blocked)] + [""] * extra
            lines.insert(last, "| " + " | ".join(cells) + " |")
            last += 1
        adopted |= set(new)
        by_source = {}
        for _, (_, _, _, source) in new.items():
            by_source[source.split(":")[0]] = by_source.get(source.split(":")[0], 0) + 1
        report.append(f"{unit}: {len(new)} rows " + ("adopted" if apply else "to adopt") + " from " + ", ".join(f"{s} ({n})" for s, n in sorted(by_source.items())))
        if apply:
            record.write_text("\n".join(lines) + "\n", encoding="utf-8")
    if apply and adopted:
        for path in repo.exceptions:
            if not path.exists():
                continue
            kept = [l for l in path.read_text(encoding="utf-8").splitlines() if l.split("#")[0].strip() not in adopted]
            path.write_text("\n".join(kept) + "\n", encoding="utf-8")
    report.append(f"{len(adopted)} slices {'adopted' if apply else 'would be adopted'}")
    return report


def plain_cell(cell: str) -> str:
    return wb.LINK_RE.sub(r"\1", cell).replace(";", ",").replace("|", "/").strip()


def regroup_exceptions(repo: wb.Repo, apply: bool) -> list[str]:
    """Rewrite the work-board section of the exceptions baseline grouped by unit, each group headed
    by the unit it belongs to, so a unit's next slice sees its own list."""
    prefixes: dict[str, str] = {}
    for unit, parsed in wb.units_here(repo).items():
        for p in parsed.prefix.split(","):
            if p.strip():
                prefixes[p.strip()] = unit
    for plan in (repo.root / repo.plans).glob("*.md"):
        m = re.search(r"^\*\*Prefix:\*\*\s*(.+?)\s*$", plan.read_text(encoding="utf-8"), re.M)
        if m:
            for p in m.group(1).split(","):
                prefixes.setdefault(p.strip(), plan.stem)
    out: list[str] = []
    for path in repo.exceptions:
        if not path.exists() or EXCEPTIONS_HEADING not in path.read_text(encoding="utf-8"):
            continue
        text = path.read_text(encoding="utf-8")
        head, _, tail = text.partition(EXCEPTIONS_HEADING)
        section_lines = (EXCEPTIONS_HEADING + tail).splitlines()
        comment = [l for l in section_lines if l.startswith("#") and not l.startswith("# unit ")]
        ids = [l.split("#")[0].strip() for l in section_lines if l.strip() and not l.startswith("#")]
        groups: dict[str, list[str]] = {}
        for i in ids:
            groups.setdefault(prefixes.get(i.split("-")[0], "no unit declares this prefix"), []).append(i)
        body = "\n".join(comment) + "\n"
        for unit, members in sorted(groups.items()):
            body += f"# unit {unit}, {len(members)} slice(s)\n" + "".join(f"{i}  # named in a plan, no board row yet\n" for i in sorted(set(members)))
        out.append(f"{path.relative_to(repo.root).as_posix()}: {len(ids)} ids in {len(groups)} groups")
        if apply:
            path.write_text(head.rstrip("\n") + "\n\n" + body, encoding="utf-8")
    return out


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--root", type=Path)
    parser.add_argument("command", choices=("rename", "normalise", "adopt"))
    parser.add_argument("--apply", action="store_true", help="write the changes. Without it, report only")
    args = parser.parse_args(argv)
    repo = wb.Repo.here(args.root)
    if args.command == "adopt":
        lines = adopt(repo, args.apply) + regroup_exceptions(repo, args.apply)
    else:
        lines = rename(repo, args.apply) if args.command == "rename" else normalise(repo, args.apply)
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
