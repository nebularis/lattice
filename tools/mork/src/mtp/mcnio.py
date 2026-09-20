"""In-process MCN decode, lint, and graph-comparison adapter."""

from __future__ import annotations

from dataclasses import dataclass

import mcn
from rdflib import Graph
from rdflib.compare import to_isomorphic
from rdflib.namespace import OWL, RDF


@dataclass(frozen=True)
class Diagnostic:
    phase: str
    code: str
    line: int | None
    message: str
    severity: str = "error"


@dataclass(frozen=True)
class DecodeResult:
    ok: bool
    graph: Graph | None
    diagnostics: tuple[Diagnostic, ...]


class InProcessTool:
    def decode(self, text: str) -> DecodeResult:
        try:
            return DecodeResult(True, mcn.decode(text), ())
        except mcn.McnSyntaxError as error:
            return DecodeResult(False, None, (Diagnostic("decode", error.code, getattr(error, "line_no", None), str(error)),))

    def lint(self, graph: Graph) -> tuple[Diagnostic, ...]:
        return tuple(Diagnostic("lint", finding.code, finding.line, finding.message, finding.severity) for finding in mcn.lint(graph))

    def graphs_equal(self, left: Graph, right: Graph) -> bool:
        left = Graph() + left
        right = Graph() + right
        for graph in (left, right):
            for triple in list(graph.triples((None, RDF.type, OWL.NamedIndividual))):
                graph.remove(triple)
        return to_isomorphic(left) == to_isomorphic(right)


class NullTool(InProcessTool):
    def encode(self, graph: Graph, hints: object | None = None) -> None:
        return None