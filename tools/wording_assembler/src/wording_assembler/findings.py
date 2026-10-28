# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""Findings as `sh:ValidationResult`s in an `sh:ValidationReport`, the form the studio worker reports
(its code predicate is the studio's, `cst:code`). The code names the stage that gave the finding
(ADR-A139 decision 6)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from rdflib import BNode, Graph, Literal, URIRef
from rdflib.namespace import RDF, SH, XSD

STAGES = ("load", "validate", "decide", "assemble", "record")
CODE = URIRef("https://www.nebularis.org/neuro-semantic/lattice/config-studio#code")


@dataclass(frozen=True)
class Finding:
    stage: str
    message: str
    focus: Optional[URIRef]
    value: Optional[URIRef]
    severity: URIRef


def report() -> Graph:
    graph = Graph()
    graph.add((BNode("report"), RDF.type, SH.ValidationReport))
    return graph


def add(graph: Graph, stage: str, message: str, focus=None, value=None, severity: URIRef = SH.Violation) -> None:
    assert stage in STAGES, stage
    node = BNode()
    graph.add((BNode("report"), SH.result, node))
    graph.add((node, RDF.type, SH.ValidationResult))
    graph.add((node, SH.resultSeverity, severity))
    graph.add((node, SH.resultMessage, Literal(message)))
    graph.add((node, CODE, Literal(stage)))
    for predicate, term in ((SH.focusNode, focus), (SH.value, value)):
        if term is not None:
            graph.add((node, predicate, term))


def merge(into: Graph, other: Graph) -> None:
    into += other


def findings(graph: Graph) -> List[Finding]:
    """The findings of a report, ordered by stage, then message, then focus."""
    found = [
        Finding(str(graph.value(r, CODE)), str(graph.value(r, SH.resultMessage)), graph.value(r, SH.focusNode),
                graph.value(r, SH.value), graph.value(r, SH.resultSeverity))
        for r in graph.subjects(RDF.type, SH.ValidationResult)
    ]
    return sorted(found, key=lambda f: (STAGES.index(f.stage) if f.stage in STAGES else 9, f.message, str(f.focus)))


def conforms(graph: Graph) -> bool:
    """True when no finding is a violation."""
    return not any(f.severity == SH.Violation for f in findings(graph))


def seal(graph: Graph) -> Graph:
    graph.set((BNode("report"), SH.conforms, Literal(conforms(graph), datatype=XSD.boolean)))
    return graph
