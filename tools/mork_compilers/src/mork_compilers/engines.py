# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""Which engine runs a compiled query's SPARQL (python-test-melting TM11).

Every backend test calls :func:`run_query` in place of ``graph.query(text)``. **rdflib stays the
default here**, unlike the skill's usual default (ADR-A125, Oxigraph), until the maintainer decides
otherwise (STD-274). Building this module's conformance task found one real disagreement between
the two engines on this suite's own generated queries (TSD-41). It is understood and the profile
query no longer depends on it, since an aggregate over an expression that errors on some row of its
group is an error on Oxigraph and a skipped row on rdflib. The whole suite now passes on both, and
`check:mork-compilers-conformance` runs Oxigraph, on demand and before a merge, to keep any further
divergence visible. ``MORK_SPARQL_ENGINE`` names one of ``REGISTRY``, read once at import, so each
task sets it, since these tests are ``unittest.TestCase`` methods with no per-test engine
parametrisation. :func:`run_query` takes an ``engine`` for a test of one engine's behaviour.

On rdflib, :func:`run_query` returns ``graph.query(text)`` unchanged: every existing call site's
``row.question``-style attribute access already works, since rdflib's own result rows support it.

On Oxigraph, the graph's triples are loaded once into a disposable in-memory store, queried through
``pyoxigraph`` directly, and each solution's pyoxigraph terms are converted back to the matching
rdflib terms (:func:`_from_ox`), so a caller's attribute access and its comparisons against rdflib
constants (for example a diagnostic IRI checked against a set of ``URIRef``) keep working unchanged.
"""

from __future__ import annotations

import os
from typing import Any

import pyoxigraph as ox
from rdflib import BNode, Graph, Literal, URIRef
from rdflib.namespace import XSD

REGISTRY = ("rdflib", "oxigraph")
DEFAULT = "rdflib"


def _selected() -> str:
    name = os.environ.get("MORK_SPARQL_ENGINE", DEFAULT).strip().lower()
    if name not in REGISTRY:
        raise ValueError(f"MORK_SPARQL_ENGINE names {name!r}, and the engines we have are {REGISTRY}")
    return name


ENGINE = _selected()


def _from_ox(term: Any):
    """A pyoxigraph term as the matching rdflib term, the same conversion
    ``tools/persistence/tests/engines.py``'s ``from_ox`` makes for that suite."""
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
    raise TypeError(f"{term!r} is not a pyoxigraph term")


class _Row:
    """One solution, readable the way rdflib's own ``ResultRow`` is: by attribute (``row.question``),
    by name (``row["question"]``), by the position of the SELECT clause's variables (``row[0]``), or
    as a dict of the variables it binds, unbound ones left out (``row.asdict()``)."""

    def __init__(self, names: list[str], values: list[Any]) -> None:
        self._names = names
        self._values = values
        self._bindings = dict(zip(names, values))

    def __getattr__(self, name: str):
        try:
            return self._bindings[name]
        except KeyError:
            raise AttributeError(name) from None

    def __getitem__(self, key):
        if isinstance(key, int):
            return self._values[key]
        return self._bindings[key]

    def asdict(self) -> dict:
        return {name: value for name, value in self._bindings.items() if value is not None}


def run_query(graph: Graph, text: str, engine: str | None = None) -> list:
    """``text`` run against ``graph`` on ``engine``, :data:`ENGINE` when none is named, as a list of
    rows with rdflib terms, readable the same way whichever engine ran it. A test of one engine's
    own behaviour names it, so it holds under either task (STD-153)."""
    engine = engine or ENGINE
    if engine not in REGISTRY:
        raise ValueError(f"{engine!r} is not one of the engines we have, {REGISTRY}")
    if engine == "rdflib":
        return list(graph.query(text))
    store = ox.Store()
    store.load(input=graph.serialize(format="nt").encode("utf-8"), format=ox.RdfFormat.N_TRIPLES)
    solutions = store.query(text)
    variables = [str(v.value) for v in solutions.variables]
    return [
        _Row(variables, [None if value is None else _from_ox(value) for value in solution])
        for solution in solutions
    ]
