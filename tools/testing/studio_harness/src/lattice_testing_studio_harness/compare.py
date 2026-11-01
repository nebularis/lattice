# SPDX-License-Identifier: MPL-2.0
"""`mise run benchmark:compare -- {benchmark} [--base {report}] [--head {report}]`. Tables the measures of two reports. It never fails on time (STD-290), and exits 1 only when a report is malformed or missing."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from . import reports
from .reports import ReportError

OUTSIDE = "*"


def change_percent(base: float, head: float) -> Optional[float]:
    """The change of `head` against `base` in percent. Nothing when `base` is zero."""
    return None if base == 0 else (head - base) / base * 100.0


def outside_noise(base: Dict[str, Any], head: Dict[str, Any]) -> bool:
    """True when each run's median lies outside the other's interquartile range, which is the change we call beyond the noise of both runs."""
    return not (base["iqr"][0] <= head["median"] <= base["iqr"][1]) and not (head["iqr"][0] <= base["median"] <= head["iqr"][1])


def rows(base: Dict[str, Any], head: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], List[str]]:
    """One row per measure of `head`, and the names `base` has and `head` lacks, or the reverse, as notes."""
    base_by = {m["name"]: m for m in base["measures"]}
    out, notes = [], []
    for m in head["measures"]:
        b = base_by.pop(m["name"], None)
        if b is None:
            notes.append(f"{m['name']} is only in the head report")
        elif b["unit"] != m["unit"]:
            notes.append(f"{m['name']} is in {b['unit']} in the base and {m['unit']} in the head, so it is not compared")
        else:
            out.append({"name": m["name"], "unit": m["unit"], "base": b["median"], "head": m["median"], "percent": change_percent(b["median"], m["median"]), "marked": outside_noise(b, m)})
    notes += [f"{name} is only in the base report" for name in base_by]
    return out, notes


def machine_warnings(base: Dict[str, Any], head: Dict[str, Any]) -> List[str]:
    warnings = [f"the machines differ in {key}: {base['machine'][key]!r} against {head['machine'][key]!r}" for key in reports.MACHINE_KEYS if base["machine"][key] != head["machine"][key]]
    return warnings


def table(base: Dict[str, Any], head: Dict[str, Any]) -> str:
    body, notes = rows(base, head)
    width = max([len(r["name"]) for r in body] + [7])
    lines = [f"benchmark {head['benchmark']}: base {base['commit']} ({base['date']}), head {head['commit']} ({head['date']})", ""]
    lines.append(f"{'measure':<{width}}  {'unit':<5}  {'base median':>12}  {'head median':>12}  {'change':>9}")
    for r in body:
        pct = "n/a" if r["percent"] is None else f"{r['percent']:+.1f}%"
        lines.append(f"{r['name']:<{width}}  {r['unit']:<5}  {r['base']:>12.3f}  {r['head']:>12.3f}  {pct:>9} {OUTSIDE if r['marked'] else ''}".rstrip())
    lines += ["", f"{OUTSIDE} the change lies outside the interquartile range of both runs. An unmarked change is within the noise of the runs."]
    for note in notes:
        lines.append(f"note: {note}")
    for w in machine_warnings(base, head):
        lines.append(f"WARNING: {w}")
    lines.append("Before reading a change as real, check each run's power mode and load (STD-040).")
    for label, report in (("base", base), ("head", head)):
        m = report["machine"]
        lines.append(f"  {label}: power mode {m['power_mode']}, load average at start {m['load_average_at_start']}")
    return "\n".join(lines)


def resolve(benchmark: str, name: Optional[str], default: Path, root: Optional[Path]) -> Path:
    if name is None:
        return default
    candidate = Path(name)
    if candidate.is_file():
        return candidate
    matches = [p for p in reports.listing(benchmark, root) if p.name == name or p.name.startswith(name) or p.stem.endswith(name)]
    if len(matches) != 1:
        raise ReportError(f"{name!r} names {len(matches)} reports of {benchmark}, not one")
    return matches[0]


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="benchmark:compare", description="Table the measures of two reports of a benchmark. Never fails on time.")
    parser.add_argument("benchmark")
    parser.add_argument("--base", help="a report's path, its file name, or the start or end of its name. Default: the one before the head")
    parser.add_argument("--head", help="as --base. Default: the latest")
    args = parser.parse_args(argv)
    try:
        found = reports.listing(args.benchmark)
        head_path = resolve(args.benchmark, args.head, found[-1] if found else Path(), None)
        if args.head is None and not found:
            raise ReportError(f"no reports of {args.benchmark} in {reports.reports_dir() / args.benchmark}")
        before = [p for p in found if p.name < head_path.name]
        base_path = resolve(args.benchmark, args.base, before[-1] if before else Path(), None)
        if args.base is None and not before:
            raise ReportError(f"{args.benchmark} has no report before {head_path.name} to compare with")
        print(table(reports.load(base_path), reports.load(head_path)))
    except ReportError as error:
        print(f"benchmark:compare: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
