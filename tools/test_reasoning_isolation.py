# SPDX-License-Identifier: MPL-2.0

"""The reasoning isolation guardrail (ADR-A83 item 6)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from reasoning_isolation_check import check  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
POM = """<project xmlns="http://maven.apache.org/POM/4.0.0"><dependencies>{}</dependencies></project>"""
DEP = "<dependency><groupId>{}</groupId><artifactId>{}</artifactId>{}</dependency>"


def write(root: Path, relative: str, text: str) -> None:
    (root / relative).parent.mkdir(parents=True, exist_ok=True)
    (root / relative).write_text(text)


def test_repository_is_isolated() -> None:
    assert check(ROOT) == []


def test_violations_are_reported(tmp_path: Path) -> None:
    write(tmp_path, "platform/reasoning-testkit/pom.xml", POM.format(DEP.format("net.sourceforge.owlapi", "org.semanticweb.hermit", "")))
    write(tmp_path, "platform/a/pom.xml", POM.format(DEP.format("com.github.galigator.openllet", "openllet-owlapi", "")))
    write(tmp_path, "platform/b/pom.xml", POM.format(DEP.format("org.nebularis.lattice", "reasoning-testkit", "")))
    write(tmp_path, "platform/c/pom.xml", POM.format(DEP.format("org.nebularis.lattice", "reasoning-testkit", "<scope>test</scope>")))
    write(tmp_path, "tools/x/pyproject.toml", '[project]\nname = "x"\ndependencies = ["owlready2>=0.4"]\n')
    assert sorted(check(tmp_path)) == [
        "platform/a/pom.xml: declares openllet-owlapi",
        "platform/b/pom.xml: depends on reasoning-testkit outside test scope",
        "tools/x/pyproject.toml: declares owlready2>=0.4",
    ]
