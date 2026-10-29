# SPDX-License-Identifier: MPL-2.0
"""MORK structure mappings between RDF vocabularies, compiled to SPARQL 1.1 CONSTRUCT. The README is the design."""

from .compile import compile_scheme, digest
from .layer import MorkLayer, load
from .model import COMPILER, CompiledMapping, CompiledQuery, CompileError, Finding, Severity
from .run import GraphSink, NTriplesSink, RunResult, Sink, run, skolemise

__all__ = ["COMPILER", "CompiledMapping", "CompiledQuery", "CompileError", "Finding", "MorkLayer", "RunResult", "Severity", "Sink", "GraphSink", "NTriplesSink",
           "compile_scheme", "digest", "load", "run", "skolemise"]
