# SPDX-License-Identifier: MPL-2.0
"""tools/portability.py: tasks that run the same under cmd.exe and a POSIX shell, text with an encoding, and no skip by
platform (STD-322, STD-323)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import portability  # noqa: E402
from lattice_repo_catalogue import find_root  # noqa: E402


def test_the_repository_passes() -> None:
    assert portability.check(find_root()) == []


@pytest.mark.parametrize("run, said", [
    ("set -e\nrm -rf x\n", "multi-line"),
    ("rm -rf build/", "`rm`"),
    ("cd docs && bundle exec jekyll serve", "cd"),
    ("python a.py && python b.py", "&&"),
    ("python a.py; python b.py", "a semicolon"),
    ("python a.py | tee log", "a pipe"),
    ("python a.py > log", "a redirect"),
    ("python -m pytest tools/test_*.py", "a glob"),
    ("python a.py --out \"$t/x\"", "a variable"),
])
def test_a_shell_feature_in_a_run_is_refused(run: str, said: str) -> None:
    problems = portability.task_problems({"t": {"run": run}})
    assert len(problems) == 1 and said in problems[0], problems


def test_plain_commands_a_run_array_and_a_template_pass() -> None:
    tasks = {
        "a": {"run": "python -m pytest workers/tests -q -n auto --dist worksteal"},
        "b": {"run": ["corepack enable", "yarn install --immutable"]},
        "c": {"run": ["mvn -q dependency:copy -DoutputDirectory={{config_root}}/platform/target/tools"], "dir": "{{config_root}}/docs"},
        "d": {"run": [{"tasks": ["a", "b"]}]},
        "e": {"run": "python -m pip install -e \"./workers[test,authoring]\""},
    }
    assert portability.task_problems(tasks) == []


def test_a_windows_variant_is_refused_unless_listed_with_its_reason() -> None:
    assert portability.task_problems({"clean": {"run": "python tools/clean.py build", "run_windows": "powershell x"}})
    listed = next(iter(portability.WINDOWS_VARIANTS))
    assert portability.task_problems({listed: {"run": "python x.py", "run_windows": "powershell -File x.ps1"}}) == []


def test_text_without_an_encoding_is_counted_and_bytes_are_not() -> None:
    source = "\n".join([
        "from pathlib import Path",
        "import subprocess",
        "p = Path('x')",
        "p.read_text()",                                   # 4
        "p.write_text('x', encoding='utf-8')",
        "p.write_text('x')",                               # 6
        "open('x')",                                       # 7
        "open('x', 'rb')",
        "open('x', mode='wb')",
        "open('x', encoding='utf-8')",
        "subprocess.run(['x'], text=True)",                # 11
        "subprocess.run(['x'], text=True, encoding='utf-8')",
        "subprocess.run(['x'], capture_output=True)",
        "subprocess.check_output(['x'], universal_newlines=True)",  # 14
    ])
    assert portability.unencoded(source) == [4, 6, 7, 11, 14]


def test_a_skip_on_the_platform_is_found_and_a_skip_for_a_package_is_not() -> None:
    source = "\n".join([
        "import os, sys, platform, pytest",
        "@pytest.mark.skipif(os.name == 'nt', reason='x')",
        "def test_a(): pass",
        "@pytest.mark.skipif(sys.platform.startswith('win'), reason='x')",
        "def test_b(): pass",
        "@pytest.mark.skipif(platform.system() == 'Darwin', reason='x')",
        "def test_c(): pass",
        "@pytest.mark.skipif(not HAVE_JAR, reason='x')",
        "def test_d(): pass",
        "@pytest.mark.requires('anthropic')",
        "def test_e(): pass",
    ])
    assert portability.platform_skips(source) == [2, 4, 6]


def test_the_baseline_only_goes_down(tmp_path: Path) -> None:
    baseline = {"tools/a.py": 3, "tools/b.py": 1}
    assert portability.encoding_problems({"tools/a.py": 3, "tools/b.py": 1}, baseline) == []
    assert any("4 text" in p for p in portability.encoding_problems({"tools/a.py": 4, "tools/b.py": 1}, baseline))
    assert any("tools/c.py: 1 text" in p for p in portability.encoding_problems({"tools/a.py": 3, "tools/b.py": 1, "tools/c.py": 1}, baseline))
    assert any("down to 2 from 3" in p for p in portability.encoding_problems({"tools/a.py": 2, "tools/b.py": 1}, baseline))
    path = tmp_path / portability.BASELINE
    portability.write_baseline(path, {"tools/a.py": 2, "tools/z.py": 0})
    assert portability.read_baseline(path) == {"tools/a.py": 2}
    assert b"\r\n" not in path.read_bytes()
