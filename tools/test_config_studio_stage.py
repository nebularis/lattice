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
