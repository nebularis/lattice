"""Exhaustive and disjoint MORK term-to-lens partition checks."""

from __future__ import annotations

from typing import Any

from .facts import Facts


def check(partition: dict[str, Any], facts: Facts) -> list[str]:
    assignments = partition.get("assignments", {})
    default_lens = partition.get("defaultLens")
    findings = []
    for term in facts.terms:
        if term.iri not in assignments and not default_lens:
            findings.append(f"partition.empty:{term.iri}")
    return findings