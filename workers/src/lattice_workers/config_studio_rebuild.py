"""Rebuilds the studio's promoted partitions from its store (projection maintenance, PM2, PM-Q3).

Each promotion of `contracts/config-studio/promotions.ttl` reads one family of aggregates, its `cst:sourceFamily`, and its rows for one
source live in that source's own partition, `urn:lattice:studio:promoted:{source graph}`. A write keeps its sources' partitions in its
own request, so a rebuild runs only at start when the contracts grew since the last one, or when an administrator asks. It returns
every source's partition, an empty one for a partition whose source is gone, and the record of the contracts it built from, which the
writer replaces whole. Derived and never authoritative (PRI-52). The summaries are not stored: the service evaluates
`workspace-summaries.rq` as it reads them.
"""

from __future__ import annotations

import functools
import re
import sys
from pathlib import Path
from typing import Optional, Protocol

from rdflib import BNode, Dataset, Graph, Literal, Namespace, URIRef

from .config_studio_jobs import CST, catalogue, find_root

PROMOTED = "urn:lattice:studio:promoted:"
RECORD = "urn:lattice:studio:promoted-record"
SRF = Namespace("https://www.nebularis.org/neuro-semantic/lattice/surface#")

_UUID = r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
_FAMILIES = {
    "description": lambda name: name.startswith("urn:lattice:studio:description/"),
    "lineage": lambda name: name.startswith("urn:lattice:studio:lineage/"),
    "version": lambda name: name.startswith("urn:lattice:studio:version/"),
    "job": lambda name: re.fullmatch(rf"urn:lattice:studio:job:{_UUID}", name) is not None,
}
"""The families a promotion may read, by their graphs' names, as `Graphs.familyOf` names them in the service."""


class Store(Protocol):
    def graph_names(self) -> list[str]:
        """The name of every named graph that holds a triple."""

    def get_graph(self, graph_iri: str) -> Graph:
        """A named graph."""


class DatasetStore:
    """A `Store` over an in-memory dataset, for a rebuild of a dump and for tests."""

    def __init__(self, dataset: Dataset) -> None:
        self._dataset = dataset

    def graph_names(self) -> list[str]:
        return sorted(str(g.identifier) for g in self._dataset.graphs() if len(g) and isinstance(g.identifier, URIRef))

    def get_graph(self, graph_iri: str) -> Graph:
        return Graph() + self._dataset.graph(URIRef(graph_iri))


@functools.lru_cache(maxsize=None)
def _declarations(root: str) -> Graph:
    """The studio's promotion contracts. Cached, so never modified."""
    found = catalogue(root)
    return Graph().parse(Path(found.root) / found.area("contracts") / "config-studio" / "promotions.ttl", format="turtle")


def digests(declarations: Graph) -> dict[str, str]:
    """Each promotion contract with the state digest of its own triples, as the service's `Promotions.digests` computes it."""
    from lattice_persistence import Payload, state_digest

    return {str(c): state_digest(Payload.from_rdflib(declarations.triples((c, None, None))))
            for c in declarations.subjects(predicate=None, object=SRF.PromotionContract) if isinstance(c, URIRef)}


def _rows(declarations: Graph, source: Graph, family: str, read_at: str) -> Graph:
    """The rows of `source` for every promotion of `family`. A value that is a blank node stays out, since a partition holds IRIs and
    literals only."""
    from surface.compile import compile_contract
    from surface.model import read_contracts

    combined = declarations + source
    out = Graph()
    for contract in read_contracts(declarations):
        if str(declarations.value(contract.iri, CST.sourceFamily)) != family:
            continue
        assertions = compile_contract(contract, combined, read_at).modules["assertions"]
        out += (t for t in assertions.triples((None, contract.promotes_to, None)) if not isinstance(t[0], BNode) and not isinstance(t[2], BNode))
    return out


def rebuild(store: Store, root: Optional[Path | str], job: str, read_at: str) -> dict[str, Graph]:
    """Every promoted partition by its graph name, rebuilt from `store`, an empty one for each whose source is gone, and the record."""
    declarations = _declarations(str(find_root(root)))
    names = store.graph_names()
    out: dict[str, Graph] = {}
    for name in names:
        family = next((f for f, wanted in _FAMILIES.items() if wanted(name)), None)
        if family is not None:
            out[PROMOTED + name] = _rows(declarations, store.get_graph(name), family, read_at)
    for name in names:
        if name.startswith(PROMOTED) and name not in out:
            out[name] = Graph()
    record = Graph()
    for contract, digest in digests(declarations).items():
        record.add((URIRef(contract), CST.contractDigest, Literal(digest)))
    out[RECORD] = record
    return out


def main(argv: list[str]) -> None:
    """`python -m lattice_workers.config_studio_rebuild <store.nq> <promoted.nq>`: the promoted partitions and the record of a dump
    of the store, as a rebuild would write them."""
    if len(argv) != 2:
        raise SystemExit(main.__doc__)
    dataset = Dataset()
    dataset.parse(argv[0], format="nquads")
    rebuilt = rebuild(DatasetStore(dataset), None, "urn:lattice:studio:job:00000000-0000-0000-0000-000000000000", "2026-01-01T00:00:00Z")
    out = Dataset()
    for name, graph in rebuilt.items():
        target = out.graph(URIRef(name))
        for triple in graph:
            target.add(triple)
    out.serialize(argv[1], format="nquads")


if __name__ == "__main__":
    main(sys.argv[1:])
