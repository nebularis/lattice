# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""
The MORK backend compiler family (ADR-A23, ADR-A24, delivery-plan Phase 5).

Namespace bindings, following the convention ``tools/mork2rml.py`` and
``tools/surface/namespaces.py`` both already establish: declared once here,
imported everywhere in this package.

This package is deliberately independent of ``tools/surface`` — it reads a
MORK mapping graph and an Eligibility/Quantification declaration graph, not
a Surface contract — even though several conventions (parameter-binding
shape, deterministic RDF-list construction) are shared in spirit with both.

**Scope note (user decision, 2026-09-18):** no "native" backend is defined
in this package. The delivery plan's Phase 5 lists a native-IR compiler
among the target family; there is no stated definition anywhere in this
repository of what a native artefact would be, so it is left out rather
than invented here.
"""

from __future__ import annotations

from rdflib import Namespace
from rdflib.namespace import OWL, RDF, RDFS, SH, SKOS, XSD

MORK = Namespace("http://www.nebularis.org/ontologies/Mork#")
EXE = Namespace("https://www.nebularis.org/neuro-semantic/lattice/executable#")
ELG = Namespace("https://www.nebularis.org/neuro-semantic/lattice/eligibility#")
QNT = Namespace("https://www.nebularis.org/neuro-semantic/lattice/quantification#")
VOC = Namespace("https://www.nebularis.org/neuro-semantic/lattice/vocabulary#")
SWRL = Namespace("http://www.w3.org/2003/11/swrl#")
SWRLB = Namespace("http://www.w3.org/2003/11/swrlb#")

OUTPUT_PREFIXES = {
    "mork": MORK,
    "exe": EXE,
    "elg": ELG,
    "qnt": QNT,
    "voc": VOC,
    "skos": SKOS,
    "swrl": SWRL,
    "swrlb": SWRLB,
    "sh": SH,
    "rdf": RDF,
    "rdfs": RDFS,
    "owl": OWL,
    "xsd": XSD,
}

__all__ = [
    "ELG",
    "EXE",
    "MORK",
    "OUTPUT_PREFIXES",
    "OWL",
    "QNT",
    "RDF",
    "RDFS",
    "SH",
    "SKOS",
    "SWRL",
    "SWRLB",
    "VOC",
    "XSD",
]
