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
PREFIX_RE = re.compile(r"^\*\*Prefix:\*\*\s*([A-Z]{2,5})\s*$", re.M)
SEPARATOR_RE = re.compile(r"^\|[\s:|-]*\|$")
MAIN = "main"
REGION_BEGIN = "<!-- BEGIN GENERATED work-board. Written by `mise run build:work` from the status records. Edit a status record, never this region. -->"
REGION_END = "<!-- END GENERATED work-board -->"
ROADMAP_BEGIN = "<!-- BEGIN GENERATED work-board-{name}. Written by `mise run build:roadmap` from the status records on every branch. Edit a status record, never this region. -->"
ROADMAP_END = "<!-- END GENERATED work-board-{name} -->"
RECENT_DAYS = 30


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
    for number, line in enumerate(lines, 1):
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
        return Board(unit, tuple(header), tuple(rows), number)
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
        packs = sorted(p.name for p in (root / repo.developer / "validation").glob(f"{unit.prefix}-*.md")) if unit.prefix else []
        if packs:
            docs.append(f"{len(packs)} Validation Packs")
        unit_rows.append((name, unit.kind, unit.prefix, f"{unit.state or '?'} {unit.day}".strip() or "?", unit.next, ", ".join(docs)))
    lines += table(("ID", "Kind", "Prefix", "State", "Next", "Documents"), unit_rows)
    lines += ["", "## Work", "", "Every slice on a board, keyed by its id, with the record and line it was read from.", ""]
    work_rows = []
    for name, unit in units.items():
        for row in (unit.board.rows if unit.board else ()):
            work_rows.append((row.id, plain(row.deliverable) or row.id, name, state_text(row), plain(row.blocked_on),
                              f"{(repo.status / name).as_posix()}.md:{row.line}"))
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

def gantt_text(joined: dict[tuple[str, str], Joined], newest: str, title: str) -> list[str]:
    """One bar per dated slice, from the earliest day in its trail to the latest, grouped by unit.
    Merged and tagged work older than RECENT_DAYS before the newest day on any board is left out,
    so the chart stays readable, and an undated slice is never drawn, since a bar invented for it
    would be a plan nobody made."""
    import datetime
    cutoff = (datetime.date.fromisoformat(newest) - datetime.timedelta(days=RECENT_DAYS)).isoformat() if newest else ""
    lines = ["```mermaid", "gantt", f"    title {title}", "    dateFormat YYYY-MM-DD", "    axisFormat %d %b"]
    by_unit: dict[str, list[str]] = {}
    for (unit, slice_id), j in joined.items():
        _, row = j.winner
        days = sorted(d for _, d in row.trail if d)
        if not days or row.state is None:
            continue
        if row.state in ("merged", "tagged", "dropped") and days[-1] < cutoff:
            continue
        tag = "done" if row.state in ("merged", "tagged") else "crit" if row.state == "blocked" else "active"
        start, end = days[0], days[-1]
        if start == end:
            end = (datetime.date.fromisoformat(end) + datetime.timedelta(days=1)).isoformat()
        label = re.sub(r"[^A-Za-z0-9 .-]", "", f"{slice_id} {row.deliverable[:30]}").strip()
        ident = re.sub(r"[^a-z0-9]", "", slice_id.lower()) or "s"
        by_unit.setdefault(unit, []).append(f"    {label} :{tag}, {ident}, {start}, {end}")
    for unit, bars in sorted(by_unit.items()):
        lines.append(f"    section {unit}")
        lines += bars
    lines.append("```")
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
    for name, unit in main_units.items():
        slices = [j for (u, _), j in joined.items() if u == name]
        counts = {}
        for j in slices:
            counts[j.winner[1].state or "?"] = counts.get(j.winner[1].state or "?", 0) + 1
        summary = ", ".join(f"{n} {st}" for st, n in sorted(counts.items(), key=lambda kv: -kv[1])) or "no board"
        on = sorted({b for j in slices for b in j.moved})
        unit_rows.append((f"[{name}](plans/{name}.md)" if (repo.root / repo.plans / f"{name}.md").exists() else name,
                          unit.kind, f"{unit.state or '?'} {unit.day}".strip(), unit.next, summary, ", ".join(on)))
    glance += table(("Unit", "Kind", "State", "Next", "Slices", "Moved on"), unit_rows)
    glance += [""] + gantt_text(joined, newest, f"Dated slices, newest day {newest}")
    branch_rows = []
    for b in found:
        if b.name == MAIN or b.ahead_of_main == 0:
            continue
        moved = sorted(s for (u, s), j in joined.items() if b.name in j.moved)
        branch_rows.append((f"`{b.name}`", b.day, str(b.ahead_of_main), b.drift, ", ".join(moved) or "no mark"))
    branches_text = [f"Branches with a commit `main` lacks, from the same reading.", ""]
    branches_text += table(("Branch", "Tip", "Ahead of main", "Upstream", "Moves"), branch_rows)
    return {"glance": "\n".join(glance) + "\n", "branches": "\n".join(branches_text) + "\n"}


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
