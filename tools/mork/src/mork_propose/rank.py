# SPDX-License-Identifier: MPL-2.0
"""Candidate target terms for a source term, so a proposing model chooses among a few terms and their neighbours, and
the cost of a proposal grows with the source, never with the target. Ranking is BM25 over each card's label, its local
name split into words, its definition and the words the translation table gives it, among the target terms of a kind
the source term can map to. It is deterministic, and ties fall to the CURIE."""

from __future__ import annotations

import math
import re
from collections import Counter

from .cards import Card

# Which target kinds a source kind can map to, the first being the likeliest.
_COMPATIBLE = {
    "class": ("class", "concept"),
    "concept": ("concept", "class", "individual"),
    "individual": ("individual", "concept", "class"),
    # An RDF source's object property often stands for what it points at, as odrl:duty for a duty, so it may map to a class.
    "object property": ("object property", "property", "datatype property", "class"),
    "datatype property": ("datatype property", "property", "object property"),
    "property": ("object property", "datatype property", "property"),
}
_STOP = frozenset("a an and as at be by for from in is it of on or that the this to which with its are any each one".split())


def words(text: str) -> list[str]:
    """Lower-case word stems: camelCase and snake_case split, a plural s dropped, stop words gone."""
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    out = []
    for w in re.findall(r"[A-Za-z][a-z0-9]*", text):
        w = w.lower()
        if w in _STOP or len(w) < 2:
            continue
        out.append(w[:-1] if len(w) > 3 and w.endswith("s") and not w.endswith("ss") else w)
    return out


def _local(card: Card) -> str:
    return card.curie.rsplit(":", 1)[-1]


def _document(card: Card, aliases: dict) -> list[str]:
    # The label, the name and a source's word for the term count twice, since they name it and a definition only
    # describes it.
    named = words(card.label) + words(_local(card)) + [w for alias in aliases.get(card.curie, ()) for w in words(alias)]
    return 2 * named + words(card.definition)


def candidates(source: Card, targets: list[Card], k: int = 8, k1: float = 1.2, b: float = 0.75,
               aliases: dict | None = None) -> list[tuple[Card, float]]:
    """The `k` target terms likeliest to be the source term's match, best first, each with its score. `aliases` gives the
    other words each target term is known by, by CURIE, such as the translation table's."""
    aliases = aliases or {}
    kinds = _COMPATIBLE.get(source.kind, (source.kind,))
    pool = [t for t in targets if t.kind in kinds]
    if not pool:
        return []
    docs = [Counter(_document(t, aliases)) for t in pool]
    lengths = [sum(d.values()) for d in docs]
    mean = sum(lengths) / len(lengths) or 1.0
    df = Counter(w for d in docs for w in d)
    query = set(words(source.label) + words(_local(source)) + words(source.definition))
    scored = []
    for target, doc, length in zip(pool, docs, lengths):
        score = 0.0
        for w in query:
            if w not in doc:
                continue
            idf = math.log(1 + (len(pool) - df[w] + 0.5) / (df[w] + 0.5))
            score += idf * doc[w] * (k1 + 1) / (doc[w] + k1 * (1 - b + b * length / mean))
        # A kind earlier in the source kind's list is likelier, which breaks near ties toward it.
        score *= 1.0 - 0.1 * kinds.index(target.kind)
        scored.append((target, round(score, 4)))
    scored.sort(key=lambda ts: (-ts[1], ts[0].curie))
    return [ts for ts in scored[:k] if ts[1] > 0]
