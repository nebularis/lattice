# SPDX-License-Identifier: MPL-2.0
"""Exhaustive checks of the kernel's claims (TA1, TA2, bounded TL1-TL3b), and
the 30 adequacy fixtures reproduced verbatim from
``tools/proofs/eligibility/Adequacy.thy`` (itself from
``tools/mork_compilers/src/mork_compilers/test_set_readings.py``'s ``MIXES``
data). Where the domain is finite and small (the three-valued ``Decision``
type), exhaustive enumeration is a complete check, not merely an example --
stated as such, per epic principle E2, rather than oversold as more than it
is for the unbounded list-length claims (TL1-TL3b), which are checked only
up to a stated bound.
"""

from __future__ import annotations

import itertools

from reference_eligibility.kernel import (
    DENIED,
    PERMITTED,
    UNDETERMINED,
    and3,
    decision_leq,
    every_value,
    neg3,
    or3,
    some_value,
)

ALL_DECISIONS = (PERMITTED, DENIED, UNDETERMINED)


def all_lists_up_to(max_length: int):
    """Every list of ``Decision`` values with length 0 to ``max_length``
    inclusive -- a bounded check, not a proof, for claims TL1-TL3b state over
    lists of any length."""
    for length in range(max_length + 1):
        yield from itertools.product(ALL_DECISIONS, repeat=length)


class TestTA1MonotoneOr3And3:
    """or3/and3 are monotone in both arguments (KernelLaws.thy's TA1),
    checked exhaustively over all 27 triples for each of the four lemmas."""

    def test_or3_monotone_left(self) -> None:
        for a, a_prime, b in itertools.product(ALL_DECISIONS, repeat=3):
            if decision_leq(a, a_prime):
                assert decision_leq(or3(a, b), or3(a_prime, b)), (a, a_prime, b)

    def test_or3_monotone_right(self) -> None:
        for a, b, b_prime in itertools.product(ALL_DECISIONS, repeat=3):
            if decision_leq(b, b_prime):
                assert decision_leq(or3(a, b), or3(a, b_prime)), (a, b, b_prime)

    def test_and3_monotone_left(self) -> None:
        for a, a_prime, b in itertools.product(ALL_DECISIONS, repeat=3):
            if decision_leq(a, a_prime):
                assert decision_leq(and3(a, b), and3(a_prime, b)), (a, a_prime, b)

    def test_and3_monotone_right(self) -> None:
        for a, b, b_prime in itertools.product(ALL_DECISIONS, repeat=3):
            if decision_leq(b, b_prime):
                assert decision_leq(and3(a, b), and3(a, b_prime)), (a, b, b_prime)


class TestTA2Neg3:
    """neg3 is involutive, monotone, and fixes Undetermined (KernelLaws.thy's
    TA2), checked exhaustively."""

    def test_neg3_involutive(self) -> None:
        for a in ALL_DECISIONS:
            assert neg3(neg3(a)) == a

    def test_neg3_monotone(self) -> None:
        for a, a_prime in itertools.product(ALL_DECISIONS, repeat=2):
            if decision_leq(a, a_prime):
                assert decision_leq(neg3(a), neg3(a_prime)), (a, a_prime)

    def test_neg3_fixes_undetermined(self) -> None:
        assert neg3(UNDETERMINED) is UNDETERMINED


CLOSED = (True, False)


class TestTL1SomeEveryValueSpec:
    """some_value/every_value's own characterisation (Eligibility.thy's
    TL1-some, TL1-every, restated for closures, L17), checked over every list
    up to length 3, closed and open."""

    def test_some_value_spec(self) -> None:
        for closed in CLOSED:
            for xs in all_lists_up_to(3):
                result = some_value(closed, list(xs))
                if PERMITTED in xs:
                    assert result is PERMITTED, (closed, xs)
                elif closed and all(x is DENIED for x in xs):
                    assert result is DENIED, (closed, xs)
                else:
                    assert result is UNDETERMINED, (closed, xs)

    def test_every_value_spec(self) -> None:
        for closed in CLOSED:
            for xs in all_lists_up_to(3):
                result = every_value(closed, list(xs))
                if DENIED in xs:
                    assert result is DENIED, (closed, xs)
                elif closed and all(x is PERMITTED for x in xs):
                    assert result is PERMITTED, (closed, xs)
                else:
                    assert result is UNDETERMINED, (closed, xs)


class TestTL2Monotone:
    """some_value/every_value are monotone pointwise over the list
    (Eligibility.thy's TL2), checked over every pair of equal-length lists
    up to length 3 whose elements are pointwise related by decision_leq,
    closed and open."""

    def test_some_value_monotone(self) -> None:
        for closed in CLOSED:
            for length in range(4):
                for xs in itertools.product(ALL_DECISIONS, repeat=length):
                    for ys in itertools.product(ALL_DECISIONS, repeat=length):
                        if all(decision_leq(x, y) for x, y in zip(xs, ys)):
                            assert decision_leq(some_value(closed, list(xs)), some_value(closed, list(ys))), (xs, ys)

    def test_every_value_monotone(self) -> None:
        for closed in CLOSED:
            for length in range(4):
                for xs in itertools.product(ALL_DECISIONS, repeat=length):
                    for ys in itertools.product(ALL_DECISIONS, repeat=length):
                        if all(decision_leq(x, y) for x, y in zip(xs, ys)):
                            assert decision_leq(every_value(closed, list(xs)), every_value(closed, list(ys))), (xs, ys)


class TestTL3NegationDoesNotCommute:
    """Negating after combining is every_value of the negated list
    (Eligibility.thy's TL3a); negating before, under the same reading,
    disagrees for some input (TL3b). Both closed and open."""

    def test_negate_after_is_every_of_negated(self) -> None:
        for closed in CLOSED:
            for xs in all_lists_up_to(3):
                assert neg3(some_value(closed, list(xs))) == every_value(closed, [neg3(x) for x in xs])

    def test_negate_before_same_reading_disagrees(self) -> None:
        witness = [PERMITTED, DENIED]
        for closed in CLOSED:
            assert neg3(some_value(closed, witness)) != some_value(closed, [neg3(x) for x in witness])


class TestTL4EmptyAndSetInvariance:
    """Eligibility.thy's TL4a (the empty case decides only when closed, L17)
    and TL4b (only the set of values matters)."""

    def test_empty(self) -> None:
        assert some_value(True, []) is DENIED
        assert every_value(True, []) is PERMITTED
        assert some_value(False, []) is UNDETERMINED
        assert every_value(False, []) is UNDETERMINED

    def test_set_invariant(self) -> None:
        for closed in CLOSED:
            for xs in all_lists_up_to(3):
                for ys in all_lists_up_to(3):
                    if set(xs) == set(ys):
                        assert some_value(closed, list(xs)) is some_value(closed, list(ys))
                        assert every_value(closed, list(xs)) is every_value(closed, list(ys))


ROWS = {
    "pd": ([PERMITTED, DENIED], PERMITTED, DENIED, PERMITTED, DENIED),
    "dd": ([DENIED, DENIED], DENIED, DENIED, UNDETERMINED, DENIED),
    "du": ([DENIED, UNDETERMINED], UNDETERMINED, DENIED, UNDETERMINED, DENIED),
    "pp": ([PERMITTED, PERMITTED], PERMITTED, PERMITTED, PERMITTED, UNDETERMINED),
    "pu": ([PERMITTED, UNDETERMINED], PERMITTED, UNDETERMINED, PERMITTED, UNDETERMINED),
    "none": ([], DENIED, PERMITTED, UNDETERMINED, UNDETERMINED),
}


class TestAdequacy:
    """The 30 fixtures of tools/proofs/eligibility/Adequacy.thy, each row
    closed and open: if this module disagreed with the Isabelle kernel,
    these would fail, not merely fail to prove."""

    def test_rows(self) -> None:
        for name, (xs, some_closed, every_closed, some_open, every_open) in ROWS.items():
            assert some_value(True, xs) is some_closed, name
            assert every_value(True, xs) is every_closed, name
            assert some_value(False, xs) is some_open, name
            assert every_value(False, xs) is every_open, name

    def test_negated(self) -> None:
        assert neg3(some_value(True, [PERMITTED, DENIED])) is DENIED
        assert neg3(some_value(True, [DENIED, DENIED])) is PERMITTED
        assert neg3(some_value(True, [DENIED, UNDETERMINED])) is UNDETERMINED
        assert neg3(some_value(False, [DENIED, DENIED])) is UNDETERMINED
        assert neg3(some_value(True, [])) is PERMITTED
        assert neg3(some_value(False, [])) is UNDETERMINED
