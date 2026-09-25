# SPDX-License-Identifier: MPL-2.0
"""Reasoning isolation guardrail (ADR-A83 item 6).

Fails when a ``pom.xml`` other than ``platform/reasoning-testkit``'s declares a
reasoner or rules engine, or depends on the testkit outside ``test`` scope, or
when a ``pyproject.toml`` declares a reasoner, a rules engine or a JVM bridge.

Usage::

    python tools/reasoning_isolation_check.py [--root .]
"""

from __future__ import annotations

import argparse
import re
import sys
import tomllib
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TESTKIT = Path("platform/reasoning-testkit/pom.xml")
ENGINE = re.compile(r"hermit|openllet|pellet|drools|owlapi|owlready|jpype|py4j|pyjnius", re.IGNORECASE)
SKIP = {"node_modules", "target", ".venv", "build", ".build"}
POM = "{http://maven.apache.org/POM/4.0.0}"


def files(root: Path, name: str) -> list[Path]:
    return [p for p in sorted(root.rglob(name)) if not SKIP & set(p.relative_to(root).parts)]


def check(root: Path) -> list[str]:
    problems = []
    for pom in files(root, "pom.xml"):
        relative = pom.relative_to(root)
        if relative == TESTKIT:
            continue
        for dep in ET.parse(pom).getroot().iter(f"{POM}dependency"):
            artifact = dep.findtext(f"{POM}artifactId", "")
            if ENGINE.search(artifact) or ENGINE.search(dep.findtext(f"{POM}groupId", "")):
                problems.append(f"{relative}: declares {artifact}")
            if artifact == "reasoning-testkit" and dep.findtext(f"{POM}scope") != "test":
                problems.append(f"{relative}: depends on reasoning-testkit outside test scope")
    for project in files(root, "pyproject.toml"):
        data = tomllib.loads(project.read_text())
        declared = list(data.get("project", {}).get("dependencies", []))
        for extra in data.get("project", {}).get("optional-dependencies", {}).values():
            declared += extra
        problems += [f"{project.relative_to(root)}: declares {d}" for d in declared if ENGINE.search(d)]
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", default=str(ROOT))
    problems = check(Path(parser.parse_args(argv).root))
    for problem in problems:
        print(f"ISOLATION {problem}", file=sys.stderr)
    if not problems:
        print("reasoning engines are isolated in platform/reasoning-testkit")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
