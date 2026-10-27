# SPDX-License-Identifier: MPL-2.0
"""Report the lines that may break two platform guardrails, PRI-55 and PRI-56. Report only, never a failure.

PRI-55: no string concatenation into SPARQL. A line is reported where a string that reads as SPARQL is
joined to something else, by ``+``, an f-string, ``.format``, ``String.format``, ``%`` or a template literal.

PRI-56: no ``now()`` in a guard, an effect, an ordering key, a canonicalisation or an identity. A line is
reported where it reads the wall clock, in Java, Python, TypeScript or SPARQL. A read through an injected clock, such as ``Instant.now(clock)``, takes time as an input and is not reported. Whether the time it reads
reaches one of those five is a judgement the scan cannot make, so every read of the clock is listed.

Both are heuristics over single lines, so a report is a list for a reviewer, with false positives and
misses. The scan covers the tracked code under the roots AGENTS.md names for the guardrails, platform,
workers, packages and apps, and leaves tests out unless asked (TD-85).

Usage::

    mise run dev:guardrail-scan
    mise run dev:guardrail-scan -- --tests
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import lattice_repo_catalogue  # noqa: E402

ROOTS = ("platform", "workers", "packages", "apps")
SUFFIXES = {".java", ".py", ".ts", ".tsx", ".js", ".mjs"}

SPARQL = re.compile(r"""["'`][^"'`]*\b(SELECT|INSERT|DELETE|CONSTRUCT|ASK|WHERE|PREFIX|GRAPH|FILTER)\b""")
JOINED = re.compile(r"""["'`]\s*\+|\+\s*["'`]|\bf["']|\.format\(|String\.format\(|\.formatted\(|["']\s*%\s*[\w(]|\$\{""")
CLOCK = re.compile(
    r"\b(Instant|LocalDateTime|LocalDate|OffsetDateTime|ZonedDateTime|LocalTime)\.now\(\s*\)|System\.currentTimeMillis\(|"
    r"System\.nanoTime\(|Clock\.system(UTC|DefaultZone)\(|\bdatetime\.(now|utcnow|today)\(|\bdate\.today\(|"
    r"\btime\.(time|time_ns)\(|\bDate\.now\(|\bnew Date\(\s*\)|\bNOW\(\s*\)"
)


def is_test(path: str) -> bool:
    name = path.rsplit("/", 1)[-1]
    return ("/test/" in path or "/tests/" in path or "/__tests__/" in path or name.startswith("test_")
            or name.endswith(("Test.java", "Tests.java", "IT.java", ".test.ts", ".test.tsx", ".spec.ts", ".spec.tsx")))


def files(root: Path, tests: bool) -> list[str]:
    catalogue = lattice_repo_catalogue.load(root)
    areas = [catalogue.area(name).as_posix() for name in ROOTS]
    listed = subprocess.run(["git", "-C", str(root), "ls-files", "--", *areas],
                            capture_output=True, text=True, check=True).stdout.splitlines()
    return [p for p in listed if Path(p).suffix in SUFFIXES and (tests or not is_test(p))]


def scan(text: str) -> tuple[list[int], list[int]]:
    """The lines of ``text`` that may break PRI-55, and those that may break PRI-56."""
    concatenated, clock = [], []
    for number, line in enumerate(text.splitlines(), 1):
        if SPARQL.search(line) and JOINED.search(line):
            concatenated.append(number)
        if CLOCK.search(line):
            clock.append(number)
    return concatenated, clock


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--tests", action="store_true", help="scan tests as well")
    arguments = parser.parse_args(argv)
    root = lattice_repo_catalogue.find_root()
    found: dict[str, list[str]] = {"PRI-55": [], "PRI-56": []}
    for path in files(root, arguments.tests):
        lines = (root / path).read_text(encoding="utf-8", errors="replace").splitlines()
        concatenated, clock = scan("\n".join(lines))
        found["PRI-55"] += [f"{path}:{n}: {lines[n - 1].strip()[:120]}" for n in concatenated]
        found["PRI-56"] += [f"{path}:{n}: {lines[n - 1].strip()[:120]}" for n in clock]
    titles = {"PRI-55": "string joined into what reads as SPARQL", "PRI-56": "a read of the wall clock"}
    for principle, hits in found.items():
        print(f"{principle}, {titles[principle]}: {len(hits)} line(s)")
        for hit in hits:
            print(f"  {hit}")
    print("Report only. Each line is for a reviewer to judge, and nothing fails (TD-85).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
