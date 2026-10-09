# SPDX-License-Identifier: MPL-2.0
"""Tests for Eligibility's single-candidate decision (L9-L12, L14) and its
set-reading and negation composition (L15, L16), written directly from the
law register's own worked descriptions, not from ``eligibility_ir.py``.

A small citrus/fruit hierarchy is used throughout:

    fruit
      \\-- citrus
            \\-- orange
            \\-- lemon

    vegetable   (a second, unrelated branch)
"""

from __future__ import annotations

from reference_eligibility.denotation import Scheme, decide_concept_match, decide_condition
from reference_eligibility.kernel import DENIED, PERMITTED, UNDETERMINED

FRUIT, CITRUS, ORANGE, LEMON, VEGETABLE = "fruit", "citrus", "orange", "lemon", "vegetable"

FRUIT_SCHEME = Scheme(
    members=frozenset({FRUIT, CITRUS, ORANGE, LEMON, VEGETABLE}),
    broader={CITRUS: frozenset({FRUIT}), ORANGE: frozenset({CITRUS}), LEMON: frozenset({CITRUS})},
)

FLAT_SCHEME = Scheme(members=frozenset({"a", "b", "c"}), broader={})


class TestL9HierarchicalClosure:
    """A candidate satisfies a hierarchical condition exactly when it is the
    required concept or narrower than it (L9's reflexive-transitive closure
    "below the asserted value")."""

    def test_narrower_candidate_matches(self) -> None:
        decision = decide_concept_match(
            ORANGE, hierarchical=True, required={CITRUS}, excluded=set(), scheme=FRUIT_SCHEME
        )
        assert decision is PERMITTED

    def test_candidate_matches_itself(self) -> None:
        decision = decide_concept_match(
            CITRUS, hierarchical=True, required={CITRUS}, excluded=set(), scheme=FRUIT_SCHEME
        )
        assert decision is PERMITTED

    def test_broader_candidate_does_not_match(self) -> None:
        decision = decide_concept_match(
            FRUIT, hierarchical=True, required={CITRUS}, excluded=set(), scheme=FRUIT_SCHEME
        )
        assert decision is DENIED

    def test_unrelated_branch_does_not_match(self) -> None:
        decision = decide_concept_match(
            VEGETABLE, hierarchical=True, required={CITRUS}, excluded=set(), scheme=FRUIT_SCHEME
        )
        assert decision is DENIED

    def test_candidate_outside_the_scheme_entirely_is_undetermined(self) -> None:
        """Found by track B2's differential harness against the compilers'
        own exe:OutsideScheme handling: a candidate that is not a member of
        the resolved scheme at all is Undetermined, overriding what L10's
        exclusion match would otherwise say -- "restricted to that scheme's
        members" (L9) takes priority over everything else."""
        decision = decide_concept_match(
            "mango", hierarchical=True, required={CITRUS}, excluded={CITRUS}, scheme=FRUIT_SCHEME
        )
        assert decision is UNDETERMINED

    def test_hierarchical_match_with_no_resolved_scheme_is_undetermined(self) -> None:
        """Found by the formal-methods epic's second review (B2.2): a
        hierarchical condition with no resolved scheme at all has no closure
        to test a candidate against -- L9's own statement is conditioned on
        "the bound scheme", which does not exist here, the same reason L14
        leaves an otherwise-undecided candidate Undetermined rather than
        Denied. Before this fix, ``matches()`` silently returned False for
        every candidate when ``hierarchical`` was true and ``scheme`` was
        ``None``, so a declared ``required`` set fell through to the
        unmatched-required branch and returned Denied -- a condition cannot
        be shown to fail a closure that was never resolved."""
        decision = decide_concept_match(
            ORANGE, hierarchical=True, required={CITRUS}, excluded=set(), scheme=None
        )
        assert decision is UNDETERMINED


class TestL10ExclusionPrecedence:
    """An excluded match is Denied, whether or not it also matches a
    required concept."""

    def test_excluded_and_required_both_match_denies(self) -> None:
        decision = decide_concept_match(
            ORANGE, hierarchical=True, required={FRUIT}, excluded={CITRUS}, scheme=FRUIT_SCHEME
        )
        assert decision is DENIED

    def test_flat_excluded_match_denies(self) -> None:
        decision = decide_concept_match(
            "y", hierarchical=False, required=set(), excluded={"y"}, scheme=None
        )
        assert decision is DENIED


class TestL11ExclusionGranularity:
    """Standing strictly above an excluded concept, and otherwise admitted,
    is Undetermined -- the candidate's true value may or may not fall under
    the exclusion."""

    def test_ancestor_of_excluded_is_undetermined(self) -> None:
        decision = decide_concept_match(
            FRUIT, hierarchical=True, required={FRUIT}, excluded={CITRUS}, scheme=FRUIT_SCHEME
        )
        assert decision is UNDETERMINED

    def test_ancestor_of_excluded_under_default_inclusion_is_undetermined(self) -> None:
        decision = decide_concept_match(
            FRUIT, hierarchical=True, required=set(), excluded={CITRUS}, scheme=FRUIT_SCHEME
        )
        assert decision is UNDETERMINED

    def test_unrelated_candidate_is_not_caught_by_exclusion_granularity(self) -> None:
        decision = decide_concept_match(
            VEGETABLE, hierarchical=True, required=set(), excluded={CITRUS}, scheme=FRUIT_SCHEME
        )
        assert decision is PERMITTED


class TestL12DefaultInclusion:
    """Exclusions only, no required concept: admits any member not excluded
    (and not an ancestor of an excluded concept, L11)."""

    def test_exact_match_default_inclusion(self) -> None:
        decision = decide_concept_match(
            "z", hierarchical=False, required=set(), excluded={"y"}, scheme=None
        )
        assert decision is PERMITTED


class TestL14HierarchyPrecondition:
    """A flat scheme (no member has a broader member within it) leaves an
    otherwise-undecided member Undetermined, before L12's default inclusion
    applies -- but L10's exclusion still takes precedence over it."""

    def test_required_member_is_permitted(self) -> None:
        decision = decide_concept_match(
            "a", hierarchical=True, required={"a"}, excluded=set(), scheme=FLAT_SCHEME
        )
        assert decision is PERMITTED

    def test_unrequired_member_is_undetermined_not_denied(self) -> None:
        decision = decide_concept_match(
            "b", hierarchical=True, required={"a"}, excluded=set(), scheme=FLAT_SCHEME
        )
        assert decision is UNDETERMINED

    def test_excluded_member_still_denies(self) -> None:
        decision = decide_concept_match(
            "c", hierarchical=True, required={"a"}, excluded={"c"}, scheme=FLAT_SCHEME
        )
        assert decision is DENIED


class TestL15SetReadingsAndL16Negation:
    """Set readings decide each value as a single candidate would be, combine
    by strong Kleene logic, and a negated condition swaps the final
    Permitted/Denied outcome."""

    def test_some_value_permitted_if_any_matches(self) -> None:
        decision = decide_condition(
            [VEGETABLE, ORANGE],
            reading="SomeValue",
            negated=False,
            hierarchical=True,
            required={CITRUS},
            excluded=set(),
            scheme=FRUIT_SCHEME,
        )
        assert decision is PERMITTED

    def test_every_value_denied_if_any_fails(self) -> None:
        decision = decide_condition(
            [VEGETABLE, ORANGE],
            reading="EveryValue",
            negated=False,
            hierarchical=True,
            required={CITRUS},
            excluded=set(),
            scheme=FRUIT_SCHEME,
        )
        assert decision is DENIED

    def test_single_value_with_no_value_is_undetermined(self) -> None:
        decision = decide_condition(
            [],
            reading="SingleValue",
            negated=False,
            hierarchical=False,
            required={"x"},
            excluded=set(),
            scheme=None,
        )
        assert decision is UNDETERMINED

    def test_single_value_with_several_values_is_undetermined(self) -> None:
        """A SingleValue reading with more than one candidate is ambiguous
        (exe:SeveralCandidates), not a silent pick of the first -- matches
        tools/mork_compilers' SPARQL backend's own "?candidates != 1" rule."""
        decision = decide_condition(
            ["x", "y"],
            reading="SingleValue",
            negated=False,
            hierarchical=False,
            required={"x"},
            excluded=set(),
            scheme=None,
        )
        assert decision is UNDETERMINED

    def test_some_value_with_no_value_is_undetermined(self) -> None:
        decision = decide_condition(
            [],
            reading="SomeValue",
            negated=False,
            hierarchical=False,
            required={"x"},
            excluded=set(),
            scheme=None,
        )
        assert decision is UNDETERMINED

    def test_negation_swaps_permitted_and_denied(self) -> None:
        decided = decide_condition(
            [ORANGE],
            reading="SingleValue",
            negated=True,
            hierarchical=True,
            required={CITRUS},
            excluded=set(),
            scheme=FRUIT_SCHEME,
        )
        assert decided is DENIED

    def test_negation_keeps_undetermined(self) -> None:
        decided = decide_condition(
            [FRUIT],
            reading="SingleValue",
            negated=True,
            hierarchical=True,
            required={FRUIT},
            excluded={CITRUS},
            scheme=FRUIT_SCHEME,
        )
        assert decided is UNDETERMINED
