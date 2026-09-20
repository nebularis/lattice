# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""
Eligibility executable IR (ADR-A24; a scoped subset of the executable-
semantics design in ``ontology/surface/docs/MorkEnhancements.md``).

Compiles an ``elg:IntervalCondition`` into a backend-neutral list of
required intervals, so the SPARQL, SHACL, and SWRL backends in this package
share one reading of containment semantics rather than each re-deriving it
from ``qnt:RangeSet``/``qnt:Range``/``qnt:Bound`` independently — the
duplication ADR-A24 and the design note both name as the reason a shared IR
exists at all.

**Scope, stated once here rather than repeated per backend:**

- Only ``elg:IntervalContainment`` is implemented. ``elg:ExactCondition``,
  ``elg:SetMembershipCondition``, and ``elg:WildcardCondition`` are not.
- Candidate evidence is read directly from an ``elg:Question``'s own
  ``elg:candidateRangeSet`` — the shape ``ontology/eligibility/examples/interval-
  containment.ttl`` already uses. A domain-facing binding mechanism (a
  "loans:creditScore supplies the candidate evidence" style contract) is
  the "Executable Projection Contract" the design note proposes in its
  final section. That is a separate, not-yet-decided architectural layer
  and is deliberately not implemented here — see
  ``ontology/mork/docs/eligibility-executable-compiler.md`` for why.
- Profile aggregation is recorded (``elg:AllRequired``, ``elg:AnySufficient``)
  but no backend in this package generates a combined, profile-level
  artefact; only per-condition artefacts are generated. Aggregating several
  conditions' results into one three-valued profile outcome is left for a
  later pass, named explicitly rather than silently missing.
- Runtime result tracking (the design note's ``exe:EvaluationRun``,
  ``exe:ConditionResult``, §6-§13) is not implemented — this module compiles
  artefacts; it does not run them or record what running them produced.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Sequence

from rdflib import Graph, URIRef
from rdflib.namespace import RDF

from .namespaces import ELG, QNT


class IRCompileError(ValueError):
    """The condition or profile cannot be compiled by this IR (unsupported shape)."""


@dataclass(frozen=True)
class RequiredInterval:
    """One member of a required range set, in comparable form.

    ``lower``/``upper`` of ``None`` means unbounded on that side; closure
    flags are meaningless on an unbounded side and should be ignored there.
    """

    lower: Optional[float]
    lower_closed: bool
    upper: Optional[float]
    upper_closed: bool


@dataclass(frozen=True)
class IntervalPlan:
    """The executable IR for one ``elg:IntervalCondition``."""

    condition: URIRef
    value_space: URIRef
    required: Sequence[RequiredInterval]
    source_nodes: Sequence[URIRef]  # provenance: every declaration node read, condition first


@dataclass(frozen=True)
class ProfilePlan:
    """The executable IR for one ``elg:AdmissionProfile`` over interval conditions."""

    profile: URIRef
    aggregation: URIRef  # elg:AllRequired or elg:AnySufficient
    conditions: Sequence[IntervalPlan]


def _numeric(graph: Graph, quantity: URIRef) -> float:
    value = graph.value(quantity, QNT.numericValue)
    if value is None:
        raise IRCompileError(f"{quantity} has no qnt:numericValue")
    return float(str(value))


def _bound_value(graph: Graph, bound: URIRef, source_nodes: List[URIRef]) -> tuple:
    """The (numeric value, is_closed) pair for one ``qnt:Bound``."""
    source_nodes.append(bound)
    value_node = graph.value(bound, QNT.boundValue)
    if value_node is None:
        raise IRCompileError(f"{bound} has no qnt:boundValue")
    source_nodes.append(value_node)
    closure = graph.value(bound, QNT.boundClosure)
    return _numeric(graph, value_node), closure == QNT.Closed


def compile_condition(graph: Graph, condition: URIRef) -> IntervalPlan:
    """Compile one ``elg:IntervalCondition`` into an ``IntervalPlan``."""
    if (condition, RDF.type, ELG.IntervalCondition) not in graph:
        raise IRCompileError(f"{condition} is not an elg:IntervalCondition")
    strategy = graph.value(condition, ELG.matchStrategy)
    if strategy != ELG.IntervalContainment:
        raise IRCompileError(
            f"{condition} declares match strategy {strategy}, not "
            f"elg:IntervalContainment; this IR compiles IntervalContainment only"
        )
    wildcard = graph.value(condition, ELG.wildcardSemantics)
    if wildcard is not None and wildcard != ELG.NoWildcard:
        raise IRCompileError(
            f"{condition} declares wildcard semantics {wildcard}; this IR has no "
            f"account of a non-NoWildcard interval condition and refuses rather than "
            f"guess at one"
        )
    range_set = graph.value(condition, ELG.requiredRangeSet)
    if range_set is None:
        raise IRCompileError(f"{condition} has no elg:requiredRangeSet")
    value_space = graph.value(range_set, QNT.onSpace)
    if value_space is None:
        raise IRCompileError(f"{range_set} has no qnt:onSpace")

    source_nodes: List[URIRef] = [condition, range_set, value_space]
    required: List[RequiredInterval] = []
    ranges = sorted(graph.objects(range_set, QNT.hasRange), key=str)
    if not ranges:
        raise IRCompileError(f"{range_set} declares no qnt:hasRange members")

    for range_node in ranges:
        source_nodes.append(range_node)
        range_space = graph.value(range_node, QNT.onSpace)
        if range_space is not None and range_space != value_space:
            raise IRCompileError(
                f"{range_node} declares value space {range_space}, which differs from "
                f"{range_set}'s {value_space} (exe:ValueSpaceMismatch)"
            )
        lower_bound = graph.value(range_node, QNT.lowerBound)
        upper_bound = graph.value(range_node, QNT.upperBound)
        if lower_bound is None and upper_bound is None:
            raise IRCompileError(f"{range_node} has neither a lower nor an upper bound")

        lower_value: Optional[float] = None
        lower_closed = False
        if lower_bound is not None:
            lower_value, lower_closed = _bound_value(graph, lower_bound, source_nodes)

        upper_value: Optional[float] = None
        upper_closed = False
        if upper_bound is not None:
            upper_value, upper_closed = _bound_value(graph, upper_bound, source_nodes)

        required.append(RequiredInterval(lower_value, lower_closed, upper_value, upper_closed))

    deduplicated = tuple(dict.fromkeys(source_nodes))
    return IntervalPlan(
        condition=condition, value_space=value_space, required=tuple(required),
        source_nodes=deduplicated,
    )


def compile_profile(graph: Graph, profile: URIRef) -> ProfilePlan:
    """Compile one ``elg:AdmissionProfile`` over interval conditions into a ``ProfilePlan``."""
    if (profile, RDF.type, ELG.AdmissionProfile) not in graph:
        raise IRCompileError(f"{profile} is not an elg:AdmissionProfile")
    aggregation = graph.value(profile, ELG.compatibilityOperation)
    if aggregation not in (ELG.AllRequired, ELG.AnySufficient):
        raise IRCompileError(
            f"{profile} declares compatibility operation {aggregation}; this IR "
            f"supports elg:AllRequired and elg:AnySufficient only"
        )
    conditions = sorted(graph.objects(profile, ELG.hasCondition), key=str)
    if not conditions:
        raise IRCompileError(f"{profile} declares no elg:hasCondition")
    plans = [compile_condition(graph, condition) for condition in conditions]
    return ProfilePlan(profile=profile, aggregation=aggregation, conditions=tuple(plans))
