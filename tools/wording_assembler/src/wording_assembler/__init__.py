# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""The reference Wording assembler (ADR-A139, ADR-A140).

Pure functions from graphs to graphs. The assembly time and the minter of every new identifier are
arguments, so the same inputs give the same record (law WA5). The one read from disk is the layer's own
specification and shapes, found through the repository catalogue and passed explicitly as a `Layer`
where a caller wants none.
"""

from .assemble import Result, assemble, reassemble
from .check import check
from .findings import Finding, findings
from .layer import Layer, load_layer
from .plan import Plan, plan
from .render import render

__all__ = [
    "Finding", "Layer", "Plan", "Result",
    "assemble", "check", "findings", "load_layer", "plan", "reassemble", "render",
]
