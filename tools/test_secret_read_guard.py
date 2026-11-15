# SPDX-License-Identifier: MPL-2.0
"""Tests the hook that refuses a tool call which would read the studio stack's secrets (`secret_read_guard.py`)."""

from __future__ import annotations

import io
import json
import subprocess
import sys
from pathlib import Path
from typing import Dict, Optional

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lattice_repo_catalogue  # noqa: E402
import secret_read_guard as guard  # noqa: E402

ROOT = str(lattice_repo_catalogue.find_root())
FOLDER = ".build/config-studio/infra/broker"
SECRET = "Zq9-sentinel-secret-value-0123456789abcdef"


def call(tool: str, cwd: Optional[str] = None, **given: str) -> Dict:
    return {"tool_name": tool, "tool_input": given, "cwd": cwd or ROOT}


def run(payload: object, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture, raw: Optional[str] = None) -> tuple:
    monkeypatch.setattr(sys, "stdin", io.StringIO(raw if raw is not None else json.dumps(payload)))
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", ROOT)
    status = guard.main()
    seen = capsys.readouterr()
    assert seen.out == "", "the guard prints nothing on standard output"
    return status, seen.err


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


@pytest.mark.parametrize("command", READS)
def test_each_way_of_reading_the_secrets_from_the_shell_is_refused(command: str, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture) -> None:
    for tool in ("Bash", "PowerShell"):
        status, err = run(call(tool, command=command), monkeypatch, capsys)
        assert status == 2, (tool, command)
        assert err.count("\n") == 1 and "mise run studio:config" in err


def test_a_command_run_from_inside_the_stacks_folders_is_refused_by_its_working_directory(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture) -> None:
    assert run(call("Bash", cwd=f"{ROOT}/.build/config-studio/infra", command="cat broker/password"), monkeypatch, capsys)[0] == 2
    assert run(call("Bash", cwd=f"{ROOT}/{FOLDER}", command="cat password ../broker/amqp-uri"), monkeypatch, capsys)[0] == 2
    assert run(call("Bash", cwd=f"{ROOT}/tools", command="cat ../.build/config-studio/infra/broker/secret"), monkeypatch, capsys)[0] == 2


@pytest.mark.parametrize("path", [f"{ROOT}/{FOLDER}/password", f"{FOLDER}/amqp-uri", f"./{FOLDER}/secret", f"{ROOT}/.build/config-studio/infra/x/../broker/stream-uri",
                                  f"{ROOT}/.build/config-studio/infra/broker/rabbitmq-secret.conf", f"{ROOT}\\.build\\config-studio\\infra\\broker\\password"])
def test_a_read_of_a_file_in_the_folder_is_refused(path: str, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture) -> None:
    status, err = run(call("Read", file_path=path), monkeypatch, capsys)
    assert status == 2 and "mise run studio:config" in err


@pytest.mark.parametrize("given", [
    {"pattern": "default_pass", "path": f"{ROOT}/{FOLDER}"},
    {"pattern": "x", "path": FOLDER},
    {"pattern": "x", "path": ".build/config-studio/infra/../infra/broker"},
    {"pattern": "x", "glob": "**/infra/broker/*"},
    {"pattern": "infra/broker/password"},
    {"pattern": "x", "path": ".build/config-studio"},
    {"pattern": "x", "path": f"{ROOT}/.build"},
])
def test_a_search_of_the_folder_or_a_folder_that_holds_it_is_refused(given: Dict[str, str], monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture) -> None:
    assert run(call("Grep", **given), monkeypatch, capsys)[0] == 2


@pytest.mark.parametrize("given", [{"pattern": f"{FOLDER}/*"}, {"pattern": "*", "path": FOLDER}, {"pattern": "**/broker/**"}, {"pattern": "password", "path": f"{ROOT}/{FOLDER}"}])
def test_a_glob_of_the_folder_is_refused(given: Dict[str, str], monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture) -> None:
    assert run(call("Glob", **given), monkeypatch, capsys)[0] == 2


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
    assert run(call("Bash", command=command), monkeypatch, capsys) == (0, "")


def test_an_unrelated_call_passes(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture) -> None:
    for payload in (call("Read", file_path=f"{ROOT}/mise.toml"), call("Grep", pattern="def main", path="tools"), call("Glob", pattern="tools/*.py"),
                    call("Edit", file_path=f"{ROOT}/{FOLDER}/password", old_string="a", new_string="b"), call("Bash", command=""),
                    call("Bash", command="python -m pytest tools -q"), {"tool_name": "Read"}, {"tool_input": []}):
        assert run(payload, monkeypatch, capsys) == (0, "")


@pytest.mark.parametrize("raw", ["", "not json", "[1, 2]", "null", '{"tool_name": "Bash", "tool_input": "cat x"}', '{"tool_name": 7, "tool_input": {"command": 5}}', '{"tool_name": "Bash"'])
def test_input_the_guard_cannot_parse_passes(raw: str, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture) -> None:
    assert run(None, monkeypatch, capsys, raw=raw) == (0, "")


def test_a_fault_inside_the_guard_passes(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture) -> None:
    monkeypatch.setattr(guard, "refusal", lambda payload: 1 / 0)
    assert run(call("Bash", command=f"cat {FOLDER}/password"), monkeypatch, capsys) == (0, "")


def test_the_refusal_holds_no_part_of_the_call(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture) -> None:
    status, err = run(call("Bash", command=f"echo {SECRET}; cat {FOLDER}/password"), monkeypatch, capsys)
    assert status == 2 and SECRET not in err and "password" not in err.replace("stack's secrets", "")
    assert run(call("Read", file_path=f"{FOLDER}/{SECRET}"), monkeypatch, capsys)[1].count(SECRET) == 0


def test_the_variables_are_read_from_mise_toml(tmp_path: Path) -> None:
    (tmp_path / "mise.toml").write_text('env = { OTHER_KEY_FILE = ".build/config-studio/infra/broker/x", UNRELATED = "y" }\n', encoding="utf-8")
    names = guard.variables(str(tmp_path))
    assert "OTHER_KEY_FILE" in names and "UNRELATED" not in names and "LATTICE_AMQP_URI_FILE" in names
    assert "LATTICE_AMQP_URI_FILE" in guard.variables(str(tmp_path / "missing"))
    real = guard.variables(ROOT)
    assert {"LATTICE_AMQP_URI_FILE", "LATTICE_STREAM_URI_FILE", "LATTICE_STUDIO_BROKER_SECRET_FILE"} <= set(real)


def test_the_hook_exits_2_with_one_line_as_a_process_and_0_otherwise() -> None:
    script = str(Path(guard.__file__))
    env = {"CLAUDE_PROJECT_DIR": ROOT, "PATH": ""}
    refused = subprocess.run([sys.executable, script], input=json.dumps(call("Read", file_path=f"{FOLDER}/password")), capture_output=True, text=True, env=env)
    assert refused.returncode == 2 and refused.stdout == "" and refused.stderr.count("\n") == 1 and "studio:config" in refused.stderr
    passed = subprocess.run([sys.executable, script], input=json.dumps(call("Bash", command="ls")), capture_output=True, text=True, env=env)
    assert (passed.returncode, passed.stdout, passed.stderr) == (0, "", "")
    assert subprocess.run([sys.executable, script], input="{", capture_output=True, text=True, env=env).returncode == 0
