# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""One release for the substrate and standalone modules (OD-D55 to OD-D59, slice VER1).
Validation Pack: docs/developer/validation/VER1.md. Test IDs are VER1-Tn."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import lattice_repo_catalogue as rc  # noqa: E402
import ontology_release  # noqa: E402
import ontology_releases  # noqa: E402
from ontology_version_check import check, check_release, check_release_bumped, check_unversioned  # noqa: E402

FENCE = "```"
L = "https://example.org/lattice"


def catalogue(version: str = "0.2.0", kinds: str = '["substrate"]') -> str:
    return (f'{FENCE}toml repository-catalogue\n[conventions]\nroles = ["spec", "shapes", "examples"]\n'
            f'versioned = ["spec"]\nartefact-directories = ["shapes"]\n'
            f'[conventions.kinds]\nsubstrate = "a layer"\napplied = "a domain module"\n'
            f'[conventions.release]\nversion = "{version}"\nkinds = {kinds}\n'
            f'[catalogue]\nschema = 1\nmodules = ["alpha", "beta"]\n{FENCE}\n')


def doc(name: str, version: str, imports: str = "") -> str:
    clause = f" ; owl:imports <{imports}>" if imports else ""
    return (f"@prefix owl: <http://www.w3.org/2002/07/owl#> .\n"
            f"<{L}/{name}> a owl:Ontology ; owl:versionIRI <{L}/{name}/{version}>{clause} .\n")


def put(root: Path, relative: str, text: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def git(root: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)


@pytest.fixture()
def repo(tmp_path: Path) -> Path:
    """alpha, a substrate member at 0.1.0 with a shapes directory, and beta, an applied module pinning it,
    committed with the catalogue still at 0.1.0."""
    put(tmp_path, "repository-catalogue.md", catalogue("0.1.0"))
    entry = lambda kind: f'{FENCE}toml repository-catalogue\n[module]\nkind = "{kind}"\nroles = ["spec", "shapes"]\n{FENCE}\n'
    put(tmp_path, "ontology/alpha/README.md", entry("substrate") + f"| `spec/alpha.ttl` | <{L}/alpha> | <{L}/alpha/0.1.0> | |\n")
    put(tmp_path, "ontology/alpha/spec/alpha.ttl", doc("alpha", "0.1.0"))
    put(tmp_path, "ontology/alpha/shapes/structural.ttl", "# shapes\n")
    put(tmp_path, "ontology/alpha/shapes/.version", "0.1.0\n")
    put(tmp_path, "ontology/beta/README.md", entry("applied"))
    put(tmp_path, "ontology/beta/spec/beta.ttl", doc("beta", "0.3.0", f"{L}/alpha/0.1.0"))
    put(tmp_path, "ontology/beta/shapes/structural.ttl", "# shapes\n")
    put(tmp_path, "ontology/beta/shapes/.version", "0.3.0\n")
    git(tmp_path, "init", "-q")
    git(tmp_path, "-c", "user.email=t@example.org", "-c", "user.name=t", "add", ".")
    git(tmp_path, "-c", "user.email=t@example.org", "-c", "user.name=t", "commit", "-q", "-m", "base")
    return tmp_path


@pytest.mark.parametrize("block, message", [
    ('[conventions.release]\nversion = "1.0"\nkinds = ["substrate"]', "not X.Y.Z"),
    ('[conventions.release]\nversion = "1.0.0"\nkinds = ["layer"]', "not conventions' kinds"),
    ('[conventions.release]\nversion = "1.0.0"', "exactly version and kinds"),
])
def test_ver1_t1_the_release_block_is_checked(tmp_path: Path, block: str, message: str) -> None:
    text = catalogue().replace('[conventions.release]\nversion = "0.2.0"\nkinds = ["substrate"]', block)
    put(tmp_path, "repository-catalogue.md", text.replace('modules = ["alpha", "beta"]', "modules = []"))
    with pytest.raises(rc.CatalogueError, match=message):
        rc.load(tmp_path)


def test_ver1_t2_members_and_their_references_carry_the_release(repo: Path) -> None:
    assert check_release(repo) == [
        "ontology/alpha/shapes/.version: a release member's directory carries no version of its own"]
    put(repo, "repository-catalogue.md", catalogue("0.2.0"))
    found = check_release(repo)
    assert any("ontology/alpha/spec/alpha.ttl: owl:versionIRI" in p for p in found)
    assert any(p.startswith("ontology/beta/spec/beta.ttl:2: names") for p in found)
    assert any(p.startswith("ontology/alpha/README.md:") for p in found)
    assert not any("beta/0.3.0" in p for p in found)  # an applied module keeps its own version


def test_ver1_t3_a_member_change_needs_a_new_release_and_a_non_member_keeps_its_own_rule(repo: Path) -> None:
    (repo / "ontology/alpha/shapes/.version").unlink()
    put(repo, "ontology/alpha/shapes/structural.ttl", "# shapes, changed\n")
    found = check_release_bumped(repo, "HEAD")
    assert len(found) == 1 and "still 0.1.0" in found[0]
    put(repo, "repository-catalogue.md", catalogue("0.2.0"))
    assert check_release_bumped(repo, "HEAD") == []
    put(repo, "ontology/beta/spec/beta.ttl", doc("beta", "0.3.0", f"{L}/alpha/0.2.0"))
    assert len(check(repo, "HEAD")) == 1  # beta changed without its own bump
    assert check_unversioned(repo) == []  # alpha's shapes need no .version now


def test_ver1_t4_prepare_moves_every_reference_in_one_substitution(repo: Path) -> None:
    counts = ontology_release.prepare(repo, "0.2.0")
    assert counts == {"ontology/alpha/README.md": 1, "ontology/alpha/spec/alpha.ttl": 1, "ontology/beta/spec/beta.ttl": 1}
    assert rc.load(repo).release_version == "0.2.0"
    assert not (repo / "ontology/alpha/shapes/.version").exists() and (repo / "ontology/beta/shapes/.version").exists()
    assert check_release(repo) == [] and check_release_bumped(repo, "HEAD") == []
    assert f"<{L}/beta/0.3.0>" in (repo / "ontology/beta/spec/beta.ttl").read_text(encoding="utf-8")
    with pytest.raises(ValueError, match="X.Y.Z"):
        ontology_release.prepare(repo, "next")


def test_ver1_t5_the_register_lists_the_release_once_and_non_members_by_document(repo: Path) -> None:
    ontology_release.prepare(repo, "0.2.0")
    ontology_releases.write(repo)
    rows = (repo / ontology_releases.REGISTER).read_text(encoding="utf-8")
    assert "| ontologies | 0.2.0 | ontologies-v0.2.0 | none | " in rows
    assert "alpha-spec-alpha-v0.2.0.ttl" in rows and "alpha-shapes-structural-v0.2.0.ttl" in rows
    assert "| lattice-beta | 0.3.0 | lattice-beta-v0.3.0 |" in rows and "| lattice-alpha | " not in rows
