# SPDX-License-Identifier: MPL-2.0
"""P1, the representation projected onto the layers by the tracked MORK scheme and a rig's extensions, compiled and run
by tools/mork_rdf on Oxigraph. The tracked scheme and its reference data live in the v-rig module's projection
directory. An extension is a graph named at run time: its reference nodes answer the lookups, and each mapping scheme
in it runs after the tracked one on the same source. Every key no scheme reads is a finding, and every row of a
compiled scheme's checks is one."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from rdflib import RDF, Graph, Literal, URIRef
from rdflib.namespace import SH

from . import canon
from .lift import KEY, VRIG, mapping_source

log = logging.getLogger("v_rig")

MORK = "http://www.nebularis.org/ontologies/Mork#"
SCHEME = URIRef(MORK + "MappingScheme")
BASE = "urn:lattice-v-rig:v1:p1/"
AT = datetime(2026, 1, 1, tzinfo=timezone.utc)  # the instant the mappings in force are read at, an input, never the clock
TARGET_MODULES = ("foundation", "vocabulary", "quantification", "ledger", "party", "wording", "instrument", "applied/insurance/common")
_KEY_IN_TEXT = re.compile(r"(?:key:|" + re.escape(KEY) + r")([A-Za-z0-9_.%-]+)")


@dataclass
class P1Result:
    source: Graph
    layers: Graph
    compiled_text: str
    findings: list[tuple[URIRef, URIRef | None, str | None, str, URIRef | None]] = field(default_factory=list)
    reading_keys: tuple[str, ...] = ()
    mapped_keys: frozenset[str] = frozenset()
    compile_findings: list[str] = field(default_factory=list)


def _catalogue():
    import lattice_repo_catalogue as reader
    return reader.load()


def tracked_scheme_paths() -> tuple[Path, Path]:
    module = _catalogue().module("v-rig")
    directory = _catalogue().root / module.directory("projection")
    return directory / "layers.mork.ttl", directory / "reference.ttl"


def target_vocabulary() -> Graph:
    catalogue = _catalogue()
    graph = Graph()
    for name in TARGET_MODULES:
        module = catalogue.module(name)
        for role in ("spec", "vocab"):
            if role in module.roles:
                for path in sorted((catalogue.root / module.directory(role)).glob("*.ttl")):
                    graph.parse(path, format="turtle")
    return graph


def reading_keys(graphs: list[Graph]) -> tuple[str, ...]:
    return tuple(sorted({str(o) for g in graphs for o in g.objects(None, VRIG.readingKey)}))


def keys_read(graphs: list[Graph]) -> frozenset[str]:
    """Every key a scheme reads, by a key: edge in a path or template, or by a guard on vrig:key."""
    found: set[str] = set()
    for g in graphs:
        for obj in g.objects(None, None):
            if isinstance(obj, Literal):
                found.update(canon.percent(k) == k and k or k for k in _KEY_IN_TEXT.findall(str(obj)))
        for shape in g.subjects(SH.path, VRIG.key):
            for value in g.objects(shape, SH.hasValue):
                found.add(str(value))
        for obj in g.objects(None, SH.path):
            if isinstance(obj, URIRef) and str(obj).startswith(KEY):
                found.add(str(obj)[len(KEY):])
    return frozenset(found)


def project(graph: Graph, extensions: list[Path] = (), *, target: Graph | None = None) -> P1Result:
    from mork_rdf import compile_scheme, run

    scheme_path, reference_path = tracked_scheme_paths()
    tracked = Graph().parse(scheme_path, format="turtle")
    reference = Graph().parse(reference_path, format="turtle")
    extension_graphs = [Graph().parse(path, format="turtle") for path in extensions]
    for ext in extension_graphs:
        reference += ext
    schemes = [tracked] + extension_graphs
    target = target if target is not None else target_vocabulary()
    source = mapping_source(graph)
    result = P1Result(source=source, layers=Graph(), compiled_text="", reading_keys=reading_keys(schemes), mapped_keys=keys_read(schemes))
    for prefix, namespace in (("vrig", VRIG), ("key", KEY)):
        result.layers.bind(prefix, str(namespace))
    texts: list[str] = []
    for mapping_graph in schemes:
        for scheme in sorted(mapping_graph.subjects(RDF.type, SCHEME)):
            compiled = compile_scheme(mapping_graph, scheme, base=BASE, at=AT, target_vocabulary=target)
            texts.append(f"# scheme {scheme}\n{compiled.text()}")
            for finding in compiled.findings:
                line = f"{finding.severity.value} {finding.code} {finding.mapping or ''} {finding.message}"
                result.compile_findings.append(line)
                log.info("compile %s", line)
            out = run(compiled, source, reference)
            if out.graph is not None:
                result.layers += out.graph
            if out.tbox is not None:
                result.layers += out.tbox
            for finding in out.findings:
                if finding.code == "Unguarded":
                    continue
                focus = URIRef(finding.focus) if finding.focus else None
                locator = graph.value(focus, VRIG.locator) if focus is not None else None
                message = f"{finding.code}: {finding.message}"
                result.findings.append((VRIG.UncertainMapping, locator, finding.code, message, focus))
    result.compiled_text = "\n\n".join(texts)
    for fact in graph.subjects(RDF.type, VRIG.Fact):
        key = str(graph.value(fact, VRIG.key))
        if key not in result.mapped_keys and key not in result.reading_keys:
            result.findings.append((VRIG.UnmappedKey, graph.value(fact, VRIG.locator), key, "No mapping row reads this key.", fact))
    return result


def add_findings(graph: Graph, run_node: URIRef, found) -> int:
    """Write P1's findings into the representation as vrig:Finding nodes under the identifier rule. A finding with no
    locator, about nothing the rig states, is attached to the run alone and reported on the run's own locator-less id."""
    count = 0
    for kind, locator, key, message, about in found:
        if locator is None:
            log.warning("a %s finding without a locator was dropped: %s", str(kind).rsplit("#", 1)[-1], message)
            continue
        document_id = str(graph.value(locator, VRIG.documentId))
        string = str(locator)[len(canon.locator_iri("")):]
        node = URIRef(canon.finding_iri(str(kind).rsplit("#", 1)[-1], document_id, string, key))
        graph.add((node, RDF.type, VRIG.Finding))
        graph.add((node, VRIG.findingKind, kind))
        graph.add((node, VRIG.locator, locator))
        graph.add((node, VRIG.message, Literal(message)))
        graph.add((node, VRIG.fromRun, run_node))
        if key is not None:
            graph.add((node, VRIG.key, Literal(key)))
        if about is not None:
            graph.add((node, VRIG.about, about))
        count += 1
    return count
