# SPDX-License-Identifier: MPL-2.0
"""Eligibility's single-candidate decision (L9-L12, L14) and its set-reading
and negation composition (L15, L16).

Written directly from ``ontology/eligibility/README.md`` \u00a76's law prose, then
cross-checked against ``tools/mork_compilers/src/mork_compilers/eligibility_ir.py``'s
``_expand`` function only to confirm no case was missed -- not copied from
it. ``_expand`` is what every compiler backend (SPARQL, SHACL, SWRL, OWL)
ultimately reads, directly or through its "Expanded" form (ADR-A89), so an
independent reference that imported it would be comparing ``_expand``
against itself: track B2's differential tests would never be able to catch
a mistake in ``_expand`` shared by every backend. See this package's
``README.md`` for the full account.

**L13 is deliberately not implemented here** (confirmed, B2.1): the law register
(``ontology/eligibility/README.md`` §6) marks L13 ``elg:StaticConstraint``, not
``elg:SemanticLaw`` -- a declaration-time well-formedness rule ("each excluded
concept matches at least one required concept"), discharged by SHACL/SPARQL
static analysis of a condition's own declarations, never by this decision
function. L15 and L16 are, by contrast, deliberately implemented one layer up,
in ``decide_condition`` below -- a different reason for the same absence here.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import AbstractSet, FrozenSet, Hashable, Iterable, Mapping, Optional, Sequence, Tuple

from .kernel import DENIED, PERMITTED, UNDETERMINED, Decision, every_value, neg3, some_value

Concept = Hashable


@dataclass(frozen=True)
class Scheme:
    """A concept scheme's membership and its ordering by one hierarchy relation,
    restricted to members (L9's "within the bound scheme"). The relation is the
    condition's own, ``elg:hierarchyRelation`` or ``skos:broader``: ``broader`` holds
    only the links of that relation, so every law below is stated over whichever
    relation the caller chose, and none reads a link of another."""

    members: AbstractSet[Concept]
    broader: Mapping[Concept, AbstractSet[Concept]]

    @classmethod
    def over(cls, members: AbstractSet[Concept], links: Iterable[Tuple[Concept, Concept]]) -> "Scheme":
        """The scheme whose ordering is ``links``, pairs of (narrower, broader) of the
        condition's hierarchy relation. A pair with an end outside ``members`` is dropped
        (L9's restriction to the bound scheme)."""
        above: dict = {member: set() for member in members}
        for narrower, broader in links:
            if narrower in members and broader in members:
                above[narrower].add(broader)
        return cls(members=frozenset(members), broader={m: frozenset(b) for m, b in above.items()})

    def ancestors(self, concept: Concept) -> frozenset:
        """``concept`` and everything above it, reflexive-transitive (L9).
        Safe over a cyclic ordering (visited members are never requeued),
        though L9 itself requires the bound scheme's ordering to be acyclic
        for hierarchical match to have a truth condition at all."""
        found: set = set()
        pending = [concept]
        while pending:
            current = pending.pop()
            if current not in found:
                found.add(current)
                pending.extend(self.broader.get(current, ()))
        return frozenset(found)

    def has_hierarchy(self) -> bool:
        """True when at least one member has a link of the condition's hierarchy
        relation to another member (L14's own condition, negated: this is false
        exactly when L14 applies)."""
        return any(self.broader.get(member) for member in self.members)


def decide_concept_match(
    candidate: Concept,
    *,
    hierarchical: bool,
    required: AbstractSet[Concept],
    excluded: AbstractSet[Concept],
    scheme: Optional[Scheme] = None,
    unresolved: bool = False,
) -> Decision:
    """The single-candidate decision for ``elg:ExactMatch``, ``elg:SetMembership``
    or ``elg:HierarchicalMatch`` (ADR-A87's decision table), laws L9-L12 and
    L14. ``scheme`` is required when ``hierarchical`` is true, or when the
    condition declares exclusions only (no required concept) -- the two
    cases the law register's own decision table needs the bound scheme for.
    ``unresolved`` says the condition's contract has bindings and none of them
    applies at the resolution time, which differs from a condition bound to no
    contract at all.
    """

    # L9: the closure is "restricted to that scheme's members" -- a candidate
    # outside the resolved scheme entirely is Undetermined (exe:OutsideScheme
    # in the compilers), before anything else is asked of it, even an
    # otherwise-matching required or excluded concept. Found missing by
    # track B2's differential harness: the first version of this function
    # checked ancestry but never scheme membership itself.
    if scheme is not None and candidate not in scheme.members:
        return UNDETERMINED

    # L9: a hierarchical condition's closure is a relation *within the bound
    # scheme*. With no resolved scheme at all there is no closure to test a
    # candidate against -- not "this candidate fails the closure" (Denied),
    # but "there is no closure to ask", the same reason L14 leaves an
    # otherwise-undecided candidate Undetermined rather than Denied. Found by
    # the formal-methods epic's second review (B2.2): before this guard,
    # every hierarchical candidate fell through to the unmatched-required
    # branch below and was wrongly Denied.
    if hierarchical and scheme is None:
        return UNDETERMINED

    # L12: a condition with exclusions only admits every member of its bound
    # scheme. When its contract's bindings resolve to no scheme there are no
    # members to admit, and the empty scheme that could have resolved leaves
    # every candidate Undetermined, so no other answer holds under every
    # resolution, an excluded candidate included (Resolution.thy, TR4). A
    # condition bound to no contract keeps its open reading below.
    if not required and unresolved:
        return UNDETERMINED

    def matches(concept: Concept) -> bool:
        if not hierarchical:
            return candidate == concept
        return scheme is not None and concept in scheme.ancestors(candidate)

    # L10: an excluded match is Denied, whether or not it also matches a
    # required concept.
    if any(matches(concept) for concept in excluded):
        return DENIED

    # L14: a flat scheme (no member has a broader member within it) leaves an
    # otherwise-undecided member Undetermined, before L12's default
    # inclusion applies.
    if hierarchical and scheme is not None and not scheme.has_hierarchy():
        return PERMITTED if candidate in required else UNDETERMINED

    # A declared required set the candidate matches none of: Denied. (ADR-A87's own
    # decision table, ``elg:AllRequired``; ``exe:NoMatchingRequiredConcept`` in the
    # compilers.) Untraced before B2.1: this branch carries no law-ID comment because
    # no single law states it in isolation; it is the complement of L12's default
    # inclusion, under the same hierarchical-vs-flat conditions L14 and L12 state.
    if required and not any(matches(concept) for concept in required):
        return DENIED

    # L11: under hierarchical match, standing strictly above an excluded
    # concept leaves Undetermined -- the candidate's true value may or may
    # not fall under the exclusion.
    if hierarchical and scheme is not None:
        for concept in excluded:
            if (
                concept in scheme.members
                and candidate in scheme.ancestors(concept)
                and candidate != concept
            ):
                return UNDETERMINED

    # L12: default inclusion -- a required match was found, or nothing is
    # required (only exclusions were declared, already checked above).
    return PERMITTED


def decide_condition(
    values: Sequence[Concept],
    *,
    reading: str,
    negated: bool,
    closed: bool = False,
    hierarchical: bool,
    required: AbstractSet[Concept],
    excluded: AbstractSet[Concept],
    scheme: Optional[Scheme] = None,
) -> Decision:
    """L15 (set readings) and L16 (negation), composed over L9-L12/L14's
    single-candidate decision (``decide_concept_match``).

    ``reading`` is one of ``"SingleValue"``, ``"SomeValue"`` or ``"EveryValue"``
    (``elg:valueReading``, ADR-A103). ``closed`` is whether the binding names a
    closure in force (``elg:closedUnder``, ADR-A105, L17): only then does a set
    reading decide on the values reached being all there are. A closure never
    changes a single-value reading. A single-value reading decides only
    when there is exactly one value: no value is Undetermined
    (``exe:MissingCandidate``), and more than one is Undetermined too
    (``exe:SeveralCandidates``) -- a question with several candidates and no
    declared reading to combine them is ambiguous, not a silent pick of the
    first. Found while differentially testing against
    ``tools/mork_compilers``' SPARQL backend (track B2): this module's first
    version took ``values[0]`` regardless of length, which agreed with the
    compiler only by accident, on fixtures with exactly one candidate.
    """
    decision, _ = decide_condition_with_reliance(
        values,
        reading=reading,
        negated=negated,
        closed=closed,
        hierarchical=hierarchical,
        required=required,
        excluded=excluded,
        scheme=scheme,
    )
    return decision


def decide_condition_with_reliance(
    values: Sequence[Concept],
    *,
    reading: str,
    negated: bool,
    closed: bool = False,
    hierarchical: bool,
    required: AbstractSet[Concept],
    excluded: AbstractSet[Concept],
    scheme: Optional[Scheme] = None,
) -> Tuple[Decision, bool]:
    """``decide_condition``'s decision, and whether it relied on the closure (ADR-A105's
    2026-10-12 addendum, HQ6a2-Q3).

    A decision relies on the closure exactly when completeness decided it: ``SomeValue`` Denied
    or ``EveryValue`` Permitted under a closure in force, the empty case included. Reliance is
    decided before negation, so a negated condition relies on what it negates relied on. Without
    a closure those outcomes are Undetermined, and nothing relies on one. The differential
    harness checks the compilers' ``?closure`` column against this."""

    def decide_one(candidate: Concept) -> Decision:
        return decide_concept_match(
            candidate,
            hierarchical=hierarchical,
            required=required,
            excluded=excluded,
            scheme=scheme,
        )

    if reading == "SingleValue":
        decision = decide_one(values[0]) if len(values) == 1 else UNDETERMINED
        relied = False
    elif reading == "SomeValue":
        decision = some_value(closed, [decide_one(v) for v in values])
        relied = closed and decision is DENIED
    elif reading == "EveryValue":
        decision = every_value(closed, [decide_one(v) for v in values])
        relied = closed and decision is PERMITTED
    else:
        raise ValueError(f"unknown value reading {reading!r}")

    return (neg3(decision) if negated else decision), relied


SUBSET, INTERSECTS, DISJOINT = "Subset", "Intersects", "Disjoint"


def _found(
    value: Concept, reference: AbstractSet[Concept], *, hierarchical: bool, scheme: Optional[Scheme]
) -> bool:
    """Whether ``value`` matches a reference value (L18): equal under exact match, and under
    hierarchical match a member of the scheme at or below a reference value that is a member,
    by the condition's hierarchy relation (L9)."""
    if not hierarchical:
        return value in reference
    return (
        scheme is not None
        and value in scheme.members
        and any(r in scheme.members and r in scheme.ancestors(value) for r in reference)
    )


def decide_member(
    value: Concept,
    reference: AbstractSet[Concept],
    *,
    hierarchical: bool,
    scheme: Optional[Scheme],
    reference_closed: bool,
) -> Decision:
    """One tested value's decision (L18): Permitted when found among the reference values,
    Denied when found in none and the reference binding names a closure in force, otherwise
    Undetermined."""
    if _found(value, reference, hierarchical=hierarchical, scheme=scheme):
        return PERMITTED
    return DENIED if reference_closed else UNDETERMINED


def decide_set_comparison_with_reliance(
    tested: Sequence[Concept],
    reference: AbstractSet[Concept],
    *,
    comparison: str,
    hierarchical: bool,
    scheme: Optional[Scheme] = None,
    tested_closed: bool = False,
    reference_closed: bool = False,
    negated: bool = False,
    unresolved: bool = False,
) -> Tuple[Decision, FrozenSet[str]]:
    """L18: ``decide_set_comparison``'s decision, and which closures it relied on, a subset of
    ``{"tested", "reference"}``.

    The tested set's closure is relied on when completeness of the tested set decided: Subset
    Permitted, or Intersects Denied. The reference set's closure is relied on when a value was
    Denied and that decided: Subset Denied, or Intersects Denied with a tested value. Disjoint
    relies on what Intersects relied on (L16)."""
    if unresolved or (hierarchical and scheme is None):
        return UNDETERMINED, frozenset()  # L9: there is no scheme to decide a value against
    outcomes = [
        decide_member(v, reference, hierarchical=hierarchical, scheme=scheme, reference_closed=reference_closed)
        for v in tested
    ]
    if comparison == SUBSET:
        decision = every_value(tested_closed, outcomes)
        relied = {"tested"} if tested_closed and decision is PERMITTED else set()
        if decision is DENIED:
            relied.add("reference")
    elif comparison in (INTERSECTS, DISJOINT):
        decision = some_value(tested_closed, outcomes)
        relied = {"tested"} if tested_closed and decision is DENIED else set()
        if decision is DENIED and outcomes:
            relied.add("reference")
        if comparison == DISJOINT:
            decision = neg3(decision)
    else:
        raise ValueError(f"unknown comparison {comparison!r}")
    return (neg3(decision) if negated else decision), frozenset(relied)


def decide_set_comparison(
    tested: Sequence[Concept],
    reference: AbstractSet[Concept],
    *,
    comparison: str,
    hierarchical: bool,
    scheme: Optional[Scheme] = None,
    tested_closed: bool = False,
    reference_closed: bool = False,
    negated: bool = False,
    unresolved: bool = False,
) -> Decision:
    """L18, with L15 to L17 and L9: each tested value is decided against the reference values
    (``decide_member``), and the outcomes are read as every value under Subset, some value under
    Intersects, and some value negated under Disjoint, the tested set's closure licensing the
    reading. ``negated`` is the condition's own ``elg:negated`` (L16)."""
    return decide_set_comparison_with_reliance(
        tested,
        reference,
        comparison=comparison,
        hierarchical=hierarchical,
        scheme=scheme,
        tested_closed=tested_closed,
        reference_closed=reference_closed,
        negated=negated,
        unresolved=unresolved,
    )[0]
