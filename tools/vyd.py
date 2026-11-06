"""Run Вивід, `vyd`, from a `mise` task or a hook (ADR-A152 decisions 3 and 4, plan vyvid-migration, VM-2).

Where `vyd` is not installed, or exits 2 to say it did not run, the caller gets a note naming what was skipped and
how to mend it, and exit 0, since an absent tool skips and never blocks (PRI-79). Any other exit code is `vyd`'s own.
`mise run vyd -- <args>` passes anything through, and `graph:ask`, `build:knowledge` and `check:identifiers` run here.

A task runs `vyd` on this process's own streams, so a question `vyd` asks, such as `vyd trust`'s, reaches the person
and their answer reaches `vyd`. A hook calls `run`, which captures the output to judge it. Either way `vyd` writes UTF-8,
since on Windows Python otherwise writes redirected output in the ANSI code page, which cannot hold the name Вивід."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys

MEND = "Run `mise run bootstrap` to install it, or `vyd trust` in the checkout where it asks for that"


def environment() -> dict[str, str]:
    """This process's environment, with Python's UTF-8 mode on for `vyd` unless the caller set it."""
    return {**os.environ, "PYTHONUTF8": os.environ.get("PYTHONUTF8", "1")}


def missing(command: str) -> str:
    return f"vyd is not installed, so `{command}` was skipped. {MEND}\n"


def did_not_run(command: str) -> str:
    return f"`{command}` did not run, so it was skipped. {MEND}\n"


def run(args: list[str], cwd: str | None = None) -> tuple[int, str, bool]:
    """vyd's exit code and captured output, and whether the command was skipped rather than run."""
    command = "vyd " + " ".join(args)
    if shutil.which("vyd") is None:
        return 0, missing(command), True
    result = subprocess.run(["vyd", *args], cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace",
                            env=environment())
    output = result.stdout + result.stderr
    if result.returncode == 2:
        return 0, output + did_not_run(command), True
    return result.returncode, output, False


def main(argv: list[str]) -> int:
    """Run `vyd` with this process's standard input, output and error, so it can ask a question and be answered."""
    command = "vyd " + " ".join(argv)
    if shutil.which("vyd") is None:
        print(missing(command), end="")
        return 0
    code = subprocess.run(["vyd", *argv], env=environment()).returncode
    if code == 2:
        print(did_not_run(command), end="")
        return 0
    return code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
