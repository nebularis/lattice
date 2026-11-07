# SPDX-License-Identifier: MPL-2.0
"""tools/clean.py: what each area removes, what it leaves, and links and read-only files on every platform (STD-322)."""

from __future__ import annotations

import stat
import sys
from dataclasses import dataclass
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import clean  # noqa: E402


@dataclass
class Page:
    page: str


class Mork:
    def directory(self, role: str) -> Path:
        assert role == "mtp"
        return Path("ontology/mork/mtp")


class Catalogue:
    """The parts of the repository catalogue clean.py reads, over a scratch tree, so a test never cleans the checkout."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.site = (Page("docs/index.html"),)

    def area(self, name: str) -> Path:
        return Path(name)

    def module(self, name: str) -> Mork:
        assert name == "mork"
        return Mork()


def touch(root: Path, *paths: str) -> None:
    for rel in paths:
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"x")


def present(root: Path) -> set[str]:
    return {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()}


def test_python_removes_caches_everywhere_but_the_folders_never_walked(tmp_path: Path) -> None:
    touch(tmp_path, ".build/pytest-cache/v/x", ".build/pytest-cache/.gitkeep", ".pytest_cache/x", "build/lib/x",
          "lattice_tooling.egg-info/PKG-INFO", "workers/build/x", "tools/a/__pycache__/m.pyc",
          "tools/a/src/a.egg-info/PKG-INFO", ".venv/Lib/site-packages/b/__pycache__/m.pyc", "node_modules/c/__pycache__/m.pyc",
          "tools/a/m.py")
    assert clean.python(Catalogue(tmp_path)) == 0
    assert present(tmp_path) == {".build/pytest-cache/.gitkeep", ".venv/Lib/site-packages/b/__pycache__/m.pyc",
                                 "node_modules/c/__pycache__/m.pyc", "tools/a/m.py"}


def test_frontend_keeps_the_dotfiles_of_test_results_and_runs_yarn_where_it_is(tmp_path: Path, monkeypatch) -> None:
    touch(tmp_path, "node_modules/x", ".yarn/cache/x", "apps/studio/node_modules/x", "apps/studio/dist/x", "apps/studio/src/x",
          ".build/yarn-cache/x", ".build/word-test-results/report.xml", ".build/word-test-results/.gitkeep")
    monkeypatch.setattr(clean.shutil, "which", lambda name: None)
    assert clean.frontend(Catalogue(tmp_path)) == 0
    assert present(tmp_path) == {"apps/studio/src/x", ".build/word-test-results/.gitkeep"}


def test_build_and_docs_remove_their_outputs_and_leave_the_sources(tmp_path: Path) -> None:
    touch(tmp_path, "build/x", "ontology/mork/mtp/out/x", "ontology/mork/mtp/data/pins.lock.json", ".build/authoring/x",
          ".build/config-studio/x", ".build/other/x", "docs/_site/x", "docs/vendor/x", "docs/.jekyll-metadata", "docs/Gemfile")
    catalogue = Catalogue(tmp_path)
    assert clean.build(catalogue) == 0 and clean.docs(catalogue) == 0
    assert present(tmp_path) == {"ontology/mork/mtp/data/pins.lock.json", ".build/other/x", "docs/Gemfile"}


def test_a_link_is_removed_and_what_it_points_at_kept(tmp_path: Path) -> None:
    target = tmp_path / "kept"
    touch(tmp_path, "kept/x")
    link = tmp_path / "node_modules"
    try:
        link.symlink_to(target, target_is_directory=True)
    except OSError:
        import agent_guidance  # a junction where Windows refuses a symlink, as skills:link makes
        agent_guidance.link_directory(link, target)
    clean.remove(link)
    assert not link.exists() and (target / "x").is_file()


def test_a_read_only_file_is_removed(tmp_path: Path) -> None:
    touch(tmp_path, "build/locked")
    (tmp_path / "build/locked").chmod(stat.S_IREAD)
    clean.remove(tmp_path / "build")
    assert not (tmp_path / "build").exists()


def test_a_missing_path_is_skipped(tmp_path: Path) -> None:
    clean.remove(tmp_path / "absent")


@pytest.mark.parametrize("area", sorted(clean.AREAS))
def test_every_area_runs_on_an_empty_tree(tmp_path: Path, area: str, monkeypatch) -> None:
    monkeypatch.setattr(clean.shutil, "which", lambda name: None)
    assert clean.AREAS[area](Catalogue(tmp_path)) == 0
