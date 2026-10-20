# SPDX-License-Identifier: MPL-2.0
"""ADR-A132 decision 3: the library imports the standard library and rdflib only, and never the compiler."""

from __future__ import annotations

import ast
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src" / "lattice_persistence"


def test_imports_are_standard_library_rdflib_or_the_package_itself():
    offenders = []
    for path in SRC.glob("*.py"):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            names = [a.name for a in node.names] if isinstance(node, ast.Import) else [node.module] if isinstance(node, ast.ImportFrom) and node.level == 0 else []
            for name in names:
                top = name.split(".")[0]
                if top not in sys.stdlib_module_names and top not in ("rdflib", "lattice_persistence"):
                    offenders.append((path.name, name))
    assert offenders == []
