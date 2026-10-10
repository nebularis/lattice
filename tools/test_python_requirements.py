# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""The Python packages share one test runner specifier.

`mise run bootstrap` resolves every Python package in one pip invocation, so two packages that ask
for incompatible versions of a shared test dependency fail the bootstrap, and installs run one at a
time (CI, `--jobs 1`) would each leave the environment on a different version. A difference between
two `pyproject.toml` files is therefore a defect, whichever file is right.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

import pytest
from packaging.requirements import Requirement

ROOT = Path(__file__).resolve().parents[1]
_SKIPPED_DIRECTORIES = {"node_modules", ".venv", ".build", "build"}
# Bootstrapped by none of the pip tasks, so it never meets the other packages in one environment.
_NOT_BOOTSTRAPPED = {"tools/spc/python/pyproject.toml"}
_SHARED = ("pytest", "pytest-xdist")


def _pyproject_files() -> list[Path]:
    found = [
        p for p in ROOT.rglob("pyproject.toml")
        if not _SKIPPED_DIRECTORIES & set(p.relative_to(ROOT).parts)
        and p.relative_to(ROOT).as_posix() not in _NOT_BOOTSTRAPPED
    ]
    return sorted(found)


def _requirements(path: Path) -> list[str]:
    project = tomllib.loads(path.read_text(encoding="utf-8")).get("project", {})
    optional = [r for group in project.get("optional-dependencies", {}).values() for r in group]
    return [*project.get("dependencies", []), *optional]


def _specifiers(name: str) -> dict[str, str]:
    """The specifier each pyproject.toml gives ``name``, keyed by repository-relative path."""
    result: dict[str, str] = {}
    for path in _pyproject_files():
        for text in _requirements(path):
            requirement = Requirement(text)
            if requirement.name == name:
                result[path.relative_to(ROOT).as_posix()] = str(requirement.specifier)
    return result


def test_the_repository_has_python_packages_that_use_pytest() -> None:
    assert len(_specifiers("pytest")) >= 5


@pytest.mark.parametrize("name", _SHARED)
def test_every_package_gives_a_shared_test_dependency_the_same_specifier(name: str) -> None:
    specifiers = _specifiers(name)
    assert len(set(specifiers.values())) <= 1, f"{name} is specified differently: {specifiers}"
