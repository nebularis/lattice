# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""What a payload may name as a subject (ADR-A132 decision 2, ADR-A123 decision 6 and its addendum on the subjects of an event append).

The payload check of an aggregate walks the owned edges of the family's boundary shape from the root, over the payload alone. The generated
``payload-check`` query asks the same question of a store a caller loads the payload into, and ``tools/persistence`` holds the two equal on
rdflib and Oxigraph. This walk needs no engine, so it does not depend on how a store reads a zero-length path.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Iterable, Optional

from .contract import PayloadContract
from .payload import Payload, Triple
from .terms import Iri

OWNED = "Owned"


def plain(term) -> str:
    """The IRI of a typed :class:`Iri` or of a plain string, without angle brackets."""
    text = str(term)
    return text[1:-1] if text.startswith("<") and text.endswith(">") else text


def _object_iri(triple: Triple) -> Optional[str]:
    return plain(triple.object) if isinstance(triple.object, Iri) else None


def reach(contract: PayloadContract, root, payload: Payload, *, owned_only: bool = True) -> set:
    """The ``(node, shape)`` states the walk from ``root`` reaches in ``payload``. A node reached through an edge with no ``dal:edgeTargetShape``
    is a member that owns nothing further, so its shape is ``None``. With ``owned_only`` false every edge is followed, which a reference-mode
    check uses to find the edges of each reached node."""
    forward: dict = defaultdict(list)
    backward: dict = defaultdict(list)
    for t in payload.triples:
        o = _object_iri(t)
        if o is not None:
            forward[(plain(t.subject), plain(t.predicate))].append(o)
            backward[(o, plain(t.predicate))].append(plain(t.subject))
    by_source: dict = defaultdict(list)
    for e in contract.edges:
        if not owned_only or e.ownership == OWNED:
            by_source[e.source_shape].append(e)
    start = (plain(root), contract.shape)
    seen, stack = {start}, [start]
    while stack:
        node, shape = stack.pop()
        for e in by_source.get(shape, ()):
            for target in (backward if e.inverse else forward).get((node, e.predicate), ()):
                state = (target, e.target_shape)
                if state not in seen:
                    seen.add(state)
                    stack.append(state)
    return seen


def outside_bound(contract: PayloadContract, root, payload: Payload) -> tuple:
    """The subjects of ``payload`` that are neither ``root`` nor reached from it by the owned edges, sorted. A contract with no boundary shape
    bounds nothing and returns none: the form of the payload is all a family with no shape can check (``UnboundedPayload``)."""
    if contract.shape is None:
        return ()
    inside = {node for node, _ in reach(contract, root, payload)}
    return tuple(sorted(s for s in payload.subjects() if plain(s) not in inside))


def outside_events(events: Iterable, payload: Payload) -> tuple:
    """The subjects of an append's event triples that are neither an event of the batch nor a node minted under one, ``{event}/part/...``."""
    names = [plain(e) for e in events]
    return tuple(sorted(
        s for s in payload.subjects()
        if not any(plain(s) == n or plain(s).startswith(n + "/part/") for n in names)
    ))


__all__ = ["plain", "reach", "outside_bound", "outside_events"]
