# SPDX-License-Identifier: MPL-2.0
"""MORK's own specification and shapes, which a mapping graph is validated against before it is compiled (README §4.3).
Found through the repository catalogue reader (STD-273), or passed as a `MorkLayer` by a caller outside the repository."""

from __future__ import annotations

import functools
from dataclasses import dataclass
from pathlib import Path

from typing import Optional

from rdflib import Graph, Literal
from rdflib.namespace import RDF, RDFS, SH

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


_SCHEMA = (RDFS.subClassOf, RDFS.subPropertyOf, RDFS.domain, RDFS.range)


@functools.lru_cache(maxsize=None)
def _tbox(layer: MorkLayer) -> tuple:
    """MORK's specification closed under RDFS once, as the tables a mapping graph's entailments are read from: each
    class's superclasses, each property's superproperties, domains and ranges, all reflexive and transitive."""
    import owlrl

    closed = Graph() + layer.spec
    owlrl.DeductiveClosure(owlrl.RDFS_Semantics).expand(closed)
    supers, props, domains, ranges = {}, {}, {}, {}
    for c, d in closed.subject_objects(RDFS.subClassOf):
        supers.setdefault(c, {c}).add(d)
    for p, q in closed.subject_objects(RDFS.subPropertyOf):
        props.setdefault(p, {p}).add(q)
    for p, c in closed.subject_objects(RDFS.domain):
        domains.setdefault(p, set()).add(c)
    for p, c in closed.subject_objects(RDFS.range):
        ranges.setdefault(p, set()).add(c)
    return supers, props, domains, ranges


def entail(g: Graph, layer: MorkLayer) -> Optional[Graph]:
    """What RDFS entails from the mapping graph against MORK's fixed specification, which is all the shapes read: the
    triples of each superproperty, the types each domain and range gives, and each type's superclasses. None when the
    mapping graph states schema of its own, whose consequences only a full closure finds."""
    if any(next(g.triples((None, p, None)), None) is not None for p in _SCHEMA):
        return None
    supers, props, domains, ranges = _tbox(layer)
    out = Graph() + g
    types = set()
    for s_, p, o in g:
        for q in props.get(p, {p}):
            out.add((s_, q, o))
            types |= {(s_, c) for c in domains.get(q, ())}
            if not isinstance(o, Literal):
                types |= {(o, c) for c in ranges.get(q, ())}
    types |= {(s_, c) for s_, c in g.subject_objects(RDF.type)}
    for node, c in types:
        for d in supers.get(c, {c}):
            out.add((node, RDF.type, d))
    return out


def validate(g: Graph, layer: MorkLayer) -> list[Finding]:
    """MORK's shapes over the mapping graph, each violation an error finding and each warning a warning."""
    import pyshacl

    # The RDFS closure of MORK's specification is computed once, and only what the mapping graph's own triples entail
    # is added here, so a compile does not close the whole specification again (README §4.3). A mapping graph that
    # states schema of its own still takes the full closure.
    entailed = entail(g, layer)
    if entailed is None:
        conforms, report, _ = pyshacl.validate(g, shacl_graph=layer.shapes, ont_graph=layer.spec, inference="rdfs", advanced=True, allow_warnings=True)
    else:
        conforms, report, _ = pyshacl.validate(entailed, shacl_graph=layer.shapes, ont_graph=layer.spec, inference="none", advanced=True,
                                               allow_warnings=True, inplace=True)
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
