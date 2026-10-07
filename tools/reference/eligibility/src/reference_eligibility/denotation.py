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
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import AbstractSet, Hashable, Mapping, Optional, Sequence

from .kernel import DENIED, PERMITTED, UNDETERMINED, Decision, every_value, neg3, some_value

Concept = Hashable


@dataclass(frozen=True)
class Scheme:
    """A concept scheme's membership and its ``skos:broader`` ordering,
    restricted to members (L9's "within the bound scheme")."""

    members: AbstractSet[Concept]
    broader: Mapping[Concept, AbstractSet[Concept]]

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
        """True when at least one member has a broader member within the
        scheme (L14's own condition, negated: this is false exactly when L14
        applies)."""
        return any(self.broader.get(member) for member in self.members)


def decide_concept_match(
    candidate: Concept,
    *,
    hierarchical: bool,
    required: AbstractSet[Concept],
    excluded: AbstractSet[Concept],
    scheme: Optional[Scheme] = None,
) -> Decision:
    """The single-candidate decision for ``elg:ExactMatch``, ``elg:SetMembership``
    or ``elg:HierarchicalMatch`` (ADR-A87's decision table), laws L9-L12 and
    L14. ``scheme`` is required when ``hierarchical`` is true, or when the
    condition declares exclusions only (no required concept) -- the two
    cases the law register's own decision table needs the bound scheme for.
    """

    # L9: the closure is "restricted to that scheme's members" -- a candidate
    # outside the resolved scheme entirely is Undetermined (exe:OutsideScheme
    # in the compilers), before anything else is asked of it, even an
    # otherwise-matching required or excluded concept. Found missing by
    # track B2's differential harness: the first version of this function
    # checked ancestry but never scheme membership itself.
    if scheme is not None and candidate not in scheme.members:
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

    # A declared required set the candidate matches none of: Denied.
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
    hierarchical: bool,
    required: AbstractSet[Concept],
    excluded: AbstractSet[Concept],
    scheme: Optional[Scheme] = None,
) -> Decision:
    """L15 (set readings) and L16 (negation), composed over L9-L12/L14's
    single-candidate decision (``decide_concept_match``).

    ``reading`` is one of ``"SingleValue"``, ``"SomeValue"`` or ``"EveryValue"``
    (``elg:valueReading``, ADR-A103). A single-value reading decides only
    when there is exactly one value: no value is Undetermined
    (``exe:MissingCandidate``), and more than one is Undetermined too
    (``exe:SeveralCandidates``) -- a question with several candidates and no
    declared reading to combine them is ambiguous, not a silent pick of the
    first. Found while differentially testing against
    ``tools/mork_compilers``' SPARQL backend (track B2): this module's first
    version took ``values[0]`` regardless of length, which agreed with the
    compiler only by accident, on fixtures with exactly one candidate.
    """

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
    elif reading == "SomeValue":
        decision = some_value([decide_one(v) for v in values])
    elif reading == "EveryValue":
        decision = every_value([decide_one(v) for v in values])
    else:
        raise ValueError(f"unknown value reading {reading!r}")

    return neg3(decision) if negated else decision
