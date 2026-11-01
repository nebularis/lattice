# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""The engines a probe runs on: rdflib, Oxigraph and Apache Jena ARQ (ADR-A125, MSC-1).

:func:`run_query` runs one query against an rdflib ``Graph`` on a named engine and returns rows readable the same way whichever
engine ran it, by attribute (``row.g``), by name, by position, and as a dict of the variables it binds (``row.asdict()``).
Oxigraph and Jena get the graph as N-Triples in a disposable in-memory store. To add an engine, add its name to
:data:`REGISTRY` and a branch to :func:`run_query`. :func:`available` says which engines can run here, so a suite skips the
others, and a conformance task that needs all three sets ``SPARQL_PROBES_REQUIRED=1`` to fail where one is missing.
"""

from __future__ import annotations

from typing import Any

from rdflib import BNode, Graph, Literal, URIRef
from rdflib.namespace import XSD

REGISTRY = ("rdflib", "oxigraph", "jena")


def available() -> dict[str, bool]:
    """Which engines can run on this machine."""
    found = {"rdflib": True}
    try:
        import lattice_testing_oxigraph  # noqa: F401

        found["oxigraph"] = True
    except ImportError:
        found["oxigraph"] = False
    try:
        import lattice_testing_jena

        found["jena"] = lattice_testing_jena.available()
    except ImportError:
        found["jena"] = False
    return found


def _from_ox(term: Any):
    import pyoxigraph as ox

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


class Row:
    """One solution, readable the way rdflib's own ``ResultRow`` is: by attribute (``row.question``), by name (``row["question"]``),
    by the position of the SELECT clause's variables (``row[0]``), or as a dict of the variables it binds, unbound ones left out."""

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
        return self._values[key] if isinstance(key, int) else self._bindings[key]

    def asdict(self) -> dict:
        return {name: value for name, value in self._bindings.items() if value is not None}


def run_query(graph: Graph, text: str, engine: str) -> list:
    """``text`` run against ``graph`` on ``engine`` as a list of rows with rdflib terms."""
    if engine not in REGISTRY:
        raise ValueError(f"{engine!r} is not one of the engines we have, {REGISTRY}")
    if engine == "rdflib":
        return list(graph.query(text))
    data = graph.serialize(format="nt")
    if engine == "oxigraph":
        import pyoxigraph as ox

        store = ox.Store()
        store.load(input=data.encode("utf-8"), format=ox.RdfFormat.N_TRIPLES)
        solutions = store.query(text)
        variables = [str(v.value) for v in solutions.variables]
        return [Row(variables, [None if value is None else _from_ox(value) for value in solution]) for solution in solutions]
    from lattice_testing_jena import JenaStore

    with JenaStore() as store:
        store.load(data)
        variables, solutions = store.solutions(text)
        return [Row(variables, [solution.get(v) for v in variables]) for solution in solutions]
