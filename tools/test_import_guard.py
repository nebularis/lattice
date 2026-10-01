# SPDX-License-Identifier: MPL-2.0

"""The import guard (computable-contract-substrate C10a, ADR-A01 addendum, law
B7). Row IDs are the C10a Validation Pack's."""

from __future__ import annotations

import re
import sys
import tomllib
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import import_guard  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = Path(__file__).resolve().parent / "fixtures" / "import_guard"


def test_c10a_01_the_repository_passes(capsys: pytest.CaptureFixture) -> None:
    assert import_guard.main(["--root", str(ROOT)]) == 0
    assert "0 violation(s)" in capsys.readouterr().out


@pytest.mark.parametrize("case, file, line, named", [
    ("upward-import", "ontology/party/spec/party.ttl", 5, "lattice/eligibility/0.7.0"),
    ("upward-spec", "ontology/quantification/spec/quantification.ttl", 3, "lattice/instrument"),
    ("upward-shape", "ontology/eligibility/shapes/constraints.ttl", 3, "lattice/behaviour"),
    ("upward-example", "ontology/foundation/examples/example.ttl", 3, "lattice/applied"),
    ("sibling", "ontology/wording/spec/wording.ttl", 3, "lattice/behaviour"),
])
def test_c10a_02_each_failing_fixture_is_reported(case: str, file: str, line: int, named: str,
                                                  capsys: pytest.CaptureFixture) -> None:
    assert import_guard.main(["--root", str(FIXTURES / case)]) == 1
    out = capsys.readouterr().out
    assert f"{file}:{line}:" in out and named in out, out


def test_c10a_03_a_projection_naming_a_lower_layer_passes() -> None:
    assert import_guard.check(FIXTURES / "passes") == []


def _diagram_order() -> dict[str, set[str]]:
    """Each layer's allowed imports, read from the dependency diagram in
    ontology-architecture.md: its ancestors in the tree, plus any 'also imports'."""
    text = (ROOT / "docs" / "architecture" / "ontology-architecture.md").read_text()
    block = text.split("Dependency order, per [ADR-A01]", 1)[1].split("```", 2)[1]
    stack: list[tuple[int, str]] = []
    allowed: dict[str, set[str]] = {}
    for raw in block.splitlines():
        match = re.search(r"([a-z][a-z ]*?)(?:\s{2,}\(also imports ([a-z ]+)\))?\s*$", raw)
        if not match or not match.group(1).strip():
            continue
        name = match.group(1).strip()
        depth = raw.index(name)
        layer = name.split()[0]  # behaviour configuration and behaviour runtime are one layer
        while stack and stack[-1][0] >= depth:
            stack.pop()
        ancestors = {a for _, a in stack} - {layer}
        if match.group(2):
            ancestors.add(match.group(2).split()[0])
        allowed.setdefault(layer, set()).update(ancestors)
        stack.append((depth, layer))
    return allowed


def test_c10a_04_the_order_table_matches_the_architecture_diagram() -> None:
    assert _diagram_order() == {layer: set(allowed) for layer, allowed in import_guard.ALLOWED.items()}


def test_c10a_05_check_runs_the_guard() -> None:
    tasks = tomllib.loads((ROOT / "mise.toml").read_text())["tasks"]
    assert "check:import-guard" in tasks["check"]["depends"]
    assert "import_guard.py" in tasks["check:import-guard"]["run"]
