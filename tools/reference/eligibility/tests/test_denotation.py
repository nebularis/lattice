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

from reference_eligibility.denotation import (
    Scheme,
    decide_concept_match,
    decide_condition,
    decide_condition_with_reliance,
    decide_set_comparison,
    decide_set_comparison_with_reliance,
)
from reference_eligibility.kernel import DENIED, PERMITTED, UNDETERMINED

FRUIT, CITRUS, ORANGE, LEMON, VEGETABLE = "fruit", "citrus", "orange", "lemon", "vegetable"

FRUIT_SCHEME = Scheme(
    members=frozenset({FRUIT, CITRUS, ORANGE, LEMON, VEGETABLE}),
    broader={CITRUS: frozenset({FRUIT}), ORANGE: frozenset({CITRUS}), LEMON: frozenset({CITRUS})},
)

FLAT_SCHEME = Scheme(members=frozenset({"a", "b", "c"}), broader={})
YZ_SCHEME = Scheme(members=frozenset({"y", "z"}), broader={})


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

    def test_a_member_of_a_resolved_scheme_is_admitted(self) -> None:
        assert decide_concept_match("z", hierarchical=False, required=set(), excluded={"y"}, scheme=YZ_SCHEME) is PERMITTED

    def test_no_resolved_scheme_leaves_a_candidate_not_excluded_undetermined(self) -> None:
        decision = decide_concept_match(
            "z", hierarchical=False, required=set(), excluded={"y"}, scheme=None, unresolved=True
        )
        assert decision is UNDETERMINED

    def test_no_resolved_scheme_leaves_an_excluded_candidate_undetermined(self) -> None:
        decision = decide_concept_match(
            "y", hierarchical=False, required=set(), excluded={"y"}, scheme=None, unresolved=True
        )
        assert decision is UNDETERMINED

    def test_a_condition_with_a_required_concept_decides_without_a_scheme(self) -> None:
        """Only hierarchical match and exclusions only read the bound scheme (Resolution.thy, TR3)."""
        assert decide_concept_match("z", hierarchical=False, required={"z"}, excluded={"y"}, unresolved=True) is PERMITTED
        assert decide_concept_match("y", hierarchical=False, required={"z"}, excluded={"y"}, unresolved=True) is DENIED


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


class TestL17Closures:
    """A set reading decides on completeness only under a closure (ADR-A105,
    L15 as restated, L17). The admissions example
    (ontology/eligibility/examples/set-reading-admissions.ttl), both of its
    tables: with the registry's closure and without it."""

    APPLICANTS = {
        "ada": ["history", "physics"],
        "ben": ["history"],
        "cai": [],
        "dee": ["medicine", "physics"],
    }
    CLOSED = {
        "ada": (PERMITTED, PERMITTED),
        "ben": (DENIED, PERMITTED),
        "cai": (DENIED, PERMITTED),
        "dee": (PERMITTED, DENIED),
    }
    OPEN = {
        "ada": (PERMITTED, UNDETERMINED),
        "ben": (UNDETERMINED, UNDETERMINED),
        "cai": (UNDETERMINED, UNDETERMINED),
        "dee": (PERMITTED, DENIED),
    }

    def decide(self, applicant: str, closed: bool) -> tuple:
        values = self.APPLICANTS[applicant]
        stem = decide_condition(values, reading="SomeValue", negated=False, closed=closed,
                                hierarchical=False, required={"mathematics", "physics"}, excluded=set())
        no_medicine = decide_condition(values, reading="SomeValue", negated=True, closed=closed,
                                       hierarchical=False, required={"medicine"}, excluded=set())
        return stem, no_medicine

    def test_with_the_closure(self) -> None:
        for applicant, expected in self.CLOSED.items():
            assert self.decide(applicant, True) == expected, applicant

    def test_without_the_closure(self) -> None:
        for applicant, expected in self.OPEN.items():
            assert self.decide(applicant, False) == expected, applicant

    def test_a_closure_never_changes_a_single_value_reading(self) -> None:
        for values in ([], ["x"], ["x", "y"]):
            for closed in (True, False):
                assert decide_condition(values, reading="SingleValue", negated=False, closed=closed,
                                        hierarchical=False, required={"x"}, excluded=set()) is \
                    decide_condition(values, reading="SingleValue", negated=False, closed=False,
                                     hierarchical=False, required={"x"}, excluded=set())


class TestReliance:
    """The reference reports whether a set reading relied on completeness (ADR-A105's 2026-10-12
    addendum, HQ6a2-Q3), so the differential harness can check the compilers' `?closure` column.
    Reliance is decided before negation: a negated condition relies on what it negates relied on."""

    def test_admissions_under_its_closure(self) -> None:
        values = TestL17Closures.APPLICANTS
        expected = {  # (stem, no-medicine), each (decision, relied)
            "ada": ((PERMITTED, False), (PERMITTED, True)),
            "ben": ((DENIED, True), (PERMITTED, True)),
            "cai": ((DENIED, True), (PERMITTED, True)),
            "dee": ((PERMITTED, False), (DENIED, False)),
        }
        for applicant, (stem, no_medicine) in expected.items():
            assert decide_condition_with_reliance(
                values[applicant], reading="SomeValue", negated=False, closed=True,
                hierarchical=False, required={"mathematics", "physics"}, excluded=set()) == stem, applicant
            assert decide_condition_with_reliance(
                values[applicant], reading="SomeValue", negated=True, closed=True,
                hierarchical=False, required={"medicine"}, excluded=set()) == no_medicine, applicant

    def test_nothing_relies_on_an_absent_closure(self) -> None:
        for values in ([], ["history"], ["physics"]):
            _, relied = decide_condition_with_reliance(
                values, reading="SomeValue", negated=False, closed=False,
                hierarchical=False, required={"physics"}, excluded=set())
            assert relied is False


class TestL18SetComparison:
    """A set comparison decides each tested value against the reference values, then reads the
    outcomes as every value (Subset), some value (Intersects) or some value negated (Disjoint)."""

    def decide(self, comparison, tested, reference, tc=False, rc=False, **rest):
        return decide_set_comparison(
            tested, set(reference), comparison=comparison, hierarchical=False,
            tested_closed=tc, reference_closed=rc, **rest,
        )

    def test_subset_over_every_row_of_the_closure_table(self) -> None:
        # C9b3a-13: tested a,b against reference a, with neither, one and both closures
        rows = {
            (False, False): UNDETERMINED, (True, False): UNDETERMINED,
            (False, True): DENIED, (True, True): DENIED,
        }
        for (tc, rc), expected in rows.items():
            assert self.decide("Subset", ["a", "b"], ["a"], tc, rc) is expected, (tc, rc)
        # every tested value found: Permitted needs only the tested set closed
        assert self.decide("Subset", ["a"], ["a", "b"], True, False) is PERMITTED
        assert self.decide("Subset", ["a"], ["a", "b"], False, False) is UNDETERMINED
        assert self.decide("Subset", ["a"], ["a", "b"], False, True) is UNDETERMINED

    def test_intersects_over_every_row_of_the_closure_table(self) -> None:
        # C9b3a-14
        for tc in (False, True):
            for rc in (False, True):
                assert self.decide("Intersects", ["a", "b"], ["b"], tc, rc) is PERMITTED
        assert self.decide("Intersects", ["a"], ["b"], True, True) is DENIED
        assert self.decide("Intersects", ["a"], ["b"], True, False) is UNDETERMINED
        assert self.decide("Intersects", ["a"], ["b"], False, True) is UNDETERMINED
        assert self.decide("Intersects", ["a"], ["b"], False, False) is UNDETERMINED

    def test_disjoint_is_intersects_negated(self) -> None:
        # C9b3a-15
        for tested in (["a"], ["b"], ["a", "b"], []):
            for tc in (False, True):
                for rc in (False, True):
                    i = self.decide("Intersects", tested, ["b"], tc, rc)
                    d = self.decide("Disjoint", tested, ["b"], tc, rc)
                    assert d is {PERMITTED: DENIED, DENIED: PERMITTED, UNDETERMINED: UNDETERMINED}[i]

    def test_an_empty_tested_set_is_read_as_l15_reads_it(self) -> None:
        # C9b3a-16: under each comparison, closed and open, whatever the reference
        for reference in ([], ["a"]):
            assert self.decide("Subset", [], reference, True, False) is PERMITTED
            assert self.decide("Subset", [], reference, False, True) is UNDETERMINED
            assert self.decide("Intersects", [], reference, True, False) is DENIED
            assert self.decide("Intersects", [], reference, False, True) is UNDETERMINED
            assert self.decide("Disjoint", [], reference, True, False) is PERMITTED
            assert self.decide("Disjoint", [], reference, False, False) is UNDETERMINED

    def test_hierarchical_membership_walks_the_relation_within_the_scheme(self) -> None:
        # C9b3a-17: paris is part of france, part of europe. canada is elsewhere.
        part_of = Scheme.over(
            {"europe", "france", "paris", "canada", "north-america"},
            [("france", "europe"), ("paris", "france"), ("canada", "north-america")],
        )

        def decide(comparison, tested, reference, **rest):
            return decide_set_comparison(
                tested, set(reference), comparison=comparison, hierarchical=True, scheme=part_of,
                tested_closed=True, reference_closed=True, **rest,
            )

        assert decide("Subset", ["paris"], ["europe"]) is PERMITTED
        assert decide("Subset", ["paris"], ["france"]) is PERMITTED
        assert decide("Subset", ["europe"], ["france"]) is DENIED  # above, not below
        assert decide("Subset", ["paris", "canada"], ["europe"]) is DENIED
        assert decide("Intersects", ["canada"], ["europe"]) is DENIED

    def test_a_negated_subset_swaps_permitted_and_denied(self) -> None:
        # C9b3a-18
        assert self.decide("Subset", ["a"], ["a"], True, True, negated=True) is DENIED
        assert self.decide("Subset", ["a"], ["b"], True, True, negated=True) is PERMITTED
        assert self.decide("Subset", ["a"], ["b"], True, False, negated=True) is UNDETERMINED

    def test_a_hierarchical_comparison_with_no_scheme_or_no_applicable_binding_is_undetermined(self) -> None:
        # C9b3a-19
        flat = Scheme(members=frozenset({"a"}), broader={})
        kwargs = dict(comparison="Subset", hierarchical=True, tested_closed=True, reference_closed=True)
        assert decide_set_comparison(["a"], {"a"}, scheme=None, **kwargs) is UNDETERMINED
        assert decide_set_comparison(["a"], {"a"}, scheme=flat, unresolved=True, **kwargs) is UNDETERMINED
        assert decide_set_comparison([], {"a"}, scheme=flat, unresolved=True, **kwargs) is UNDETERMINED
        assert decide_set_comparison(["a"], {"a"}, scheme=flat, **kwargs) is PERMITTED

    def test_reliance_names_the_closure_that_decided(self) -> None:
        # C9b3a-20
        def relied(comparison, tested, reference, tc, rc):
            return decide_set_comparison_with_reliance(
                tested, set(reference), comparison=comparison, hierarchical=False, tested_closed=tc, reference_closed=rc
            )[1]

        assert relied("Subset", ["a"], ["a"], True, True) == {"tested"}
        assert relied("Subset", ["a"], ["b"], False, True) == {"reference"}
        assert relied("Intersects", ["a"], ["a"], True, True) == frozenset()
        assert relied("Intersects", ["a"], ["b"], True, True) == {"tested", "reference"}
        assert relied("Intersects", [], ["b"], True, False) == {"tested"}
        assert relied("Disjoint", ["a"], ["b"], True, True) == {"tested", "reference"}
        assert relied("Subset", ["a"], ["b"], True, False) == frozenset()

    def test_a_value_the_scheme_cannot_place_matches_nothing(self) -> None:
        # C9b3a-47: members b and c, c part of b. x is outside the scheme and linked to both.
        scheme = Scheme.over({"b", "c"}, [("c", "b"), ("c", "x"), ("x", "b")])
        kwargs = dict(comparison="Subset", hierarchical=True, scheme=scheme, tested_closed=True, reference_closed=True)
        assert decide_set_comparison(["c"], {"x"}, **kwargs) is DENIED  # a reference value outside matches nothing
        assert decide_set_comparison(["x"], {"b"}, **kwargs) is UNDETERMINED  # a tested value outside is unplaced (L9)
        assert decide_set_comparison(["c"], {"b"}, **kwargs) is PERMITTED

    def test_over_a_scheme_with_no_hierarchy_only_an_equal_value_is_found(self) -> None:
        # C9b3a-50: L14 for a comparison, zero links. b equals a reference value, c is another member, x is outside.
        flat = Scheme.over({"b", "c"}, [])
        for comparison in ("Subset", "Intersects", "Disjoint"):
            for closed in (False, True):
                kwargs = dict(comparison=comparison, hierarchical=True, scheme=flat, tested_closed=True, reference_closed=closed)
                assert decide_set_comparison(["b"], {"b"}, **kwargs) is (DENIED if comparison == "Disjoint" else PERMITTED)
                assert decide_set_comparison(["c"], {"b"}, **kwargs) is UNDETERMINED, (comparison, closed)
                assert decide_set_comparison(["x"], {"b"}, **kwargs) is UNDETERMINED, (comparison, closed)
        # with one link the same unfound member is Denied under a closed reference
        linked = Scheme.over({"b", "c"}, [("c", "b")])
        assert decide_set_comparison(
            ["b"], {"c"}, comparison="Subset", hierarchical=True, scheme=linked, tested_closed=True, reference_closed=True
        ) is DENIED
