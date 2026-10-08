# src/spc/util/namespaces.py
"""
RDF namespace definitions for the SPC toolchain.
All IRI prefixes used across the encoder, verifier, and extractor.
"""

from rdflib import Namespace, RDF, RDFS, OWL, XSD

# SPC Core ontology
SPC = Namespace("http://spc.example.org/ontology/core#")

# SPC Extension ontologies
EXT_TIMER = Namespace("http://spc.example.org/ontology/ext/timer#")
EXT_JOB = Namespace("http://spc.example.org/ontology/ext/job#")
EXT_ERROR = Namespace("http://spc.example.org/ontology/ext/error#")
EXT_COMP = Namespace("http://spc.example.org/ontology/ext/compensation#")
EXT_SIGNAL = Namespace("http://spc.example.org/ontology/ext/signal#")
EXT_CONN = Namespace("http://spc.example.org/ontology/ext/connector#")

# Protocol instance namespace (per-protocol A-Box individuals)
PROTO = Namespace("http://spc.example.org/protocol/")

# Domain ontology (insurance — configurable)
INS = Namespace("http://spc.example.org/ontology/insurance#")

# SHACL
SH = Namespace("http://www.w3.org/ns/shacl#")

# Standard bindings for rdflib graph serialisation
NAMESPACE_BINDINGS = {
    "spc": SPC,
    "ext-timer": EXT_TIMER,
    "ext-job": EXT_JOB,
    "ext-error": EXT_ERROR,
    "ext-comp": EXT_COMP,
    "ext-signal": EXT_SIGNAL,
    "ext-conn": EXT_CONN,
    "proto": PROTO,
    "ins": INS,
    "sh": SH,
    "rdf": RDF,
    "rdfs": RDFS,
    "owl": OWL,
    "xsd": XSD,
}


def bind_namespaces(graph):
    """Bind all SPC namespaces to a graph for clean serialisation."""
    for prefix, ns in NAMESPACE_BINDINGS.items():
        graph.bind(prefix, ns)
    return graph