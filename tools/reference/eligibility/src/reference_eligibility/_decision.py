# SPDX-License-Identifier: MPL-2.0
"""The three-valued outcome (``elg:Decision``'s three named individuals, `elg:Permitted`,
`elg:Denied`, `elg:Undetermined`).

Split out of ``kernel.py`` (FM-D17) so the generated ``_kernel_defs.py`` can depend on it
without a cycle: ``kernel.py`` imports both this module and ``_kernel_defs``, but this module
imports neither.
"""

from __future__ import annotations

from enum import Enum


class Decision(Enum):
    """The three-valued outcome (``elg:Decision``'s three named individuals)."""

    PERMITTED = "Permitted"
    DENIED = "Denied"
    UNDETERMINED = "Undetermined"


PERMITTED = Decision.PERMITTED
DENIED = Decision.DENIED
UNDETERMINED = Decision.UNDETERMINED
