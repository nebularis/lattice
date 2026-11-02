# SPDX-License-Identifier: MPL-2.0
"""Where the work is: the slice boards of the status records, read across every branch.

A status record's slice board is the one place a slice's state is written (plan work-board,
decision 1). This tool reads the boards at the tip of every local and remote branch without a
checkout, joins the rows per slice, and prints where everything is. It also writes INDEX.md's
generated region from the working tree, so the knowledge index can answer from the same rows.

  python tools/work_board.py board [--all] [--fetch] [--measure] [--commits]
  python tools/work_board.py build [--check]
  python tools/work_board.py parse <status record>      the board as the tool reads it

A state cell opens with a word of the closed set and the day it was reached, newest first, so
"merged 2026-10-28, built 2026-10-25" is a trail. The join across branches takes the row furthest
along the ladder, then the latest day. Two branches other than main both building one slice is a
double claim, printed and never chosen. A branch's row behind main's is stale, not a claim.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Optional, Sequence

LADDER = ("planned", "briefed", "building", "built", "verified", "merged", "tagged")
ASIDE = ("blocked", "dropped")
STATES = LADDER + ASIDE
DATED = frozenset(LADDER[2:])
RANK = {state: n for n, state in enumerate(LADDER)}
RANK.update({"blocked": 1, "dropped": -1})
STATE_RE = re.compile(r"^(" + "|".join(STATES) + r")\b\s*(\d{4}-\d{2}-\d{2})?\s*(.*)$")
STATUS_LINE_RE = re.compile(r"^\*\*Status:\*\*\s*(.+?)\s*$", re.M)
UNIT_TYPE_RE = re.compile(r"^\*\*Unit type:\*\*\s*(.+?)\s*$", re.M)
PREFIX_RE = re.compile(r"^\*\*Prefix:\*\*\s*([A-Z]{2,5}(?:,\s*[A-Z]{2,5})*)\s*$", re.M)
SEPARATOR_RE = re.compile(r"^\|[\s:|-]*\|$")
MAIN = "main"
REGION_BEGIN = "<!-- BEGIN GENERATED work-board. Written by `mise run build:work` from the status records. Edit a status record, never this region. -->"
REGION_END = "<!-- END GENERATED work-board -->"
ROADMAP_BEGIN = "<!-- BEGIN GENERATED work-board-{name}. Written by `mise run build:roadmap` from the status records on every branch. Edit a status record, never this region. -->"
ROADMAP_END = "<!-- END GENERATED work-board-{name} -->"
SIZEABLE = 5  # dated slices a unit outside an epic needs for a chart of its own


# ---- the repository ----------------------------------------------------------------------------

@dataclass(frozen=True)
class Repo:
    """The root, and the developer area relative to it, which the catalogue names (STD-273)."""
    root: Path
    developer: Path
    architecture: Optional[Path] = None
    skills: Optional[Path] = None
    exceptions: tuple[Path, ...] = ()

    @classmethod
    def here(cls, root: Optional[Path] = None) -> "Repo":
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import lattice_repo_catalogue as rc  # noqa: E402
        catalogue = rc.load(root)
        return cls(catalogue.root, catalogue.area("developer"), catalogue.area("architecture"), catalogue.area("skills"),
                   tuple(catalogue.files("identifier-exceptions.txt")))

    @property
    def status(self) -> Path:
        return self.developer / "status"

    @property
    def plans(self) -> Path:
        return self.developer / "plans"

    @property
    def index(self) -> Path:
        return self.developer / "INDEX.md"

    @property
    def roadmap(self) -> Path:
        return self.developer / "ROADMAP.md"


def git(root: Path, *args: str, check: bool = True) -> str:
    result = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, encoding="utf-8")
    if check and result.returncode:
        raise RuntimeError(f"git {' '.join(args)}: {result.stderr.strip()}")
    return result.stdout


# ---- the board -----------------------------------------------------------------------------------

@dataclass(frozen=True)
class Row:
    """One slice's row. ``trail`` is newest first, ``state`` and ``day`` its head. A cell that does not
    open with a word of the set parses as state None, which the board prints and the check refuses."""
    unit: str
    id: str
    deliverable: str
    state: Optional[str]
    day: str
    trail: tuple[tuple[str, str], ...]
    blocked_on: str
    raw: str
    line: int

    @property
    def rank(self) -> int:
        return RANK[self.state] if self.state else -2

    @property
    def key(self) -> tuple[int, str]:
        return (self.rank, self.day)


@dataclass(frozen=True)
class Board:
    unit: str
    columns: tuple[str, ...]
    rows: tuple[Row, ...]
    line: int
    heading: str = ""

    @property
    def anchor(self) -> str:
        """The slug of the heading above the board, as GitHub renders it, so a pointer names a
        section that survives an edit rather than a line number (STD-015)."""
        slug = re.sub(r"[^a-z0-9 -]", "", self.heading.lower()).strip().replace(" ", "-")
        return f"#{slug}" if slug else ""


@dataclass(frozen=True)
class Unit:
    """A unit as its status record and plan describe it at one ref."""
    id: str
    kind: str
    state: Optional[str]
    day: str
    status_text: str
    board: Optional[Board]
    prefix: str = ""

    @property
    def next(self) -> str:
        if not self.board:
            return ""
        for row in self.board.rows:
            if row.state in ("planned", "briefed", "building", "built", "verified", "blocked"):
                return row.id
        return ""


def cells(line: str) -> list[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def parse_state(cell: str) -> tuple[Optional[str], str, tuple[tuple[str, str], ...]]:
    """The state, the day and the trail of a cell. The trail stops at the first item that is not
    a state word, so free text after the dated word is kept out of it."""
    trail: list[tuple[str, str]] = []
    for item in cell.split(","):
        m = STATE_RE.match(item.strip().strip("*").strip())
        if not m:
            break
        trail.append((m.group(1), m.group(2) or ""))
        if m.group(3) and not m.group(3).startswith(","):
            break
    if not trail:
        return None, "", ()
    return trail[0][0], trail[0][1], tuple(trail)


def find_board(unit: str, text: str) -> Optional[Board]:
    """The first table with a state column and an identifier column. The standard board is
    ``Slice, Deliverable, State, Blocked on``. A board headed ``#`` keeps its ids there, and its
    ``Slice`` column is then the deliverable, which is how the older boards are written."""
    lines = text.splitlines()
    heading = ""
    for number, line in enumerate(lines, 1):
        if line.startswith("#"):
            heading = line.lstrip("#").strip()
        if not line.startswith("|") or number >= len(lines) or not SEPARATOR_RE.match(lines[number].strip()):
            continue
        header = cells(line)
        lower = [h.lower() for h in header]
        state_at = next((i for i, h in enumerate(lower) if h in ("state", "status")), None)
        if state_at is None:
            continue
        if "#" in lower:
            id_at = lower.index("#")
            deliverable_at = lower.index("slice") if "slice" in lower else None
        elif "slice" in lower:
            id_at = lower.index("slice")
            deliverable_at = next((i for i, h in enumerate(lower) if h in ("deliverable", "delivers", "scope")), None)
        else:
            continue
        blocked_at = next((i for i, h in enumerate(lower) if h.startswith("blocked")), None)
        rows: list[Row] = []
        for offset, body in enumerate(lines[number + 1:], number + 2):
            if not body.startswith("|"):
                break
            row = cells(body)
            if len(row) < len(header):
                row += [""] * (len(header) - len(row))
            raw_id = row[id_at].strip("`* ")
            slice_id = raw_id.split(" ")[0].split("(")[0].strip("`*,;:") or raw_id
            state, day, trail = parse_state(row[state_at])
            rows.append(Row(unit, slice_id, row[deliverable_at] if deliverable_at is not None else "",
                            state, day, trail, row[blocked_at] if blocked_at is not None else "",
                            row[state_at], offset))
        return Board(unit, tuple(header), tuple(rows), number, heading)
    return None


def parse_unit(unit: str, status_text: str, plan_text: str = "") -> Unit:
    status_line = STATUS_LINE_RE.search(status_text)
    state, day = None, ""
    text = status_line.group(1) if status_line else ""
    if status_line:
        state, day, _ = parse_state(text)
    kind_match = UNIT_TYPE_RE.search(plan_text)
    kind = re.split(r"[,(]", kind_match.group(1))[0].strip().lower() if kind_match else "unit"
    prefix = PREFIX_RE.search(plan_text)
    return Unit(unit, kind, state, day, text, find_board(unit, status_text), prefix.group(1) if prefix else "")


# ---- branches ------------------------------------------------------------------------------------

@dataclass(frozen=True)
class Branch:
    """A branch name with the tip the board reads, folded over its local and remote refs. ``drift``
    says how the local branch stands to its upstream, so an unpushed or unpulled worktree is seen."""
    name: str
    tip: str
    day: str
    local: bool
    remote: bool
    drift: str
    worktree: str = ""
    ahead_of_main: int = 0


def remotes(root: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    for line in git(root, "config", "--get-regexp", r"^remote\..*\.url$", check=False).splitlines():
        key, _, url = line.partition(" ")
        out[key.split(".")[1]] = url.strip()
    return out


def worktrees(root: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    path = ""
    for line in git(root, "worktree", "list", "--porcelain").splitlines():
        if line.startswith("worktree "):
            path = line[9:]
        elif line.startswith("branch refs/heads/"):
            out[line[18:]] = path
    return out


def branches(root: Path) -> list[Branch]:
    """Every branch, local or remote, one row each. Remotes that share a URL are one remote. Where
    the local and remote tips differ, the tip read is the one further on, and ``drift`` says so."""
    urls = remotes(root)
    seen_urls: dict[str, str] = {}
    folded = {name: seen_urls.setdefault(url, name) for name, url in urls.items()}
    local: dict[str, tuple[str, str]] = {}
    remote: dict[str, tuple[str, str]] = {}
    for line in git(root, "for-each-ref", "--format=%(refname) %(objectname) %(committerdate:short)",
                    "refs/heads", "refs/remotes").splitlines():
        ref, sha, day = line.split()
        if ref.startswith("refs/heads/"):
            local[ref[11:]] = (sha, day)
        else:
            rest = ref[13:]
            remote_name, _, name = rest.partition("/")
            if not name or name == "HEAD" or folded.get(remote_name, remote_name) != remote_name:
                continue
            remote.setdefault(name, (sha, day))
    trees = worktrees(root)
    main_sha = local.get(MAIN, remote.get(MAIN, ("", "")))[0]
    out: list[Branch] = []
    for name in sorted(set(local) | set(remote)):
        l, r = local.get(name), remote.get(name)
        if l and r and l[0] != r[0]:
            ahead, behind = git(root, "rev-list", "--count", "--left-right", f"{l[0]}...{r[0]}").split()
            tip, day = (l if int(ahead) else r)
            drift = f"local ahead {ahead}, behind {behind}" if int(ahead) and int(behind) else (
                f"local ahead {ahead}, not pushed" if int(ahead) else f"local behind {behind}, not pulled")
        elif l and r:
            tip, day, drift = l[0], l[1], "pushed"
        elif l:
            tip, day, drift = l[0], l[1], "local only"
        else:
            tip, day, drift = r[0], r[1], "remote only"
        ahead_of_main = int(git(root, "rev-list", "--count", f"{main_sha}..{tip}").strip()) if main_sha else 0
        out.append(Branch(name, tip, day, bool(l), bool(r), drift, trees.get(name, ""), ahead_of_main))
    return out


def units_at(repo: Repo, tip: str) -> dict[str, Unit]:
    """Every unit's status record, and its plan where one exists, read at ``tip`` through one
    ``git cat-file --batch`` call and no checkout."""
    status_dir, plans_dir = repo.status.as_posix(), repo.plans.as_posix()
    listing = git(repo.root, "ls-tree", "-r", "--format=%(objectname) %(path)", tip, "--", status_dir, plans_dir, check=False)
    wanted: dict[str, tuple[str, str]] = {}
    for line in listing.splitlines():
        sha, _, path = line.partition(" ")
        if not path.endswith(".md"):
            continue
        name = Path(path).stem
        if path.startswith(status_dir + "/"):
            wanted[sha] = ("status", name)
        elif path.startswith(plans_dir + "/"):
            wanted[sha] = ("plan", name)
    blobs = read_blobs(repo.root, list(wanted))
    statuses: dict[str, str] = {}
    plans: dict[str, str] = {}
    for sha, (kind, name) in wanted.items():
        (statuses if kind == "status" else plans)[name] = blobs.get(sha, "")
    return {name: parse_unit(name, text, plans.get(name, "")) for name, text in sorted(statuses.items())}


def read_blobs(root: Path, shas: Sequence[str]) -> dict[str, str]:
    if not shas:
        return {}
    result = subprocess.run(["git", "cat-file", "--batch"], cwd=root, input=("\n".join(shas) + "\n").encode(),
                            capture_output=True)
    out: dict[str, str] = {}
    data = result.stdout
    pos = 0
    while pos < len(data):
        end = data.index(b"\n", pos)
        head = data[pos:end].split()
        pos = end + 1
        if len(head) < 3:
            continue
        size = int(head[2])
        out[head[0].decode()] = data[pos:pos + size].decode("utf-8", errors="replace")
        pos += size + 1
    return out


def units_here(repo: Repo) -> dict[str, Unit]:
    """The units as the working tree has them, which is what ``build`` reads."""
    out: dict[str, Unit] = {}
    for path in sorted((repo.root / repo.status).glob("*.md")):
        plan = repo.root / repo.plans / path.name
        out[path.stem] = parse_unit(path.stem, path.read_text(encoding="utf-8"),
                                    plan.read_text(encoding="utf-8") if plan.exists() else "")
    return out


# ---- the join ------------------------------------------------------------------------------------

@dataclass
class Joined:
    """One slice across branches. ``rows`` maps branch name to its row."""
    unit: str
    id: str
    rows: dict[str, Row] = field(default_factory=dict)

    @property
    def main(self) -> Optional[Row]:
        return self.rows.get(MAIN)

    @property
    def winner(self) -> tuple[str, Row]:
        return max(self.rows.items(), key=lambda item: (item[1].key, item[0] == MAIN, item[0]))

    @property
    def claims(self) -> list[str]:
        return sorted(name for name, row in self.rows.items() if row.state == "building" and name != MAIN)

    @property
    def stale(self) -> list[str]:
        base = self.main
        return sorted(name for name, row in self.rows.items() if base and row.key < base.key and name != MAIN)

    @property
    def moved(self) -> list[str]:
        """Branches whose row is further on than main's, or that hold a row main lacks."""
        base = self.main
        return sorted(name for name, row in self.rows.items()
                      if name != MAIN and (base is None or row.key > base.key))


def join(boards: dict[str, dict[str, Unit]]) -> dict[tuple[str, str], Joined]:
    out: dict[tuple[str, str], Joined] = {}
    for branch, units in boards.items():
        for unit in units.values():
            for row in (unit.board.rows if unit.board else ()):
                out.setdefault((unit.id, row.id), Joined(unit.id, row.id)).rows[branch] = row
    return dict(sorted(out.items()))


# ---- measuring -----------------------------------------------------------------------------------

def share_on_main(root: Path, tip: str) -> str:
    """The branching skill's content measure: of the lines the branch added since its merge-base,
    the share present on main today. Squash merges leave ancestry silent, and this is the answer."""
    base = git(root, "merge-base", MAIN, tip).strip()
    added = present = 0
    for path in git(root, "diff", "--name-only", base, tip).splitlines():
        before = set(git(root, "show", f"{base}:{path}", check=False).splitlines())
        after = set(git(root, "show", f"{tip}:{path}", check=False).splitlines())
        on_main = set(git(root, "show", f"{MAIN}:{path}", check=False).splitlines())
        new = after - before
        added += len(new)
        present += len(new & on_main)
    return f"{present / added:.0%} of {added}" if added else "nothing added"


def commit_of(repo: Repo, tip: str, row: Row) -> str:
    """The commit that set the row's current state on that branch, read from git rather than written."""
    path = (repo.status / f"{row.unit}.md").as_posix()
    needle = f"{row.state} {row.day}".strip()
    return git(repo.root, "log", "-1", "--format=%h", f"-S{needle}", tip, "--", path, check=False).strip()


# ---- rendering -----------------------------------------------------------------------------------

def table(headers: Sequence[str], rows: Iterable[Sequence[str]]) -> list[str]:
    out = ["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)]
    out += ["| " + " | ".join(str(c).replace("|", "\\|") for c in row) + " |" for row in rows]
    return out


LINK_RE = re.compile(r"\[([^\]]*)\]\([^)]*\)")


def plain(cell: str, limit: int = 0) -> str:
    """A cell as the generated tables carry it: a link reduced to its text, since the record's
    relative links do not resolve from another file, and no semicolon, since the writing rule
    reads a generated line as prose."""
    text = LINK_RE.sub(r"\1", cell).replace(";", ",").strip()
    return text[:limit] if limit else text


def state_text(row: Row) -> str:
    if row.state is None:
        return f"? {plain(row.raw, 40)}"
    return f"{row.state} {row.day}".strip()


def board_text(repo: Repo, show_all: bool, measure: bool, commits: bool) -> str:
    """The live board: Units, Work and Branches, filtered to what differs from main unless ``show_all``."""
    found = branches(repo.root)
    boards = {b.name: units_at(repo, b.tip) for b in found}
    joined = join(boards)
    main_units = boards.get(MAIN, {})
    lines = [f"# Work board, {len(found)} branches", "", "## Units", ""]
    unit_rows = []
    for name, unit in main_units.items():
        on = sorted({b for (u, _), j in joined.items() if u == name for b in j.moved})
        if show_all or on:
            unit_rows.append((name, unit.kind, f"{unit.state or '?'} {unit.day}".strip(), unit.next, ", ".join(on)))
    lines += table(("Unit", "Kind", "State", "Next", "Moved on"), unit_rows)
    lines += ["", "## Work", ""]
    work_rows = []
    for (unit, slice_id), j in joined.items():
        winner_branch, winner = j.winner
        flags = []
        if len(j.claims) > 1:
            flags.append("double claim: " + ", ".join(j.claims))
        if j.stale:
            flags.append("stale: " + ", ".join(j.stale))
        if winner.state is None:
            flags.append("unparsed")
        if show_all or j.moved or len(j.claims) > 1 or winner.state is None:
            where = winner_branch + (f" at {commit_of(repo, next(b.tip for b in found if b.name == winner_branch), winner)}" if commits else "")
            work_rows.append((slice_id, unit, plain(winner.deliverable, 60), state_text(winner), where, plain(winner.blocked_on), ". ".join(flags)))
    lines += table(("Slice", "Unit", "Deliverable", "State", "Where", "Blocked on", "Flags"), work_rows)
    lines += ["", "## Branches", ""]
    branch_rows = []
    for b in found:
        if b.name == MAIN or (b.ahead_of_main == 0 and not show_all):
            continue
        moved = sorted(s for (u, s), j in joined.items() if b.name in j.moved)
        row = [b.name, b.day, str(b.ahead_of_main), b.drift, b.worktree, ", ".join(moved) or "no mark"]
        if measure:
            row.append(share_on_main(repo.root, b.tip))
        branch_rows.append(row)
    headers = ["Branch", "Tip", "Ahead of main", "Upstream", "Worktree", "Moves"] + (["On main by content"] if measure else [])
    lines += table(headers, branch_rows)
    return "\n".join(lines) + "\n"


def region_text(repo: Repo) -> str:
    """INDEX.md's generated region: the Units and Work tables from the working tree. Links are
    relative to the developer area, and every row is deterministic in the records' order."""
    units = units_here(repo)
    root = repo.root
    lines = ["## Units", "", "Every unit with a status record, its state from the record's Status line, and its documents where they exist.", ""]
    unit_rows = []
    for name, unit in units.items():
        docs = []
        for label, rel in (("plan", f"plans/{name}.md"), ("status", f"status/{name}.md"), ("review", f"review/{name}-review.md")):
            if (root / repo.developer / rel).exists():
                docs.append(f"[{label}]({rel})")
        packs = sorted(p.name for prefix in unit.prefix.replace(" ", "").split(",") if prefix
                       for p in (root / repo.developer / "validation").glob(f"{prefix}-*.md"))
        if packs:
            docs.append(f"{len(packs)} Validation Packs")
        unit_rows.append((name, unit.kind, unit.prefix, f"{unit.state or '?'} {unit.day}".strip() or "?", unit.next, ", ".join(docs)))
    lines += table(("ID", "Kind", "Prefix", "State", "Next", "Documents"), unit_rows)
    lines += ["", "## Work", "", "Every slice on a board, keyed by its id, with the record and section it was read from.", ""]
    work_rows = []
    for name, unit in units.items():
        for row in (unit.board.rows if unit.board else ()):
            work_rows.append((row.id, plain(row.deliverable, 190) or row.id, name, state_text(row), plain(row.blocked_on),
                              f"{(repo.status / name).as_posix()}.md{unit.board.anchor}"))
    lines += table(("ID", "Claim", "Unit", "State", "Blocked on", "Pointer"), work_rows)
    return "\n".join(lines) + "\n"


def render_index(existing: str, region: str) -> str:
    body = f"{REGION_BEGIN}\n\n{region}\n{REGION_END}"
    if REGION_BEGIN in existing and REGION_END in existing:
        head, _, rest = existing.partition(REGION_BEGIN)
        _, _, tail = rest.partition(REGION_END)
        return head + body + tail
    return existing.rstrip("\n") + "\n\n" + body + "\n"


def build(repo: Repo, check: bool) -> int:
    path = repo.root / repo.index
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    wanted = render_index(existing, region_text(repo))
    if wanted == existing:
        return 0
    if check:
        print(f"{repo.index.as_posix()}: the work-board region is stale against the status records. Run `mise run build:work`")
        return 1
    path.write_text(wanted, encoding="utf-8")
    return 0


# ---- the roadmap ---------------------------------------------------------------------------------

GANTT_THEME = ('%%{init: {"themeVariables": {"taskBkgColor": "#f2c14e", "taskBorderColor": "#b8860b", "taskTextColor": "#000000", '
               '"activeTaskBkgColor": "#4e9af1", "activeTaskBorderColor": "#1f5fbf", "activeTaskBorderColor": "#1f5fbf", '
               '"doneTaskBkgColor": "#8fcf8f", "doneTaskBorderColor": "#2f7d32", "critBkgColor": "#f28b82", "critBorderColor": "#b23a30", '
               '"taskTextDarkColor": "#000000", "taskTextLightColor": "#000000"}}}%%')
GANTT_KEY = ["```mermaid", "flowchart LR",
             '    K1["building"]:::active --- K2["built or verified"]:::open --- K3["merged or tagged"]:::done --- K4["blocked"]:::crit',
             "    classDef active fill:#4e9af1,stroke:#1f5fbf,color:#000", "    classDef open fill:#f2c14e,stroke:#b8860b,color:#000",
             "    classDef done fill:#8fcf8f,stroke:#2f7d32,color:#000", "    classDef crit fill:#f28b82,stroke:#b23a30,color:#000", "```"]


def gantt_text(joined: dict[tuple[str, str], Joined], title: str, names: Optional[Iterable[str]] = None,
               completed: bool = False) -> list[str]:
    """One bar per dated slice of the named units, from the earliest day in its trail to the latest,
    a section per unit, coloured by state as the key says. The chart runs from the first day any of
    its slices has, so an epic's chart goes back to its first commit. With ``completed`` only
    merged, tagged or dropped slices are drawn. An undated slice is never drawn, since a bar
    invented for it would be a plan nobody made. Nothing is returned where nothing is dated."""
    import datetime
    wanted = set(names) if names is not None else None
    by_unit: dict[str, list[str]] = {}
    for (unit, slice_id), j in joined.items():
        if wanted is not None and unit not in wanted:
            continue
        _, row = j.winner
        days = sorted(d for _, d in row.trail if d)
        if not days or row.state is None:
            continue
        closed = row.state in ("merged", "tagged", "dropped")
        if completed and not closed:
            continue
        tag = "done" if closed else "crit" if row.state == "blocked" else "active" if row.state == "building" else ""
        start, end = days[0], days[-1]
        if start == end:
            end = (datetime.date.fromisoformat(end) + datetime.timedelta(days=1)).isoformat()
        label = re.sub(r"\s+", " ", re.sub(r"[^A-Za-z0-9 .-]", " ", re.sub(r"'s\b", "", f"{slice_id} {row.deliverable[:30]}"))).strip()
        ident = re.sub(r"[^a-z0-9]", "", slice_id.lower()) or "s"
        by_unit.setdefault(unit, []).append(f"    {label} :{tag + ', ' if tag else ''}{ident}, {start}, {end}")
    if not by_unit:
        return []
    lines = ["```mermaid", GANTT_THEME, "gantt", f"    title {title}", "    dateFormat YYYY-MM-DD", "    axisFormat %d %b"]
    for unit, bars in sorted(by_unit.items()):
        lines.append(f"    section {unit}")
        lines += bars
    lines.append("```")
    return lines


def chart_groups(units: dict[str, Unit], joined: dict[tuple[str, str], Joined], names: Iterable[str]) -> list[tuple[str, list[str]]]:
    """How the units share charts: an epic with every unit named after it, a unit outside an epic
    with SIZEABLE dated slices or more on its own, and the rest together as the smaller units."""
    names = list(names)
    dated = {n: sum(1 for (u, _), j in joined.items() if u == n and any(d for _, d in j.winner[1].trail)) for n in names}
    epics = sorted((n for n in names if units[n].kind.startswith("epic")), key=len, reverse=True)
    owned: dict[Optional[str], list[str]] = {}
    for n in names:
        parent = next((e for e in epics if n == e or n.startswith(e + "-")), None)
        owned.setdefault(parent, []).append(n)
    groups: list[tuple[str, list[str]]] = [(f"the {e} epic", owned[e]) for e in sorted(epics) if e in owned]
    small: list[str] = []
    for n in owned.get(None, []):
        if dated[n] >= SIZEABLE:
            groups.append((n, [n]))
        else:
            small.append(n)
    if small:
        groups.append(("the smaller units", small))
    return groups


def charts_text(units: dict[str, Unit], joined: dict[tuple[str, str], Joined], names: Iterable[str], completed: bool = False) -> list[str]:
    """The key once, then one chart per group, each from its first day. A group with nothing dated draws nothing."""
    lines: list[str] = list(GANTT_KEY)
    for title, members in chart_groups(units, joined, names):
        chart = gantt_text(joined, title.capitalize() if title[0].islower() else title, members, completed)
        if chart:
            lines += [""] + chart
    return lines


def roadmap_regions(repo: Repo) -> dict[str, str]:
    """The two regions ROADMAP.md carries: the programme at a glance (units and the gantt) and the
    branches, both from every branch, dated by the newest day any board holds."""
    found = branches(repo.root)
    boards = {b.name: units_at(repo, b.tip) for b in found}
    joined = join(boards)
    main_units = boards.get(MAIN, {})
    newest = max((d for j in joined.values() for r in j.rows.values() for _, d in r.trail if d), default="")
    glance = [f"Built from the status records on {len(found)} branches, the newest board day {newest or 'unknown'}.", ""]
    unit_rows = []
    done_rows = []
    open_units: list[str] = []
    done_units: list[str] = []
    for name, unit in main_units.items():
        slices = [j for (u, _), j in joined.items() if u == name]
        if unit.state in ("merged", "tagged", "dropped") and not any(j.moved for j in slices):
            last = max((d for j in slices for _, d in j.winner[1].trail if d), default=unit.day)
            done_rows.append((f"[{name}](plans/{name}.md)" if (repo.root / repo.plans / f"{name}.md").exists() else name,
                              unit.kind, f"{unit.state} {unit.day}".strip(), str(len(slices)), last))
            done_units.append(name)
            continue
        open_units.append(name)
        counts = {}
        for j in slices:
            counts[j.winner[1].state or "?"] = counts.get(j.winner[1].state or "?", 0) + 1
        summary = ", ".join(f"{n} {st}" for st, n in sorted(counts.items(), key=lambda kv: -kv[1])) or "no board"
        on = sorted({b for j in slices for b in j.moved})
        unit_rows.append((f"[{name}](plans/{name}.md)" if (repo.root / repo.plans / f"{name}.md").exists() else name,
                          unit.kind, f"{unit.state or '?'} {unit.day}".strip(), unit.next, summary, ", ".join(on)))
    glance += table(("Unit", "Kind", "State", "Next", "Slices", "Moved on"), unit_rows)
    glance += ["", "One chart per epic, or per unit outside an epic with five dated slices or more, from the first day it has to the newest, every dated slice in the state its board gives.", ""]
    glance += charts_text(main_units, joined, open_units)
    completed = ["Every unit whose Status line reads merged, tagged or dropped and that no branch moves, with its slices, and a chart per group of their merged, tagged or dropped slices with a day, whatever its age.", ""]
    completed += table(("Unit", "Kind", "State", "Slices", "Last day"), done_rows)
    completed += [""] + charts_text(main_units, joined, done_units, completed=True)
    branch_rows = []
    for b in found:
        if b.name == MAIN or b.ahead_of_main == 0:
            continue
        moved = sorted(s for (u, s), j in joined.items() if b.name in j.moved)
        branch_rows.append((f"`{b.name}`", b.day, str(b.ahead_of_main), b.drift, ", ".join(moved) or "no mark"))
    branches_text = [f"Branches with a commit `main` lacks, from the same reading.", ""]
    branches_text += table(("Branch", "Tip", "Ahead of main", "Upstream", "Moves"), branch_rows)
    return {"glance": "\n".join(glance) + "\n", "branches": "\n".join(branches_text) + "\n",
            "completed": "\n".join(completed) + "\n", "decisions": decisions_text(repo)}


def decisions_text(repo: Repo) -> str:
    """What waits on the maintainer, read from the registers in the working tree: the Proposed decisions
    from the catalogue, the pending design decisions, the open debt, and the slices named only in prose."""
    root = repo.root
    catalogue = root / repo.architecture / "decisions" / "README.md" if repo.architecture else None
    proposed = []
    if catalogue and catalogue.exists():
        for line in catalogue.read_text(encoding="utf-8").splitlines():
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) >= 3 and cells[0].startswith("[") and cells[-1].lower().startswith("proposed"):
                # The catalogue's links are relative to its own folder, and this region lives in the developer area.
                link = cells[0].replace("](", f"]({(Path('..') / repo.architecture.relative_to(repo.architecture.parent) / 'decisions').as_posix()}/")
                proposed.append((link, plain(cells[1], 90), cells[-1]))
    def rows_of(name: str) -> int:
        path = root / repo.developer / name
        return sum(1 for l in path.read_text(encoding="utf-8").splitlines() if re.match(r"^\| [A-Z]+-\d+ \|", l)) if path.exists() else 0
    prose_only = 0
    for path in repo.exceptions:
        if path.exists() and "# unit " in path.read_text(encoding="utf-8"):
            prose_only = sum(1 for l in path.read_text(encoding="utf-8").split("# Slices a plan names", 1)[-1].splitlines()
                             if l.strip() and not l.startswith("#"))
    def register_rows(name: str) -> list[tuple[str, str]]:
        path = root / repo.developer / name
        out = []
        for line in (path.read_text(encoding="utf-8").splitlines() if path.exists() else []):
            m = re.match(r"^\| ([A-Z]+-\d+) \| (.*)$", line)
            if m:
                cells = [c.strip() for c in m.group(2).split("|")]
                bold = re.match(r"\*\*(.+?)\*\*", cells[0])
                out.append((m.group(1), plain(bold.group(1) if bold else cells[0], 160)))
        return out
    pending = register_rows("pending-design-decisions.md")
    debt = rows_of("technical-debt.md")
    lines = [f"Read from the registers in this tree: {len(proposed)} Proposed decisions, {len(pending)} pending design decisions, {debt} rows of [technical debt](technical-debt.md), and {prose_only} slices named only in prose, listed by unit in the identifier exceptions baseline.",
             "", "### 9.1 Proposed decisions", ""]
    lines += table(("Decision", "Subject", "Status"), proposed)
    lines += ["", "### 9.2 Pending design decisions", "", "Every row of [pending-design-decisions.md](pending-design-decisions.md), which loses a row when a sketch, plan or ADR settles it.", ""]
    lines += table(("Decision", "Question"), pending)
    return "\n".join(lines) + "\n"


def render_regions(existing: str, regions: dict[str, str]) -> str:
    out = existing
    for name, body in regions.items():
        begin, end = ROADMAP_BEGIN.format(name=name), ROADMAP_END.format(name=name)
        block = f"{begin}\n\n{body}\n{end}"
        if begin in out and end in out:
            head, _, rest = out.partition(begin)
            _, _, tail = rest.partition(end)
            out = head + block + tail
        else:
            out = out.rstrip("\n") + "\n\n" + block + "\n"
    return out


def build_roadmap(repo: Repo, check: bool) -> int:
    path = repo.root / repo.roadmap
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    wanted = render_regions(existing, roadmap_regions(repo))
    if wanted == existing:
        return 0
    if check:
        print(f"{repo.roadmap.as_posix()}: the work-board regions are stale. Run `mise run build:roadmap`")
        return 1
    path.write_text(wanted, encoding="utf-8")
    return 0


# ---- presence ------------------------------------------------------------------------------------

PRESENCE_DIR = Path(".local") / "agents"
PRESENCE_HOURS = 12
ROLES = ("build", "review", "read")


def session_from_environment(environ: dict[str, str]) -> tuple[str, str]:
    """(session, client) as the client exposes them. Claude Code sets CLAUDE_CODE_SESSION_ID and
    AI_AGENT in every command it runs. Another client is read the same way when it names them."""
    session = environ.get("CLAUDE_CODE_SESSION_ID") or environ.get("AGENT_SESSION_ID") or ""
    client = environ.get("AI_AGENT") or environ.get("CLAUDE_CODE_ENTRYPOINT") or ""
    return session, client


def write_presence(root: Path, session: str, client: str, model: str, role: str, on: Sequence[str], now: str) -> Path:
    """Write or refresh this session's presence file (plan work-board, WB-6). The file's modification
    time is the fact the listing compares, so a later run with the same arguments touches it."""
    if role not in ROLES:
        raise ValueError(f"role is one of {', '.join(ROLES)}, not {role!r}")
    directory = root / PRESENCE_DIR
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{session or 'unnamed'}.toml"
    since = now
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.startswith("since = "):
                since = line.split("=", 1)[1].strip().strip('"')
    slices = ", ".join(f'"{s}"' for s in on)
    path.write_text(f'session = "{session}"\nclient = "{client}"\nmodel = "{model}"\nrole = "{role}"\n'
                    f'on = [{slices}]\nsince = "{since}"\n', encoding="utf-8")
    os_utime = __import__("os").utime
    os_utime(path, None)
    return path


def list_presence(root: Path, now_epoch: float) -> list[dict[str, str]]:
    """Every session whose file was touched within PRESENCE_HOURS of ``now_epoch``, oldest first. A
    crashed session ages out, a left one is gone, and no lock is ever held."""
    import tomllib
    directory = root / PRESENCE_DIR
    found: list[dict[str, str]] = []
    for path in sorted(directory.glob("*.toml")) if directory.is_dir() else []:
        age = max(0.0, now_epoch - path.stat().st_mtime)
        if age > PRESENCE_HOURS * 3600:
            continue
        data = tomllib.loads(path.read_text(encoding="utf-8"))
        found.append({"session": str(data.get("session", path.stem)), "client": str(data.get("client", "")),
                      "model": str(data.get("model", "")), "role": str(data.get("role", "")),
                      "on": ", ".join(data.get("on", [])), "since": str(data.get("since", "")),
                      "touched": f"{int(age // 60)} min ago"})
    return found


def leave_presence(root: Path, session: str) -> bool:
    path = root / PRESENCE_DIR / f"{session or 'unnamed'}.toml"
    if path.exists():
        path.unlink()
        return True
    return False


def presence_text(found: list[dict[str, str]], me: str) -> str:
    if not found:
        return "nobody here. Run `mise run work:here -- --role build|review|read --model <model>` before your first edit.\n"
    rows = [(("you " if f["session"] == me else "") + f["session"][:8], f["client"], f["model"], f["role"], f["on"], f["since"], f["touched"]) for f in found]
    lines = table(("Session", "Client", "Model", "Role", "On", "Since", "Touched"), rows)
    builders = [f for f in found if f["role"] == "build" and f["session"] != me]
    if builders:
        lines.append("")
        lines.append("another session is building here. Say who is here and ask the maintainer before writing.")
    return "\n".join(lines) + "\n"


# ---- entry ---------------------------------------------------------------------------------------

def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--root", type=Path, help="the repository root, found through the catalogue by default")
    sub = parser.add_subparsers(dest="command", required=True)
    board = sub.add_parser("board", help="the live board across every branch")
    board.add_argument("--all", action="store_true", help="every row, not only what differs from main")
    board.add_argument("--fetch", action="store_true", help="fetch every remote first")
    board.add_argument("--measure", action="store_true", help="add each branch's content share on main, the slow part")
    board.add_argument("--commits", action="store_true", help="add the commit that set each printed row")
    built = sub.add_parser("build", help="write INDEX.md's generated region from the working tree")
    built.add_argument("--check", action="store_true", help="fail if the region is stale, write nothing")
    road = sub.add_parser("roadmap", help="write ROADMAP.md's generated regions from every branch")
    road.add_argument("--check", action="store_true")
    road.add_argument("--fetch", action="store_true")
    here = sub.add_parser("here", help="who is in this worktree: write your presence, or list the live sessions")
    here.add_argument("--role", choices=ROLES, help="write your presence with this role")
    here.add_argument("--model", default="", help="the model you run on, stated by hand since no client names it")
    here.add_argument("--on", default="", help="the slices you are on, comma separated")
    here.add_argument("--leave", action="store_true", help="remove your presence")
    here.add_argument("--now", default="", help="the clock, as an ISO timestamp, for tests. The wall clock otherwise")
    parsed = sub.add_parser("parse", help="print a status record's board as read")
    parsed.add_argument("record", type=Path)
    args = parser.parse_args(argv)
    repo = Repo.here(args.root)
    if args.command == "board":
        if args.fetch:
            git(repo.root, "fetch", "--all", "--prune", "--quiet", check=False)
        sys.stdout.write(board_text(repo, args.all, args.measure, args.commits))
        return 0
    if args.command == "build":
        return build(repo, args.check)
    if args.command == "roadmap":
        if args.fetch:
            git(repo.root, "fetch", "--all", "--prune", "--quiet", check=False)
        return build_roadmap(repo, args.check)
    if args.command == "here":
        import datetime
        import os
        session, client = session_from_environment(dict(os.environ))
        now = datetime.datetime.fromisoformat(args.now) if args.now else datetime.datetime.now(datetime.timezone.utc)
        if now.tzinfo is None:
            now = now.replace(tzinfo=datetime.timezone.utc)
        if args.leave:
            print("left" if leave_presence(repo.root, session) else "no presence to leave")
            return 0
        if args.role:
            write_presence(repo.root, session, client, args.model, args.role,
                           [s.strip() for s in args.on.split(",") if s.strip()], now.strftime("%Y-%m-%dT%H:%M:%SZ"))
        sys.stdout.write(presence_text(list_presence(repo.root, now.timestamp()), session))
        return 0
    unit = parse_unit(args.record.stem, args.record.read_text(encoding="utf-8"))
    if not unit.board:
        print(f"{args.record}: no board. Unit state {unit.state or '?'} {unit.day}".strip())
        return 0
    print("\n".join(table(("Slice", "State", "Day", "Trail", "Blocked on"),
                          ((r.id, r.state or "?", r.day, ", ".join(f"{s} {d}".strip() for s, d in r.trail), r.blocked_on)
                           for r in unit.board.rows))))
    return 0


if __name__ == "__main__":
    sys.exit(main())
