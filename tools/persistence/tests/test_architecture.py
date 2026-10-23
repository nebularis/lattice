# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""Policy enforcement (plan Slice 2, item 4): the Python equivalent of an
ArchUnit rule. These are collection-time / AST-level checks on the
package's own source, not runtime behaviour tests, so a refactor that
violates the trust boundary in ADR-A79 point 4 fails CI immediately
rather than being caught by chance in a later test."""

from __future__ import annotations

import ast
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src" / "persistence"


def _module_source(name: str) -> str:
    return (SRC / f"{name}.py").read_text(encoding="utf-8")


def _imported_names(tree: ast.AST) -> set[str]:
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
    return names


def test_no_module_imports_chevron():
    """H2.9: the Mustache templates and the renderer are gone, so no module of the package may bring a template engine back. The
    trust boundary of ADR-A79 point 4 is the encoder and the typed builders (persistence.ir)."""
    offenders = []
    for path in SRC.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        if {"chevron", "pystache"} & {name.split(".")[0] for name in _imported_names(tree)}:
            offenders.append(path.name)
    assert offenders == [], f"a Mustache library is imported in: {offenders}"


def test_the_package_ships_no_template_files():
    assert not (SRC / "templates").exists() and not list(SRC.rglob("*.mustache"))


def test_resolver_and_terms_do_not_call_wall_clock_functions():
    """Mirrors the guide's QP2 rule (scoped NOW() policy), applied to the
    Python side: no module involved in resolution or term-encoding may
    call datetime.now()/time.time(), because a resolution outcome must be
    a pure function of the loaded graph and the supplied capability spec,
    never of when the compiler happened to run."""
    banned_modules = ["resolver", "terms", "scopes", "capability", "boundary", "validator"]
    offenders = []
    for name in banned_modules:
        tree = ast.parse(_module_source(name), filename=name)
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func = node.func
                attr = getattr(func, "attr", None)
                if attr in ("now", "time", "utcnow"):
                    offenders.append(f"{name}.py: {attr}()")
    assert offenders == [], f"wall-clock call found in resolution-critical module(s): {offenders}"
