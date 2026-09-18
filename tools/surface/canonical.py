# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""
Canonicalisation and hashing.

Two hashes, answering different questions:

``semantic content hash``
    over the canonical, meaning-bearing inputs a run consumed — the contract
    declaration, the enumerated population, the closure edges, and, where the
    run materialises, the carrier assertions. With the profile identity it
    decides whether an existing surface may be reused rather than regenerated.

``artefact hash``
    over the emitted content, excluding the manifest. A change here while the
    semantic content hash and the profile identity both hold is a generator
    defect, not a source change — which is why the manifest's own production
    timestamp sits outside it.

**Canonicalisation version.** This module hashes ``rdflib.compare``'s canonical
graph, so blank nodes are labelled by their graph position rather than by the
label they happened to be serialised with. That is a change of canonicalisation
contract from the previous dependency-free implementation, which required the
generator to mint deterministic labels before a graph could be hashed at all.
Per ADR-A12 a change to the canonicalisation contract changes every structural
hash in the estate, so the version string moves with it and the estate needs a
planned rehash at cutover rather than a silent drift.
"""

from __future__ import annotations

import hashlib
from typing import Iterable, List

from rdflib import Graph
from rdflib.compare import to_canonical_graph

CANONICALISATION_VERSION = "srf-canon/2"


def canonical_lines(graph: Graph) -> List[str]:
    """The canonical N-Triples rendering of a graph, sorted."""
    canonical = to_canonical_graph(graph)
    serialised = canonical.serialize(format="nt")
    if isinstance(serialised, bytes):  # rdflib 5 returns bytes
        serialised = serialised.decode("utf-8")
    return sorted(line for line in serialised.splitlines() if line.strip())


def canonical_form(graph: Graph) -> str:
    return "\n".join(canonical_lines(graph))


def hash_graph(graph: Graph) -> str:
    """The content hash of a graph, independent of serialisation and blank-node labels."""
    return hashlib.sha256(canonical_form(graph).encode("utf-8")).hexdigest()


def hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def combine(parts: Iterable[str]) -> str:
    """Fold an unordered collection of hashes into one."""
    return hashlib.sha256("\n".join(sorted(parts)).encode("utf-8")).hexdigest()
