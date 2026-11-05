# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""
Eligibility executable IR (ADR-A24; a scoped subset of the executable-
semantics design in the MORK enhancements analysis).

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
- A hierarchical condition walks the relation it names with ``elg:hierarchyRelation``,
  ``skos:broader`` when it names none (L9). A scheme contract whose bindings apply at no
  instant or in no scope compiles to a plan that answers Undetermined for every candidate
  (``exe:NoApplicableBinding``). Conflicting bindings are refused (ADR-A85).
- A set comparison (``elg:SetComparison``, L18) compiles to a ``SetComparisonPlan`` holding its
  comparison, match strategy, hierarchy relation and scheme, and the two bindings' evidence paths
  with their closures. The comparison fixes the reading, so each path's closure is resolved as a
  set reading would be (L17). Whatever ``elg:SetComparisonBindingsShape`` and the structural
  shapes refuse is refused here with an ``IRCompileError``.
- Profile aggregation (``elg:AllRequired``, ``elg:AnySufficient``) uses
  strong Kleene logic over the three outcomes (ADR-A89 item 5).
  Any other composition operation, for example one a downstream ontology
  adds, has no evaluable definition here and is refused
  (``exe:RefusedOperation``).
- Runtime result tracking (the design note's ``exe:EvaluationRun``,
  ``exe:ConditionResult``, §6-§13) is not implemented — this module compiles
  artefacts; it does not run them or record what running them produced.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, FrozenSet, List, Optional, Sequence, Set, Tuple, Union

from rdflib import Graph, Literal, URIRef
from rdflib.namespace import RDF, RDFS, SKOS
from vocabulary import BindingConflictError, NoApplicableBindingError, resolve

from .namespaces import ELG, FND, QNT, VOC

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
    ``unit`` is the unit the bounds are stated in. It applies only to a
    candidate in that unit (ADR-A95). ``None`` applies to any candidate.
    """

    lower: Optional[float]
    lower_closed: bool
    upper: Optional[float]
    upper_closed: bool
    unit: Optional[URIRef] = None


@dataclass(frozen=True)
class EvidencePath:
    """Where a bound condition reads its candidate (ADR-A91): each instance of
    ``subject_class``, along ``steps`` of (property, inverse) in order."""

    binding: URIRef
    subject_class: URIRef
    steps: Tuple[Tuple[URIRef, bool], ...]
    space: Optional[URIRef] = None  # elg:readOnSpace, for a literal at the path's end
    single_valued: bool = False  # elg:singleValued, the claim the OWL backend needs
    reading: URIRef = ELG.SingleValue  # elg:valueReading (ADR-A103, L15)
    closure: Optional[URIRef] = None  # elg:closedUnder, in force at the resolution instant (ADR-A105, L17)


@dataclass(frozen=True)
class IntervalPlan:
    """The executable IR for one ``elg:IntervalCondition``."""

    condition: URIRef
    value_space: URIRef
    required: Sequence[RequiredInterval]
    source_nodes: Sequence[URIRef]  # provenance: every declaration node read, condition first
    evidence: Optional[EvidencePath] = None
    negated: bool = False  # elg:negated (ADR-A103, L16)


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
    with its decision, sorted by concept. ``hierarchy`` pairs every member
    with the members above it by ``relation``, both sorted.

    ``relation`` is the property a hierarchical condition walks, its
    ``elg:hierarchyRelation`` or ``skos:broader`` when it names none (L9). It is
    read from the graph exactly, never widened to its sub-properties.
    ``unresolved`` is set when the condition needs its scheme and the contract's
    bindings apply at no instant or in no scope: ``scheme`` is then ``None``
    and every candidate is Undetermined (L9, ``exe:NoApplicableBinding``).
    """

    condition: URIRef
    strategy: URIRef
    required: Sequence[URIRef]
    excluded: Sequence[URIRef]
    source_nodes: Sequence[URIRef]  # provenance: condition, concepts, contract, scheme, binding
    scheme: Optional[SchemeResolution] = None
    expansion: Tuple[Tuple[URIRef, str], ...] = ()
    evidence: Optional[EvidencePath] = None
    negated: bool = False  # elg:negated (ADR-A103, L16)
    hierarchy: Tuple[Tuple[URIRef, Tuple[URIRef, ...]], ...] = ()
    relation: URIRef = SKOS.broader
    unresolved: bool = False

    @property
    def hierarchical(self) -> bool:
        return self.strategy == ELG.HierarchicalMatch

    @property
    def no_hierarchy(self) -> bool:
        """Hierarchical match over a resolved scheme in which no member has a
        link of ``relation`` to another member (L14, ADR-A100)."""
        return self.hierarchical and self.scheme is not None and not any(above for _, above in self.hierarchy)


CONCEPT_STRATEGIES = (ELG.ExactMatch, ELG.SetMembership, ELG.HierarchicalMatch)
COMPARISONS = (ELG.Subset, ELG.Intersects, ELG.Disjoint)
COMPARISON_STRATEGIES = (ELG.ExactMatch, ELG.HierarchicalMatch)


@dataclass(frozen=True)
class SetComparisonPlan:
    """The executable IR for one ``elg:SetComparison`` (L18).

    ``tested`` and ``reference`` are the two bindings' paths from one subject class. A tested
    value is Permitted when it matches a reference value, equal under ``elg:ExactMatch`` and, under
    ``elg:HierarchicalMatch``, a member of ``scheme`` at or below a reference value that is a member,
    by ``relation``. It is Denied when it matches none and ``reference.closure`` is in force,
    otherwise Undetermined. A tested value outside ``scheme`` is Undetermined (``exe:OutsideScheme``), and
    when ``no_hierarchy`` a value that is not equal to a reference value is Undetermined
    (``exe:NoHierarchy``) whatever the closure (L14). ``tested.closure`` licenses the reading of the outcomes. ``unresolved``
    is set when the contract's bindings apply at no instant or in no scope, so ``scheme`` is ``None``
    and every subject is Undetermined (L9, ``exe:NoApplicableBinding``)."""

    condition: URIRef
    comparison: URIRef
    strategy: URIRef
    tested: EvidencePath
    reference: EvidencePath
    source_nodes: Sequence[URIRef]
    scheme: Optional[SchemeResolution] = None
    relation: URIRef = SKOS.broader
    unresolved: bool = False
    hierarchy: Tuple[Tuple[URIRef, Tuple[URIRef, ...]], ...] = ()
    negated: bool = False  # elg:negated (L16)

    @property
    def evidence(self) -> EvidencePath:
        """The tested path, which fixes the plan's subject class as a bound condition's path does."""
        return self.tested

    @property
    def hierarchical(self) -> bool:
        return self.strategy == ELG.HierarchicalMatch

    @property
    def no_hierarchy(self) -> bool:
        """Hierarchical match over a resolved scheme in which no member has a link of ``relation`` to
        another member: L14 applies to the reference values as it does to required concepts (L18)."""
        return self.hierarchical and self.scheme is not None and not any(above for _, above in self.hierarchy)

    @property
    def closures(self) -> Tuple[URIRef, ...]:
        return tuple(c for c in (self.tested.closure, self.reference.closure) if c is not None)


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
    conditions: Sequence[Union[IntervalPlan, ConceptPlan, "SetComparisonPlan"]]

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


def _statements(graph: Graph, bound: URIRef, source_nodes: List[URIRef]) -> Dict[Optional[URIRef], tuple]:
    """The bound and its ``qnt:alternativeBound`` statements, keyed by unit (ADR-A95)."""
    statements: Dict[Optional[URIRef], tuple] = {}
    peers = {bound} | set(graph.objects(bound, QNT.alternativeBound)) | set(graph.subjects(QNT.alternativeBound, bound))
    for statement in sorted(peers, key=str):
        unit = graph.value(graph.value(statement, QNT.boundValue), QNT.inUnit)
        if unit in statements:
            raise IRCompileError(f"{bound} is stated twice in unit {unit}")
        statements[unit] = _bound_value(graph, statement, source_nodes)
    return statements


def read_evidence(
    graph: Graph, condition: URIRef, context: Optional["ResolutionContext"] = None
) -> Optional[EvidencePath]:
    """The condition's ``elg:EvidenceBinding``, if it has one."""
    bindings = sorted(graph.subjects(ELG.bindsCondition, condition), key=str)
    if not bindings:
        return None
    if len(bindings) > 1:
        raise IRCompileError(f"{condition} is bound by several elg:EvidenceBinding individuals: {bindings}")
    return read_binding(graph, bindings[0], context)


def read_binding(
    graph: Graph, binding: URIRef, context: Optional["ResolutionContext"] = None, reading: Optional[URIRef] = None
) -> EvidencePath:
    """One ``elg:EvidenceBinding``'s path. ``reading`` overrides the binding's own, as a set
    comparison fixes the reading of both its bindings (L18)."""
    reading = reading if reading is not None else _reading(graph, binding)
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
        single_valued=graph.value(binding, ELG.singleValued) == Literal(True),
        reading=reading,
        closure=_closure(graph, binding, reading, context),
    )


READINGS = (ELG.SingleValue, ELG.SomeValue, ELG.EveryValue)


def _closure(graph: Graph, binding: URIRef, reading: URIRef, context: Optional["ResolutionContext"]) -> Optional[URIRef]:
    """The closure a binding relies on, if one is named and in force (ADR-A105, L17).

    A binding naming something that is not an ``elg:Closure``, or a closure with no
    ``elg:licensedBy`` source, is refused (``exe:NoClosureLicence``). A closure never changes a
    single-value reading. A closure whose source states a valid time is in force from it, which
    needs the caller's resolution instant (ADR-A89 item 2). The instant stands for the deciding
    record's recording time, the cut."""
    closure = graph.value(binding, ELG.closedUnder)
    if closure is None:
        return None
    if (closure, RDF.type, ELG.Closure) not in graph:
        raise IRCompileError(f"exe:NoClosureLicence: {binding} names {closure}, which is not an elg:Closure (ADR-A105)")
    source = graph.value(closure, ELG.licensedBy)
    if source is None:
        raise IRCompileError(f"exe:NoClosureLicence: {closure} names no elg:licensedBy source (ADR-A105)")
    if reading == ELG.SingleValue:
        return None
    start = graph.value(graph.value(source, FND.hasTemporalScope), FND.validFrom)
    if start is None:
        return closure
    if context is None:
        raise IRCompileError(
            f"{closure}'s source takes effect at {start}, so compiling {binding} needs an explicit "
            f"resolution instant (ADR-A89 item 2, L17)"
        )
    return closure if start.toPython() <= context.at else None


def _reading(graph: Graph, binding: URIRef) -> URIRef:
    reading = graph.value(binding, ELG.valueReading, default=ELG.SingleValue)
    if reading not in READINGS:
        raise IRCompileError(f"{binding} declares elg:valueReading {reading}, which is none of {READINGS}")
    return reading


def _negated(graph: Graph, condition: URIRef) -> bool:
    return graph.value(condition, ELG.negated) == Literal(True)


def refuse_without_scheme(plan, backend: str) -> None:
    """Refuse a concept plan that has no scheme to decide against, for a backend that cannot
    state Undetermined (L9): an unresolved plan, or a hierarchical one with no scheme."""
    if isinstance(plan, ConceptPlan) and (plan.unresolved or (plan.hierarchical and plan.scheme is None)):
        raise IRCompileError(
            f"{plan.condition} has no resolved scheme, so every candidate is Undetermined (L9), "
            f"which a {backend} cannot express"
        )


def refuse_set_comparison(plan, backend: str, reason: str) -> None:
    """Refuse a plan, or a profile holding a condition, that is a set comparison (ADR-A90)."""
    for part in plan.conditions if isinstance(plan, ProfilePlan) else (plan,):
        if isinstance(part, SetComparisonPlan):
            raise IRCompileError(f"{part.condition} is a set comparison, which a {backend} cannot compile: {reason} (ADR-A90)")


def closures_of(plan) -> Tuple[URIRef, ...]:
    """The closures a condition plan may rely on: its path's, or both of a set comparison's."""
    if isinstance(plan, SetComparisonPlan):
        return plan.closures
    return (plan.evidence.closure,) if plan.evidence is not None and plan.evidence.closure is not None else ()


def has_readings(plan) -> bool:
    """Whether a plan, or any condition of a profile plan, reads several values
    or is negated (ADR-A103). The SWRL and OWL backends refuse such plans."""
    if isinstance(plan, ProfilePlan):
        return any(has_readings(condition) for condition in plan.conditions)
    if isinstance(plan, SetComparisonPlan):
        return True
    reading = plan.evidence.reading if plan.evidence is not None else ELG.SingleValue
    return plan.negated or reading != ELG.SingleValue


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

        lower = _statements(graph, lower_bound, source_nodes) if lower_bound is not None else None
        upper = _statements(graph, upper_bound, source_nodes) if upper_bound is not None else None
        # a unit counts only where every declared bound of the range is stated in it
        units = set(lower or upper) & set(upper or lower)
        if not units:
            raise IRCompileError(f"{range_node}'s bounds share no unit (qnt:NoBoundInUnit)")
        for unit in sorted(units, key=lambda u: str(u or "")):
            lower_value, lower_closed = lower[unit] if lower else (None, False)
            upper_value, upper_closed = upper[unit] if upper else (None, False)
            required.append(RequiredInterval(lower_value, lower_closed, upper_value, upper_closed, unit))

    evidence = read_evidence(graph, condition)
    if evidence is not None and evidence.space is not None and evidence.space != value_space:
        raise IRCompileError(
            f"{evidence.binding} reads on {evidence.space}, but {condition} constrains {value_space} "
            f"(exe:ValueSpaceMismatch)"
        )
    deduplicated = tuple(dict.fromkeys(source_nodes))
    return IntervalPlan(
        condition=condition, value_space=value_space, required=tuple(required),
        source_nodes=deduplicated, evidence=evidence, negated=_negated(graph, condition),
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
) -> Optional[SchemeResolution]:
    """The scheme the condition's contract resolves to, or ``None`` when its
    bindings apply at no instant or in no scope and no scheme is bound as a
    fallback. A condition that needs its scheme then answers Undetermined for
    every candidate (L9). Conflicting bindings are refused (ADR-A85)."""
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
        except NoApplicableBindingError:
            return None
        except BindingConflictError as error:
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


def hierarchy_relation(graph: Graph, condition: URIRef) -> URIRef:
    """The relation a hierarchical condition walks (L9): its ``elg:hierarchyRelation``,
    ``skos:broader`` when it names none. A relation that is neither ``skos:broader`` nor
    declared a sub-property of it in ``graph`` is refused, as ``elg:HierarchyRelationShape``
    reports it."""
    named = sorted(graph.objects(condition, ELG.hierarchyRelation), key=str)
    if not named:
        return SKOS.broader
    if len(named) > 1:
        raise IRCompileError(f"{condition} names several hierarchy relations: {named}")
    relation = named[0]
    if relation != SKOS.broader and SKOS.broader not in set(graph.transitive_objects(relation, RDFS.subPropertyOf)):
        raise IRCompileError(
            f"{condition} names hierarchy relation {relation}, which is neither skos:broader nor "
            f"declared a sub-property of it (L9)"
        )
    return relation


def _ordering(graph: Graph, scheme: URIRef, relation: URIRef = SKOS.broader) -> Dict[URIRef, Set[URIRef]]:
    """Each member of ``scheme`` mapped to the members above it by ``relation``."""
    members = set(graph.subjects(SKOS.inScheme, scheme))
    return {
        member: {broader for broader in graph.objects(member, relation) if broader in members}
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


def _refuse_cycles(ordering: Dict[URIRef, Set[URIRef]], scheme: URIRef, relation: URIRef) -> None:
    for member in ordering:
        if any(member in _ancestors(ordering, broader) for broader in ordering[member]):
            raise IRCompileError(
                f"{scheme} has a cycle of {relation} through {member}; hierarchical match has no "
                f"truth condition under it (L9)"
            )


def _expand(
    ordering: Dict[URIRef, Set[URIRef]],
    hierarchical: bool,
    required: Sequence[URIRef],
    excluded: Sequence[URIRef],
) -> Tuple[Tuple[URIRef, str], ...]:
    """The ADR-A87 decision for every member of the resolved scheme."""
    ancestors = {member: _ancestors(ordering, member) for member in ordering}
    no_hierarchy = hierarchical and not any(ordering.values())

    def matches(candidate: URIRef, concept: URIRef) -> bool:
        return concept in ancestors[candidate] if hierarchical else concept == candidate

    decided = []
    for candidate in sorted(ordering, key=str):
        if any(matches(candidate, concept) for concept in excluded):
            decision = DENIED  # L10
        elif no_hierarchy:
            decision = PERMITTED if candidate in required else UNDETERMINED  # L14, before L12
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
    relation = hierarchy_relation(graph, condition) if hierarchical else SKOS.broader
    scheme: Optional[SchemeResolution] = None
    unresolved = False
    expansion: Tuple[Tuple[URIRef, str], ...] = ()
    hierarchy: Tuple[Tuple[URIRef, Tuple[URIRef, ...]], ...] = ()
    if hierarchical or not required:
        scheme = _resolve_scheme(graph, condition, context)
        unresolved = scheme is None
        if scheme is not None:
            ordering = _ordering(graph, scheme.scheme, relation)
            _refuse_cycles(ordering, scheme.scheme, relation)
            expansion = _expand(ordering, hierarchical, required, excluded)
            hierarchy = tuple((m, tuple(sorted(ordering[m], key=str))) for m in sorted(ordering, key=str))

    resolution_nodes: Tuple[URIRef, ...] = ()
    if scheme is not None:
        resolution_nodes = (scheme.contract, scheme.scheme) + ((scheme.binding,) if scheme.binding else ())
    elif unresolved:
        resolution_nodes = (graph.value(condition, ELG.constrainedByContract),)
    return ConceptPlan(
        condition=condition,
        strategy=strategy,
        required=required,
        excluded=excluded,
        source_nodes=tuple(dict.fromkeys((condition,) + required + excluded + resolution_nodes)),
        scheme=scheme,
        expansion=expansion,
        evidence=read_evidence(graph, condition, context),
        hierarchy=hierarchy,
        negated=_negated(graph, condition),
        relation=relation,
        unresolved=unresolved,
    )


def _single(graph: Graph, subject: URIRef, predicate: URIRef, what: str) -> URIRef:
    found = sorted(graph.objects(subject, predicate), key=str)
    if len(found) != 1:
        raise IRCompileError(f"{subject} names {len(found)} {what}, and a set comparison names exactly one (L18)")
    return found[0]


def compile_set_comparison(
    graph: Graph, condition: URIRef, context: Optional[ResolutionContext] = None
) -> SetComparisonPlan:
    """Compile one ``elg:SetComparison`` (L18). Refuses what its shapes refuse: not exactly one
    comparison, tested binding or reference binding, the two bindings being one, a binding that
    does not name the comparison or names another subject class, a binding that declares a value
    reading or a value space, a binding of the comparison that is neither of its two, a match
    strategy other than exact or hierarchical, and a required or excluded concept."""
    if (condition, RDF.type, ELG.SetComparison) not in graph:
        raise IRCompileError(f"{condition} is not an elg:SetComparison")
    comparison = _single(graph, condition, ELG.comparison, "comparisons")
    if comparison not in COMPARISONS:
        raise IRCompileError(f"{condition} declares comparison {comparison}, which is none of {COMPARISONS}")
    strategy = graph.value(condition, ELG.matchStrategy)
    if strategy not in COMPARISON_STRATEGIES:
        raise IRCompileError(
            f"{condition} declares match strategy {strategy}; a set comparison matches by elg:ExactMatch "
            f"or elg:HierarchicalMatch"
        )
    _refuse_wildcards(graph, condition)
    if any(graph.objects(condition, ELG.requiredConcept)) or any(graph.objects(condition, ELG.excludedConcept)):
        raise IRCompileError(f"{condition} names a required or excluded concept, and a set comparison's reference binding takes their place")
    tested = _single(graph, condition, ELG.testedBinding, "tested bindings")
    reference = _single(graph, condition, ELG.referenceBinding, "reference bindings")
    if tested == reference:
        raise IRCompileError(f"{condition}'s tested and reference bindings are one binding, {tested}")
    bound = set(graph.subjects(ELG.bindsCondition, condition))
    if bound != {tested, reference}:
        raise IRCompileError(
            f"{condition} is bound by {sorted(map(str, bound))}, and must be bound by exactly its tested and "
            f"reference bindings (L18)"
        )
    for binding in (tested, reference):
        if graph.value(binding, ELG.valueReading) is not None or graph.value(binding, ELG.readOnSpace) is not None:
            raise IRCompileError(
                f"{binding} declares a value reading or a value space, and a set comparison fixes the reading "
                f"and compares IRIs only (L18)"
            )
    tested_path = read_binding(graph, tested, context, ELG.SomeValue)
    reference_path = read_binding(graph, reference, context, ELG.SomeValue)
    if tested_path.subject_class != reference_path.subject_class:
        raise IRCompileError(f"{condition}'s two bindings name different subject classes, which must be one (L18)")

    hierarchical = strategy == ELG.HierarchicalMatch
    relation = hierarchy_relation(graph, condition) if hierarchical else SKOS.broader
    scheme: Optional[SchemeResolution] = None
    hierarchy: Tuple[Tuple[URIRef, Tuple[URIRef, ...]], ...] = ()
    unresolved = False
    if hierarchical:
        scheme = _resolve_scheme(graph, condition, context)
        unresolved = scheme is None
        if scheme is not None:
            ordering = _ordering(graph, scheme.scheme, relation)
            _refuse_cycles(ordering, scheme.scheme, relation)
            hierarchy = tuple((m, tuple(sorted(ordering[m], key=str))) for m in sorted(ordering, key=str))
    resolution_nodes: Tuple[URIRef, ...] = ()
    if scheme is not None:
        resolution_nodes = (scheme.contract, scheme.scheme) + ((scheme.binding,) if scheme.binding else ())
    elif unresolved:
        resolution_nodes = (graph.value(condition, ELG.constrainedByContract),)
    return SetComparisonPlan(
        condition=condition,
        comparison=comparison,
        strategy=strategy,
        tested=tested_path,
        reference=reference_path,
        source_nodes=tuple(dict.fromkeys((condition, tested, reference) + resolution_nodes)),
        scheme=scheme,
        relation=relation,
        unresolved=unresolved,
        hierarchy=hierarchy,
        negated=_negated(graph, condition),
    )


def compile_any_condition(
    graph: Graph, condition: URIRef, context: Optional[ResolutionContext] = None
):
    """An ``IntervalPlan``, a ``ConceptPlan`` or a ``SetComparisonPlan``, by the condition's class and match strategy."""
    if (condition, RDF.type, ELG.SetComparison) in graph:
        return compile_set_comparison(graph, condition, context)
    if graph.value(condition, ELG.matchStrategy) == ELG.IntervalContainment:
        return compile_condition(graph, condition)
    return compile_concept_condition(graph, condition, context)


def compile_profile(
    graph: Graph, profile: URIRef, context: Optional[ResolutionContext] = None
) -> ProfilePlan:
    """Compile one ``elg:AdmissionProfile`` and each of its conditions into a ``ProfilePlan``."""
    if (profile, RDF.type, ELG.AdmissionProfile) not in graph:
        raise IRCompileError(f"{profile} is not an elg:AdmissionProfile")
    aggregation = graph.value(profile, ELG.compositionOperation)
    if aggregation not in (ELG.AllRequired, ELG.AnySufficient):
        raise IRCompileError(
            f"{profile} declares composition operation {aggregation}, which has no evaluable "
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
