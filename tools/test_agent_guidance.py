# SPDX-License-Identifier: MPL-2.0
"""Agent guidance and the deny-terms check (ADR-A117)."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import agent_guidance  # noqa: E402
import deny_terms  # noqa: E402

ROOT = agent_guidance.ROOT


def test_the_repository_passes() -> None:
    assert agent_guidance.check(ROOT) == []


def test_copilot_links_resolve_from_github_dir() -> None:
    text = agent_guidance.render_copilot("[a](docs/x.md) [b](https://example.org/y) [c](#here)")
    assert "[a](../docs/x.md)" in text and "(https://example.org/y)" in text and "(#here)" in text


@pytest.fixture
def copy_of_guidance(tmp_path: Path) -> Path:
    for rel in ("AGENTS.md", ".github/copilot-instructions.md", ".claude-plugin/marketplace.json"):
        (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(ROOT / rel, tmp_path / rel)
    shutil.copytree(ROOT / ".claude/skills", tmp_path / ".claude/skills")
    return tmp_path


def test_drift_a_missing_skill_and_a_wrong_name_are_reported(copy_of_guidance: Path) -> None:
    root = copy_of_guidance
    (root / ".github/copilot-instructions.md").write_text("edited by hand\n")
    skill = root / ".claude/skills/lattice-design/SKILL.md"
    skill.write_text(skill.read_text().replace("name: lattice-design", "name: design"))
    (root / ".claude/skills/lattice-extra").mkdir()
    problems = "\n".join(agent_guidance.check(root))
    assert "drifted from AGENTS.md" in problems
    assert "name must be 'lattice-design'" in problems
    assert "lattice-extra: no SKILL.md" in problems
    assert "skill table lists" in problems


def test_link_replaces_its_own_links_and_refuses_others(copy_of_guidance: Path, tmp_path: Path) -> None:
    target = tmp_path / "personal"
    assert "lattice-design" in agent_guidance.link(copy_of_guidance, target, copy=False)
    assert "lattice-design" in agent_guidance.link(copy_of_guidance, target, copy=False)
    (target / "lattice-design").unlink()
    (target / "lattice-design").mkdir()
    with pytest.raises(SystemExit):
        agent_guidance.link(copy_of_guidance, target, copy=False)


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    work = tmp_path / "repo"
    work.mkdir()
    for args in (["init", "-q"], ["config", "user.email", "t@example.org"], ["config", "user.name", "t"]):
        subprocess.run(["git", *args], cwd=work, check=True)
    deny = tmp_path / "deny-terms"
    deny.write_text("# personal\nforbidden\\s+word\n!data/*.py\n")
    monkeypatch.setenv("LATTICE_DENY_TERMS", str(deny))
    return work


def stage(repo: Path, path: str, text: str) -> None:
    (repo / path).parent.mkdir(parents=True, exist_ok=True)
    (repo / path).write_text(text)
    subprocess.run(["git", "add", path], cwd=repo, check=True)


def test_a_staged_term_is_found_without_printing_it(repo: Path, capsys: pytest.CaptureFixture) -> None:
    stage(repo, "docs/a.md", "fine\nsome Forbidden  Word here\n")
    assert deny_terms.main([], cwd=repo) == 1
    out = capsys.readouterr().out
    assert "docs/a.md:2: matches deny-list entry 2" in out
    assert "orbidden" not in out


def test_skipped_paths_and_clean_changes_pass(repo: Path) -> None:
    stage(repo, "data/synthetic.py", "forbidden word\n")
    stage(repo, "docs/b.md", "nothing to see\n")
    assert deny_terms.main([], cwd=repo) == 0


def test_all_scans_committed_files(repo: Path) -> None:
    stage(repo, "docs/c.md", "forbidden word\n")
    subprocess.run(["git", "commit", "-qm", "c"], cwd=repo, check=True)
    assert deny_terms.main([], cwd=repo) == 0
    assert deny_terms.main(["--all"], cwd=repo) == 1


def test_no_list_passes(repo: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("LATTICE_DENY_TERMS", str(tmp_path / "absent"))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "empty"))
    monkeypatch.setenv("APPDATA", str(tmp_path / "empty"))
    stage(repo, "docs/d.md", "forbidden word\n")
    assert deny_terms.main([], cwd=repo) == 0


def test_the_hook_is_ours_or_refused(repo: Path) -> None:
    hook = Path(deny_terms.install_hook(repo))
    assert deny_terms.HOOK_MARK in hook.read_text()
    deny_terms.install_hook(repo)
    hook.write_text("#!/bin/sh\necho someone else's hook\n")
    with pytest.raises(SystemExit):
        deny_terms.install_hook(repo)
