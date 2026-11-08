# SPDX-License-Identifier: MPL-2.0
"""The seam for a read case. A reader that lives outside the repository writes what it read from a document's body as
a Turtle graph in the `vrig:` vocabulary, facts of documents with their locators in the blind view or a rendering's. The
tool validates it against the module's shapes, refuses one that does not conform, and compares what it states with the
declared view: a fact of the same document and key whose value or state differs is a disagreement, located at the
declared fact, about both. The comparison runs unchanged whatever wrote the read case."""

from __future__ import annotations

import logging
from pathlib import Path

from pyshacl import validate
from rdflib import RDF, Graph, URIRef

from . import canon
from .cases import fact_value
from .lift import VRIG

log = logging.getLogger("v_rig")


class ReadCaseError(Exception):
    """A read case the shapes refuse."""


def module_graphs() -> tuple[Graph, Graph]:
    import lattice_repo_catalogue as reader
    module = reader.load().module("v-rig")
    spec, shapes = Graph(), Graph()
    for path in module.files("spec") + module.files("vocab"):
        spec.parse(path, format="turtle")
    for path in module.files("shapes"):
        shapes.parse(path, format="turtle")
    return spec, shapes


def load(path: Path, graphs: tuple[Graph, Graph] | None = None) -> Graph:
    """The read case, parsed and validated. Refused with the validation report where the shapes do not conform."""
    spec, shapes = graphs if graphs is not None else module_graphs()
    case = Graph().parse(path, format="turtle")
    conforms, _, text = validate(case + spec, shacl_graph=shapes, inference="rdfs", advanced=True)
    if not conforms:
        raise ReadCaseError(f"the read case {path} does not conform to the v-rig shapes:\n{text}")
    log.info("read case %s: %d fact(s)", path.name, len(list(case.subjects(RDF.type, VRIG.Fact))))
    return case


def _declared_facts(graph: Graph) -> dict[tuple[str, str], URIRef]:
    found: dict[tuple[str, str], URIRef] = {}
    for fact in graph.subjects(RDF.type, VRIG.Fact):
        locator = graph.value(fact, VRIG.locator)
        if locator is None or graph.value(locator, VRIG.view) != VRIG.Declared:
            continue
        carrier = graph.value(fact, VRIG.of)
        if (carrier, RDF.type, VRIG.Document) not in graph:
            continue
        found[(str(graph.value(carrier, VRIG.rigId)), str(graph.value(fact, VRIG.key)))] = fact
    return found


def compare(graph: Graph, case: Graph) -> list[tuple[URIRef, URIRef, str | None, str, URIRef | None]]:
    """Disagreements between the read case and the declared view, as findings. A read fact's document is the id its
    locator names, and its carrier may be any node, since the reader's documents are its own."""
    declared = _declared_facts(graph)
    findings = []
    for fact in sorted(case.subjects(RDF.type, VRIG.Fact), key=str):
        locator = case.value(fact, VRIG.locator)
        key = case.value(fact, VRIG.key)
        if locator is None or key is None:
            continue
        document = str(case.value(locator, VRIG.documentId))
        stated = declared.get((document, str(key)))
        if stated is None:
            continue
        if canon.json_canonical(fact_value(case, fact)) != canon.json_canonical(fact_value(graph, stated)):
            findings.append((VRIG.Disagreement, graph.value(stated, VRIG.locator), str(key),
                             "The declared value and the value read from the body differ.", fact))
    log.info("read case compared: %d disagreement(s)", len(findings))
    return findings


def add_read_case(graph: Graph, case: Graph) -> None:
    """Carry the read case's nodes into the representation, so a disagreement's `vrig:about` resolves there too."""
    graph += case
