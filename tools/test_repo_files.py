# SPDX-License-Identifier: MPL-2.0

"""Tests for `tools/conftest.py`'s `repo_files` (python-test-melting, TM6, TD-29)."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from conftest import repo_files

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def _git_checkout(request: pytest.FixtureRequest, tmp_path: Path) -> None:
    """`repo_files` enumerates with `git ls-files`, so each test's tmp_path is a git checkout,
    except the one that tests the refusal without one."""
    if "without_git" not in request.node.name:
        subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)


def test_finds_a_fixed_string(tmp_path: Path) -> None:
    (tmp_path / "a.ttl").write_text("hello LATTICE/foo/0.1.0 world\n", encoding="utf-8")
    (tmp_path / "b.ttl").write_text("nothing relevant here\n", encoding="utf-8")
    found = repo_files(["."], "LATTICE/foo/0.1.0", fixed=True, repo_root=tmp_path)
    assert found == ["a.ttl"]


def test_finds_a_regex_with_line_anchors(tmp_path: Path) -> None:
    (tmp_path / "a.ttl").write_text("ins:Element\n", encoding="utf-8")
    (tmp_path / "b.ttl").write_text("ins:ElementKind\n", encoding="utf-8")  # must NOT match ([^A-Za-z0-9_]|$)
    (tmp_path / "c.ttl").write_text("ins:Element other text\n", encoding="utf-8")
    pattern = r"ins:(Element)([^A-Za-z0-9_]|$)"
    found = repo_files(["."], pattern, repo_root=tmp_path)
    assert found == ["a.ttl", "c.ttl"]


def test_returns_forward_slash_relative_paths(tmp_path: Path) -> None:
    nested = tmp_path / "sub" / "dir"
    nested.mkdir(parents=True)
    (nested / "x.ttl").write_text("needle\n", encoding="utf-8")
    found = repo_files(["sub"], "needle", fixed=True, repo_root=tmp_path)
    assert found == ["sub/dir/x.ttl"]


def test_skips_build_and_dependency_directories(tmp_path: Path) -> None:
    skipped = tmp_path / "__pycache__"
    skipped.mkdir()
    (skipped / "cached.ttl").write_text("needle\n", encoding="utf-8")
    kept = tmp_path / "src"
    kept.mkdir()
    (kept / "real.ttl").write_text("needle\n", encoding="utf-8")
    found = repo_files(["."], "needle", fixed=True, repo_root=tmp_path)
    assert found == ["src/real.ttl"]


def test_a_root_that_is_a_file_is_searched_directly(tmp_path: Path) -> None:
    (tmp_path / "single.md").write_text("needle here\n", encoding="utf-8")
    found = repo_files(["single.md"], "needle", fixed=True, repo_root=tmp_path)
    assert found == ["single.md"]


def test_handles_non_utf8_bytes_without_raising(tmp_path: Path) -> None:
    (tmp_path / "latin1.ttl").write_bytes("caf\xe9 needle\n".encode("latin-1"))
    found = repo_files(["."], "needle", fixed=True, repo_root=tmp_path)
    assert found == ["latin1.ttl"]


def test_no_match_returns_empty_list(tmp_path: Path) -> None:
    (tmp_path / "a.ttl").write_text("nothing here\n", encoding="utf-8")
    assert repo_files(["."], "absent-term", fixed=True, repo_root=tmp_path) == []


def test_a_nonexistent_root_is_simply_empty(tmp_path: Path) -> None:
    assert repo_files(["does-not-exist"], "needle", fixed=True, repo_root=tmp_path) == []


def test_plants_a_retired_term_and_catches_it_on_this_platform(tmp_path: Path) -> None:
    """Adversarial probe (TM6's, per the plan's Validation table): a retired term
    planted in a scanned directory is found, on whatever platform this runs on."""
    layer = tmp_path / "ontology" / "instrument"
    layer.mkdir(parents=True)
    (layer / "README.md").write_text("this mentions ins:Element in prose\n", encoding="utf-8")
    pattern = r"ins:(Element|Provision)([^A-Za-z0-9_]|$)"
    found = repo_files(["ontology"], pattern, repo_root=tmp_path)
    assert found == ["ontology/instrument/README.md"]


def test_an_ignored_path_is_never_returned(tmp_path: Path) -> None:
    """A scan must not read a gitignored directory, which may hold material that is not for the repository."""
    (tmp_path / ".gitignore").write_text("private/\n", encoding="utf-8")
    (tmp_path / "private").mkdir()
    (tmp_path / "private" / "secret.md").write_text("needle\n", encoding="utf-8")
    (tmp_path / "public.md").write_text("needle\n", encoding="utf-8")
    assert repo_files(["."], "needle", fixed=True, repo_root=tmp_path) == ["public.md"]
    assert repo_files(["private"], "needle", fixed=True, repo_root=tmp_path) == []


def test_an_untracked_file_that_is_not_ignored_is_still_scanned(tmp_path: Path) -> None:
    """A file a contributor has just written is scanned before it is added or committed."""
    (tmp_path / "new.md").write_text("needle\n", encoding="utf-8")
    assert repo_files(["."], "needle", fixed=True, repo_root=tmp_path) == ["new.md"]


def test_refuses_without_git(tmp_path: Path) -> None:
    """Without git metadata a scan cannot tell an ignored file from a tracked one, so it refuses."""
    (tmp_path / "a.md").write_text("needle\n", encoding="utf-8")
    with pytest.raises(RuntimeError, match="needs a git checkout"):
        repo_files(["."], "needle", fixed=True, repo_root=tmp_path)
