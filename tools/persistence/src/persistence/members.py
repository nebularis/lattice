# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""The caller's side of `dal:DeltaMembership` (formal-methods H2.6f), kept small and free of any store.

A family that states its members as changes keeps a version's members in a chain of `pat:addsMember` and `pat:dropsMember` back to the
nearest checkpoint. The generated `members` query resolves them. Two things remain for the caller, and both are here so that the tests, the
benchmark and an adopter's code agree.

* :func:`is_checkpoint` says whether the version about to be written lists every member. The write does not decide it, since SPARQL has no
  remainder and the caller already holds the sequence. H2.8's caller check verifies the choice against `dal:checkpointEvery`.
* :func:`materialise` puts the results of the `members` query into a scratch graph under the domain's membership property, which is the form
  a domain shape (`sh:path` the membership property) validates. A shape never runs over the stored delta, which does not hold that property
  for any version but a checkpoint (H2.6f-Q4).
"""

from __future__ import annotations

from typing import Iterable

from rdflib import Graph, URIRef


def is_checkpoint(next_seq: int, checkpoint_every: int) -> bool:
    """Whether the version written at ``next_seq`` (the version row's seq after the write) lists every member and carries
    `pat:checkpoint true`. The first version always does, since nothing precedes it to be a delta against, and so does every
    ``checkpoint_every``-th version after that, so no chain read is longer than ``checkpoint_every``."""
    if isinstance(checkpoint_every, bool) or not isinstance(checkpoint_every, int) or checkpoint_every < 1:
        raise ValueError(f"checkpoint_every must be an integer of at least 1, got {checkpoint_every!r}")
    return next_seq == 1 or next_seq % checkpoint_every == 0


def materialise(version: str | URIRef, membership_property: str | URIRef, members: Iterable) -> Graph:
    """A scratch graph holding `version membership_property member` for each member the `members` query returned. ``members`` is the
    query's rows, each a term or a one-column row. Validate it with the domain's own shapes, then discard it."""
    scratch = Graph()
    for row in members:
        member = row[0] if isinstance(row, (tuple, list)) else row
        scratch.add((URIRef(str(version)), URIRef(str(membership_property)), member))
    return scratch


__all__ = ["is_checkpoint", "materialise"]
