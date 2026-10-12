# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""An in-memory Oxigraph engine for tests, checks and benchmarks (ADR-A125).

This names no interface beyond what its users need, and it is not a store SPI. The persistence compiler's tests run
generated SPARQL on rdflib. Oxigraph is a second, independent engine (a Rust implementation), so that a conclusion
about what a generated update does to data does not rest on one engine.

The compiler leaves the caller's parameters as ``$name`` variables in the generated text. :meth:`OxigraphStore.update`
fills them by substituting each value as SPARQL term text, which is what a caller's own client would do when it has no
initial-binding API. A name left out stays an ordinary, unbound variable, which is how a caller's omission is reproduced.

The substitution is textual and does not look inside string literals, IRIs or comments. The generated templates have
none that contain a parameter name.
"""

from __future__ import annotations

import re
from typing import Iterable, Mapping

import pyoxigraph as ox

XSD = "http://www.w3.org/2001/XMLSchema#"
Term = ox.NamedNode | ox.Literal | ox.BlankNode


def iri(value: str) -> ox.NamedNode:
    return ox.NamedNode(value)


def literal(value, datatype: str | None = None) -> ox.Literal:
    """A literal. An int gets ``xsd:integer`` unless a datatype is given."""
    if datatype is None and isinstance(value, int) and not isinstance(value, bool):
        datatype = XSD + "integer"
    return ox.Literal(str(value), datatype=ox.NamedNode(datatype)) if datatype else ox.Literal(str(value))


def bind_parameters(text: str, parameters: Mapping[str, Term], strict: bool = True) -> str:
    """Replace each ``$name`` and ``?name`` for the given parameters with its term.

    SPARQL treats ``$x`` and ``?x`` as one variable, so both spellings are replaced. With ``strict`` a parameter that
    never appears in the text is an error, since a misspelt name would otherwise leave the real variable silently
    unbound."""
    if not parameters:
        return text
    pattern = re.compile(r"[$?](%s)\b" % "|".join(re.escape(n) for n in parameters))
    used: set[str] = set()

    def substitute(match: re.Match) -> str:
        used.add(match.group(1))
        return str(parameters[match.group(1)])

    bound = pattern.sub(substitute, text)
    if strict and (missing := sorted(set(parameters) - used)):
        raise ValueError(f"parameter(s) {', '.join(missing)} do not appear in the update")
    return bound


class OxigraphStore:
    """An in-memory quad store that runs SPARQL 1.1 Update and Query."""

    def __init__(self) -> None:
        self.store = ox.Store()

    def add(self, subject: Term, predicate: Term, obj: Term, graph: Term | None = None) -> None:
        """Add one quad. ``graph=None`` is the default graph."""
        self.store.add(ox.Quad(subject, predicate, obj, graph if graph is not None else ox.DefaultGraph()))

    def add_all(self, quads: Iterable[tuple]) -> None:
        for quad in quads:
            self.add(*quad)

    def remove_graph(self, graph: Term | None) -> None:
        """Remove every quad of one graph (``None`` for the default graph)."""
        for quad in list(self.store.quads_for_pattern(None, None, None, graph if graph is not None else ox.DefaultGraph())):
            self.store.remove(quad)

    def update(self, text: str, parameters: Mapping[str, Term] | None = None, strict: bool = True) -> None:
        self.store.update(bind_parameters(text, parameters or {}, strict))

    def select(self, text: str, parameters: Mapping[str, Term] | None = None) -> list[dict[str, Term]]:
        """The solutions of a SELECT, each as a dict of the variables it binds. An unbound variable is absent."""
        solutions = self.store.query(bind_parameters(text, parameters or {}))
        return [{str(v.value): solution[v] for v in solutions.variables if solution[v] is not None} for solution in solutions]

    def quads(self, graph: Term | None = None) -> list[ox.Quad]:
        """Every quad, or those in one graph (pass ``ox.DefaultGraph()`` for the default graph)."""
        return list(self.store.quads_for_pattern(None, None, None, graph))

    def count(self, predicate: str, graph: Term | None = None) -> int:
        return sum(1 for q in self.quads(graph) if q.predicate.value == predicate)


__all__ = ["OxigraphStore", "bind_parameters", "iri", "literal", "Term", "XSD"]
