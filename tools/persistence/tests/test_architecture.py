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


def test_only_render_module_imports_chevron():
    """ADR-A79 point 4: the trust boundary is the encoder. Only
    persistence.render may import chevron; every other module, in
    particular the resolver and the encoders themselves, must go through
    render()'s type-enforced wrapper, never call chevron directly."""
    offenders = []
    for path in SRC.glob("*.py"):
        if path.stem in ("render", "__init__"):
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        if "chevron" in _imported_names(tree):
            offenders.append(path.name)
    assert offenders == [], f"only persistence.render may import chevron, found in: {offenders}"


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


def test_chevron_render_is_never_called_with_a_dynamically_built_template_argument():
    """A structural proxy for ADR-A79 point 4: the *template text* argument
    to chevron.render must always come from load_template()'s file read,
    never from an f-string, %-format, or .format() call that could smuggle
    untrusted content into the template position itself (the context
    argument's own safety is the encoders' job, checked in test_terms.py's
    injection corpus; this test is about the template argument specifically,
    the one thing that must always be Lattice-authored, reviewed source)."""
    tree = ast.parse(_module_source("render"), filename="render.py")
    offending_first_args = []
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "render"
            and getattr(node.func.value, "id", None) == "chevron"
        ):
            if node.args and isinstance(node.args[0], (ast.JoinedStr, ast.BinOp)):
                offending_first_args.append(node.lineno)
    assert offending_first_args == [], (
        f"chevron.render called with a dynamically-assembled template argument at line(s) "
        f"{offending_first_args}; the template text must always come from load_template()"
    )
