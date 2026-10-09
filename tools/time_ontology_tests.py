#!/usr/bin/env python3
"""Profiles the `check:ontology-catalog` mise task, slowest first.

Run from the repository root: python tools/time_ontology_tests.py [--top N] [--per-file]

Default: runs the task's own pytest command once, with its own flags (so the same xdist
workers and `--dist loadfile` scheduling), plus a JUnit report, and prints the wall time, the
slowest files and the slowest tests. This is the shape of a real run, so a tail made of a few
big files shows up here.

--per-file: runs each test file in its own process, one after another. Import-time ontology
parsing is counted against the file that pays it, and the sum exceeds a real run. Use it to
find which file hangs, since a single run reports nothing until it ends.
"""

import argparse
import collections
import re
import shlex
import subprocess
import sys
import tempfile
import time
import tomllib
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TASK = "check:ontology-catalog"

parser = argparse.ArgumentParser()
parser.add_argument("--top", type=int, default=15, help="slowest tests and files to show")
parser.add_argument("--per-file", action="store_true", help="one process per file instead of one real run")
parser.add_argument("--timeout", type=int, default=1800, help="seconds before a run, or a file with --per-file, is reported as hung and killed")
args = parser.parse_args()

run = tomllib.loads((ROOT / "mise.toml").read_text())["tasks"][TASK]["run"]
pytest_part, *rest = [p.strip() for p in run.split("&&")]
tokens = shlex.split(pytest_part)
files = [t for t in tokens if t.endswith(".py")]
python_flags = [t for t in tokens[3:] if not t.endswith(".py")]  # drop `python -m pytest`


def timed(cmd):
    """(seconds, completed process or None when it hung, stdout so far)."""
    start = time.perf_counter()
    try:
        proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=args.timeout)
        return time.perf_counter() - start, proc, proc.stdout
    except subprocess.TimeoutExpired as hung:
        # a reasoner call can block on a network fetch with no timeout of its own (TD-31)
        return float(args.timeout), None, (hung.stdout or b"").decode(errors="replace")


def last_summary(stdout):
    return next((l.strip() for l in reversed(stdout.splitlines()) if re.search(r"\b(passed|failed|error|skipped)", l)), "")


def report_steps(steps):
    for step in steps:
        elapsed, proc, _ = timed(shlex.split(step))
        print(f"{elapsed:7.1f}s  {step}" + ("" if proc and proc.returncode == 0 else "  [FAILED OR HUNG]"), flush=True)


def one_run():
    with tempfile.TemporaryDirectory() as directory:
        junit = Path(directory) / "junit.xml"
        cmd = [sys.executable, "-m", "pytest", *files, *python_flags, "-p", "no:cacheprovider", f"--junitxml={junit}"]
        print(f"Running: pytest {shlex.join(python_flags)} over {len(files)} files", flush=True)
        elapsed, proc, out = timed(cmd)
        print(f"\nWall time {elapsed:.1f}s. {last_summary(out)}")
        if proc is None:
            print("HUNG: no report is written until a run ends. Re-run with --per-file to find the file.")
            return
        cases = ET.parse(junit).getroot().iter("testcase")
        per_file = collections.defaultdict(lambda: [0, 0.0, 0])
        tests = []
        for case in cases:
            name = case.get("classname").replace(".", "/") + ".py"
            time_taken = float(case.get("time"))
            per_file[name][0] += 1
            per_file[name][1] += time_taken
            per_file[name][2] += case.find("skipped") is not None
            tests.append((time_taken, f"{name}::{case.get('name')}"))
        total = sum(v[1] for v in per_file.values())
        print(f"\nSlowest files (sum of test times {total:.1f}s, across all workers)\n")
        for name, (count, seconds, skipped) in sorted(per_file.items(), key=lambda kv: -kv[1][1])[: args.top]:
            print(f"{seconds:8.1f}s {100 * seconds / total:5.1f}%  {count:4d} tests  {skipped:3d} skipped  {name}")
        print(f"\nSlowest tests\n")
        for seconds, name in sorted(tests, reverse=True)[: args.top]:
            print(f"{seconds:8.2f}s  {name}")
    report_steps(rest)


def per_file():
    results = []
    for f in files:
        cmd = [sys.executable, "-m", "pytest", f, "-q", "-p", "no:cacheprovider", f"--durations={min(args.top, 5)}"]
        elapsed, proc, out = timed(cmd)
        results.append((elapsed, f, "HUNG" if proc is None else proc.returncode, last_summary(out), out))
        print(f"{elapsed:7.1f}s  {f}" + ("  HUNG" if proc is None else ""), flush=True)
    for step in rest:
        elapsed, proc, _ = timed(shlex.split(step))
        results.append((elapsed, step, "HUNG" if proc is None else proc.returncode, "", ""))
        print(f"{elapsed:7.1f}s  {step}", flush=True)
    results.sort(key=lambda r: r[0], reverse=True)
    total = sum(r[0] for r in results)
    print(f"\nSlowest first (sum of separate runs {total:.1f}s)\n")
    for elapsed, name, code, summary, _ in results:
        flag = "" if code == 0 else f"  [{code}]"
        print(f"{elapsed:7.1f}s {100 * elapsed / total:5.1f}%  {name}{flag}  {summary}")
    print("\nSlowest tests inside the three slowest files\n")
    for _, name, _, _, out in results[:3]:
        print(name)
        for l in out.splitlines():
            if re.match(r"\s*[\d.]+s (call|setup|teardown)", l):
                print(f"  {l.strip()}")


per_file() if args.per_file else one_run()
