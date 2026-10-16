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


def some_value(closed: bool, values: Sequence[Decision]) -> Decision:
    """L15's ``SomeValue`` reading, under L17 (``Eligibility.thy``'s ``some_value``).

    Closed (the binding names a closure in force, ADR-A105): fold ``or3`` from
    ``Denied``, its identity, so ``Permitted`` if any value is, ``Denied`` if
    every value is, the empty case included, and ``Undetermined`` otherwise.
    Open: ``Permitted`` if any value is, ``Undetermined`` otherwise, since a
    record proves only what it shows."""
    if closed:
        return reduce(or3, values, DENIED)
    return PERMITTED if PERMITTED in values else UNDETERMINED


def every_value(closed: bool, values: Sequence[Decision]) -> Decision:
    """L15's ``EveryValue`` reading, under L17 (``Eligibility.thy``'s ``every_value``).

    Closed: fold ``and3`` from ``Permitted``, its identity, so ``Denied`` if any
    value is, ``Permitted`` if every value is, the empty case included, and
    ``Undetermined`` otherwise. Open: ``Denied`` if any value is,
    ``Undetermined`` otherwise."""
    if closed:
        return reduce(and3, values, PERMITTED)
    return DENIED if DENIED in values else UNDETERMINED
