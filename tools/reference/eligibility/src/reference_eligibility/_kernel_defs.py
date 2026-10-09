# SPDX-License-Identifier: MPL-2.0
"""Eligibility's kernel connectives, generated from `ontology/eligibility/README.md`'s `isabelle-spec` block by `tools/literate_extract.py` (FM-D17). Never hand-edited: edit the README and regenerate. `decision_leq` is not generated (a predicate over equality, not a finite case table) and stays hand-written in `kernel.py`."""

from __future__ import annotations

from typing import Dict, Tuple

from ._decision import DENIED, PERMITTED, UNDETERMINED, Decision

_OR3: Dict[Tuple[Decision, Decision], Decision] = {
    (PERMITTED, PERMITTED): PERMITTED,
    (PERMITTED, DENIED): PERMITTED,
    (PERMITTED, UNDETERMINED): PERMITTED,
    (DENIED, PERMITTED): PERMITTED,
    (DENIED, DENIED): DENIED,
    (DENIED, UNDETERMINED): UNDETERMINED,
    (UNDETERMINED, PERMITTED): PERMITTED,
    (UNDETERMINED, DENIED): UNDETERMINED,
    (UNDETERMINED, UNDETERMINED): UNDETERMINED,
}

def or3(a: Decision, b: Decision) -> Decision:
    return _OR3[(a, b)]

_AND3: Dict[Tuple[Decision, Decision], Decision] = {
    (PERMITTED, PERMITTED): PERMITTED,
    (PERMITTED, DENIED): DENIED,
    (PERMITTED, UNDETERMINED): UNDETERMINED,
    (DENIED, PERMITTED): DENIED,
    (DENIED, DENIED): DENIED,
    (DENIED, UNDETERMINED): DENIED,
    (UNDETERMINED, PERMITTED): UNDETERMINED,
    (UNDETERMINED, DENIED): DENIED,
    (UNDETERMINED, UNDETERMINED): UNDETERMINED,
}

def and3(a: Decision, b: Decision) -> Decision:
    return _AND3[(a, b)]

_NEG3: Dict[Decision, Decision] = {
    PERMITTED: DENIED,
    DENIED: PERMITTED,
    UNDETERMINED: UNDETERMINED,
}

def neg3(a: Decision) -> Decision:
    return _NEG3[a]
