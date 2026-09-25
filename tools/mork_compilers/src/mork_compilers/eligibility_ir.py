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

Compiles a concept-matching condition (``elg:ExactMatch``,
``elg:SetMembership``, ``elg:HierarchicalMatch``) into a ``ConceptPlan``
holding its required and excluded concepts, read under the ADR-A87 decision
table (ADR-A89). Where the table needs the bound scheme (hierarchical match,
or a condition with exclusions only), the plan also records the scheme the
contract resolved to and the ADR-A87 decision for each of its members, the
"Expanded" form of ADR-A89 item 3.

**Scope, stated once here rather than repeated per backend:**

- ``elg:IntervalContainment``, ``elg:ExactMatch``, ``elg:SetMembership`` and
  ``elg:HierarchicalMatch`` are implemented. ``elg:Wildcard`` is not.
- Candidate evidence is read from an ``elg:Question``'s own
  ``elg:candidateRangeSet`` or ``elg:candidateConcept`` — the shape
  ``ontology/eligibility/examples/interval-containment.ttl`` already uses —
  or, where an ``elg:EvidenceBinding`` binds the condition, from each
  instance of the binding's subject class along its path (ADR-A91). The plan
  then carries an ``EvidencePath`` and every backend reads through it. A domain-facing binding mechanism (a
  "loans:creditScore supplies the candidate evidence" style contract) is
  the "Executable Projection Contract" the design note proposes in its
  final section. That is a separate, not-yet-decided architectural layer
  and is deliberately not implemented here — see
  ``ontology/mork/docs/eligibility-executable-compiler.md`` for why.
- Profile aggregation (``elg:AllRequired``, ``elg:AnySufficient``) uses
  strong Kleene logic over the three outcomes (ADR-A89 item 5).
  ``elg:DimensionConsistent`` has no evaluable definition and is refused
  (``exe:RefusedOperation``).
- Runtime result tracking (the design note's ``exe:EvaluationRun``,
  ``exe:ConditionResult``, §6-§13) is not implemented — this module compiles
  artefacts; it does not run them or record what running them produced.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, FrozenSet, List, Optional, Sequence, Set, Tuple, Union

from rdflib import Graph, URIRef
from rdflib.namespace import RDF, SKOS
from vocabulary import BindingConflictError, NoApplicableBindingError, resolve

from .namespaces import ELG, QNT, VOC

PERMITTED = "Permitted"
DENIED = "Denied"
UNDETERMINED = "Undetermined"


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
class EvidencePath:
    """Where a bound condition reads its candidate (ADR-A91): each instance of
    ``subject_class``, along ``steps`` of (property, inverse) in order."""

    binding: URIRef
    subject_class: URIRef
    steps: Tuple[Tuple[URIRef, bool], ...]
    space: Optional[URIRef] = None  # elg:readOnSpace, for a literal at the path's end


@dataclass(frozen=True)
class IntervalPlan:
    """The executable IR for one ``elg:IntervalCondition``."""

    condition: URIRef
    value_space: URIRef
    required: Sequence[RequiredInterval]
    source_nodes: Sequence[URIRef]  # provenance: every declaration node read, condition first
    evidence: Optional[EvidencePath] = None


@dataclass(frozen=True)
class ResolutionContext:
    """The caller's resolution instant and active binding scopes (ADR-A85).

    Required to compile a condition whose scheme contract has any
    ``voc:SchemeBinding``. ADR-A89 item 2 makes both explicit compile inputs
    rather than defaulting to the time of compilation.
    """

    at: datetime
    scope: FrozenSet[URIRef] = frozenset()


@dataclass(frozen=True)
class SchemeResolution:
    """The scheme a condition's contract resolved to, and how."""

    contract: URIRef
    scheme: URIRef
    binding: Optional[URIRef]  # None when voc:boundScheme applied
    at: Optional[datetime]  # None when the contract has no binding
    scope: Tuple[URIRef, ...]


@dataclass(frozen=True)
class ConceptPlan:
    """The executable IR for one concept-matching condition (ADR-A87, ADR-A89).

    ``required`` concepts are alternatives. Each ``excluded`` concept excludes
    independently and takes precedence over any required concept (L10).
    ``scheme`` and ``expansion`` are set when the decision table needs the
    bound scheme. ``expansion`` pairs every member of the resolved scheme
    with its decision, sorted by concept.
    """

    condition: URIRef
    strategy: URIRef
    required: Sequence[URIRef]
    excluded: Sequence[URIRef]
    source_nodes: Sequence[URIRef]  # provenance: condition, concepts, contract, scheme, binding
    scheme: Optional[SchemeResolution] = None
    expansion: Tuple[Tuple[URIRef, str], ...] = ()
    evidence: Optional[EvidencePath] = None

    @property
    def hierarchical(self) -> bool:
        return self.strategy == ELG.HierarchicalMatch


CONCEPT_STRATEGIES = (ELG.ExactMatch, ELG.SetMembership, ELG.HierarchicalMatch)


@dataclass(frozen=True)
class ProfilePlan:
    """The executable IR for one ``elg:AdmissionProfile``.

    ``elg:AllRequired``: any Denied gives Denied, else any Undetermined or
    unanswered condition gives Undetermined, else Permitted.
    ``elg:AnySufficient``: any Permitted gives Permitted, else any Undetermined
    or unanswered condition gives Undetermined, else Denied.
    """

    profile: URIRef
    aggregation: URIRef  # elg:AllRequired or elg:AnySufficient
    conditions: Sequence[Union[IntervalPlan, ConceptPlan]]

    @property
    def subject_class(self) -> Optional[URIRef]:
        """The bound subject class shared by every condition, or None when the
        profile evaluates questions."""
        return self.conditions[0].evidence.subject_class if self.conditions[0].evidence else None


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


def read_evidence(graph: Graph, condition: URIRef) -> Optional[EvidencePath]:
    """The condition's ``elg:EvidenceBinding``, if it has one."""
    bindings = sorted(graph.subjects(ELG.bindsCondition, condition), key=str)
    if not bindings:
        return None
    if len(bindings) > 1:
        raise IRCompileError(f"{condition} is bound by several elg:EvidenceBinding individuals: {bindings}")
    binding = bindings[0]
    subject_class = graph.value(binding, ELG.subjectClass)
    if subject_class is None:
        raise IRCompileError(f"{binding} declares no elg:subjectClass")
    steps = []
    for step in graph.objects(binding, ELG.evidenceStep):
        index, prop = graph.value(step, ELG.stepIndex), graph.value(step, ELG.stepProperty)
        direction = graph.value(step, ELG.stepDirection)
        if index is None or prop is None or direction not in (ELG.Forward, ELG.Inverse):
            raise IRCompileError(f"{binding} has a step without an index, property or direction")
        steps.append((int(index), prop, direction == ELG.Inverse))
    steps.sort()
    if not steps or [index for index, _, _ in steps] != list(range(len(steps))):
        raise IRCompileError(f"{binding}'s step indexes are not 0 to n-1 without gaps")
    return EvidencePath(
        binding=binding,
        subject_class=subject_class,
        steps=tuple((prop, inverse) for _, prop, inverse in steps),
        space=graph.value(binding, ELG.readOnSpace),
    )


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

    evidence = read_evidence(graph, condition)
    if evidence is not None and evidence.space is not None and evidence.space != value_space:
        raise IRCompileError(
            f"{evidence.binding} reads on {evidence.space}, but {condition} constrains {value_space} "
            f"(exe:ValueSpaceMismatch)"
        )
    deduplicated = tuple(dict.fromkeys(source_nodes))
    return IntervalPlan(
        condition=condition, value_space=value_space, required=tuple(required),
        source_nodes=deduplicated, evidence=evidence,
    )


def _refuse_wildcards(graph: Graph, condition: URIRef) -> None:
    wildcard = graph.value(condition, ELG.wildcardSemantics)
    if wildcard is not None and wildcard != ELG.NoWildcard:
        raise IRCompileError(
            f"{condition} declares wildcard semantics {wildcard}; this IR has no "
            f"account of a non-NoWildcard condition and refuses rather than guess at one"
        )


def _resolve_scheme(
    graph: Graph, condition: URIRef, context: Optional[ResolutionContext]
) -> SchemeResolution:
    contract = graph.value(condition, ELG.constrainedByContract)
    if contract is None:
        raise IRCompileError(
            f"{condition} needs its bound scheme but declares no elg:constrainedByContract"
        )
    if any(graph.subjects(VOC.forContract, contract)):
        if context is None:
            raise IRCompileError(
                f"{contract} has voc:SchemeBinding individuals; compile {condition} with an "
                f"explicit resolution instant and scope (ADR-A89 item 2)"
            )
        try:
            resolution = resolve(graph, contract, context.scope, context.at)
        except (BindingConflictError, NoApplicableBindingError) as error:
            raise IRCompileError(str(error)) from error
        return SchemeResolution(
            contract=contract,
            scheme=resolution.scheme,
            binding=resolution.winning_binding,
            at=context.at,
            scope=tuple(sorted(context.scope, key=str)),
        )
    scheme = graph.value(contract, VOC.boundScheme)
    if scheme is None:
        raise IRCompileError(f"{contract} has neither a voc:SchemeBinding nor a voc:boundScheme")
    return SchemeResolution(contract=contract, scheme=scheme, binding=None, at=None, scope=())


def _ordering(graph: Graph, scheme: URIRef) -> Dict[URIRef, Set[URIRef]]:
    """Each member of ``scheme`` mapped to its broader concepts within the scheme."""
    members = set(graph.subjects(SKOS.inScheme, scheme))
    return {
        member: {broader for broader in graph.objects(member, SKOS.broader) if broader in members}
        for member in members
    }


def _ancestors(ordering: Dict[URIRef, Set[URIRef]], concept: URIRef) -> Set[URIRef]:
    """``concept`` and everything above it, reflexive-transitive (L9)."""
    found: Set[URIRef] = set()
    pending = [concept]
    while pending:
        current = pending.pop()
        if current not in found:
            found.add(current)
            pending.extend(ordering.get(current, ()))
    return found


def _refuse_cycles(ordering: Dict[URIRef, Set[URIRef]], scheme: URIRef) -> None:
    for member in ordering:
        if any(member in _ancestors(ordering, broader) for broader in ordering[member]):
            raise IRCompileError(
                f"{scheme} has a cycle through {member}; hierarchical match has no truth "
                f"condition under it (L9)"
            )


def _expand(
    ordering: Dict[URIRef, Set[URIRef]],
    hierarchical: bool,
    required: Sequence[URIRef],
    excluded: Sequence[URIRef],
) -> Tuple[Tuple[URIRef, str], ...]:
    """The ADR-A87 decision for every member of the resolved scheme."""
    ancestors = {member: _ancestors(ordering, member) for member in ordering}

    def matches(candidate: URIRef, concept: URIRef) -> bool:
        return concept in ancestors[candidate] if hierarchical else concept == candidate

    decided = []
    for candidate in sorted(ordering, key=str):
        if any(matches(candidate, concept) for concept in excluded):
            decision = DENIED  # L10
        elif required and not any(matches(candidate, concept) for concept in required):
            decision = DENIED
        elif hierarchical and any(
            concept in ancestors and candidate in ancestors[concept] and concept != candidate
            for concept in excluded
        ):
            decision = UNDETERMINED  # L11
        else:
            decision = PERMITTED  # L12 when nothing is required
        decided.append((candidate, decision))
    return tuple(decided)


def compile_concept_condition(
    graph: Graph, condition: URIRef, context: Optional[ResolutionContext] = None
) -> ConceptPlan:
    """Compile one condition matching by ``elg:ExactMatch``, ``elg:SetMembership``
    or ``elg:HierarchicalMatch``. ``context`` is required when the condition's
    contract has scheme bindings."""
    strategy = graph.value(condition, ELG.matchStrategy)
    if strategy not in CONCEPT_STRATEGIES:
        raise IRCompileError(
            f"{condition} declares match strategy {strategy}; this IR compiles concept "
            f"conditions matching by elg:ExactMatch, elg:SetMembership or elg:HierarchicalMatch"
        )
    _refuse_wildcards(graph, condition)
    required = tuple(sorted(graph.objects(condition, ELG.requiredConcept), key=str))
    excluded = tuple(sorted(graph.objects(condition, ELG.excludedConcept), key=str))
    if not required and not excluded:
        raise IRCompileError(f"{condition} declares neither elg:requiredConcept nor elg:excludedConcept")

    hierarchical = strategy == ELG.HierarchicalMatch
    scheme: Optional[SchemeResolution] = None
    expansion: Tuple[Tuple[URIRef, str], ...] = ()
    if hierarchical or not required:
        scheme = _resolve_scheme(graph, condition, context)
        ordering = _ordering(graph, scheme.scheme)
        _refuse_cycles(ordering, scheme.scheme)
        expansion = _expand(ordering, hierarchical, required, excluded)

    resolution_nodes: Tuple[URIRef, ...] = ()
    if scheme is not None:
        resolution_nodes = (scheme.contract, scheme.scheme) + ((scheme.binding,) if scheme.binding else ())
    return ConceptPlan(
        condition=condition,
        strategy=strategy,
        required=required,
        excluded=excluded,
        source_nodes=tuple(dict.fromkeys((condition,) + required + excluded + resolution_nodes)),
        scheme=scheme,
        expansion=expansion,
        evidence=read_evidence(graph, condition),
    )


def compile_any_condition(
    graph: Graph, condition: URIRef, context: Optional[ResolutionContext] = None
):
    """An ``IntervalPlan`` or a ``ConceptPlan``, by the condition's match strategy."""
    if graph.value(condition, ELG.matchStrategy) == ELG.IntervalContainment:
        return compile_condition(graph, condition)
    return compile_concept_condition(graph, condition, context)


def compile_profile(
    graph: Graph, profile: URIRef, context: Optional[ResolutionContext] = None
) -> ProfilePlan:
    """Compile one ``elg:AdmissionProfile`` and each of its conditions into a ``ProfilePlan``."""
    if (profile, RDF.type, ELG.AdmissionProfile) not in graph:
        raise IRCompileError(f"{profile} is not an elg:AdmissionProfile")
    aggregation = graph.value(profile, ELG.compatibilityOperation)
    if aggregation not in (ELG.AllRequired, ELG.AnySufficient):
        raise IRCompileError(
            f"{profile} declares compatibility operation {aggregation}, which has no evaluable "
            f"definition here (exe:RefusedOperation); elg:AllRequired and elg:AnySufficient are supported"
        )
    conditions = sorted(graph.objects(profile, ELG.hasCondition), key=str)
    if not conditions:
        raise IRCompileError(f"{profile} declares no elg:hasCondition")
    plans = [compile_any_condition(graph, condition, context) for condition in conditions]
    subjects = {plan.evidence.subject_class if plan.evidence else None for plan in plans}
    if len(subjects) > 1:
        raise IRCompileError(
            f"{profile}'s conditions read from different sources {sorted(map(str, subjects))}; a "
            f"profile evaluates either questions or one class of bound subjects"
        )
    return ProfilePlan(profile=profile, aggregation=aggregation, conditions=tuple(plans))
