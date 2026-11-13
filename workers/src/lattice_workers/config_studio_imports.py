"""The validation of a workspace's baseline (SVA-B2b, ADR-A88). No AMQP and no HTTP.

It reports one thing for now: an `owl:imports` that no held import declares, as a warning that never blocks (SVA-Q7).
"""

from __future__ import annotations

from typing import Iterable, List, Set, Tuple

from rdflib import Graph, URIRef
from rdflib.namespace import OWL, RDF

from .config_studio_jobs import SH, _Result


def _named_ontologies(graph: Graph) -> List[URIRef]:
    return sorted(n for n in graph.subjects(RDF.type, OWL.Ontology) if isinstance(n, URIRef))


def _names(graph: Graph, ontology: URIRef) -> Set[str]:
    """The ontology IRI and each version IRI it declares, which an `owl:imports` may name."""
    return {str(ontology)} | {str(v) for v in graph.objects(ontology, OWL.versionIRI) if isinstance(v, URIRef)}


def _held_names(held: Iterable[Graph]) -> Set[str]:
    """What the held imports declare. A document that declares no single named `owl:Ontology` declares no name, since nothing
    says which ontology it is (the same rule the fence job applies to cst:declaresOntology)."""
    names: Set[str] = set()
    for document in held:
        ontologies = _named_ontologies(document)
        if len(ontologies) == 1:
            names |= _names(document, ontologies[0])
    return names


def missing_imports(baseline: Graph, held: Iterable[Graph]) -> List[Tuple[URIRef, URIRef]]:
    """The (importing ontology, imported IRI) pairs, sorted, that name no held import and not the baseline itself. The
    importers are every named ontology of the baseline and of each held import."""
    held = list(held)
    known = _held_names(held)
    for ontology in _named_ontologies(baseline):
        known |= _names(baseline, ontology)
    found: Set[Tuple[URIRef, URIRef]] = set()
    for document in (baseline, *held):
        for ontology in _named_ontologies(document):
            for target in document.objects(ontology, OWL.imports):
                if isinstance(target, URIRef) and str(target) not in known:
                    found.add((ontology, target))
    return sorted(found, key=lambda pair: (str(pair[0]), str(pair[1])))


def validate_baseline(job: URIRef, baseline: Graph, held: Iterable[Graph]) -> Graph:
    """The finished job's triples. A warning does not stop the baseline conforming. Only an import the baseline's own ontology
    states has the baseline's ontology as its focus node. One a held import states has that held import's ontology, since
    nothing else would say it is missing."""
    result = _Result(job)
    for importer, target in missing_imports(baseline, held):
        result.finding(
            SH.Warning,
            f"{importer} imports {target}, and no held document declares that IRI as its ontology IRI or version IRI. "
            "Add the document that declares it to the imports.",
            "ImportNotHeld", importer, OWL.imports, target,
        )
    result.conforms(True)
    return result.graph
