# SPDX-License-Identifier: MPL-2.0
"""Reference resolver for the LATTICE Vocabulary layer's scoped and temporal
binding law (ontology/vocabulary, ADR-A85)."""

from __future__ import annotations

from .model import (
    Binding,
    BindingConflictError,
    CandidateTrace,
    NoApplicableBindingError,
    Resolution,
    ResolutionError,
)
from .resolver import resolve

__all__ = [
    "Binding",
    "BindingConflictError",
    "CandidateTrace",
    "NoApplicableBindingError",
    "Resolution",
    "ResolutionError",
    "resolve",
]
