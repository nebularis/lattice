# SPDX-License-Identifier: MPL-2.0

"""Foundation's derived-artefact contract and the PROV-O alignment of Surface
and Executable (ADR-A92). Imports are resolved through the repository catalog
(ADR-A88). External documents (PROV-O itself) are not fetched."""

from __future__ import annotations

import sys
from pathlib import Path

import owlrl
from rdflib import Graph, Namespace, URIRef
from rdflib.namespace import OWL, RDF, RDFS

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent / "mork_compilers" / "src"))

from ontology_catalog import Catalog, closure  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
CATALOG = Catalog(ROOT / "ontology" / "catalog-v001.xml")
PROV = Namespace("http://www.w3.org/ns/prov#")
FND = Namespace("https://www.nebularis.org/neuro-semantic/lattice/foundation#")
SRF = Namespace("https://www.nebularis.org/neuro-semantic/lattice/surface#")
EXE = Namespace("https://www.nebularis.org/neuro-semantic/lattice/executable#")
KINDS = {"Inferred", "Validated", "Materialised", "Projected", "Indexed", "Generated", "Compiled", "DecisionRecord"}


def document(relative: str) -> Graph:
    return Graph().parse(ROOT / "ontology" / relative)


def test_foundation_declares_the_derived_artefact_contract() -> None:
    spec = document("foundation/spec/foundation.ttl")
    assert (FND.DerivedArtefact, RDFS.subClassOf, PROV.Entity) in spec
    assert (FND.DerivationRun, RDFS.subClassOf, PROV.Activity) in spec
    assert (FND.derivationKind, RDFS.range, FND.DerivationKind) in spec
    assert (FND.derivationKind, RDF.type, OWL.FunctionalProperty) not in spec
    vocab = document("foundation/vocab/foundation-vocab.ttl")
    assert {str(k).rsplit("#", 1)[1] for k in vocab.subjects(RDF.type, FND.DerivationKind)} == KINDS


def test_surface_derived_artefact_is_a_foundation_derived_artefact() -> None:
    assert (SRF.DerivedArtefact, RDFS.subClassOf, FND.DerivedArtefact) in document("surface/spec/surface.ttl")


def test_executable_aligns_directly_to_prov_o() -> None:
    spec = document("mork/spec/Executable.ttl")
    ontology = next(spec.subjects(RDF.type, OWL.Ontology))
    imports = {str(i) for i in spec.objects(ontology, OWL.imports)}
    assert "http://www.w3.org/ns/prov-o-20130430" in imports
    assert not any("lattice/foundation" in i for i in imports)
    for cls in (EXE.ExecutablePlan, EXE.GeneratedArtefact):
        assert (cls, RDFS.subClassOf, PROV.Entity) in spec
    for prop in (EXE.derivedFromEligibilityNode, EXE.derivedFromQuantificationNode,
                 EXE.derivedFromVocabularyNode, EXE.compiledFromMapping):
        assert (prop, RDFS.subPropertyOf, PROV.wasDerivedFrom) in spec


def test_compiled_plans_and_their_sources_are_prov_entities() -> None:
    from mork_compilers import compile_concept_condition
    from mork_compilers.sparql_backend import compile_query_template

    example = Graph().parse(ROOT / "ontology/eligibility/examples/condition-taxonomy.ttl")
    condition = URIRef("https://example.org/lattice/eligibility/exact-condition")
    artefact = compile_query_template(compile_concept_condition(example, condition))
    executable = closure(CATALOG, "https://www.nebularis.org/neuro-semantic/lattice/executable")
    # PROV-O's own domain and range for prov:wasDerivedFrom, since it is not fetched
    executable.add((PROV.wasDerivedFrom, RDFS.domain, PROV.Entity))
    executable.add((PROV.wasDerivedFrom, RDFS.range, PROV.Entity))
    graph = executable + artefact
    owlrl.DeductiveClosure(owlrl.RDFS_Semantics).expand(graph)
    plan = next(artefact.subjects(RDF.type, EXE.ConceptMatchPlan))
    assert (plan, RDF.type, PROV.Entity) in graph
    assert (condition, RDF.type, PROV.Entity) in graph
