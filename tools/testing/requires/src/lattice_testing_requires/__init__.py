# SPDX-License-Identifier: MPL-2.0
"""The Python packages a test needs, declared with ``@pytest.mark.requires("anthropic")`` (STD-323).

A test whose package cannot be imported here is skipped, and its reason names the package, since some environments can never
install it. A skip says nothing about the operating system. ``LATTICE_REQUIRE_ALL=1`` fails such a test instead, for a run that
must prove every test ran. Loaded by every pytest run in an environment where this package is installed, through its ``pytest11``
entry point.
"""

from __future__ import annotations

import importlib.util
import os

import pytest

REQUIRE_ALL = "LATTICE_REQUIRE_ALL"
_MISSING = pytest.StashKey[dict[str, int]]()


def missing(names: tuple[str, ...]) -> list[str]:
    """The names among ``names`` no module can be imported for."""
    absent = []
    for name in names:
        try:
            found = importlib.util.find_spec(name) is not None
        except (ImportError, ValueError):
            found = False
        if not found:
            absent.append(name)
    return absent


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "requires(*packages): the Python packages a test needs. A missing one skips it, naming the package, "
        f"or fails it where {REQUIRE_ALL}=1 (STD-323)")
    config.stash[_MISSING] = {}


def pytest_runtest_setup(item: pytest.Item) -> None:
    names = tuple(name for marker in item.iter_markers("requires") for name in marker.args)
    absent = missing(names)
    if not absent:
        return
    counts = item.config.stash[_MISSING]
    for name in absent:
        counts[name] = counts.get(name, 0) + 1
    reason = f"needs {', '.join(absent)}, which cannot be imported here"
    if os.environ.get(REQUIRE_ALL) == "1":
        pytest.fail(f"{reason}, and {REQUIRE_ALL}=1", pytrace=False)
    pytest.skip(reason)


def pytest_terminal_summary(terminalreporter, exitstatus: int, config: pytest.Config) -> None:
    counts = config.stash.get(_MISSING, {})
    if counts:
        listed = ", ".join(f"{name} ({count} test{'s' if count > 1 else ''})" for name, count in sorted(counts.items()))
        terminalreporter.write_line(f"lattice: not run for a package this environment lacks: {listed}. {REQUIRE_ALL}=1 fails them")
