# SPDX-License-Identifier: MPL-2.0
"""Policy enforcement (temporal-binding-consumer-hardening plan, Finding 4):
the Python equivalent of an ArchUnit rule, mirroring
tools/persistence/tests/test_architecture.py. These are collection-time /
AST-level checks on the package's own source, not runtime behaviour tests, so
a future change that makes resolution depend on wall-clock time fails CI
immediately rather than being caught by chance in a later test.
"""

from __future__ import annotations

import ast
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src" / "vocabulary"

#: Modules exempt from the wall-clock check. Empty today: unlike
#: tools/persistence (whose HLC module legitimately reads a clock),
#: nothing in tools/vocabulary has a reason to. Add a module here only with
#: the same kind of documented justification persistence's exemption carries.
EXEMPT_MODULES: tuple[str, ...] = ()


def _module_source(name: str) -> str:
    return (SRC / f"{name}.py").read_text(encoding="utf-8")


def test_no_module_calls_a_wall_clock_function():
    """Mirrors the guide's QP2 rule (scoped NOW() policy), applied to the
    Python side: no module in this package may call datetime.now()/
    time.time()/datetime.utcnow(), because a resolution outcome must be a
    pure function of the loaded graph, the caller-supplied active context,
    and the caller-supplied resolution time, never of when resolve() happened
    to be called."""
    offenders = []
    for path in sorted(SRC.glob("*.py")):
        if path.stem in EXEMPT_MODULES:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func = node.func
                attr = getattr(func, "attr", None)
                if attr in ("now", "time", "utcnow"):
                    offenders.append(f"{path.name}: {attr}()")
    assert offenders == [], f"wall-clock call found in vocabulary module(s): {offenders}"


def test_no_module_imports_the_time_module():
    """A coarser, complementary check: nothing in this package should need
    to import the standard library `time` module at all. `datetime` itself
    stays permitted (Resolution/Binding legitimately hold datetime values
    supplied by the caller); only the *call* to a wall-clock function is
    what test_no_module_calls_a_wall_clock_function forbids."""
    offenders = []
    for path in sorted(SRC.glob("*.py")):
        if path.stem in EXEMPT_MODULES:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == "time":
                        offenders.append(f"{path.name}: import time")
            elif isinstance(node, ast.ImportFrom) and node.module == "time":
                offenders.append(f"{path.name}: from time import ...")
    assert offenders == [], f"import of the time module found in: {offenders}"
