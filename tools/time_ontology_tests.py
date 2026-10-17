#!/usr/bin/env python3
"""Profiles the `check:ontology-catalog` mise task, slowest first.

Run from the repository root:
python tools/time_ontology_tests.py [--top N] [--per-file] [--workers N] [--dist MODE]

Default: runs the task's own pytest command once, with its own flags (so the same xdist
workers and `--dist loadfile` scheduling), plus a JUnit report, and prints the wall time, the
slowest files and the slowest tests. This is the shape of a real run, so a tail made of a few
big files shows up here. It also prints when each xdist worker finished and which files it ran,
which shows a run waiting on one worker, and the peak memory of the process tree (macOS and
Linux). `--workers` and `--dist` replace the task's own `-n` and `--dist`, to compare worker
counts and scheduling modes on the machine in front of you, for example
`--workers 4 --dist worksteal`. On a machine with performance and efficiency cores, a late
worker is often one the scheduler put on an efficiency core.

--per-file: runs each test file in its own process, one after another. Import-time ontology
parsing is counted against the file that pays it, and the sum exceeds a real run. Use it to
find which file hangs, since a single run reports nothing until it ends.
"""

import argparse
import collections
import os
import re
import shlex
import subprocess
import sys
import tempfile
import threading
import time
import tomllib
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TASK = "check:ontology-catalog"

parser = argparse.ArgumentParser()
parser.add_argument("--top", type=int, default=15, help="slowest tests and files to show")
parser.add_argument("--per-file", action="store_true", help="one process per file instead of one real run")
parser.add_argument("--workers", help="xdist workers for the run, replacing the task's -n (a number or auto)")
parser.add_argument("--dist", help="xdist scheduling mode for the run, replacing the task's --dist (loadfile, worksteal, load)")
parser.add_argument("--timeout", type=int, default=1800, help="seconds before a run, or a file with --per-file, is reported as hung and killed")
args = parser.parse_args()

run = tomllib.loads((ROOT / "mise.toml").read_text())["tasks"][TASK]["run"]
pytest_part, *rest = [p.strip() for p in run.split("&&")]
tokens = shlex.split(pytest_part)
files = [t for t in tokens if t.endswith(".py")]
python_flags = [t for t in tokens[3:] if not t.endswith(".py")]  # drop `python -m pytest`


def with_option(flags, name, value):
    """`flags` with the option `name` and its value replaced, or added when absent."""
    kept, skip = [], False
    for flag in flags:
        if skip:
            skip = False
        elif flag == name:
            skip = True
        else:
            kept.append(flag)
    return [*kept, name, value]


if args.workers:
    python_flags = with_option(python_flags, "-n", args.workers)
if args.dist:
    python_flags = with_option(python_flags, "--dist", args.dist)


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


def sample_memory(root_pid, stop, peaks):
    """Every second until `stop`, the resident memory of the process tree under `root_pid`,
    from `ps` (macOS and Linux). `peaks` gets the largest tree, the largest Python process,
    and the most JVMs, and their combined size, seen at once."""
    while not stop.is_set():
        try:
            listing = subprocess.run(["ps", "-axo", "pid=,ppid=,rss=,comm="], capture_output=True, text=True, timeout=10).stdout
        except (OSError, subprocess.SubprocessError):
            return
        rows, children = {}, collections.defaultdict(list)
        for line in listing.splitlines():
            fields = line.split(None, 3)
            if len(fields) == 4 and fields[0].isdigit() and fields[1].isdigit() and fields[2].isdigit():
                rows[int(fields[0])] = (int(fields[2]) * 1024, os.path.basename(fields[3].strip()))
                children[int(fields[1])].append(int(fields[0]))
        tree, pending = [], [root_pid]
        while pending:
            pid = pending.pop()
            if pid in rows:
                tree.append(rows[pid])
            pending.extend(children[pid])
        jvms = [rss for rss, name in tree if name.startswith("java")]
        peaks["tree"] = max(peaks["tree"], sum(rss for rss, _ in tree))
        peaks["python"] = max([peaks["python"], *(rss for rss, name in tree if not name.startswith("java"))])
        peaks["jvm_count"] = max(peaks["jvm_count"], len(jvms))
        peaks["jvm_total"] = max(peaks["jvm_total"], sum(jvms))
        stop.wait(1.0)


def system_memory():
    """One line on how much memory the machine has free and how much it has swapped, or
    nothing where it cannot be read. A suite that fits in memory still runs slowly on a
    machine that is short of it."""
    try:
        if sys.platform == "darwin":
            pressure = subprocess.run(["memory_pressure"], capture_output=True, text=True, timeout=10).stdout
            free = re.search(r"free percentage: (\d+)%", pressure)
            swap = subprocess.run(["sysctl", "-n", "vm.swapusage"], capture_output=True, text=True, timeout=10).stdout.strip()
            used = re.search(r"used = ([\d.]+M)", swap)
            return f"{free.group(1)}% of memory free, {used.group(1) if used else '?'} swapped out"
        if sys.platform.startswith("linux"):
            info = {k: int(v.split()[0]) for k, v in (l.split(":", 1) for l in Path("/proc/meminfo").read_text().splitlines())}
            return f"{info['MemAvailable'] / 1024 ** 2:.1f} GB of {info['MemTotal'] / 1024 ** 2:.1f} GB available, {(info['SwapTotal'] - info['SwapFree']) / 1024:.0f} MB swapped out"
    except (OSError, subprocess.SubprocessError, KeyError, ValueError):
        pass
    return None


def streamed(cmd):
    """(seconds, completed or None when hung, [(seconds since start, line)], memory peaks).
    Lines are timestamped as they arrive, which `timed` cannot do. Progress is printed
    at every tenth of the run, from the percentage pytest puts on each result."""
    start = time.perf_counter()
    peaks = {"tree": 0, "python": 0, "jvm_count": 0, "jvm_total": 0}
    proc = subprocess.Popen(cmd, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
    hung = threading.Event()
    stop = threading.Event()
    # daemon, so that an interrupted run is not held open until the timeout
    killer = threading.Timer(args.timeout, lambda: (hung.set(), proc.kill()))
    killer.daemon = True
    killer.start()
    if os.name != "nt":
        threading.Thread(target=sample_memory, args=(proc.pid, stop, peaks), daemon=True).start()
    lines, mark = [], 10
    try:
        for line in proc.stdout:
            lines.append((time.perf_counter() - start, line.rstrip("\n")))
            percent = re.search(r"\[\s*(\d+)%\]", line)
            if percent and int(percent.group(1)) >= mark:
                print(f"{lines[-1][0]:7.1f}s  {percent.group(1):>3s}%", flush=True)
                mark = (int(percent.group(1)) // 10 + 1) * 10
        proc.wait()
    finally:
        # an interrupt must not leave pytest and its workers running
        killer.cancel()
        stop.set()
        if proc.poll() is None:
            proc.kill()
            proc.wait()
    return time.perf_counter() - start, None if hung.is_set() else proc, lines, peaks


RESULT = re.compile(r"^\[(gw\d+)\] \[\s*\d+%\] (?:PASSED|FAILED|SKIPPED|ERROR|XFAIL|XPASS) (\S+?)(?:::|\s|$)")


def report_workers(lines, wall):
    """When each xdist worker reported its last result, and the files it ran."""
    workers = collections.defaultdict(lambda: {"tests": 0, "first": None, "last": 0.0, "files": set()})
    placed = collections.defaultdict(set)
    last_of_file = collections.defaultdict(float)
    for seconds, line in lines:
        found = RESULT.match(line)
        if not found:
            continue
        worker, file = found.group(1), found.group(2)
        entry = workers[worker]
        entry["tests"] += 1
        entry["first"] = seconds if entry["first"] is None else entry["first"]
        entry["last"] = seconds
        entry["files"].add(file)
        placed[file].add(worker)
        last_of_file[file] = seconds
    if not workers:
        return
    print(f"\nWorkers, by when their last result arrived (wall {wall:.1f}s)\n")
    for worker, entry in sorted(workers.items(), key=lambda kv: kv[1]["last"]):
        print(f"{entry['last']:8.1f}s  {worker:5s} {entry['tests']:4d} tests  {len(entry['files']):3d} files  first result at {entry['first']:.1f}s")
    finishes = sorted(entry["last"] for entry in workers.values())
    print(f"\nThe last worker finished {finishes[-1] - finishes[len(finishes) // 2]:.1f}s after the median one, and {finishes[-1] - finishes[0]:.1f}s after the first.")
    print("\nWhere the files that finished last ran\n")
    for file, seconds in sorted(last_of_file.items(), key=lambda kv: -kv[1])[:5]:
        print(f"{seconds:8.1f}s  {','.join(sorted(placed[file])):12s} {file}")


def one_run():
    with tempfile.TemporaryDirectory() as directory:
        junit = Path(directory) / "junit.xml"
        # -v prints each result with its worker, which the worker report reads
        flags = ["-v" if flag == "-q" else flag for flag in python_flags]
        cmd = [sys.executable, "-m", "pytest", *files, *flags, "-p", "no:cacheprovider", f"--junitxml={junit}"]
        print(f"Running: pytest {shlex.join(python_flags)} over {len(files)} files", flush=True)
        before = system_memory()
        if before:
            print(f"Memory before: {before}", flush=True)
        elapsed, proc, lines, peaks = streamed(cmd)
        out = "\n".join(line for _, line in lines)
        print(f"\nWall time {elapsed:.1f}s. {last_summary(out)}")
        after = system_memory()
        if after:
            print(f"Memory after: {after}")
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
        report_workers(lines, elapsed)
        if peaks["tree"]:
            gb, mb = 1024 ** 3, 1024 ** 2
            print(f"\nPeak memory {peaks['tree'] / gb:.2f} GB for the whole process tree. The largest Python process reached {peaks['python'] / mb:.0f} MB, "
                  f"and up to {peaks['jvm_count']} JVMs at once held {peaks['jvm_total'] / mb:.0f} MB")
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


try:
    per_file() if args.per_file else one_run()
except KeyboardInterrupt:
    print("\nInterrupted, and the test run stopped.")
    sys.exit(130)
