# SPDX-License-Identifier: MPL-2.0
"""Tests the hook that refuses a tool call which would read the studio stack's secrets (`secret_read_guard.py`)."""

from __future__ import annotations

import io
import json
import shutil
import stat
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lattice_repo_catalogue  # noqa: E402
import secret_read_guard as guard  # noqa: E402

ROOT = str(lattice_repo_catalogue.find_root())
FOLDER = ".build/config-studio/infra/broker"
SECRET = "Zq9-sentinel-secret-value-0123456789abcdef"
ROOT_NAMES = ("studio-sploot", "lattice", "plain-root")
SETTINGS = Path(ROOT) / ".claude" / "settings.json"
DENY, ALLOW = "deny", "allow"


@pytest.fixture(scope="module", params=ROOT_NAMES)
def root_dir(request: pytest.FixtureRequest, tmp_path_factory: pytest.TempPathFactory) -> str:
    """A repository root, as a folder with a `mise.toml`, whose own path holds the name the parameter gives."""
    path = tmp_path_factory.mktemp("roots") / request.param
    path.mkdir()
    (path / "mise.toml").write_text("", encoding="utf-8")
    return str(path)


def call(tool: str, cwd: Optional[str] = None, **given: str) -> Dict:
    return {"tool_name": tool, "tool_input": given, "cwd": cwd or ROOT}


def run(payload: object, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture, raw: Optional[str] = None) -> tuple:
    """The guard's verdict as `(DENY, reason)` or `(ALLOW, "")`. The guard always exits 0, and only a refusal prints, as one JSON decision."""
    monkeypatch.setattr(sys, "stdin", io.StringIO(raw if raw is not None else json.dumps(payload)))
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", ROOT)
    status = guard.main()
    seen = capsys.readouterr()
    assert status == 0 and seen.err == "", "the guard exits 0 and writes nothing on standard error"
    if not seen.out:
        return ALLOW, ""
    decision = json.loads(seen.out)
    assert list(decision) == ["hookSpecificOutput"] and seen.out.count("\n") == 1
    assert list(decision["hookSpecificOutput"]) == ["hookEventName", "permissionDecision", "permissionDecisionReason"]
    assert decision["hookSpecificOutput"]["hookEventName"] == "PreToolUse" and decision["hookSpecificOutput"]["permissionDecision"] == "deny"
    return DENY, decision["hookSpecificOutput"]["permissionDecisionReason"]


READS = [
    f"cat {FOLDER}/password",
    f"cat ./{FOLDER}/password",
    f"cat {ROOT}/{FOLDER}/amqp-uri",
    f"cat .build/config-studio/infra/../infra/broker/secret",
    f"cat .build/config-studio//infra/./broker/stream-uri",
    f"head -c 5 '{FOLDER}/password'",
    f"cat .build/config-studio/infra/'bro'ker/password",
    f"cat {FOLDER}\\password",
    f"cat < {FOLDER}/password",
    f"sed -n 1p --file={FOLDER}/password",
    f"grep -r x {FOLDER}",
    f"rg default .build/config-studio/infra/broker/rabbitmq-secret.conf",
    "cat .build/config-studio/infra/rabbitmq-secret.conf",
    "cat .build/config-studio/infra/compose/rabbitmq-studio.conf",
    f"python -c \"print(open('{FOLDER}/password').read())\"",
    f"bash -c 'cat {FOLDER}/password'",
    f"ls {FOLDER} && cat {FOLDER}/password",
    f"echo ok; cat {FOLDER}/password",
    f"echo $(cat {FOLDER}/password)",
    f"cat .build/config-studio/infra/br*/password",
    f"cat .build/config-studio/infra/b?oker/pass*",
    'cat "$LATTICE_AMQP_URI_FILE"',
    "cat ${LATTICE_STREAM_URI_FILE}",
    "cat $LATTICE_STUDIO_BROKER_SECRET_FILE",
    "echo $LATTICE_AMQP_URI",
    "printenv LATTICE_AMQP_URI_FILE",
    "grep -rn x .build/config-studio",
    "rg x .build",
]

# What the report of 2026-11-26 says was refused and is allowed.
HARMLESS = [
    "git branch -a --list '*sploot*'",
    "git branch -a --list '*studio*'",
    "git branch --list '*lattice*'",
    "find . -name '*broker*'",
    "find docs -name '*config*'",
    "git log --oneline -- '*secret*'",
    "git log --grep 'pass*'",
    "echo [a-z]*",
    # Allowed before and to stay allowed.
    "ls *work*",
    "git for-each-ref 'refs/heads/*sploot'",
    # More names and expressions, and wildcards that match nothing in the folder.
    "git log --oneline --author='pass*' -- 'docs/*secret*'",
    "find . -iname '*password*' -path '*broker*'",
    "find . -regex '.*broker.*'",
    "rg -g '*secret*' x docs",
    "rg --glob='*broker*' x docs",
    "grep -rn 'pass*' docs",
    "grep -e 'password.*' docs/a.md",
    "cat docs/*.md",
    "cat *",
    "cat [a-z]*",
    "head -n 3 tools/*.py",
    "bash -c 'git branch --list \"*studio*\"'",
    "mise exec -- git branch --list '*sploot*'",
    # A pattern that does match the folder's files, given to a program that opens nothing by it.
    "echo .build/*/infra/*/pass*",
    "git log --oneline -- '.build/*/infra/*/pass*'",
    "find . -path '.build/*/infra/*/pass*'",
    "git branch --list '.build/*/infra/*/pass*'",
]

REFUSED = [
    f"cat {FOLDER}/password",
    "cat .build/*/infra/*/pass*",
    f"cat {FOLDER}/*",
    "cat .build/config-studio/infra/b*/password",
    "cat .build/**/password",
    "cat **/broker/secret",
    "head -c 3 .build/config-studio/infra/broker/amqp-*",
    "find .build/config-studio/infra/br* -type f -exec cat {} +",
    "grep -r x .build/*/infra/*",
    "grep -e x .build/*/infra/broker/pass*",
    "rg -g '*.conf' x .build/*/infra/*",
    "cp .build/config-studio/infra/broker/pa* /tmp/x",
    "bash -c 'cat .build/*/infra/*/pass*'",
    "mise exec -- cat .build/*/infra/*/pass*",
    "eval cat .build/*/infra/*/pass*",
    "echo ok; cat .build/*/infra/*/pass*",
    "Get-Content .build/*/infra/*/pass*",
]


@pytest.mark.parametrize("command", READS)
def test_each_way_of_reading_the_secrets_from_the_shell_is_refused(command: str, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture) -> None:
    for tool in ("Bash", "PowerShell"):
        verdict, reason = run(call(tool, command=command), monkeypatch, capsys)
        assert verdict == DENY, (tool, command)
        assert "mise run studio:config" in reason and "\n" not in reason


def test_a_command_run_from_inside_the_stacks_folders_is_refused_by_its_working_directory(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture) -> None:
    assert run(call("Bash", cwd=f"{ROOT}/.build/config-studio/infra", command="cat broker/password"), monkeypatch, capsys)[0] == DENY
    assert run(call("Bash", cwd=f"{ROOT}/{FOLDER}", command="cat password ../broker/amqp-uri"), monkeypatch, capsys)[0] == DENY
    assert run(call("Bash", cwd=f"{ROOT}/tools", command="cat ../.build/config-studio/infra/broker/secret"), monkeypatch, capsys)[0] == DENY


@pytest.mark.parametrize("path", [f"{ROOT}/{FOLDER}/password", f"{FOLDER}/amqp-uri", f"./{FOLDER}/secret", f"{ROOT}/.build/config-studio/infra/x/../broker/stream-uri",
                                  f"{ROOT}/.build/config-studio/infra/broker/rabbitmq-secret.conf", f"{ROOT}\\.build\\config-studio\\infra\\broker\\password"])
def test_a_read_of_a_file_in_the_folder_is_refused(path: str, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture) -> None:
    verdict, reason = run(call("Read", file_path=path), monkeypatch, capsys)
    assert verdict == DENY and "mise run studio:config" in reason


@pytest.mark.parametrize("given", [
    {"pattern": "default_pass", "path": f"{ROOT}/{FOLDER}"},
    {"pattern": "x", "path": FOLDER},
    {"pattern": "x", "path": ".build/config-studio/infra/../infra/broker"},
    {"pattern": "x", "glob": "**/infra/broker/*"},
    {"pattern": "x", "path": ".build/config-studio"},
    {"pattern": "x", "path": f"{ROOT}/.build"},
    {"pattern": "x", "path": ".build/*/infra/broker"},
])
def test_a_search_of_the_folder_or_a_folder_that_holds_it_is_refused(given: Dict[str, str], monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture) -> None:
    assert run(call("Grep", **given), monkeypatch, capsys)[0] == DENY


@pytest.mark.parametrize("given", [{"pattern": f"{FOLDER}/*"}, {"pattern": "*", "path": FOLDER}, {"pattern": "**/broker/**"}, {"pattern": "password", "path": f"{ROOT}/{FOLDER}"},
                                   {"pattern": ".build/*/infra/*/*"}])
def test_a_glob_of_the_folder_is_refused(given: Dict[str, str], monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture) -> None:
    assert run(call("Glob", **given), monkeypatch, capsys)[0] == DENY


@pytest.mark.parametrize("command", [
    f"ls {FOLDER}",
    f"ls -la {ROOT}/{FOLDER}",
    f"rm -f {FOLDER}/password {FOLDER}/secret {FOLDER}/amqp-uri {FOLDER}/stream-uri",
    f"rm -rf .build/config-studio/infra/broker .build/config-studio/infra/rabbitmq/mnesia",
    "mise run studio:up",
    "mise run studio:status",
    "mise run studio:config",
    "mise run studio:config -- --root .",
    "python tools/config_studio_stack.py config",
    "mise exec -- python tools/config_studio_stack.py down",
    f"mise exec -- bash -c 'python tools/config_studio_stack.py up'",
    "python tools/config_studio_stack.py up --root " + ROOT,
    "git status --short",
    "mise run check:config-studio",
    "grep -rn LATTICE_AMQP_URI_FILE docs mise.toml",
    "grep -rn x .",
    "cat tools/config_studio_stack.py",
    "cat .build/config-studio/infra/rabbitmq/rabbitmq.conf",
    "ls .build/config-studio",
])
def test_the_commands_that_run_the_stack_list_names_or_delete_pass(command: str, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture) -> None:
    assert run(call("Bash", command=command), monkeypatch, capsys) == (ALLOW, "")


def test_an_unrelated_call_passes(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture) -> None:
    for payload in (call("Read", file_path=f"{ROOT}/mise.toml"), call("Grep", pattern="def main", path="tools"), call("Glob", pattern="tools/*.py"),
                    call("Edit", file_path=f"{ROOT}/{FOLDER}/password", old_string="a", new_string="b"), call("Bash", command=""),
                    call("Bash", command="python -m pytest tools -q"), {"tool_name": "Read"}, {"tool_input": []}):
        assert run(payload, monkeypatch, capsys) == (ALLOW, "")


@pytest.mark.parametrize("raw", ["", "not json", "[1, 2]", "null", '{"tool_name": "Bash", "tool_input": "cat x"}', '{"tool_name": 7, "tool_input": {"command": 5}}', '{"tool_name": "Bash"'])
def test_input_the_guard_cannot_parse_passes(raw: str, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture) -> None:
    assert run(None, monkeypatch, capsys, raw=raw) == (ALLOW, "")


def test_a_fault_inside_the_guard_passes(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture) -> None:
    monkeypatch.setattr(guard, "refusal", lambda payload: 1 / 0)
    assert run(call("Bash", command=f"cat {FOLDER}/password"), monkeypatch, capsys) == (ALLOW, "")


def test_the_refusal_holds_no_part_of_the_call(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture) -> None:
    verdict, reason = run(call("Bash", command=f"echo {SECRET}; cat {FOLDER}/password"), monkeypatch, capsys)
    assert verdict == DENY and SECRET not in reason and "password" not in reason.replace("stack's secrets", "")
    assert run(call("Read", file_path=f"{FOLDER}/{SECRET}"), monkeypatch, capsys)[1].count(SECRET) == 0


def test_the_variables_are_read_from_mise_toml(tmp_path: Path) -> None:
    (tmp_path / "mise.toml").write_text('env = { OTHER_KEY_FILE = ".build/config-studio/infra/broker/x", UNRELATED = "y" }\n', encoding="utf-8")
    names = guard.variables(str(tmp_path))
    assert "OTHER_KEY_FILE" in names and "UNRELATED" not in names and "LATTICE_AMQP_URI_FILE" in names
    assert "LATTICE_AMQP_URI_FILE" in guard.variables(str(tmp_path / "missing"))
    real = guard.variables(ROOT)
    assert {"LATTICE_AMQP_URI_FILE", "LATTICE_STREAM_URI_FILE", "LATTICE_STUDIO_BROKER_SECRET_FILE"} <= set(real)


def test_a_refusal_is_the_hooks_json_decision_and_the_exit_status_is_0() -> None:
    script = str(Path(guard.__file__))
    env = {"CLAUDE_PROJECT_DIR": ROOT, "PATH": ""}
    refused = subprocess.run([sys.executable, script], input=json.dumps(call("Read", file_path=f"{FOLDER}/password")), capture_output=True, text=True, env=env)
    assert (refused.returncode, refused.stderr) == (0, "")
    assert json.loads(refused.stdout) == {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                                                                 "permissionDecisionReason": guard.MESSAGE.format(what="path to read", folder=FOLDER)}}
    passed = subprocess.run([sys.executable, script], input=json.dumps(call("Bash", command="ls")), capture_output=True, text=True, env=env)
    assert (passed.returncode, passed.stdout, passed.stderr) == (0, "", "")
    assert subprocess.run([sys.executable, script], input="{", capture_output=True, text=True, env=env).returncode == 0


# The false refusals of 2026-11-26, under a root whose path holds `studio-sploot`, one that holds `lattice` and a plain one.

@pytest.mark.parametrize("command", HARMLESS)
def test_a_command_that_only_names_or_lists_what_a_pattern_matches_is_allowed_under_each_root(command: str, root_dir: str, monkeypatch: pytest.MonkeyPatch,
                                                                                               capsys: pytest.CaptureFixture) -> None:
    for tool in ("Bash", "PowerShell"):
        assert run(call(tool, cwd=root_dir, command=command), monkeypatch, capsys) == (ALLOW, ""), (tool, command)


@pytest.mark.parametrize("given", [
    ("Glob", {"pattern": "**/*studio*"}),
    ("Glob", {"pattern": "*config-studio*"}),
    ("Glob", {"pattern": "**/*broker*.py"}),
    ("Glob", {"pattern": "**/*.md"}),
    ("Glob", {"pattern": "**/*sploot*"}),
    ("Glob", {"pattern": "*lattice*"}),
    ("Grep", {"pattern": "password.*"}),
    ("Grep", {"pattern": "secret", "path": "docs"}),
    ("Grep", {"pattern": "infra/broker/password"}),
    ("Grep", {"pattern": "*sploot*", "path": "docs"}),
    ("Grep", {"pattern": "x", "glob": "*.py"}),
    ("Grep", {"pattern": "x", "glob": "**/*broker*.py"}),
    ("Grep", {"pattern": "x", "glob": "*studio*"}),
    ("Read", {"file_path": "docs/developer/INDEX.md"}),
])
def test_a_glob_a_pattern_and_a_regular_expression_that_read_nothing_of_the_folder_are_allowed_under_each_root(given: tuple, root_dir: str, monkeypatch: pytest.MonkeyPatch,
                                                                                                           capsys: pytest.CaptureFixture) -> None:
    tool, values = given
    assert run(call(tool, cwd=root_dir, **values), monkeypatch, capsys) == (ALLOW, "")


@pytest.mark.parametrize("command", REFUSED)
def test_a_wildcard_that_names_the_folder_where_a_program_opens_it_is_refused_under_each_root(command: str, root_dir: str, monkeypatch: pytest.MonkeyPatch,
                                                                                               capsys: pytest.CaptureFixture) -> None:
    for tool in ("Bash", "PowerShell"):
        assert run(call(tool, cwd=root_dir, command=command), monkeypatch, capsys)[0] == DENY, (tool, command)


def test_the_folder_is_refused_under_each_root_by_each_tool(root_dir: str, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture) -> None:
    inside = f"{root_dir}/{FOLDER}"
    assert run(call("Read", cwd=root_dir, file_path=f"{FOLDER}/password"), monkeypatch, capsys)[0] == DENY
    assert run(call("Read", cwd=root_dir, file_path=f"{inside}/secret"), monkeypatch, capsys)[0] == DENY
    assert run(call("Grep", cwd=root_dir, pattern="x", path=FOLDER), monkeypatch, capsys)[0] == DENY
    assert run(call("Grep", cwd=root_dir, pattern="x", path=inside), monkeypatch, capsys)[0] == DENY
    assert run(call("Grep", cwd=root_dir, pattern="x", glob=".build/*/infra/broker/*"), monkeypatch, capsys)[0] == DENY
    assert run(call("Glob", cwd=root_dir, pattern=".build/*/infra/*/pass*"), monkeypatch, capsys)[0] == DENY
    assert run(call("Bash", cwd=root_dir, command="cat pass*"), monkeypatch, capsys)[0] == ALLOW
    assert run(call("Bash", cwd=inside, command="cat pass*"), monkeypatch, capsys)[0] == DENY
    assert run(call("Bash", cwd=inside, command="cat *"), monkeypatch, capsys)[0] == DENY
    assert run(call("Bash", cwd=inside, command="ls *"), monkeypatch, capsys)[0] == ALLOW
    assert run(call("Bash", cwd=f"{root_dir}/tools", command="cat ../.build/*/infra/*/pass*"), monkeypatch, capsys)[0] == DENY
    assert run(call("Bash", cwd=root_dir, command=f"cat {inside}/pass*"), monkeypatch, capsys)[0] == DENY
    assert run(call("Bash", cwd=root_dir, command=f"cat {root_dir}/.build/*/infra/*/pass*"), monkeypatch, capsys)[0] == DENY


# The matcher.

@pytest.mark.parametrize("pattern, target, expected", [
    ("*", "a", True),
    ("*", "a/b", False),
    ("a/*", "a/b", True),
    ("a/*", "a", False),
    ("a?", "ab", True),
    ("a?", "a", False),
    ("[a-z]*", "x1", True),
    ("[a-z]*", "x1/y", False),
    ("[!a-z]*", "x1", False),
    ("*sploot*", "work/studio-sploot/docs", False),
    ("*sploot*", "studio-sploot", True),
    ("**", "", True),
    ("**", "a/b/c", True),
    ("**/b", "b", True),
    ("**/b", "a/b", True),
    ("**/b", "a/c", False),
    ("a/**/c", "a/c", True),
    ("a/**/c", "a/b/d/c", True),
    ("a/**/c", "a/b/d", False),
    ("a/**", "a", True),
    ("**/*.py", "x/y/z.py", True),
    ("**/*.py", "x/y/z.md", False),
    ("a**b", "a/b", False),
    ("a**b", "axxb", True),
    ("../a/*", "../a/b", True),
    ("../a/*", "a/b", False),
])
def test_a_wildcard_is_matched_by_path_segment(pattern: str, target: str, expected: bool) -> None:
    assert guard.segments_match(guard.split_path(pattern), guard.split_path(target)) is expected


@pytest.mark.parametrize("form, cwd, guarded, expected", [
    (".build/*/infra/*/pass*", "", True, True),
    (".build/*/infra/*/pass*", "", False, True),
    ("*", "", True, False),
    ("*/", "", True, False),
    ("[a-z]*", "", True, False),
    ("*studio*", "", True, False),
    ("*broker*", "", True, False),
    ("*config*", "", True, False),
    ("*secret*", "", True, False),
    ("*lattice*", "", True, False),
    ("**/*broker*.py", "", True, False),
    ("**/*.md", "", True, False),
    ("**/broker/**", "", True, True),
    ("**/*studio*", "", True, True),
    ("**/*studio*", "", False, False),
    ("**/*secret*.conf", "", True, True),
    ("**/*secret*.conf", "", False, True),
    ("pass*", "/.build/config-studio/infra/broker", True, True),
    ("pass*", "/tools", True, False),
    ("*", "/.build/config-studio/infra/broker", False, True),
    ("../.build/*/infra/*/pass*", "/tools", True, True),
    ("../*/infra/*/pass*", "/.build/config-studio/infra/broker", True, False),
    ("../../*/*/pass*", "/.build/config-studio/infra/broker", True, True),
    ("../*/pass*", "/.build/config-studio/infra/broker", True, True),
])
def test_a_wildcard_is_resolved_against_the_working_directory_and_the_root_only(form: str, cwd: str, guarded: bool, expected: bool) -> None:
    # The root's own text holds wildcard characters and the name of what the cases ask about, and none of it may act as a pattern.
    for root in ("/work/studio-sploot/lattice", "/work/[a-z]*/lattice", "C:/work/studio-sploot"):
        assert guard.wildcard_names(form, root, root + cwd, guarded) is expected, (root, form)
    absolute = "/work/studio-sploot/lattice"
    assert guard.wildcard_names(absolute + "/.build/*/infra/broker/*", absolute, absolute, True) is True
    assert guard.wildcard_names("/work/*/lattice/.build/*/infra/broker/pass*", absolute, absolute, True) is True
    assert guard.wildcard_names("/work/*/lattice/*", absolute, absolute, True) is False


@pytest.mark.parametrize("program, rest, expected", [
    ("cat", ["-n", "pass*", "x*"], {1, 2}),
    ("cat", ["-e", "pass*"], {1}),
    ("cat", ["--file=a*"], {0}),
    ("head", ["-c", "5", "a*"], {1, 2}),
    ("grep", ["-rn", "pass*", "docs", "tools/*"], {2, 3}),
    ("grep", ["-e", "pass*", "docs"], {2}),
    ("grep", ["-rne", "pass*", "docs"], {2}),
    ("grep", ["-f", "pats*", "docs"], {1, 2}),
    ("rg", ["-g", "*.py", "x", "dir"], {3}),
    ("rg", ["--glob=*.py", "x", "dir"], {2}),
    ("rg", ["-A", "3", "x", "dir"], {3}),
    ("sed", ["-n", "s/a*/b/p", "f*"], {2}),
    ("sed", ["-e", "s/a*/b/", "f*"], {2}),
    ("find", [".", "-name", "*b*"], {0}),
    ("find", ["-L", "docs", "tools", "-type", "f", "-name", "*x"], {1, 2}),
    ("find", ["-name", "*b*"], set()),
    ("find", ["docs", "!", "-name", "*b*"], {0}),
    ("git", ["log", "--grep", "pass*", "--", "*secret*"], set()),
    ("git", ["branch", "--list", "*studio*"], set()),
    ("echo", ["[a-z]*"], set()),
    ("ls", ["*work*"], set()),
    ("unknown-tool", ["*work*"], set()),
])
def test_a_wildcard_is_tested_only_where_the_program_opens_what_it_names(program: str, rest: List[str], expected: set) -> None:
    assert guard.opened(program, rest) == expected


# The root.

def test_the_root_comes_from_the_calls_working_directory_before_the_project_directory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    mine = tmp_path / "mine"
    (mine / "tools").mkdir(parents=True)
    (mine / "mise.toml").write_text("", encoding="utf-8")
    stale = tmp_path / "stale"
    stale.mkdir()
    (stale / "mise.toml").write_text("", encoding="utf-8")
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(stale))
    assert guard.root_of({"cwd": str(mine / "tools")}) == str(mine)
    assert guard.root_of({"cwd": str(mine)}) == str(mine)
    assert guard.root_of({"cwd": ""}) == str(stale)
    assert guard.root_of({}) == str(stale)
    assert guard.root_of({"cwd": 7}) == str(stale)
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path / "gone"))
    assert guard.root_of({"cwd": str(mine)}) == str(mine)
    assert guard.root_of({}) == str(tmp_path / "gone")
    bare = tmp_path / "bare"
    bare.mkdir()
    assert guard.root_of({"cwd": str(bare)}) == str(bare), "a working directory with no mise.toml above it is its own root"


def test_a_stale_project_directory_decides_nothing(root_dir: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture) -> None:
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(call("Bash", cwd=root_dir, command=f"cat {FOLDER}/password; git branch --list '*studio*'"))))
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path / "an-earlier-checkout"))
    assert guard.main() == 0
    assert json.loads(capsys.readouterr().out)["hookSpecificOutput"]["permissionDecision"] == "deny"
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(call("Read", cwd=root_dir, file_path=f"{root_dir}/{FOLDER}/amqp-uri"))))
    assert guard.main() == 0
    assert json.loads(capsys.readouterr().out)["hookSpecificOutput"]["permissionDecision"] == "deny"
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps({"tool_name": "Bash", "tool_input": {"command": f"cat {root_dir}/{FOLDER}/password"}})))
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", root_dir)
    assert guard.main() == 0
    assert json.loads(capsys.readouterr().out)["hookSpecificOutput"]["permissionDecision"] == "deny", "the project directory decides where the call states no working directory"


# The hook command, which keeps a guard that cannot run from blocking the session.

def hook_command() -> str:
    settings = json.loads(SETTINGS.read_text(encoding="utf-8"))
    commands = [hook["command"] for entry in settings["hooks"]["PreToolUse"] for hook in entry["hooks"] if "secret_read_guard" in hook["command"]]
    assert len(commands) == 1
    return commands[0]


def shim_mise(folder: Path) -> str:
    """A `mise` that runs `mise exec -- python <script>` with the interpreter of this run, so the hook command is tested without the toolchain."""
    folder.mkdir()
    shim = folder / "mise"
    shim.write_text(f'#!/bin/sh\nshift 3\nexec "{sys.executable}" "$@"\n', encoding="utf-8")
    shim.chmod(shim.stat().st_mode | stat.S_IXUSR)
    return str(folder)


def run_hook(project: str, path: str, stdin: str = "") -> subprocess.CompletedProcess:
    sh = shutil.which("sh")
    assert sh
    return subprocess.run([sh, "-c", hook_command()], input=stdin, capture_output=True, text=True, env={"CLAUDE_PROJECT_DIR": project, "PATH": path})


def project_with(folder: Path, source: str) -> str:
    (folder / "tools").mkdir(parents=True)
    (folder / "tools" / "secret_read_guard.py").write_text(source, encoding="utf-8")
    return str(folder)


needs_sh = pytest.mark.skipif(shutil.which("sh") is None, reason="the hook command is POSIX sh")


def says_not_run(done: subprocess.CompletedProcess, why: str) -> None:
    message = f"secret_read_guard did not run ({why}), so this call was not checked"
    assert done.returncode == 0
    assert json.loads(done.stdout) == {"systemMessage": message}
    assert message.replace(", so this call was not checked", "") in done.stderr and done.stderr.count("\n") >= 1


@needs_sh
def test_the_hook_command_is_one_short_line_of_sh() -> None:
    command = hook_command()
    assert "\n" not in command and len(command) < 700
    assert "[ -f" in command or "[ ! -f" in command


@needs_sh
def test_a_guard_that_is_missing_lets_the_call_through_with_a_warning(tmp_path: Path) -> None:
    path = shim_mise(tmp_path / "bin")
    (tmp_path / "gone").mkdir()
    says_not_run(run_hook(str(tmp_path / "gone"), path), "the script is missing")
    says_not_run(run_hook(str(tmp_path / "never-made"), path), "the script is missing")
    says_not_run(run_hook("", path), "the script is missing")


@needs_sh
def test_a_guard_that_exits_2_or_raises_lets_the_call_through_with_a_warning(tmp_path: Path) -> None:
    path = shim_mise(tmp_path / "bin")
    exits = project_with(tmp_path / "exits", "import sys\nprint('half a decision')\nsys.exit(2)\n")
    done = run_hook(exits, path, "{}")
    says_not_run(done, "the run exited non-zero")
    assert "half a decision" not in done.stdout
    raises = project_with(tmp_path / "raises", "raise RuntimeError('broken')\n")
    says_not_run(run_hook(raises, path, "{}"), "the run exited non-zero")
    broken = project_with(tmp_path / "broken", "def (:\n")
    says_not_run(run_hook(broken, path, "{}"), "the run exited non-zero")


@needs_sh
def test_a_mise_that_is_not_found_lets_the_call_through_with_a_warning(tmp_path: Path) -> None:
    (tmp_path / "empty").mkdir()
    says_not_run(run_hook(ROOT, str(tmp_path / "empty"), "{}"), "mise is not found")


@needs_sh
def test_the_real_guard_run_by_the_hook_command_denies_a_read_and_says_nothing_else(tmp_path: Path) -> None:
    path = shim_mise(tmp_path / "bin")
    refused = run_hook(ROOT, path, json.dumps(call("Read", file_path=f"{FOLDER}/password")))
    assert (refused.returncode, refused.stderr) == (0, "")
    assert json.loads(refused.stdout) == json.loads(guard.decision(guard.MESSAGE.format(what="path to read", folder=FOLDER)))
    allowed = run_hook(ROOT, path, json.dumps(call("Bash", command="git branch --list '*studio*'")))
    assert (allowed.returncode, allowed.stdout, allowed.stderr) == (0, "", "")
    unparsable = run_hook(ROOT, path, "{")
    assert (unparsable.returncode, unparsable.stdout, unparsable.stderr) == (0, "", "")


@needs_sh
@pytest.mark.skipif(shutil.which("mise") is None, reason="mise is not installed")
def test_the_real_guard_run_by_the_hook_command_through_mise_denies_a_read(tmp_path: Path) -> None:
    done = run_hook(ROOT, str(Path(shutil.which("mise") or "").parent), json.dumps(call("Read", file_path=f"{FOLDER}/password")))
    assert done.returncode == 0 and json.loads(done.stdout)["hookSpecificOutput"]["permissionDecision"] == "deny"
