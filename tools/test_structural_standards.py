# SPDX-License-Identifier: MPL-2.0
"""Checks for two standards that hold across the repository, STD-003 and STD-025, and for ADR-A124's rule that a
benchmark is never part of ``check``.

STD-003: a derived file has one source, so nothing a build writes into ``.build`` is tracked, apart
from the placeholders that keep its directories in a fresh checkout. A derived file committed so a
consumer can fetch it by its GitHub URL, such as an extracted Turtle document, is held instead by the
check that regenerates it and fails on a difference.

STD-025: text a tool writes takes an explicit encoding and newline, never the platform's, so a file
generated on Windows matches one generated elsewhere. This checks ``Path.write_text`` in the tools'
own code, not their tests, which write only to temporary directories.
"""

from __future__ import annotations

import ast
import json
import subprocess
import tomllib

import lattice_repo_catalogue

ROOT = lattice_repo_catalogue.find_root()


def tracked(*pathspecs: str) -> list[str]:
    return subprocess.run(["git", "-C", str(ROOT), "ls-files", "--", *pathspecs],
                          capture_output=True, text=True, encoding="utf-8", check=True).stdout.splitlines()


def test_nothing_a_build_writes_is_tracked():
    assert [p for p in tracked(".build") if not p.endswith("/.gitkeep")] == []


def unpinned_writes(source: str) -> list[int]:
    """The line of every ``write_text`` call in ``source`` that leaves its encoding or newline to the platform."""
    lines = []
    for node in ast.walk(ast.parse(source)):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "write_text"
                and node.args and not {"encoding", "newline"} <= {k.arg for k in node.keywords}):
            lines.append(node.lineno)
    return lines


def test_a_write_without_an_encoding_or_a_newline_is_found():
    assert unpinned_writes('p.write_text("x")\np.write_text("x", encoding="utf-8")\n') == [1, 2]
    assert unpinned_writes('p.write_text("x", encoding="utf-8", newline="\\n")\n') == []


def test_every_tool_writes_text_with_an_explicit_encoding_and_newline():
    found = []
    for path in tracked("tools/*.py"):
        name = path.rsplit("/", 1)[-1]
        if name.startswith("test_") or name == "conftest.py":
            continue
        found += [f"{path}:{line}" for line in unpinned_writes((ROOT / path).read_text(encoding="utf-8"))]
    assert found == []


def reached(tasks: dict, name: str, seen: set[str] | None = None) -> set[str]:
    """The task and every task it depends on, however far."""
    seen = set() if seen is None else seen
    if name in tasks and name not in seen:
        seen.add(name)
        for dependency in tasks[name].get("depends", []) or []:
            reached(tasks, dependency if isinstance(dependency, str) else dependency[0], seen)
    return seen


def benchmarks_reached(tasks: dict, entry: str) -> list[str]:
    """The tasks ``entry`` reaches that run something under ``benchmark/``. A description may name the folder."""
    def runs(name: str) -> bool:
        return "benchmark/" in json.dumps({k: v for k, v in tasks[name].items() if k != "description"}, default=str)
    return sorted(name for name in reached(tasks, entry) if runs(name))


def test_a_benchmark_reached_from_a_task_is_found():
    tasks = {"check": {"depends": ["check:a"]}, "check:a": {"depends": ["check:b"], "run": "python tools/a.py"},
             "check:b": {"run": "python benchmark/b/check.py", "description": "measures"},
             "check:c": {"run": "python tools/c.py", "description": "never benchmark/ itself"}}
    assert benchmarks_reached(tasks, "check") == ["check:b"]
    assert benchmarks_reached(tasks, "check:c") == []


def test_no_benchmark_is_reached_from_check_or_test():
    tasks = tomllib.loads((ROOT / "mise.toml").read_text(encoding="utf-8"))["tasks"]
    assert any("benchmark/" in json.dumps(task, default=str) for task in tasks.values())
    assert benchmarks_reached(tasks, "check") == []
    assert benchmarks_reached(tasks, "test") == []

