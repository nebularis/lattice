# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""Walking a ``dal:boundaryShape`` into a closure definition (sketch §4.3).

A SHACL shape used as a boundary declaration is walked once, here, at
compile time. No target backend is ever asked to execute SHACL to
determine where a write's boundary lies (ADR-A78 point 4). Only
``sh:property``/``sh:path``/``sh:node`` recursion is interpreted; any other
SHACL construct in the same shape (``sh:pattern``, ``sh:datatype``, and so
on) is left untouched for the adopter's own validation tooling.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from rdflib import Graph, URIRef

from .namespaces import DAL, SH


class BoundaryCycleError(Exception):
    """The shape's sh:node recursion reaches back to an ancestor shape."""

    def __init__(self, shape: URIRef, path: list[URIRef]):
        self.shape = shape
        self.path = path
        chain = " -> ".join(str(s) for s in path + [shape])
        super().__init__(f"cycle in boundary shape recursion: {chain}")


class MissingBoundaryShapeError(Exception):
    """A CompositePropertyBoundary profile declared no dal:boundaryShape.

    Defence in depth: the SHACL shape
    ``dal:CompositePropertyBoundaryRequiresShapeShape`` in
    ``shapes/constraints.ttl`` should already have caught this before the
    compiler ever reaches resolution, but the compiler does not assume its
    own callers always ran that validation pass first.
    """


@dataclass
class Closure:
    """The compiled-down result of walking a boundary shape: which
    properties are composite, and to what depth."""

    root_shape: URIRef
    composite_properties: list[URIRef] = field(default_factory=list)
    max_depth_reached: int = 0


def walk_boundary_shape(graph: Graph, shape: URIRef, max_depth: int = 8) -> Closure:
    closure = Closure(root_shape=shape)
    _walk(graph, shape, max_depth, [], closure, depth=0)
    return closure


def _walk(
    graph: Graph,
    shape: URIRef,
    max_depth: int,
    ancestors: list[URIRef],
    closure: Closure,
    depth: int,
) -> None:
    if shape in ancestors:
        raise BoundaryCycleError(shape, ancestors)
    if depth > max_depth:
        return
    closure.max_depth_reached = max(closure.max_depth_reached, depth)
    for prop_shape in graph.objects(shape, SH.property):
        path = graph.value(prop_shape, SH.path)
        if path is not None and path not in closure.composite_properties:
            closure.composite_properties.append(path)
        node_shape = graph.value(prop_shape, SH.node)
        if node_shape is not None:
            _walk(graph, node_shape, max_depth, ancestors + [shape], closure, depth + 1)


def reachable_properties(graph: Graph, boundary_shape: URIRef, max_depth: int = 8) -> set[URIRef]:
    """The set of properties reachable within a boundary shape's closure,
    used by the validator to check a uniqueness constraint's key property
    does not leave the declared boundary (sketch §3.5, row 5)."""
    return set(walk_boundary_shape(graph, boundary_shape, max_depth).composite_properties)


__all__ = ["Closure", "walk_boundary_shape", "reachable_properties", "BoundaryCycleError", "MissingBoundaryShapeError"]
