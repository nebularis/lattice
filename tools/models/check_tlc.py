#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI
"""Check the TLA+ models of tools/models/multi-store-protocols/ with TLC, each run sized to the machine (MSA-I6).

The models' manifest, ``manifest.toml`` beside them, states for each configuration its module, its ``.cfg``, its tier, the
verdict expected of TLC and the peak heap and time measured on machine S. This runner:

1. Finds TLC in the tools jar ``TLA2TOOLS_JAR`` names, and Java on the path ``mise`` gives a task, then through
   ``mise where java``. Where either, or ``mem_check``, is missing it says what it skipped and exits 0.
2. Reads physical memory from the operating system and the memory available from ``mem_check`` (STD-151), on Windows,
   macOS and Linux, each within a Linux cgroup's limit where one is set. The budget is a quarter of physical memory, never
   above what is available, and lowered further by ``LATTICE_MODELS_MAX_HEAP_MB``. ``MEM_CHECK_AVAILABLE_MIB`` stands in
   for what is available, as it does for ``mem_check``.
3. Sets each run's heap to twice the configuration's measured peak and 64 MB more, at least 256 MB. A configuration whose
   heap exceeds the budget is skipped with both figures and is never started, as is one never measured or stopped at
   machine S's limit, unless ``--heap-mb`` gives it a heap. Several configurations run at once only with ``--jobs``, and those running never hold more heap
   together than the budget. TLC's workers are bounded by the cores, shared between the jobs. A configuration expected to
   violate a property runs with one worker, so its counts and its trace do not vary between runs.
4. Runs TLC in a copy of the models under ``.build/formal/tlc/multi-store-protocols/<configuration>/``, so its states, its
   trace files, its temporary files and its GC log are written there, and reads the verdict, the counts, the depth, TLC's
   time and the peak heap from what it printed. The young generation is fixed at 16 MB, so a collection runs at least
   every 16 MB allocated and the peak heap read from the GC log is at most 16 MB below the true peak.

A configuration fails only where TLC's verdict differs from the manifest's. A skip, a run stopped by ``--max-minutes`` and
a run that runs out of heap are reported and do not fail, since nothing fails for want of a machine.

Usage: python tools/models/check_tlc.py [configuration | tier | pattern ...] [--jobs N] [--heap-mb MB] [--max-minutes M]
       [--list]

A selector is a configuration's name, a tier (``base``, ``wide`` or ``all``) or a pattern such as ``X1_*``. The default is
the base tier. ``--heap-mb`` gives every selected run that heap, to measure it, including one the manifest states no peak for
and one stopped at machine S's limit, within the budget all the same.
"""

from __future__ import annotations

import argparse
import ctypes
import fnmatch
import math
import os
import re
import shutil
import subprocess
import sys
import threading
import time
import tomllib
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lattice_repo_catalogue import load  # noqa: E402

MODELS = "multi-store-protocols"
MANIFEST = "manifest.toml"
TIERS = ("base", "wide")
BUDGET_VARIABLE = "LATTICE_MODELS_MAX_HEAP_MB"
YOUNG_MB = 16
MIN_HEAP_MB = 256
GC_LINE = re.compile(r"Pause .*?(\d+)([KMG])->(\d+)([KMG])\((\d+)([KMG])\)")
STATES = re.compile(r"([\d,]+) states generated(?: \([^)]*\))?, ([\d,]+) distinct states found")
UNIT_MB = {"K": 1 / 1024, "M": 1, "G": 1024}


@dataclass(frozen=True)
class Configuration:
    name: str
    module: str
    config: str
    tier: str
    expect: str                 # "no error" or "violated"
    property: str | None        # the property expected to be violated
    kind: str | None            # "invariant", "action" or "temporal"
    peak_heap_mb: int | None
    limit: str | None           # why machine S stopped it, where it did
    distinct: int | None        # the distinct states TLC printed on machine S

    @property
    def expected(self) -> str:
        return "no error" if self.expect == "no error" else f"{self.kind} {self.property} violated"

    def heap_mb(self) -> int | None:
        """The heap a run is given, twice the measured peak and 64 MB more, at least 256 MB, in steps of 32 MB, or None where
        the manifest states no peak. The peak a large heap shows understates what a small one needs, since TLC's liveness
        checking ran out of a 208 MB heap in a configuration whose peak read 111 MB under 2 GB, and completed in 240 MB."""
        if self.peak_heap_mb is None:
            return None
        return max(MIN_HEAP_MB, 32 * math.ceil((2 * self.peak_heap_mb + 64) / 32))


@dataclass
class Result:
    status: str                 # PASS, FAIL, SKIP or STOP
    configuration: Configuration
    text: str


def read_manifest(path: Path) -> list[Configuration]:
    entries = tomllib.loads(path.read_text(encoding="utf-8")).get("configuration", [])
    found = []
    for entry in entries:
        expect = entry["expect"]
        if expect not in ("no error", "violated") or entry["tier"] not in TIERS:
            raise SystemExit(f"{path.name}: {entry['name']} has expect {expect!r} or tier {entry['tier']!r}, which this runner does not know")
        if expect == "violated" and entry.get("kind") not in ("invariant", "action", "temporal"):
            raise SystemExit(f"{path.name}: {entry['name']} is expected to violate a property, so it names the property's kind")
        found.append(Configuration(entry["name"], entry["module"], entry["config"], entry["tier"], expect, entry.get("property"),
                                   entry.get("kind"), entry.get("peak_heap_mb"), entry.get("limit"), entry.get("distinct")))
    return found


def select(configurations: list[Configuration], selectors: list[str]) -> list[Configuration]:
    chosen: list[Configuration] = []
    for selector in selectors or ["base"]:
        if selector == "all":
            matched = configurations
        elif selector in TIERS:
            matched = [c for c in configurations if c.tier == selector]
        else:
            matched = [c for c in configurations if fnmatch.fnmatchcase(c.name, selector)]
        if not matched:
            raise SystemExit(f"no configuration, tier or pattern {selector!r} in the manifest")
        chosen += [c for c in matched if c not in chosen]
    return chosen


# Memory. What is available comes from mem_check (STD-151), and physical memory from the operating system.

def physical_bytes() -> int:
    if sys.platform == "win32":
        class MemoryStatus(ctypes.Structure):
            _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong), ("ullTotalPhys", ctypes.c_ulonglong),
                        ("ullAvailPhys", ctypes.c_ulonglong), ("ullTotalPageFile", ctypes.c_ulonglong),
                        ("ullAvailPageFile", ctypes.c_ulonglong), ("ullTotalVirtual", ctypes.c_ulonglong),
                        ("ullAvailVirtual", ctypes.c_ulonglong), ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]

        status = MemoryStatus()
        status.dwLength = ctypes.sizeof(MemoryStatus)
        if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
            raise OSError("GlobalMemoryStatusEx failed")
        return int(status.ullTotalPhys)
    return os.sysconf("SC_PHYS_PAGES") * os.sysconf("SC_PAGE_SIZE")


def cgroup_limit() -> tuple[int | None, int | None]:
    """A Linux cgroup's memory limit and its usage, where one is set, so a container's share is read and not the host's."""
    for limit_file, usage_file in (("/sys/fs/cgroup/memory.max", "/sys/fs/cgroup/memory.current"),
                                   ("/sys/fs/cgroup/memory/memory.limit_in_bytes", "/sys/fs/cgroup/memory/memory.usage_in_bytes")):
        try:
            limit = Path(limit_file).read_text(encoding="utf-8").strip()
            usage = Path(usage_file).read_text(encoding="utf-8").strip()
        except OSError:
            continue
        if limit.isdigit() and int(limit) < 1 << 60:
            return int(limit), int(usage) if usage.isdigit() else None
    return None, None


def memory_mb(mem_check) -> tuple[int, int | None]:
    """Physical memory and the memory available now, in MB, each within a Linux cgroup's limit where one is set. Available
    is None where mem_check cannot read it."""
    total, available = physical_bytes(), mem_check.available_bytes()
    limit, usage = cgroup_limit() if sys.platform.startswith("linux") else (None, None)
    if limit is not None:
        total = min(total, limit)
        available = limit - (usage or 0) if available is None else min(available, limit - (usage or 0))
    return total // (1 << 20), None if available is None else available // (1 << 20)


def budget_mb(total: int, available: int | None, given: str | None) -> tuple[int, str]:
    """The heap all runs together may hold, in MB, and a line saying where it comes from: a quarter of physical memory
    ``total``, never above ``available``, and lowered, never raised, by ``given``, the value of LATTICE_MODELS_MAX_HEAP_MB."""
    budget, why = total // 4, f"a quarter of {total:,} MB physical"
    if available is not None and available < budget:
        budget, why = available, f"the {available:,} MB available"
    if given:
        if not given.isdigit():
            raise SystemExit(f"{BUDGET_VARIABLE} is {given!r}, and it gives a number of MB")
        if int(given) < budget:
            budget, why = int(given), BUDGET_VARIABLE
    shown = "unknown" if available is None else f"{available:,} MB"
    return budget, f"{budget:,} MB, {why} ({total:,} MB physical, {shown} available)"


def plan(configurations: list[Configuration], budget: int, measure: int | None = None) -> tuple[list[tuple[Configuration, int]], list[Result]]:
    """The configurations to run, each with its heap, and those skipped, each with its reason. ``measure``, from --heap-mb, gives
    every run that heap, to measure it, a configuration with no peak in the manifest or one stopped at machine S's limit
    among them. A configuration whose heap exceeds the budget is skipped, with both figures, and never started."""
    planned: list[tuple[Configuration, int]] = []
    skipped: list[Result] = []
    for c in configurations:
        heap = measure if measure is not None else None if c.limit else c.heap_mb()
        if heap is None and c.limit:
            skipped.append(Result("SKIP", c, f"stopped at machine S's limit ({c.limit}), so it has no verdict to check. "
                                             "Give --heap-mb to run it"))
        elif heap is None:
            skipped.append(Result("SKIP", c, "the manifest states no peak heap for it. Give --heap-mb to measure one"))
        elif heap > budget:
            skipped.append(Result("SKIP", c, f"needs a heap of {heap:,} MB, and the budget is {budget:,} MB"))
        else:
            planned.append((c, heap))
    return planned, skipped


# Tools.

def find_java() -> str | None:
    found = shutil.which("java")
    if found:
        return found
    mise = shutil.which("mise")
    if mise:
        where = subprocess.run([mise, "where", "java"], capture_output=True, encoding="utf-8")
        if where.returncode == 0 and where.stdout.strip():
            candidate = Path(where.stdout.strip()) / "bin" / ("java.exe" if sys.platform == "win32" else "java")
            if candidate.is_file():
                return str(candidate)
    return None


# One run.

def read_verdict(output: str) -> tuple[str, str | None, str | None]:
    """What TLC concluded: ("no error", None, None), ("violated", kind, property), or ("error", None, a line)."""
    if "Model checking completed. No error has been found." in output:
        return "no error", None, None
    for kind, pattern in (("invariant", r"Error: Invariant (\w+) is violated"), ("action", r"Error: Action property (\w+) is violated")):
        match = re.search(pattern, output)
        if match:
            return "violated", kind, match.group(1)
    if "Error: Temporal properties were violated" in output:
        return "violated", "temporal", None
    if "OutOfMemoryError" in output or "ran out of memory" in output:
        return "out of memory", None, None
    error = next((line for line in output.splitlines() if line.startswith("Error") or "Exception" in line), "no verdict printed")
    return "error", None, error


def judge(c: Configuration, output: str) -> tuple[str, str]:
    """PASS, FAIL or STOP for a run TLC finished, and what it printed. A run fails only where TLC's verdict differs from the
    manifest's, or where TLC printed none. One that ran out of its heap is stopped, and does not fail."""
    verdict, kind, name = read_verdict(output)
    if verdict == "out of memory":
        return "STOP", "ran out of its heap"
    if verdict == "error":
        return "FAIL", f"TLC did not finish: {name}. Expected {c.expected}"
    printed = ("no error" if verdict == "no error" else "temporal properties violated" if kind == "temporal"
               else f"{kind} {name} violated")
    # TLC does not name the temporal property it found violated, so a temporal violation agrees on its kind alone.
    agrees = verdict == c.expect and (verdict == "no error" or (kind == c.kind and (kind == "temporal" or name == c.property)))
    if not agrees:
        return "FAIL", f"TLC printed {printed}, expected {c.expected}"
    return "PASS", printed


def peak_heap(gc_log: Path) -> int | None:
    if not gc_log.is_file():
        return None
    peaks = [float(m.group(1)) * UNIT_MB[m.group(2)] for m in GC_LINE.finditer(gc_log.read_text(encoding="utf-8", errors="replace"))]
    return math.ceil(max(peaks)) if peaks else None


def last_counts(output: str) -> tuple[str, str] | None:
    """The states generated and the distinct states of the last count TLC printed, its final one or, for a run stopped early,
    its last progress line's, as TLC wrote them."""
    found = STATES.findall(output)
    return found[-1] if found else None


def run(c: Configuration, java: str, jar: str, models: Path, work: Path, heap: int, workers: int, max_minutes: float | None) -> Result:
    directory = work / c.name
    if directory.exists():
        shutil.rmtree(directory)
    directory.mkdir(parents=True)
    for source in [*models.glob("*.tla"), models / c.config]:
        shutil.copy2(source, directory)
    # TLC writes the standard modules it reads, Naturals.tla among them, to the temporary directory, so runs started together
    # in one shared directory read each other's half-written copies and fail to parse. Each run has its own.
    (directory / "tmp").mkdir()
    command = [java, f"-Xmx{heap}m", f"-Xmn{YOUNG_MB}m", "-XX:+UseParallelGC", "-Xlog:gc:file=gc.log", "-Djava.io.tmpdir=tmp",
               "-cp", jar, "tlc2.TLC", "-workers", str(workers), "-deadlock", "-config", c.config, f"{c.module}.tla"]
    started = time.monotonic()
    with open(directory / "tlc.out", "w", encoding="utf-8", newline="\n") as out:
        process = subprocess.Popen(command, cwd=directory, stdout=out, stderr=subprocess.STDOUT)
        try:
            process.wait(timeout=None if max_minutes is None else max_minutes * 60)
            stopped = False
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
            stopped = True
        except BaseException:
            process.kill()
            raise
    wall = time.monotonic() - started
    output = (directory / "tlc.out").read_text(encoding="utf-8", errors="replace")
    peak = peak_heap(directory / "gc.log")
    counts = last_counts(output)
    depth = re.search(r"The depth of the complete state graph search is (\d+)", output)
    progress = re.findall(r"Progress\((\d+)\)", output)
    finished = re.search(r"Finished in (.+?) at", output)
    figures = ", ".join([
        f"{counts[1]} distinct of {counts[0]} generated" if counts else "no state count printed",
        f"depth {depth.group(1)}" if depth else f"depth not printed, last progress {progress[-1]}" if progress else "depth not printed",
        f"TLC {finished.group(1)}" if finished else "TLC time not printed",
        f"wall {wall:.1f} s",
        f"peak heap {peak} MB" if peak is not None else "no collection logged",
        f"heap {heap:,} MB, {workers} worker(s)",
    ])
    if stopped:
        return Result("STOP", c, f"stopped at the limit of {max_minutes:g} min, {figures}")
    status, printed = judge(c, output)
    if status != "PASS":
        return Result(status, c, f"{printed}, {figures}. Output in {directory.as_posix()}")
    distinct = int(counts[1].replace(",", "")) if counts else None
    note = f". The manifest states {c.distinct:,} distinct states" if c.distinct is not None and distinct != c.distinct else ""
    return Result("PASS", c, f"{printed}, {figures}{note}")


class Budget:
    """The heap of the runs going on, which never exceeds the budget together."""

    def __init__(self, total: int) -> None:
        self.total, self.used, self.condition = total, 0, threading.Condition()

    def take(self, amount: int) -> None:
        with self.condition:
            self.condition.wait_for(lambda: self.used + amount <= self.total)
            self.used += amount

    def give(self, amount: int) -> None:
        with self.condition:
            self.used -= amount
            self.condition.notify_all()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("selectors", nargs="*", help="configuration names, tiers (base, wide, all) or patterns. Default: base")
    parser.add_argument("--jobs", type=int, default=1, help="how many configurations may run at once, within the budget")
    parser.add_argument("--heap-mb", type=int, default=None,
                        help="give every selected run this heap, to measure it, one with no peak in the manifest or stopped at machine S's limit among them")
    parser.add_argument("--max-minutes", type=float, default=None, help="stop a run after this long and report it, without failing")
    parser.add_argument("--list", action="store_true", help="list the selected configurations and the heap each would get")
    args = parser.parse_args(argv)

    catalogue = load()
    models = catalogue.root / catalogue.area("tools") / "models" / MODELS
    work = catalogue.root / ".build" / "formal" / "tlc" / MODELS
    configurations = select(read_manifest(models / MANIFEST), args.selectors)
    try:
        import mem_check
    except ImportError:
        print("SKIP: mem_check is not installed, so the memory available is unknown and no configuration was checked. "
              "Run `mise run bootstrap:testing-mem-check`")
        return 0
    budget, budget_text = budget_mb(*memory_mb(mem_check), os.environ.get(BUDGET_VARIABLE))
    print(f"models: {len(configurations)} configuration(s) of {MODELS}, heap budget {budget_text}", flush=True)

    planned, results = plan(configurations, budget, args.heap_mb)
    if args.list:
        for c, heap in planned:
            print(f"  {c.name:28} {c.tier:5} heap {heap:>6,} MB  expects {c.expected}")
        for r in results:
            print(f"  {r.configuration.name:28} {r.configuration.tier:5} SKIP {r.text}")
        return 0

    jar = os.environ.get("TLA2TOOLS_JAR")
    if not jar or not Path(jar).is_file():
        print(f"SKIP: TLA2TOOLS_JAR {'names no file' if jar else 'is not set'}, so no configuration was checked. Set it to the TLA+ tools jar")
        return 0
    java = find_java()
    if java is None:
        print("SKIP: no java on the path or from `mise where java`, so no configuration was checked. Run through mise")
        return 0

    for r in results:
        print(f"SKIP {r.configuration.name}: {r.text}", flush=True)
    jobs = max(1, args.jobs)
    cores = os.cpu_count() or 1
    pool = Budget(budget)
    lock = threading.Lock()

    def one(item: tuple[Configuration, int]) -> Result:
        c, heap = item
        workers = 1 if c.expect == "violated" else max(1, cores // jobs)
        pool.take(heap)
        try:
            with lock:
                print(f"RUN  {c.name}: heap {heap:,} MB, {workers} worker(s)", flush=True)
            result = run(c, java, jar, models, work, heap, workers, args.max_minutes)
        finally:
            pool.give(heap)
        with lock:
            print(f"{result.status} {c.name}: {result.text}", flush=True)
        return result

    with ThreadPoolExecutor(max_workers=jobs) as executor:
        results += list(executor.map(one, planned))

    counts = {status: sum(r.status == status for r in results) for status in ("PASS", "FAIL", "SKIP", "STOP")}
    print(f"models: {counts['PASS']} as expected, {counts['FAIL']} failed, {counts['SKIP']} skipped, {counts['STOP']} stopped")
    return 1 if counts["FAIL"] else 0


if __name__ == "__main__":
    sys.exit(main())
