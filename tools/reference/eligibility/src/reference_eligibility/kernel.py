# SPDX-License-Identifier: MPL-2.0
"""The logic kernel: Decision, or3/and3/neg3 and the information order decision_leq.

``Decision`` and the three connectives are now generated (FM-D17), not hand-ported: `or3`/`and3`/
`neg3` are rendered by ``tools/literate_extract.py`` from the exact Isabelle ``fun`` clauses
``tools/proofs/eligibility/Kernel.thy`` mechanises (``ontology/eligibility/README.md`` \u00a710), so
the two languages' statements of the same connectives agree by construction, not by two
independent authors' care. ``decision_leq``, ``some_value`` and ``every_value`` stay hand-written
here: ``decision_leq`` is a predicate over equality, not a finite case table; ``some_value``/
``every_value`` fold over an unbounded list, not a closed domain, so neither is generated.
Verified by test (``tests/test_kernel.py``), which reproduces track E's TA1/TA2 claims by
exhaustive enumeration over the three-valued domain, not mechanised again.
"""

from __future__ import annotations

from functools import reduce
from typing import Sequence

from ._decision import DENIED, PERMITTED, UNDETERMINED, Decision
from ._kernel_defs import and3, neg3, or3

__all__ = [
    "Decision",
    "PERMITTED",
    "DENIED",
    "UNDETERMINED",
    "decision_leq",
    "or3",
    "and3",
    "neg3",
    "some_value",
    "every_value",
]


def decision_leq(u: Decision, x: Decision) -> bool:
    """The information order (``KernelLaws.thy``'s ``decision_leq``): ``Undetermined``
    is below every decision, and otherwise a decision is below only itself."""
    return u is UNDETERMINED or u == x


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
