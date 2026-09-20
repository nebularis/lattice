"""Conservative rendering of simple OWL class expressions for teaching text."""

from __future__ import annotations

from rdflib import BNode, Graph, URIRef
from rdflib.namespace import OWL

from .codebook import code_for


def render(graph: Graph, node: URIRef | BNode) -> str:
    if isinstance(node, URIRef):
        return code_for(str(node)) or f"<{node}>"
    restriction_property = graph.value(node, OWL.onProperty)
    some = graph.value(node, OWL.someValuesFrom)
    if restriction_property and some:
        return f"exists {render(graph, restriction_property)}.{render(graph, some)}"
    return node.n3()