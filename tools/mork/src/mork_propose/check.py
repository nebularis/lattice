# SPDX-License-Identifier: MPL-2.0
"""The check a proposing agent runs on its proposal before a person reviews it: decode the MCN with the reference
decoder, validate the graph against MORK's shapes, compile each mapping scheme it holds with `tools/mork_rdf`, and,
given a sample source, run it. Every failure is a finding the agent can act on, never an exception."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from rdflib import Graph
from rdflib.namespace import RDF

MORK_NS = "http://www.nebularis.org/ontologies/Mork#"


@dataclass
class Checked:
    graph: Optional[Graph]
    findings: list = field(default_factory=list)   # (stage, severity, code, about, message)
    schemes: list = field(default_factory=list)    # (scheme, queries, strata)
    output: Optional[Graph] = None

    def summary(self) -> dict:
        return {
            "decoded": self.graph is not None,
            "triples": len(self.graph) if self.graph is not None else 0,
            "schemes": [{"scheme": s, "queries": q, "strata": n} for s, q, n in self.schemes],
            "findings": [{"stage": st, "severity": sv, "code": c, "about": a, "message": m} for st, sv, c, a, m in self.findings],
            "errors": sum(1 for f in self.findings if f[1] == "error"),
            "output_triples": len(self.output) if self.output is not None else None,
        }


def check(mcn: str, *, base: str = "urn:mork-propose:out/", at: Optional[datetime] = None,
          sample: Optional[Graph] = None, target_vocabulary: Optional[Graph] = None) -> Checked:
    """`at` is the instant the mappings in force are read at, an input and never the clock (PRI-56), the epoch of the
    proposal when none is given."""
    import mcn_decoder
    from mork_rdf import CompileError, compile_scheme, run

    at = at or datetime(2000, 1, 1, tzinfo=timezone.utc)
    try:
        g = mcn_decoder.decode(mcn)
    except mcn_decoder.McnSyntaxError as error:
        return Checked(None, [("decode", "error", getattr(error, "code", "syntax"), f"line {getattr(error, 'line_no', '?')}", str(error))])
    return check_graph(g, base=base, at=at, sample=sample, target_vocabulary=target_vocabulary)


def check_graph(g: Graph, *, base: str = "urn:mork-propose:out/", at: Optional[datetime] = None,
                sample: Optional[Graph] = None, target_vocabulary: Optional[Graph] = None, compiled_out: Optional[list] = None) -> Checked:
    """The check of a mapping graph already decoded or parsed, such as the LangGraph pipeline's Turtle. Each compiled
    mapping is appended to `compiled_out` when it is given."""
    from mork_rdf import CompileError, compile_scheme, run

    at = at or datetime(2000, 1, 1, tzinfo=timezone.utc)
    result = Checked(g)
    schemes = sorted(g.subjects(RDF.type, __import__("rdflib").URIRef(MORK_NS + "MappingScheme")), key=str)
    if not schemes:
        result.findings.append(("compile", "error", "NoScheme", None, "the proposal declares no mork:MappingScheme, so nothing compiles"))
    for scheme in schemes:
        try:
            compiled = compile_scheme(g, scheme, base=base, at=at, target_vocabulary=target_vocabulary)
        except CompileError as error:
            for f in error.findings:
                result.findings.append(("compile", f.severity.value, f.code, f.mapping, f.message))
            continue
        result.schemes.append((str(scheme), len(compiled.queries), compiled.strata))
        if compiled_out is not None:
            compiled_out.append(compiled)
        for f in compiled.findings:
            # An uncertain mapping is never compiled, which in a proposal is what it is for: a question a reviewer
            # answers. So the check reports it for review and never counts it an error.
            severity = "review" if f.code == "Uncertain" else f.severity.value
            result.findings.append(("validate" if f.code == "MorkShape" else "compile", severity, f.code, f.mapping, f.message))
        if sample is not None:
            ran = run(compiled, sample)
            result.output = (result.output or Graph()) + ran.graph + ran.tbox
            for f in ran.findings:
                result.findings.append(("run", f.severity.value, f.code, f.focus, f"{f.message} ({f.value})" if f.value else f.message))
    return result
