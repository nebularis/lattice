# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""Namespace constants shared across the persistence compiler."""

from __future__ import annotations

from rdflib import Namespace

DAL = Namespace("https://www.nebularis.org/neuro-semantic/lattice/persistence#")
SH = Namespace("http://www.w3.org/ns/shacl#")
PAT = Namespace("https://example.org/lattice/patterns#")
# Foundation is not imported. Persistence names one of its terms by IRI, as a boundary shape names domain properties (ADR-A78, VH-Q3).
FND = Namespace("https://www.nebularis.org/neuro-semantic/lattice/foundation#")

__all__ = ["DAL", "SH", "PAT", "FND"]
