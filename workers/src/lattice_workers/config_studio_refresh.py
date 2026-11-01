"""Rebuilds the studio's projections whole from its store (ADR-A149 decision 14).

Each projection is one graph, `urn:lattice:studio:projection:{key}`, derived and never authoritative (PRI-52). The registry, jobs,
holders and terms are surface promotions, compiled here with `tools/surface` over the union of the graphs they read. The summaries
are the constant query `workspace-summaries.rq`, kept beside the contracts. Both are in `contracts/config-studio`. The refresh job
hands the graphs to the writer, which replaces each whole.
"""

from __future__ import annotations

import functools
import re
import sys
from pathlib import Path
from typing import Callable, Optional, Protocol

from rdflib import BNode, Dataset, Graph, Literal, Namespace, URIRef
from rdflib.namespace import RDF, XSD

from .config_studio_jobs import CST, catalogue, find_root

PRJ = Namespace("https://www.nebularis.org/neuro-semantic/lattice/config-studio/projection#")
PROJECTION = "urn:lattice:studio:projection:"
KEYS = ("registry", "jobs", "holders", "terms", "summaries")

_UUID = r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
_JOB_GRAPH = re.compile(rf"urn:lattice:studio:job:{_UUID}")

# For each promoted projection, which graphs it reads and the contracts of `projections.ttl` it compiles over them.
_PROMOTED: dict[str, tuple[Callable[[str], bool], tuple[str, ...]]] = {
    "registry": (lambda name: name.startswith("urn:lattice:studio:lineage/"), ("registry",)),
    "jobs": (lambda name: _JOB_GRAPH.fullmatch(name) is not None, ("jobs",)),
    "holders": (lambda name: name.startswith("urn:lattice:studio:description/"), ("holders-follows", "holders-imports")),
    "terms": (lambda name: name.startswith("urn:lattice:studio:version/"), ("terms-label", "terms-version")),
}


class Store(Protocol):
    def graph_names(self) -> list[str]:
        """The name of every named graph that holds a triple."""

    def get_graph(self, graph_iri: str) -> Graph:
        """A named graph."""

    def construct(self, query: str) -> Graph:
        """The graph a constant CONSTRUCT query gives."""


class DatasetStore:
    """A `Store` over an in-memory dataset, for a refresh of a dump and for tests."""

    def __init__(self, dataset: Dataset) -> None:
        self._dataset = dataset

    def graph_names(self) -> list[str]:
        return sorted(str(g.identifier) for g in self._dataset.graphs() if len(g) and isinstance(g.identifier, URIRef))

    def get_graph(self, graph_iri: str) -> Graph:
        return Graph() + self._dataset.graph(URIRef(graph_iri))

    def construct(self, query: str) -> Graph:
        return Graph() + self._dataset.query(query).graph


@functools.lru_cache(maxsize=None)
def _contracts(root: str) -> tuple[Graph, str]:
    """The projections' surface contracts and the text of the summaries query. Cached, so never modified."""
    found = catalogue(root)
    folder = Path(found.root) / found.area("contracts") / "config-studio"
    return Graph().parse(folder / "projections.ttl", format="turtle"), (folder / "workspace-summaries.rq").read_text(encoding="utf-8")


def _promote(declaration: Graph, source: Graph, keys: tuple[str, ...], read_at: str) -> Graph:
    """The assertions the promotions `keys` materialise over `source`. The core and manifest modules say how the surface was
    built, so they stay out, and so does a value that is a blank node, since a projection holds IRIs and literals only."""
    from surface.compile import compile_contract
    from surface.model import read_contracts

    combined = Graph()
    combined += declaration
    combined += source
    out = Graph()
    for contract in read_contracts(declaration):
        if contract.key in keys:
            assertions = compile_contract(contract, combined, read_at).modules["assertions"]
            out += (t for t in assertions.triples((None, contract.promotes_to, None)) if not isinstance(t[0], BNode) and not isinstance(t[2], BNode))
    return out


def refresh(store: Store, root: Optional[Path | str], job: str, read_at: str) -> dict[str, Graph]:
    """Every projection by its graph name, rebuilt from `store`, each with one `prj:Refresh` node naming `job` and `read_at`."""
    declaration, summaries = _contracts(str(find_root(root)))
    names = store.graph_names()
    out: dict[str, Graph] = {}
    for key, (wanted, contracts) in _PROMOTED.items():
        source = Graph()
        for name in names:
            if wanted(name):
                graph = store.get_graph(name)
                # ponytail: reads every graph of a kind whole, so a refresh costs the store's size. Read a constant CONSTRUCT of the carriers' properties if it matters.
                if key != "jobs" or (URIRef(name), CST.kind, CST.Refresh) not in graph:
                    source += graph
        out[PROJECTION + key] = _promote(declaration, source, contracts, read_at)
    out[PROJECTION + "summaries"] = store.construct(summaries)
    for name, graph in out.items():
        node = URIRef(name)
        graph.add((node, RDF.type, PRJ.Refresh))
        graph.add((node, PRJ.job, URIRef(job)))
        graph.add((node, PRJ.readAt, Literal(read_at, datatype=XSD.dateTime)))
    return out


def main(argv: list[str]) -> None:
    """`python -m lattice_workers.config_studio_refresh <store.nq> <projections.nq>`: the projections of a dump of the store, as a
    refresh would write them."""
    if len(argv) != 2:
        raise SystemExit(main.__doc__)
    dataset = Dataset()
    dataset.parse(argv[0], format="nquads")
    projections = refresh(DatasetStore(dataset), None, "urn:lattice:studio:job:00000000-0000-0000-0000-000000000000", "2026-01-01T00:00:00Z")
    out = Dataset()
    for name, graph in projections.items():
        target = out.graph(URIRef(name))
        for triple in graph:
            target.add(triple)
    out.serialize(argv[1], format="nquads")


if __name__ == "__main__":
    main(sys.argv[1:])
