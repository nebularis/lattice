# SPDX-License-Identifier: MPL-2.0
"""A compiled mapping as RDF, and back (README §11.1, MR-Q6), so a deployment can keep it beside its mapping graph,
under version control or in its graph store, and another component can read what will run. The description is named
by the digest of the compiled text, so the same compilation always has the same IRI, and it is its own named graph."""

from __future__ import annotations

from datetime import timezone

from rdflib import Graph, Literal, URIRef
from rdflib.collection import Collection
from rdflib.namespace import PROV, RDF, XSD

from .model import MORK, SH, CompiledMapping, CompiledQuery, Finding, Severity

PREFIX = "urn:mork-rdf:compiled:"
_BOX = {"abox": MORK.InstanceOutput, "tbox": MORK.TerminologyOutput}
_MODE = {"draft": MORK.DraftMode, "review": MORK.ReviewMode, "production": MORK.ProductionMode}
_SEVERITY = {s: MORK[f"{s.value.capitalize()}Finding"] for s in Severity}


def iri(compiled: CompiledMapping) -> URIRef:
    return URIRef(PREFIX + compiled.digest)


def to_rdf(compiled: CompiledMapping) -> Graph:
    """The compiled mapping, each query with its text, the mapping it comes from, its path through the DAG, its stratum,
    its box and what it reads, each finding, and each mapping's effective confidence."""
    g = Graph(identifier=iri(compiled))
    g.bind("mork", MORK)
    g.bind("sh", SH)
    g.bind("prov", PROV)
    node = iri(compiled)
    g.add((node, RDF.type, MORK.CompiledMapping))
    g.add((node, RDF.type, PROV.Entity))
    g.add((node, PROV.wasDerivedFrom, URIRef(compiled.scheme)))
    g.add((node, MORK.mappingDigest, Literal(compiled.mapping_digest)))
    g.add((node, MORK.readAt, Literal(compiled.at, datatype=XSD.dateTime)))
    g.add((node, MORK.compiledBase, Literal(compiled.base, datatype=XSD.anyURI)))
    g.add((node, MORK.compiledInMode, _MODE[compiled.mode]))
    g.add((node, MORK.compiler, Literal(compiled.compiler)))
    for i, q in enumerate(compiled.queries):
        query = URIRef(f"{node}#query-{i}")
        g.add((node, MORK.hasCompiledQuery, query))
        g.add((query, RDF.type, MORK.CompiledQuery))
        g.add((query, RDF.type, SH.SPARQLConstructExecutable if q.kind == "construct" else SH.SPARQLSelectExecutable))
        g.add((query, SH.construct if q.kind == "construct" else SH.select, Literal(q.text)))
        g.add((query, MORK.queryIndex, Literal(i)))
        g.add((query, MORK.queryKind, Literal(q.kind)))
        g.add((query, MORK.compiledFrom, URIRef(q.mapping)))
        path = URIRef(f"{node}#query-{i}-path")
        Collection(g, path, [URIRef(p) for p in q.path])
        g.add((query, MORK.contextPath, path))
        g.add((query, MORK.stratum, Literal(q.stratum)))
        g.add((query, MORK.outputBox, _BOX[q.box]))
        for r in q.reads:
            g.add((query, MORK.readsOutputOf, URIRef(r)))
        if q.code:
            g.add((query, MORK.checkCode, Literal(q.code)))
        if q.head:
            prop, axiom, combination = (URIRef(t) for t in q.head)
            g.add((query, MORK.closureProperty, prop))
            g.add((query, MORK.closureAxiom, axiom))
            g.add((query, MORK.closureCombination, combination))
    for i, f in enumerate(compiled.findings):
        finding = URIRef(f"{node}#finding-{i}")
        g.add((node, MORK.hasCompileFinding, finding))
        g.add((finding, RDF.type, MORK.CompileFinding))
        g.add((finding, MORK.findingIndex, Literal(i)))
        g.add((finding, MORK.findingCode, Literal(f.code)))
        g.add((finding, MORK.findingSeverity, _SEVERITY[f.severity]))
        g.add((finding, MORK.findingMessage, Literal(f.message)))
        if f.mapping:
            g.add((finding, MORK.findingAbout, URIRef(f.mapping)))
    for i, (mapping, value) in enumerate(compiled.confidence):
        entry = URIRef(f"{node}#confidence-{i}")
        g.add((node, MORK.hasEffectiveConfidence, entry))
        g.add((entry, MORK.confidenceOf, URIRef(mapping)))
        g.add((entry, MORK.effectiveConfidence, Literal(value)))
    return g


def from_rdf(g: Graph, node: URIRef | str | None = None) -> CompiledMapping:
    """The compiled mapping a description holds, which runs as the one it was made from. Refused when the queries no
    longer give the digest the description is named by, since a changed query is a different compilation."""
    node = URIRef(node) if node is not None else next(g.subjects(RDF.type, MORK.CompiledMapping))
    one = lambda s, p: g.value(s, p)
    boxes = {v: k for k, v in _BOX.items()}
    queries = []
    for query in sorted(g.objects(node, MORK.hasCompiledQuery), key=lambda q: int(one(q, MORK.queryIndex))):
        kind = str(one(query, MORK.queryKind))
        head = (str(one(query, MORK.closureProperty)), str(one(query, MORK.closureAxiom)), str(one(query, MORK.closureCombination))) \
            if one(query, MORK.closureProperty) is not None else None
        queries.append(CompiledQuery(
            mapping=str(one(query, MORK.compiledFrom)),
            path=tuple(str(p) for p in Collection(g, one(query, MORK.contextPath))),
            kind=kind,
            code=str(one(query, MORK.checkCode)) if one(query, MORK.checkCode) is not None else None,
            text=str(one(query, SH.construct if kind == "construct" else SH.select)),
            box=boxes[one(query, MORK.outputBox)],
            reads=tuple(sorted(str(r) for r in g.objects(query, MORK.readsOutputOf))),
            stratum=int(one(query, MORK.stratum)),
            head=head,
        ))
    severities = {v: k for k, v in _SEVERITY.items()}
    findings = []
    for finding in sorted(g.objects(node, MORK.hasCompileFinding), key=lambda f: int(one(f, MORK.findingIndex))):
        about = one(finding, MORK.findingAbout)
        findings.append(Finding(str(one(finding, MORK.findingCode)), str(about) if about is not None else None,
                                str(one(finding, MORK.findingMessage)), severities[one(finding, MORK.findingSeverity)]))
    confidence = tuple(sorted((str(one(e, MORK.confidenceOf)), float(one(e, MORK.effectiveConfidence)))
                              for e in g.objects(node, MORK.hasEffectiveConfidence)))
    compiled = CompiledMapping(
        scheme=str(one(node, PROV.wasDerivedFrom)),
        mapping_digest=str(one(node, MORK.mappingDigest)),
        # rdflib writes a parsed instant's Z as +00:00 (TSD-63), so it is written back as the compiler writes it.
        at=one(node, MORK.readAt).toPython().astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
        base=str(one(node, MORK.compiledBase)),
        mode={v: k for k, v in _MODE.items()}[one(node, MORK.compiledInMode)],
        queries=tuple(queries),
        findings=tuple(findings),
        confidence=confidence,
        compiler=str(one(node, MORK.compiler)),
    )
    if str(node) != PREFIX + compiled.digest:
        raise ValueError(f"the description's queries give digest {compiled.digest}, not the one {node} is named by")
    return compiled
