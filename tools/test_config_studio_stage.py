# SPDX-License-Identifier: MPL-2.0
"""Tests `tools/config_studio_stage.py` against the repository's own samples (ADR-A136)."""

from __future__ import annotations

import csv
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.compare import isomorphic
from rdflib.namespace import OWL, RDF, RDFS

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
        for n in ("axioms", "builder", "employment", "facility", "legalruleml-mappings", "lending", "lending-eligibility", "library-imports", "odrl-mappings", "policies-csv",
                  "policies-transforms", "policies-yaml", "quantities", "saas", "species-mappings", "vocabulary-bindings")
    ]
    assert not list(listing.objects(None, CST.part))
    lending = Graph().parse(staged / "samples" / "lending.ttl")
    assert (URIRef("https://example.org/lending#LoanApplication"), RDF.type, OWL.Class) in lending
    assert (URIRef("https://example.org/lending#LoanApplicationStrongProfile"), RDF.type, DAL.DataAccessProfile) in lending


def test_the_library_sample_imports_two_layers_and_binds_a_scheme_of_its_own(staged: Path) -> None:
    sample = Graph().parse(staged / "samples" / "library-imports.ttl")
    ontology = URIRef("https://example.org/library")
    vocabulary = URIRef("https://www.nebularis.org/neuro-semantic/vocabulary")
    foundation = URIRef("https://www.nebularis.org/neuro-semantic/foundation")
    assert (ontology, RDF.type, OWL.Ontology) in sample
    # Stated: the baseline imports the vocabulary layer and not the foundation layer it imports.
    assert set(sample.objects(ontology, OWL.imports)) == {vocabulary}
    # Both layers are staged and answer by ontology IRI, the vocabulary layer importing the foundation layer.
    index = Graph().parse(staged / "ontologies" / "index.ttl")
    assert (vocabulary, RDF.type, OWL.Ontology) in index
    assert (foundation, RDF.type, OWL.Ontology) in index
    assert any(o in set(index.objects(vocabulary, OWL.imports)) for o in index.objects(foundation, OWL.versionIRI))
    # The baseline uses a foundation term, and a scheme contract's binding names a scheme of the sample.
    fnd = "https://www.nebularis.org/neuro-semantic/lattice/foundation#"
    assert (URIRef("https://example.org/library#CatalogueEntry"), RDFS.subClassOf, URIRef(f"{fnd}Governable")) in sample
    voc = "https://www.nebularis.org/neuro-semantic/lattice/vocabulary#"
    binding = URIRef("https://example.org/library#subject-binding")
    scheme = URIRef("https://example.org/library#SubjectHeadings")
    assert (binding, URIRef(f"{voc}bindsScheme"), scheme) in sample
    assert (scheme, RDF.type, URIRef(f"{voc}ConceptScheme")) in sample


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


def test_the_promotions_are_staged_as_six_promotions_and_the_summaries_query(staged: Path) -> None:
    from surface.model import read_contracts

    contracts = Graph().parse(staged / "promotions" / "promotions.ttl", format="turtle")
    assert sorted(c.key for c in read_contracts(contracts)) == [
        "holders-follows", "holders-imports", "jobs", "registry", "terms-label", "terms-version"]
    assert all(str(c.promotes_to).startswith("https://www.nebularis.org/neuro-semantic/lattice/config-studio/promotion#") for c in read_contracts(contracts))
    assert "CONSTRUCT" in (staged / "promotions" / "workspace-summaries.rq").read_text(encoding="utf-8")


def _ontology_index(staged: Path) -> Graph:
    return Graph().parse(staged / "ontologies" / "index.ttl", format="turtle")


def test_the_ontologies_are_staged_with_an_index_of_ontology_iri_version_iri_imports_and_file(staged: Path) -> None:
    """SVA-B2b: the service serves a LATTICE document by an IRI this index holds."""
    foundation = URIRef("https://www.nebularis.org/neuro-semantic/foundation")
    index = _ontology_index(staged)
    assert (foundation, RDF.type, OWL.Ontology) in index
    versions = [str(v) for v in index.objects(foundation, OWL.versionIRI)]
    assert len(versions) == 1 and versions[0].startswith("https://www.nebularis.org/neuro-semantic/lattice/foundation/")
    assert URIRef("http://www.w3.org/ns/prov-o-20130430") in set(index.objects(foundation, OWL.imports))
    file = index.value(foundation, CST.stagedAs)
    assert isinstance(file, Literal) and (staged / "ontologies" / str(file)).is_file()
    assert str(file).endswith(".ttl") and len(str(file)) == 64 + len(".ttl")
    # Every staged copy is an index entry's, and every entry's copy exists.
    assert sorted(p.name for p in (staged / "ontologies").iterdir() if p.name != "index.ttl") == sorted(str(o) for o in index.objects(None, CST.stagedAs))


def test_two_iris_of_one_file_share_one_staged_copy(staged: Path) -> None:
    """The catalog maps both the ontology IRI and the version IRI of MORK to one file."""
    import ontology_catalog

    root = lattice_repo_catalogue.find_root()
    entries = ontology_catalog.Catalog(root / "ontology" / "catalog-v001.xml").entries
    mork = [name for name, location in entries.items() if location == "mork/spec/Mork.ttl"]
    assert len(mork) >= 2
    index = _ontology_index(staged)
    nodes = [n for n in index.subjects(RDF.type, OWL.Ontology) if str(n) in mork]
    assert len(nodes) == 1
    assert len(list(index.objects(nodes[0], CST.stagedAs))) == 1


def test_staging_the_ontologies_twice_gives_byte_identical_output(staged: Path, tmp_path: Path) -> None:
    stage(lattice_repo_catalogue.find_root(), tmp_path)
    first = {p.relative_to(staged / "ontologies").as_posix(): p.read_bytes() for p in (staged / "ontologies").rglob("*") if p.is_file()}
    second = {p.relative_to(tmp_path / "ontologies").as_posix(): p.read_bytes() for p in (tmp_path / "ontologies").rglob("*") if p.is_file()}
    assert first == second and "index.ttl" in first


def test_a_document_that_declares_no_single_named_ontology_is_skipped_and_counted(tmp_path: Path) -> None:
    import config_studio_stage

    root = tmp_path / "ontology"
    root.mkdir()
    (root / "catalog-v001.xml").write_text(
        '<catalog xmlns="urn:oasis:names:tc:entity:xmlns:xml:catalog">'
        '<uri name="urn:x:one" uri="one.ttl"/><uri name="urn:x:two" uri="two.ttl"/><uri name="urn:x:web" uri="https://example.org/w.ttl"/>'
        '<uri name="urn:x:gone" uri="gone.ttl"/></catalog>', encoding="utf-8")
    prefix = "@prefix owl: <http://www.w3.org/2002/07/owl#> .\n"
    (root / "one.ttl").write_text(prefix + "<urn:x:one> a owl:Ontology .\n", encoding="utf-8")
    (root / "two.ttl").write_text(prefix + "<urn:x:a> a owl:Ontology . <urn:x:b> a owl:Ontology .\n", encoding="utf-8")

    class Fake:
        root = tmp_path

        @staticmethod
        def area(name: str) -> Path:
            return Path("ontology")

    staged, skipped = config_studio_stage.stage_ontologies(Fake, tmp_path / "out")  # type: ignore[arg-type]
    assert staged == 1
    assert skipped == {"declaring no single named ontology": 1}
    assert len(list((tmp_path / "out").iterdir())) == 2


# --- The samples' README (SVA-D1) ----------------------------------------------------------------------------------------------------

MORK = Namespace("http://www.nebularis.org/ontologies/Mork#")
SKOS_EXAMPLE = URIRef("http://www.w3.org/2004/02/skos/core#example")


def _folders() -> tuple[Path, Path]:
    catalogue = lattice_repo_catalogue.load(lattice_repo_catalogue.find_root())
    return catalogue.root / catalogue.area("contracts") / "config-studio" / "samples", catalogue.root / catalogue.area("tools") / "mork_transforms" / "tests" / "examples" / "policies"


def _slug(heading: str) -> str:
    """The anchor a Markdown renderer gives a heading: lower case, punctuation dropped, spaces as hyphens."""
    return re.sub(r"\s", "-", re.sub(r"[^\w\s-]", "", heading.strip().lower()))


def _anchors(path: Path) -> set[str]:
    in_fence, found = False, set()
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("```"):
            in_fence = not in_fence
        elif not in_fence and (m := re.match(r"#{1,6}\s+(.*)", line)):
            found.add(_slug(m.group(1)))
    return found


def test_every_file_the_samples_readme_links_exists_and_every_file_of_the_folder_is_linked() -> None:
    samples, _ = _folders()
    readme = samples / "README.md"
    text = readme.read_text(encoding="utf-8")
    targets = re.findall(r"\]\(([^)\s]+)\)", text)
    assert targets, "the README links its documents"
    linked: set[Path] = set()
    for target in targets:
        if re.match(r"[a-z][a-z0-9+.-]*:", target):
            continue
        name, _, fragment = target.partition("#")
        path = (readme.parent / name).resolve() if name else readme
        assert path.exists(), f"{target} is linked and does not exist"
        if fragment and path.suffix == ".md":
            assert fragment in _anchors(path), f"{target} names a heading that {path.name} does not have"
        linked.add(path)
    folder = {p.resolve() for p in samples.rglob("*") if p.is_file() and p.name not in ("README.md", "samples.ttl") and "__pycache__" not in p.parts}
    assert not (folder - linked), f"files of the samples folder that the README does not link: {sorted(p.name for p in folder - linked)}"


def test_every_studio_sample_the_samples_readme_names_is_listed_and_loads_and_every_listed_sample_is_named(staged: Path) -> None:
    samples, _ = _folders()
    text = (samples / "README.md").read_text(encoding="utf-8")
    named: dict[str, str] = {}
    for line in re.findall(r"^\*\*Studio sample:\*\* (.+)$", text, flags=re.MULTILINE):
        for label, key in re.findall(r"([A-Z][^()`]*?) \(`([a-z0-9-]+)`\)", line):
            named[key] = label
        if not re.search(r"\(`[a-z0-9-]+`\)", line):
            assert line.startswith("none"), f"a Studio sample line that names no sample says none: {line}"
    listing = Graph().parse(staged / "samples.ttl")
    listed = {str(s)[len("urn:lattice:studio:sample:"):]: str(listing.value(s, RDFS.label)) for s in listing.subjects(RDF.type, CST.Sample)}
    assert set(named) == set(listed), "the README names each studio sample once or more, and no other"
    for key, label in named.items():
        assert listed[key] == label, f"the README calls {key} {label!r} and samples.ttl calls it {listed[key]!r}"
        loaded = Graph().parse(staged / "samples" / f"{key}.ttl")
        assert len(loaded) > 0, f"sample {key} loads empty"
    # The README's own table lists each sample by its key too.
    for key in listed:
        assert f"`{key}`" in text


def test_the_imports_folder_resolves_two_imports_the_second_by_a_file_of_an_unrelated_name_and_leaves_one_missing() -> None:
    samples, _ = _folders()
    folder = samples / "imports"
    imports = {str(o) for o in Graph().parse(folder / "base.ttl").objects(None, OWL.imports)}
    assert len(imports) == 3
    root = ET.parse(folder / "catalog-v001.xml").getroot()
    entries = {e.get("name"): e.get("uri") for e in root if e.tag.endswith("}uri")}
    declared = {}
    for file in sorted(folder.glob("*.ttl")):
        for ontology in Graph().parse(file).subjects(RDF.type, OWL.Ontology):
            declared[str(ontology)] = file.name
    resolved = {iri: entries[iri] for iri in imports if iri in entries}
    assert len(resolved) == 2 and set(entries) == set(resolved), "the catalog names two of the three imports and no other"
    for iri, file in resolved.items():
        assert (folder / file).is_file() and declared[iri] == file, f"{iri} is declared by the file the catalog names"
    unrelated = [iri for iri, file in resolved.items() if iri.rsplit("/", 1)[-1] not in file]
    assert len(unrelated) == 1, "one resolved file is named by nothing in its ontology's IRI"
    (missing,) = imports - set(resolved)
    assert missing not in declared, "no dropped file declares the third import"


def test_the_species_sample_runs_in_two_strata_with_a_closure_over_its_own_example() -> None:
    from mork_rdf import compile_scheme, run

    samples, _ = _folders()
    mapping = Graph().parse(samples / "species-mappings.ttl")
    scheme = "https://example.org/zoo/mapping#Scheme"
    compiled = compile_scheme(mapping, scheme, base="https://example.org/zoo/out/", at=__import__("datetime").datetime(2026, 11, 25, tzinfo=__import__("datetime").timezone.utc))
    assert not compiled.errors and compiled.strata == 2 and len(compiled.closures) == 1
    examples = list(mapping.subject_objects(SKOS_EXAMPLE))
    assert len(examples) == 1, "the scheme's representation scheme carries one example source"
    result = run(compiled, Graph().parse(data=str(examples[0][1]), format="turtle"))
    assert {(f.code, str(f.value)) for f in result.findings} == {("LookupUnresolved", "Dodo")}


def test_the_odrl_turtle_source_beside_the_json_ld_holds_the_triples_of_the_trials_copy() -> None:
    samples, _ = _folders()
    odrl = samples.parent / "odrl"
    assert (odrl / "software-licence.odrl.jsonld").is_file()
    assert isomorphic(Graph().parse(odrl / "software-licence.odrl.ttl"), Graph().parse(odrl / "trial" / "software-licence.ttl"))


def test_the_csv_and_yaml_sources_hold_the_policies_of_the_json_source_and_each_scheme_reads_what_they_name() -> None:
    import yaml

    _, policies = _folders()
    original = json.loads((policies / "source.json").read_text(encoding="utf-8"))
    assert yaml.safe_load((policies / "source.yaml").read_text(encoding="utf-8")) == original
    with (policies / "source.csv").open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    assert rows == [{"policy": p["number"], "holder": p["holder"], "cover": c["code"]} for p in original["policies"] for c in p["covers"]]
    scheme = Graph().parse(policies / "csv.mork.ttl")
    assert {str(o) for o in scheme.objects(None, MORK.dataRef)} <= set(rows[0]), "each column the CSV scheme names is a column of the source"
    assert (URIRef("urn:example:source/csv#Source"), MORK["format"], MORK.CSV) in scheme
    assert (URIRef("urn:example:source/yaml#Source"), MORK["format"], MORK.YAML) in Graph().parse(policies / "yaml.mork.ttl")


@pytest.mark.parametrize("name", ["csv", "yaml"])
def test_a_scheme_over_csv_or_yaml_compiles_to_rml_alone_as_the_sample_pane_lists_it_waiting(name: str) -> None:
    from lattice_workers import config_studio_jobs as jobs

    root = lattice_repo_catalogue.find_root()
    _, policies = _folders()
    job = URIRef(f"urn:lattice:studio:job:{name}")
    done = jobs.run_job(job, "compile", "mapping", Graph().parse(policies / f"{name}.mork.ttl"), Graph(), root, "2026-11-25T00:00:00Z")
    assert (job, jobs.CST.conforms, Literal(True)) in done
    artefacts = {str(done.value(a, jobs.CST.path)): str(done.value(a, jobs.CST.group)) for a in done.subjects(RDF.type, jobs.CST.Artefact)}
    assert artefacts["mapping.rml.ttl"] == f"urn:example:mapping/{name}#Scheme"
    assert not any(path.endswith((".xsl", ".jolt.json")) for path in artefacts), "no transform reads the format, so the RML form is the only one"
