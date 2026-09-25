# SPDX-License-Identifier: MPL-2.0

"""Tests for ``tools/ontology_catalog.py`` (ADR-A88)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest
from rdflib import Namespace
from rdflib.namespace import OWL, RDF

sys.path.insert(0, str(Path(__file__).resolve().parent))

import ontology_catalog  # noqa: E402
from ontology_catalog import Catalog, CatalogError, check, closure, expected_files, scan, write  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
ROOT_CATALOG = ROOT / "ontology" / "catalog-v001.xml"
LATTICE = "https://www.nebularis.org/neuro-semantic/lattice/"


def version_iri(relative: str) -> str:
    """The version IRI a repository document declares, read from the tree so
    the tests do not pin a version number."""
    document = next(d for d in scan(ROOT).documents if d.path == relative)
    return document.names[1]


def ontology(iri: str, imports: tuple[str, ...] = (), body: str = "") -> str:
    clauses = "".join(f" ; owl:imports <{target}>" for target in imports)
    return (
        "@prefix owl: <http://www.w3.org/2002/07/owl#> .\n"
        f"<{iri}> a owl:Ontology ; owl:versionIRI <{iri}/1.0.0>{clauses} .\n{body}"
    )


@pytest.fixture()
def tree(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Two published documents, a importing b, and no known defects."""
    monkeypatch.setattr(ontology_catalog, "KNOWN_DEFECTS", {})
    (tmp_path / "ontology/a/spec").mkdir(parents=True)
    (tmp_path / "ontology/b/spec").mkdir(parents=True)
    (tmp_path / "ontology/a/spec/a.ttl").write_text(ontology("https://example.org/a", ("https://example.org/b/1.0.0",)))
    (tmp_path / "ontology/b/spec/b.ttl").write_text(
        ontology("https://example.org/b", body="<https://example.org/b#Term> a owl:Class .\n")
    )
    write(tmp_path)
    return tmp_path


def test_repository_catalog_is_consistent() -> None:
    problems, _ = check(ROOT)
    assert problems == []


def test_fixture_tree_is_consistent_and_its_closure_loads(tree: Path) -> None:
    assert check(tree) == ([], [])
    graph = closure(Catalog(tree / "ontology/a/spec/catalog-v001.xml"), "https://example.org/a/1.0.0")
    assert (Namespace("https://example.org/b#").Term, RDF.type, OWL.Class) in graph


def test_removed_entry_is_reported(tree: Path) -> None:
    catalog = tree / "ontology/catalog-v001.xml"
    text = catalog.read_text()
    catalog.write_text("\n".join(line for line in text.splitlines() if "b/1.0.0" not in line) + "\n")
    problems, _ = check(tree)
    assert any("differs from a fresh generation" in p for p in problems)
    with pytest.raises(CatalogError):
        closure(Catalog(catalog), "https://example.org/a/1.0.0")


def test_entry_pointing_at_the_wrong_file_is_reported(tree: Path) -> None:
    catalog = tree / "ontology/catalog-v001.xml"
    catalog.write_text(catalog.read_text().replace('uri="b/spec/b.ttl"', 'uri="a/spec/a.ttl"'))
    problems, _ = check(tree)
    assert any("which does not declare it" in p for p in problems)


def test_hand_edited_stub_is_reported_as_drift(tree: Path) -> None:
    stub = tree / "ontology/a/spec/catalog-v001.xml"
    stub.write_text(stub.read_text().replace("../../catalog-v001.xml", "../catalog-v001.xml"))
    problems, _ = check(tree)
    assert problems == ["ontology/a/spec/catalog-v001.xml: differs from a fresh generation, run: python tools/ontology_catalog.py write"]


def test_unresolved_import_is_reported(tree: Path) -> None:
    (tree / "ontology/a/spec/a.ttl").write_text(ontology("https://example.org/a", ("https://example.org/missing",)))
    write(tree)
    problems, _ = check(tree)
    assert problems == ["ontology/a/spec/a.ttl: imports https://example.org/missing, which no document under ontology/ declares"]


def test_iri_declared_twice_is_refused(tree: Path) -> None:
    (tree / "ontology/b/spec/copy.ttl").write_text(ontology("https://example.org/b"))
    with pytest.raises(CatalogError):
        scan(tree).declared()


def test_stale_known_defect_is_reported(tree: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ontology_catalog, "KNOWN_DEFECTS", {"ontology/a/spec/a.ttl": "was broken"})
    problems, known = check(tree)
    assert known == []
    assert problems == ["ontology/a/spec/a.ttl: listed in KNOWN_DEFECTS (was broken) but no longer defective, remove the entry"]


def test_generation_is_deterministic() -> None:
    assert expected_files(ROOT) == expected_files(ROOT)


def test_behaviour_closure_reaches_every_layer_below_it() -> None:
    graph = closure(Catalog(ROOT_CATALOG), version_iri("ontology/behaviour/spec/behaviour.ttl"))
    subjects = {str(s) for s in graph.subjects()}
    for layer in ("foundation", "vocabulary", "quantification", "party", "eligibility", "instrument", "behaviour"):
        assert any(s.startswith(f"{LATTICE}{layer}#") for s in subjects), layer


def test_applied_ontology_chains_to_lattice_catalog(tmp_path: Path) -> None:
    eligibility = version_iri("ontology/eligibility/spec/eligibility.ttl")
    (tmp_path / "applied.ttl").write_text(ontology("https://example.org/applied", (eligibility,)))
    relative = Path(os.path.relpath(ROOT_CATALOG, tmp_path)).as_posix()
    (tmp_path / "catalog-v001.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<catalog xmlns="urn:oasis:names:tc:entity:xmlns:xml:catalog">\n'
        '    <uri name="https://example.org/applied/1.0.0" uri="applied.ttl"/>\n'
        f'    <nextCatalog catalog="{relative}"/>\n'
        "</catalog>\n"
    )
    graph = closure(Catalog(tmp_path / "catalog-v001.xml"), "https://example.org/applied/1.0.0")
    assert (Namespace(f"{LATTICE}eligibility#").Condition, RDF.type, OWL.Class) in graph
