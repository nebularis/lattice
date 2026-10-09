#!/usr/bin/env python3
"""Runs every check an ontology change needs, one after another, and prints one line per check.

Run from the repository root: python tools/full_sweep.py [--base-ref REF]

Each check's full output goes to .build/full-sweep/<check>.log. A failed check is printed in red
with its failing tests, or the end of its output when it ran no tests. The tool packages are this
checkout's: their source directories go first on PYTHONPATH, since an editable install can point at
another clone (skill lattice-toolchain). Colour follows NO_COLOR and FORCE_COLOR, and is off when
the output is not a terminal. Exits non-zero when any check fails.
"""

import argparse
import os
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOGS = ROOT / ".build" / "full-sweep"

# (label, command). Versions are compared with --base-ref, not HEAD, so a branch with several
# commits to one unreleased version still passes.
CHECKS = [
    ("ontology versions", ["python", "tools/ontology_version_check.py", "--base-ref", "{base}"]),
    ("release register", ["python", "tools/ontology_releases.py", "check"]),
    *[(task, ["mise", "run", task]) for task in (
        "check:import-guard", "check:python-root", "check:deny-terms", "check:vocabulary",
        "check:mork-compilers", "check:reference-eligibility", "check:formal-freshness", "build:mtp",
        "check:mtp", "check:persistence", "check:agent-guidance", "check:ontology-catalog")],
]

ANSI = re.compile(r"\x1b\[[0-9;]*m")
SUMMARY = re.compile(r"^=*\s*((?:\d+ (?:passed|failed|skipped|errors?|xfailed|xpassed|deselected)(?:, )?)+)"
                     r"(?:, \d+ warnings?)? in [\d.]+s")
FAILED = re.compile(r"^(?:FAILED|ERROR) (\S+)")


def colours(stream) -> tuple[str, str, str, str]:
    """(red, green, dim, reset), empty when colour is off."""
    on = os.environ.get("FORCE_COLOR") or (stream.isatty() and not os.environ.get("NO_COLOR"))
    if on and os.name == "nt":
        os.system("")  # turns on ANSI escape handling in a Windows console
    return ("\x1b[31m", "\x1b[32m", "\x1b[2m", "\x1b[0m") if on else ("", "", "", "")


def outcome(output: str) -> tuple[str, list[str]]:
    """The last pytest summary (counts only) and every failing test id, from a check's output."""
    lines = [ANSI.sub("", line) for line in output.splitlines()]
    summaries = [m.group(1).rstrip(", ") for line in lines if (m := SUMMARY.match(line.strip()))]
    failed = [m.group(1) for line in lines if (m := FAILED.match(line))]
    return (summaries[-1] if summaries else ""), list(dict.fromkeys(failed))


def local_pythonpath() -> str:
    sources = sorted([*ROOT.glob("tools/*/src"), *ROOT.glob("tools/reference/*/src"), *ROOT.glob("packages/*/python/src")])
    return os.pathsep.join([*map(str, sources), *filter(None, [os.environ.get("PYTHONPATH")])])


def duration(seconds: float) -> str:
    return f"{int(seconds)}s" if seconds < 60 else f"{int(seconds) // 60}m {int(seconds) % 60:02d}s"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-ref", default="main", help="the ref ontology versions are compared with (default: main)")
    args = parser.parse_args()

    red, green, dim, reset = colours(sys.stdout)
    LOGS.mkdir(parents=True, exist_ok=True)
    env = {**os.environ, "PYTHONPATH": local_pythonpath()}
    width = max(len(label) for label, _ in CHECKS)
    print(f"Full sweep of {ROOT}, versions against {args.base_ref}, logs in {LOGS.relative_to(ROOT)}")
    print()

    failures, started = 0, time.monotonic()
    for label, command in CHECKS:
        command = [part.replace("{base}", args.base_ref) for part in command]
        log = LOGS / (re.sub(r"[^A-Za-z0-9]+", "-", label).strip("-") + ".log")
        start = time.monotonic()
        result = subprocess.run(command, cwd=ROOT, env=env, capture_output=True, text=True,
                                encoding="utf-8", errors="replace")
        output = result.stdout + result.stderr
        log.write_text(output, encoding="utf-8")
        counts, failed = outcome(output)
        passed = result.returncode == 0
        failures += not passed
        mark = f"{green}PASS{reset}" if passed else f"{red}FAIL{reset}"
        detail = counts or ("" if passed else f"exit {result.returncode}")
        print(f"  {mark}  {label:<{width}}  {'' if passed else red}{detail:<30}{reset}"
              f"  {dim}{duration(time.monotonic() - start)}{reset}", flush=True)
        if not passed:
            tail = failed or [line for line in ANSI.sub("", output).splitlines() if line.strip()][-5:]
            for line in tail:
                print(f"        {red}{line}{reset}")
            print(f"        {dim}log: {log.relative_to(ROOT)}{reset}")

    print()
    total = duration(time.monotonic() - started)
    if failures:
        print(f"{red}{failures} of {len(CHECKS)} checks failed{reset} ({total})")
    else:
        print(f"{green}All {len(CHECKS)} checks passed{reset} ({total})")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
