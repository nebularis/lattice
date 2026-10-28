# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""The namespaces of a compiled profile and of the patterns vocabulary, shared with the compiler (ADR-A132 decision 3)."""

from __future__ import annotations

from rdflib import Namespace

DAL = Namespace("https://www.nebularis.org/neuro-semantic/lattice/persistence#")
PAT = Namespace("https://www.nebularis.org/neuro-semantic/lattice/persistence-store#")

__all__ = ["DAL", "PAT"]
