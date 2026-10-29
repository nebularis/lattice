# SPDX-License-Identifier: MPL-2.0
"""Runs a compiled mapping over a source graph (README §12): blank nodes skolemised from the source's RDFC-1.0
canonical form, the source in the default graph and reference data in its own named graph, every CONSTRUCT unioned
into the result, and every check's rows returned as findings. Oxigraph is the engine (STD-153)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import pyoxigraph as ox
from rdflib import Graph

from .model import REFERENCE_GRAPH, CompiledMapping, Finding, Severity

SKOLEM = "urn:mork-rdf:skolem:"


@dataclass(frozen=True)
class RunResult:
    graph: Graph                 # the target triples
    findings: tuple[Finding, ...]  # the checks' rows, each a focus node the mapping could not map


def _quads(g: Graph, graph_name) -> list[ox.Quad]:
    return [ox.Quad(t.subject, t.predicate, t.object, graph_name) for t in ox.parse(g.serialize(format="nt"), format=ox.RdfFormat.N_TRIPLES)]


def skolemise(g: Graph) -> list[ox.Triple]:
    """The graph with each blank node replaced by an IRI from its RDFC-1.0 canonical label, so the same source always
    gives the same IRIs, and a mapping can read a blank node's identity with STR()."""
    dataset = ox.Dataset(ox.Quad(t.subject, t.predicate, t.object) for t in ox.parse(g.serialize(format="nt"), format=ox.RdfFormat.N_TRIPLES))
    dataset.canonicalize(ox.CanonicalizationAlgorithm.RDFC_1_0)

    def term(t):
        return ox.NamedNode(SKOLEM + t.value) if isinstance(t, ox.BlankNode) else t

    return [ox.Triple(term(q.subject), q.predicate, term(q.object)) for q in dataset]


def run(compiled: CompiledMapping, source: Graph, reference: Optional[Graph] = None) -> RunResult:
    store = ox.Store()
    store.extend(ox.Quad(t.subject, t.predicate, t.object, ox.DefaultGraph()) for t in skolemise(source))
    if reference is not None:
        store.extend(_quads(reference, ox.NamedNode(REFERENCE_GRAPH)))
    triples: set = set()
    for query in compiled.constructs:
        triples.update(store.query(query.text))
    out = Graph()
    if triples:
        out.parse(data=ox.serialize(sorted(triples, key=str), format=ox.RdfFormat.N_TRIPLES).decode("utf-8"), format="nt")
    findings = []
    for query in compiled.checks:
        for row in store.query(query.text):
            focus = row["focus"]
            try:
                value = row["value"]
            except (KeyError, IndexError):
                value = None
            findings.append(Finding(query.code or "Check", query.mapping, _message(query.code),
                                    Severity.WARNING, focus=focus.value if focus is not None else None,
                                    value=value.value if value is not None else None))
    return RunResult(out, tuple(sorted(findings, key=lambda f: (f.code, f.mapping or "", f.focus or "", f.value or ""))))


def _message(code: Optional[str]) -> str:
    return {
        "IdentityUnbound": "the focus node lacks a value its identity reads, so no target node was made for it",
        "IdentityAmbiguous": "the focus node gives more than one identity, so it was mapped to several target nodes",
        "UnmappedValue": "the value has no correspondence, so the property was not asserted",
        "LookupUnresolved": "no reference node matches the value, so the property was not asserted",
        "LookupAmbiguous": "several reference nodes match the value, and each was asserted",
        "TermKind": "the value's kind, an IRI or a literal, is not what the target property takes",
    }.get(code or "", "a check reported this focus node")
