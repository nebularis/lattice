# SPDX-License-Identifier: MPL-2.0
"""The Configuration Studio's assembly jobs (ADR-A138, ADR-A140): an `assemble` job runs `tools/wording_assembler`
on each `cst:Assembly` of its input, and a `validate` job on the library checks each form, as
contracts/config-studio/README.md describes. The assembler is pure, so the job's submission time and its own IRI
are all that make a run differ, and the same job gives the same record."""

from __future__ import annotations

from datetime import datetime
from typing import Optional, Tuple

from rdflib import BNode, Graph, Literal, URIRef
from rdflib.namespace import RDF, RDFS, SH

from .config_studio_jobs import CST, _Result, catalogue

WRD = "https://www.nebularis.org/neuro-semantic/lattice/wording#"


def _assembler():
    # The assembler finds its layer through the catalogue reader, which `catalogue` puts on the path.
    catalogue()
    import wording_assembler

    return wording_assembler


def _copy_findings(result: _Result, findings: Graph, group: Optional[URIRef] = None) -> bool:
    """Adds each of the assembler's findings to the job's report. True when none is a violation."""
    ok = True
    for node in sorted(findings.subjects(RDF.type, SH.ValidationResult), key=str):
        severity = findings.value(node, SH.resultSeverity) or SH.Violation
        ok &= severity != SH.Violation
        message = str(findings.value(node, SH.resultMessage) or "")
        if group is not None:
            message = f"{group}: {message}"
        code = findings.value(node, CST.code)
        focus = findings.value(node, SH.focusNode)
        result.finding(severity, message, str(code) if code is not None else None, focus)
    return ok


def validate_library(job: URIRef, library: Graph) -> Graph:
    """Each form of the library checked against Wording's laws for a form."""
    assembler = _assembler()
    result = _Result(job)
    ok = True
    # The input may carry the assemblies beside the library, whose value records belong to no assembled wording yet.
    library = _library(library)
    for form in sorted((w for w in library.subjects(RDF.type, URIRef(WRD + "Wording")) if isinstance(w, URIRef)), key=str):
        if (form, RDF.type, URIRef(WRD + "AssembledWording")) in library:
            continue
        ok &= _copy_findings(result, assembler.check(library, form))
    result.conforms(ok)
    return result.graph


def _settings(graph: Graph, assembly: URIRef) -> Graph:
    """The value records an assembly sets, with every triple reachable from them through blank nodes."""
    out = Graph()
    pending = list(graph.objects(assembly, CST.setting))
    seen = set()
    while pending:
        node = pending.pop()
        if node in seen:
            continue
        seen.add(node)
        for triple in graph.triples((node, None, None)):
            out.add(triple)
            if isinstance(triple[2], BNode):
                pending.append(triple[2])
    return out


def _library(config: Graph) -> Graph:
    """The input without its assemblies and the value records they set, so a form is checked as the library holds it."""
    out = Graph() + config
    for assembly in list(config.subjects(RDF.type, CST.Assembly)):
        for triple in _settings(config, assembly):
            out.remove(triple)
        out.remove((assembly, None, None))
    return out


def assemble_all(job: URIRef, config: Graph, submitted_at: str) -> Tuple[Graph, Graph]:
    """The job's result, and the records of the assemblies that gave one, for the record graph."""
    assembler = _assembler()
    at = datetime.fromisoformat(submitted_at.replace("Z", "+00:00"))
    result = _Result(job)
    records = Graph()
    library = _library(config)
    assemblies = sorted((a for a in config.subjects(RDF.type, CST.Assembly) if isinstance(a, URIRef)), key=str)
    if not assemblies:
        result.finding(SH.Violation, "the input holds no cst:Assembly", "load")
    ok = bool(assemblies)
    for n, assembly in enumerate(assemblies, start=1):
        form = config.value(assembly, CST.assembles)
        if not isinstance(form, URIRef) or (form, RDF.type, URIRef(WRD + "Wording")) not in config:
            result.finding(SH.Violation, f"{config.value(assembly, RDFS.label) or assembly}: names no form of the library with cst:assembles", "load", assembly)
            ok = False
            continue
        counts = {}

        def mint(kind: str, n: int = n) -> URIRef:
            counts[kind] = counts.get(kind, 0) + 1
            return URIRef(f"{job}:record/{n}/{kind}-{counts[kind]}")

        plan = assembler.plan(library, form)
        choices = [c for c in config.objects(assembly, CST.choice) if isinstance(c, URIRef)]
        outcome = assembler.assemble(plan, _settings(config, assembly), choices, at=at, mint=mint)
        ok &= _copy_findings(result, outcome.findings, config.value(assembly, RDFS.label) or assembly) and outcome.ok
        if not outcome.ok or outcome.record is None:
            ok = False
            continue
        records += outcome.record
        result.artefact("record.ttl", "text/turtle", outcome.record.serialize(format="turtle"), str(assembly))
        result.artefact("document.xml", "application/xml", assembler.render(outcome.record, outcome.record_iri, library), str(assembly))
    result.conforms(ok)
    return result.graph, records
