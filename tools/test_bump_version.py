# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""The version bump: the number, a module's spec documents in unison, its shapes, and the refusals that
keep the substrate's release and a module released on its own apart (ADR-A129, ADR-A120)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import bump_version as bv  # noqa: E402
import lattice_repo_catalogue  # noqa: E402

BASE = "https://example.org/x"


def doc(name: str, version: str, imports: str = "") -> str:
    return (f"@prefix owl: <http://www.w3.org/2002/07/owl#> .\n<{BASE}/{name}> a owl:Ontology ;\n"
            f"    owl:versionIRI <{BASE}/{name}/{version}>{imports} .\n")


@pytest.fixture
def layer(tmp_path: Path) -> tuple[Path, lattice_repo_catalogue.Module]:
    spec = tmp_path / "ontology/x/spec"
    spec.mkdir(parents=True)
    (spec / "x.ttl").write_text(doc("x", "0.21.0"))
    (spec / "x-store.ttl").write_text(doc("x-store", "0.21.0", f" ;\n    owl:imports <https://example.org/foundation/0.21.0>, <{BASE}/x/0.21.0>"))
    (tmp_path / "ontology/x/shapes").mkdir()
    (tmp_path / "ontology/x/shapes/.version").write_text("0.20.0\n")
    (tmp_path / "ontology/x/README.md").write_text(f"| `spec/x.ttl` | <{BASE}/x> | <{BASE}/x/0.21.0> | none |\n\n- **Unreleased**.\n  - a change.\n- **0.21.0**.\n")
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    return tmp_path, lattice_repo_catalogue.Module("x", Path("ontology/x"), "standalone", ("spec", "shapes"), None)


def test_the_next_number() -> None:
    assert bv.next_version("0.21.0", "minor", None) == "0.22.0"
    assert bv.next_version("0.21.3", "patch", None) == "0.21.4"
    assert bv.next_version("0.21.3", "major", None) == "1.0.0"
    assert bv.next_version("0.21.0", None, "1.0.0") == "1.0.0"
    with pytest.raises(bv.BumpError, match="not after"):
        bv.next_version("0.21.0", None, "0.21.0")
    with pytest.raises(bv.BumpError, match="not X.Y.Z"):
        bv.next_version("0.21.0", None, "1.0")


def test_a_layer_spec_documents_move_in_unison_and_its_imports_of_others_stay(layer) -> None:
    root, module = layer
    log: list[str] = []
    assert bv.bump_spec(root, module, "minor", None, log) == "0.22.0"
    store = (root / "ontology/x/spec/x-store.ttl").read_text()
    assert f"<{BASE}/x-store/0.22.0>" in store and f"<{BASE}/x/0.22.0>" in store
    assert "<https://example.org/foundation/0.21.0>" in store, "another module's pin is not this module's to move"
    assert f"<{BASE}/x/0.22.0>" in (root / "ontology/x/README.md").read_text()
    assert "x: 2 spec document(s) 0.21.0 -> 0.22.0" in log


def test_spec_documents_at_different_numbers_are_refused(layer) -> None:
    root, module = layer
    (root / "ontology/x/spec/x.ttl").write_text(doc("x", "0.20.0"))
    with pytest.raises(bv.BumpError, match="move in unison"):
        bv.bump_spec(root, module, "minor", None, [])


def test_the_shapes_share_one_version_moved_by_their_own_number(layer) -> None:
    root, module = layer
    assert bv.bump_shapes(root, module, "minor", None, []) == "0.21.0", "the shapes' own 0.20.0, not the specs' number"
    assert (root / "ontology/x/shapes/.version").read_text() == "0.21.0\n"


def test_the_unreleased_notes_take_the_number(layer) -> None:
    root, _ = layer
    log: list[str] = []
    bv.name_release(root, root / "ontology/x/README.md", "0.22.0", log)
    assert "- **0.22.0**.\n  - a change." in (root / "ontology/x/README.md").read_text()
    bv.name_release(root, root / "ontology/x/README.md", "0.23.0", log)
    assert "no Unreleased notes" in log[-1]


def test_the_substrate_and_a_module_on_its_own_are_never_confused() -> None:
    root = lattice_repo_catalogue.find_root(None)
    with pytest.raises(bv.BumpError, match="member of the substrate release"):
        bv.bump(root, "foundation", "minor", None, "no", [])
    with pytest.raises(bv.BumpError, match="have no .version"):
        bv.bump(root, None, "minor", None, "with", [])
    with pytest.raises(bv.BumpError, match="no module of the catalogue"):
        bv.bump(root, "persistance", "minor", None, "no", [])


def test_increment_and_new_version_exclude_each_other_and_so_do_the_shapes_flags(capsys) -> None:
    for argv in (["--increment", "minor", "--new-version", "1.0.0"], ["--increment", "minor", "--with-shapes", "--only-shapes"], []):
        with pytest.raises(SystemExit):
            bv.main(argv)
