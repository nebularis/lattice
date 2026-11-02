# SPDX-License-Identifier: MPL-2.0
"""Tests of the work board tool (tools/work_board.py). Each runs git in a temporary repository."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))
import work_board as wb  # noqa: E402

DEV = Path("docs/developer")
A2 = "building 2026-10-30, briefed 2026-10-27"
ALPHA = f"""# Alpha: status

**Unit ID:** `alpha`
**Status:** building 2026-10-30. Slice A-2 next.

## Position

| Slice | Deliverable | State | Blocked on |
|---|---|---|---|
| A-1 | the parser | merged 2026-10-28, verified 2026-10-27, built 2026-10-25, briefed 2026-10-20 | |
| A-2 | the join | {A2} | |
| A-3 | the tool | planned | A-2 |
"""
PLAN = "# Alpha\n\n**Unit type:** multi-slice unit, one tool\n**Prefix:** AL\n"
OLD_BOARD = """| # | Slice | Tranche | State | Blocked on |
|---|---|---|---|---|
| C9b3 | set comparisons | T1 | planned | |
| B2.1 (harden the harness) | harness | T1 | planned | |
| AOR-10, AOR-11 | the pair | T2 | planned | |
"""


def sh(cwd: Path, *args: str) -> str:
    return subprocess.run(list(args), cwd=cwd, capture_output=True, text=True, check=True).stdout.strip()


def identify(root: Path) -> None:
    sh(root, "git", "config", "user.email", "test@example.org")
    sh(root, "git", "config", "user.name", "Test")
    sh(root, "git", "config", "commit.gpgsign", "false")


def commit(root: Path, rel: str, text: str) -> str:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    sh(root, "git", "add", ".")
    sh(root, "git", "commit", "-q", "--no-verify", "-m", f"edit {rel}")
    return sh(root, "git", "rev-parse", "HEAD")


def on_branch(repo: wb.Repo, name: str, rel: str, text: str, new: bool = True) -> str:
    """Commit one file on a branch, then return to main. Returns the new tip."""
    sh(repo.root, "git", "checkout", "-q", *(["-b", name] if new else [name]))
    tip = commit(repo.root, rel, text)
    sh(repo.root, "git", "checkout", "-q", "main")
    return tip


@pytest.fixture
def repo(tmp_path: Path) -> wb.Repo:
    """A repository with main committed and pushed to a bare repository under two remote names."""
    root, bare = tmp_path / "work", tmp_path / "bare.git"
    root.mkdir()
    sh(root, "git", "init", "-q", "-b", "main")
    identify(root)
    commit(root, "README.md", "A file.\n")
    commit(root, (DEV / "status/alpha.md").as_posix(), ALPHA)
    commit(root, (DEV / "plans/alpha.md").as_posix(), PLAN)
    bare.mkdir()
    sh(bare, "git", "init", "-q", "--bare")
    sh(root, "git", "remote", "add", "origin", str(bare))
    sh(root, "git", "remote", "add", "origin-ssh", str(bare))
    sh(root, "git", "push", "-q", "origin", "main")
    sh(root, "git", "fetch", "-q", "--all")
    return wb.Repo(root, DEV)


def with_a2(state: str, drop_a3: bool = False) -> str:
    text = ALPHA.replace(A2, state)
    return text.replace("| A-3 | the tool | planned | A-2 |\n", "") if drop_a3 else text


def unit(text: str) -> dict[str, wb.Unit]:
    return {"alpha": wb.parse_unit("alpha", text)}


def section(text: str, start: str, end: str | None = None) -> str:
    tail = text.split(start)[1]
    return tail.split(end)[0] if end else tail


def cells_of(block: str, first: str) -> list[str]:
    return wb.cells(next(line for line in block.splitlines() if line.startswith(f"| {first} |")))


def test_wb1_01_parse_state_reads_the_trail() -> None:
    assert wb.parse_state("merged 2026-10-28, verified 2026-10-27, built 2026-10-25") == (
        "merged", "2026-10-28", (("merged", "2026-10-28"), ("verified", "2026-10-27"), ("built", "2026-10-25")))
    assert wb.parse_state("planned") == ("planned", "", (("planned", ""),))
    assert wb.parse_state("building 2026-10-30, and a note")[2] == (("building", "2026-10-30"),)
    assert wb.parse_state("Done (`6b2a577`)") == (None, "", ())
    assert wb.parse_state("**done**, 2026-10-09") == (None, "", ())
    state, day, trail = wb.parse_state("blocked 2026-10-01 on the review")
    assert (state, day, trail) == ("blocked", "2026-10-01", (("blocked", "2026-10-01"),))


def test_wb1_02_find_board_reads_the_standard_board() -> None:
    board = wb.find_board("alpha", ALPHA)
    lines = ALPHA.splitlines()
    assert board is not None
    assert board.line == lines.index("| Slice | Deliverable | State | Blocked on |") + 1
    assert [r.id for r in board.rows] == ["A-1", "A-2", "A-3"]
    assert [r.deliverable for r in board.rows] == ["the parser", "the join", "the tool"]
    assert [r.blocked_on for r in board.rows] == ["", "", "A-2"]
    assert [r.line for r in board.rows] == [next(i for i, l in enumerate(lines, 1) if l.startswith(f"| {r.id} |")) for r in board.rows]


def test_wb1_03_find_board_reads_the_older_board() -> None:
    board = wb.find_board("old", OLD_BOARD)
    assert board is not None
    assert [r.id for r in board.rows] == ["C9b3", "B2.1", "AOR-10"]
    assert [r.deliverable for r in board.rows] == ["set comparisons", "harness", "the pair"]


def test_wb1_04_find_board_skips_tables_without_a_state_column() -> None:
    text = "| Name | Note |\n|---|---|\n| x | y |\n\n| Slice | State |\n|---|---|\n| A-1 | planned |\n"
    board = wb.find_board("u", text)
    assert board is not None and [r.id for r in board.rows] == ["A-1"]
    assert wb.find_board("u", "# No table here\n\nJust prose.\n") is None


def test_wb1_05_parse_unit_reads_state_kind_prefix_and_next() -> None:
    u = wb.parse_unit("alpha", ALPHA, PLAN)
    assert (u.state, u.day, u.kind, u.prefix, u.next) == ("building", "2026-10-30", "multi-slice unit", "AL", "A-2")
    bare = wb.parse_unit("alpha", ALPHA)
    assert (bare.kind, bare.prefix) == ("unit", "")


def test_wb1_06_read_blobs_returns_text_exact(repo: wb.Repo) -> None:
    first, second = "café — dash\n", "second file\n"
    commit(repo.root, "docs/one.md", first)
    commit(repo.root, "docs/two.md", second)
    one, two = (sh(repo.root, "git", "rev-parse", f"HEAD:docs/{n}.md") for n in ("one", "two"))
    assert wb.read_blobs(repo.root, [one, two]) == {one: first, two: second}
    assert wb.read_blobs(repo.root, []) == {}


def test_wb1_07_units_at_reads_a_tip_without_checkout(repo: wb.Repo) -> None:
    main_tip = sh(repo.root, "git", "rev-parse", "main")
    edit_tip = on_branch(repo, "edit", (DEV / "status/alpha.md").as_posix(), with_a2("built 2026-11-01, " + A2))
    assert wb.units_at(repo, edit_tip)["alpha"].board.rows[1].state == "built"
    old = wb.units_at(repo, main_tip)["alpha"]
    assert old.board.rows[1].state == "building"
    assert (old.kind, old.prefix) == ("multi-slice unit", "AL")


def test_wb1_08_branches_fold_remotes_and_report_drift(repo: wb.Repo, tmp_path: Path) -> None:
    root = repo.root
    on_branch(repo, "loc", "n/loc.txt", "x\n")
    on_branch(repo, "ahead", "n/ahead.txt", "x\n")
    on_branch(repo, "behind", "n/behind.txt", "x\n")
    sh(root, "git", "push", "-q", "origin", "ahead", "behind")
    ahead_tip = on_branch(repo, "ahead", "n/ahead2.txt", "y\n", new=False)
    clone = tmp_path / "clone2"
    sh(tmp_path, "git", "clone", "-q", str(tmp_path / "bare.git"), str(clone))
    identify(clone)
    sh(clone, "git", "checkout", "-q", "behind")
    behind_tip = commit(clone, "n/behind2.txt", "y\n")
    sh(clone, "git", "push", "-q", "origin", "behind")
    sh(clone, "git", "checkout", "-q", "-b", "remo", "origin/main")
    commit(clone, "n/remo.txt", "z\n")
    sh(clone, "git", "push", "-q", "origin", "remo")
    sh(root, "git", "fetch", "-q", "--all")

    found = wb.branches(root)
    assert [b.name for b in found] == ["ahead", "behind", "loc", "main", "remo"]
    by = {b.name: b for b in found}
    assert by["main"].drift == "pushed" and by["main"].ahead_of_main == 0
    assert by["loc"].drift == "local only" and by["loc"].ahead_of_main == 1
    assert (by["ahead"].drift, by["ahead"].tip, by["ahead"].ahead_of_main) == ("local ahead 1, not pushed", ahead_tip, 2)
    assert (by["behind"].drift, by["behind"].tip) == ("local behind 1, not pulled", behind_tip)
    assert by["remo"].drift == "remote only" and by["remo"].ahead_of_main == 1
    assert Path(by["main"].worktree).resolve() == root.resolve()
    assert by["loc"].worktree == ""


def test_wb1_09_join_picks_winner_and_marks_stale_and_moved() -> None:
    main, b, c = (unit(with_a2(s)) for s in ("built 2026-10-25", "verified 2026-10-27", "built 2026-10-25"))
    joined = wb.join({"main": main, "b": b, "c": c})[("alpha", "A-2")]
    assert joined.winner == ("b", b["alpha"].board.rows[1])
    assert joined.stale == [] and joined.moved == ["b"]
    merged = unit(with_a2("merged 2026-10-28"))
    assert wb.join({"main": merged, "c": c})[("alpha", "A-2")].stale == ["c"]
    claim_b, claim_c = unit(with_a2("building 2026-10-30")), unit(with_a2("building 2026-11-01"))
    assert wb.join({"main": main, "b": claim_b, "c": claim_c})[("alpha", "A-2")].claims == ["b", "c"]
    no_a3 = unit(with_a2("built 2026-10-25", drop_a3=True))
    assert wb.join({"main": no_a3, "b": b})[("alpha", "A-3")].moved == ["b"]
    one, two = {"main": main, "b": b, "c": c}, {"c": c, "b": b, "main": main}
    first, second = wb.join(one), wb.join(two)
    assert list(first) == list(second)
    assert all(first[k].winner == second[k].winner for k in first)


def test_wb1_10_share_on_main_measures_content(repo: wb.Repo) -> None:
    lines = [f"line{n}" for n in range(10)]
    tip = on_branch(repo, "feat", "data.txt", "\n".join(lines) + "\n")
    commit(repo.root, "data.txt", "\n".join(lines[:5]) + "\n")
    assert wb.share_on_main(repo.root, tip) == "50% of 10"
    sh(repo.root, "git", "checkout", "-q", "-b", "empty")
    sh(repo.root, "git", "commit", "-q", "--no-verify", "--allow-empty", "-m", "nothing")
    empty = sh(repo.root, "git", "rev-parse", "HEAD")
    sh(repo.root, "git", "checkout", "-q", "main")
    assert wb.share_on_main(repo.root, empty) == "nothing added"


def test_wb1_11_render_index_replaces_only_the_region() -> None:
    appended = wb.render_index("# Index\n", "new\n")
    assert appended.startswith("# Index\n") and wb.REGION_BEGIN in appended and appended.endswith(wb.REGION_END + "\n")
    before, after = "intro\n\n", "\n\ntrailer\n"
    text = before + wb.REGION_BEGIN + "\n\nold\n\n" + wb.REGION_END + after
    out = wb.render_index(text, "new\n")
    assert out == before + wb.REGION_BEGIN + "\n\nnew\n\n" + wb.REGION_END + after
    assert wb.render_index(out, "new\n") == out
    assert wb.render_index(appended, "new\n") == appended


def test_wb1_12_build_checks_then_writes(repo: wb.Repo, capsys: pytest.CaptureFixture[str]) -> None:
    index = repo.root / repo.index
    assert wb.build(repo, check=True) == 1
    assert "mise run build:work" in capsys.readouterr().out
    assert not index.exists()
    assert wb.build(repo, check=False) == 0 and index.exists()
    assert wb.build(repo, check=True) == 0
    region = wb.region_text(repo)
    assert "| alpha | multi-slice unit | AL | building 2026-10-30 | A-2 |" in region
    lines = ALPHA.splitlines()
    for slice_id in ("A-1", "A-2", "A-3"):
        number = next(i for i, l in enumerate(lines, 1) if l.startswith(f"| {slice_id} |"))
        assert "status/alpha.md#position |" in region
    assert "| A-2 | the join | alpha | building 2026-10-30 |" in region


def test_wb1_13_board_text_shows_what_differs_from_main(repo: wb.Repo) -> None:
    record = (DEV / "status/alpha.md").as_posix()
    b_tip = on_branch(repo, "b", record, with_a2("built 2026-11-01, " + A2))
    on_branch(repo, "docs", "README.md", "Changed.\n")
    text = wb.board_text(repo, show_all=False, measure=False, commits=False)
    work = section(text, "## Work", "## Branches")
    branches = section(text, "## Branches")
    assert cells_of(work, "A-2")[4] == "b"
    assert "| A-1 |" not in work and "| A-3 |" not in work
    assert cells_of(branches, "b")[5] == "A-2"
    assert cells_of(branches, "docs")[5] == "no mark"
    everything = section(wb.board_text(repo, show_all=True, measure=False, commits=False), "## Work", "## Branches")
    assert all(f"| {s} |" in everything for s in ("A-1", "A-2", "A-3"))
    with_commits = section(wb.board_text(repo, show_all=False, measure=False, commits=True), "## Work", "## Branches")
    assert cells_of(with_commits, "A-2")[4] == f"b at {sh(repo.root, 'git', 'rev-parse', '--short', b_tip)}"


GANTT_BOARD = """**Status:** building 2026-10-30.

| Slice | Deliverable | State | Blocked on |
|---|---|---|---|
| A-1 | the parser | merged 2026-10-28, verified 2026-10-27, built 2026-10-25, briefed 2026-10-20 | |
| A-2 | the join | building 2026-10-30, briefed 2026-10-27 | |
| A-3 | the tool | planned | |
| A-4 | the gate | blocked 2026-10-29 | |
"""


def gantt(newest: str) -> list[str]:
    return wb.gantt_text(wb.join({"main": {"alpha": wb.parse_unit("alpha", GANTT_BOARD)}}), newest, "t")


def test_wb3_01_gantt_text_draws_one_bar_per_dated_slice() -> None:
    lines = gantt("2026-11-02")
    assert lines[:2] == ["```mermaid", "gantt"] and lines[-1] == "```"
    assert "    section alpha" in lines
    bars = [l for l in lines if ":done," in l or ":active," in l or ":crit," in l]
    assert len(bars) == 3
    assert any(l.endswith(":done, a1, 2026-10-20, 2026-10-28") for l in bars)
    assert any(l.endswith(":active, a2, 2026-10-27, 2026-10-30") for l in bars)
    assert any(l.endswith(":crit, a4, 2026-10-29, 2026-10-30") for l in bars)
    assert not any("A-3" in l for l in lines)


def test_wb3_02_gantt_text_leaves_out_old_merged_work() -> None:
    bars = "\n".join(gantt("2026-12-15"))
    assert " a1," not in bars and " a2," in bars


def test_wb3_03_render_regions_appends_replaces_and_is_idempotent() -> None:
    regions = {"glance": "G\n", "branches": "B\n"}
    mark = {n: (wb.ROADMAP_BEGIN.format(name=n), wb.ROADMAP_END.format(name=n)) for n in regions}
    appended = wb.render_regions("# Roadmap\n", regions)
    assert appended.startswith("# Roadmap\n") and appended.endswith(mark["branches"][1] + "\n")
    assert all(b in appended and e in appended for b, e in mark.values())
    old = "top\n\n" + mark["glance"][0] + "\n\nold\n\n" + mark["glance"][1] + "\n\nmiddle\n\n" + mark["branches"][0] + "\n\nold\n\n" + mark["branches"][1] + "\n\nend\n"
    new = wb.render_regions(old, regions)
    assert new == ("top\n\n" + mark["glance"][0] + "\n\nG\n\n" + mark["glance"][1] + "\n\nmiddle\n\n"
                   + mark["branches"][0] + "\n\nB\n\n" + mark["branches"][1] + "\n\nend\n")
    assert wb.render_regions(new, regions) == new and wb.render_regions(appended, regions) == appended


def test_wb3_04_roadmap_regions_summarise_units_and_branches(repo: wb.Repo) -> None:
    on_branch(repo, "b", (DEV / "status/alpha.md").as_posix(), with_a2("built 2026-11-01"))
    sh(repo.root, "git", "push", "-q", "origin", "b")
    regions = wb.roadmap_regions(repo)
    row = cells_of(regions["glance"], "[alpha](plans/alpha.md)")
    assert "1 built" in row[4] and row[5] == "b"
    assert "```mermaid" in regions["glance"]
    assert cells_of(regions["branches"], "`b`")[4] == "A-2"
    assert "| `main` |" not in regions["branches"]


def test_wb3_05_build_roadmap_checks_then_writes(repo: wb.Repo, capsys: pytest.CaptureFixture[str]) -> None:
    path = repo.root / repo.roadmap
    assert wb.build_roadmap(repo, check=True) == 1
    assert "mise run build:roadmap" in capsys.readouterr().out
    assert not path.exists()
    assert wb.build_roadmap(repo, check=False) == 0
    assert wb.ROADMAP_BEGIN.format(name="glance") in path.read_text(encoding="utf-8")
    assert wb.build_roadmap(repo, check=True) == 0


# ---- WB-6 presence ----------------------------------------------------------------------------

def _touch(path: Path, epoch: float) -> None:
    os.utime(path, (epoch, epoch))


def test_wb6_01_the_session_and_client_come_from_the_environment() -> None:
    assert wb.session_from_environment({"CLAUDE_CODE_SESSION_ID": "abc", "AI_AGENT": "claude-code_2-1-309_agent"}) == ("abc", "claude-code_2-1-309_agent")
    assert wb.session_from_environment({"CLAUDE_CODE_ENTRYPOINT": "cli"}) == ("", "cli")
    assert wb.session_from_environment({}) == ("", "")


def test_wb6_02_write_presence_keeps_the_first_since(tmp_path: Path) -> None:
    path = wb.write_presence(tmp_path, "abc", "client", "fable-5.1", "build", ["CCS-9b.3b"], "2026-11-02T10:00:00Z")
    assert path == tmp_path / ".local" / "agents" / "abc.toml"
    expected = {"session": "abc", "client": "client", "model": "fable-5.1", "role": "build", "on": ["CCS-9b.3b"], "since": "2026-11-02T10:00:00Z"}
    assert tomllib.loads(path.read_text(encoding="utf-8")) == expected
    wb.write_presence(tmp_path, "abc", "client", "fable-5.1", "build", ["CCS-9b.3b"], "2026-11-02T11:00:00Z")
    assert tomllib.loads(path.read_text(encoding="utf-8"))["since"] == "2026-11-02T10:00:00Z"
    with pytest.raises(ValueError):
        wb.write_presence(tmp_path, "abc", "client", "m", "boss", [], "2026-11-02T10:00:00Z")
    assert wb.write_presence(tmp_path, "", "", "", "read", [], "2026-11-02T10:00:00Z").name == "unnamed.toml"


def test_wb6_03_list_presence_ages_out_and_never_goes_negative(tmp_path: Path) -> None:
    assert wb.list_presence(tmp_path, 1_000_000.0) == []
    now_epoch = 1_000_000.0
    for name, touched in (("fresh", now_epoch - 300), ("stale", now_epoch - wb.PRESENCE_HOURS * 3600 - 60), ("future", now_epoch + 600)):
        _touch(wb.write_presence(tmp_path, name, "c", "m", "read", [], "2026-11-02T10:00:00Z"), touched)
    touched_by = {f["session"]: f["touched"] for f in wb.list_presence(tmp_path, now_epoch)}
    assert touched_by == {"fresh": "5 min ago", "future": "0 min ago"}


def test_wb6_04_leave_presence_removes_the_file(tmp_path: Path) -> None:
    path = wb.write_presence(tmp_path, "abc", "c", "m", "read", [], "2026-11-02T10:00:00Z")
    assert wb.leave_presence(tmp_path, "abc") is True
    assert not path.exists()
    assert wb.leave_presence(tmp_path, "abc") is False


def test_wb6_05_presence_text_warns_only_of_another_builder() -> None:
    def one(session: str, role: str) -> list[dict[str, str]]:
        return [{"session": session, "client": "c", "model": "m", "role": role, "on": "A-1", "since": "s", "touched": "1 min ago"}]
    empty = wb.presence_text([], "abc")
    assert "nobody here" in empty and "mise run work:here" in empty
    other = wb.presence_text(one("zzz", "build"), "abc")
    assert "| Session |" in other and "build" in other and "another session is building here" in other
    mine = wb.presence_text(one("abc", "build"), "abc")
    assert any(line.startswith("| you abc") for line in mine.splitlines())
    assert "another session is building here" not in mine
    assert "another session is building here" not in wb.presence_text(one("zzz", "review"), "abc")


def test_wb6_06_the_here_subcommand_writes_lists_and_leaves(tmp_path: Path) -> None:
    real = Path(__file__).resolve().parents[1]
    shutil.copy(real / "repository-catalogue.md", tmp_path / "repository-catalogue.md")
    for readme in (real / "ontology").glob("**/README.md"):
        target = tmp_path / readme.relative_to(real)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(readme, target)
    env = {**os.environ, "CLAUDE_CODE_SESSION_ID": "sess1"}

    def here(*args: str) -> str:
        done = subprocess.run([sys.executable, str(real / "tools" / "work_board.py"), "--root", str(tmp_path), "here", *args],
                              cwd=real, env=env, capture_output=True, text=True, check=True)
        return done.stdout
    out = here("--role", "review", "--model", "m", "--on", "A-1", "--now", "2026-11-02T10:00:00+00:00")
    assert "sess1" in out and "review" in out
    assert (tmp_path / ".local" / "agents" / "sess1.toml").exists()
    assert "left" in here("--leave")
    assert not (tmp_path / ".local" / "agents" / "sess1.toml").exists()
