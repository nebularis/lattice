# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""The engines the persistence tests run generated SPARQL on (formal-methods track H, slice H2.4b, ADR-A125).

A test that executes an update takes a dataset from :func:`dataset` and uses the small part of rdflib's ``Dataset`` API
that these tests need. On rdflib it is the ``Dataset`` itself. On Oxigraph it is :class:`OxDataset`, which has the same
methods, answers in rdflib terms, and runs the update on :class:`lattice_testing_oxigraph.OxigraphStore`, putting each
`initBindings` parameter in the text as a caller with no initial-binding API would. The ``engine`` fixture in
``conftest.py`` chooses the engine, and a test opts in with :data:`each_engine`."""

from __future__ import annotations

import warnings

import pytest
from rdflib import BNode, Dataset, Literal, URIRef
from rdflib.namespace import XSD

CURRENT = "rdflib"
DEFAULT_GRAPH = URIRef("urn:x-rdflib:default")
ENGINES = ["rdflib", pytest.param("oxigraph", marks=pytest.mark.oxigraph)]
each_engine = pytest.mark.usefixtures("engine")
each_engine_and_guards = pytest.mark.usefixtures("engine", "guard_axis")


GUARDS = True
"""Whether a test that executes an update and does not say otherwise asks for the parameter guards. The ``guard_axis`` fixture
sets it, so a behaviour test that does not depend on the guard runs with the guards on and off (FMH-H2-5, gate 1)."""


def guards(requested: bool | None = None) -> bool:
    """Whether a test that executes an update asks for the parameter guards. A test that is about the guard says so. The
    others take the axis, which is on unless the ``guard_axis`` fixture turns it off. Guard D (ADR-A123, addendum of
    2026-10-13) passes on both engines, so there is no engine default any more."""
    return GUARDS if requested is None else requested


_INTEGER_TYPES = {str(XSD) + n for n in ("long", "int", "short", "byte", "nonNegativeInteger", "positiveInteger", "unsignedLong", "unsignedInt", "unsignedShort", "unsignedByte", "nonPositiveInteger", "negativeInteger")}


def canon(term):
    """``term`` as the current engine stores it. Oxigraph 0.5.11 stores an integer-derived literal such as
    ``"1"^^xsd:long`` as ``"1"^^xsd:integer`` (FMH-H2-4b, P5). rdflib keeps the term."""
    if CURRENT == "oxigraph" and isinstance(term, Literal) and term.datatype is not None and str(term.datatype) in _INTEGER_TYPES:
        return Literal(str(term), datatype=XSD.integer)
    return term


def dataset():
    """An empty dataset on the current engine."""
    if CURRENT == "rdflib":
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            return Dataset()
    return OxDataset()


# ---- Oxigraph behind rdflib's vocabulary ---------------------------------------------------------------------------


def _ox():
    import pyoxigraph

    return pyoxigraph


def to_ox(term):
    ox = _ox()
    if isinstance(term, URIRef):
        return ox.NamedNode(str(term))
    if isinstance(term, BNode):
        return ox.BlankNode(str(term))
    if isinstance(term, Literal):
        if term.language:
            return ox.Literal(str(term), language=term.language)
        if term.datatype and str(term.datatype) != str(XSD.string):
            return ox.Literal(str(term), datatype=ox.NamedNode(str(term.datatype)))
        return ox.Literal(str(term))
    raise TypeError(f"{term!r} is not an rdflib term")


def from_ox(term):
    ox = _ox()
    if isinstance(term, ox.NamedNode):
        return URIRef(term.value)
    if isinstance(term, ox.BlankNode):
        return BNode(term.value)
    if isinstance(term, ox.Literal):
        if term.language:
            return Literal(term.value, lang=term.language)
        if term.datatype.value == str(XSD.string):
            return Literal(term.value)
        return Literal(term.value, datatype=URIRef(term.datatype.value))
    if isinstance(term, ox.DefaultGraph):
        return DEFAULT_GRAPH
    raise TypeError(f"{term!r} is not a pyoxigraph term")


class OxGraph:
    """One graph of an :class:`OxDataset`, with the methods of an rdflib graph that the tests use."""

    def __init__(self, store, name) -> None:
        self._store = store
        self._name = name  # an rdflib URIRef, or None for the default graph

    @property
    def identifier(self):
        return DEFAULT_GRAPH if self._name is None else self._name

    def _graph(self):
        ox = _ox()
        return ox.DefaultGraph() if self._name is None else to_ox(self._name)

    def _match(self, pattern):
        s, p, o = (None if t is None else to_ox(t) for t in pattern)
        return self._store.store.quads_for_pattern(s, p, o, self._graph())

    def add(self, triple) -> None:
        s, p, o = triple
        self._store.add(to_ox(s), to_ox(p), to_ox(o), None if self._name is None else to_ox(self._name))

    def remove(self, pattern) -> None:
        for quad in list(self._match(pattern)):
            self._store.store.remove(quad)

    def __iter__(self):
        for quad in self._match((None, None, None)):
            yield from_ox(quad.subject), from_ox(quad.predicate), from_ox(quad.object)

    def __contains__(self, triple) -> bool:
        return next(iter(self._match(triple)), None) is not None

    def __len__(self) -> int:
        return sum(1 for _ in self._match((None, None, None)))

    def objects(self, subject=None, predicate=None):
        for quad in self._match((subject, predicate, None)):
            yield from_ox(quad.object)


class OxDataset:
    """The part of rdflib's ``Dataset`` that the persistence tests use, on Oxigraph."""

    def __init__(self) -> None:
        from lattice_testing_oxigraph import OxigraphStore

        self._store = OxigraphStore()

    def graph(self, name) -> OxGraph:
        return OxGraph(self._store, URIRef(str(name)))

    @property
    def default_context(self) -> OxGraph:
        return OxGraph(self._store, None)

    def graphs(self):
        ox = _ox()
        names = {quad.graph_name for quad in self._store.quads()}
        for name in sorted(names, key=str):
            yield OxGraph(self._store, None if isinstance(name, ox.DefaultGraph) else from_ox(name))

    def quads(self, pattern=(None, None, None, None)):
        s, p, o, g = pattern
        for quad in self._store.store.quads_for_pattern(
            None if s is None else to_ox(s), None if p is None else to_ox(p), None if o is None else to_ox(o),
            None if g is None else to_ox(g),
        ):
            name = quad.graph_name
            yield from_ox(quad.subject), from_ox(quad.predicate), from_ox(quad.object), OxGraph(self._store, None if isinstance(name, _ox().DefaultGraph) else from_ox(name))

    def update(self, text: str, initBindings=None) -> None:
        parameters = {str(k): to_ox(v) for k, v in (initBindings or {}).items()}
        self._store.update(text, parameters, strict=False)

    def query(self, text: str, initBindings=None):
        from lattice_testing_oxigraph import bind_parameters

        parameters = {str(k): to_ox(v) for k, v in (initBindings or {}).items()}
        solutions = self._store.store.query(bind_parameters(text, parameters, strict=False))
        variables = list(solutions.variables)
        return [tuple(None if (value := solution[v]) is None else from_ox(value) for v in variables) for solution in solutions]
