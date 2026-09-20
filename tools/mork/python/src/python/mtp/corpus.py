"""Corpus statistics for MORK teaching-pack prioritisation."""

from __future__ import annotations

from collections import Counter
from pathlib import Path

from rdflib import Graph


def predicate_counts(root: Path) -> Counter[str]:
    counts: Counter[str] = Counter()
    for path in root.rglob("*.ttl"):
        graph = Graph().parse(path, format="turtle")
        counts.update(str(predicate) for _, predicate, _ in graph)
    return counts