# SPDX-License-Identifier: MPL-2.0
"""What an agent needs to propose a MORK mapping (README "Proposing mappings"): cards that state a source and a target
ontology in one line per term, candidate target terms ranked for each source term, and a check that decodes a proposal's
MCN, validates it against MORK's shapes and compiles it, so the agent corrects itself before a person reviews it."""

from .cards import Card, codebook_card, layer_card, source_card
from .rank import candidates

__all__ = ["Card", "candidates", "codebook_card", "layer_card", "source_card"]
