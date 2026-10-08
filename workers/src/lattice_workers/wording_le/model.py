"""Reads the Wording layer (CCS sketch section 4) of one document from an rdflib graph."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import rdflib
from rdflib.namespace import DCTERMS, RDF, RDFS

from .namespaces import WAP, WRD


@dataclass(frozen=True)
class Part:
    index: int
    kind: str  # "literal" | "variable" | "reference"
    text: str
    variable_key: Optional[str] = None
    target_element_id: Optional[str] = None


@dataclass(frozen=True)
class Element:
    element_id: str
    iri: str
    object_id: str
    section_key: str
    kind: str  # "clause" | "definition"
    defined_term: Optional[str]
    parts: tuple[Part, ...]

    @property
    def text(self) -> str:
        return "".join(part.text for part in self.parts)


@dataclass(frozen=True)
class Variable:
    key: str
    iri: str
    label: str
    value_type: str


@dataclass(frozen=True)
class Wording:
    iri: str
    document_id: str
    title: str
    template_id: str
    revision: int
    elements: tuple[Element, ...]
    variables: tuple[Variable, ...]


def load_wording(graph: rdflib.Graph, wording_iri: str) -> Wording:
    wording = rdflib.URIRef(wording_iri)
    if (wording, RDF.type, WRD.Wording) not in graph:
        raise ValueError(f"no wrd:Wording at {wording_iri}")

    document_id = _require(graph, wording, WAP.documentId)
    title = _require(graph, wording, DCTERMS.title)
    template_id = _require(graph, wording, WAP.templateId)
    revision = int(_require(graph, wording, WAP.revisionNumber))

    children = sorted(graph.objects(wording, WRD.directlyComprises), key=lambda node: _rank_key(graph, node))
    section_nodes = [node for node in children if (node, WRD.elementType, WAP.Section) in graph]
    variable_nodes = [node for node in children if (node, RDF.type, WRD.EmbeddedVariable) in graph]

    variables = tuple(_load_variable(graph, node) for node in variable_nodes)

    elements: list[Element] = []
    for section_node in section_nodes:
        section_key = _require(graph, section_node, WAP.sectionKey)
        element_nodes = sorted(
            graph.objects(section_node, WRD.directlyComprises), key=lambda node: _rank_key(graph, node)
        )
        for element_node in element_nodes:
            elements.append(_load_element(graph, element_node, section_key))

    return Wording(wording_iri, document_id, title, template_id, revision, tuple(elements), variables)


def _load_variable(graph: rdflib.Graph, node: rdflib.term.Node) -> Variable:
    key = _require(graph, node, WRD.variableKey)
    label = _require(graph, node, RDFS.label)
    value_type_node = graph.value(node, WAP.valueType)
    if value_type_node is None:
        raise ValueError(f"{node} has no wap:valueType")
    value_type = str(value_type_node).rsplit("#", 1)[-1].lower()
    return Variable(key, str(node), label, value_type)


def _load_element(graph: rdflib.Graph, node: rdflib.term.Node, section_key: str) -> Element:
    element_id = _require(graph, node, WAP.elementId)
    object_id = _require(graph, node, WRD.objectId)
    kind = _element_kind(graph, node)
    defined_term = _optional(graph, node, WAP.definedTerm)
    part_nodes = sorted(graph.objects(node, WAP.hasPart), key=lambda part: int(_require(graph, part, WRD.partIndex)))
    parts = tuple(_load_part(graph, part_node, index) for index, part_node in enumerate(part_nodes))
    return Element(element_id, str(node), object_id, section_key, kind, defined_term, parts)


def _element_kind(graph: rdflib.Graph, node: rdflib.term.Node) -> str:
    element_type = graph.value(node, WRD.elementType)
    if element_type == WAP.Definition:
        return "definition"
    if element_type == WAP.Clause:
        return "clause"
    raise ValueError(f"{node} has unexpected wrd:elementType {element_type}")


def _load_part(graph: rdflib.Graph, node: rdflib.term.Node, index: int) -> Part:
    literal_text = graph.value(node, WRD.partText)
    if literal_text is not None:
        return Part(index, "literal", str(literal_text))

    variable_ref = graph.value(node, WRD.refersToVariable)
    if variable_ref is not None:
        display_text = _require(graph, node, WAP.displayText)
        variable_key = _require(graph, variable_ref, WRD.variableKey)
        return Part(index, "variable", display_text, variable_key=variable_key)

    object_ref = graph.value(node, WRD.refersToObject)
    if object_ref is not None:
        display_text = _require(graph, node, WAP.displayText)
        target_element_id = _require(graph, object_ref, WAP.elementId)
        return Part(index, "reference", display_text, target_element_id=target_element_id)

    raise ValueError(f"{node} is a wrd:TextPart with none of partText, refersToVariable, refersToObject")


def _rank_key(graph: rdflib.Graph, node: rdflib.term.Node) -> str:
    return _require(graph, node, WRD.rankKey)


def _optional(graph: rdflib.Graph, subject: rdflib.term.Node, predicate: rdflib.term.Node) -> Optional[str]:
    value = graph.value(subject, predicate)
    return str(value) if value is not None else None


def _require(graph: rdflib.Graph, subject: rdflib.term.Node, predicate: rdflib.term.Node) -> str:
    value = _optional(graph, subject, predicate)
    if value is None:
        raise ValueError(f"{subject} has no {predicate}")
    return value
