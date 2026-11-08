# SPDX-License-Identifier: MPL-2.0
"""Tests of the hooks dispatcher (ADR-A133). Each runs git in a temporary repository."""

from __future__ import annotations

import os
import shutil
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
        assert hooks.HOOK_MARK in hook.read_text(encoding="utf-8")
        assert os.access(hook, os.X_OK)  # the mode bit on POSIX. Git for Windows runs a hook whatever its mode
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
    # Without mise on the path, the hook starts the dispatcher with the first Python that runs, as on a bare checkout.
    path = os.pathsep.join(d for d in os.environ.get("PATH", "").split(os.pathsep)
                           if d and not shutil.which("mise", path=d))
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
    assert not [c for c in hooks.checks() if c.name == "studio-browser"], "a test suite runs by convention, never in a hook (GH-5)"
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


def test_or1_01_a_register_or_decision_change_runs_the_identifier_check() -> None:
    assert "identifiers" in names_for("docs/developer/standards.md")
    assert "identifiers" in names_for("docs/architecture/decisions/ADR-A133-git-hooks.md")
    assert "identifiers" not in names_for("ontology/party/README.md")


def test_or1_02_post_merge_rebuilds_the_index_and_never_fails(repo: Path, capsys) -> None:
    assert hooks.run(repo, "post-merge") == 0
    assert "post-merge" in capsys.readouterr().out


# ---- WB-4: the work board check and the post-merge registers, over vyd (ADR-A152, plan vyvid-migration, VM-4) ----

RECORD = """# Alpha: status

**Unit ID:** `alpha`
**Status:** building 2026-10-30. A-2 next.

## Position

| Slice | Deliverable | State | Blocked on |
|---|---|---|---|
| AL-1 | the parser | merged 2026-10-28, built 2026-10-25 | |
| AL-2 | the join | building 2026-10-30 | |
| AL-3 | the tool | planned | AL-2 |
"""

# The probe project, with the work settings of this checkout's own vyvid.toml (sweep left out).
WORK_PROJECT = """[project]
name = "probe"
visibility = "private"
docs = "code:docs"

[project.families]
SL = { pattern = 'AL-\\d+', defined = "docs:developer/INDEX.md", type = "slice" }

[project.work]
status = "docs:developer/status"
plans = "docs:developer/plans"
sketches = "docs:developer/sketches"
validation = "docs:developer/validation"
reviews = "docs:developer/review"
decisions = "docs:architecture/decisions"
index = "docs:developer/INDEX.md"
roadmap = "docs:developer/ROADMAP.md"
levels = ["epic", "unit", "slice"]
roadmap_section = "9"
presence = ".local/agents"

[project.work.markers]
index_begin = "<!-- BEGIN GENERATED work-board. Written by `mise run build:work` from the status records. Edit a status record, never this region. -->"
roadmap_begin = "<!-- BEGIN GENERATED work-board-{name}. Written by `mise run build:roadmap` from the status records on every branch. Edit a status record, never this region. -->"

[project.work.commands]
build = "mise run build:work"
roadmap = "mise run build:roadmap"
normalise = "mise run work:normalise -- --apply"
rename = "mise run work:rename -- --apply"
here = "mise run work:here --"
"""


@pytest.fixture
def work_repo(repo: Path, tmp_path_factory, monkeypatch) -> Path:
    """A repository vyd reads as a project. A vyvid.toml nobody has trusted makes vyd write nothing, and a test never
    trusts one, so the project is declared in a configuration this test writes and names in VYVID_CONFIG, with an
    index store of its own."""
    if shutil.which("vyd") is None:
        pytest.skip("vyd is not installed")
    shutil.copy(TOOLS / "vyd.py", repo / "tools" / "vyd.py")
    scratch = tmp_path_factory.mktemp("vyd")
    declared = WORK_PROJECT.replace("[project]\n", "", 1).replace("[project.", "[projects.")
    config = scratch / "config.toml"
    config.write_text(f'[framework]\nstore = "{(scratch / "index").as_posix()}"\n\n[[projects]]\ncode = "{repo.as_posix()}"\n{declared}',
                      encoding="utf-8")
    monkeypatch.setenv("VYVID_CONFIG", str(config))
    (repo / "docs" / "developer" / "status").mkdir(parents=True)
    (repo / "docs" / "developer" / "INDEX.md").write_text("# Index\n")
    return repo


def record(root: Path, text: str = RECORD) -> str:
    (root / "docs" / "developer" / "status" / "alpha.md").write_text(text)
    return "docs/developer/status/alpha.md"


def build(root: Path, *args: str) -> subprocess.CompletedProcess:
    return sh(root, "vyd", "work", "build", *args, check=False)


def work_messages(root: Path, *files: str) -> list[str]:
    """What the work check says about the staged tree, after staging whatever the scenario changed."""
    sh(root, "git", "add", ".")
    check = next(c for c in hooks.checks() if c.name == "work")
    outcomes = hooks.evaluate(hooks.Change(root, files, merge=False), [check], set())
    return [m for o in outcomes for m in o.messages]


def row_line(text: str, slice_id: str) -> int:
    return next(n for n, row in enumerate(text.splitlines(), 1) if slice_id in row)


def test_wb4_01_a_well_formed_record_with_a_current_index_passes(work_repo: Path) -> None:
    rel = record(work_repo)
    assert build(work_repo).returncode == 0
    assert work_messages(work_repo, rel) == []


def test_wb4_02_a_historic_state_word_is_refused(work_repo: Path) -> None:
    text = RECORD.replace("| AL-2 | the join | building 2026-10-30 |", "| AL-2 | the join | Done (abc123) |")
    rel = record(work_repo, text)
    found = "\n".join(work_messages(work_repo, rel))
    assert f"{rel}:{row_line(text, 'AL-2')}: AL-2: the State cell opens with 'Done (abc123)'" in found
    assert "Run `mise run work:normalise -- --apply`" in found
    assert "merged" in found and "building" in found


def test_wb4_03_a_dated_state_needs_its_day(work_repo: Path) -> None:
    text = RECORD.replace("| building 2026-10-30 | |", "| building | |")
    rel = record(work_repo, text)
    build(work_repo)
    found = work_messages(work_repo, rel)
    assert f"{rel}:{row_line(text, 'AL-2')}: AL-2: building needs the day it was reached, as `building YYYY-MM-DD`" in found


def test_wb4_04_slice_ids_follow_the_grammar(work_repo: Path) -> None:
    rel = record(work_repo, RECORD.replace("AL-3", "C9b3b"))
    build(work_repo)
    found = work_messages(work_repo, rel)
    assert any("C9b3b: a slice id must match" in m and "Run `mise run work:rename -- --apply`" in m for m in found)
    ok = RECORD + "| HQ-6a.1 | a | planned | |\n| AIR-S1 | b | planned | |\n| OD-DOC1 | c | planned | |\n"
    rel = record(work_repo, ok)
    build(work_repo)
    assert work_messages(work_repo, rel) == []


def test_wb4_05_the_status_line_opens_with_a_state_word(work_repo: Path) -> None:
    rel = record(work_repo, RECORD.replace("building 2026-10-30. A-2 next.", "\U0001F528 In progress"))
    build(work_repo)
    assert any("the Status line opens with '\U0001F528 In progress', not a word of planned" in m for m in work_messages(work_repo, rel))
    rel = record(work_repo, RECORD.replace("**Status:** building 2026-10-30. A-2 next.\n", ""))
    build(work_repo)
    assert work_messages(work_repo, rel) == []


def test_wb10_04_a_status_word_its_board_does_not_give_is_refused(work_repo: Path) -> None:
    rel = record(work_repo, RECORD.replace("**Status:** building 2026-10-30.", "**Status:** planned."))
    build(work_repo)
    found = "\n".join(work_messages(work_repo, rel))
    assert "the Status line reads 'planned', its board rolls up to 'building 2026-10-30'" in found
    assert "Run `mise run work:normalise -- --apply`" in found


def test_wb4_06_a_stale_index_region_is_refused_until_rebuilt(work_repo: Path) -> None:
    rel = record(work_repo)
    build(work_repo)
    record(work_repo, RECORD.replace("| AL-3 | the tool | planned |", "| AL-3 | the tool | building 2026-11-01 |"))
    found = work_messages(work_repo, rel)
    assert any("docs/developer/INDEX.md: the work-board region is stale against the status records. Run `mise run build:work`" in m
               for m in found)
    build(work_repo)
    assert work_messages(work_repo, rel) == []
    check = next(c for c in hooks.checks() if c.name == "work")
    assert hooks.evaluate(hooks.Change(work_repo, ("README.md", "docs/developer/plans/x.md"), False), [check], set()) == []


def test_wb4_07_the_work_check_blocks_at_a_commit_and_at_a_merge() -> None:
    check = next(c for c in hooks.checks() if c.name == "work")
    assert (check.on_commit, check.on_merge, check.merge_only) == (hooks.BLOCK, hooks.BLOCK, False)


def commit_all(root: Path) -> None:
    sh(root, "git", "add", ".")
    sh(root, "git", "commit", "-q", "--no-verify", "-m", "work board")


def test_wb4_08_post_merge_regenerates_the_registers_and_never_fails(work_repo: Path, monkeypatch, capsys) -> None:
    record(work_repo)
    roadmap = work_repo / "docs" / "developer" / "ROADMAP.md"
    roadmap.write_text("# Roadmap\n")
    commit_all(work_repo)
    assert hooks.post_merge(work_repo) == 0
    out = capsys.readouterr().out
    assert "INDEX.md region regenerated" in out and "ROADMAP.md regions regenerated" in out
    assert build(work_repo, "--check").returncode == 0
    assert "<!-- BEGIN GENERATED work-board-glance" in roadmap.read_text()
    assert "<!-- BEGIN GENERATED work-board-branches" in roadmap.read_text()
    sh(work_repo, "git", "checkout", "-q", "-b", "feature")
    roadmap.write_text("# Roadmap\n")
    (work_repo / "docs" / "developer" / "INDEX.md").write_text("# Index\n")
    assert hooks.post_merge(work_repo) == 0
    out = capsys.readouterr().out
    assert "INDEX.md region regenerated" in out and "ROADMAP.md" not in out
    assert roadmap.read_text() == "# Roadmap\n"
    assert build(work_repo, "--check").returncode == 0
    without_vyd(monkeypatch)
    assert hooks.post_merge(work_repo) == 0
    out = capsys.readouterr().out
    assert "not regenerated" in out and "Run `mise run build:work`" in out



def test_vm4_01_the_work_check_runs_under_a_git_hooks_environment(work_repo: Path, monkeypatch) -> None:
    """A git hook exports GIT_DIR, under which vyd 0.2.6 took the status folder for the repository root and crashed. Vyvid
    0.2.7 fixes it where vyd starts, and this holds the fix (plan vyvid-migration, VM-4)."""
    rel = record(work_repo)
    assert build(work_repo).returncode == 0
    monkeypatch.setenv("GIT_DIR", str(work_repo / ".git"))
    assert work_messages(work_repo, rel) == []


def test_vm5_01_the_skills_check_skips_with_a_note_where_vyd_is_absent(monkeypatch, capsys) -> None:
    without_vyd(monkeypatch)
    change = hooks.Change(ROOT, (".claude/skills/lattice-lifecycle/SKILL.md",), False)
    assert hooks.vyd("check", "skills")(change, []) == []
    out = capsys.readouterr().out
    assert "`vyd check skills` was skipped" in out and "mise run bootstrap" in out


def test_vm5_02_the_skills_check_passes_on_this_checkout() -> None:
    if shutil.which("vyd") is None:
        pytest.skip("vyd is not installed")
    config = subprocess.run(["vyd", "config"], capture_output=True, text=True, timeout=60, cwd=ROOT).stdout
    if "is not trusted" in config or "projects: none" in config:
        pytest.skip("the binding is not trusted here, run `vyd trust` in the checkout")
    change = hooks.Change(ROOT, (".claude/skills/lattice-lifecycle/SKILL.md",), False)
    assert hooks.vyd("check", "skills")(change, []) == []


# ---- VM-2: the index hooks over vyd, an absent tool skips and never blocks (ADR-A152 decision 4) ----

PROBE_PROJECT = """[project]
name = "probe"
visibility = "private"
docs = "code:docs"

[project.families]
STD = { defined = "docs:standards.md", type = "standard" }
"""


@pytest.fixture
def vyd_repo(repo: Path) -> Path:
    shutil.copy(TOOLS / "vyd.py", repo / "tools" / "vyd.py")
    return repo


def without_vyd(monkeypatch) -> None:
    real = shutil.which
    monkeypatch.setattr(shutil, "which", lambda name, *a, **k: None if name == "vyd" else real(name, *a, **k))


def test_vm2_01_the_identifiers_check_skips_with_a_note_where_vyd_is_absent(vyd_repo: Path, monkeypatch, capsys) -> None:
    without_vyd(monkeypatch)
    change = hooks.Change(vyd_repo, ("docs/developer/standards.md",), False)
    assert hooks.vyd("check", "identifiers")(change, []) == []
    out = capsys.readouterr().out
    assert "`vyd check identifiers` was skipped" in out and "mise run bootstrap" in out


def test_vm2_02_post_merge_says_the_index_was_not_rebuilt_and_never_fails_where_vyd_is_absent(vyd_repo: Path, monkeypatch, capsys) -> None:
    without_vyd(monkeypatch)
    assert hooks.run(vyd_repo, "post-merge") == 0
    out = capsys.readouterr().out
    assert "not rebuilt" in out and "`vyd build` was skipped" in out and "mise run bootstrap" in out


def test_vm2_03_a_vyd_that_did_not_run_skips_with_its_reason(vyd_repo: Path, monkeypatch, tmp_path_factory, capsys) -> None:
    bin_dir = tmp_path_factory.mktemp("bin")
    script = bin_dir / "fake_vyd.py"
    script.write_text("import sys\nprint('vyvid.toml is not trusted', file=sys.stderr)\nsys.exit(2)\n", encoding="utf-8")
    if os.name == "nt":
        (bin_dir / "vyd.cmd").write_text(f'@"{sys.executable}" "{script}" %*\r\n', encoding="utf-8", newline="")
    else:
        fake = bin_dir / "vyd"
        fake.write_text(f'#!/bin/sh\nexec "{sys.executable}" "{script}" "$@"\n', encoding="utf-8", newline="\n")
        fake.chmod(0o755)
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ['PATH']}")
    assert hooks.vyd("check", "identifiers")(hooks.Change(vyd_repo, (), False), []) == []
    out = capsys.readouterr().out
    assert "did not run" in out and "vyd trust" in out


def test_vm2_04_the_identifiers_check_fails_a_mention_nothing_defines_where_vyd_is_present(vyd_repo: Path) -> None:
    if shutil.which("vyd") is None:
        pytest.skip("vyd is not installed")
    (vyd_repo / "vyvid.toml").write_text(PROBE_PROJECT)
    (vyd_repo / "docs").mkdir()
    standards = vyd_repo / "docs" / "standards.md"
    standards.write_text("# Standards\n\n| ID | Claim |\n|---|---|\n| STD-01 | **A rule.** |\n\nSee STD-99.\n")
    sh(vyd_repo, "git", "add", ".")
    sh(vyd_repo, "git", "commit", "-q", "--no-verify", "-m", "probe")
    check = hooks.vyd("check", "identifiers")
    change = hooks.Change(vyd_repo, ("docs/standards.md",), False)
    assert any("STD-99" in line for line in check(change, []))
    standards.write_text("# Standards\n\n| ID | Claim |\n|---|---|\n| STD-01 | **A rule.** |\n\nSee STD-01.\n")
    assert check(change, []) == []


def test_gh1_install_writes_the_repositorys_own_hooks_whatever_core_hookspath_says(repo: Path, tmp_path_factory) -> None:
    """A user may point core.hooksPath at shims of their own, which run the repository's hooks from its own folder. The
    installer writes there, so it never overwrites a shim, and the dispatcher still runs."""
    shims = tmp_path_factory.mktemp("shims")
    (shims / "pre-commit").write_text("#!/bin/sh\nexit 0\n")
    sh(repo, "git", "config", "core.hooksPath", str(shims))
    assert hooks.hooks_dir(repo) == (repo / ".git" / "hooks").resolve() or hooks.hooks_dir(repo) == repo / ".git" / "hooks"
    hooks.install(repo)
    assert (repo / ".git" / "hooks" / "pre-commit").is_file() and (shims / "pre-commit").read_text() == "#!/bin/sh\nexit 0\n"
