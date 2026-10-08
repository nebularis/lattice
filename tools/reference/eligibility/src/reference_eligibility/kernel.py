# SPDX-License-Identifier: MPL-2.0
"""The logic kernel: Decision, or3/and3/neg3 and the information order decision_leq.

Ported from ``tools/proofs/eligibility/KernelLaws.thy`` and ``Eligibility.thy``
(track E, Isabelle/HOL) -- same names, same case tables, restated in Python so
an independent oracle exists for Eligibility's compilers to be checked
against (track B2). Not a proof: track E already proved TA1 (``or3``/``and3``
monotone in both arguments) and TA2 (``neg3`` involutive, monotone, fixes
``Undetermined``) of the Isabelle original. This module is verified by test
(``tests/test_kernel.py``), which reproduces those claims by exhaustive
enumeration over the three-valued domain, not mechanised again.
"""

from __future__ import annotations

from enum import Enum
from functools import reduce
from typing import Sequence


class Decision(Enum):
    """The three-valued outcome (``elg:Decision``'s three named individuals)."""

    PERMITTED = "Permitted"
    DENIED = "Denied"
    UNDETERMINED = "Undetermined"


PERMITTED = Decision.PERMITTED
DENIED = Decision.DENIED
UNDETERMINED = Decision.UNDETERMINED


def decision_leq(u: Decision, x: Decision) -> bool:
    """The information order (``KernelLaws.thy``'s ``decision_leq``): ``Undetermined``
    is below every decision, and otherwise a decision is below only itself."""
    return u is UNDETERMINED or u == x


def or3(a: Decision, b: Decision) -> Decision:
    """Strong Kleene disjunction (``KernelLaws.thy``'s ``or3``)."""
    if a is PERMITTED:
        return PERMITTED
    if a is DENIED:
        return b
    # a is Undetermined
    if b is PERMITTED:
        return PERMITTED
    return UNDETERMINED


def and3(a: Decision, b: Decision) -> Decision:
    """Strong Kleene conjunction (``KernelLaws.thy``'s ``and3``)."""
    if a is PERMITTED:
        return b
    if a is DENIED:
        return DENIED
    # a is Undetermined
    if b is DENIED:
        return DENIED
    return UNDETERMINED


def neg3(a: Decision) -> Decision:
    """Strong Kleene negation (``KernelLaws.thy``'s ``neg3``): involutive (TA2),
    monotone, and fixes ``Undetermined``."""
    if a is PERMITTED:
        return DENIED
    if a is DENIED:
        return PERMITTED
    return UNDETERMINED


def some_value(values: Sequence[Decision]) -> Decision:
    """L15's ``SomeValue`` reading: ``Permitted`` if any value is, ``Denied`` if
    every value is, ``Undetermined`` otherwise or when there is no value
    (``Eligibility.thy``'s ``some_value``, folding ``or3`` left to right -- the
    fold shape is kept identical to the Isabelle original for a direct
    comparison, though ``or3`` is commutative and associative so the order
    does not affect the result)."""
    if not values:
        return UNDETERMINED
    return reduce(or3, values[1:], values[0])


def every_value(values: Sequence[Decision]) -> Decision:
    """L15's ``EveryValue`` reading: ``Denied`` if any value is, ``Permitted`` if
    every value is, ``Undetermined`` otherwise or when there is no value
    (``Eligibility.thy``'s ``every_value``, folding ``and3``)."""
    if not values:
        return UNDETERMINED
    return reduce(and3, values[1:], values[0])
