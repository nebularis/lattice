# SPDX-License-Identifier: MPL-2.0
"""The requires marker: a skip naming the missing package, a run where every package is present, and LATTICE_REQUIRE_ALL."""

from __future__ import annotations

import pytest

pytest_plugins = ["pytester"]

TESTS = """
import pytest

@pytest.mark.requires("json")
def test_present():
    pass

@pytest.mark.requires("no_such_package_for_lattice")
def test_absent():
    raise AssertionError("ran without its package")

def test_plain():
    pass
"""


def test_a_missing_package_skips_its_test_and_names_the_package(pytester: pytest.Pytester, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LATTICE_REQUIRE_ALL", raising=False)
    pytester.makepyfile(TESTS)
    result = pytester.runpytest("-rs")
    result.assert_outcomes(passed=2, skipped=1)
    out = result.stdout.str()
    assert "needs no_such_package_for_lattice" in out  # the short summary cuts a reason at the terminal's width
    assert "lattice: not run for a package this environment lacks: no_such_package_for_lattice (1 test)" in out


def test_require_all_fails_a_test_whose_package_is_missing(pytester: pytest.Pytester, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LATTICE_REQUIRE_ALL", "1")
    pytester.makepyfile(TESTS)
    result = pytester.runpytest()
    result.assert_outcomes(passed=2, errors=1)  # failed in setup, before the test body
    assert result.ret != 0
    result.stdout.fnmatch_lines(["*needs no_such_package_for_lattice, which cannot be imported here, and LATTICE_REQUIRE_ALL=1*"])


def test_a_run_with_every_package_present_says_nothing(pytester: pytest.Pytester, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LATTICE_REQUIRE_ALL", raising=False)
    pytester.makepyfile("import pytest\n\n@pytest.mark.requires('json', 'os')\ndef test_present():\n    pass\n")
    result = pytester.runpytest()
    result.assert_outcomes(passed=1)
    assert "lattice: not run" not in result.stdout.str()
