# SPDX-License-Identifier: MPL-2.0
"""Tests of the hooks dispatcher (ADR-A133). Each runs git in a temporary repository."""

from __future__ import annotations

import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))
import hooks  # noqa: E402


def sh(cwd: Path, *args: str, env: dict | None = None, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(list(args), cwd=cwd, capture_output=True, text=True, check=check, env=env)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    sh(tmp_path, "git", "init", "-q", "-b", "main")
    sh(tmp_path, "git", "config", "user.email", "test@example.org")
    sh(tmp_path, "git", "config", "user.name", "Test")
    sh(tmp_path, "git", "config", "commit.gpgsign", "false")
    (tmp_path / "tools").mkdir()
    for name in ("hooks.py", "deny_terms.py"):
        shutil.copy(TOOLS / name, tmp_path / "tools" / name)
    (tmp_path / "README.md").write_text("A file.\n")
    sh(tmp_path, "git", "add", ".")
    sh(tmp_path, "git", "commit", "-q", "--no-verify", "-m", "start")
    return tmp_path


def recorder(seen: list) -> hooks.Check:
    return hooks.Check("docs", ("docs/*",), lambda change, touched: seen.append(touched) or ["a problem"],
                       on_commit=hooks.WARN, on_merge=hooks.BLOCK)


def test_gh1_01_a_check_runs_only_on_what_it_governs(repo: Path) -> None:
    seen: list = []
    change = hooks.Change(repo, ("README.md", "docs/a.md", "docs/b/c.md"), merge=False)
    outcomes = hooks.evaluate(change, [recorder(seen)], set())
    assert seen == [["docs/a.md", "docs/b/c.md"]]
    assert [o.severity for o in outcomes] == [hooks.WARN]
    assert hooks.evaluate(hooks.Change(repo, ("README.md",), False), [recorder(seen)], set()) == []


def test_gh1_02_a_check_blocks_at_a_merge_and_warns_at_a_commit(repo: Path, capsys) -> None:
    seen: list = []
    commit = hooks.Change(repo, ("docs/a.md",), merge=False)
    merge = hooks.Change(repo, ("docs/a.md",), merge=True)
    assert hooks.report(commit, hooks.evaluate(commit, [recorder(seen)], set()), "pre-commit") == 0
    assert hooks.report(merge, hooks.evaluate(merge, [recorder(seen)], set()), "pre-commit") == 1
    assert "LATTICE_HOOKS_SKIP=docs" in capsys.readouterr().out


def test_gh1_03_skips_by_name_and_all(repo: Path) -> None:
    change = hooks.Change(repo, ("docs/a.md",), merge=True)
    assert hooks.evaluate(change, [recorder([])], {"docs"}) == []
    assert hooks.evaluate(change, [recorder([])], {"all"}) == []


def test_gh1_04_a_merge_only_check_waits_for_a_merge(repo: Path) -> None:
    gate = hooks.Check("gate", ("*",), lambda change, touched: [], merge_only=True)
    assert hooks.evaluate(hooks.Change(repo, ("x",), False), [gate], set()) == []
    assert [o.check for o in hooks.evaluate(hooks.Change(repo, ("x",), True), [gate], set())] == ["gate"]


def test_gh1_05_staged_files_and_added_lines(repo: Path) -> None:
    (repo / "README.md").write_text("A file.\nA second line.\n")
    (repo / "new.md").write_text("New.\n")
    sh(repo, "git", "add", ".")
    assert set(hooks.staged_files(repo)) == {"README.md", "new.md"}
    change = hooks.Change(repo, hooks.staged_files(repo), False)
    assert ("README.md", 2, "A second line.") in list(change.added_lines())


def branch_with_change(repo: Path) -> None:
    sh(repo, "git", "checkout", "-q", "-b", "feature")
    (repo / "f.md").write_text("Feature.\n")
    sh(repo, "git", "add", ".")
    sh(repo, "git", "commit", "-q", "--no-verify", "-m", "feature")


def test_gh1_06_a_merge_into_main_is_detected(repo: Path) -> None:
    branch_with_change(repo)
    assert not hooks.merging(repo, "pre-commit")
    assert not hooks.merging(repo, "pre-merge-commit")
    sh(repo, "git", "checkout", "-q", "main")
    assert hooks.merging(repo, "pre-merge-commit")
    assert not hooks.merging(repo, "pre-commit")
    sh(repo, "git", "merge", "-q", "--no-ff", "--no-commit", "feature")
    assert hooks.merging(repo, "pre-commit")
    assert hooks.staged_files(repo) == ("f.md",)


def test_gh1_07_a_squash_into_main_is_detected(repo: Path) -> None:
    branch_with_change(repo)
    sh(repo, "git", "checkout", "-q", "main")
    sh(repo, "git", "merge", "-q", "--squash", "feature")
    assert hooks.merging(repo, "pre-commit")


def test_gh1_08_merge_by_hand_reads_the_branch(repo: Path) -> None:
    branch_with_change(repo)
    change = hooks.Change(repo, hooks.branch_files(repo, "main"), True, "main")
    assert change.files == ("f.md",)
    assert list(change.added_lines()) == [("f.md", 1, "Feature.")]


def test_gh1_09_install_writes_every_hook(repo: Path) -> None:
    lines = hooks.install(repo)
    for name in hooks.HOOKS:
        hook = repo / ".git" / "hooks" / name
        assert hooks.HOOK_MARK in hook.read_text()
        assert hook.stat().st_mode & stat.S_IXUSR
    assert len(lines) == len(hooks.HOOKS)
    assert sh(repo, "sh", "-n", str(repo / ".git" / "hooks" / "pre-commit")).returncode == 0


def test_gh1_10_install_replaces_the_old_hook_and_refuses_a_foreign_one(repo: Path) -> None:
    directory = repo / ".git" / "hooks"
    (directory / "pre-commit").write_text("#!/bin/sh\n# lattice deny-terms hook\nexec python3 tools/deny_terms.py\n")
    (directory / "pre-merge-commit").write_text("#!/bin/sh\necho mine\n")
    with pytest.raises(SystemExit, match="was not installed by this task"):
        hooks.install(repo)
    lines = hooks.install(repo, bootstrap=True)
    assert hooks.HOOK_MARK in (directory / "pre-commit").read_text()
    assert (directory / "pre-merge-commit").read_text() == "#!/bin/sh\necho mine\n"
    assert any("was not installed by this task" in line for line in lines)


def test_gh1_11_install_under_bootstrap_outside_git(tmp_path: Path) -> None:
    assert hooks.install(tmp_path, bootstrap=True) == ["hooks: not a git checkout, no hooks installed"]


def test_gh1_12_the_installed_hook_refuses_a_denied_term(repo: Path, tmp_path_factory) -> None:
    deny = tmp_path_factory.mktemp("deny") / "deny-terms"
    deny.write_text("forbidden-word\n")
    hooks.install(repo)
    # Without mise on the path, the hook starts the dispatcher with python3, as on a bare checkout.
    path = os.pathsep.join(d for d in os.environ.get("PATH", "").split(os.pathsep)
                           if d and not (Path(d) / "mise").exists())
    env = {**os.environ, "PATH": path, "LATTICE_DENY_TERMS": str(deny)}
    env.pop("LATTICE_HOOKS_SKIP", None)
    (repo / "README.md").write_text("A forbidden-word here.\n")
    sh(repo, "git", "add", "README.md")
    refused = sh(repo, "git", "commit", "-q", "-m", "x", env=env, check=False)
    assert refused.returncode != 0
    assert "README.md:1: matches deny-list entry 1" in refused.stdout + refused.stderr
    allowed = sh(repo, "git", "commit", "-q", "-m", "x", env={**env, "LATTICE_HOOKS_SKIP": "deny-terms"}, check=False)
    assert allowed.returncode == 0, allowed.stdout + allowed.stderr


# ---- GH-2: the checks ---------------------------------------------------------------------------

ROOT = TOOLS.parent


def names_for(*files: str, merge: bool = False) -> list[str]:
    change = hooks.Change(ROOT, files, merge)
    return [c.name for c in hooks.checks() if (not c.merge_only or merge) and c.touched(change.files)]


def test_gh2_01_each_change_triggers_its_checks() -> None:
    assert names_for("tools/hooks.py") == ["deny-terms", "catalogue"]
    assert names_for("ontology/party/spec/party.ttl") == ["deny-terms", "literate", "catalogue", "import-guard"]
    assert set(names_for("ontology/party/README.md")) >= {"literate", "import-guard", "links", "formal-freshness",
                                                         "site-sections", "published-decisions"}
    assert names_for("AGENTS.md") == ["deny-terms", "agent-guidance", "links", "writing", "wrapping", "published-decisions"]
    assert "ontology-versioning" not in names_for("ontology/party/spec/party.ttl")
    assert "ontology-versioning" in names_for("ontology/party/spec/party.ttl", merge=True)
    assert names_for("package.json") == ["deny-terms"]


def test_gh2_02_links_judges_only_the_touched_files(tmp_path: Path) -> None:
    (tmp_path / "docs" / "_includes").mkdir(parents=True)
    (tmp_path / "good.md").write_text("[here](good.md)\n")
    (tmp_path / "bad.md").write_text("[gone](missing.md) and [web](https://example.org)\n")
    (tmp_path / "docs" / "_includes" / "copy.md").write_text("[gone](missing.md)\n")
    change = hooks.Change(tmp_path, ("good.md", "bad.md", "docs/_includes/copy.md"), False)
    assert hooks.links(change, list(change.files)) == ["broken link in bad.md: missing.md"]


def test_gh2_03_published_decisions_warns_on_the_touched_and_blocks_on_all_at_a_merge(monkeypatch) -> None:
    found = ["SOURCES ontology/a/README.md:3: cites ADR-A1, which is not published",
             "SOURCES ontology/b/README.md:9: cites ADR-A2, which is not published"]
    monkeypatch.setattr(hooks, "run_tool", lambda change, *args: found if "sources_check.py" in args[0] else [])
    commit = hooks.Change(ROOT, ("ontology/a/README.md",), False)
    assert hooks.published_decisions(commit, list(commit.files)) == found[:1]
    merge = hooks.Change(ROOT, ("ontology/a/README.md",), True)
    assert hooks.published_decisions(merge, list(merge.files)) == found
    check = next(c for c in hooks.checks() if c.name == "published-decisions")
    assert (check.on_commit, check.on_merge) == (hooks.WARN, hooks.BLOCK)


def test_gh2_04_literate_checks_each_touched_module_with_its_options(monkeypatch) -> None:
    calls: list = []
    monkeypatch.setattr(hooks, "run_tool", lambda change, *args: calls.append(args) or [])
    change = hooks.Change(ROOT, ("ontology/eligibility/shapes/rules.ttl", "ontology/party/README.md", "x.md"), False)
    assert hooks.literate(change, ["ontology/eligibility/shapes/rules.ttl", "ontology/party/README.md"]) == []
    layers = {args[args.index("--layer") + 1]: args for args in calls}
    assert set(layers) == {"eligibility", "party"}
    assert "--proofs-root" in layers["eligibility"] and "--proofs-root" not in layers["party"]


def test_gh2_05_literate_reports_a_disagreement(monkeypatch) -> None:
    monkeypatch.setattr(hooks, "run_tool", lambda change, *args: ["spec/party.ttl differs"])
    change = hooks.Change(ROOT, ("ontology/party/README.md",), False)
    messages = hooks.literate(change, list(change.files))
    assert messages[0].startswith("ontology/party/README.md and the files it generates disagree")
    assert "  spec/party.ttl differs" in messages


def test_gh2_06_literate_passes_on_this_checkout() -> None:
    change = hooks.Change(ROOT, ("ontology/party/README.md", "ontology/foundation/spec/foundation.ttl"), False)
    assert hooks.literate(change, list(change.files)) == []


def test_gh2_07_a_tool_that_cannot_run_warns(tmp_path: Path) -> None:
    gate = hooks.Check("absent", ("*",), lambda change, touched: hooks.run_tool(change, "tools/absent.py"))
    outcomes = hooks.evaluate(hooks.Change(tmp_path, ("a",), True), [gate], set())
    assert outcomes[0].severity == hooks.WARN
    assert "not run: tools/absent.py is not in this checkout" in outcomes[0].messages[0]


def test_gh3_10_writing_blocks_at_a_commit_and_wrapping_warns(repo: Path) -> None:
    shutil.copy(TOOLS / "writing_rules.py", repo / "tools")
    (repo / "README.md").write_text("A file.\n\nOne clause; another.\nA wrapped\nparagraph.\n")
    sh(repo, "git", "add", "README.md")
    change = hooks.Change(repo, hooks.staged_files(repo), False)
    registry = [c for c in hooks.checks() if c.name in ("writing", "wrapping")]
    outcomes = {o.check: o for o in hooks.evaluate(change, registry, set())}
    assert outcomes["writing"].severity == hooks.BLOCK
    assert outcomes["writing"].messages == ("README.md:3: a semicolon in prose. Use a period or a comma",)
    assert outcomes["wrapping"].severity == hooks.WARN
    assert outcomes["wrapping"].messages[0].startswith("README.md: 2 hard-wrapped line(s), from line 4")
    merge = hooks.Change(repo, change.files, True)
    assert {o.check: o.severity for o in hooks.evaluate(merge, registry, set())}["writing"] == hooks.WARN
