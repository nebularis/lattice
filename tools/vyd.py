"""Run Вивід, `vyd`, from a `mise` task or a hook (ADR-A152 decisions 3 and 4, plan vyvid-migration, VM-2).

Where `vyd` is not installed, or exits 2 to say it did not run, the caller gets a note naming what was skipped and
how to mend it, and exit 0, since an absent tool skips and never blocks (PRI-79). Any other exit code is `vyd`'s own.
`mise run vyd -- <args>` passes anything through, and `graph:ask`, `build:knowledge` and `check:identifiers` run here."""

from __future__ import annotations

import shutil
import subprocess
import sys

MEND = "Run `mise run bootstrap` to install it, or `vyd trust` in the checkout where it asks for that"


def run(args: list[str], cwd: str | None = None) -> tuple[int, str, bool]:
    """vyd's exit code and output, and whether the command was skipped rather than run."""
    command = "vyd " + " ".join(args)
    found = shutil.which("vyd")
    if found is None:
        return 0, f"vyd is not installed, so `{command}` was skipped. {MEND}\n", True
    # The program found is the one run, which on Windows may be a launcher PATHEXT names, such as vyd.cmd.
    result = subprocess.run([found, *args], cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    output = result.stdout + result.stderr
    if result.returncode == 2:
        return 0, f"{output}`{command}` did not run, so it was skipped. {MEND}\n", True
    return result.returncode, output, False


def main(argv: list[str]) -> int:
    code, output, _ = run(argv)
    print(output, end="")
    return code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
