# SPDX-License-Identifier: MPL-2.0
"""MORK's own specification and shapes, which a mapping graph is validated against before it is compiled (README §4.3).
Found through the repository catalogue reader (STD-273), or passed as a `MorkLayer` by a caller outside the repository."""

from __future__ import annotations

import functools
from dataclasses import dataclass
from pathlib import Path

from rdflib import Graph
from rdflib.namespace import SH

from .model import Finding, Severity


@dataclass(frozen=True)
class MorkLayer:
    spec: Graph    # MORK's specification, the ontology graph a validation infers types from
    shapes: Graph  # MORK's shapes: acyclic precedence, the production gate, governance states


@functools.lru_cache(maxsize=None)
def load() -> MorkLayer:
    """The layer of the repository found from `LATTICE_ROOT` or the working directory. Cached, so never modify it."""
    try:
        import lattice_repo_catalogue as reader
    except ImportError as error:
        raise RuntimeError("the repository catalogue reader is not importable: put tools/ on the path, or pass a MorkLayer") from error
    catalogue = reader.load()
    mork = catalogue.module("mork")

    def parse(paths: list[Path]) -> Graph:
        graph = Graph()
        for path in paths:
            graph.parse(path, format="turtle")
        return graph

    foundation = catalogue.module("foundation")
    spec = sorted((catalogue.root / mork.directory("spec")).glob("*.ttl")) + sorted((catalogue.root / foundation.directory("spec")).glob("*.ttl"))
    return MorkLayer(spec=parse(spec), shapes=parse(sorted((catalogue.root / mork.directory("shapes")).glob("*.ttl"))))


def validate(g: Graph, layer: MorkLayer) -> list[Finding]:
    """MORK's shapes over the mapping graph, each violation an error finding and each warning a warning."""
    import pyshacl

    conforms, report, _ = pyshacl.validate(g, shacl_graph=layer.shapes, ont_graph=layer.spec, inference="rdfs", advanced=True, allow_warnings=True)
    if conforms:
        return []
    findings = []
    for result in report.subjects(SH.resultSeverity, None):
        severity = report.value(result, SH.resultSeverity)
        focus = report.value(result, SH.focusNode)
        message = str(report.value(result, SH.resultMessage) or "violates a MORK shape")
        findings.append(Finding("MorkShape", str(focus) if focus is not None else None, message,
                                Severity.ERROR if severity == SH.Violation else Severity.WARNING if severity == SH.Warning else Severity.INFO))
    return findings
