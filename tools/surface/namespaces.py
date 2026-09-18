# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""
Namespace bindings.

Declared once and imported everywhere, following the convention
``tools/mork2rml.py`` establishes for the MORK compiler. Two MORK namespaces
are in play in this repository — the original ontology namespace used by
``mork/spec/Mork.ttl`` and the harmonised lattice namespace used by
``mork/targets/``. Both are bound; ``MORK`` is the one a mapping graph is
actually written in.
"""

from __future__ import annotations

from rdflib import Namespace
from rdflib.namespace import DCTERMS, OWL, RDF, RDFS, SH, SKOS, XSD

LATTICE = "https://www.nebularis.org/neuro-semantic/lattice/"

SRF = Namespace(LATTICE + "surface#")
FND = Namespace(LATTICE + "foundation#")
VOC = Namespace(LATTICE + "vocabulary#")
QNT = Namespace(LATTICE + "quantification#")

MORK = Namespace("http://www.nebularis.org/ontologies/Mork#")
MORK_LATTICE = Namespace(LATTICE + "mork#")

SURFACE_ONTOLOGY = "https://www.nebularis.org/neuro-semantic/surface/0.0.1"

#: Prefixes bound on every emitted module, so that generated Turtle reads the
#: same way whichever module it came from.
OUTPUT_PREFIXES = {
    "srf": SRF,
    "fnd": FND,
    "owl": OWL,
    "rdf": RDF,
    "rdfs": RDFS,
    "xsd": XSD,
    "sh": SH,
    "skos": SKOS,
    "dct": DCTERMS,
}

__all__ = [
    "DCTERMS",
    "FND",
    "LATTICE",
    "MORK",
    "MORK_LATTICE",
    "OUTPUT_PREFIXES",
    "OWL",
    "QNT",
    "RDF",
    "RDFS",
    "SH",
    "SKOS",
    "SRF",
    "SURFACE_ONTOLOGY",
    "VOC",
    "XSD",
]
