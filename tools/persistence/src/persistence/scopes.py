# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""Scope matching (sketch §3.2): does a given ``dal:ProfileScope`` apply to
a given target class.

Five scope kinds, three of which need no reasoning at all (GraphPattern,
Namespace, Class), one resolved once offline (Shape), and one that is
intrinsically reasoning-dependent (EquivalentClass). This module only
answers "does it match"; :mod:`persistence.resolver` decides which matching
candidate wins.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from rdflib import RDFS, Graph, URIRef

from .namespaces import DAL, SH


@dataclass(frozen=True)
class Target:
    """A compilation target: a class, plus, when that class has more than
    one disjoint ``dal:GraphPatternScope`` deployment (sketch §3.4.3:
    lending and credit each deploy ``beh:Behaviour`` into their own graph
    family), which deployment this target represents. ``deployment`` is
    ``None`` for the unscoped/fallback target and for classes with no
    graph-pattern deployment at all.

    A class alone cannot distinguish "beh:Behaviour as lending deploys it"
    from "beh:Behaviour as credit deploys it": that distinction lives in
    which graph the instances are written to, which is exactly what a
    GraphPatternScope declares. A single class-only target cannot host two
    GraphPatternScope candidates at once without them appearing as a false
    ambiguity, so a class with N deployments compiles to N (or N+1, with
    the fallback) separate compiled profiles, not one."""

    cls: URIRef
    deployment: Optional[URIRef] = None

    def __str__(self) -> str:  # pragma: no cover - trivial
        if self.deployment is None:
            return str(self.cls)
        return f"{self.cls}@{self.deployment}"


SCOPE_KINDS = (
    "GraphPatternScope",
    "NamespaceScope",
    "ClassScope",
    "ShapeScope",
    "EquivalentClassScope",
)


@dataclass(frozen=True)
class ScopeInfo:
    iri: URIRef
    kind: str
    priority: int
    requires_reasoning: bool


def scope_kind(graph: Graph, scope: URIRef) -> Optional[str]:
    from rdflib import RDF

    for kind in SCOPE_KINDS:
        if (scope, RDF.type, DAL[kind]) in graph:
            return kind
    return None


def load_scope(graph: Graph, scope: URIRef) -> Optional[ScopeInfo]:
    kind = scope_kind(graph, scope)
    if kind is None:
        return None
    priority_lit = graph.value(scope, DAL.priority)
    priority = int(priority_lit) if priority_lit is not None else 0
    requires_reasoning = kind == "EquivalentClassScope"
    if kind == "ClassScope":
        include_sub = graph.value(scope, DAL.includeSubclasses)
        # Only entailed (not asserted rdfs:subClassOf*) subclass membership
        # needs reasoning. This compiler always walks the asserted
        # rdfs:subClassOf* closure (a plain property path, sketch §3.2), so
        # includeSubclasses never itself sets requires_reasoning here.
        del include_sub
    return ScopeInfo(iri=scope, kind=kind, priority=priority, requires_reasoning=requires_reasoning)


def all_scopes(graph: Graph) -> list[ScopeInfo]:
    from rdflib import RDF

    out: list[ScopeInfo] = []
    for kind in SCOPE_KINDS:
        for scope in graph.subjects(RDF.type, DAL[kind]):
            info = load_scope(graph, scope)
            if info:
                out.append(info)
    return out


def matches(graph: Graph, scope: ScopeInfo, target: Target) -> bool:
    """Does ``scope`` apply to ``target``.

    Non-graph-pattern scopes match on ``target.cls`` alone: a ClassScope,
    NamespaceScope, ShapeScope, or EquivalentClassScope is not deployment-
    specific, and applies uniformly across every deployment of a class. A
    GraphPatternScope, by contrast, *is* how a deployment is distinguished,
    so it matches only the one target whose ``deployment`` names that exact
    scope (never a different scope, never the unscoped/fallback target)."""
    if scope.kind == "GraphPatternScope":
        return target.deployment == scope.iri

    cls = target.cls

    if scope.kind == "ClassScope":
        declared = graph.value(scope.iri, DAL.targetClass)
        if declared == cls:
            return True
        include_sub = graph.value(scope.iri, DAL.includeSubclasses)
        if include_sub is not None and bool(include_sub):
            # asserted rdfs:subClassOf* closure only, never entailment
            subclasses = graph.transitive_subjects(RDFS.subClassOf, declared)
            return cls in set(subclasses)
        return False

    if scope.kind == "NamespaceScope":
        prefix = graph.value(scope.iri, DAL.iriPrefix)
        return prefix is not None and str(cls).startswith(str(prefix))

    if scope.kind == "ShapeScope":
        shape = graph.value(scope.iri, DAL.targetShape)
        if shape is None:
            return False
        shape_target = graph.value(shape, SH.targetClass)
        return shape_target == cls

    if scope.kind == "EquivalentClassScope":
        # No reasoner is required or assumed to exist (sketch non-goals).
        # A design-time approximation: the scope matches a target class
        # when that class is syntactically named inside the equivalence
        # expression's owl:intersectionOf list. Full OWL entailment beyond
        # this is out of scope for a compiler with no reasoner dependency.
        equiv = graph.value(scope.iri, DAL.equivalentTo)
        if equiv is None:
            return False
        from rdflib import OWL, RDF as _RDF

        members: set = set()
        head = graph.value(equiv, OWL.intersectionOf)
        node = head
        while node is not None and node != _RDF.nil:
            first = graph.value(node, _RDF.first)
            if first is not None:
                members.add(first)
            node = graph.value(node, _RDF.rest)
        if not members and equiv == cls:
            return True
        return cls in members

    return False


def discover_targets(graph: Graph, classes: Optional[set[URIRef]] = None) -> list[Target]:
    """Every ``Target`` the compiler should resolve a profile for.

    For each class (discovered via ``dal:targetClass`` if ``classes`` is not
    given explicitly), yields one ``Target`` per distinct ``GraphPatternScope``
    that declares ``dal:coversClass`` for it (one per deployment, sketch
    §3.4.3), plus one unscoped ``Target`` representing "this class where no
    graph-pattern deployment applies" -- which is the *only* target for a
    class with no graph-pattern deployment at all."""
    if classes is None:
        classes = set(graph.objects(None, DAL.targetClass))

    scopes = [s for s in all_scopes(graph) if s.kind == "GraphPatternScope"]
    out: list[Target] = []
    for cls in classes:
        deployments = [s.iri for s in scopes if cls in set(graph.objects(s.iri, DAL.coversClass))]
        for deployment in deployments:
            out.append(Target(cls=cls, deployment=deployment))
        out.append(Target(cls=cls, deployment=None))
    return out


def graph_prefix_for_target(graph: Graph, target: Target) -> Optional[str]:
    """The static prefix of ``target``'s own resolved ``dal:graphIriTemplate``,
    if any AggregateBoundaryProfile scoped by a non-GraphPattern scope
    declares one for it. Used only for diagnostics that want to relate a
    target to a graph family; scope *matching* itself never depends on this."""
    from rdflib import RDF

    for profile in graph.subjects(RDF.type, DAL.AggregateBoundaryProfile):
        scope = graph.value(profile, DAL.appliesTo)
        if scope is None:
            continue
        info = load_scope(graph, scope)
        if info is None or info.kind == "GraphPatternScope":
            continue
        if matches(graph, info, target):
            template = graph.value(profile, DAL.graphIriTemplate)
            if template:
                return str(template).split("{", 1)[0]
    return None


__all__ = [
    "ScopeInfo",
    "Target",
    "SCOPE_KINDS",
    "scope_kind",
    "load_scope",
    "all_scopes",
    "matches",
    "discover_targets",
    "graph_prefix_for_target",
]
