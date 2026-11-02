# SPDX-License-Identifier: MPL-2.0
"""Runs a compiled mapping over a source graph (README §12): blank nodes named by the skolem rule (§12.2),
the source in the default graph and reference data in its own named graph. The queries run stratum by
stratum. Each construct's triples go to a sink as the store yields them, and a mapping's output is kept in the store,
in a graph named for the mapping, only while a later stratum still reads it. Every check's rows are returned as
findings. Oxigraph is the engine (STD-153)."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Iterator, Optional, Protocol, TextIO, Union

import pyoxigraph as ox
from rdflib import Graph

from . import skolem
from .model import REFERENCE_GRAPH, CompiledMapping, CompiledQuery, Finding, Severity



class Sink(Protocol):
    """Where a run's triples go (README §12.1). `write` is called once per construct or closure, with its query, so a
    sink can tell instance data (`query.box == "abox"`) from T-Box triples and name the mapping that wrote them. A
    triple two queries write reaches the sink twice, which a graph store's set semantics absorbs."""

    def write(self, query: CompiledQuery, triples: Iterable[ox.Triple]) -> None: ...

    def close(self) -> None: ...


class GraphSink:
    """Holds the triples in memory and gives them as two rdflib graphs, instance data and T-Box, once closed."""

    def __init__(self) -> None:
        self._triples: dict = {"abox": set(), "tbox": set()}
        self.graph: Optional[Graph] = None
        self.tbox: Optional[Graph] = None

    def write(self, query: CompiledQuery, triples: Iterable[ox.Triple]) -> None:
        self._triples[query.box].update(triples)

    def close(self) -> None:
        self.graph, self.tbox = (_graph(self._triples[box]) for box in ("abox", "tbox"))


class NTriplesSink:
    """Writes each triple as an N-Triples line as it arrives, the T-Box to its own stream when one is given. Standard
    output keeps the runner's contract to a stream of lines, for a listener that publishes them elsewhere."""

    def __init__(self, abox: TextIO, tbox: Optional[TextIO] = None) -> None:
        self.streams = {"abox": abox, "tbox": tbox or abox}

    def write(self, query: CompiledQuery, triples: Iterable[ox.Triple]) -> None:
        stream = self.streams[query.box]
        for t in triples:
            stream.write(f"{t.subject} {t.predicate} {t.object} .\n")

    def close(self) -> None:
        for stream in set(self.streams.values()):
            stream.flush()


@dataclass(frozen=True)
class RunResult:
    graph: Optional[Graph]         # the target instance triples, when the run kept them in memory
    findings: tuple[Finding, ...]  # the checks' rows, each a focus node the mapping could not map
    tbox: Optional[Graph] = None   # the classes, properties and axioms the mappings create (README §7.6)


Source = Union[Graph, ox.Dataset, Path]


def _triples(source: Source) -> Iterator[ox.Triple]:
    """The triples of a source given as an Oxigraph dataset, an RDF file Oxigraph parses by its extension, or an rdflib
    graph, which is serialised once to reach Oxigraph and is the slowest of the three."""
    if isinstance(source, ox.Dataset):
        return (ox.Triple(q.subject, q.predicate, q.object) for q in source)
    if isinstance(source, Path):
        return (ox.Triple(q.subject, q.predicate, q.object) for q in ox.parse(path=str(source)))
    return iter(ox.parse(source.serialize(format="nt"), format=ox.RdfFormat.N_TRIPLES))


def _quads(source: Source, graph_name) -> Iterator[ox.Quad]:
    return (ox.Quad(t.subject, t.predicate, t.object, graph_name) for t in _triples(source))


def skolemise(source: Source) -> Iterable[ox.Triple]:
    """The source with each blank node named by the skolem rule (README §12.2), so a mapping can read a blank node's
    identity with STR(), and the same node always gives the same target IRIs."""
    return skolem.skolemise(_triples(source))


def run(compiled: CompiledMapping, source: Source, reference: Optional[Source] = None, sink: Optional[Sink] = None) -> RunResult:
    """Runs every query. The source and the reference data may each be an Oxigraph dataset, an RDF file or an rdflib
    graph. With no sink the triples are kept in memory and returned. With a sink they go to it, and the result holds only
    the findings."""
    store = ox.Store()
    report = skolem.Skolemised()
    store.extend(ox.Quad(t.subject, t.predicate, t.object, ox.DefaultGraph()) for t in skolem._rule(_triples(source), report))
    if reference is not None:
        store.extend(_quads(reference, ox.NamedNode(REFERENCE_GRAPH)))
    out = sink if sink is not None else GraphSink()
    # How many queries still to run read each mapping's output, so the output is kept only while one does (option A
    # of the run planner): a mapping no query reads never enters the store.
    readers = Counter(r for q in compiled.queries for r in q.reads)
    rows = []
    for stratum in range(compiled.strata):
        kept = []
        done = Counter()
        for query in compiled.queries:
            if query.stratum != stratum:
                continue
            if query.kind == "construct":
                triples = list(store.query(query.text)) if readers[query.mapping] else store.query(query.text)
                out.write(query, triples)
                if readers[query.mapping]:
                    kept += [ox.Quad(t.subject, t.predicate, t.object, ox.NamedNode(query.mapping)) for t in triples]
            elif query.kind == "closure":
                out.write(query, _close(query, [row["member"] for row in store.query(query.text)]))
            else:
                rows += [(query, row) for row in store.query(query.text)]
            done.update(query.reads)
        # A stratum's output is added once the stratum is done, so no query reads its own stratum's output, and an
        # output no query still to run reads is dropped.
        store.extend(kept)
        for mapping, count in done.items():
            readers[mapping] -= count
            if readers[mapping] == 0:
                store.remove_graph(ox.NamedNode(mapping))
    out.close()
    findings = []
    for query, row in rows:
        focus = row["focus"]
        try:
            value = row["value"]
        except (KeyError, IndexError):
            value = None
        findings.append(Finding(query.code or "Check", query.mapping, _message(query.code),
                                Severity.WARNING, focus=focus.value if focus is not None else None,
                                value=value.value if value is not None else None))
    for digest, count in report.components:
        findings.append(Finding("SkolemCanonical", None, _message("SkolemCanonical"), Severity.WARNING,
                                focus=f"{skolem.PREFIX}c:{digest}", value=str(count)))
    findings = tuple(sorted(findings, key=lambda f: (f.code, f.mapping or "", f.focus or "", f.value or "")))
    if sink is None:
        return RunResult(out.graph, findings, out.tbox)
    return RunResult(None, findings)


def _graph(triples: set) -> Graph:
    out = Graph()
    if triples:
        out.parse(data=ox.serialize(sorted(triples, key=str), format=ox.RdfFormat.N_TRIPLES).decode("utf-8"), format="nt")
    return out


def _close(query: CompiledQuery, members: list) -> list[ox.Triple]:
    """The axiom a closure writes once its members are all known: the one class, or their combination as an OWL list,
    the members in IRI order so a repeat run writes the same graph."""
    prop, axiom, combination = (ox.NamedNode(t) for t in query.head)
    members = sorted({m for m in members if isinstance(m, ox.NamedNode)}, key=str)
    if len(members) == 1:
        return [ox.Triple(prop, axiom, members[0])]
    if not members:
        return []
    first, rest, nil = (ox.NamedNode("http://www.w3.org/1999/02/22-rdf-syntax-ns#" + n) for n in ("first", "rest", "nil"))
    expression, cells = ox.BlankNode(), [ox.BlankNode() for _ in members]
    triples = [ox.Triple(prop, axiom, expression), ox.Triple(expression, combination, cells[0])]
    for i, (cell, member) in enumerate(zip(cells, members)):
        triples += [ox.Triple(cell, first, member), ox.Triple(cell, rest, cells[i + 1] if i + 1 < len(cells) else nil)]
    return triples


def _message(code: Optional[str]) -> str:
    return {
        "IdentityUnbound": "the focus node lacks a value its identity reads, so no target node was made for it",
        "IdentityAmbiguous": "the focus node gives more than one identity, so it was mapped to several target nodes",
        "UnmappedValue": "the value has no correspondence, so the property was not asserted",
        "LookupUnresolved": "no reference node matches the value, so the property was not asserted",
        "LookupAmbiguous": "several reference nodes match the value, and each was asserted",
        "TermKind": "the value's kind, an IRI or a literal, is not what the target property takes",
        "Unguarded": "no guard of the mappings that share this node's path admits it, so none of them mapped it",
        "SkolemCanonical": "these blank nodes are in a cycle, shared, or reached from no named node, so they are named by their component's canonical labels, which change whenever the component does",
        "Uncovered": "the node's class is a declared source entity that no compiled root iterates, so nothing was made from it",
    }.get(code or "", "a check reported this focus node")
