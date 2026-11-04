# SPDX-License-Identifier: MPL-2.0

"""Tests for ``tools/ontology_version_check.py`` (ADR-A86 and its proposed
addendum). Each test builds a throwaway git repository with one commit as
the base ref, then edits its working tree."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from ontology_version_check import check, check_unversioned  # noqa: E402

HEADER = """@prefix owl: <http://www.w3.org/2002/07/owl#> .
<https://example.org/doc> a owl:Ontology {version} .
"""


def document(version: str | None, body: str = "") -> str:
    clause = f"; owl:versionIRI <https://example.org/doc/{version}>" if version else ""
    return HEADER.format(version=clause) + body


def git(root: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)


@pytest.fixture()
def repo(tmp_path: Path) -> Path:
    git(tmp_path, "init", "-q")
    git(tmp_path, "config", "user.email", "test@example.org")
    git(tmp_path, "config", "user.name", "test")
    write(tmp_path, "ontology/layer/spec/layer.ttl", document("0.1.0"))
    write(tmp_path, "ontology/layer/examples/example.ttl", document(None))
    git(tmp_path, "add", ".")
    git(tmp_path, "commit", "-q", "-m", "base")
    return tmp_path


def write(root: Path, relative: str, text: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_content_changed_without_bump_is_flagged(repo: Path) -> None:
    write(repo, "ontology/layer/spec/layer.ttl", document("0.1.0", "<https://example.org/t> a owl:Class ."))
    assert len(check(repo, "HEAD")) == 1


def test_content_and_version_changed_together_pass(repo: Path) -> None:
    write(repo, "ontology/layer/spec/layer.ttl", document("0.2.0", "<https://example.org/t> a owl:Class ."))
    assert check(repo, "HEAD") == []


def test_untouched_repository_passes(repo: Path) -> None:
    assert check(repo, "HEAD") == []
    assert check_unversioned(repo) == []


def test_spec_document_without_version_iri_is_flagged(repo: Path) -> None:
    write(repo, "ontology/layer/spec/layer.ttl", document(None))
    assert check_unversioned(repo) == ["ontology/layer/spec/layer.ttl: declares owl:Ontology without owl:versionIRI"]


def test_new_vocab_document_without_version_iri_is_flagged(repo: Path) -> None:
    write(repo, "ontology/layer/vocab/layer-vocab.ttl", document(None))
    assert len(check_unversioned(repo)) == 1


def test_example_document_without_version_iri_passes(repo: Path) -> None:
    write(repo, "ontology/layer/examples/example.ttl", document(None, "<https://example.org/x> a owl:Thing ."))
    assert check_unversioned(repo) == []
    assert check(repo, "HEAD") == []


def test_new_document_with_version_iri_passes(repo: Path) -> None:
    write(repo, "ontology/other/spec/other.ttl", document("0.1.0"))
    assert check(repo, "HEAD") == []
    assert check_unversioned(repo) == []


def test_a_flagged_module_is_told_how_it_is_released() -> None:
    """A standalone module is released on its own and a substrate layer with the release, which an
    agent once got wrong for Persistence, so the check names the way for each flagged module."""
    import ontology_version_check as ovc
    lines = ovc.how_released(ovc.ROOT, ["ontology/persistence/spec/persistence.ttl: content changed",
                                        "ontology/foundation/spec/foundation.ttl: content changed"])
    assert len(lines) == 2
    assert any("ontology/foundation is substrate" in l and "version:bump -- --increment" in l for l in lines)
    assert any("ontology/persistence is standalone, released on its own" in l and "--layer-target persistence" in l and "move in unison" in l for l in lines)
    assert ovc.how_released(ovc.ROOT, []) == []
