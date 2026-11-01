# SPDX-License-Identifier: MPL-2.0
"""A benchmark's report, one JSON file per run, kept in git (ADR-A150 decision 1), and a timer for Python measures.

`benchmark/reports/{benchmark}/{UTC date and time}-{short commit}.json`, described by `benchmark/reports/report.schema.json`. A report names the kind of machine and
never its host name or its user (ADR-A124 decision 5)."""

from __future__ import annotations

import json
import os
import platform
import re
import statistics
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence

from ._tools import catalogue

SCHEMA_VERSION = 1
STAMP = "%Y%m%dT%H%M%SZ"
MACHINE_KEYS = ("os", "os_version", "architecture", "processor_model", "processor_count", "memory_bytes", "java", "python", "power_mode")
"""The keys that make two machines the same kind. The load average at start is recorded beside them and is not one of them."""


class ReportError(ValueError):
    """A report that does not have the form `report.schema.json` describes."""


def reports_dir(root: Optional[Path] = None) -> Path:
    root = catalogue.find_root(root)
    return root / catalogue.load(root).area("benchmark") / "reports"


# --- the timer ---------------------------------------------------------------------------------


def time_ms(action: Callable[[], Any], repeats: int, warmup: int = 2) -> List[float]:
    """Runs `action` `warmup` times and discards them, then `repeats` times, and returns each run's time in milliseconds on `time.perf_counter_ns`."""
    for _ in range(warmup):
        action()
    out = []
    for _ in range(repeats):
        start = time.perf_counter_ns()
        action()
        out.append((time.perf_counter_ns() - start) / 1e6)
    return out


# --- a measure ---------------------------------------------------------------------------------


def quartiles(values: Sequence[float]) -> List[float]:
    """The first and third quartile by the inclusive method. One value is its own quartiles."""
    if len(values) == 1:
        return [values[0], values[0]]
    q = statistics.quantiles(values, n=4, method="inclusive")
    return [q[0], q[2]]


def measure(name: str, unit: str, repeats: Sequence[float]) -> Dict[str, Any]:
    if not repeats:
        raise ReportError(f"measure {name!r} has no repeats")
    values = [float(v) for v in repeats]
    return {"name": name, "unit": unit, "repeats": values, "median": statistics.median(values), "iqr": quartiles(values), "min": min(values), "max": max(values)}


# --- the machine -------------------------------------------------------------------------------


def _run(argv: List[str]) -> str:
    try:
        return subprocess.run(argv, capture_output=True, text=True, timeout=10).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return ""


def _processor_model() -> str:
    if sys.platform == "darwin":
        return _run(["sysctl", "-n", "machdep.cpu.brand_string"]) or platform.processor()
    cpuinfo = Path("/proc/cpuinfo")
    if cpuinfo.is_file():
        for line in cpuinfo.read_text(errors="replace").splitlines():
            if line.lower().startswith("model name"):
                return line.partition(":")[2].strip()
    return platform.processor()


def _memory_bytes() -> Optional[int]:
    if sys.platform == "darwin":
        text = _run(["sysctl", "-n", "hw.memsize"])
        return int(text) if text.isdigit() else None
    meminfo = Path("/proc/meminfo")
    if meminfo.is_file():
        match = re.search(r"MemTotal:\s+(\d+) kB", meminfo.read_text(errors="replace"))
        return int(match.group(1)) * 1024 if match else None
    return None


def _java() -> Optional[str]:
    match = re.search(r'version "([^"]+)"', subprocess.run(["java", "-version"], capture_output=True, text=True, timeout=10).stderr) if _on_path("java") else None
    return match.group(1) if match else None


def _on_path(program: str) -> bool:
    from shutil import which
    return which(program) is not None


def _power_mode() -> Optional[str]:
    """macOS power settings from `pmset -g`, for example `powermode 0, lowpowermode 0`. Nothing where `pmset` is absent or unreadable."""
    if sys.platform != "darwin":
        return None
    found = re.findall(r"^\s*((?:low)?powermode)\s+(\d+)", _run(["pmset", "-g"]), re.MULTILINE)
    return ", ".join(f"{k} {v}" for k, v in found) or None


def machine() -> Dict[str, Any]:
    """The kind of machine, never its name or its user, and the load average when this was called."""
    load = list(os.getloadavg()) if hasattr(os, "getloadavg") else None
    return {
        "os": platform.system(), "os_version": (platform.mac_ver()[0] if sys.platform == "darwin" else platform.release()),
        "architecture": platform.machine(), "processor_model": _processor_model(), "processor_count": os.cpu_count(),
        "memory_bytes": _memory_bytes(), "java": _java(), "python": platform.python_version(), "power_mode": _power_mode(),
        "load_average_at_start": load,
    }


def short_commit(checkout: Path) -> str:
    out = _run(["git", "-C", str(checkout), "rev-parse", "--short=8", "HEAD"])
    if not out:
        raise ReportError(f"{checkout} has no commit")
    return out


# --- a report ----------------------------------------------------------------------------------


def build(benchmark: str, commit: str, measures: List[Dict[str, Any]], machine_kind: Dict[str, Any], when: Optional[datetime] = None, notes: str = "") -> Dict[str, Any]:
    when = (when or datetime.now(timezone.utc)).astimezone(timezone.utc)
    report = {"schema": SCHEMA_VERSION, "benchmark": benchmark, "commit": commit, "date": when.strftime("%Y-%m-%dT%H:%M:%SZ"), "machine": machine_kind, "measures": measures}
    if notes:
        report["notes"] = notes
    validate(report)
    return report


def write(report: Dict[str, Any], root: Optional[Path] = None) -> Path:
    validate(report)
    when = datetime.strptime(report["date"], "%Y-%m-%dT%H:%M:%SZ")
    target = reports_dir(root) / report["benchmark"] / f"{when.strftime(STAMP)}-{report['commit']}.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8", newline="\n")
    return target


def listing(benchmark: str, root: Optional[Path] = None) -> List[Path]:
    """The benchmark's reports, oldest first. The date leads the name, so the names sort in time."""
    return sorted((reports_dir(root) / benchmark).glob("*.json"))


def load(path: Path) -> Dict[str, Any]:
    try:
        report = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ReportError(f"{path}: {error}") from None
    try:
        validate(report)
    except ReportError as error:
        raise ReportError(f"{path}: {error}") from None
    return report


def _need(ok: bool, message: str) -> None:
    if not ok:
        raise ReportError(message)


def _number(v: Any) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def validate(report: Any) -> None:
    """Checks the form `benchmark/reports/report.schema.json` describes, without a schema library, so it runs wherever the harness does."""
    _need(isinstance(report, dict), "a report is an object")
    for key in ("schema", "benchmark", "commit", "date", "machine", "measures"):
        _need(key in report, f"a report has {key}")
    _need(report["schema"] == SCHEMA_VERSION, f"schema {report['schema']!r} is not {SCHEMA_VERSION}")
    _need(isinstance(report["benchmark"], str) and re.fullmatch(r"[a-z0-9][a-z0-9-]*", report["benchmark"]) is not None, "benchmark is a lower-case name")
    _need(isinstance(report["commit"], str) and re.fullmatch(r"[0-9a-f]{7,40}", report["commit"]) is not None, "commit is a hexadecimal short or full hash")
    _need(isinstance(report["date"], str) and re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ", report["date"]) is not None, "date is UTC, as 2026-10-31T14:02:11Z")
    machine_kind = report["machine"]
    _need(isinstance(machine_kind, dict), "machine is an object")
    for key in MACHINE_KEYS + ("load_average_at_start",):
        _need(key in machine_kind, f"machine has {key}")
    _need(set(machine_kind) <= set(MACHINE_KEYS) | {"load_average_at_start"}, f"machine has only {', '.join(MACHINE_KEYS)} and load_average_at_start")
    _need(isinstance(report["measures"], list) and report["measures"], "measures is a list of at least one")
    names = set()
    for m in report["measures"]:
        _need(isinstance(m, dict) and set(m) == {"name", "unit", "repeats", "median", "iqr", "min", "max"}, "a measure has name, unit, repeats, median, iqr, min and max")
        _need(isinstance(m["name"], str) and m["name"] and m["name"] not in names, f"measure name {m['name']!r} is a string and unique")
        names.add(m["name"])
        _need(isinstance(m["unit"], str) and m["unit"], f"{m['name']}: unit is a string")
        _need(isinstance(m["repeats"], list) and m["repeats"] and all(_number(v) for v in m["repeats"]), f"{m['name']}: repeats are numbers, at least one")
        _need(isinstance(m["iqr"], list) and len(m["iqr"]) == 2 and all(_number(v) for v in m["iqr"]) and m["iqr"][0] <= m["iqr"][1], f"{m['name']}: iqr is [first quartile, third quartile]")
        _need(_number(m["median"]) and _number(m["min"]) and _number(m["max"]) and m["min"] <= m["median"] <= m["max"], f"{m['name']}: median lies between min and max")
        _need(m["min"] == min(m["repeats"]) and m["max"] == max(m["repeats"]), f"{m['name']}: min and max are those of the repeats")
        _need(m["median"] == statistics.median(m["repeats"]), f"{m['name']}: median is that of the repeats")
