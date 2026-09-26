# SPDX-License-Identifier: MPL-2.0

"""Tests for ``tools/ontology_releases.py`` and the artefact ``.version``
checks of ``tools/ontology_version_check.py`` (ADR-A86 second addendum)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from ontology_releases import REGISTER, check, pending_tags, release_name, write  # noqa: E402
from ontology_version_check import check_artefacts, check_unversioned  # noqa: E402
from test_ontology_version_check import document, git, repo, write as write_file  # noqa: E402,F401


def test_release_names_drop_known_prefixes() -> None:
    assert release_name("https://www.nebularis.org/neuro-semantic/lattice/foundation-vocab/0.3.0") == ("foundation-vocab", "0.3.0")
    assert release_name("https://www.nebularis.org/neuro-semantic/lattice/applied/capacity/execution/0.6.0") == ("applied-capacity-execution", "0.6.0")
    assert release_name("http://www.nebularis.org/ontologies/Mork/0.4.0") == ("mork", "0.4.0")
    assert release_name("http://example.org/spc/0.2.0") == ("spc", "0.2.0")


def test_unlisted_version_fails_until_written_and_rows_are_kept(repo: Path) -> None:
    write_file(repo, "ontology/layer/shapes/structural.ttl", "")
    write_file(repo, "ontology/layer/shapes/.version", "0.1.0\n")
    assert len(check(repo)) == 2
    write(repo)
    assert check(repo) == []
    assert pending_tags(repo) == ["doc-v0.1.0", "layer-shapes-v0.1.0"]
    assert "shapes/structural.ttl" in (repo / REGISTER).read_text()
    write_file(repo, "ontology/layer/spec/layer.ttl", document("0.2.0"))
    write(repo)
    rows = [line for line in (repo / REGISTER).read_text().splitlines() if line.startswith("| `doc`")]
    assert [row.split("|")[2].strip() for row in rows] == ["`0.1.0`", "`0.2.0`"]


def test_tag_on_another_version_fails(repo: Path) -> None:
    write(repo)
    git(repo, "add", ".")
    git(repo, "commit", "-q", "-m", "register")
    git(repo, "tag", "doc-v0.1.0")
    assert check(repo) == [] and pending_tags(repo) == []
    write_file(repo, "ontology/layer/spec/layer.ttl", document("0.2.0"))
    write(repo)
    git(repo, "tag", "doc-v0.2.0")  # names HEAD, which still has 0.1.0
    assert check(repo) == ["tag doc-v0.2.0 names a commit where ontology/layer/spec/layer.ttl does not hold https://example.org/doc/0.2.0"]


def test_artefact_change_needs_its_version_file_bumped(repo: Path) -> None:
    write_file(repo, "ontology/layer/shapes/structural.ttl", "# shapes\n")
    assert check_unversioned(repo) == ["ontology/layer/shapes/.version: missing, or not a semantic version X.Y.Z"]
    write_file(repo, "ontology/layer/shapes/.version", "0.1.0\n")
    git(repo, "add", ".")
    git(repo, "commit", "-q", "-m", "shapes")
    write_file(repo, "ontology/layer/shapes/structural.ttl", "# changed shapes\n")
    assert len(check_artefacts(repo, "HEAD")) == 1
    write_file(repo, "ontology/layer/shapes/.version", "0.1.1\n")
    assert check_artefacts(repo, "HEAD") == [] and check_unversioned(repo) == []
