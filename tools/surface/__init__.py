# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""
Reference implementation of the LATTICE surface compiler.

A surface contract is a semantic declaration and is directly usable without
this compiler: it can be queried with SPARQL, checked with SHACL, and reasoned
over as authored. Compilation is one realisation strategy among several
(ADR-A15), and this is the reference one — deterministic, auditable, and able
to establish its own claims rather than assert them.

Module map, following the layout ``tools/mork2rml.py`` establishes:

``namespaces``  shared namespace bindings
``model``       specification dataclasses and ``SurfaceGraphAnalyser``
``naming``      identifier minting and injectivity checking
``canonical``   canonicalisation and content hashing
``serialise``   deterministic Turtle output and file loading
``compile``     ``SurfaceCompiler`` — the algebra map from contract to symbols
``parity``      the ontology/surface/source comparison discharging law ``srf:R2``
``mork``        lifting to and lowering from ``mrk:ProjectionMapping``
``cli``         command line

Requires rdflib.
"""

__all__ = [
    "canonical",
    "cli",
    "compile",
    "model",
    "mork",
    "namespaces",
    "naming",
    "parity",
    "serialise",
]

GENERATOR_VERSION = "lattice-surface-compiler/0.2.0"
