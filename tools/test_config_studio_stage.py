# SPDX-License-Identifier: MPL-2.0
"""Tests `tools/config_studio_stage.py` against the repository's own samples (ADR-A136)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import OWL, RDF

sys.path.insert(0, str(Path(__file__).resolve().parent))

import lattice_repo_catalogue  # noqa: E402
from config_studio_stage import CST, stage  # noqa: E402

DAL = Namespace("https://www.nebularis.org/neuro-semantic/lattice/persistence#")
SRF = Namespace("https://www.nebularis.org/neuro-semantic/lattice/surface#")


@pytest.fixture(scope="module")
def staged(tmp_path_factory: pytest.TempPathFactory) -> Path:
    out = tmp_path_factory.mktemp("config-studio")
    stage(lattice_repo_catalogue.find_root(), out)
    return out


def test_vocabulary_merges_the_persistence_and_surface_specifications(staged: Path) -> None:
    g = Graph().parse(staged / "vocabulary.ttl")
    assert (DAL.strategy, RDF.type, OWL.ObjectProperty) in g
    assert (SRF.NominalClass, RDF.type, SRF.IndexForm) in g
    assert (URIRef("https://www.nebularis.org/neuro-semantic/lattice/eligibility#HierarchicalMatch"), None, None) in g
    assert (URIRef("https://www.nebularis.org/neuro-semantic/lattice/quantification#ValueSpace"), None, None) in g


def test_vocabulary_carries_the_form_shapes_and_no_sparql_constraints(staged: Path) -> None:
    sh = Namespace("http://www.w3.org/ns/shacl#")
    g = Graph().parse(staged / "vocabulary.ttl")
    assert (DAL.ProfileScopeShape, sh.targetClass, DAL.ProfileScope) in g
    assert (None, sh.maxCount, None) in g
    assert not list(g.subjects(sh.sparql, None))
    assert not list(g.subjects(sh.select, None))
    assert not list(g.subjects(sh.message, None))


def test_every_sample_is_listed_without_its_parts_and_staged_merged(staged: Path) -> None:
    listing = Graph().parse(staged / "samples.ttl")
    samples = sorted(str(s) for s in listing.subjects(RDF.type, CST.Sample))
    assert samples == [
        f"urn:lattice:studio:sample:{n}"
        for n in ("builder", "employment", "facility", "legalruleml-mappings", "lending", "lending-eligibility", "odrl-mappings", "policies-transforms", "quantities", "saas",
                  "vocabulary-bindings")
    ]
    assert not list(listing.objects(None, CST.part))
    lending = Graph().parse(staged / "samples" / "lending.ttl")
    assert (URIRef("https://example.org/lending#LoanApplication"), RDF.type, OWL.Class) in lending
    assert (URIRef("https://example.org/lending#LoanApplicationStrongProfile"), RDF.type, DAL.DataAccessProfile) in lending


def test_the_policies_sample_offers_each_examples_source_as_it_is(staged: Path) -> None:
    """The sources mapping mode offers are the files `tools/mork_transforms` tests the transforms on."""
    catalogue = lattice_repo_catalogue.load(lattice_repo_catalogue.find_root())
    example = catalogue.root / catalogue.area("tools") / "mork_transforms" / "tests" / "examples" / "policies"
    sample = Graph().parse(staged / "samples" / "policies-transforms.ttl")
    skos = URIRef("http://www.w3.org/2004/02/skos/core#example")
    for fmt in ("xml", "json"):
        offered = sample.value(URIRef(f"urn:example:source/{fmt}#Source"), skos)
        assert str(offered) == (example / f"source.{fmt}").read_text(encoding="utf-8")


def test_a_sample_naming_a_missing_file_is_refused(tmp_path: Path) -> None:
    import config_studio_stage

    root = lattice_repo_catalogue.find_root()
    catalogue = lattice_repo_catalogue.load(root)
    manifest = Graph()
    sample = URIRef("urn:lattice:studio:sample:broken")
    part = URIRef("urn:part")
    manifest.add((sample, CST.part, part))
    manifest.add((part, CST.fileName, Literal("absent.ttl")))
    with pytest.raises(SystemExit, match="absent.ttl"):
        config_studio_stage.sample_files(catalogue, manifest, sample, tmp_path)


def test_the_units_of_publication_are_staged_each_with_a_root_class_and_a_part(staged: Path) -> None:
    """ADR-A149: the service serves the units table to the browser."""
    from rdflib import Graph, Namespace
    from rdflib.namespace import RDF

    cst = Namespace("https://www.nebularis.org/neuro-semantic/lattice/config-studio#")
    units = Graph().parse(staged / "publication-units.ttl", format="turtle")
    kinds = list(units.subjects(RDF.type, cst.PublicationUnit))
    assert len(kinds) >= 10
    assert all(units.value(u, cst.rootClass) is not None and units.value(u, cst.authoredIn) is not None for u in kinds)


def test_the_studio_s_persistence_profile_is_compiled_with_its_operations(staged: Path) -> None:
    """ADR-A149 decisions 12 and 13: one target per family, each with the operations the writer runs."""
    folder = staged / "persistence"
    assert (folder / "profile.ttl").is_file()
    targets = sorted(p.name for p in folder.iterdir() if p.is_dir())
    assert targets == ["Document", "FencedImport", "Lineage", "Part", "PublishedVersion", "Workspace"]
    for target in targets:
        assert {"create-if-absent.rq", "cas-replace.rq", "tombstone-delete.rq"} <= {p.name for p in (folder / target).iterdir()}
    # The caller names each root's graph, and a part's replace writes the patch log's delta.
    replace = (folder / "Part" / "cas-replace.rq").read_text(encoding="utf-8")
    assert "$g" in replace and "{{{assertTriples}}}" in replace and "{{{retractTriples}}}" in replace
    assert "{{{assertTriples}}}" not in (folder / "Workspace" / "cas-replace.rq").read_text(encoding="utf-8")


def test_the_projections_are_staged_as_six_promotions_and_the_summaries_query(staged: Path) -> None:
    from surface.model import read_contracts

    contracts = Graph().parse(staged / "projections" / "projections.ttl", format="turtle")
    assert sorted(c.key for c in read_contracts(contracts)) == [
        "holders-follows", "holders-imports", "jobs", "registry", "terms-label", "terms-version"]
    assert all(str(c.promotes_to).startswith("https://www.nebularis.org/neuro-semantic/lattice/config-studio/projection#") for c in read_contracts(contracts))
    assert "CONSTRUCT" in (staged / "projections" / "workspace-summaries.rq").read_text(encoding="utf-8")
