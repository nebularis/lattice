#!/usr/bin/env python3
"""The portability check (STD-322, STD-323): what keeps `mise` tasks and tests the same on Windows, Linux and macOS.

1. A task in `mise.toml` runs plain commands: no multi-line script, variable, pipe, redirect, glob, `&&`, `||`, `;`,
   `cd` or POSIX-only command such as `rm` or `find`, since `cmd.exe` runs none of them, or only the first line of a
   script, and still reports success. A sequence is a `run` array and a folder is `dir`. Anything more is a Python
   script under `tools/`. `run_windows` and `shell` are allowed only for the tasks in WINDOWS_VARIANTS, with a reason.
2. Python under the scanned folders gives every text read and write, and every subprocess call that uses text, an
   encoding, since Windows otherwise decodes with the console's code page. The calls that predate this check are
   counted per file in `tools/portability-baseline.txt`, and a file may only go down. `--lower-baseline` writes the
   lower counts, and never adds a file or raises a count.
3. A test never skips on the platform: a `skipif` on `os.name`, `sys.platform` or `platform.system()`. A test that
   needs a package says so with `@pytest.mark.requires` (CAP-107)."""

from __future__ import annotations

import argparse
import ast
import re
import sys
import tomllib
import warnings
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lattice_repo_catalogue as rc  # noqa: E402

BASELINE = "portability-baseline.txt"
SCANNED = ("tools", "workers", "packages", "benchmark")
NOT_WALKED = {".venv", "node_modules", ".git", "build", ".build", "target", "__pycache__"}

# The tasks allowed a Windows variant, each with why it has no portable form.
WINDOWS_VARIANTS = {
    "bootstrap:formal-native-rocq": "installs an opam switch and Rocq, a platform's own toolchain, through its PowerShell installer",
    "bootstrap:formal-native-isabelle": "installs Isabelle, a platform's own toolchain, through its PowerShell installer",
}

POSIX_COMMANDS = {"rm", "find", "sed", "grep", "awk", "cp", "mv", "mkdir", "cat", "true", "false", "test", "[",
                  "basename", "dirname", "touch", "ln", "chmod", "export", "set", "mktemp", "rmdir"}
SHELL_FEATURES = [
    ("a variable", re.compile(r"\$[A-Za-z_({]")),
    ("a pipe", re.compile(r"(?<!\|)\|(?!\|)")),
    ("a redirect", re.compile(r"(?:^|\s)\d?[<>]{1,2}")),
    ("a glob", re.compile(r"(?:^|\s)[^\s\"'=]*[*?][^\s\"']*")),
    ("&&", re.compile(r"&&")),
    ("||", re.compile(r"\|\|")),
    ("a semicolon", re.compile(r";")),
    ("a backtick", re.compile(r"`")),
]


def task_problems(tasks: dict) -> list[str]:
    """What in each task's `run` would not run the same under `cmd.exe` and a POSIX shell."""
    problems = []
    for name, task in tasks.items():
        for key in ("run_windows", "shell"):
            if key in task and name not in WINDOWS_VARIANTS:
                problems.append(f"mise.toml: {name} sets {key}. Run a Python script on every platform instead (STD-322)")
        runs = task.get("run", [])
        for command in [runs] if isinstance(runs, str) else [r for r in runs if isinstance(r, str)]:
            text = command.strip()
            if "\n" in text:
                problems.append(f"mise.toml: {name} runs a multi-line script, which cmd.exe runs only the first line of")
                continue
            found = [what for what, pattern in SHELL_FEATURES if pattern.search(text)]
            first = text.split()[0] if text.split() else ""
            if first == "cd":
                found.append("cd, where the task should set dir")
            elif first in POSIX_COMMANDS:
                found.append(f"`{first}`, which Windows does not have")
            if found:
                problems.append(f"mise.toml: {name} runs `{text[:80]}` with {', '.join(found)}")
    return problems


def _keyword(call: ast.Call, name: str) -> ast.AST | None:
    return next((k.value for k in call.keywords if k.arg == name), None)


def _is_true(node: ast.AST | None) -> bool:
    return isinstance(node, ast.Constant) and node.value is True


def _parse(source: str) -> ast.AST:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")  # another file's invalid escapes are not this check's to report
        return ast.parse(source)


def unencoded(source: str) -> list[int]:
    """The lines of text reads, text writes and text subprocess calls in ``source`` that name no encoding."""
    lines = []
    for node in ast.walk(_parse(source)):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        name = func.attr if isinstance(func, ast.Attribute) else func.id if isinstance(func, ast.Name) else ""
        if _keyword(node, "encoding") is not None:
            continue
        if name in ("read_text", "write_text"):
            lines.append(node.lineno)
        elif name == "open":
            mode = node.args[1] if len(node.args) > 1 else _keyword(node, "mode")
            if not (isinstance(mode, ast.Constant) and "b" in str(mode.value)):
                lines.append(node.lineno)
        elif name in ("run", "check_output", "Popen") and (_is_true(_keyword(node, "text")) or _is_true(_keyword(node, "universal_newlines"))):
            lines.append(node.lineno)
    return lines


def platform_skips(source: str) -> list[int]:
    """The lines of a `skipif` whose condition reads the platform."""
    lines = []
    for node in ast.walk(_parse(source)):
        if isinstance(node, ast.Call) and getattr(node.func, "attr", "") == "skipif":
            condition = ast.unparse(node.args[0]) if node.args else ""
            if re.search(r"\bos\.name\b|\bsys\.platform\b|\bplatform\.system\(", condition):
                lines.append(node.lineno)
    return lines


def python_files(root: Path, folders: tuple[str, ...]) -> list[Path]:
    found = []
    for folder in folders:
        for path in sorted((root / folder).rglob("*.py")):
            if not NOT_WALKED & set(path.relative_to(root).parts):
                found.append(path)
    return found


def read_baseline(path: Path) -> dict[str, int]:
    if not path.is_file():
        return {}
    counts = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip() and not line.startswith("#"):
            name, _, count = line.rpartition(" ")
            counts[name] = int(count)
    return counts


def write_baseline(path: Path, counts: dict[str, int]) -> None:
    header = ("# Text reads, writes and subprocess calls without an encoding that predate the portability check (STD-322, TD-154).\n"
              "# A file's count may only go down. `python tools/portability.py --lower-baseline` writes the lower counts.\n")
    path.write_text(header + "".join(f"{name} {count}\n" for name, count in sorted(counts.items()) if count),
                    encoding="utf-8", newline="\n")


def encoding_problems(counts: dict[str, int], baseline: dict[str, int]) -> list[str]:
    problems = []
    for name, count in sorted(counts.items()):
        allowed = baseline.get(name, 0)
        if count > allowed:
            problems.append(f"{name}: {count} text read(s), write(s) or subprocess call(s) without an encoding, "
                            f"{allowed} allowed. Name encoding=\"utf-8\" (STD-322)")
    for name, allowed in sorted(baseline.items()):
        if counts.get(name, 0) < allowed:
            problems.append(f"{BASELINE}: {name} is down to {counts.get(name, 0)} from {allowed}. "
                            "Run `python tools/portability.py --lower-baseline`")
    return problems


def check(root: Path, lower: bool = False) -> list[str]:
    problems = task_problems(tomllib.loads((root / "mise.toml").read_text(encoding="utf-8")).get("tasks", {}))
    counts: dict[str, int] = {}
    for path in python_files(root, SCANNED):
        relative = path.relative_to(root).as_posix()
        try:
            source = path.read_text(encoding="utf-8")
            found = unencoded(source)
            skips = platform_skips(source)
        except SyntaxError as error:
            problems.append(f"{relative}: cannot be parsed ({error.msg}, line {error.lineno})")
            continue
        if found:
            counts[relative] = len(found)
        problems += [f"{relative}:{line}: a test skips on the platform. Skip for a missing package instead (STD-323)" for line in skips]
    baseline_path = root / rc.load(root).area("tools") / BASELINE
    baseline = read_baseline(baseline_path)
    if lower:
        write_baseline(baseline_path, {name: min(count, counts.get(name, 0)) for name, count in baseline.items()})
        baseline = read_baseline(baseline_path)
    return problems + encoding_problems(counts, baseline)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--lower-baseline", action="store_true", help="lower each baseline count to what the files hold now")
    args = parser.parse_args(argv)
    problems = check(rc.find_root(), lower=args.lower_baseline)
    for problem in problems:
        print(f"ERROR: {problem}")
    print(f"portability: {len(problems)} problem(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
