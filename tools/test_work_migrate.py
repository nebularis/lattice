# SPDX-License-Identifier: MPL-2.0
"""Tests of the work board migration tool (tools/work_migrate.py). Each runs git in a temporary repository."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))
import work_board as wb  # noqa: E402
import work_migrate as wm  # noqa: E402

DEV = Path("docs/developer")
CCS = "computable-contract-substrate"
DAY = re.compile(r"\d{4}-\d{2}-\d{2}")
OLD_RECORD = """# Computable contract substrate: status

**Branch:** `x`
**Status:** 🔨 In progress

## Position

| # | Slice | Tranche | State | Blocked on |
|---|---|---|---|---|
| C3 | Wording spec, vocab and shapes | B | merged, tagged | |
| C9b3, C9b4 | set comparisons | D | waiting | C9b2 |
| C12 | evaluator | D | not started | nothing |
"""
BOARD = """# Computable contract substrate: status

**Unit ID:** `computable-contract-substrate`
**Status:** blocked. C9b3 next. See validation/computable-contract-substrate-c10a.md.

| Slice | Deliverable | State | Blocked on |
|---|---|---|---|
| C3 | Wording | merged 2026-10-01 | |
| C9b3 | set comparisons | blocked | C9b2 |
| C9b4 | more comparisons | blocked | C9b2 |
| C12 | evaluator | planned | |
| F1 | a fix | planned | |
| HQ-6a.1 | already new | planned | |
"""
PLAN = "# CCS plan\n\nSlice C9b3 builds sets. See C9b3-Q1. The CCS C12 slice.\n"
OTHER = "Other notes: C12 stays, C9b3 moves.\n"
PACK = "# Pack\n\nA Validation Pack.\n"


def sh(cwd: Path, *args: str) -> str:
    return subprocess.run(list(args), cwd=cwd, capture_output=True, text=True, check=True).stdout.strip()


def make_repo(tmp_path: Path, files: dict[str, str]) -> wb.Repo:
    """A repository with the given files (relative to docs/developer) committed on main."""
    root = tmp_path / "work"
    root.mkdir()
    sh(root, "git", "init", "-q", "-b", "main")
    sh(root, "git", "config", "user.email", "test@example.org")
    sh(root, "git", "config", "user.name", "Test")
    sh(root, "git", "config", "commit.gpgsign", "false")
    for sub in ("status", "plans", "validation", "notes", "sketches"):
        (root / DEV / sub).mkdir(parents=True)
        (root / DEV / sub / ".keep").write_text("", encoding="utf-8")
    for rel, text in files.items():
        (root / DEV / rel).write_text(text, encoding="utf-8")
    sh(root, "git", "add", ".")
    sh(root, "git", "commit", "-q", "--no-verify", "-m", "seed")
    return wb.Repo(root, DEV)


def rule(unit: str) -> wm.Rule:
    return next(r for r in wm.RULES if r.unit == unit)


def read(repo: wb.Repo, rel: str) -> str:
    return (repo.root / DEV / rel).read_text(encoding="utf-8")


@pytest.fixture
def ccs(tmp_path: Path) -> wb.Repo:
    return make_repo(tmp_path, {f"status/{CCS}.md": BOARD, f"plans/{CCS}.md": PLAN, "sketches/other.md": OTHER,
                                f"validation/{CCS}-c10a.md": PACK})


def test_wb2_01_crossed_joins_digit_groups_with_dots() -> None:
    assert wm.crossed("CCS", "9b3b") == "CCS-9b.3b"
    assert wm.crossed("FMH", "2.6d") == "FMH-2.6d"
    assert wm.crossed("PLT", "0.1.1") == "PLT-0.1.1"
    assert wm.crossed("FM", "D0") == "FM-D0"
    assert wm.crossed("LG", "1-05b") == "LG-1.05b"


def test_wb2_02_cross_reads_a_historic_id_by_the_unit_rule() -> None:
    r = rule(CCS)
    assert wm.cross(r, "C9b3b") == "CCS-9b.3b"
    assert wm.cross(r, "C10a") == "CCS-10a"
    assert wm.cross(r, "F1") == "CCS-F1"
    assert wm.cross(r, "HQ-6a.1") == "HQ-6a.1"
    assert wm.cross(r, "AIR-3.3") == "AIR-3.3"
    assert wm.cross(r, "garbage") is None
    h = rule("formal-methods-track-h")
    assert wm.cross(h, "H2.6d") == "FMH-2.6d"
    assert wm.cross(h, "HO0") == "FMH-HO0"
    assert wm.cross(h, "H10") == "FMH-10"


def test_wb2_03_pack_target_reads_a_pack_stem() -> None:
    assert wm.pack_target(rule("formal-methods-track-h"), "FMH-H1-2b") == "FMH-1.2b"
    assert wm.pack_target(rule("formal-methods-track-h"), "FMH-HO0") == "FMH-HO0"
    assert wm.pack_target(rule(CCS), "computable-contract-substrate-c10a") == "CCS-10a"
    assert wm.pack_target(rule("applied-ontology-readiness"), "applied-ontology-readiness-aor-12") == "AOR-12"
    assert wm.pack_target(rule(CCS), "something-else") is None


def test_wb2_04_map_state_maps_the_historic_words() -> None:
    assert wm.map_state("Done (`6b2a577`)", "")[:2] == ("built", "")
    assert wm.map_state("**done**, 2026-10-09", "")[:2] == ("built", "2026-10-09")
    assert wm.map_state("**signed off** 2026-10-10, merged.", "")[0] == "merged"
    assert wm.map_state("merged (`5da9412`), tagged", "")[0] == "tagged"
    assert wm.map_state("not started, outline only", "")[:2] == ("planned", "")
    assert wm.map_state("waiting", "AIR-3.3")[0] == "blocked"
    assert wm.map_state("waiting", "nothing")[0] == "planned"
    assert wm.map_state("retired from this track", "")[0] == "dropped"
    assert wm.map_state("✅ Complete — see VP", "")[0] == "built"
    assert wm.map_state("built 2026-10-27, more", "") is None
    assert wm.map_state("zzz nothing known", "") is None


def test_wb2_05_split_ids_reads_lists_ranges_and_prose() -> None:
    assert wm.split_ids("AOR-10, AOR-11") == ["AOR-10", "AOR-11"]
    assert wm.split_ids("AOR-2 to AOR-4") == ["AOR-2", "AOR-3", "AOR-4"]
    assert wm.split_ids("PF1/PF4") == ["PF1", "PF4"]
    assert wm.split_ids("B2.1 (harden the differential harness, seed a fault)") == ["B2.1"]
    assert wm.split_ids("H1.1 (prefix antichain and overlap check)") == ["H1.1"]
    assert wm.split_ids("C9b3") == ["C9b3"]
    assert wm.split_ids("1. Core patterns") == ["1."]


def test_wb2_06_pattern_for_matches_a_whole_id_and_distinctive_tells_prose_from_ids() -> None:
    pattern = wm.pattern_for("C9b3b")
    assert pattern.search("slice C9b3b, built") and pattern.search("`C9b3b`")
    for text in ("C9b3b-Q1", "C9b3b-01", "ADR-A-C9b3b", "C9b3bx", "x/C9b3b"):
        assert not pattern.search(text), text
    for old in ("AIR-3.3", "C9b3b", "H2.6d", "DOC1", "HO0"):
        assert wm.distinctive(old), old
    for old in ("C2", "B1", "D0", "M0"):
        assert not wm.distinctive(old), old


def test_wb2_07_normalise_record_puts_an_old_board_on_the_standard_shape(tmp_path: Path) -> None:
    repo = make_repo(tmp_path, {f"status/{CCS}.md": OLD_RECORD})
    path = repo.root / DEV / f"status/{CCS}.md"
    text, notes = wm.normalise_record(repo, path)
    assert "**Branch:**" not in text and f"**Unit ID:** `{CCS}`" in text
    assert "| Slice | Deliverable | State | Blocked on | Tranche |" in text
    unit = wb.parse_unit(CCS, text)
    rows = {r.id: r for r in unit.board.rows}
    assert list(rows) == ["C3", "C9b3", "C9b4", "C12"]
    assert all(r.state is not None for r in rows.values())
    for rid in ("C9b3", "C9b4"):
        assert (rows[rid].state, rows[rid].blocked_on) == ("blocked", "C9b2")
    assert (rows["C12"].state, rows["C12"].blocked_on) == ("planned", "")
    assert re.fullmatch(r"merged \d{4}-\d{2}-\d{2}, tagged", rows["C3"].raw)
    assert unit.state is not None
    assert notes == []


def test_wb2_08_normalise_record_is_idempotent(tmp_path: Path) -> None:
    repo = make_repo(tmp_path, {f"status/{CCS}.md": OLD_RECORD, "status/foo.md": "# T\n\n**Status:** Underway, nothing.\n"})
    path = repo.root / DEV / f"status/{CCS}.md"
    first, _ = wm.normalise_record(repo, path)
    path.write_text(first, encoding="utf-8")
    second, notes = wm.normalise_record(repo, path)
    assert second == first and notes == []
    foo, notes = wm.normalise_record(repo, repo.root / DEV / "status/foo.md")
    assert foo == "# T\n\n**Unit ID:** `foo`\n\n**Status:** Underway, nothing.\n"
    assert len(notes) == 1 and "no board" in notes[0]


def test_wb2_09_normalise_reports_then_writes_and_declares_the_prefix(tmp_path: Path) -> None:
    plan = f"# CCS plan\n\n**Unit ID:** `{CCS}`\n**Unit type:** multi-slice unit\n"
    repo = make_repo(tmp_path, {f"status/{CCS}.md": OLD_RECORD, f"plans/{CCS}.md": plan})
    before = {rel: read(repo, rel) for rel in (f"status/{CCS}.md", f"plans/{CCS}.md")}
    report = wm.normalise(repo, apply=False)
    assert report[-1].endswith("would change") and not report[-1].endswith(": 0 would change")
    assert before == {rel: read(repo, rel) for rel in before}
    assert any("Prefix CCS, HQ" in line for line in report)
    wm.normalise(repo, apply=True)
    lines = read(repo, f"plans/{CCS}.md").splitlines()
    assert lines[lines.index(f"**Unit ID:** `{CCS}`") + 1] == "**Prefix:** CCS, HQ"
    assert "**Branch:**" not in read(repo, f"status/{CCS}.md")
    again = wm.normalise(repo, apply=True)
    assert again == ["records and plans: 0 rewritten"]


def test_wb2_10_crosswalk_lists_the_historic_ids_of_a_board(ccs: wb.Repo) -> None:
    crossings = wm.crosswalk(ccs)
    assert [(c.old, c.new) for c in crossings] == [
        ("C12", "CCS-12"), ("C3", "CCS-3"), ("C9b3", "CCS-9b.3"), ("C9b4", "CCS-9b.4"), ("F1", "CCS-F1")]
    assert {c.unit for c in crossings} == {CCS}


def test_wb2_11_rename_sweeps_mentions_moves_packs_and_writes_the_crosswalk(ccs: wb.Repo) -> None:
    report = wm.rename(ccs, apply=True)
    record, plan = read(ccs, f"status/{CCS}.md"), read(ccs, f"plans/{CCS}.md")
    assert "| CCS-3 | Wording |" in record and "| CCS-9b.3 |" in record and "| HQ-6a.1 |" in record
    assert "Slice CCS-9b.3 builds sets" in plan and "C9b3-Q1" in plan
    assert "The CCS-12 slice" in plan and "CCS CCS-12" not in plan
    other = read(ccs, "sketches/other.md")
    assert "C12 stays" in other and "CCS-9b.3 moves" in other
    packs = ccs.root / DEV / "validation"
    assert (packs / "CCS-10a.md").exists() and not (packs / f"{CCS}-c10a.md").exists()
    assert "R " in sh(ccs.root, "git", "status", "--porcelain") or "CCS-10a.md" in sh(ccs.root, "git", "status", "--porcelain")
    assert "validation/CCS-10a.md" in record and f"validation/{CCS}-c10a.md" not in record
    crosswalk = read(ccs, "notes/slice-crosswalk-2026-11.md")
    assert "| Was | Is | Unit |" in crosswalk
    assert f"| C9b3 | CCS-9b.3 | {CCS} |" in crosswalk
    assert any("validation packs: 1 renamed" in line for line in report)
    assert wm.rename(ccs, apply=False)[1] == "mentions: 0 files would change"


def test_wb2_12_two_units_claiming_one_old_id_keep_it_outside_their_own_records(tmp_path: Path) -> None:
    fmc = "# FMC\n\n**Unit ID:** `formal-methods-track-c`\n**Status:** planned. C2 next.\n\n" \
          "| Slice | Deliverable | State | Blocked on |\n|---|---|---|---|\n| C2 | a thing | planned | |\n"
    ccs = BOARD.split("| Slice")[0] + "| Slice | Deliverable | State | Blocked on |\n|---|---|---|---|\n| C2 | a thing | planned | |\n"
    repo = make_repo(tmp_path, {"status/formal-methods-track-c.md": fmc, f"status/{CCS}.md": ccs,
                                "sketches/x.md": "Prose about C2 here.\n"})
    report = wm.rename(repo, apply=True)
    assert any("claimed by two units" in line and "C2" in line for line in report)
    assert "| FMC-2 |" in read(repo, "status/formal-methods-track-c.md")
    assert "| CCS-2 |" in read(repo, f"status/{CCS}.md")
    assert read(repo, "sketches/x.md") == "Prose about C2 here.\n"
