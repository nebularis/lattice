# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""Namespace constants shared across the persistence compiler."""

from __future__ import annotations

from rdflib import Namespace

DAL = Namespace("https://www.nebularis.org/neuro-semantic/lattice/persistence#")
SH = Namespace("http://www.w3.org/ns/shacl#")
PAT = Namespace("https://example.org/lattice/patterns#")

__all__ = ["DAL", "SH", "PAT"]
