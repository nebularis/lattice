#!/usr/bin/env python3
"""Times each step of the `check:ontology-catalog` mise task separately, slowest first.

Run from anywhere: python .local/time_ontology_tests.py [--top N]
Each test file runs in its own pytest process, so import-time ontology parsing is counted
against the file that pays it. The sum therefore exceeds the single-process task time.
"""

import argparse
import re
import shlex
import subprocess
import sys
import time
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TASK = "check:ontology-catalog"

parser = argparse.ArgumentParser()
parser.add_argument("--top", type=int, default=3, help="slowest tests to show for each of the slowest files")
args = parser.parse_args()

run = tomllib.loads((ROOT / "mise.toml").read_text())["tasks"][TASK]["run"]
pytest_part, *rest = [p.strip() for p in run.split("&&")]
files = [t for t in shlex.split(pytest_part) if t.endswith(".py")]

results = []
for f in files:
    cmd = [sys.executable, "-m", "pytest", f, "-q", "-p", "no:cacheprovider", f"--durations={args.top}"]
    start = time.perf_counter()
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    elapsed = time.perf_counter() - start
    summary = next((l for l in reversed(proc.stdout.splitlines()) if re.search(r"\b(passed|failed|error|skipped)", l)), "")
    results.append((elapsed, f, proc.returncode, summary.strip(), proc.stdout))
    print(f"{elapsed:7.1f}s  {f}", flush=True)

for step in rest:
    start = time.perf_counter()
    proc = subprocess.run(shlex.split(step), cwd=ROOT, capture_output=True, text=True)
    elapsed = time.perf_counter() - start
    results.append((elapsed, step, proc.returncode, "", ""))
    print(f"{elapsed:7.1f}s  {step}", flush=True)

results.sort(key=lambda r: r[0], reverse=True)
total = sum(r[0] for r in results)

print(f"\nSlowest first (sum of separate runs {total:.1f}s)\n")
for elapsed, name, code, summary, _ in results:
    flag = "" if code == 0 else f"  [exit {code}]"
    print(f"{elapsed:7.1f}s {100 * elapsed / total:5.1f}%  {name}{flag}  {summary}")

print("\nSlowest tests inside the three slowest files\n")
for elapsed, name, _, _, out in results[:3]:
    lines = [l for l in out.splitlines() if re.match(r"\s*[\d.]+s (call|setup|teardown)", l)]
    print(f"{name}")
    for l in lines:
        print(f"  {l.strip()}")
