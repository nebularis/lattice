# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""Static hygiene checks over a persistence configuration (formal-methods
track H, slice H1).

Each check reads a loaded ``dal:`` graph, needs no compiled profile and no
backend, and returns :class:`Finding` records. A finding is either a
``violation`` (the configuration is ill-defined and the command refuses it)
or a ``warning`` (well-defined, but resolved by a rule the author may not
intend). Findings are sorted, so a report is byte-identical across runs.

H1.1, :func:`check_prefix_antichain`, tests whether the declared scope
prefixes can claim one resource twice (review §6.2, finding #2).
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from typing import Iterable

from rdflib import RDF, Graph, URIRef

from .namespaces import DAL

VIOLATION = "violation"
WARNING = "warning"


@dataclass(frozen=True, order=True)
class Finding:
    """One result of a hygiene check.

    ``counterexample`` is a concrete IRI that the cited scopes both match,
    so a reader can confirm the overlap by hand."""

    check: str
    severity: str
    subjects: tuple[str, ...]
    message: str
    counterexample: str = ""

    def __str__(self) -> str:
        tail = f" (counterexample: {self.counterexample})" if self.counterexample else ""
        return f"{self.severity.upper()} [{self.check}] {self.message}{tail}"


def _prefix_scopes(graph: Graph, scope_class: URIRef, prefix_property: URIRef) -> list[tuple[URIRef, str]]:
    """Every (scope, prefix) pair declared for ``scope_class``, sorted.

    A scope that declares several prefixes yields one pair per prefix. A
    scope that declares none yields nothing: it matches no resource, so it
    cannot overlap another scope."""
    out: list[tuple[URIRef, str]] = []
    for scope in graph.subjects(RDF.type, scope_class):
        if not isinstance(scope, URIRef):
            continue
        for prefix in graph.objects(scope, prefix_property):
            out.append((scope, str(prefix)))
    return sorted(out, key=lambda pair: (str(pair[0]), pair[1]))


def _nested(a: str, b: str) -> bool:
    """True when one prefix is equal to, or a prefix of, the other: a
    resource IRI exists that starts with both. Two prefixes that merely
    share leading characters (``urn:g:lend/`` and ``urn:g:lending/``) are
    not nested, and no IRI starts with both."""
    return a.startswith(b) or b.startswith(a)


def _graph_pattern_overlaps(graph: Graph) -> Iterable[Finding]:
    """Two ``dal:GraphPatternScope`` nodes with nested ``dal:graphPrefix``
    values that cover a common class are a violation.

    Each graph-pattern scope compiles to its own target (scopes.py
    ``discover_targets``), so an instance of the shared class written to a
    graph under both prefixes belongs to two targets with, in general,
    different profiles. Nested prefixes over disjoint classes are fine,
    because a scope also matches on class and no instance is in both."""
    pairs = _prefix_scopes(graph, DAL.GraphPatternScope, DAL.graphPrefix)
    for (scope_a, prefix_a), (scope_b, prefix_b) in combinations(pairs, 2):
        if scope_a == scope_b or not _nested(prefix_a, prefix_b):
            continue
        shared = sorted(
            str(c)
            for c in set(graph.objects(scope_a, DAL.coversClass)) & set(graph.objects(scope_b, DAL.coversClass))
        )
        if not shared:
            continue
        longer = max(prefix_a, prefix_b, key=len)
        relation = "equals" if prefix_a == prefix_b else "is a prefix of"
        outer, inner = (prefix_a, prefix_b) if len(prefix_a) <= len(prefix_b) else (prefix_b, prefix_a)
        yield Finding(
            check="prefix-antichain",
            severity=VIOLATION,
            subjects=(str(scope_a), str(scope_b)),
            message=(
                f"graph prefix {outer!r} {relation} {inner!r}: <{scope_a}> and <{scope_b}> both claim "
                f"graphs under it for {', '.join(shared)}, so one instance belongs to two targets"
            ),
            counterexample=longer,
        )


def _namespace_overlaps(graph: Graph) -> Iterable[Finding]:
    """Two ``dal:NamespaceScope`` nodes with nested ``dal:iriPrefix`` values
    are a warning.

    Overlap is legal here, since the resolver ranks competing scopes by
    ``dal:priority`` (resolver.py), but it is never by longest prefix. An
    author who nests ``https://example.org/a#`` inside ``https://example.org/``
    and expects the inner scope to win must also give it the higher
    priority."""
    pairs = _prefix_scopes(graph, DAL.NamespaceScope, DAL.iriPrefix)
    for (scope_a, prefix_a), (scope_b, prefix_b) in combinations(pairs, 2):
        if scope_a == scope_b or not _nested(prefix_a, prefix_b):
            continue
        longer = max(prefix_a, prefix_b, key=len)
        yield Finding(
            check="prefix-antichain",
            severity=WARNING,
            subjects=(str(scope_a), str(scope_b)),
            message=(
                f"iri prefixes {prefix_a!r} and {prefix_b!r} are nested: <{scope_a}> and <{scope_b}> both match "
                "a resource under the longer one. The resolver ranks by dal:priority, not by longest prefix"
            ),
            counterexample=longer,
        )


def check_prefix_antichain(graph: Graph) -> list[Finding]:
    """H1.1: do the declared ``dal:graphPrefix`` and ``dal:iriPrefix`` values
    form an antichain, where it matters.

    The resolver implements no longest-prefix rule, so nested graph prefixes
    over a shared class are refused (a violation), and nested iri prefixes
    are reported (a warning)."""
    return sorted([*_graph_pattern_overlaps(graph), *_namespace_overlaps(graph)])


__all__ = ["Finding", "VIOLATION", "WARNING", "check_prefix_antichain"]
