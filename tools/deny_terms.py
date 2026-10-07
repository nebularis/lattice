#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Check text about to be committed against a personal deny-list (ADR-A117, skill
lattice-publication-hygiene).

The list is never published. It is read from the first of these that exists, and the check
passes when none does:

  1. the file named by LATTICE_DENY_TERMS
  2. ${XDG_CONFIG_HOME:-~/.config}/lattice/deny-terms   (macOS, Linux)
  3. %APPDATA%\\lattice\\deny-terms                        (Windows)

One case-insensitive regular expression per line, '#' for comments. A line starting '!' names a
path glob to skip. A finding names the file, the line and the entry's line number, never the
pattern, so a shared log does not repeat it.

  python tools/deny_terms.py                 the lines staged for commit
  python tools/deny_terms.py --all           every tracked file
  python tools/deny_terms.py install-hook    an opt-in git pre-commit hook

Standard library only.
"""

from __future__ import annotations

import argparse
import fnmatch
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOOK_MARK = "# lattice deny-terms hook"


def list_path() -> Path | None:
    candidates = []
    if os.environ.get("LATTICE_DENY_TERMS"):
        candidates.append(Path(os.environ["LATTICE_DENY_TERMS"]).expanduser())
    if os.name == "nt":
        if os.environ.get("APPDATA"):
            candidates.append(Path(os.environ["APPDATA"]) / "lattice" / "deny-terms")
    else:
        base = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
        candidates.append(Path(base) / "lattice" / "deny-terms")
    return next((p for p in candidates if p.is_file()), None)


def load(path: Path) -> tuple[list[tuple[int, re.Pattern]], list[str]]:
    patterns, skips = [], []
    for number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("!"):
            skips.append(line[1:].strip())
        else:
            patterns.append((number, re.compile(line, re.IGNORECASE)))
    return patterns, skips


def git(*args: str, cwd: Path) -> str:
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=True,
                          encoding="utf-8", errors="replace").stdout


def staged_lines(cwd: Path):
    """(path, line number, text) for every line the index adds."""
    path, number = None, 0
    for line in git("diff", "--cached", "-U0", "--no-color", "--no-ext-diff", cwd=cwd).splitlines():
        if line.startswith("+++ "):
            path = None if line[4:] == "/dev/null" else line[6:]
        elif line.startswith("@@"):
            number = int(re.search(r"\+(\d+)", line).group(1))
        elif line.startswith("+") and path:
            yield path, number, line[1:]
            number += 1


def tracked_lines(cwd: Path):
    for path in git("ls-files", "-z", cwd=cwd).split("\0"):
        if not path or not (cwd / path).is_file():
            continue
        try:
            text = (cwd / path).read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for number, line in enumerate(text.splitlines(), 1):
            yield path, number, line


def findings(lines, patterns, skips) -> list[str]:
    found = []
    for path, number, text in lines:
        if any(fnmatch.fnmatch(path, glob) for glob in skips):
            continue
        for entry, pattern in patterns:
            if pattern.search(text):
                found.append(f"{path}:{number}: matches deny-list entry {entry}")
    return found


def install_hook(cwd: Path) -> str:
    hooks = Path(git("rev-parse", "--git-path", "hooks", cwd=cwd).strip())
    hook = (cwd / hooks / "pre-commit") if not hooks.is_absolute() else hooks / "pre-commit"
    if hook.exists() and HOOK_MARK not in hook.read_text(encoding="utf-8", errors="replace"):
        raise SystemExit(f"{hook} exists and was not installed by this task. Add the check to it by hand.")
    hook.parent.mkdir(parents=True, exist_ok=True)
    hook.write_text(f"#!/bin/sh\n{HOOK_MARK}\n"
                    "command -v python3 >/dev/null 2>&1 && exec python3 tools/deny_terms.py\n"
                    "exec python tools/deny_terms.py\n", encoding="utf-8")
    hook.chmod(0o755)
    return str(hook)


def main(argv: list[str] | None = None, cwd: Path = ROOT) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("command", nargs="?", choices=["check", "install-hook"], default="check")
    parser.add_argument("--all", action="store_true", help="scan every tracked file, not only staged lines")
    args = parser.parse_args(argv)
    if args.command == "install-hook":
        print(f"installed {install_hook(cwd)}")
        return 0
    path = list_path()
    if path is None:
        print("deny terms: no personal list, nothing to check")
        return 0
    patterns, skips = load(path)
    found = findings(tracked_lines(cwd) if args.all else staged_lines(cwd), patterns, skips)
    for finding in found:
        print(finding)
    print(f"deny terms: {len(found)} finding(s) against {len(patterns)} entr{'y' if len(patterns) == 1 else 'ies'}")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
