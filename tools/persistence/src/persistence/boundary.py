# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""Reading a ``dal:boundaryShape`` as a classified tree (ADR-A122, sketch §4).

A SHACL shape used as a boundary declaration is walked once, here, at compile time. No target
backend is ever asked to execute SHACL to determine where a write's boundary lies (ADR-A78
point 4). Every property shape that leads to a node carries ``dal:ownership``, and the owned edges
compile to one SPARQL property path (:mod:`persistence.paths`). Only ``sh:property``, ``sh:path``,
``sh:node``, ``sh:class`` and ``dal:ownership`` are interpreted. Any other SHACL construct in the
same shape (``sh:pattern``, ``sh:datatype``, and so on) is left untouched for the adopter's own
validation tooling.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from rdflib import Graph, URIRef
from rdflib.term import Node

from .functional import functional_value
from .namespaces import DAL, SH
from .paths import LEAF, PathExpr, Step, eliminate


class MissingBoundaryShapeError(Exception):
    """A CompositePropertyBoundary profile declared no dal:boundaryShape.

    Defence in depth: the SHACL shape
    ``dal:CompositePropertyBoundaryRequiresShapeShape`` in
    ``shapes/constraints.ttl`` should already have caught this before the
    compiler ever reaches resolution, but the compiler does not assume its
    own callers always ran that validation pass first.
    """


# ---------------------------------------------------------------------------------------------
# The classified tree (ADR-A122, sketch §4).

OWNED = "Owned"
REFERENCE = "Reference"
VOCABULARY = "Vocabulary"
VALUE = "Value"


@dataclass(frozen=True)
class Edge:
    """One property shape of an owned shape."""

    source_shape: URIRef
    property_shape: Node
    step: Step
    kind: str  # OWNED | REFERENCE | VOCABULARY | VALUE
    target_shape: URIRef | None  # the sh:node
    target_class: URIRef | None  # the sh:class, else the sh:targetClass of the sh:node


@dataclass
class OwnershipTree:
    """A boundary shape read as a classified tree. Classification problems are recorded and not raised, so
    the validator can name each as a refusal of its own."""

    root_shape: URIRef
    root_class: URIRef | None
    shapes: list[URIRef] = field(default_factory=list)  # owned shapes in visiting order, root first
    edges: list[Edge] = field(default_factory=list)  # every property shape of every owned shape, in walk order
    complex_paths: list[tuple[URIRef, Node]] = field(default_factory=list)  # (shape, property shape)
    unclassified: list[tuple[URIRef, Node, URIRef]] = field(default_factory=list)  # (shape, property shape, predicate)
    ownership_on_values: list[tuple[URIRef, Node, URIRef]] = field(default_factory=list)

    def owned_edges(self) -> list[Edge]:
        return [e for e in self.edges if e.kind == OWNED]

    def member_classes(self) -> set[URIRef]:
        """The classes of the nodes an owned edge leads to."""
        return {e.target_class for e in self.owned_edges() if e.target_class is not None}

    def predicates(self) -> set[URIRef]:
        """Every step predicate on every owned shape, of any kind."""
        return {e.step.predicate for e in self.edges}

    def owned_path(self) -> PathExpr | None:
        """The one path that reaches the root and every member, or ``None`` when no edge is owned."""
        owned = self.owned_edges()
        if not owned:
            return None
        transitions = [(e.source_shape, e.target_shape or LEAF, Step(e.step.predicate, e.step.inverse)) for e in owned]
        return eliminate([*self.shapes, LEAF], transitions, self.root_shape)


_KINDS = {DAL.Owned: OWNED, DAL.Reference: REFERENCE, DAL.Vocabulary: VOCABULARY}


def _step(graph: Graph, path: Node) -> Step | None:
    """The one step an ``sh:path`` names: an IRI, or ``[ sh:inversePath IRI ]``. Anything else is ``None``."""
    if isinstance(path, URIRef):
        return Step(path, False)
    triples = list(graph.predicate_objects(path))
    if len(triples) == 1 and triples[0][0] == SH.inversePath and isinstance(triples[0][1], URIRef):
        return Step(triples[0][1], True)
    return None


def _is_value(graph: Graph, property_shape: Node) -> bool:
    return (property_shape, SH.datatype, None) in graph or (property_shape, SH.nodeKind, SH.Literal) in graph


def walk_ownership(graph: Graph, root_shape: URIRef) -> OwnershipTree:
    """Read ``root_shape`` as a classified tree. Visits each owned shape once, in the order it is first
    queued, and each shape's property shapes in a total order independent of how the triples were written."""
    tree = OwnershipTree(root_shape=root_shape, root_class=functional_value(graph, root_shape, SH.targetClass))
    queue: list[URIRef] = [root_shape]
    while queue:
        shape = queue.pop(0)
        if shape in tree.shapes:
            continue
        tree.shapes.append(shape)
        entries = []
        for property_shape in graph.objects(shape, SH.property):
            path = functional_value(graph, property_shape, SH.path)
            step = _step(graph, path) if path is not None else None
            entries.append((str(step.predicate) if step else "", "1" if step and step.inverse else "0", str(property_shape), property_shape, step))
        for _, _, _, property_shape, step in sorted(entries, key=lambda entry: entry[:3]):
            if step is None:
                tree.complex_paths.append((shape, property_shape))
                continue
            declared = functional_value(graph, property_shape, DAL.ownership)
            if _is_value(graph, property_shape):
                if declared is not None:
                    tree.ownership_on_values.append((shape, property_shape, step.predicate))
                tree.edges.append(Edge(shape, property_shape, step, VALUE, None, None))
                continue
            if declared is None or declared not in _KINDS:
                tree.unclassified.append((shape, property_shape, step.predicate))
                continue
            target_shape = functional_value(graph, property_shape, SH.node)
            target_class = functional_value(graph, property_shape, SH["class"])
            if target_class is None and target_shape is not None:
                target_class = functional_value(graph, target_shape, SH.targetClass)
            kind = _KINDS[declared]
            tree.edges.append(Edge(shape, property_shape, step, kind, target_shape, target_class))
            if kind == OWNED and target_shape is not None:
                queue.append(target_shape)
    return tree


__all__ = [
    "MissingBoundaryShapeError",
    "Edge", "OwnershipTree", "walk_ownership", "OWNED", "REFERENCE", "VOCABULARY", "VALUE",
]
